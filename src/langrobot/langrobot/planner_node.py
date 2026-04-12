"""planner_node — orchestrates 9-step pick-and-place using MoveIt2.

Subscribes to:
  /task_command  (std_msgs/String, JSON) — {"action": "pick_and_place",
                                             "object": "<colour>",
                                             "target": "<colour>"}
  /object_poses  (std_msgs/String, JSON) — latest block positions from perception

On each /task_command:
  1. Validates both blocks are visible.
  2. Executes the 9-step sequence using moveit_py.
  3. Logs each step result.
"""
from __future__ import annotations
import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

try:
    from moveit.planning import MoveItPy
    from moveit.core.robot_state import RobotState
    from geometry_msgs.msg import PoseStamped
    HAS_MOVEIT = True
except ImportError:
    HAS_MOVEIT = False


# ── Pure helpers (tested without ROS2) ───────────────────────────────────

def find_block(poses: list[dict], colour: str) -> dict | None:
    """Return the block dict for the given colour if visible, else None."""
    for block in poses:
        if block['colour'] == colour and block.get('visible'):
            return block
    return None


def compute_pre_grasp_pose(block: dict) -> tuple[float, float, float]:
    """Return (x, y, z) 10 cm above the block centre."""
    return (block['x'], block['y'], block['z'] + 0.10)


def compute_grasp_pose(block: dict) -> tuple[float, float, float]:
    """Return (x, y, z) at the block centre (grasp height)."""
    return (block['x'], block['y'], block['z'])


def compute_lift_pose(block: dict) -> tuple[float, float, float]:
    """Return (x, y, z) 15 cm above the block centre."""
    return (block['x'], block['y'], block['z'] + 0.15)


def compute_pre_place_pose(target: dict) -> tuple[float, float, float]:
    """Return (x, y, z) 10 cm above the target block."""
    return (target['x'], target['y'], target['z'] + 0.10)


def compute_place_pose(target: dict) -> tuple[float, float, float]:
    """Return (x, y, z) at target top + 5 cm (stack height)."""
    return (target['x'], target['y'], target['z'] + 0.05)


def make_pose_stamped(x: float, y: float, z: float) -> 'PoseStamped':
    """Build a PoseStamped pointing straight down (pitch=π) in fr3_link0 frame."""
    pose_stamped = PoseStamped()
    pose_stamped.header.frame_id = 'fr3_link0'
    pose_stamped.pose.position.x = x
    pose_stamped.pose.position.y = y
    pose_stamped.pose.position.z = z
    # roll=0, pitch=π, yaw=0 → end-effector pointing straight down
    # Quaternion for pitch=π: (x=0, y=1, z=0, w=0)
    pose_stamped.pose.orientation.x = 0.0
    pose_stamped.pose.orientation.y = 1.0
    pose_stamped.pose.orientation.z = 0.0
    pose_stamped.pose.orientation.w = 0.0
    return pose_stamped


# ── ROS2 node ─────────────────────────────────────────────────────────────

_GRIPPER_OPEN = 0.04   # metres — fully open
_GRIPPER_CLOSE = 0.0   # metres — fully closed


class PlannerNode(Node):
    def __init__(self):
        super().__init__('planner_node')
        self._latest_poses: list[dict] = []

        self.create_subscription(String, '/object_poses', self._on_object_poses, 10)
        self.create_subscription(String, '/task_command', self._on_task_command, 10)

        if HAS_MOVEIT:
            self._moveit = MoveItPy(node_name='planner_node')
            self._arm = self._moveit.get_planning_component('panda_arm')
            self._gripper = self._moveit.get_planning_component('hand')
        else:
            self._moveit = None
            self._arm = None
            self._gripper = None

        self.get_logger().info('planner_node ready')

    def _on_object_poses(self, msg: String) -> None:
        try:
            self._latest_poses = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().error('Invalid JSON on /object_poses')

    def _on_task_command(self, msg: String) -> None:
        try:
            cmd = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().error('Invalid JSON on /task_command')
            return

        if cmd.get('action') != 'pick_and_place':
            self.get_logger().warning(f'Unknown action: {cmd.get("action")} — ignoring')
            return

        object_colour = cmd.get('object', '')
        target_colour = cmd.get('target', '')

        obj_block = find_block(self._latest_poses, object_colour)
        tgt_block = find_block(self._latest_poses, target_colour)

        if obj_block is None:
            self.get_logger().error(f'Object block "{object_colour}" not visible — aborting')
            return
        if tgt_block is None:
            self.get_logger().error(f'Target block "{target_colour}" not visible — aborting')
            return

        self.get_logger().info(f'Pick-and-place: {object_colour} → {target_colour}')
        self._run_pick_and_place(obj_block, tgt_block)

    def _move_to_pose(self, x: float, y: float, z: float, label: str) -> bool:
        """Plan and execute a Cartesian end-effector pose goal. Returns True on success."""
        if self._arm is None:
            self.get_logger().warning(f'MoveIt not available — skipping {label}')
            return False
        self._arm.set_start_state_to_current_state()
        self._arm.set_goal_state(
            pose_stamped_msg=make_pose_stamped(x, y, z),
            pose_link='fr3_hand',
        )
        plan = self._arm.plan()
        if not plan:
            self.get_logger().error(f'Planning failed: {label}')
            return False
        result = self._moveit.execute(plan.trajectory, controllers=[])
        if not result:
            self.get_logger().error(f'Execution failed: {label}')
            return False
        self.get_logger().info(f'Step OK: {label}')
        return True

    def _move_gripper(self, position: float, label: str) -> bool:
        """Open or close gripper. Returns True on success."""
        if self._gripper is None:
            self.get_logger().warning(f'MoveIt not available — skipping {label}')
            return False
        self._gripper.set_start_state_to_current_state()
        robot_state = RobotState(self._moveit.get_robot_model())
        robot_state.set_joint_group_positions('hand', [position, position])
        self._gripper.set_goal_state(robot_state=robot_state)
        plan = self._gripper.plan()
        if not plan:
            self.get_logger().error(f'Gripper planning failed: {label}')
            return False
        result = self._moveit.execute(plan.trajectory, controllers=[])
        if not result:
            self.get_logger().error(f'Gripper execution failed: {label}')
            return False
        self.get_logger().info(f'Gripper step OK: {label}')
        return True

    def _move_to_home(self) -> bool:
        """Move arm to Franka home configuration (named state 'ready' in SRDF)."""
        if self._arm is None:
            return False
        self._arm.set_start_state_to_current_state()
        self._arm.set_goal_state(configuration_name='ready')
        plan = self._arm.plan()
        if not plan:
            self.get_logger().error('Home planning failed')
            return False
        result = self._moveit.execute(plan.trajectory, controllers=[])
        if not result:
            self.get_logger().error('Home execution failed')
            return False
        self.get_logger().info('Step OK: home')
        return True

    def _run_pick_and_place(self, obj: dict, tgt: dict) -> None:
        steps = [
            lambda: self._move_gripper(_GRIPPER_OPEN,  'step1_open_gripper'),
            lambda: self._move_to_pose(*compute_pre_grasp_pose(obj), 'step2_pre_grasp'),
            lambda: self._move_to_pose(*compute_grasp_pose(obj),     'step3_grasp'),
            lambda: self._move_gripper(_GRIPPER_CLOSE, 'step4_close_gripper'),
            lambda: self._move_to_pose(*compute_lift_pose(obj),      'step5_lift'),
            lambda: self._move_to_pose(*compute_pre_place_pose(tgt), 'step6_pre_place'),
            lambda: self._move_to_pose(*compute_place_pose(tgt),     'step7_place'),
            lambda: self._move_gripper(_GRIPPER_OPEN,  'step8_open_gripper'),
            lambda: self._move_to_home(),
        ]
        for step in steps:
            if not step():
                self.get_logger().error('Pick-and-place aborted at failed step')
                return
        self.get_logger().info('Pick-and-place complete')


def main(args=None):
    rclpy.init(args=args)
    node = PlannerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
