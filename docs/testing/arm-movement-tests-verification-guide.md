# Arm Movement Tests Verification Guide

How to verify `trajectory.py`, the `controller_node` refactor, and the integration tests.

**Gate:** Both integration tests pass — arm physically reaches commanded positions in Gazebo within 8 seconds.

---

## Mac — Unit tests only

No ROS2 needed. Run from the repo root:

```bash
PYTHONPATH=src/langrobot pytest tests/ --ignore=tests/integration -v
```

**What to look for:** 39 tests pass, including the 6 new `test_trajectory.py` tests:
```
tests/test_trajectory.py::test_final_point_positions_returned PASSED
tests/test_trajectory.py::test_only_last_point_used PASSED
tests/test_trajectory.py::test_single_point PASSED
tests/test_trajectory.py::test_empty_points_raises_value_error PASSED
tests/test_trajectory.py::test_seven_joint_positions PASSED
tests/test_trajectory.py::test_positions_are_floats PASSED
6 passed
```

Verify integration tests skip silently on Mac:

```bash
PYTHONPATH=src/langrobot pytest tests/integration/ -v
```

**What to look for:**
```
tests/integration/test_arm_movement.py::test_arm_moves_to_home_position SKIPPED
tests/integration/test_arm_movement.py::test_arm_moves_to_custom_position SKIPPED
2 skipped
```

---

## GhostMachine — Before you start

```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
colcon build --symlink-install
source install/setup.bash
```

---

## Test 1 — Unit tests (39 tests)

```bash
PYTHONPATH=src/langrobot pytest tests/ --ignore=tests/integration -v
```

**What to look for:** All 39 tests pass.

---

## Test 2 — Launch the stack

**Terminal 1:**
```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

Wait until you see both:
```
[controller_node]: Controller node started for FrankaRobot
[perception_node]: perception_node ready
```

The arm should be visible in Gazebo at a neutral pose.

---

## Test 3 — Integration tests

**Terminal 2:**
```bash
cd ~/Desktop/Projects/LangRobot
source install/setup.bash
PYTHONPATH=src/langrobot pytest tests/integration/test_arm_movement.py -v
```

**What to look for:**
```
tests/integration/test_arm_movement.py::test_arm_moves_to_home_position PASSED
tests/integration/test_arm_movement.py::test_arm_moves_to_custom_position PASSED
2 passed
```

**If a test fails**, the error shows per-joint diffs:
```
Arm did not reach home within 8.0s.
Per-joint diffs (tolerance=0.05rad): panda_joint1: 0.002rad, panda_joint2: 0.210rad, ...
```

A large diff on a specific joint means that joint isn't responding. Check `/joint_commands` is reaching Gazebo:
```bash
ros2 topic hz /joint_commands
```

---

## Test 4 — Manual arm command (optional visual check)

Send a trajectory manually and watch the arm move in Gazebo:

**Terminal 2:**
```bash
source install/setup.bash
ros2 topic pub --once /joint_trajectory trajectory_msgs/msg/JointTrajectory \
  '{joint_names: [panda_joint1, panda_joint2, panda_joint3, panda_joint4, panda_joint5, panda_joint6, panda_joint7],
    points: [{positions: [0.5, -0.5, 0.0, -2.0, 0.0, 1.3, 0.785], time_from_start: {sec: 2}}]}'
```

**What to look for:** Arm moves in Gazebo. Controller logs:
```
[controller_node]: Published joint command (7 joints): 0.500, -0.500, 0.000, -2.000, 0.000, 1.300, 0.785
```

---

## Test 5 — Active nodes

```bash
ros2 node list
```

**What to look for:** `/controller_node` in the list.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Integration tests not skipping on Mac | `rclpy` is installed on Mac — tests will try to run. Kill any stale ROS2 processes first |
| `Arm did not reach home within 8.0s` | Check `ros2 topic hz /joint_commands` — if 0 Hz the controller isn't running |
| Controller logs empty trajectory warning | Trajectory message has no points — check `msg.points` is populated before publishing |
| Arm twitches but doesn't hold position | Gazebo physics step may be slow — increase `TIMEOUT` in `test_arm_movement.py` |

---

## Logging results

Fill in `logs/phase4-test-log.md` (arm movement results fit in the Phase 4 log under a new section), then:

```bash
git add logs/phase4-test-log.md
git commit -m "test: arm movement integration test results"
git push origin main
```
