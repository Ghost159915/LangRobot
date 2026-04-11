#!/bin/bash
# Recreate the symlinks for Panda compatibility in Jazzy
mkdir -p src/franka_description/robots/panda
ln -sf ../fr3/fr3.urdf.xacro src/franka_description/robots/panda/panda.urdf.xacro
ln -sf ../../end_effectors/franka_hand/franka_hand.urdf.xacro src/franka_description/robots/panda/hand.urdf.xacro
echo "Franka Panda-compatibility symlinks restored."

