"""gripper_node — GripperCommand action server for fr3_finger_joint1/2.

Translates control_msgs/action/GripperCommand position commands into
per-finger joint Float64 commands using the same JointPositionController
pipeline as the arm joints.

  position = 0.04  → fully open  (~8 cm total gap)
  position = 0.0   → fully closed

Polls /joint_states until both joints are within SETTLE_TOL of target,
then reports succeeded. Times out after SETTLE_TIMEOUT seconds.
"""
import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float64
from sensor_msgs.msg import JointState
from control_msgs.action import GripperCommand

_MODEL_NAME = 'panda'
_FINGER_JOINTS = ['fr3_finger_joint1', 'fr3_finger_joint2']
SETTLE_TOL = 0.002      # metres — 2 mm
SETTLE_TIMEOUT = 3.0    # seconds


class GripperNode(Node):
    def __init__(self):
        super().__init__('gripper_node')

        self._pubs = {
            name: self.create_publisher(
                Float64,
                f'/model/{_MODEL_NAME}/joint/{name}/cmd_pos',
                10,
            )
            for name in _FINGER_JOINTS
        }

        best_effort_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=10,
        )
        self._joint_positions: dict[str, float] = {}
        self.create_subscription(
            JointState, '/joint_states', self._on_joint_state, best_effort_qos
        )

        self._action_server = ActionServer(
            self,
            GripperCommand,
            '/hand_controller/gripper_action',
            self._execute_gripper_command,
        )

        self.get_logger().info('gripper_node ready')

    def _on_joint_state(self, msg: JointState) -> None:
        for name, pos in zip(msg.name, msg.position):
            self._joint_positions[name] = pos

    def _publish_target(self, position: float) -> None:
        for name in _FINGER_JOINTS:
            msg = Float64()
            msg.data = float(position)
            self._pubs[name].publish(msg)

    def _execute_gripper_command(self, goal_handle):
        target = goal_handle.request.command.position
        self.get_logger().info(f'GripperCommand: moving to position={target:.4f} m')

        self._publish_target(target)

        deadline = time.time() + SETTLE_TIMEOUT
        settled = False
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            if all(
                abs(self._joint_positions.get(name, float('inf')) - target) <= SETTLE_TOL
                for name in _FINGER_JOINTS
            ):
                settled = True
                break
            self._publish_target(target)  # re-publish in case message was dropped

        result = GripperCommand.Result()
        if settled:
            result.reached_goal = True
            goal_handle.succeed()
            self.get_logger().info('GripperCommand: succeeded')
        else:
            result.reached_goal = False
            goal_handle.succeed()  # still succeed — arm motion continues
            self.get_logger().warning(
                f'GripperCommand: timeout after {SETTLE_TIMEOUT}s — continuing anyway'
            )
        return result


def main(args=None):
    rclpy.init(args=args)
    node = GripperNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
