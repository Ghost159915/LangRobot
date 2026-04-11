"""
perception_node.py — ROS2 node: camera topics → detect_blocks() → /object_poses.

Subscribes to /camera/rgb_image, /camera/depth_image, /camera/camera_info.
Publishes   to /object_poses (std_msgs/String, JSON array of 5 block dicts).
"""
import json

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String

from langrobot.perception import detect_blocks


class PerceptionNode(Node):
    def __init__(self):
        super().__init__('perception_node')
        self._bridge = CvBridge()
        self._latest_depth = None
        self._camera_info = None

        self.create_subscription(Image, '/camera/rgb_image', self._on_rgb, 10)
        self.create_subscription(Image, '/camera/depth_image', self._on_depth, 10)
        self.create_subscription(CameraInfo, '/camera/camera_info', self._on_camera_info, 10)
        self._pub = self.create_publisher(String, '/object_poses', 10)

        self.get_logger().info('perception_node ready — waiting for camera frames')

    def _on_camera_info(self, msg: CameraInfo) -> None:
        if self._camera_info is None:
            self._camera_info = {
                'fx': msg.k[0],
                'fy': msg.k[4],
                'cx': msg.k[2],
                'cy': msg.k[5],
            }
            self.get_logger().info(f'Camera intrinsics cached: {self._camera_info}')

    def _on_depth(self, msg: Image) -> None:
        try:
            self._latest_depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding='32FC1')
        except Exception as exc:
            self.get_logger().error(f'Depth conversion failed: {exc}')

    def _on_rgb(self, msg: Image) -> None:
        if self._latest_depth is None:
            self.get_logger().warning(
                'No depth frame yet — skipping', throttle_duration_sec=5.0
            )
            return
        if self._camera_info is None:
            self.get_logger().warning(
                'No camera_info yet — skipping', throttle_duration_sec=5.0
            )
            return

        try:
            bgr = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'RGB conversion failed: {exc}')
            return

        try:
            result = detect_blocks(bgr, self._latest_depth, self._camera_info)
        except Exception as exc:
            self.get_logger().error(f'detect_blocks raised: {exc}')
            return

        out = String()
        out.data = json.dumps(result)
        self._pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
