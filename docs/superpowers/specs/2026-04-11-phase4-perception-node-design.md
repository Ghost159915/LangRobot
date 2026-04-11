# Phase 4 — `perception_node` Design Spec
**Date:** 2026-04-11
**Status:** Approved

---

## Overview

`perception_node` is the vision layer for LangRobot. It consumes RGB and depth images from the Gazebo camera, detects the 5 coloured blocks using HSV colour segmentation, projects each detection to a 3D world coordinate using camera intrinsics and the known camera pose, and publishes the result as a JSON array on `/object_poses`.

**Phase 4 gate:** `ros2 topic echo /object_poses` shows a JSON array with correct 3D positions for all visible blocks.

---

## Architecture

Two files plus one test file — same pattern as `lang_node`:

```
src/langrobot/langrobot/
├── perception.py       ← pure Python: HSV detection, depth lookup, 3D projection
└── perception_node.py  ← ROS2 node: subscribe camera topics, call perception.py, publish JSON

tests/
└── test_perception.py  ← unit tests for perception.py (synthetic numpy arrays, no ROS2)
```

`perception.py` has zero ROS2 imports. Its public interface is one function:

```python
def detect_blocks(
    rgb: np.ndarray,       # HxWx3 uint8, BGR (OpenCV convention)
    depth: np.ndarray,     # HxW float32, metres
    camera_info: dict,     # {"fx": ..., "fy": ..., "cx": ..., "cy": ...}
) -> list[dict]:
    """
    Detect all 5 blocks in the image.
    Returns a list of 5 dicts, always one per colour, in fixed order:
    [red, blue, green, yellow, white]
    Each dict: {"colour": str, "x": float|None, "y": float|None, "z": float|None, "visible": bool}
    Never raises — failures produce visible=False entries.
    """
```

`perception_node.py` is a thin ROS2 wrapper (~60 lines): subscribe to `/camera/rgb_image`, `/camera/depth_image`, `/camera/camera_info`, cache latest depth + intrinsics, call `detect_blocks` on each RGB frame, publish JSON to `/object_poses`.

---

## ROS2 Topics

| Topic | Type | Direction |
|-------|------|-----------|
| `/camera/rgb_image` | `sensor_msgs/Image` | Gazebo → `perception_node` |
| `/camera/depth_image` | `sensor_msgs/Image` | Gazebo → `perception_node` |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | Gazebo → `perception_node` |
| `/object_poses` | `std_msgs/String` (JSON) | `perception_node` → `planner_node` (Phase 5) |

**Sync strategy:** cache-latest. The RGB callback processes whatever depth frame was most recently received. In Gazebo both sensors publish in lockstep at the same frequency so frames are always matched. `message_filters` synchronisation is deferred — add when moving to real hardware where sensor timing can drift.

---

## JSON Schema

### `/object_poses` — all 5 blocks always published

```json
[
  {"colour": "red",    "x": 0.32, "y":  0.10, "z": 0.43, "visible": true},
  {"colour": "blue",   "x": 0.41, "y": -0.05, "z": 0.43, "visible": true},
  {"colour": "green",  "x": null, "y":  null,  "z": null,  "visible": false},
  {"colour": "yellow", "x": 0.28, "y":  0.15,  "z": 0.43, "visible": true},
  {"colour": "white",  "x": null, "y":  null,  "z": null,  "visible": false}
]
```

| Field | Type | Notes |
|-------|------|-------|
| `colour` | string | Always one of `red`, `blue`, `green`, `yellow`, `white` |
| `x`, `y`, `z` | float or null | World-frame coordinates in metres. `null` when `visible` is false. |
| `visible` | bool | False when no contour found for that colour in this frame |

All 5 entries always present, in fixed order: red, blue, green, yellow, white.

---

## Detection Pipeline (`perception.py`)

For each RGB + depth frame pair:

1. **Convert to HSV** — `cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)`
2. **Mask per colour** — apply hardcoded HSV ranges (see table below); red requires two ranges (wraps around 0°)
3. **Find contour** — `cv2.findContours` on each mask; take the largest contour above a minimum area threshold (filters noise)
4. **Centroid** — `cv2.moments` → pixel `(u, v)`
5. **Depth lookup** — `depth[v, u]` in metres; if `0` or `NaN` → treat as not visible
6. **Back-project to camera frame** — using intrinsics `(fx, fy, cx, cy)`:
   ```
   X_cam = (u - cx) * depth / fx
   Y_cam = (v - cy) * depth / fy
   Z_cam = depth
   ```
7. **Transform to world frame** — camera is fixed at `(x=0.5, y=0, z=1.5)` pointing straight down (pitch=π/2). Rotation maps camera frame → world frame. World coordinates:
   ```
   x_world =  X_cam + 0.5
   y_world = -Y_cam
   z_world =  1.5 - Z_cam
   ```
8. **Pack result** — `{"colour": colour, "x": x_world, "y": y_world, "z": z_world, "visible": True}`
9. **If no contour / bad depth** — `{"colour": colour, "x": None, "y": None, "z": None, "visible": False}`

### HSV Colour Ranges (Gazebo simulation)

| Colour | H range | S range | V range | Notes |
|--------|---------|---------|---------|-------|
| Red | 0–10 + 170–180 | 100–255 | 100–255 | Two masks, OR'd together |
| Blue | 100–130 | 100–255 | 100–255 | |
| Green | 40–80 | 100–255 | 100–255 | |
| Yellow | 20–35 | 100–255 | 100–255 | |
| White | 0–180 | 0–30 | 200–255 | Low saturation, high value |

Ranges are tuned for Gazebo's rendered colours. If a colour is missed or mis-detected during integration testing, widen the corresponding range — no code restructure needed.

---

## Camera Intrinsics

Consumed from `/camera/camera_info` (cached on first message). Fields used:

```python
fx = camera_info_msg.k[0]   # focal length x
fy = camera_info_msg.k[4]   # focal length y
cx = camera_info_msg.k[2]   # principal point x
cy = camera_info_msg.k[5]   # principal point y
```

Cached as a dict `{"fx": fx, "fy": fy, "cx": cx, "cy": cy}` and reused for every frame (intrinsics don't change at runtime).

---

## Camera Pose (Fixed)

Camera SDF pose: `0.5 0 1.5 0 1.5708 0` (x, y, z, roll, pitch, yaw).

Pointing straight down (pitch = π/2). The world-frame transform is hardcoded — no TF2 lookup needed since the camera never moves. If the camera pose changes in `worlds/basic.sdf`, update the constants in `perception.py`.

---

## Error Handling

`detect_blocks` never raises. All failure modes produce `visible: False` for the affected block:

| Failure | Behaviour |
|---------|-----------|
| No contour found | `visible: False`, null coords |
| Depth = 0 or NaN at centroid | `visible: False`, null coords |
| OpenCV error on mask/contour | Caught, logged, `visible: False` |
| depth image not yet cached | Node skips frame, logs warning |
| camera_info not yet cached | Node skips frame, logs warning |

The node never crashes on bad frames.

---

## Testing

All tests in `tests/test_perception.py`. Use synthetic numpy arrays — no ROS2, no Gazebo, no camera hardware needed.

| Test | What it verifies |
|------|-----------------|
| `test_red_block_detected` | Solid-red synthetic image → `red` block found, `visible: True` |
| `test_unknown_colour_not_detected` | Image with no matching colour → all blocks `visible: False` |
| `test_depth_to_3d` | Known pixel + depth + intrinsics → correct world coordinate (within 1 cm) |
| `test_all_five_colours` | Image with all 5 colour patches → all 5 `visible: True` |
| `test_missing_block_returns_null` | One colour absent → that block `visible: False`, others normal |

---

## Phase 4 Verification Gate

**Unit tests (Mac — no Linux needed):**
```bash
PYTHONPATH=src/langrobot pytest tests/test_perception.py -v
```

**Integration test (Linux PC):**

Terminal 1:
```bash
source install/setup.bash
ros2 launch langrobot langrobot.launch.py
```

Terminal 2:
```bash
source install/setup.bash
ros2 topic echo /object_poses
```

**Expected output (updates at camera framerate):**
```
data: '[{"colour": "red", "x": 0.32, ...}, ...]'
```

**Pass criteria:**
1. All unit tests pass
2. `/object_poses` publishes a JSON array of 5 entries on every camera frame
3. Visible blocks have non-null x/y/z coordinates that match their approximate positions in Gazebo
4. Occluded or off-camera blocks have `visible: false` and null coordinates

---

## Decision Log

| Date | Decision | Reason | Deferred |
|------|----------|--------|---------|
| 2026-04-11 | HSV colour segmentation over YOLOv8 | Simulation blocks have clean solid colours; no training data needed; zero setup; reliable. YOLOv8 would require custom training (days of work) for no accuracy gain in sim. | YOLOv8 fine-tuning when moving to real hardware |
| 2026-04-11 | JSON on `std_msgs/String` over `geometry_msgs/PoseArray` | PoseArray has no names or visibility flags — planner must guess block order by convention. JSON carries colour name + `visible` flag explicitly; same pattern as `/task_command`; easy to extend with confidence/occlusion fields later. | Custom message type deferred — not needed yet |
| 2026-04-11 | Always publish all 5 blocks (visible + null) | Consistent message shape; planner always gets a full picture; `visible: false` is unambiguous vs stale position data | Last-known-position caching deferred; not needed for Phase 5 scope |
| 2026-04-11 | Cache-latest sync over `message_filters` | Gazebo publishes RGB and depth in lockstep — frames are always matched in sim; no complexity needed | `message_filters.ApproximateTimeSynchronizer` when moving to real hardware |
| 2026-04-11 | Hardcoded camera transform over TF2 lookup | Camera never moves in simulation; hardcoded is simpler and has no runtime dependency on TF tree | TF2 lookup when camera becomes dynamic or multiple cameras added |
