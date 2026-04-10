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
