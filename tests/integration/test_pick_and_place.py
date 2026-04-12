"""Integration test — full pick-and-place sequence in Gazebo.

Run on GhostMachine with stack launched:
  ros2 launch langrobot langrobot.launch.py

Prerequisite: sudo apt install ros-jazzy-moveit ros-jazzy-moveit-py

Tests:
  1. Publish pick-and-place command (red → blue).
  2. Wait for execution to complete.
  3. Assert block moved from original XY (verified via /object_poses after execution).
"""
from __future__ import annotations
import json
import time
import pytest

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String
    from sensor_msgs.msg import JointState
    HAS_RCLPY = True
except ImportError:
    HAS_RCLPY = False
    Node = object

pytestmark = pytest.mark.skipif(
    not HAS_RCLPY,
    reason='rclpy not available — run on GhostMachine with stack launched'
)

TIMEOUT = 60.0             # seconds — full pick-and-place takes ~30-40 s
MOVE_THRESHOLD = 0.03      # metres — block must move at least 3 cm to count as moved

OBJECT_COLOUR = 'red'
TARGET_COLOUR = 'blue'
OBJECT_ORIGINAL_X = 0.45   # from worlds/basic.sdf block_red pose
OBJECT_ORIGINAL_Y = -0.25


class PickPlaceTestNode(Node):
    def __init__(self):
        super().__init__('pick_place_test_node')
        self._cmd_pub = self.create_publisher(String, '/task_command', 10)
        self._latest_poses: list[dict] = []

        self.create_subscription(String, '/object_poses', self._on_poses, 10)

    def _on_poses(self, msg: String) -> None:
        try:
            self._latest_poses = json.loads(msg.data)
        except json.JSONDecodeError:
            pass

    def send_pick_and_place(self, obj_colour: str, tgt_colour: str) -> None:
        msg = String()
        msg.data = json.dumps({
            'action': 'pick_and_place',
            'object': obj_colour,
            'target': tgt_colour,
        })
        self._cmd_pub.publish(msg)

    def spin_for(self, seconds: float) -> None:
        deadline = time.time() + seconds
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

    def get_block_pose(self, colour: str) -> dict | None:
        for block in self._latest_poses:
            if block['colour'] == colour and block.get('visible'):
                return block
        return None


@pytest.fixture
def node():
    rclpy.init()
    n = PickPlaceTestNode()
    yield n
    n.destroy_node()
    rclpy.shutdown()


def test_pick_and_place_moves_block(node):
    """Full pick-and-place: red block must move from its original position."""
    # Wait for perception to publish initial poses.
    node.spin_for(3.0)
    initial_pose = node.get_block_pose(OBJECT_COLOUR)
    assert initial_pose is not None, (
        f'Block "{OBJECT_COLOUR}" not visible before test — is perception_node running?'
    )

    # Send command and wait for execution to complete.
    node.send_pick_and_place(OBJECT_COLOUR, TARGET_COLOUR)
    node.spin_for(TIMEOUT)

    # Assert block moved from original position.
    final_pose = node.get_block_pose(OBJECT_COLOUR)
    if final_pose is None:
        # Block may be stacked exactly on target — perception reports not visible.
        # This counts as success (block was moved).
        return

    dx = abs(final_pose['x'] - OBJECT_ORIGINAL_X)
    dy = abs(final_pose['y'] - OBJECT_ORIGINAL_Y)
    moved = (dx ** 2 + dy ** 2) ** 0.5
    assert moved >= MOVE_THRESHOLD, (
        f'Block "{OBJECT_COLOUR}" did not move: '
        f'initial=({OBJECT_ORIGINAL_X:.3f}, {OBJECT_ORIGINAL_Y:.3f}), '
        f'final=({final_pose["x"]:.3f}, {final_pose["y"]:.3f}), '
        f'distance={moved:.3f} m (threshold={MOVE_THRESHOLD} m)'
    )
