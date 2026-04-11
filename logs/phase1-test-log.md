# Phase 1 Test Log: GhostMachine (Jazzy/Noble Edition)

**Date:** 2026-04-11  
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04.4 LTS  
**Branch/commit:** `main` / (Phase 1 Final Verification)

---

## 💻 Environment

| Item | Version / Status |
| :--- | :--- |
| **Ubuntu version** | Ubuntu 24.04.4 LTS (Noble Numbat) |
| **Kernel** | 6.8.0-generic |
| **ROS2 version** | Jazzy Jalisco |
| **Gazebo version** | Gazebo Sim (Ignition) |
| **ROCm version** | ROCm 6.x |
| **Ollama version** | 0.1.x |
| **GPU detected** | `gfx1101` (Forced to `11.0.1` via `HSA_OVERRIDE`) |

---

## 🛠 Pre-Start & Environment Deviations

### Pathing & Navigation
- **Issue:** The guide assumed `~/LangRobot`, but the project is at `~/Desktop/Projects/LangRobot`.
- **Fix:** Created a persistent alias `cdlang` in `.bashrc`.
- **Status:** PASS

### GPU Hardware Override
- **Issue:** `rocminfo` detected the GPU as `gfx1101`, but standard ROCm libraries often target `gfx1100`.
- **Fix:** Added `export HSA_OVERRIDE_GFX_VERSION=11.0.1` to `.bashrc` to ensure AI and rendering compatibility.
- **Status:** PASS

### Python Alias
- **Issue:** `python` command was missing (Ubuntu 24.04 only includes `python3` by default).
- **Fix:** Installed `python-is-python3` via apt.
- **Status:** PASS

---

## 🧪 Test Results

### Test 1 — ROS2 environment is working
- **Command Used:** `ros2 doctor`
- **Output:** Confirmed binary is active. Note: `ros2 --version` failed due to CLI changes in Jazzy.
- **Status:** PASS

### Test 2 — ROCm GPU is detected
- **Command Used:** `rocminfo | grep "Name:"`
- **Result:** Successfully detected **AMD Radeon RX 7700 XT (gfx1101)**.
- **Status:** PASS
- **Notes:** The RX 7700 XT requires the 11.0.1 override for ROCm stability. Environment persistence verified in .bashrc.

### Test 3 — Ollama is running and model is ready
- **Model Used:** `gemma4:latest` (User requested swap from Llama 3.2).
- **Inference Speed:** Near-instant (GPU accelerated via ROCm).
- **Status:** PASS
- **Notes:** Did inference test (ollama run gemma4 "Say hello in one word") respond?

[x] Yes, within a few seconds

[ ] Yes, but slowly (>30s) — GPU may not be active

[ ] No / error

### Test 4 & 5 — Colcon build & Unit tests
- **Issue:** `franka_description` was missing from the Jazzy apt repositories.
- **Action:** Source-built `franka_ros2` (jazzy branch) and the standalone `franka_description` repo.
- **Result:** 9/9 Unit tests passed in 0.01s.
- **Status:** PASS

---

## 🤖 Test 6 — Gazebo Launch (Major Troubleshooting)

This test required significant patching to work on the Jazzy/Noble environment.

### Problem 1: Legacy "Panda" Naming
The new description repository replaced "Panda" with "FR3."
- **Fix:** Created a `robots/panda` directory in `src` and symlinked `fr3.urdf.xacro` to `panda.urdf.xacro` and `franka_hand.urdf.xacro` to `hand.urdf.xacro`.

### Problem 2: Xacro Boolean Error
- **Error:** `evaluated to "ignition", which is not a boolean expression`.
- **Fix:** Patched `langrobot.launch.py` to change `gazebo:=ignition` to `gazebo:=true`.

### Problem 3: Jazzy YAML Parsing Crash
- **Error:** `Unable to parse parameter robot_description as yaml`.
- **Fix:** Modified the launch file to wrap the robot description in a `ParameterValue` object:
  `'robot_description': ParameterValue(robot_description, value_type=str)`

### Problem 4: Missing 3D Visuals
- **Error:** Terminal flooded with `Unable to find file with URI` for meshes.
- **Fix:** Added `GZ_SIM_RESOURCE_PATH` pointing to the workspace `install` folder in `.bashrc`.

**Final Test 6 Outcome:** Gazebo opened correctly, and the silver FR3 arm spawned in the world.
- **Status:** PASS

---

## 🕹 Test 7 & 8 — Joint Commands & Node List

### Joint Command Logic
- **Action:** Published a joint trajectory command to `/joint_trajectory`.
- **Terminal 1 Log:** `[controller_node]: Published joint command (7 joints): 0.500, -0.500, 0.300, -1.800, 0.100, 1.200, 0.500`.
- **Note:** Arm did not move in simulation due to Phase 1's lack of a hardware bridge, but logic was verified.

### Active Nodes
- **Command:** `ros2 node list`
- **Output:**
  - `/controller_node`
  - `/robot_state_publisher`
  - `/clock_bridge`
- **Status:** PASS

---

## 🛠 Critical Patches Applied
1. **Launch Fix:** Modified `langrobot.launch.py` to use `gazebo:=true` and `ParameterValue` for Jazzy compatibility.
2. **Path Fix:** Exported `GZ_SIM_RESOURCE_PATH` to resolve mesh loading errors.
3. **Hardware Alias:** Created `fix_franka.sh` to maintain Panda-to-FR3 symlinks within source-built description packages.
4. **Compatibility Script:** Created `fix_franka.sh` to automate the recreation of Panda-to-FR3 symlinks within the untracked source directories.

---

## 🏁 Overall Phase 1 Result
[x] PASSED WITH ISSUES — Successfully migrated to ROS 2 Jazzy.

[ ] PASSED — all tests passed, proceeding to Phase 2

Non-blocking observations:
Workspace has been converted to a Monorepo (embedded .git folders removed from src/franka_*) to ensure all Jazzy-specific hardware patches and symlinks are preserved in the main repository. GZ resource paths and GPU overrides are verified and persistent.

## 📝 Final Notes for Phase 2
The **GhostMachine** environment is now fully patched for ROS 2 Jazzy. All legacy "Panda" calls have been successfully aliased to the **FR3** hardware files.