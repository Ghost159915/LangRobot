# Phase 4 Verification Guide

How to verify Phase 4 (`perception_node`) on the Linux PC.

**Gate:** `ros2 topic echo /object_poses` shows a JSON array with correct 3D positions for all visible blocks.

---

## Before you start

```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
rosdep install --from-paths src --ignore-src -r -y
pip install --break-system-packages opencv-python
colcon build --symlink-install
source install/setup.bash
```

If `cv_bridge` is missing:
```bash
sudo apt install ros-jazzy-cv-bridge
```

---

## Test 1 — Unit tests (33 tests)

```bash
PYTHONPATH=src/langrobot pytest tests/ -v
```

**What to look for:** All 33 tests pass including 8 new `test_perception.py` tests.

---

## Test 2 — Launch and verify perception_node starts

**Terminal 1:**
```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

**What to look for in terminal output:**
```
[perception_node]: perception_node ready — waiting for camera frames
[perception_node]: Camera intrinsics cached: {'fx': ..., 'fy': ..., 'cx': ..., 'cy': ...}
```

The intrinsics line confirms the camera is publishing and the node received `camera_info`.

---

## Test 3 — Check /object_poses output

**Terminal 2:**
```bash
source install/setup.bash
ros2 topic echo /object_poses
```

**What to look for:** JSON array of 5 dicts updating at camera framerate:
```
data: '[{"colour": "red", "x": 0.32, "y": 0.1, "z": 0.43, "visible": true}, {"colour": "blue", ...}, ...]'
```

All 5 colours always present. Visible blocks have non-null x/y/z. Any block out of camera view has `"visible": false`.

---

## Test 4 — Verify 3D positions roughly match Gazebo

Open Gazebo and note the approximate position of a block (e.g. red block near the arm). Compare with the `x`/`y`/`z` values on `/object_poses`.

**Expected:** positions within ~5 cm of actual block locations in Gazebo.

**If y-axis is flipped:** negate `y_world` in `perception.py:_project_to_world`:
```python
y_world = CAMERA_Y + y_cam   # change minus to plus
```
Note the correction in `logs/phase4-test-log.md` and push.

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
/lang_node
/perception_node
/robot_state_publisher
/rviz2
```

`/perception_node` must appear.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `cv_bridge` import error on launch | `sudo apt install ros-jazzy-cv-bridge` |
| `Camera intrinsics cached` never appears | Camera bridge not started yet — wait 5 s after launch |
| All blocks `visible: false` | Run `ros2 topic list \| grep camera` — confirm `/camera/rgb_image` and `/camera/depth_image` are present |
| `/object_poses` not publishing | Check `ros2 topic hz /camera/rgb_image` — if 0 Hz, camera bridge has a problem |
| Wrong positions (y-axis flipped) | Flip sign of `y_world` in `perception.py:_project_to_world` as described above |

---

## Logging results

Fill in `logs/phase4-test-log.md`, then:

```bash
git add logs/phase4-test-log.md
git commit -m "test: Phase 4 verification results"
git push origin main
```
