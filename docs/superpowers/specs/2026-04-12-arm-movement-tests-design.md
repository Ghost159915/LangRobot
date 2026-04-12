# Arm Movement Tests — Design Spec

**Date:** 2026-04-12
**Author:** Claude (Mac session)
**Status:** Approved

---

## Problem

No test in the project verifies that the Franka arm actually moves when commanded. All existing tests check static config (joint names, types, counts). `controller_node.py` — the only code path that drives the arm — has zero test coverage. A regression in the message conversion logic would go completely undetected.

---

## Goal

Add two levels of tests:

1. **Unit tests** (Mac, no ROS2) — test the `JointTrajectory → Float64MultiArray` conversion logic in isolation
2. **Integration tests** (GhostMachine, Gazebo must be running) — verify the arm physically reaches commanded joint positions

---

## Architecture

```
src/langrobot/langrobot/
├── trajectory.py          NEW  — pure conversion logic, zero ROS2 imports
├── controller_node.py     EDIT — import from trajectory.py, slim callback

tests/
├── test_trajectory.py           NEW  — 6 unit tests, runs on Mac
└── integration/
    ├── __init__.py              NEW  — package marker
    └── test_arm_movement.py     NEW  — 2 integration tests, GhostMachine only
```

Pattern mirrors the existing `perception.py` / `perception_node.py` split: pure logic lives in `trajectory.py`, the ROS2 wrapper lives in `controller_node.py`.

---

## `trajectory.py` — Pure Conversion Module

**Location:** `src/langrobot/langrobot/trajectory.py`

**No ROS2 imports.** Accepts plain Python objects so it is fully testable without a ROS2 environment.

```python
def extract_final_positions(points: list) -> list[float]:
    """Return joint positions from the last point of a trajectory points list.

    Args:
        points: list of objects with a .positions attribute (or plain lists)

    Returns:
        list of float joint positions

    Raises:
        ValueError: if points is empty
    """

def trajectory_to_command(joint_trajectory_msg) -> list[float]:
    """Convert a JointTrajectory ROS2 message to a flat list of float positions.

    Extracts the final trajectory point's positions.

    Raises:
        ValueError: if the message has no points
    """
```

`controller_node.py` calls `trajectory_to_command`. Unit tests call `extract_final_positions` with plain Python data — no mocking required.

---

## `controller_node.py` — Changes

The `_trajectory_callback` method is slimmed down:

- Remove inline conversion logic
- Call `trajectory_to_command(msg)` from `trajectory.py`
- Catch `ValueError` (empty trajectory) and log a warning — same behaviour as before, but now the guard is exercised by the unit tests

---

## Unit Tests — `tests/test_trajectory.py`

Runs on Mac with `pytest`. No ROS2 dependency.

| Test | What it checks |
|------|---------------|
| `test_final_point_positions_returned` | Last point's positions are returned correctly |
| `test_only_last_point_used` | With multiple points, only the final point is used |
| `test_single_point` | Works correctly with exactly one point |
| `test_empty_points_raises_value_error` | Empty list raises `ValueError` |
| `test_seven_joint_positions` | Correct count returned for Franka's 7 joints |
| `test_positions_are_floats` | Returned values are floats |

All tests use plain Python lists — no mocking, no ROS2 imports.

---

## Integration Tests — `tests/integration/test_arm_movement.py`

**Prerequisites:** Stack launched on GhostMachine (`ros2 launch langrobot langrobot.launch.py`)

**Skip guard:** `pytest.mark.skipif(rclpy not importable)` — silently skips on Mac.

**Shared fixture:** A pytest fixture initialises and tears down a minimal `rclpy` test node. The node publishes to `/joint_trajectory` and subscribes to `/joint_states`. Properly destroyed after each test to avoid orphan ROS2 processes.

### Test 1 — `test_arm_moves_to_home_position`

Commands the arm to `FrankaRobot.home_joint_positions`:
```
[0.0, -π/4, 0.0, -3π/4, 0.0, π/2, π/4]
```

Waits up to 8 seconds for all 7 joints to be within ±0.05 rad of the target. Fails with a per-joint diff if timeout is reached.

### Test 2 — `test_arm_moves_to_custom_position`

Commands the arm to a distinct non-home pose (visually different — base rotated, elbow raised):
```
[0.5, -0.5, 0.0, -2.0, 0.0, 1.3, 0.785]
```

Same 8-second timeout, ±0.05 rad tolerance, per-joint diff on failure.

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Empty `JointTrajectory` | `ValueError` raised in `trajectory.py`; `controller_node` catches it and logs a warning |
| Arm doesn't reach target within 8s | Integration test fails with a clear per-joint diff message |
| `rclpy` not available (Mac) | Integration tests are skipped silently |

---

## Running the Tests

### Unit tests (Mac)
```bash
cd ~/Desktop/Projects/LangRobot
pytest tests/test_trajectory.py -v
```

### Integration tests (GhostMachine)
```bash
# Terminal 1 — stack must be running
ros2 launch langrobot langrobot.launch.py

# Terminal 2
source install/setup.bash
pytest tests/integration/test_arm_movement.py -v
```

---

## Success Criteria

- All 6 unit tests pass on Mac
- Both integration tests pass on GhostMachine with Gazebo running
- `controller_node.py` callback is visibly simpler after the refactor
- No existing tests broken (total count increases from 33 to 39+)
