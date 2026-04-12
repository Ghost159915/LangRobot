# Arm Movement Tests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pure-Python `trajectory.py` conversion module, 6 unit tests for it, refactor `controller_node.py` to use it, and add 2 integration tests that verify the Franka arm physically reaches commanded positions in Gazebo.

**Architecture:** Extract `JointTrajectory → Float64MultiArray` conversion into `trajectory.py` (no ROS2 imports), mirroring the `perception.py`/`perception_node.py` split already in the project. Unit tests call `extract_final_positions` with plain Python data — no mocking. Integration tests use a minimal `rclpy` node, skipped automatically on Mac.

**Tech Stack:** Python 3.12, pytest, rclpy (integration tests only), `trajectory_msgs`, `sensor_msgs`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/langrobot/langrobot/trajectory.py` | **Create** | Pure conversion: `JointTrajectory points → list[float]` |
| `src/langrobot/langrobot/controller_node.py` | **Edit** | Import from `trajectory.py`, remove inline conversion |
| `tests/test_trajectory.py` | **Create** | 6 unit tests, no ROS2 |
| `tests/integration/__init__.py` | **Create** | Package marker (empty) |
| `tests/integration/test_arm_movement.py` | **Create** | 2 integration tests, GhostMachine only |

---

## Task 1: Create `trajectory.py` with TDD

**Files:**
- Create: `src/langrobot/langrobot/trajectory.py`
- Create: `tests/test_trajectory.py`

- [ ] **Step 1: Create the failing test file**

Create `tests/test_trajectory.py` with all 6 tests:

```python
import pytest
import math
from langrobot.trajectory import extract_final_positions, trajectory_to_command


class FakePoint:
    def __init__(self, positions):
        self.positions = positions


class FakeTrajectory:
    def __init__(self, points):
        self.points = points


def test_final_point_positions_returned():
    points = [FakePoint([1.0, 2.0, 3.0]), FakePoint([4.0, 5.0, 6.0])]
    result = extract_final_positions(points)
    assert result == [4.0, 5.0, 6.0]


def test_only_last_point_used():
    points = [FakePoint([0.1, 0.2]), FakePoint([0.3, 0.4]), FakePoint([0.5, 0.6])]
    result = extract_final_positions(points)
    assert result == [0.5, 0.6]


def test_single_point():
    points = [FakePoint([1.0, 2.0, 3.0])]
    result = extract_final_positions(points)
    assert result == [1.0, 2.0, 3.0]


def test_empty_points_raises_value_error():
    with pytest.raises(ValueError):
        extract_final_positions([])


def test_seven_joint_positions():
    home = [0.0, -math.pi / 4, 0.0, -3 * math.pi / 4, 0.0, math.pi / 2, math.pi / 4]
    points = [FakePoint(home)]
    result = extract_final_positions(points)
    assert len(result) == 7


def test_positions_are_floats():
    points = [FakePoint([1.0, 2.0, 3.0])]
    result = extract_final_positions(points)
    for v in result:
        assert isinstance(v, float)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd ~/Desktop/Projects/LangRobot
pytest tests/test_trajectory.py -v
```

Expected: `ImportError: cannot import name 'extract_final_positions' from 'langrobot.trajectory'` (module doesn't exist yet)

- [ ] **Step 3: Create `trajectory.py`**

Create `src/langrobot/langrobot/trajectory.py`:

```python
def extract_final_positions(points) -> list[float]:
    """Return joint positions from the last point of a trajectory points list.

    Args:
        points: list of objects with a .positions attribute

    Returns:
        list of float joint positions

    Raises:
        ValueError: if points is empty
    """
    if not points:
        raise ValueError("JointTrajectory has no points")
    return list(points[-1].positions)


def trajectory_to_command(joint_trajectory_msg) -> list[float]:
    """Convert a JointTrajectory ROS2 message to a flat list of float positions.

    Extracts the final trajectory point's positions.

    Raises:
        ValueError: if the message has no points
    """
    return extract_final_positions(joint_trajectory_msg.points)
```

- [ ] **Step 4: Run tests — verify all 6 pass**

```bash
pytest tests/test_trajectory.py -v
```

Expected output:
```
tests/test_trajectory.py::test_final_point_positions_returned PASSED
tests/test_trajectory.py::test_only_last_point_used PASSED
tests/test_trajectory.py::test_single_point PASSED
tests/test_trajectory.py::test_empty_points_raises_value_error PASSED
tests/test_trajectory.py::test_seven_joint_positions PASSED
tests/test_trajectory.py::test_positions_are_floats PASSED
6 passed
```

- [ ] **Step 5: Run full test suite — no regressions**

```bash
pytest tests/ --ignore=tests/integration -v
```

Expected: all previously passing tests still pass (33 + 6 = 39 total)

- [ ] **Step 6: Commit**

```bash
git add src/langrobot/langrobot/trajectory.py tests/test_trajectory.py
git commit -m "feat: trajectory.py — pure JointTrajectory conversion + 6 unit tests"
```

---

## Task 2: Refactor `controller_node.py` to use `trajectory.py`

**Files:**
- Modify: `src/langrobot/langrobot/controller_node.py`

- [ ] **Step 1: Replace the callback in `controller_node.py`**

Open `src/langrobot/langrobot/controller_node.py`. Add the import after the existing imports:

```python
from langrobot.trajectory import trajectory_to_command
```

Replace the entire `_trajectory_callback` method (currently lines 34–47):

```python
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
```

- [ ] **Step 2: Run full test suite — verify no regressions**

```bash
pytest tests/ --ignore=tests/integration -v
```

Expected: 39 passed (same as after Task 1)

- [ ] **Step 3: Commit**

```bash
git add src/langrobot/langrobot/controller_node.py
git commit -m "refactor: controller_node uses trajectory.py for conversion"
```

---

## Task 3: Create integration tests

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_arm_movement.py`

- [ ] **Step 1: Create the package marker**

Create an empty file `tests/integration/__init__.py`:

```python
```

(Empty file — just marks the directory as a Python package.)

- [ ] **Step 2: Create the integration test file**

Create `tests/integration/test_arm_movement.py`:

```python
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

from langrobot.robots.franka import FrankaRobot

pytestmark = pytest.mark.skipif(
    not HAS_RCLPY,
    reason="rclpy not available — run on GhostMachine with stack launched"
)

JOINT_NAMES = FrankaRobot().joint_names  # 7 panda_joint* names
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
```

- [ ] **Step 3: Verify integration tests are skipped on Mac**

```bash
pytest tests/integration/ -v
```

Expected output:
```
tests/integration/test_arm_movement.py::test_arm_moves_to_home_position SKIPPED (rclpy not available...)
tests/integration/test_arm_movement.py::test_arm_moves_to_custom_position SKIPPED (rclpy not available...)
2 skipped
```

- [ ] **Step 4: Run full unit suite — no regressions**

```bash
pytest tests/ --ignore=tests/integration -v
```

Expected: 39 passed

- [ ] **Step 5: Commit**

```bash
git add tests/integration/__init__.py tests/integration/test_arm_movement.py
git commit -m "feat: integration tests — arm movement verified against /joint_states"
```

---

## Task 4: Push and verify on GhostMachine

- [ ] **Step 1: Push to remote**

```bash
git push origin main
```

- [ ] **Step 2: Pull and rebuild on GhostMachine**

On GhostMachine:
```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
colcon build --symlink-install
```

- [ ] **Step 3: Launch the stack (Terminal 1)**

```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

Wait until you see:
```
[controller_node]: Controller node started for FrankaRobot
[perception_node]: perception_node ready
```

- [ ] **Step 4: Run integration tests (Terminal 2)**

```bash
cd ~/Desktop/Projects/LangRobot
source install/setup.bash
pytest tests/integration/test_arm_movement.py -v
```

Expected:
```
tests/integration/test_arm_movement.py::test_arm_moves_to_home_position PASSED
tests/integration/test_arm_movement.py::test_arm_moves_to_custom_position PASSED
2 passed
```

If a test fails, the error message will show per-joint diffs, e.g.:
```
Arm did not reach home within 8.0s.
Per-joint diffs (tolerance=0.05rad): panda_joint1: 0.002rad, panda_joint2: 0.210rad, ...
```
A large diff on a specific joint means that joint isn't responding to commands — check the `/joint_commands` topic is being received by Gazebo.

- [ ] **Step 5: Run the full unit suite on GhostMachine**

```bash
pytest tests/ --ignore=tests/integration -v
```

Expected: 39 passed

---

## Done — Success Criteria

- [ ] `trajectory.py` exists with `extract_final_positions` and `trajectory_to_command`
- [ ] `controller_node.py` callback calls `trajectory_to_command`, no inline conversion
- [ ] 6 unit tests pass on Mac (`pytest tests/test_trajectory.py`)
- [ ] Integration tests skip silently on Mac
- [ ] Both integration tests pass on GhostMachine with stack running
- [ ] Total test count: 39 unit + 2 integration
