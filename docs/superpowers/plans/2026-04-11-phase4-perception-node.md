# Phase 4 — `perception_node` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `perception_node` — detects 5 coloured blocks from Gazebo camera images using HSV segmentation and publishes their 3D world positions as JSON on `/object_poses`.

**Architecture:** `perception.py` is pure Python (no ROS2) — it handles HSV masking, contour detection, depth lookup, and 3D back-projection. `perception_node.py` is a thin ROS2 wrapper that subscribes to `/camera/rgb_image`, `/camera/depth_image`, `/camera/camera_info`, calls `perception.py`, and publishes JSON. All detection logic is unit-testable without ROS2 or a camera.

**Tech Stack:** Python 3.12, OpenCV (`cv2`), NumPy, `cv_bridge`, ROS2 Jazzy, `pytest` + NumPy synthetic images.

---

## Environment context (read before starting)

- **Repo root = colcon workspace:** `~/Desktop/Projects/LangRobot/`
- **ROS2 package source:** `src/langrobot/langrobot/`
- **Run unit tests (Mac, no ROS2):** `PYTHONPATH=src/langrobot pytest tests/ -v`
- **Run unit tests (Linux):** same command after `source install/setup.bash`
- **Build command:** `colcon build --symlink-install`
- **Camera pose in SDF:** `0.5 0 1.5 0 1.5708 0` — position (x=0.5, y=0, z=1.5), pitch=π/2 (pointing straight down)
- **Block size:** 0.05m cubes sitting on table top at z≈0.425m
- **opencv-python** must be installed for Mac tests: `pip install opencv-python`

---

## File map

| Action | Path | Responsibility |
|--------|------|----------------|
| **Create** | `tests/test_perception.py` | Unit tests — synthetic numpy images, no ROS2 |
| **Create** | `src/langrobot/langrobot/perception.py` | HSV detection, depth lookup, 3D projection — pure Python |
| **Modify** | `requirements.txt` | Add `opencv-python>=4.8.0` |
| **Modify** | `src/langrobot/package.xml` | Add `cv_bridge` depend |
| **Create** | `src/langrobot/langrobot/perception_node.py` | ROS2 wrapper: camera topics → perception.py → `/object_poses` |
| **Modify** | `src/langrobot/setup.py` | Add `perception_node` console script entry point |
| **Modify** | `src/langrobot/launch/langrobot.launch.py` | Add `perception_node` to launch description |
| **Create** | `docs/testing/phase4-verification-guide.md` | Linux PC verification steps |
| **Create** | `logs/phase4-test-log.md` | Fillable test log template |

---

## Task 1: `perception.py` — core detection logic (TDD)

**Files:**
- Create: `tests/test_perception.py`
- Create: `src/langrobot/langrobot/perception.py`

- [ ] **Step 1: Install opencv-python on Mac (if not already installed)**

```bash
pip install opencv-python
python3 -c "import cv2; print(cv2.__version__)"
```

Expected: a version string like `4.9.0` (no error).

- [ ] **Step 2: Write all 5 failing tests**

Create `tests/test_perception.py` with this exact content:

```python
import numpy as np
import pytest

from langrobot.perception import detect_blocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _camera_info():
    """Typical pinhole intrinsics for a 640×480 image."""
    return {"fx": 554.0, "fy": 554.0, "cx": 320.0, "cy": 240.0}


def _solid_rgb(bgr_colour, h=480, w=640):
    """Synthetic image filled with a single BGR colour."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = bgr_colour
    return img


def _solid_depth(value=1.0, h=480, w=640):
    """Depth image where every pixel is `value` metres."""
    return np.full((h, w), value, dtype=np.float32)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_red_block_detected():
    """Solid red image → red block detected as visible."""
    rgb = _solid_rgb((0, 0, 200))        # BGR red
    depth = _solid_depth(1.0)
    result = detect_blocks(rgb, depth, _camera_info())
    red = next(b for b in result if b["colour"] == "red")
    assert red["visible"] is True
    assert red["x"] is not None
    assert red["y"] is not None
    assert red["z"] is not None


def test_unknown_colour_not_detected():
    """Purple image (not one of our 5 colours) → all blocks not visible."""
    rgb = _solid_rgb((128, 0, 128))      # BGR purple
    depth = _solid_depth(1.0)
    result = detect_blocks(rgb, depth, _camera_info())
    assert len(result) == 5
    assert all(b["visible"] is False for b in result)
    assert all(b["x"] is None for b in result)


def test_depth_to_3d():
    """
    Solid red image with centroid at centre pixel + depth=1.0m.
    Camera at (0.5, 0, 1.5) pointing straight down.
    Centre pixel → directly below camera → world (0.5, 0.0, 0.5).
    """
    rgb = _solid_rgb((0, 0, 200))        # BGR red — centroid lands at (320, 240)
    depth = _solid_depth(1.0)
    result = detect_blocks(rgb, depth, _camera_info())
    red = next(b for b in result if b["colour"] == "red")
    assert red["visible"] is True
    assert abs(red["x"] - 0.5) < 0.05   # within 5 cm
    assert abs(red["y"] - 0.0) < 0.05
    assert abs(red["z"] - 0.5) < 0.05


def test_all_five_colours():
    """Image with all 5 colour strips → all 5 blocks visible."""
    h, w = 480, 640
    img = np.zeros((h, w, 3), dtype=np.uint8)
    # Each colour occupies a horizontal strip (top 96 rows, 128 px wide)
    img[0:96, 0:128]   = (0,   0,   200)   # red
    img[0:96, 128:256] = (200, 0,   0  )   # blue
    img[0:96, 256:384] = (0,   200, 0  )   # green
    img[0:96, 384:512] = (0,   200, 200)   # yellow
    img[0:96, 512:640] = (220, 220, 220)   # white
    depth = _solid_depth(1.0)

    result = detect_blocks(img, depth, _camera_info())
    assert len(result) == 5
    visible = [b for b in result if b["visible"]]
    assert len(visible) == 5


def test_missing_block_returns_null():
    """Only red present → red visible, other 4 have visible=False and null coords."""
    rgb = _solid_rgb((0, 0, 200))        # BGR red only
    depth = _solid_depth(1.0)
    result = detect_blocks(rgb, depth, _camera_info())

    red = next(b for b in result if b["colour"] == "red")
    assert red["visible"] is True

    for colour in ["blue", "green", "yellow", "white"]:
        block = next(b for b in result if b["colour"] == colour)
        assert block["visible"] is False
        assert block["x"] is None
        assert block["y"] is None
        assert block["z"] is None
```

- [ ] **Step 3: Run tests — confirm they all fail**

```bash
cd ~/Desktop/Projects/LangRobot
PYTHONPATH=src/langrobot pytest tests/test_perception.py -v
```

Expected: `ModuleNotFoundError: No module named 'langrobot.perception'`. All 5 tests must error.

- [ ] **Step 4: Implement `perception.py`**

Create `src/langrobot/langrobot/perception.py` with this exact content:

```python
"""
perception.py — pure Python block detection via HSV colour segmentation.

No ROS2 imports. Public interface: detect_blocks(rgb, depth, camera_info) -> list[dict].
All failures return visible=False entries — never raises.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Camera world position (from worlds/basic.sdf pose: 0.5 0 1.5 0 1.5708 0)
CAMERA_X = 0.5
CAMERA_Y = 0.0
CAMERA_Z = 1.5

# Minimum contour area in pixels — filters out noise specks
MIN_CONTOUR_AREA = 100

# Fixed colour order: output list always has entries in this order
COLOURS = ["red", "blue", "green", "yellow", "white"]

# HSV ranges per colour. Each entry is (range1, range2).
# range2 is only used for red (hue wraps around 0°).
# Format: (np.array([H_lo, S_lo, V_lo]), np.array([H_hi, S_hi, V_hi]))
_HSV_RANGES = {
    "red":    ((np.array([0,   100, 100]), np.array([10,  255, 255])),
               (np.array([170, 100, 100]), np.array([180, 255, 255]))),
    "blue":   ((np.array([100, 100, 100]), np.array([130, 255, 255])), None),
    "green":  ((np.array([40,  100, 100]), np.array([80,  255, 255])), None),
    "yellow": ((np.array([20,  100, 100]), np.array([35,  255, 255])), None),
    "white":  ((np.array([0,   0,   200]), np.array([180, 30,  255])), None),
}


def _get_mask(hsv: np.ndarray, colour: str) -> np.ndarray:
    """Return binary mask for `colour` in the HSV image."""
    range1, range2 = _HSV_RANGES[colour]
    mask = cv2.inRange(hsv, range1[0], range1[1])
    if range2 is not None:
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, range2[0], range2[1]))
    return mask


def _find_centroid(mask: np.ndarray):
    """Return (u, v) centroid of the largest contour, or None if not found."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < MIN_CONTOUR_AREA:
        return None
    M = cv2.moments(largest)
    if M["m00"] == 0:
        return None
    u = int(M["m10"] / M["m00"])
    v = int(M["m01"] / M["m00"])
    return u, v


def _project_to_world(u: int, v: int, depth: float, camera_info: dict):
    """
    Back-project pixel (u, v) + depth to world-frame (x, y, z).

    Camera is fixed at (CAMERA_X, CAMERA_Y, CAMERA_Z) pointing straight down
    (pitch = π/2). Image +u → world +x. Image +v → world -y (flipped).
    Depth increases downward so world_z = CAMERA_Z - depth.
    """
    fx = camera_info["fx"]
    fy = camera_info["fy"]
    cx = camera_info["cx"]
    cy = camera_info["cy"]

    x_cam = (u - cx) * depth / fx
    y_cam = (v - cy) * depth / fy

    x_world = CAMERA_X + x_cam
    y_world = CAMERA_Y - y_cam   # image Y increases downward; world Y increases upward
    z_world = CAMERA_Z - depth

    return x_world, y_world, z_world


def detect_blocks(
    rgb: np.ndarray,
    depth: np.ndarray,
    camera_info: dict,
) -> list:
    """
    Detect all 5 coloured blocks in the image.

    Args:
        rgb:         HxWx3 uint8 array in BGR order (OpenCV convention).
        depth:       HxW float32 array, values in metres.
        camera_info: dict with keys fx, fy, cx, cy (pinhole intrinsics).

    Returns:
        List of 5 dicts, always one per colour, in fixed order
        [red, blue, green, yellow, white]:
          {"colour": str, "x": float|None, "y": float|None,
           "z": float|None, "visible": bool}
        Never raises — failures produce visible=False entries.
    """
    try:
        hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
    except Exception as exc:
        logger.error("HSV conversion failed: %s", exc)
        return [
            {"colour": c, "x": None, "y": None, "z": None, "visible": False}
            for c in COLOURS
        ]

    results = []
    for colour in COLOURS:
        entry = {"colour": colour, "x": None, "y": None, "z": None, "visible": False}
        try:
            mask = _get_mask(hsv, colour)
            centroid = _find_centroid(mask)
            if centroid is None:
                results.append(entry)
                continue

            u, v = centroid
            d = float(depth[v, u])
            if d == 0.0 or not np.isfinite(d):
                results.append(entry)
                continue

            x, y, z = _project_to_world(u, v, d, camera_info)
            entry = {
                "colour": colour,
                "x": round(x, 3),
                "y": round(y, 3),
                "z": round(z, 3),
                "visible": True,
            }
        except Exception as exc:
            logger.error("Detection failed for %s: %s", colour, exc)
        results.append(entry)

    return results
```

- [ ] **Step 5: Run tests — confirm all 5 pass**

```bash
PYTHONPATH=src/langrobot pytest tests/test_perception.py -v
```

Expected:
```
tests/test_perception.py::test_red_block_detected PASSED
tests/test_perception.py::test_unknown_colour_not_detected PASSED
tests/test_perception.py::test_depth_to_3d PASSED
tests/test_perception.py::test_all_five_colours PASSED
tests/test_perception.py::test_missing_block_returns_null PASSED

5 passed
```

Also confirm all existing tests still pass:

```bash
PYTHONPATH=src/langrobot pytest tests/ -v
```

Expected: **30 passed** (25 existing + 5 new).

- [ ] **Step 6: Commit**

```bash
git add src/langrobot/langrobot/perception.py tests/test_perception.py
git commit -m "feat: perception — HSV block detection and 3D projection"
```

---

## Task 2: Add dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `src/langrobot/package.xml`

- [ ] **Step 1: Add `opencv-python` to `requirements.txt`**

Current `requirements.txt`:
```
pytest==8.3.4
requests>=2.31.0
```

New `requirements.txt`:
```
pytest==8.3.4
requests>=2.31.0
opencv-python>=4.8.0
```

- [ ] **Step 2: Add `cv_bridge` to `package.xml`**

In `src/langrobot/package.xml`, add this line after the existing `<depend>sensor_msgs</depend>` line:

```xml
  <depend>cv_bridge</depend>
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt src/langrobot/package.xml
git commit -m "deps: add opencv-python and cv_bridge for perception_node"
```

---

## Task 3: `perception_node.py` — ROS2 wrapper

**Files:**
- Create: `src/langrobot/langrobot/perception_node.py`
- Modify: `src/langrobot/setup.py`

- [ ] **Step 1: Create `src/langrobot/langrobot/perception_node.py`**

```python
"""
perception_node.py — ROS2 node: camera topics → detect_blocks() → /object_poses.

Subscribes to /camera/rgb_image, /camera/depth_image, /camera/camera_info.
Publishes   to /object_poses (std_msgs/String, JSON array of 5 block dicts).
"""
import json

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String

from langrobot.perception import detect_blocks


class PerceptionNode(Node):
    def __init__(self):
        super().__init__('perception_node')
        self._bridge = CvBridge()
        self._latest_depth = None
        self._camera_info = None

        self.create_subscription(Image, '/camera/rgb_image', self._on_rgb, 10)
        self.create_subscription(Image, '/camera/depth_image', self._on_depth, 10)
        self.create_subscription(CameraInfo, '/camera/camera_info', self._on_camera_info, 10)
        self._pub = self.create_publisher(String, '/object_poses', 10)

        self.get_logger().info('perception_node ready — waiting for camera frames')

    def _on_camera_info(self, msg: CameraInfo) -> None:
        if self._camera_info is None:
            self._camera_info = {
                'fx': msg.k[0],
                'fy': msg.k[4],
                'cx': msg.k[2],
                'cy': msg.k[5],
            }
            self.get_logger().info(f'Camera intrinsics cached: {self._camera_info}')

    def _on_depth(self, msg: Image) -> None:
        try:
            self._latest_depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding='32FC1')
        except Exception as exc:
            self.get_logger().error(f'Depth conversion failed: {exc}')

    def _on_rgb(self, msg: Image) -> None:
        if self._latest_depth is None:
            self.get_logger().warning(
                'No depth frame yet — skipping', throttle_duration_sec=5.0
            )
            return
        if self._camera_info is None:
            self.get_logger().warning(
                'No camera_info yet — skipping', throttle_duration_sec=5.0
            )
            return

        try:
            rgb = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'RGB conversion failed: {exc}')
            return

        try:
            result = detect_blocks(rgb, self._latest_depth, self._camera_info)
        except Exception as exc:
            self.get_logger().error(f'detect_blocks raised: {exc}')
            return

        out = String()
        out.data = json.dumps(result)
        self._pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Add `perception_node` entry point to `setup.py`**

In `src/langrobot/setup.py`, the `console_scripts` list currently reads:

```python
        'console_scripts': [
            'controller_node = langrobot.controller_node:main',
            'lang_node = langrobot.lang_node:main',
        ],
```

Change it to:

```python
        'console_scripts': [
            'controller_node = langrobot.controller_node:main',
            'lang_node = langrobot.lang_node:main',
            'perception_node = langrobot.perception_node:main',
        ],
```

- [ ] **Step 3: Verify syntax**

```bash
cd src/langrobot
python3 -c "import ast; ast.parse(open('langrobot/perception_node.py').read()); print('perception_node OK')"
python3 -c "import ast; ast.parse(open('setup.py').read()); print('setup.py OK')"
```

Expected: both print OK.

- [ ] **Step 4: Run full test suite**

```bash
cd ~/Desktop/Projects/LangRobot
PYTHONPATH=src/langrobot pytest tests/ -v
```

Expected: **30 passed** (no regressions — `perception_node.py` has no testable pure-Python logic).

- [ ] **Step 5: Commit**

```bash
git add src/langrobot/langrobot/perception_node.py src/langrobot/setup.py
git commit -m "feat: perception_node ROS2 wrapper — camera topics → /object_poses"
```

---

## Task 4: Wire `perception_node` into the launch file

**Files:**
- Modify: `src/langrobot/launch/langrobot.launch.py`

- [ ] **Step 1: Add `perception_node` Node definition and add to LaunchDescription**

Read the current launch file. Find the `lang_node` definition and the `return LaunchDescription([...])` block.

Add this Node definition after `lang_node`:

```python
    perception_node = Node(
        package='langrobot',
        executable='perception_node',
        name='perception_node',
        output='screen',
    )
```

Then add `perception_node` to the LaunchDescription list:

```python
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        delayed_camera_bridge,
        delayed_spawn,
        controller_node,
        rviz_node,
        lang_node,
        perception_node,
    ])
```

Note: `perception_node` does NOT get `use_sim_time` — it processes camera frames in real time and does not use ROS2 simulation time.

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('src/langrobot/launch/langrobot.launch.py').read()); print('Syntax OK')"
```

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add src/langrobot/launch/langrobot.launch.py
git commit -m "feat: add perception_node to launch file"
```

---

## Task 5: Build verification + push

**Files:** none new — verify everything integrates.

- [ ] **Step 1: Run full unit test suite (Mac)**

```bash
cd ~/Desktop/Projects/LangRobot
PYTHONPATH=src/langrobot pytest tests/ -v
```

Expected: **30 passed**.

- [ ] **Step 2: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 3: Build on Linux PC (GhostMachine)**

```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
rosdep install --from-paths src --ignore-src -r -y
pip install --break-system-packages opencv-python
colcon build --symlink-install
```

Expected:
```
Summary: 2 packages finished [Xs]
```

If `cv_bridge` is missing:
```bash
sudo apt install ros-jazzy-cv-bridge
```

- [ ] **Step 4: Verify `perception_node` executable exists**

```bash
source install/setup.bash
ros2 pkg executables langrobot
```

Expected output includes:
```
langrobot controller_node
langrobot lang_node
langrobot perception_node
```

---

## Task 6: Phase 4 verification guide + test log

**Files:**
- Create: `docs/testing/phase4-verification-guide.md`
- Create: `logs/phase4-test-log.md`

- [ ] **Step 1: Create `docs/testing/phase4-verification-guide.md`**

```markdown
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

---

## Test 1 — Unit tests (30 tests)

```bash
PYTHONPATH=src/langrobot pytest tests/ -v
```

**What to look for:** All 30 tests pass including 5 new `test_perception.py` tests.

---

## Test 2 — Launch and verify perception_node starts

**Terminal 1:**
```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

**What to look for:**
```
[perception_node]: perception_node ready — waiting for camera frames
[perception_node]: Camera intrinsics cached: {'fx': ..., 'fy': ..., 'cx': ..., 'cy': ...}
```

---

## Test 3 — Check /object_poses output

**Terminal 2:**
```bash
source install/setup.bash
ros2 topic echo /object_poses
```

**What to look for:** JSON array of 5 dicts updating at camera framerate:
```
data: '[{"colour": "red", "x": 0.32, "y": 0.1, "z": 0.43, "visible": true}, ...]'
```

All 5 colours present. Visible blocks have non-null x/y/z. Any block out of camera view has `"visible": false`.

---

## Test 4 — Verify 3D positions roughly match Gazebo

Open Gazebo and note the approximate position of a block. Compare with the x/y/z values published on `/object_poses`.

Expected: positions within ~5 cm of actual block locations.

If positions are off (especially y-axis flipped), update `CAMERA_Y` sign or `_project_to_world` in `perception.py` and re-test. Note any corrections in the test log.

---

## Test 5 — Check active nodes

```bash
ros2 node list
```

**What to look for:**
```
/perception_node
/lang_node
/controller_node
/camera_bridge
/clock_bridge
/robot_state_publisher
/rviz2
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `cv_bridge` import error | `sudo apt install ros-jazzy-cv-bridge` |
| All blocks `visible: false` | Check camera topics are active: `ros2 topic list \| grep camera` |
| Wrong positions (y-axis flipped) | Flip sign of `y_world` in `perception.py:_project_to_world` |
| No output on `/object_poses` | Check `Camera intrinsics cached` appeared in Terminal 1 |

---

## Logging results

Fill in `logs/phase4-test-log.md`, then:

```bash
git add logs/phase4-test-log.md
git commit -m "test: Phase 4 verification results"
git push origin main
```
```

- [ ] **Step 2: Create `logs/phase4-test-log.md`**

```markdown
# Phase 4 Test Log

**Date:** <!-- e.g. 2026-04-15 -->
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04
**Branch/commit:** <!-- run: git log --oneline -1 -->

---

## Test Results

### Test 1 — Unit tests (30 tests)
- [ ] All 30 PASSED  [ ] Some FAILED

**Output (last 5 lines):**
```
<!-- paste here -->
```

---

### Test 2 — perception_node starts
- [ ] `perception_node ready` appears
- [ ] `Camera intrinsics cached` appears (with values)

**Intrinsics logged:**
```
<!-- paste here -->
```

---

### Test 3 — /object_poses output
- [ ] JSON array of 5 dicts updating at framerate
- [ ] Visible blocks have non-null coordinates

**Sample output:**
```
<!-- paste here -->
```

---

### Test 4 — Position accuracy
- [ ] Positions within ~5 cm of Gazebo block locations
- [ ] Any axis corrections needed: <!-- describe if any -->

---

### Test 5 — Active nodes
- [ ] `/perception_node` in `ros2 node list`

---

## Overall Phase 4 Result

- [ ] **PASSED**
- [ ] **PASSED WITH ISSUES** — see notes
- [ ] **FAILED**

**Issues:**
<!-- describe -->

---

## What to do next

```bash
git add logs/phase4-test-log.md
git commit -m "test: Phase 4 verification results"
git push origin main
```
```

- [ ] **Step 3: Commit and push**

```bash
git add docs/testing/phase4-verification-guide.md logs/phase4-test-log.md
git commit -m "docs: Phase 4 verification guide and test log template"
git push origin main
```

---

## Phase 4 gate

**PASS criteria (all required):**
1. All 30 unit tests pass
2. `perception_node ready` and `Camera intrinsics cached` appear in launch output
3. `/object_poses` publishes a JSON array of 5 entries at camera framerate
4. Visible blocks have non-null x/y/z coordinates within ~5 cm of actual Gazebo positions
5. `/perception_node` appears in `ros2 node list`

---

## Phase 5 preview

Phase 5 adds `planner_node`: subscribes to `/task_command` (from `lang_node`) and `/object_poses` (from `perception_node`), uses MoveIt2 to plan a collision-free trajectory, and publishes `/joint_trajectory`. Gate: arm picks a block and places it at the target location in Gazebo.
