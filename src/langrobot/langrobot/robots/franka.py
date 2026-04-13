import math
from langrobot.robots.base_robot import BaseRobot, RobotConfig


class FrankaRobot(BaseRobot):
    """Franka Panda (FR3) robot configuration."""

    @property
    def config(self) -> RobotConfig:
        return RobotConfig(
            joint_names=[
                'fr3_joint1',
                'fr3_joint2',
                'fr3_joint3',
                'fr3_joint4',
                'fr3_joint5',
                'fr3_joint6',
                'fr3_joint7',
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
