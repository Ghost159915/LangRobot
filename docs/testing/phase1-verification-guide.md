# Phase 1 Verification Guide

How to test Phase 1 on the Linux PC, what to look for, and how to log results so they can be reviewed and improved.

---

## Before You Start

Make sure you have:
- Run `./scripts/bootstrap.sh` to completion (no FAIL lines in smoke tests)
- Logged out and back in after bootstrap (ROCm GPU group activation)
- Opened a fresh terminal and run `source ~/.bashrc`

---

## Test 1 — ROS2 environment is working

**Run:**
```bash
ros2 --version
```

**What to look for:**
```
ros2 cli version: X.X.X
```
Any version output is a pass. An error like `command not found` means ROS2 isn't sourced.

**If it fails:**
```bash
source /opt/ros/jazzy/setup.bash
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
```

---

## Test 2 — ROCm GPU is detected

**Run:**
```bash
rocminfo | grep "gfx1100"
```

**What to look for:**
At least one line containing `gfx1100`. Example:
```
  Name:                    gfx1100
```

**If it fails:**
You likely haven't logged out since bootstrap. Log out, log back in, try again. If still failing run `groups` and check that `render` and `video` are listed.

---

## Test 3 — Ollama is running and model is ready

**Run:**
```bash
ollama list
```

**What to look for:**
```
NAME            ID              SIZE    MODIFIED
llama3.2:latest ...             ...     ...
```
`llama3.2` must appear in the list.

**Quick inference test:**
```bash
ollama run llama3.2 "Say hello in one word"
```
Should respond within a few seconds. If it responds slowly (>30s), the GPU may not be active — check Test 2.

---

## Test 4 — Colcon build succeeds

**Run:**
```bash
cd ~/LangRobot
colcon build --symlink-install
```

**What to look for:**
```
Summary: 1 package finished [Xs]
```
No `failed` or `aborted` packages.

**If it fails:**
Copy the full error output into your log file (see below).

---

## Test 5 — Unit tests pass

**Run:**
```bash
cd ~/LangRobot
source install/setup.bash
PYTHONPATH=src/langrobot python -m pytest tests/ -v
```

**What to look for:**
```
tests/test_robot_abstraction.py::test_franka_implements_base_robot PASSED
tests/test_robot_abstraction.py::test_franka_config_is_robot_config_instance PASSED
tests/test_robot_abstraction.py::test_franka_has_seven_joints PASSED
tests/test_robot_abstraction.py::test_franka_joint_names_are_panda_joints PASSED
tests/test_robot_abstraction.py::test_franka_end_effector_link PASSED
tests/test_robot_abstraction.py::test_franka_planning_group PASSED
tests/test_robot_abstraction.py::test_franka_home_position_length_matches_joint_count PASSED
tests/test_robot_abstraction.py::test_franka_home_positions_are_floats PASSED
tests/test_robot_abstraction.py::test_franka_gripper_open_close_lengths_match PASSED

9 passed in X.XXs
```
All 9 must pass. Any FAILED line is a problem — copy it into your log.

---

## Test 6 — Gazebo launches with Franka arm

**Run in Terminal 1:**
```bash
cd ~/LangRobot
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

**What to look for (in the terminal output):**
```
[controller_node]: Controller node started for FrankaRobot
[controller_node]: Joints: ['panda_joint1', 'panda_joint2', ...]
```

**What to look for (in the Gazebo window):**
- A window opens showing a 3D environment
- The Franka Panda arm is visible (silver/grey 7-joint robot arm)
- The arm is upright, not fallen or clipping through the ground

**Common issues:**

| What you see | What it means |
|-------------|---------------|
| Gazebo opens but no arm after 10s | franka_description not found — check Step 4 of bootstrap |
| `[ERROR] franka_description package not found` | Run `sudo apt install ros-jazzy-franka-description` or check bootstrap Step 4 |
| Gazebo window is black / crashes | GPU/display driver issue — try `export LIBGL_ALWAYS_SOFTWARE=1` before launch as a test |
| `controller_node` not in output | Check `colcon build` succeeded and `source install/setup.bash` was run |

**Take a screenshot** of the Gazebo window with the arm visible. Save it as `logs/phase1-gazebo-screenshot.png`.

---

## Test 7 — Joint command moves the arm

**Keep Terminal 1 running (Gazebo + nodes).**

**Open Terminal 2:**
```bash
cd ~/LangRobot
source install/setup.bash

ros2 topic pub --once /joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [panda_joint1, panda_joint2, panda_joint3, panda_joint4, panda_joint5, panda_joint6, panda_joint7],
  points: [{
    positions: [0.5, -0.5, 0.3, -1.8, 0.1, 1.2, 0.5],
    time_from_start: {sec: 2, nanosec: 0}
  }]
}'
```

**What to look for in Terminal 1 (controller_node output):**
```
[controller_node]: Published joint command (7 joints): 0.500, -0.500, 0.300, -1.800, 0.100, 1.200, 0.500
```

**What to look for in Gazebo:**
The arm should visibly move to a new pose. The joints will rotate — the arm bends.

> **Note:** In Phase 1 the arm may not move smoothly in Gazebo because the full ros2_control hardware plugin isn't wired up yet — that's Phase 5. What matters right now is that the controller node logs the command correctly. If the arm doesn't move in Gazebo but the log line appears, Phase 1 is still a pass.

**Also verify the topic exists:**
```bash
ros2 topic list | grep joint
```
Should show:
```
/joint_commands
/joint_trajectory
```

---

## Test 8 — Check active ROS2 nodes

**Run in Terminal 2:**
```bash
ros2 node list
```

**What to look for:**
```
/controller_node
/robot_state_publisher
```

---

## How to Log Your Results

Copy the template below into `logs/phase1-test-log.md`, fill it in as you run each test, then commit and push. I'll review it and adjust the code or bootstrap script based on what you found.

```bash
# After filling in the log:
git add logs/phase1-test-log.md
git add logs/phase1-gazebo-screenshot.png   # if you took one
git commit -m "test: Phase 1 verification results"
git push origin main
```

---

## What Makes a Good Log Entry

- **Be specific about errors** — paste the full error message, not just "it failed"
- **Note your environment** — Ubuntu version, GPU driver version if you know it
- **Screenshot Gazebo** — a picture is faster to diagnose than a description
- **Paste command output** — copy/paste terminal text rather than paraphrasing
- **Note what you tried** — if you had to do something different from the guide, write it down

The log doesn't need to be perfect — even "I typed X and saw Y" is enough. The goal is to give enough information to diagnose and fix problems.
