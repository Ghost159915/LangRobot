# Phase 2 Verification Guide

How to verify Phase 2 (scene setup: table, blocks, camera) on the Linux PC.

**Gate:** Camera image with all five coloured blocks visible in RViz2.

---

## Before you start

```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

The `rosdep install` step installs any missing ROS packages automatically — run it every time after a `git pull` to avoid manual apt installs.

If `colcon build` fails with a franka error, run `bash fix_franka.sh` first, then repeat `colcon build --symlink-install`.

---

## Test 1 — Unit tests (17 tests)

```bash
PYTHONPATH=src/langrobot python -m pytest tests/ -v
```

**What to look for:** All 17 tests pass, including the 8 new `test_scene.py` tests.

---

## Test 2 — Launch and check Gazebo

**Terminal 1:**
```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

**What to look for in Gazebo:**
- Ground plane (grey)
- Brown rectangular table (0.5 m × 1.0 m × 0.4 m tall)
- Five small coloured cubes on the table (red, blue, green, yellow, white)
- The arm is still collapsed — this is expected until Phase 5

**Take a screenshot** of Gazebo showing the table and blocks. Save as `logs/phase2-gazebo-screenshot.png`.

---

## Test 3 — Camera topics appear in ROS2

**Terminal 2 (while Terminal 1 is running):**
```bash
source install/setup.bash
ros2 topic list | grep camera
```

**What to look for:**
```
/camera/camera_info
/camera/depth_image
/camera/rgb_image
```

All three must be present. If `/camera/image` appears instead of `/camera/rgb_image`, the bridge remapping did not apply — see troubleshooting below.

---

## Test 4 — Camera image visible in RViz2

RViz2 opens automatically when you launched in Test 2.

**What to look for in RViz2:**
- Left panel: `Camera` display enabled, subscribed to `/camera/rgb_image`
- A live downward-looking view of the table
- The five coloured blocks should be visible as distinct coloured squares

**Take a screenshot** of RViz2 showing the camera image with blocks. Save as `logs/phase2-rviz-screenshot.png`.

---

## Test 5 — Check active nodes

```bash
ros2 node list
```

**What to look for:**
```
/camera_bridge
/clock_bridge
/controller_node
/robot_state_publisher
/rviz2
```

All five nodes must appear.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `/camera/image` appears, not `/camera/rgb_image` | Bridge remapping didn't apply. Check `camera_bridge` node in launch file has `remappings=[('/camera/image', '/camera/rgb_image')]`. |
| No camera topics at all | Run `gz topic --list` in another terminal. If `/camera/image` appears there, the bridge is the issue. If not, the SDF sensor isn't publishing — check Sensors plugin is enabled in the SDF. |
| RViz2 doesn't open | Check rviz2 is installed: `ros2 run rviz2 rviz2`. If not: `sudo apt install ros-jazzy-rviz2`. |
| Table/blocks missing in Gazebo | `colcon build` may not have picked up the SDF change. Check `install/langrobot/share/langrobot/worlds/basic.sdf` contains the table model. |
| Camera image is black | ogre2 render engine may not have initialised. Wait 10 s after Gazebo starts. If still black, try `export LIBGL_ALWAYS_SOFTWARE=1` before launch. |
| Camera topics appear after ~3 s delay | This is expected — the bridge is delayed 3 s to give Gazebo time to start. |

---

## Logging results

Fill in `logs/phase2-test-log.md`, then:

```bash
git add logs/phase2-test-log.md logs/phase2-gazebo-screenshot.png logs/phase2-rviz-screenshot.png
git commit -m "test: Phase 2 verification results"
git push origin main
```
