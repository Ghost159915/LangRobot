"""
lang_node.py — ROS2 node that bridges /task_input → Ollama → /task_command.

Subscribes to /task_input (std_msgs/String).
Publishes   to /task_command (std_msgs/String, JSON).
"""
import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from langrobot.llm_client import parse_command


class LangNode(Node):
    def __init__(self):
        super().__init__('lang_node')

        self._sub = self.create_subscription(
            String,
            '/task_input',
            self._on_task_input,
            10,
        )
        self._pub = self.create_publisher(String, '/task_command', 10)

        self.get_logger().info(
            'lang_node ready — publish to /task_input to send a command'
        )

    def _on_task_input(self, msg: String) -> None:
        text = msg.data.strip()
        if not text:
            self.get_logger().warning('Received empty /task_input — ignoring')
            return

        self.get_logger().info(f'Received command: {text!r}')
        try:
            result = parse_command(text)
        except Exception as exc:
            self.get_logger().error(f'parse_command raised: {exc}')
            result = {'action': 'error', 'reason': str(exc)}

        if result.get('action') == 'error':
            self.get_logger().error(f'LLM error: {result.get("reason")}')
        else:
            self.get_logger().info(f'Parsed task: {result}')

        out = String()
        out.data = json.dumps(result)
        self._pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = LangNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
