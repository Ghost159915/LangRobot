from __future__ import annotations

import math
import time

import pytest

try:
    import rclpy
    from rclpy.node import Node
    from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
    from sensor_msgs.msg import JointState
    from builtin_interfaces.msg import Duration
    HAS_RCLPY = True
except ImportError:
    HAS_RCLPY = False
    Node = object

pytestmark = pytest.mark.skipif(
    not HAS_RCLPY,
    reason="rclpy not available — run on GhostMachine with stack launched"
)

JOINT_NAMES = [
    'panda_joint1', 'panda_joint2', 'panda_joint3', 'panda_joint4',
    'panda_joint5', 'panda_joint6', 'panda_joint7',
]
TOLERANCE = 0.05   # radians
TIMEOUT = 8.0      # seconds

HOME = [0.0, -math.pi / 4, 0.0, -3 * math.pi / 4, 0.0, math.pi / 2, math.pi / 4]
CUSTOM = [0.5, -0.5, 0.0, -2.0, 0.0, 1.3, 0.785]


class ArmTestNode(Node):
    def __init__(self):
        super().__init__('arm_test_node')
        self._pub = self.create_publisher(JointTrajectory, '/joint_trajectory', 10)
        self._latest_positions: dict[str, float] | None = None
        self.create_subscription(JointState, '/joint_states', self._on_joint_state, 10)

    def _on_joint_state(self, msg: JointState) -> None:
        self._latest_positions = dict(zip(msg.name, msg.position))

    def command(self, positions: list[float]) -> None:
        msg = JointTrajectory()
        msg.joint_names = JOINT_NAMES
        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start = Duration(sec=2)
        msg.points = [point]
        self._pub.publish(msg)

    def wait_for_positions(self, target: list[float]) -> tuple[bool, dict]:
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self._latest_positions is not None:
                diffs = {
                    name: abs(self._latest_positions.get(name, float('inf')) - target[i])
                    for i, name in enumerate(JOINT_NAMES)
                }
                if all(d <= TOLERANCE for d in diffs.values()):
                    return True, diffs
        diffs = (
            {
                name: abs(self._latest_positions.get(name, float('inf')) - target[i])
                for i, name in enumerate(JOINT_NAMES)
            }
            if self._latest_positions is not None
            else {}
        )
        return False, diffs


@pytest.fixture
def arm_node():
    rclpy.init()
    node = ArmTestNode()
    yield node
    node.destroy_node()
    rclpy.shutdown()


def test_arm_moves_to_home_position(arm_node):
    """Arm must reach Franka home position within TIMEOUT seconds."""
    arm_node.command(HOME)
    reached, diffs = arm_node.wait_for_positions(HOME)
    diff_str = ", ".join(f"{k}: {v:.3f}rad" for k, v in diffs.items())
    assert reached, (
        f"Arm did not reach home within {TIMEOUT}s.\n"
        f"Per-joint diffs (tolerance={TOLERANCE}rad): {diff_str}"
    )


def test_arm_moves_to_custom_position(arm_node):
    """Arm must reach a distinct non-home pose within TIMEOUT seconds."""
    arm_node.command(CUSTOM)
    reached, diffs = arm_node.wait_for_positions(CUSTOM)
    diff_str = ", ".join(f"{k}: {v:.3f}rad" for k, v in diffs.items())
    assert reached, (
        f"Arm did not reach custom pose within {TIMEOUT}s.\n"
        f"Per-joint diffs (tolerance={TOLERANCE}rad): {diff_str}"
    )
