"""Fan out Float64MultiArray joint commands to per-joint Float64 topics.

controller_node publishes Float64MultiArray to /forward_position_controller/commands.
This node splits that into 7 individual Float64 messages, one per arm joint, on topics
that the ros_gz_bridge forwards to Gazebo's JointPositionController plugins.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, Float64MultiArray

from langrobot.robots.franka import FrankaRobot

_JOINT_NAMES = FrankaRobot().joint_names   # fr3_joint1 … fr3_joint7
_MODEL_NAME = 'panda'


class JointRelayNode(Node):
    def __init__(self):
        super().__init__('joint_relay_node')
        # JointPositionController in Gazebo Harmonic uses the axis-indexed topic
        # /model/<model>/joint/<joint>/0/cmd_pos  (axis index 0).
        self._pubs = {
            name: self.create_publisher(
                Float64,
                f'/model/{_MODEL_NAME}/joint/{name}/0/cmd_pos',
                10,
            )
            for name in _JOINT_NAMES
        }
        self.create_subscription(
            Float64MultiArray,
            '/forward_position_controller/commands',
            self._on_command,
            10,
        )
        self.get_logger().info(
            f'joint_relay_node ready — relaying to {len(_JOINT_NAMES)} joints'
        )

    def _on_command(self, msg: Float64MultiArray) -> None:
        for i, name in enumerate(_JOINT_NAMES):
            if i < len(msg.data):
                out = Float64()
                out.data = float(msg.data[i])
                self._pubs[name].publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = JointRelayNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
