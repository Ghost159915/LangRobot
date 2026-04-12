import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from trajectory_msgs.msg import JointTrajectory

from langrobot.robots.franka import FrankaRobot
from langrobot.trajectory import trajectory_to_command


class ControllerNode(Node):
    def __init__(self):
        super().__init__('controller_node')
        self._robot = FrankaRobot()

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

        self.get_logger().info(
            f'Controller node started for {self._robot.__class__.__name__}'
        )
        self.get_logger().info(
            f'Joints: {self._robot.joint_names}'
        )

    def _trajectory_callback(self, msg: JointTrajectory) -> None:
        try:
            positions = trajectory_to_command(msg)
        except ValueError:
            self.get_logger().warning('Received empty JointTrajectory — ignoring')
            return

        cmd = Float64MultiArray()
        cmd.data = positions
        self._joint_commands_pub.publish(cmd)
        self.get_logger().info(
            f'Published joint command ({len(cmd.data)} joints): '
            + ', '.join(f'{v:.3f}' for v in cmd.data)
        )


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
