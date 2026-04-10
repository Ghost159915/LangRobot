# Phase 1: Bootstrap + Gazebo + Franka Arm Moving

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the colcon workspace, install all system dependencies on the Linux PC via a one-time bootstrap script, spawn the Franka Panda arm in Gazebo Harmonic, and verify it moves in response to a ROS2 joint command.

**Architecture:** Standard ROS2 Jazzy colcon workspace at the repo root. A robot abstraction layer (`robots/base_robot.py` + `robots/franka.py`) defines the arm's config independently of any node logic. A minimal `controller_node` subscribes to `/joint_trajectory` and forwards commands to Gazebo via ros2_control. The launch file starts Gazebo, spawns the robot, and bridges topics.

**Tech Stack:** ROS2 Jazzy, Gazebo Harmonic, gz_ros2_control, franka_description, ros_gz_bridge, Python 3.12, pytest

**Phase:** 1 of 7 — subsequent phases are planned once this gate passes:  
`ros2 topic pub /joint_commands std_msgs/msg/Float64MultiArray` → Franka arm visibly moves in Gazebo

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `.gitignore` | Create | Exclude build artifacts and local dirs |
| `requirements.txt` | Create | Python deps (pytest for now; more added per phase) |
| `tests/__init__.py` | Create | Make tests a package |
| `tests/test_robot_abstraction.py` | Create | TDD — verify Franka implements base interface |
| `src/langrobot/langrobot/__init__.py` | Create | Python package marker |
| `src/langrobot/langrobot/robots/__init__.py` | Create | Package marker |
| `src/langrobot/langrobot/robots/base_robot.py` | Create | Abstract robot interface |
| `src/langrobot/langrobot/robots/franka.py` | Create | Franka Panda config |
| `src/langrobot/package.xml` | Create | ROS2 package manifest |
| `src/langrobot/setup.py` | Create | Python package install config |
| `src/langrobot/setup.cfg` | Create | Test and lint config |
| `src/langrobot/resource/langrobot` | Create | ROS2 resource marker |
| `src/langrobot/langrobot/controller_node.py` | Create | Receives JointTrajectory, sends to Gazebo |
| `src/langrobot/launch/langrobot.launch.py` | Create | Starts Gazebo + spawns Franka + bridges topics |
| `worlds/basic.sdf` | Create | Minimal Gazebo world (ground + light; no blocks yet) |
| `scripts/bootstrap.sh` | Create | One-time install: ROS2 Jazzy, Gazebo Harmonic, ROCm, Ollama |

---

## Task 1: Repository scaffold — .gitignore and requirements.txt

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create .gitignore**

```
# ROS2 colcon build artifacts
build/
install/
log/

# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
*.pt

# Project-local
.superpowers/
models/
.env
```

Save to `.gitignore` at repo root.

- [ ] **Step 2: Create requirements.txt**

```
pytest==8.3.4
```

Save to `requirements.txt` at repo root. Additional deps (langchain, ultralytics, etc.) are added in their respective phases.

- [ ] **Step 3: Create tests/__init__.py**

```python
```

Empty file — makes `tests/` a Python package so pytest discovers it correctly.

- [ ] **Step 4: Commit**

```bash
git add .gitignore requirements.txt tests/__init__.py
git commit -m "chore: initial scaffold — gitignore, requirements, tests package"
```

---

## Task 2: Robot abstraction layer

**Files:**
- Create: `src/langrobot/langrobot/robots/__init__.py`
- Create: `src/langrobot/langrobot/robots/base_robot.py`
- Create: `src/langrobot/langrobot/robots/franka.py`
- Test: `tests/test_robot_abstraction.py`

- [ ] **Step 1: Write the failing tests**

Save to `tests/test_robot_abstraction.py`:

```python
import math
import pytest
from langrobot.robots.base_robot import BaseRobot, RobotConfig
from langrobot.robots.franka import FrankaRobot


def test_franka_implements_base_robot():
    robot = FrankaRobot()
    assert isinstance(robot, BaseRobot)


def test_franka_config_is_robot_config_instance():
    robot = FrankaRobot()
    assert isinstance(robot.config, RobotConfig)


def test_franka_has_seven_joints():
    robot = FrankaRobot()
    assert len(robot.joint_names) == 7


def test_franka_joint_names_are_panda_joints():
    robot = FrankaRobot()
    for name in robot.joint_names:
        assert name.startswith('panda_joint'), f"Unexpected joint name: {name}"


def test_franka_end_effector_link():
    robot = FrankaRobot()
    assert robot.end_effector_link == 'panda_hand'


def test_franka_planning_group():
    robot = FrankaRobot()
    assert robot.planning_group == 'panda_arm'


def test_franka_home_position_length_matches_joint_count():
    robot = FrankaRobot()
    assert len(robot.home_joint_positions) == len(robot.joint_names)


def test_franka_home_positions_are_floats():
    robot = FrankaRobot()
    for pos in robot.home_joint_positions:
        assert isinstance(pos, float), f"Expected float, got {type(pos)}"


def test_franka_gripper_open_close_lengths_match():
    robot = FrankaRobot()
    assert len(robot.config.gripper_open_values) == len(robot.config.gripper_joint_names)
    assert len(robot.config.gripper_close_values) == len(robot.config.gripper_joint_names)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /path/to/LangRobot
python -m pytest tests/test_robot_abstraction.py -v
```

Expected: `ModuleNotFoundError: No module named 'langrobot'` — correct, the package doesn't exist yet.

- [ ] **Step 3: Create `src/langrobot/langrobot/robots/__init__.py`**

```python
```

Empty file.

- [ ] **Step 4: Create `src/langrobot/langrobot/robots/base_robot.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class RobotConfig:
    joint_names: List[str]
    end_effector_link: str
    planning_group: str
    gripper_joint_names: List[str]
    gripper_open_values: List[float]
    gripper_close_values: List[float]
    home_joint_positions: List[float]


class BaseRobot(ABC):
    @property
    @abstractmethod
    def config(self) -> RobotConfig:
        """Return the robot's configuration."""
        ...

    @property
    def joint_names(self) -> List[str]:
        return self.config.joint_names

    @property
    def end_effector_link(self) -> str:
        return self.config.end_effector_link

    @property
    def planning_group(self) -> str:
        return self.config.planning_group

    @property
    def home_joint_positions(self) -> List[float]:
        return self.config.home_joint_positions
```

- [ ] **Step 5: Create `src/langrobot/langrobot/robots/franka.py`**

```python
import math
from langrobot.robots.base_robot import BaseRobot, RobotConfig


class FrankaRobot(BaseRobot):
    """Franka Panda (FR3) robot configuration."""

    @property
    def config(self) -> RobotConfig:
        return RobotConfig(
            joint_names=[
                'panda_joint1',
                'panda_joint2',
                'panda_joint3',
                'panda_joint4',
                'panda_joint5',
                'panda_joint6',
                'panda_joint7',
            ],
            end_effector_link='panda_hand',
            planning_group='panda_arm',
            gripper_joint_names=[
                'panda_finger_joint1',
                'panda_finger_joint2',
            ],
            gripper_open_values=[0.04, 0.04],
            gripper_close_values=[0.0, 0.0],
            # Safe home pose: arm slightly raised, elbow bent, wrist neutral
            home_joint_positions=[
                0.0,
                -math.pi / 4,
                0.0,
                -3 * math.pi / 4,
                0.0,
                math.pi / 2,
                math.pi / 4,
            ],
        )
```

- [ ] **Step 6: Run tests from src/ so Python can find the package**

```bash
cd /path/to/LangRobot
PYTHONPATH=src/langrobot python -m pytest tests/test_robot_abstraction.py -v
```

Expected output:
```
tests/test_robot_abstraction.py::test_franka_implements_base_robot PASSED
tests/test_robot_abstraction.py::test_franka_config_is_robot_config_instance PASSED
tests/test_robot_abstraction.py::test_franka_has_seven_joints PASSED
tests/test_robot_abstraction.py::test_franka_joint_names_are_panda_joints PASSED
tests/test_robot_abstraction.py::test_franka_end_effector_link PASSED
tests/test_robot_abstraction.py::test_franka_planning_group PASSED
tests/test_robot_abstraction.py::test_franka_home_position_length_matches_joint_count PASSED
tests/test_robot_abstraction.py::test_franka_home_positions_are_floats PASSED
tests/test_robot_abstraction.py::test_franka_gripper_open_close_lengths_match PASSED
9 passed in 0.XXs
```

If any test fails, fix the implementation before continuing.

- [ ] **Step 7: Commit**

```bash
git add tests/test_robot_abstraction.py \
        src/langrobot/langrobot/robots/__init__.py \
        src/langrobot/langrobot/robots/base_robot.py \
        src/langrobot/langrobot/robots/franka.py
git commit -m "feat: robot abstraction layer — BaseRobot interface and Franka config"
```

---

## Task 3: ROS2 package boilerplate

**Files:**
- Create: `src/langrobot/langrobot/__init__.py`
- Create: `src/langrobot/package.xml`
- Create: `src/langrobot/setup.py`
- Create: `src/langrobot/setup.cfg`
- Create: `src/langrobot/resource/langrobot`

- [ ] **Step 1: Create `src/langrobot/langrobot/__init__.py`**

```python
```

Empty file.

- [ ] **Step 2: Create `src/langrobot/package.xml`**

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>langrobot</name>
  <version>0.1.0</version>
  <description>Language-driven robot manipulation system</description>
  <maintainer email="benas@example.com">Benas Vaiciulis</maintainer>
  <license>MIT</license>

  <buildtool_depend>ament_python</buildtool_depend>

  <depend>rclpy</depend>
  <depend>std_msgs</depend>
  <depend>geometry_msgs</depend>
  <depend>sensor_msgs</depend>
  <depend>trajectory_msgs</depend>
  <depend>ros_gz_sim</depend>
  <depend>ros_gz_bridge</depend>

  <test_depend>ament_copyright</test_depend>
  <test_depend>ament_flake8</test_depend>
  <test_depend>ament_pep257</test_depend>
  <test_depend>python3-pytest</test_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

- [ ] **Step 3: Create `src/langrobot/setup.py`**

```python
from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'langrobot'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'worlds'), glob('../../worlds/*.sdf')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Benas Vaiciulis',
    maintainer_email='benas@example.com',
    description='Language-driven robot manipulation system',
    license='MIT',
    entry_points={
        'console_scripts': [
            'controller_node = langrobot.controller_node:main',
        ],
    },
)
```

- [ ] **Step 4: Create `src/langrobot/setup.cfg`**

```ini
[develop]
script_dir=$base/lib/langrobot

[install]
install_scripts=$base/lib/langrobot
```

- [ ] **Step 5: Create resource marker**

```bash
mkdir -p src/langrobot/resource
touch src/langrobot/resource/langrobot
```

- [ ] **Step 6: Create config and launch directories**

```bash
mkdir -p src/langrobot/config
mkdir -p src/langrobot/launch
```

- [ ] **Step 7: Commit**

```bash
git add src/langrobot/
git commit -m "chore: ROS2 package boilerplate — package.xml, setup.py, setup.cfg"
```

---

## Task 4: Controller node

**Files:**
- Create: `src/langrobot/langrobot/controller_node.py`

This is the only node needed for Phase 1. It receives a `JointTrajectory` message and forwards the joint positions to Gazebo. The other four nodes (lang, perception, planner, feedback) are added in their respective phases.

- [ ] **Step 1: Create `src/langrobot/langrobot/controller_node.py`**

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from trajectory_msgs.msg import JointTrajectory

from langrobot.robots.franka import FrankaRobot


class ControllerNode(Node):
    def __init__(self):
        super().__init__('controller_node')
        self._robot = FrankaRobot()

        self._trajectory_sub = self.create_subscription(
            JointTrajectory,
            '/joint_trajectory',
            self._trajectory_callback,
            10,
        )

        self._joint_commands_pub = self.create_publisher(
            Float64MultiArray,
            '/joint_commands',
            10,
        )

        self.get_logger().info(
            f'Controller node started for {self._robot.__class__.__name__}'
        )
        self.get_logger().info(
            f'Joints: {self._robot.joint_names}'
        )

    def _trajectory_callback(self, msg: JointTrajectory) -> None:
        if not msg.points:
            self.get_logger().warn('Received empty JointTrajectory — ignoring')
            return

        # Forward the final point of the trajectory as the target position
        final_point = msg.points[-1]
        cmd = Float64MultiArray()
        cmd.data = list(final_point.positions)
        self._joint_commands_pub.publish(cmd)
        self.get_logger().info(
            f'Published joint command ({len(cmd.data)} joints): '
            + ', '.join(f'{v:.3f}' for v in cmd.data)
        )


def main(args=None):
    rclpy.init(args=args)
    node = ControllerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/langrobot/langrobot/controller_node.py
git commit -m "feat: controller_node skeleton — receives JointTrajectory, publishes joint commands"
```

---

## Task 5: Gazebo world file

**Files:**
- Create: `worlds/basic.sdf`

Phase 1 world is minimal — ground plane and lighting only. Table and blocks are added in Phase 2.

- [ ] **Step 1: Create `worlds/basic.sdf`**

```xml
<?xml version="1.0" ?>
<sdf version="1.9">
  <world name="langrobot_basic">

    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <plugin
      filename="gz-sim-physics-system"
      name="gz::sim::systems::Physics"/>
    <plugin
      filename="gz-sim-sensors-system"
      name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin
      filename="gz-sim-scene-broadcaster-system"
      name="gz::sim::systems::SceneBroadcaster"/>
    <plugin
      filename="gz-sim-user-commands-system"
      name="gz::sim::systems::UserCommands"/>

    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <plane><normal>0 0 1</normal><size>10 10</size></plane>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <plane><normal>0 0 1</normal><size>10 10</size></plane>
          </geometry>
          <material>
            <ambient>0.6 0.6 0.6 1</ambient>
            <diffuse>0.6 0.6 0.6 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

  </world>
</sdf>
```

- [ ] **Step 2: Commit**

```bash
git add worlds/basic.sdf
git commit -m "feat: basic Gazebo world — ground plane and lighting"
```

---

## Task 6: Launch file

**Files:**
- Create: `src/langrobot/launch/langrobot.launch.py`

This launch file starts Gazebo Harmonic, spawns the Franka Panda, bridges the clock topic, and starts the controller node.

**Note on franka_description:** The `franka_description` package provides the URDF/xacro. On Ubuntu 24.04 with ROS2 Jazzy, install it with:
```bash
sudo apt install ros-jazzy-franka-description
```
If that package is not yet in the Jazzy apt repo, clone and build it from source (see bootstrap.sh in Task 7).

- [ ] **Step 1: Create `src/langrobot/launch/langrobot.launch.py`**

```python
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('langrobot')

    # Try to find franka_description; fail early with a clear message if missing
    try:
        franka_pkg = get_package_share_directory('franka_description')
    except Exception:
        raise RuntimeError(
            'franka_description package not found. '
            'Run: sudo apt install ros-jazzy-franka-description  '
            'or build from source — see scripts/bootstrap.sh'
        )

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Build robot description from xacro
    robot_description = Command([
        'xacro ',
        os.path.join(franka_pkg, 'robots', 'panda', 'panda.urdf.xacro'),
        ' hand:=true',
        ' gazebo:=ignition',
    ])

    # Publish robot state (joint positions → TF transforms)
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
        output='screen',
    )

    # Start Gazebo Harmonic with the basic world
    gazebo = ExecuteProcess(
        cmd=[
            'gz', 'sim', '-r',
            os.path.join(pkg_share, 'worlds', 'basic.sdf'),
        ],
        output='screen',
    )

    # Spawn Franka Panda from robot_description topic
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

    # Bridge Gazebo clock → ROS2 clock (required for use_sim_time)
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )

    # Controller node (receives /joint_trajectory, publishes /joint_commands)
    controller_node = Node(
        package='langrobot',
        executable='controller_node',
        name='controller_node',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    # Delay spawn until Gazebo is ready (~3 seconds)
    delayed_spawn = TimerAction(period=3.0, actions=[spawn_robot])

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        delayed_spawn,
        controller_node,
    ])
```

- [ ] **Step 2: Commit**

```bash
git add src/langrobot/launch/langrobot.launch.py
git commit -m "feat: launch file — Gazebo Harmonic + Franka spawn + controller node"
```

---

## Task 7: Bootstrap script

**Files:**
- Create: `scripts/bootstrap.sh`

**Run this ONCE on the Linux PC. Never run again.**

- [ ] **Step 1: Create `scripts/bootstrap.sh`**

```bash
#!/usr/bin/env bash
# LangRobot bootstrap — run ONCE on a fresh Ubuntu 24.04 machine.
# After this script completes, the daily workflow is just:
#   git pull && colcon build && ros2 launch langrobot langrobot.launch.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "LangRobot Bootstrap — Ubuntu 24.04 + ROS2 Jazzy"
echo "============================================================"

# ── Step 1: System update ─────────────────────────────────────────
echo ""
echo "Step 1/9: System update + base deps"
sudo apt-get update -y
sudo apt-get install -y \
    curl \
    git \
    build-essential \
    wget \
    software-properties-common \
    apt-transport-https \
    gnupg \
    lsb-release

# ── Step 2: ROS2 Jazzy ───────────────────────────────────────────
echo ""
echo "Step 2/9: ROS2 Jazzy"
if ! dpkg -l ros-jazzy-desktop &>/dev/null; then
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
        http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
        | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y \
        ros-jazzy-desktop \
        ros-jazzy-ros2-control \
        ros-jazzy-ros2-controllers \
        ros-jazzy-moveit \
        ros-jazzy-xacro \
        ros-jazzy-robot-state-publisher \
        ros-jazzy-joint-state-publisher \
        python3-rosdep \
        python3-colcon-common-extensions
    echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
else
    echo "  ROS2 Jazzy already installed — skipping"
fi

# ── Step 3: Gazebo Harmonic + ros-gz bridge ───────────────────────
echo ""
echo "Step 3/9: Gazebo Harmonic + ros-gz"
if ! command -v gz &>/dev/null; then
    sudo curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
        -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
        http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
        | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y gz-harmonic
    sudo apt-get install -y \
        ros-jazzy-ros-gz \
        ros-jazzy-ros-gz-sim \
        ros-jazzy-ros-gz-bridge \
        ros-jazzy-ros-gz-interfaces
else
    echo "  Gazebo already installed — skipping"
fi

# ── Step 4: Franka description ────────────────────────────────────
echo ""
echo "Step 4/9: Franka ROS2 packages"
# Try apt first; fall back to source build if not yet in Jazzy repo
if apt-cache show ros-jazzy-franka-description &>/dev/null; then
    sudo apt-get install -y ros-jazzy-franka-description
else
    echo "  franka_description not in apt — building from source"
    FRANKA_WS="$HOME/franka_ws"
    mkdir -p "$FRANKA_WS/src"
    cd "$FRANKA_WS/src"
    if [ ! -d franka_description ]; then
        git clone https://github.com/frankaemika/franka_description.git -b main
    fi
    cd "$FRANKA_WS"
    source /opt/ros/jazzy/setup.bash
    colcon build --symlink-install
    echo "source $FRANKA_WS/install/setup.bash" >> ~/.bashrc
fi

# ── Step 5: ROCm 6.x (AMD GPU) ───────────────────────────────────
echo ""
echo "Step 5/9: ROCm 6.x for AMD RX 7700 XT"
if ! command -v rocminfo &>/dev/null; then
    # Download AMD GPU installer
    ROCM_DEB="amdgpu-install_6.3.3.60303-1_all.deb"
    ROCM_URL="https://repo.radeon.com/amdgpu-install/6.3.3/ubuntu/noble/$ROCM_DEB"
    wget -q "$ROCM_URL" -O "/tmp/$ROCM_DEB"
    sudo apt-get install -y "/tmp/$ROCM_DEB"
    sudo amdgpu-install --usecase=rocm --no-dkms -y
    sudo usermod -a -G render,video "$USER"
    echo ""
    echo "  ⚠  ROCm installed. You MUST log out and back in (or reboot)"
    echo "  before GPU acceleration will work. The bootstrap will continue,"
    echo "  but run 'rocminfo' after relogin to confirm GPU is detected."
    rm "/tmp/$ROCM_DEB"
else
    echo "  ROCm already installed — skipping"
fi

# ── Step 6: Ollama + Llama 3.2 ───────────────────────────────────
echo ""
echo "Step 6/9: Ollama + Llama 3.2"
if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi
# Pull model (Ollama auto-detects ROCm for AMD GPU)
ollama pull llama3.2

# ── Step 7: Python deps ───────────────────────────────────────────
echo ""
echo "Step 7/9: Python dependencies"
pip install -r "$REPO_ROOT/requirements.txt"

# ── Step 8: rosdep + colcon build ────────────────────────────────
echo ""
echo "Step 8/9: rosdep install + colcon build"
source /opt/ros/jazzy/setup.bash
cd "$REPO_ROOT"
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo rosdep init
fi
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
echo "source $REPO_ROOT/install/setup.bash" >> ~/.bashrc

# ── Step 9: Smoke tests ───────────────────────────────────────────
echo ""
echo "Step 9/9: Smoke tests"
source "$REPO_ROOT/install/setup.bash"

echo -n "  ROS2 Jazzy:   "
ros2 --version && echo "OK" || echo "FAIL"

echo -n "  Gazebo:       "
gz sim --version 2>&1 | head -1 && echo "OK" || echo "FAIL"

echo -n "  Ollama:       "
ollama list | grep llama3.2 && echo "OK" || echo "FAIL (run: ollama pull llama3.2)"

echo -n "  ROCm:         "
if command -v rocminfo &>/dev/null; then
    rocminfo 2>/dev/null | grep -c "gfx1100" | grep -q "1" \
        && echo "gfx1100 (RX 7700 XT) detected — OK" \
        || echo "ROCm installed but GPU not detected — log out and back in"
else
    echo "FAIL — ROCm not found"
fi

echo ""
echo "============================================================"
echo "Bootstrap complete."
echo ""
echo "Next steps:"
echo "  1. Log out and back in to activate ROCm GPU access"
echo "  2. Open a new terminal and run:"
echo "     source ~/.bashrc"
echo "     cd $REPO_ROOT"
echo "     ros2 launch langrobot langrobot.launch.py"
echo "============================================================"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x scripts/bootstrap.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/bootstrap.sh
git commit -m "feat: bootstrap.sh — one-time install for Ubuntu 24.04 (ROS2 Jazzy, Gazebo Harmonic, ROCm, Ollama)"
```

---

## Task 8: Phase 1 verification

This task is performed **on the Linux PC** after running bootstrap.sh. No code is written — this is the integration gate.

- [ ] **Step 1: Run bootstrap (one time only)**

```bash
cd ~/LangRobot   # wherever you cloned the repo on Linux
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

Watch for errors. If a step fails, re-run that step manually before continuing.

- [ ] **Step 2: Log out and back in (activate ROCm)**

Required for GPU group membership to take effect.

- [ ] **Step 3: Verify ROCm sees the GPU**

```bash
rocminfo | grep "gfx1100"
```

Expected output: a line containing `gfx1100` — confirms RX 7700 XT is detected.

- [ ] **Step 4: Source and build**

```bash
source ~/.bashrc
cd ~/LangRobot
colcon build --symlink-install
source install/setup.bash
```

Expected: build finishes with `Summary: 1 package finished`.

- [ ] **Step 5: Run unit tests**

```bash
PYTHONPATH=src/langrobot python -m pytest tests/test_robot_abstraction.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 6: Launch the simulation**

```bash
ros2 launch langrobot langrobot.launch.py
```

Expected: Gazebo opens with the Franka Panda arm visible. The controller node logs:
```
[controller_node]: Controller node started for FrankaRobot
[controller_node]: Joints: ['panda_joint1', ..., 'panda_joint7']
```

- [ ] **Step 7: Send a joint command — verify arm moves**

Open a second terminal on the Linux PC:

```bash
source ~/.bashrc && source ~/LangRobot/install/setup.bash

ros2 topic pub --once /joint_trajectory trajectory_msgs/msg/JointTrajectory '{
  joint_names: [panda_joint1, panda_joint2, panda_joint3, panda_joint4, panda_joint5, panda_joint6, panda_joint7],
  points: [{
    positions: [0.5, -0.5, 0.3, -1.8, 0.1, 1.2, 0.5],
    time_from_start: {sec: 2, nanosec: 0}
  }]
}'
```

Expected:
- Controller node logs: `Published joint command (7 joints): 0.500, -0.500, ...`
- Franka arm visibly moves in Gazebo to the new joint positions

**Phase 1 gate PASSED.** Proceed to plan Phase 2.

- [ ] **Step 8: Commit final state from Mac**

```bash
# On Mac — ensure all files are committed
git status  # should be clean
git log --oneline -5
```

---

## Troubleshooting

**`franka_description` xacro not found:**
Check `ros2 pkg list | grep franka`. If missing, the apt package didn't install — try the source build path in bootstrap.sh Step 4 manually.

**Gazebo opens but arm not spawned:**
The `create` node runs after a 3-second delay. Wait 10 seconds after Gazebo opens. If still missing, check terminal for spawn errors. Common cause: `franka_description` xacro path differs — inspect with `ros2 pkg prefix franka_description`.

**`/joint_commands` has no effect on Gazebo arm:**
Phase 1 uses a minimal publisher. Full ros2_control hardware interface integration (which makes Gazebo actually execute the trajectory) is set up in Phase 5 (planner_node + MoveIt2). In Phase 1, confirming the topic is published is sufficient — the arm moving visually requires the ros2_control Gazebo plugin to be wired up, which Phase 5 completes.

**ROCm `rocminfo` shows no GPU:**
Log out and back in — group membership (`render`, `video`) requires a new session. If still failing: `groups` should list `render video`. If not: `sudo usermod -a -G render,video $USER` then log out.

**Ollama not using GPU:**
After ROCm is working, `ollama run llama3.2` should show GPU memory usage in `rocm-smi`. If it runs on CPU, check `ROCM_PATH=/opt/rocm ollama serve`.
