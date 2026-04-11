#!/bin/bash
# Recreate the symlinks for Panda compatibility in Jazzy
mkdir -p src/franka_description/robots/panda
ln -sf ../fr3/fr3.urdf.xacro src/franka_description/robots/panda/panda.urdf.xacro
ln -sf ../../end_effectors/franka_hand/franka_hand.urdf.xacro src/franka_description/robots/panda/hand.urdf.xacro
echo "Franka Panda-compatibility symlinks restored."

# Ignore the full franka_ros2 repo — those packages need the real libfranka
# hardware SDK which is not available in simulation. Only franka_description
# (cloned separately into src/franka_description/) is needed.
if [ -d "src/franka_ros2" ]; then
    touch src/franka_ros2/COLCON_IGNORE
    echo "COLCON_IGNORE set on src/franka_ros2 (hardware packages not needed for sim)."
fi

