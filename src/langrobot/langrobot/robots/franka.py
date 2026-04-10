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
