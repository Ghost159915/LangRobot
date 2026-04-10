#!/usr/bin/env bash
# LangRobot bootstrap — run ONCE on a fresh Ubuntu 24.04 machine.
# After this completes, daily workflow is:
#   git pull && colcon build --symlink-install && ros2 launch langrobot langrobot.launch.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo " LangRobot Bootstrap — Ubuntu 24.04 + ROS2 Jazzy"
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
    lsb-release \
    python3-pip

# ── Step 2: ROS2 Jazzy ───────────────────────────────────────────
echo ""
echo "Step 2/9: ROS2 Jazzy"
if ! dpkg -l ros-jazzy-desktop &>/dev/null 2>&1; then
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
    # Add ROS2 source to .bashrc if not already there
    grep -qxF 'source /opt/ros/jazzy/setup.bash' ~/.bashrc \
        || echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
else
    echo "  ROS2 Jazzy already installed — skipping"
fi

# ── Step 3: Gazebo Harmonic + ros-gz ─────────────────────────────
echo ""
echo "Step 3/9: Gazebo Harmonic + ros-gz bridge"
if ! command -v gz &>/dev/null 2>&1; then
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
    echo "  Gazebo Harmonic already installed — skipping"
fi

# ── Step 4: Franka description ────────────────────────────────────
echo ""
echo "Step 4/9: Franka ROS2 packages"
if apt-cache show ros-jazzy-franka-description &>/dev/null 2>&1; then
    sudo apt-get install -y ros-jazzy-franka-description
else
    echo "  ros-jazzy-franka-description not in apt — building from source"
    FRANKA_WS="$HOME/franka_ws"
    mkdir -p "$FRANKA_WS/src"
    if [ ! -d "$FRANKA_WS/src/franka_description" ]; then
        git clone https://github.com/frankaemika/franka_description.git \
            -b main "$FRANKA_WS/src/franka_description"
    fi
    cd "$FRANKA_WS"
    source /opt/ros/jazzy/setup.bash
    colcon build --symlink-install
    grep -qxF "source $FRANKA_WS/install/setup.bash" ~/.bashrc \
        || echo "source $FRANKA_WS/install/setup.bash" >> ~/.bashrc
    cd "$REPO_ROOT"
fi

# ── Step 5: ROCm 6.x (AMD RX 7700 XT) ───────────────────────────
echo ""
echo "Step 5/9: ROCm 6.x for AMD RX 7700 XT (gfx1100)"
if ! command -v rocminfo &>/dev/null 2>&1; then
    ROCM_DEB="amdgpu-install_6.3.3.60303-1_all.deb"
    ROCM_URL="https://repo.radeon.com/amdgpu-install/6.3.3/ubuntu/noble/$ROCM_DEB"
    wget -q "$ROCM_URL" -O "/tmp/$ROCM_DEB"
    sudo apt-get install -y "/tmp/$ROCM_DEB"
    sudo amdgpu-install --usecase=rocm --no-dkms -y
    sudo usermod -a -G render,video "$USER"
    rm -f "/tmp/$ROCM_DEB"
    echo ""
    echo "  ⚠  ROCm installed. You MUST log out and back in (or reboot)"
    echo "     before GPU acceleration is active. Run 'rocminfo' after"
    echo "     relogin to confirm gfx1100 (RX 7700 XT) is detected."
else
    echo "  ROCm already installed — skipping"
fi

# ── Step 6: Ollama + Llama 3.2 ───────────────────────────────────
echo ""
echo "Step 6/9: Ollama + Llama 3.2"
if ! command -v ollama &>/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
fi
# Pull model — Ollama auto-detects ROCm for AMD GPU inference
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
grep -qxF "source $REPO_ROOT/install/setup.bash" ~/.bashrc \
    || echo "source $REPO_ROOT/install/setup.bash" >> ~/.bashrc

# ── Step 9: Smoke tests ───────────────────────────────────────────
echo ""
echo "Step 9/9: Smoke tests"
source "$REPO_ROOT/install/setup.bash"

echo -n "  ROS2 Jazzy:   "
ros2 --version && echo "OK" || echo "FAIL"

echo -n "  Gazebo:       "
gz sim --version 2>&1 | head -1 || echo "FAIL"

echo -n "  Ollama:       "
ollama list | grep -q llama3.2 && echo "llama3.2 present — OK" || echo "FAIL (run: ollama pull llama3.2)"

echo -n "  ROCm GPU:     "
if command -v rocminfo &>/dev/null 2>&1; then
    rocminfo 2>/dev/null | grep -q "gfx1100" \
        && echo "gfx1100 (RX 7700 XT) detected — OK" \
        || echo "ROCm installed but GPU not yet visible — log out and back in"
else
    echo "FAIL — rocminfo not found"
fi

echo ""
echo "============================================================"
echo " Bootstrap complete."
echo ""
echo " Next steps:"
echo "   1. Log out and back in to activate ROCm GPU access"
echo "   2. Open a new terminal and run:"
echo "        source ~/.bashrc"
echo "        cd $REPO_ROOT"
echo "        ros2 launch langrobot langrobot.launch.py"
echo "============================================================"
