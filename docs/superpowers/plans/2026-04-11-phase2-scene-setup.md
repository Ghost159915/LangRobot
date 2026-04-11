# Phase 2 — Scene Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a table, five coloured blocks, and an overhead RGB-D camera to the Gazebo world so that a live camera image showing the blocks is visible in RViz2.

**Architecture:** Scene geometry is defined once in `scene.py` as Python constants; unit tests verify geometric invariants (blocks on table, within reach, no overlap). The Gazebo world SDF adds static table/block models and an `rgbd_camera` sensor; `ros_gz_bridge` relays the camera image to ROS2; RViz2 is launched automatically with a preconfigured display.

**Tech Stack:** Gazebo Harmonic SDF 1.9, `gz-sim-sensors-system` (already enabled), `ros_gz_bridge`, `rviz2`, Python 3.12, pytest.

---

## Environment context (read before starting)

- **Repo root = colcon workspace:** `~/Desktop/Projects/LangRobot/`
- **Build command:** `cd ~/Desktop/Projects/LangRobot && colcon build --symlink-install`
- **Source command:** `source install/setup.bash`
- **Run tests:** `PYTHONPATH=src/langrobot python -m pytest tests/ -v`
- **Launch:** `ros2 launch langrobot langrobot.launch.py`
- The arm is sourced from `src/franka_description/` (not apt). Run `bash fix_franka.sh` if panda symlinks are missing after a fresh clone.
- The arm will appear **collapsed** in Gazebo — that is expected until Phase 5 (ros2_control). Focus on the table, blocks, and camera.

---

## File map

| Action | Path |
|--------|------|
| **Create** | `src/langrobot/langrobot/scene.py` |
| **Create** | `tests/test_scene.py` |
| **Modify** | `worlds/basic.sdf` |
| **Modify** | `src/langrobot/launch/langrobot.launch.py` |
| **Modify** | `src/langrobot/setup.py` |
| **Create** | `src/langrobot/config/rviz/phase2.rviz` |
| **Create** | `docs/testing/phase2-verification-guide.md` |
| **Create** | `logs/phase2-test-log.md` |

---

## Task 1: Scene geometry constants + unit tests

**Files:**
- Create: `src/langrobot/langrobot/scene.py`
- Create: `tests/test_scene.py`

### Scene geometry design (read this before writing any code)

```
Arm base at (0, 0, 0).
Table: solid box, top surface at z = 0.4 m, centred at x = 0.5 m in front of arm.
  SDF box centre: (0.5, 0.0, 0.2)  — because box extends ±0.2 m in z from centre
  SDF box size:   (0.5, 1.0, 0.4)  — 0.5 m deep × 1.0 m wide × 0.4 m tall
  Table top surface z = 0.2 + 0.2 = 0.4 m

Blocks: 5 cm solid cubes, resting on table top.
  Block centre z = TABLE_TOP_Z + 0.025 = 0.425 m
  Table x range: 0.25 – 0.75 m (centre 0.5 ± 0.25)
  Table y range: −0.5 – 0.5 m  (centre 0.0 ± 0.5)

Camera: overhead, looking straight down.
  Position: (0.5, 0.0, 1.5)
  SDF pose rotation: pitch = π/2 (1.5708 rad) — rotates +X optical axis to point −Z
```

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scene.py` with this exact content:

```python
import math

import pytest

from langrobot.scene import (
    ARM_REACH_M,
    BLOCK_POSITIONS,
    BLOCK_SIZE,
    CAMERA_POSE_XYZ,
    TABLE_POSE_XYZ,
    TABLE_SIZE_XYZ,
    TABLE_TOP_Z,
)


def test_table_top_height():
    expected = TABLE_POSE_XYZ[2] + TABLE_SIZE_XYZ[2] / 2
    assert TABLE_TOP_Z == pytest.approx(expected)


def test_table_within_arm_reach():
    # Nearest table edge to arm base must be strictly closer than max reach.
    nearest_x = TABLE_POSE_XYZ[0] - TABLE_SIZE_XYZ[0] / 2
    assert nearest_x < ARM_REACH_M


def test_all_blocks_on_table_surface():
    expected_z = TABLE_TOP_Z + BLOCK_SIZE / 2
    for name, (x, y, z) in BLOCK_POSITIONS.items():
        assert z == pytest.approx(expected_z), f"{name} block z incorrect"


def test_all_blocks_within_table_bounds():
    x_min = TABLE_POSE_XYZ[0] - TABLE_SIZE_XYZ[0] / 2
    x_max = TABLE_POSE_XYZ[0] + TABLE_SIZE_XYZ[0] / 2
    y_min = TABLE_POSE_XYZ[1] - TABLE_SIZE_XYZ[1] / 2
    y_max = TABLE_POSE_XYZ[1] + TABLE_SIZE_XYZ[1] / 2
    half = BLOCK_SIZE / 2
    for name, (x, y, z) in BLOCK_POSITIONS.items():
        assert x_min + half <= x <= x_max - half, f"{name} block x={x} out of table"
        assert y_min + half <= y <= y_max - half, f"{name} block y={y} out of table"


def test_five_blocks():
    assert len(BLOCK_POSITIONS) == 5


def test_block_names():
    assert set(BLOCK_POSITIONS.keys()) == {"red", "blue", "green", "yellow", "white"}


def test_camera_above_everything():
    assert CAMERA_POSE_XYZ[2] > TABLE_TOP_Z + BLOCK_SIZE


def test_blocks_no_overlap():
    names = list(BLOCK_POSITIONS.keys())
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            ax, ay, _ = BLOCK_POSITIONS[a]
            bx, by, _ = BLOCK_POSITIONS[b]
            dist = math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)
            assert dist >= BLOCK_SIZE, f"{a} and {b} blocks overlap (dist={dist:.3f})"
```

- [ ] **Step 2: Run tests — confirm they all fail**

```bash
cd ~/Desktop/Projects/LangRobot
PYTHONPATH=src/langrobot python -m pytest tests/test_scene.py -v
```

Expected: `ImportError: cannot import name 'ARM_REACH_M' from 'langrobot.scene'` (or `ModuleNotFoundError` if scene.py doesn't exist yet). All 8 tests must fail or error.

- [ ] **Step 3: Implement `scene.py`**

Create `src/langrobot/langrobot/scene.py` with this exact content:

```python
# Gazebo world geometry constants — single source of truth.
# Used by unit tests to verify layout invariants.
# Will also be imported by planner_node (Phase 5) for initial pose estimates.

# ── Arm ──────────────────────────────────────────────────────────────────────
ARM_REACH_M: float = 0.855  # Franka FR3 maximum reach from base centre (metres)

# ── Table ────────────────────────────────────────────────────────────────────
# SDF box is centred at TABLE_POSE_XYZ; its half-extents are TABLE_SIZE_XYZ / 2.
TABLE_POSE_XYZ: tuple[float, float, float] = (0.5, 0.0, 0.2)
TABLE_SIZE_XYZ: tuple[float, float, float] = (0.5, 1.0, 0.4)

# Top surface z-coordinate (derived — do not edit independently)
TABLE_TOP_Z: float = TABLE_POSE_XYZ[2] + TABLE_SIZE_XYZ[2] / 2  # 0.4 m

# ── Blocks ───────────────────────────────────────────────────────────────────
BLOCK_SIZE: float = 0.05  # 5 cm solid cubes

# Centre positions (x, y, z) — blocks rest on TABLE_TOP_Z surface.
_BLOCK_Z = TABLE_TOP_Z + BLOCK_SIZE / 2  # 0.425 m

BLOCK_POSITIONS: dict[str, tuple[float, float, float]] = {
    "red":    (0.45, -0.25, _BLOCK_Z),
    "blue":   (0.45,  0.25, _BLOCK_Z),
    "green":  (0.55, -0.15, _BLOCK_Z),
    "yellow": (0.55,  0.15, _BLOCK_Z),
    "white":  (0.60,  0.00, _BLOCK_Z),
}

# ── Camera ───────────────────────────────────────────────────────────────────
# Overhead position; SDF pose pitch = π/2 rotates +X optical axis to point −Z.
CAMERA_POSE_XYZ: tuple[float, float, float] = (0.5, 0.0, 1.5)
```

- [ ] **Step 4: Run tests — confirm all 8 pass**

```bash
PYTHONPATH=src/langrobot python -m pytest tests/test_scene.py -v
```

Expected output:
```
tests/test_scene.py::test_table_top_height PASSED
tests/test_scene.py::test_table_within_arm_reach PASSED
tests/test_scene.py::test_all_blocks_on_table_surface PASSED
tests/test_scene.py::test_all_blocks_within_table_bounds PASSED
tests/test_scene.py::test_five_blocks PASSED
tests/test_scene.py::test_block_names PASSED
tests/test_scene.py::test_camera_above_everything PASSED
tests/test_scene.py::test_blocks_no_overlap PASSED

8 passed in X.XXs
```

Also run the full test suite to confirm Phase 1 tests still pass:

```bash
PYTHONPATH=src/langrobot python -m pytest tests/ -v
```

Expected: all 17 tests pass (9 from Phase 1 + 8 new).

- [ ] **Step 5: Commit**

```bash
git add src/langrobot/langrobot/scene.py tests/test_scene.py
git commit -m "feat: scene geometry constants + 8 unit tests"
```

---

## Task 2: Gazebo world — table and five coloured blocks

**Files:**
- Modify: `worlds/basic.sdf`

Add the table and block models to the world. The geometry values must exactly match `scene.py` constants.

- [ ] **Step 1: Add table and block models to `worlds/basic.sdf`**

Open `worlds/basic.sdf`. Insert the following models immediately before the closing `</world>` tag (after the `ground_plane` model):

```xml
    <!-- ── Table ─────────────────────────────────────────────────────── -->
    <!-- Solid oak-coloured box. Centre at (0.5, 0, 0.2); top surface at z=0.4 m. -->
    <!-- Coordinates match scene.py: TABLE_POSE_XYZ=(0.5,0,0.2), TABLE_SIZE_XYZ=(0.5,1.0,0.4) -->
    <model name="table">
      <static>true</static>
      <pose>0.5 0 0.2 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>0.5 1.0 0.4</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>0.5 1.0 0.4</size></box></geometry>
          <material>
            <ambient>0.55 0.35 0.15 1</ambient>
            <diffuse>0.55 0.35 0.15 1</diffuse>
            <specular>0.08 0.08 0.08 1</specular>
          </material>
        </visual>
      </link>
    </model>

    <!-- ── Blocks (5 cm cubes, resting on table top at z=0.425) ─────── -->
    <!-- Coordinates match scene.py BLOCK_POSITIONS -->
    <model name="block_red">
      <static>true</static>
      <pose>0.45 -0.25 0.425 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
          <material>
            <ambient>0.9 0.1 0.1 1</ambient>
            <diffuse>0.9 0.1 0.1 1</diffuse>
            <specular>0.3 0.3 0.3 1</specular>
          </material>
        </visual>
      </link>
    </model>

    <model name="block_blue">
      <static>true</static>
      <pose>0.45 0.25 0.425 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
          <material>
            <ambient>0.1 0.1 0.9 1</ambient>
            <diffuse>0.1 0.1 0.9 1</diffuse>
            <specular>0.3 0.3 0.3 1</specular>
          </material>
        </visual>
      </link>
    </model>

    <model name="block_green">
      <static>true</static>
      <pose>0.55 -0.15 0.425 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
          <material>
            <ambient>0.1 0.8 0.1 1</ambient>
            <diffuse>0.1 0.8 0.1 1</diffuse>
            <specular>0.3 0.3 0.3 1</specular>
          </material>
        </visual>
      </link>
    </model>

    <model name="block_yellow">
      <static>true</static>
      <pose>0.55 0.15 0.425 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
          <material>
            <ambient>0.9 0.9 0.1 1</ambient>
            <diffuse>0.9 0.9 0.1 1</diffuse>
            <specular>0.3 0.3 0.3 1</specular>
          </material>
        </visual>
      </link>
    </model>

    <model name="block_white">
      <static>true</static>
      <pose>0.60 0.0 0.425 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>0.05 0.05 0.05</size></box></geometry>
          <material>
            <ambient>0.9 0.9 0.9 1</ambient>
            <diffuse>0.9 0.9 0.9 1</diffuse>
            <specular>0.5 0.5 0.5 1</specular>
          </material>
        </visual>
      </link>
    </model>
```

- [ ] **Step 2: Commit**

```bash
git add worlds/basic.sdf
git commit -m "feat: add table and five coloured blocks to Gazebo world"
```

---

## Task 3: Gazebo world — overhead RGB-D camera

**Files:**
- Modify: `worlds/basic.sdf`

Add a static camera model with an `rgbd_camera` sensor positioned above the table.

- [ ] **Step 1: Add camera model to `worlds/basic.sdf`**

Insert the following model immediately before the closing `</world>` tag (after the five block models added in Task 2):

```xml
    <!-- ── Overhead RGB-D camera ──────────────────────────────────────── -->
    <!-- Position matches scene.py: CAMERA_POSE_XYZ=(0.5, 0, 1.5)         -->
    <!-- Pitch = π/2 (1.5708) rotates the +X optical axis to point −Z      -->
    <!-- (straight down). The Sensors system plugin (already enabled in     -->
    <!-- this world) is required for the sensor to publish.                 -->
    <!--                                                                     -->
    <!-- rgbd_camera publishes to these Gazebo topics:                       -->
    <!--   /camera/image          — RGB (gz.msgs.Image)                      -->
    <!--   /camera/depth_image    — Depth (gz.msgs.Image)                    -->
    <!--   /camera/camera_info    — CameraInfo (gz.msgs.CameraInfo)          -->
    <!-- These are bridged to ROS2 in langrobot.launch.py.                   -->
    <model name="overhead_camera">
      <static>true</static>
      <pose>0.5 0 1.5 0 1.5708 0</pose>
      <link name="link">
        <sensor name="camera_sensor" type="rgbd_camera">
          <always_on>true</always_on>
          <update_rate>30</update_rate>
          <topic>camera</topic>
          <camera name="overhead">
            <horizontal_fov>1.047</horizontal_fov>
            <image>
              <width>640</width>
              <height>480</height>
              <format>R8G8B8</format>
            </image>
            <clip>
              <near>0.1</near>
              <far>10.0</far>
            </clip>
          </camera>
        </sensor>
      </link>
    </model>
```

- [ ] **Step 2: Commit**

```bash
git add worlds/basic.sdf
git commit -m "feat: add overhead rgbd_camera sensor to Gazebo world"
```

---

## Task 4: Camera bridge + RViz2 in launch file

**Files:**
- Modify: `src/langrobot/launch/langrobot.launch.py`
- Modify: `src/langrobot/setup.py`
- Create: `src/langrobot/config/rviz/phase2.rviz`

### 4a — RViz2 config file

- [ ] **Step 1: Create `src/langrobot/config/rviz/phase2.rviz`**

```yaml
Panels:
  - Class: rviz_common/Displays
    Name: Displays
  - Class: rviz_common/Selection
    Name: Selection
  - Class: rviz_common/Tool Properties
    Name: Tool Properties
  - Class: rviz_common/Views
    Name: Views
Visualization Manager:
  Class: ""
  Displays:
    - Class: rviz_default_plugins/Grid
      Enabled: true
      Name: Grid
      Value: true
    - Class: rviz_default_plugins/RobotModel
      Description Source: Topic
      Description Topic:
        Depth: 5
        Durability Policy: Volatile
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /robot_description
      Enabled: true
      Name: RobotModel
    - Class: rviz_default_plugins/Image
      Enabled: true
      Name: Camera
      Topic:
        Depth: 5
        Durability Policy: Volatile
        Filter size: 10
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: /camera/rgb_image
  Global Options:
    Background Color: 48; 48; 48
    Fixed Frame: world
    Frame Rate: 30
  Tools:
    - Class: rviz_default_plugins/Interact
      Hide Inactive Icons: false
    - Class: rviz_default_plugins/MoveCamera
    - Class: rviz_default_plugins/Select
  Value: true
  Views:
    Current:
      Class: rviz_default_plugins/Orbit
      Distance: 3
      Focal Point:
        X: 0.5
        Y: 0
        Z: 0.4
      Name: Current View
      Pitch: 0.7
      Target Frame: <Fixed Frame>
      Value: Orbit (rviz)
      Yaw: 3.14
    Saved: ~
Window Geometry:
  Height: 846
  Width: 1280
  X: 0
  Y: 27
```

### 4b — Update `setup.py`

- [ ] **Step 2: Update `src/langrobot/setup.py` — add rviz glob**

In `src/langrobot/setup.py`, the `data_files` list currently ends with:

```python
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
```

Change that line to these two lines:

```python
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'config', 'rviz'), glob('config/rviz/*.rviz')),
```

### 4c — Update launch file

- [ ] **Step 3: Update `src/langrobot/launch/langrobot.launch.py`**

Replace the entire file with this content:

```python
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('langrobot')

    try:
        franka_pkg = get_package_share_directory('franka_description')
    except Exception:
        raise RuntimeError(
            'franka_description package not found.\n'
            'Run: bash fix_franka.sh  then  colcon build --symlink-install\n'
            'See scripts/bootstrap.sh Step 4.'
        )

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    robot_description = Command([
        'xacro ',
        os.path.join(franka_pkg, 'robots', 'panda', 'panda.urdf.xacro'),
        ' hand:=true',
        ' gazebo:=true',
    ])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{
            # Explicitly cast Xacro output to string — prevents Jazzy YAML parser crash
            'robot_description': ParameterValue(robot_description, value_type=str),
            'use_sim_time': use_sim_time,
        }],
        output='screen',
    )

    gazebo = ExecuteProcess(
        cmd=[
            'gz', 'sim', '-r',
            os.path.join(pkg_share, 'worlds', 'basic.sdf'),
        ],
        output='screen',
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'panda',
            '-topic', '/robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.0',
        ],
        output='screen',
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )

    # Bridge camera topics from Gazebo → ROS2.
    # Gazebo rgbd_camera sensor with <topic>camera</topic> publishes:
    #   /camera/image          (gz.msgs.Image)
    #   /camera/depth_image    (gz.msgs.Image)
    #   /camera/camera_info    (gz.msgs.CameraInfo)
    # Remapping renames /camera/image → /camera/rgb_image to match the spec.
    camera_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='camera_bridge',
        arguments=[
            '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        remappings=[('/camera/image', '/camera/rgb_image')],
        output='screen',
    )

    controller_node = Node(
        package='langrobot',
        executable='controller_node',
        name='controller_node',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(pkg_share, 'config', 'rviz', 'phase2.rviz')],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    # Delay spawn 3 seconds to give Gazebo time to initialise
    delayed_spawn = TimerAction(period=3.0, actions=[spawn_robot])

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        camera_bridge,
        delayed_spawn,
        controller_node,
        rviz_node,
    ])
```

- [ ] **Step 4: Build and check for import errors**

```bash
cd ~/Desktop/Projects/LangRobot
colcon build --symlink-install 2>&1 | tail -20
```

Expected:
```
Summary: 2 packages finished [Xs]
```

No `failed` or `aborted`. If `franka_description` fails to build, run `bash fix_franka.sh` first.

- [ ] **Step 5: Commit**

```bash
git add src/langrobot/launch/langrobot.launch.py \
        src/langrobot/setup.py \
        src/langrobot/config/rviz/phase2.rviz
git commit -m "feat: camera bridge, RViz2 auto-launch, rviz config"
```

---

## Task 5: Phase 2 docs — verification guide + test log

**Files:**
- Create: `docs/testing/phase2-verification-guide.md`
- Create: `logs/phase2-test-log.md`

- [ ] **Step 1: Create `docs/testing/phase2-verification-guide.md`**

```markdown
# Phase 2 Verification Guide

How to verify Phase 2 (scene setup: table, blocks, camera) on the Linux PC.

**Gate:** Camera image with all five coloured blocks visible in RViz2.

---

## Before you start

```bash
cd ~/Desktop/Projects/LangRobot
git pull origin main
colcon build --symlink-install
source install/setup.bash
```

If `colcon build` fails with a franka error, run `bash fix_franka.sh` first.

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

RViz2 should open automatically when you launched in Test 2.

**What to look for in RViz2:**
- Left panel: `Camera` display enabled, subscribed to `/camera/rgb_image`
- A separate Image window (or panel) showing a live downward-looking view of the table
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
| `/camera/image` appears, not `/camera/rgb_image` | The bridge remapping didn't apply. Check `camera_bridge` node in launch file has `remappings=[('/camera/image', '/camera/rgb_image')]`. |
| No camera topics at all | Run `gz topic --list` in another terminal. If `/camera/image` appears there, the bridge is the issue. If not, the SDF sensor isn't publishing — check Sensors plugin is enabled. |
| RViz2 doesn't open | Check `rviz2` is installed: `ros2 run rviz2 rviz2`. If not: `sudo apt install ros-jazzy-rviz2`. |
| Table/blocks missing in Gazebo | `colcon build` may not have picked up the SDF change. Check `install/langrobot/share/langrobot/worlds/basic.sdf` contains the table model. |
| Camera image is black | ogre2 render engine may not have initialised. Wait 10s after Gazebo starts. If still black, try `export LIBGL_ALWAYS_SOFTWARE=1` before launch. |

---

## Logging results

Fill in `logs/phase2-test-log.md`, then:

```bash
git add logs/phase2-test-log.md logs/phase2-gazebo-screenshot.png logs/phase2-rviz-screenshot.png
git commit -m "test: Phase 2 verification results"
git push origin main
```
```

- [ ] **Step 2: Create `logs/phase2-test-log.md`**

```markdown
# Phase 2 Test Log

**Date:** <!-- e.g. 2026-04-15 -->
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04
**Branch/commit:** <!-- run: git log --oneline -1 -->

---

## Test Results

### Test 1 — Unit tests (17 tests)
- [ ] All 17 PASSED  [ ] Some FAILED

**Output of `pytest tests/ -v` (last 5 lines):**
```
<!-- paste here -->
```

---

### Test 2 — Gazebo: table and blocks visible
- [ ] Table visible (brown box)
- [ ] All 5 blocks visible (red, blue, green, yellow, white)
- [ ] Arm present (collapsed is OK)

**Gazebo screenshot:**
<!-- Save as logs/phase2-gazebo-screenshot.png -->

**Any errors in Terminal 1?**
```
<!-- paste here -->
```

---

### Test 3 — Camera topics in ROS2
- [ ] `/camera/rgb_image` present
- [ ] `/camera/depth_image` present
- [ ] `/camera/camera_info` present

**Output of `ros2 topic list | grep camera`:**
```
<!-- paste here -->
```

---

### Test 4 — Camera image in RViz2
- [ ] RViz2 opened automatically
- [ ] Camera panel shows a live image
- [ ] Blocks are visible in the image

**RViz2 screenshot:**
<!-- Save as logs/phase2-rviz-screenshot.png -->

---

### Test 5 — Active nodes
- [ ] PASS  [ ] FAIL

**Output of `ros2 node list`:**
```
<!-- paste here -->
```

---

## Overall Phase 2 Result

- [ ] **PASSED** — table, blocks, and camera image all visible
- [ ] **PASSED WITH ISSUES** — mostly working, see notes
- [ ] **FAILED** — blocked

**Blocking issues (if any):**
<!-- Describe the problem and paste the full error -->

**Non-blocking observations:**
<!-- Anything odd but not broken -->

---

## What to do next

```bash
git add logs/phase2-test-log.md
git add logs/phase2-gazebo-screenshot.png
git add logs/phase2-rviz-screenshot.png
git commit -m "test: Phase 2 verification results"
git push origin main
```
```

- [ ] **Step 3: Commit**

```bash
git add docs/testing/phase2-verification-guide.md logs/phase2-test-log.md
git commit -m "docs: Phase 2 verification guide and test log template"
```

---

## Phase 2 gate

**PASS criteria (all required):**
1. All 17 unit tests pass
2. Gazebo shows a brown table with 5 distinct coloured blocks
3. `ros2 topic list` shows `/camera/rgb_image`, `/camera/depth_image`, `/camera/camera_info`
4. RViz2 Image display shows a live downward view of the table with blocks visible

If any criterion fails, commit the log with the error and push — fixes will be issued before Phase 3.

---

## Phase 3 preview (for context, not implemented here)

Phase 3 adds `lang_node`: a Gemma 4 LLM node that receives an English command string on `/task_input` and publishes a structured JSON task spec to `/task_command`. Gate: `ros2 topic echo /task_command` shows valid JSON for any English input.
