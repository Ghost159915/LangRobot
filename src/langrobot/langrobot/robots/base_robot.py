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
