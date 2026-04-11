# LangRobot — System Design Spec
**Date:** 2026-04-10  
**Status:** Approved  

---

## Overview

LangRobot is a language-driven robot manipulation system. A user types a plain English command; a Franka Panda arm simulated in Gazebo executes it. The system demonstrates the full perception → planning → action loop using industry-standard ROS2 tooling — the same architecture used at real robotics companies.

**Target audience:** Recruiters and engineers at Figure AI, Agility Robotics, Boston Dynamics, 1X Technologies, Apptronik.

---

## Hardware & Environment

| Machine | Role |
|---------|------|
| Mac M4 | Coding — all source code written here |
| Linux PC (AMD RX 7700 XT, Ubuntu 24.04) | Simulation & execution — ROS2, Gazebo, Ollama run natively |

**Development workflow:** Git-based. Code is committed from the Mac and pulled on the Linux PC. Daily loop:
```
[Mac]   edit → git commit → git push
[Linux] git pull → colcon build → ros2 launch langrobot langrobot.launch.py
```

`colcon build` recompiles only what changed (seconds for Python nodes). The system installs (ROS2, Gazebo, ROCm, Ollama) are one-time and never repeated.

---

## Tech Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Robot middleware | ROS2 Jazzy | Current LTS; native on Ubuntu 24.04; industry standard |
| Physics simulation | Gazebo Harmonic | Paired release for Jazzy |
| Motion planning | MoveIt2 | Standard arm planning framework |
| Robot arm | Franka Panda (FR3) | 7-DOF; used in research labs at target companies |
| Language model | Ollama + Llama 3.2 | Local, no API key, GPU-accelerated via ROCm |
| LLM framework | LangChain | Structured output parsing |
| Object detection | YOLOv8 | GPU-accelerated via ROCm; reused architecture from InspectAI |
| Language | Python 3.12 | Default on Ubuntu 24.04; supported by Jazzy |
| Visualisation | RViz2 | Standard ROS2 visualisation |
| GPU compute | ROCm 6.x | AMD RX 7700 XT (gfx1100); accelerates Ollama + YOLOv8 from day one |

---

## Repository Structure

```
LangRobot/                          ← git repo root = colcon workspace
├── src/
│   └── langrobot/                  ← ROS2 package
│       ├── langrobot/              ← Python package
│       │   ├── lang_node.py        ← LLM command parser
│       │   ├── perception_node.py  ← YOLOv8 + depth → object poses
│       │   ├── planner_node.py     ← MoveIt2 motion planning (orchestrator)
│       │   ├── controller_node.py  ← Trajectory execution via ros2_control
│       │   ├── feedback_node.py    ← Vision-based task verification
│       │   └── robots/             ← Robot abstraction layer
│       │       ├── base_robot.py   ← Abstract interface (joint names, limits, etc.)
│       │       ├── franka.py       ← Franka Panda implementation
│       │       └── ur5.py          ← UR5 (future)
│       ├── config/                 ← MoveIt2 YAML, robot params
│       ├── launch/
│       │   └── langrobot.launch.py ← Single command starts everything
│       ├── resource/, package.xml, setup.py
├── models/                         ← YOLOv8 weights (.pt) — downloaded by bootstrap.sh, not committed to git
├── worlds/                         ← Gazebo .sdf scene files
├── tests/                          ← pytest unit + node tests
│   ├── test_lang_node.py
│   ├── test_perception.py
│   ├── test_planner.py
│   └── test_robot_abstraction.py
├── scripts/
│   └── bootstrap.sh                ← One-time install script for Linux PC
├── docs/superpowers/specs/         ← Design documents
├── ABOUT.md                        ← Project overview + decision log
├── CLAUDE.md                       ← AI assistant instructions
├── README.md
├── requirements.txt                ← Python deps (langchain, ultralytics, …)
└── .gitignore                      ← Includes build/, install/, log/, .superpowers/
```

---

## Node Architecture

Five ROS2 nodes, each with a single responsibility. All communication via named topics — nodes start, stop, and test independently.

### `lang_node`
- **Input:** User text command (string, from terminal or future voice interface)
- **Process:** Sends command to Ollama (Llama 3.2) via LangChain with a structured output parser
- **Output:** Publishes JSON task spec to `/task_command`
- **GPU:** ROCm-accelerated Ollama inference

### `perception_node`
- **Input:** Subscribes to `/camera/rgb_image` and `/camera/depth_image` from Gazebo
- **Process:** YOLOv8 detects and classifies objects; depth data converts 2D detections to 3D world coordinates
- **Output:** Publishes `/object_poses` (geometry_msgs/PoseArray)
- **GPU:** ROCm-accelerated YOLOv8 inference

### `planner_node` _(orchestrator)_
- **Input:** Subscribes to `/task_command` and `/object_poses`
- **Process:** Requests MoveIt2 to plan a collision-free trajectory to achieve the task; uses the robot abstraction layer for arm-specific config
- **Output:** Publishes `/joint_trajectory` (trajectory_msgs/JointTrajectory)

### `controller_node`
- **Input:** Subscribes to `/joint_trajectory`
- **Process:** Sends trajectory to Gazebo via ros2_control interface
- **Output:** Publishes `/joint_commands` (std_msgs/Float64MultiArray) to Gazebo

### `feedback_node`
- **Input:** Subscribes to `/camera/rgb_image` after execution completes
- **Process:** Re-runs perception, compares outcome to task goal
- **Output:** Natural language result string ("Done. The blue block is on the red block." / "Failed — retrying…")

---

## ROS2 Topics

| Topic | Message Type | Publisher → Subscriber |
|-------|-------------|----------------------|
| `/task_command` | std_msgs/String (JSON) | lang_node → planner_node |
| `/object_poses` | geometry_msgs/PoseArray | perception_node → planner_node |
| `/joint_trajectory` | trajectory_msgs/JointTrajectory | planner_node → controller_node |
| `/joint_commands` | std_msgs/Float64MultiArray | controller_node → Gazebo |
| `/camera/rgb_image` | sensor_msgs/Image | Gazebo → perception_node, feedback_node |
| `/camera/depth_image` | sensor_msgs/Image | Gazebo → perception_node |

---

## Robot Abstraction Layer

`robots/base_robot.py` defines the interface all robot configs must implement:
- Joint names and count
- End-effector link name
- Gripper open/close commands
- Planning group name (for MoveIt2)
- Home pose

`robots/franka.py` implements this for the Franka Panda. Adding a new arm (UR5, xArm, custom) means writing a new file and passing `--robot ur5` to the launch file — no node code changes required.

---

## Bootstrap Script (`scripts/bootstrap.sh`)

**Runs once on a fresh Ubuntu 24.04 machine. Never run again after initial setup.**

| Step | What it installs |
|------|-----------------|
| 1 | System update + base deps (curl, git, build-essential) |
| 2 | ROS2 Jazzy (ros-jazzy-desktop, ros2-control, ros-jazzy-moveit) |
| 3 | Gazebo Harmonic + ros-gz bridge |
| 4 | Franka ROS2 packages (franka_ros2, franka_description) |
| 5 | ROCm 6.x (amdgpu-install → rocm, rocm-hip-sdk) |
| 6 | Ollama + pull llama3.2 |
| 7 | Python deps (`pip install -r requirements.txt`) |
| 8 | rosdep install + initial colcon build |
| 9 | Smoke test — verify ROS2, Gazebo, Ollama, ROCm all reachable |

---

## Testing Strategy

Three layers, each independently runnable:

| Layer | Scope | Command |
|-------|-------|---------|
| Unit | Pure Python logic — JSON parsing, pose math, trajectory validation | `pytest tests/` |
| Node | Single ROS2 node in isolation with mock messages | `ros2 launch ... test_*.launch.py` |
| Integration | Full pipeline with Gazebo running | `ros2 launch langrobot langrobot.launch.py` |

### Per-phase verification gates

Each phase must pass its gate before the next phase begins:

| Phase | Gate |
|-------|------|
| 1 — Bootstrap + arm control | `ros2 topic pub /joint_commands` → Franka arm moves in Gazebo |
| 2 — Scene setup | Camera feed with blocks visible in RViz2 |
| 3 — lang_node | `ros2 topic echo /task_command` shows valid JSON for any English input |
| 4 — perception_node | `ros2 topic echo /object_poses` shows correct block positions |
| 5 — planner_node | Arm picks a block and places it at target location |
| 6 — feedback_node + integration | Full loop: English command → arm moves → "Done." printed |

---

## Demo Scenario

**Scene:** Table with 5 coloured blocks (red, blue, green, yellow, white) in random positions. Franka Panda arm. One overhead RGB-D camera.

**Target commands:**
```
"Stack all the blocks by colour, lightest on top"
"Move the red block to the left side of the table"
"Pick up the block closest to you"
"Undo that last action"
```

Covers: perception, spatial reasoning, sequential planning, memory, error recovery.

---

## Design Decision Log

All significant decisions recorded here. Every architectural change must be sub-agent evaluated before implementation.

| Date | Decision | Reason | Alternatives Considered |
|------|----------|--------|------------------------|
| 2026-04-10 | ROS2 Jazzy over Humble | Ubuntu 24.04 native; current LTS; more CV-relevant | Humble via Docker (rejected: unnecessary complexity) |
| 2026-04-10 | Gazebo Harmonic | Paired with Jazzy | Ignition (rejected: older ROS2 target) |
| 2026-04-10 | Git-based Mac→Linux workflow | Clean separation of coding and execution | VS Code Remote SSH, Docker on Mac (rejected: more overhead) |
| 2026-04-10 | Python 3.12 | Default on Ubuntu 24.04; Jazzy-supported | 3.11 (rejected: manual install needed) |
| 2026-04-10 | Franka Panda (FR3) | 7-DOF; used at target companies; academic prestige | UR5 (considered: better for industrial, less relevant here) |
| 2026-04-10 | Robot abstraction layer | Swap arms without rewriting nodes | Hardcoded Franka (rejected: no extensibility) |
| 2026-04-10 | ROCm GPU from day one | RX 7700 XT (gfx1100) is ROCm 6.x supported; faster LLM + vision | CPU-only (rejected: wasted hardware) |
| 2026-04-10 | Standard colcon workspace (Option A) | Industry-standard layout; native performance; no Docker GPU headaches | Docker Compose hybrid, multi-package workspace (both rejected: premature complexity) |
| 2026-04-11 | Gemma 4 over Llama 3.2 (Phase 1 finding) | Faster GPU-accelerated inference on RX 7700 XT via ROCm; user preference confirmed during Phase 1 testing | Llama 3.2 (was original spec; swapped after Phase 1) |
| 2026-04-11 | Direct Ollama HTTP over LangChain for lang_node | Simpler, fewer dependencies, easier to debug for Phase 3 scope | LangChain deferred to Phase 6+ when chains/memory/tool-use are needed |
| 2026-04-11 | lang_node input via /task_input topic only (no stdin) | Clean ROS2 architecture; stdin unreliable when launched via ros2 launch | Stdin via background thread deferred; add when convenient |
