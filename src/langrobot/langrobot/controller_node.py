"""controller_node — executes joint trajectories received via two interfaces:

  1. /joint_trajectory topic (trajectory_msgs/JointTrajectory) — legacy, used by
     test_arm_movement.py integration tests.
  2. /panda_arm_controller/follow_joint_trajectory action server
     (control_msgs/action/FollowJointTrajectory) — used by MoveIt2 move_group.

Both paths publish to /forward_position_controller/commands (Float64MultiArray)
which joint_relay_node fans out to per-joint Float64 topics bridged to Gazebo.
"""
import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from std_msgs.msg import Float64MultiArray
from trajectory_msgs.msg import JointTrajectory
from control_msgs.action import FollowJointTrajectory

from langrobot.robots.franka import FrankaRobot
from langrobot.trajectory import trajectory_to_command


def run_trajectory_points(points, publish_fn, now_fn, sleep_fn):
    """Iterate trajectory points in time order, publishing each one.

    Args:
        points: list of objects with .positions and .time_from_start (.sec, .nanosec)
        publish_fn: callable(positions: list[float]) — sends command to joints
        now_fn: callable() -> float — returns current time in seconds
        sleep_fn: callable(seconds: float) — blocks for the inter-point delay
    """
    if not points:
        return
    sorted_points = sorted(
        points,
        key=lambda p: p.time_from_start.sec + p.time_from_start.nanosec / 1e9,
    )
    prev_t = 0.0
    for point in sorted_points:
        t = point.time_from_start.sec + point.time_from_start.nanosec / 1e9
        delay = t - prev_t
        if delay > 0:
            sleep_fn(delay)
        publish_fn(list(point.positions))
        prev_t = t


class ControllerNode(Node):
    def __init__(self):
        super().__init__('controller_node')
        self._robot = FrankaRobot()

        # Legacy topic interface (kept for test_arm_movement.py).
        self._trajectory_sub = self.create_subscription(
            JointTrajectory,
            '/joint_trajectory',
            self._trajectory_callback,
            10,
        )

        self._joint_commands_pub = self.create_publisher(
            Float64MultiArray,
            '/forward_position_controller/commands',
            10,
        )

        # MoveIt2 action server interface.
        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            '/panda_arm_controller/follow_joint_trajectory',
            self._execute_follow_joint_trajectory,
        )

        self.get_logger().info(
            f'controller_node ready — joints: {self._robot.joint_names}'
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def _publish_positions(self, positions: list[float]) -> None:
        cmd = Float64MultiArray()
        cmd.data = positions
        self._joint_commands_pub.publish(cmd)
        self.get_logger().info(
            'Joint command: ' + ', '.join(f'{v:.3f}' for v in positions)
        )

    # ── Legacy topic handler ──────────────────────────────────────────────

    def _trajectory_callback(self, msg: JointTrajectory) -> None:
        try:
            positions = trajectory_to_command(msg)
        except ValueError:
            self.get_logger().warning('Received empty JointTrajectory — ignoring')
            return
        self._publish_positions(positions)

    # ── FollowJointTrajectory action handler ──────────────────────────────

    def _execute_follow_joint_trajectory(self, goal_handle):
        self.get_logger().info('FollowJointTrajectory: executing trajectory')
        trajectory = goal_handle.request.trajectory

        run_trajectory_points(
            trajectory.points,
            publish_fn=self._publish_positions,
            now_fn=time.time,
            sleep_fn=time.sleep,
        )

        goal_handle.succeed()
        result = FollowJointTrajectory.Result()
        result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
        self.get_logger().info('FollowJointTrajectory: succeeded')
        return result


def main(args=None):
    rclpy.init(args=args)
    node = ControllerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
