# LangRobot — Project Status

> **Living document.** Updated by Claude sessions on Mac and GhostMachine after each phase or significant milestone. When starting a new Claude session, read this file first for full context.

**Last updated:** 2026-04-13  
**Updated by:** Claude (Mac session)

---

## What This Project Is

LangRobot is a language-driven robot manipulation system. A user types a plain English command; a Franka Panda arm simulated in Gazebo executes it.

**Full pipeline:** English command → LLM (Gemma 4 via Ollama) → JSON task spec → perception (camera → block positions) → MoveIt2 planner → trajectory execution → visual feedback

**Purpose:** Portfolio project targeting Figure AI, Agility Robotics, Boston Dynamics, 1X Technologies, Apptronik.

---

## Hardware Setup

| Machine | Role |
|---------|------|
| **Mac M4** | Code development — all source written here, committed to GitHub |
| **GhostMachine** (AMD RX 7700 XT, Ubuntu 24.04) | Simulation & execution — ROS2, Gazebo, Ollama run here |

**Daily workflow:**
```
[Mac]         edit → git commit → git push
[GhostMachine] git pull → colcon build --symlink-install → ros2 launch langrobot langrobot.launch.py
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Robot middleware | ROS2 Jazzy |
| Simulation | Gazebo Harmonic |
| Motion planning | MoveIt2 (Phase 5+) |
| Robot arm | Franka Panda (FR3) |
| LLM | Gemma 4 via Ollama (local, ROCm-accelerated) |
| Object detection | HSV colour segmentation (OpenCV) — YOLOv8 when moving to real hardware |
| GPU | ROCm 6.x (RX 7700 XT / gfx1100) |
| Language | Python 3.12 |

---

## Phase Status

| Phase | Description | Status | Gate |
|-------|-------------|--------|------|
| 1 | Bootstrap + arm control scaffold | ✅ **DONE** | Franka arm moves in Gazebo via `/joint_commands` |
| 2 | Scene: table, blocks, camera, RViz2 | ✅ **DONE** | Camera feed with blocks visible in RViz2 |
| 3 | `lang_node` — English → JSON | ✅ **DONE** | `/task_command` shows valid JSON for any English input |
| 4 | `perception_node` — camera → block poses | ✅ **DONE** | `/object_poses` shows correct 3D positions |
| 4b | Arm movement integration tests | ✅ **DONE** | `pytest tests/integration/` passes — arm physically moves to commanded positions in Gazebo |
| 5 | `planner_node` — MoveIt2 planning | 🔄 **BUILT** (needs GhostMachine verification) | Arm picks and places a block |
| 6 | `feedback_node` + full integration | ⏳ Not started | Full loop: English → arm moves → "Done." |

---

## What's Built (File Map)

```
src/langrobot/langrobot/
├── controller_node.py     ✅ Phase 5 — upgraded: FollowJointTrajectory action server + legacy /joint_trajectory topic
├── gripper_node.py        ✅ Phase 5 — GripperCommand action server for fr3_finger_joint1/2
├── joint_relay_node.py    ✅ Phase 4b — fans out Float64MultiArray → 7 per-joint Float64 topics
├── lang_node.py           ✅ Phase 3 — /task_input → Ollama → /task_command
├── llm_client.py          ✅ Phase 3 — pure Python Ollama HTTP client
├── perception.py          ✅ Phase 4 — HSV detection + 3D projection (pure Python)
├── perception_node.py     ✅ Phase 4 — camera topics → /object_poses
├── planner_node.py        ✅ Phase 5 — /task_command + /object_poses → 9-step pick-and-place via MoveIt2
├── scene.py               ✅ Phase 2 — block/table geometry helpers
├── trajectory.py          ✅ Phase 4b — JointTrajectory → flat position list
└── robots/
    ├── base_robot.py      ✅ Phase 1 — abstract robot interface
    └── franka.py          ✅ Phase 1 — Franka Panda (fr3_joint1–7)

src/langrobot/config/moveit/
├── panda.srdf             ✅ Phase 5 — planning groups: panda_arm (7-DOF), hand (fingers)
├── kinematics.yaml        ✅ Phase 5 — KDL IK solver, 50ms timeout
├── joint_limits.yaml      ✅ Phase 5 — FR3 velocity/acceleration limits
├── moveit_controllers.yaml ✅ Phase 5 — FollowJointTrajectory + GripperCommand action mappings
└── ompl_planning.yaml     ✅ Phase 5 — RRTConnect planner

worlds/
└── basic.sdf              ✅ Phase 5 — blocks now dynamic (mass 50g, mu 1.5 friction); table/camera static

tests/
├── test_controller_action.py  ✅ Phase 5 — FollowJointTrajectory logic unit tests
├── test_lang_node.py          ✅ 8 tests — llm_client unit tests
├── test_perception.py         ✅ 8 tests — perception unit tests (synthetic numpy)
├── test_planner.py            ✅ Phase 5 — planner pose helpers unit tests
├── test_robot_abstraction.py  ✅ 9 tests — FrankaRobot contract
├── test_scene.py              ✅ existing
├── test_trajectory.py         ✅ Phase 4b — trajectory.py unit tests
└── integration/
    ├── test_arm_movement.py       ✅ Phase 4b — arm reaches commanded positions in Gazebo
    └── test_pick_and_place.py     ✅ Phase 5 — full pick-and-place in Gazebo (GhostMachine)

docs/testing/
├── arm-movement-tests-verification-guide.md  ✅ Phase 4b
├── phase5-verification-guide.md              ✅ Phase 5
└── logs/arm-movement-tests-log.md            ✅ Phase 4b — full debug log of Gazebo control issues
```

**Current test count:** 51 passing (Mac, no ROS2 needed) + 3 integration tests (GhostMachine)

---

## Key Design Decisions

| Decision | What | Why |
|----------|------|-----|
| LLM | Direct Ollama HTTP over LangChain | Simpler; LangChain deferred to Phase 6+ |
| LLM model | Gemma 4 over Llama 3.2 | Faster on RX 7700 XT via ROCm |
| Perception | HSV colour segmentation over YOLOv8 | Simulation blocks are solid colours; no training needed. YOLOv8 when moving to real hardware |
| `/object_poses` format | JSON string (`std_msgs/String`) over `geometry_msgs/PoseArray` | PoseArray has no colour names or visibility flags |
| Camera sync | Cache-latest over `message_filters` | Gazebo publishes RGB+depth in lockstep; no drift in sim |
| Camera transform | Hardcoded (no TF2) | Camera never moves in sim |
| lang_node input | `/task_input` topic only (no stdin) | Clean ROS2 architecture |

---

## Inter-Node Communication

| Topic | Type | Publisher → Subscriber |
|-------|------|----------------------|
| `/task_input` | `std_msgs/String` | User → `lang_node` |
| `/task_command` | `std_msgs/String` (JSON) | `lang_node` → `planner_node` |
| `/object_poses` | `std_msgs/String` (JSON array) | `perception_node` → `planner_node` |
| `/joint_trajectory` | `trajectory_msgs/JointTrajectory` | `planner_node` → `controller_node` |
| `/camera/rgb_image` | `sensor_msgs/Image` | Gazebo → `perception_node`, `feedback_node` |
| `/camera/depth_image` | `sensor_msgs/Image` | Gazebo → `perception_node` |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | Gazebo → `perception_node` |

### `/object_poses` JSON schema

```json
[
  {"colour": "red",   "x": 0.32, "y": 0.10, "z": 0.43, "visible": true},
  {"colour": "blue",  "x": null, "y": null,  "z": null,  "visible": false},
  {"colour": "green", "x": 0.28, "y": -0.05, "z": 0.43, "visible": true},
  {"colour": "yellow","x": null, "y": null,  "z": null,  "visible": false},
  {"colour": "white", "x": 0.41, "y": 0.12, "z": 0.43, "visible": true}
]
```

Always 5 entries. `visible: false` + null coords when block not detected.

---

## Known Issues / Watch Points

| Issue | Status | Notes |
|-------|--------|-------|
| `franka_ros2` hardware packages | Handled | `COLCON_IGNORE` set by `fix_franka.sh` — never needed for sim |
| `notify2` DBus error on colcon | Harmless | Desktop notification daemon not running — ignore |
| 3D camera transform y-axis sign | Unverified | Needs confirmation during Phase 4 GhostMachine test. If y-positions are flipped, negate `y_world` in `perception.py:_project_to_world` |
| Ollama model tag | Confirmed | `gemma4` (pull with `ollama pull gemma4`) |
| `gz_ros2_control` ABI mismatch | Worked around | `libgz_hardware_plugins.so` has undefined symbol — compiled against ros2_control 4.x but installed version is older. Bypassed entirely: using `gz-sim-joint-position-controller-system` (Gazebo built-in) + `joint_relay_node` instead |
| JointPositionController default topic | Resolved | Gazebo Harmonic defaults to `/model/<m>/joint/<j>/0/cmd_pos` (axis-indexed). ROS2 rejects numeric-only path tokens. Fix: set explicit `<topic>` in plugin config |
| Joint state bridge | Resolved | `SceneBroadcaster` does not publish per-model joint state topics. Must inject `gz-sim-joint-state-publisher-system` into URDF to get `/world/<w>/model/<m>/joint_state` data |

---

## How to Run (GhostMachine)

### Build
```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
rosdep install --from-paths src --ignore-src -r -y
pip install --break-system-packages opencv-python
colcon build --symlink-install
```

### Launch everything
```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

### Send a command (Phase 3 test)
```bash
source install/setup.bash
ros2 topic pub --once /task_input std_msgs/msg/String "data: 'move the red block onto the blue block'"
ros2 topic echo /task_command
```

### Check block positions (Phase 4 test)
```bash
source install/setup.bash
ros2 topic echo /object_poses
```

---

## How to Update This Document

After completing a phase or fixing a significant issue:

1. Update the **Phase Status** table
2. Update the **What's Built** file map
3. Update **Known Issues** if anything is resolved or newly discovered
4. Change **Last updated** and **Updated by**
5. Commit:

```bash
git add PROJECT_STATUS.md
git commit -m "docs: update PROJECT_STATUS — Phase X complete"
git push origin main
```

---

## Docs & Plans

| Document | Path |
|----------|------|
| System design spec | `docs/superpowers/specs/2026-04-10-langrobot-design.md` |
| Phase 3 spec | `docs/superpowers/specs/2026-04-11-phase3-lang-node-design.md` |
| Phase 4 spec | `docs/superpowers/specs/2026-04-11-phase4-perception-node-design.md` |
| Phase 3 plan | `docs/superpowers/plans/2026-04-11-phase3-lang-node.md` |
| Phase 4 plan | `docs/superpowers/plans/2026-04-11-phase4-perception-node.md` |
| Phase 3 verification | `docs/testing/phase3-verification-guide.md` |
| Phase 4 verification | `docs/testing/phase4-verification-guide.md` |
| Phase 3 test log | `logs/phase3-test-log.md` |
| Phase 4 test log | `logs/phase4-test-log.md` |
| Bootstrap script | `scripts/bootstrap.sh` |
| Franka fix script | `fix_franka.sh` |
