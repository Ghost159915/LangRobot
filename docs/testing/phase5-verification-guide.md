# Phase 5 Verification Guide — planner_node Pick-and-Place

**Gate:** Arm physically picks up a block and places it on another block in Gazebo.

## Prerequisites

On GhostMachine:

```bash
sudo apt install ros-jazzy-moveit ros-jazzy-moveit-py
cd ~/Desktop/Projects/LangRobot
git pull origin main
colcon build --symlink-install
source install/setup.bash
```

## Step 1: Launch the Stack

```bash
ros2 launch langrobot langrobot.launch.py
```

Wait ~10 seconds for Gazebo, RViz2, and all nodes to start.

Verify these nodes are running:
```bash
ros2 node list
# Expected (among others):
#   /controller_node
#   /gripper_node
#   /joint_relay_node
#   /move_group
#   /perception_node
#   /planner_node
```

## Step 2: Verify Object Poses

```bash
ros2 topic echo /object_poses --once
```

Expected: JSON array with 5 blocks, at least `red` and `blue` showing `"visible": true`.

## Step 3: Send a Pick-and-Place Command

```bash
ros2 topic pub --once /task_command std_msgs/msg/String \
  "data: '{\"action\": \"pick_and_place\", \"object\": \"red\", \"target\": \"blue\"}'"
```

## Step 4: Observe in Gazebo (9 steps)

Watch the Franka arm in the Gazebo viewport:

| Step | What you should see |
|------|---------------------|
| 1 | Fingers open (gap widens) |
| 2 | Arm moves to 10 cm above red block |
| 3 | Arm descends to red block height |
| 4 | Fingers close around block |
| 5 | Arm lifts 15 cm with block |
| 6 | Arm translates to 10 cm above blue block |
| 7 | Arm descends to 5 cm above blue block |
| 8 | Fingers open (block drops onto blue) |
| 9 | Arm returns to home position |

## Step 5: Verify Block Moved

```bash
ros2 topic echo /object_poses --once
```

The red block should now appear near the blue block's XY coordinates, or `"visible": false` if it is stacked exactly on top.

## Step 6: Run Integration Test

```bash
source install/setup.bash
pytest tests/integration/test_pick_and_place.py -v -s
```

Expected: 1 PASS.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `move_group` not in node list | `sudo apt install ros-jazzy-moveit` and rebuild |
| Planning fails immediately | SRDF link names must match URDF — check `fr3_link0`, `fr3_hand` exist |
| Arm doesn't reach block | Verify block Z in `basic.sdf` matches `z + 0.425` expected in planner |
| Gripper doesn't close | Check `finger_command_bridge` is running: `ros2 topic list \| grep finger` |
| Block falls through table | Table `<static>` must remain `true` — only block models should be dynamic |
