# Phase 5 — `planner_node` Design Spec

**Date:** 2026-04-12  
**Status:** Approved  
**Gate:** Arm physically picks up a block and places it on another block in Gazebo

---

## Goal

Add `planner_node` — the component that bridges language understanding and arm execution. It receives a structured task command (which block to pick, where to place it), looks up block positions from the perception layer, and drives the Franka arm through a full pick-and-place sequence using MoveIt2 for motion planning.

---

## Architecture

```
/task_command ──► planner_node ◄── /object_poses
                      │
              MoveIt2 move_group
              (OMPL path planning, IK)
                      │
         FollowJointTrajectory action  ◄── controller_node (upgraded)
                      │
              joint_relay_node
                      │
              ros_gz_bridge
                      │
         JointPositionController × 7 (Gazebo)
                      │
                   ARM MOVES

planner_node ──► /gripper_action ──► gripper_node
                                          │
                                  fr3_finger_joint1/2
                                  JointPositionController
```

MoveIt2 is used for **planning only**. Execution flows through our existing custom pipeline (`joint_relay_node` → `ros_gz_bridge` → Gazebo `JointPositionController`), bypassing `ros2_control` hardware interface entirely to avoid the known ABI mismatch on GhostMachine.

---

## New Components

### `planner_node.py`

**Responsibility:** Orchestrate the 9-step pick-and-place sequence.

**Subscribes to:**
- `/task_command` (`std_msgs/String`, JSON) — `{"action": "pick_and_place", "object": "<colour>", "target": "<colour>"}`
- `/object_poses` (`std_msgs/String`, JSON array) — latest block positions from perception

**Behaviour:**
1. Caches latest `/object_poses` at all times.
2. On each `/task_command`:
   - Validates both object and target blocks are visible (`visible: true`). Logs error and aborts if either is missing.
   - Runs the pick-and-place sequence (see below).
   - Logs each step result.

**Pick-and-place sequence:**

| Step | Action | Detail |
|------|--------|--------|
| 1 | Open gripper | GripperCommand: position = 0.04 m |
| 2 | Pre-grasp | End-effector 10 cm above object block XY, pointing straight down |
| 3 | Grasp | End-effector at object block centre Z (0.425 m) |
| 4 | Close gripper | GripperCommand: position = 0.0 m |
| 5 | Lift | End-effector 15 cm above object block |
| 6 | Pre-place | End-effector 10 cm above target block XY |
| 7 | Place | End-effector at target block top Z + 5 cm (stack height) |
| 8 | Open gripper | GripperCommand: position = 0.04 m |
| 9 | Home | Retreat to Franka home joint configuration |

Each arm motion step: calls `move_group.plan()` then `move_group.execute()`. Uses `moveit_py` Python API. Aborts sequence on any planning or execution failure.

**Grasp orientation:** End-effector pointing straight down (roll=0, pitch=π, yaw=0) for all grasps. Works for all 5 blocks given the table layout and overhead camera position.

---

### `gripper_node.py`

**Responsibility:** Implement `control_msgs/action/GripperCommand` — translate open/close position commands into finger joint targets.

**Action server:** `/gripper_action` (`control_msgs/action/GripperCommand`)

**Behaviour:**
- `position = 0.04` → both finger joints set to 0.04 m (fully open, ~8 cm gap)
- `position = 0.0` → both finger joints set to 0.0 m (fully closed)
- Publishes to `/model/panda/joint/fr3_finger_joint1/cmd_pos` and `/fr3_finger_joint2/cmd_pos` via the same JointPositionController bridge pattern used for arm joints.
- Polls `/joint_states` until both finger joints are within 2 mm of target, then sends `succeeded`. Timeout: 3 seconds.

---

### `config/moveit/` (5 files)

| File | Purpose |
|------|---------|
| `panda.srdf` | Planning groups: `panda_arm` (fr3_joint1–7, EEF=fr3_hand), `hand` (fr3_finger_joint1–2) |
| `kinematics.yaml` | KDL IK solver for `panda_arm`, max 0.005 rad tolerance |
| `joint_limits.yaml` | Per-joint velocity and acceleration limits from FR3 spec |
| `moveit_controllers.yaml` | Maps `panda_arm` → `/follow_joint_trajectory` action, `hand` → `/gripper_action` action |
| `ompl_planning.yaml` | RRTConnect planner, 5 s planning timeout, 10 planning attempts |

---

## Upgraded Component

### `controller_node.py` — FollowJointTrajectory action server

**Change:** Implement `control_msgs/action/FollowJointTrajectory` action server at `/follow_joint_trajectory`.

**Behaviour:**
- Iterates through trajectory points in time order.
- For each point, publishes its positions to `/forward_position_controller/commands` (`Float64MultiArray`).
- Waits for the inter-point delay before publishing the next point.
- After the final point's `time_from_start` elapses, sends `result.error_code = SUCCESSFUL`.

**Backward compatibility:** Keeps the existing `/joint_trajectory` topic subscription so the integration tests (`test_arm_movement.py`) continue to pass without changes.

---

## Modified Components

### `worlds/basic.sdf`

Remove `<static>true</static>` from all 5 block models. Add to each:

```xml
<inertial>
  <mass>0.05</mass>
  <inertia>
    <ixx>2.083e-5</ixx><ixy>0</ixy><ixz>0</ixz>
    <iyy>2.083e-5</iyy><iyz>0</iyz>
    <izz>2.083e-5</izz>
  </inertia>
</inertial>
```

Surface friction on each block's collision:
```xml
<surface>
  <friction><ode><mu>1.5</mu><mu2>1.5</mu2></ode></friction>
</surface>
```

Table stays `<static>true</static>`.

---

### `launch/langrobot.launch.py`

Add:
1. Two `gz-sim-joint-position-controller-system` plugins for `fr3_finger_joint1` and `fr3_finger_joint2` in the URDF injection (same pattern as arm joints).
2. Two ROS→GZ bridge entries for finger joint cmd_pos topics.
3. `gripper_node` as a launched node.
4. `move_group` node with the MoveIt2 config files as parameters.

---

## Interface Summary

| Topic / Action | Type | Flow |
|---|---|---|
| `/task_command` | `std_msgs/String` (JSON) | `lang_node` → `planner_node` |
| `/object_poses` | `std_msgs/String` (JSON) | `perception_node` → `planner_node` |
| `/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` | `move_group` → `controller_node` |
| `/gripper_action` | `control_msgs/action/GripperCommand` | `planner_node` → `gripper_node` |
| `/model/panda/joint/fr3_finger_joint1/cmd_pos` | `std_msgs/Float64` | `gripper_node` → bridge → Gazebo |
| `/model/panda/joint/fr3_finger_joint2/cmd_pos` | `std_msgs/Float64` | `gripper_node` → bridge → Gazebo |

---

## Testing

### Unit tests (Mac, no ROS2)

**`tests/test_planner.py`**
- Pose computation: pre-grasp offset (+10 cm Z), grasp height (block centre Z), place height (target top + 5 cm)
- Sequence abort when object block not visible
- Sequence abort when target block not visible
- Gripper position mapping: open → 0.04, close → 0.0

**`tests/test_controller_action.py`**
- Points published in time order
- Correct inter-point timing
- `SUCCESSFUL` result returned after final point

### Integration test (GhostMachine)

**`tests/integration/test_pick_and_place.py`**
- Publish `/task_command` for a known block pair (e.g. red → blue)
- Assert arm reaches pre-grasp Z within tolerance
- Assert arm reaches grasp Z within tolerance
- Assert block moved from original XY (verified via `/object_poses` after execution)

### Verification guide

`docs/testing/phase5-verification-guide.md` — manual step-by-step: launch stack, send command, observe each of the 9 motion steps in Gazebo, confirm block is at target position.

---

## Install requirements (GhostMachine)

```bash
sudo apt install ros-jazzy-moveit ros-jazzy-moveit-py
```

No other new dependencies. All other packages (`control_msgs`, `trajectory_msgs`) are already present.
