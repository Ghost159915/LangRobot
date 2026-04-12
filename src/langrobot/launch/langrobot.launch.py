import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Arm joint names — must match the spawned Gazebo model name.
_ARM_JOINTS = [f'fr3_joint{i}' for i in range(1, 8)]
_MODEL_NAME = 'panda'


def _build_robot_description() -> str:
    """Run xacro on the franka URDF and inject Gazebo JointPositionController
    plugins for each arm joint.

    We use Gazebo's built-in gz-sim-joint-position-controller-system (one per
    joint) instead of gz_ros2_control, because gz_ros2_control has an ABI
    mismatch with the installed hardware_interface on this system.

    Each plugin listens on the default Gazebo topic:
        /model/<model_name>/joint/<joint_name>/cmd_pos  (gz.msgs.Double)
    These are bridged from ROS2 std_msgs/Float64 in the joint_command_bridge.
    """
    try:
        franka_pkg = get_package_share_directory('franka_description')
    except Exception:
        raise RuntimeError(
            'franka_description package not found.\n'
            'Run: bash fix_franka.sh  then  colcon build --symlink-install'
        )

    xacro_path = os.path.join(franka_pkg, 'robots', 'panda', 'panda.urdf.xacro')
    result = subprocess.run(
        ['xacro', xacro_path, 'hand:=true', 'gazebo:=true'],
        capture_output=True, text=True,
    )
    if not result.stdout.strip():
        raise RuntimeError(f'xacro produced no output.\nstderr: {result.stderr}')

    # Build one JointPositionController plugin block per arm joint.
    # PID gains are tuned for smooth simulation (not hardware).
    # Explicit <topic> overrides Gazebo's default axis-indexed topic
    # (/model/<model>/joint/<joint>/0/cmd_pos) which is invalid as a ROS2 topic
    # name because numeric-only path tokens are forbidden.
    joint_plugins = '\n'.join(
        f"""    <plugin filename="gz-sim-joint-position-controller-system"
            name="gz::sim::systems::JointPositionController">
      <joint_name>{name}</joint_name>
      <topic>/model/{_MODEL_NAME}/joint/{name}/cmd_pos</topic>
      <p_gain>500</p_gain>
      <i_gain>0</i_gain>
      <d_gain>20</d_gain>
      <cmd_max>1000</cmd_max>
      <cmd_min>-1000</cmd_min>
    </plugin>"""
        for name in _ARM_JOINTS
    )

    # JointStatePublisher publishes /world/<world>/model/<model>/joint_state
    # (gz.msgs.Model) so the joint_state_bridge can forward it to /joint_states.
    state_publisher_plugin = """    <plugin filename="gz-sim-joint-state-publisher-system"
        name="gz::sim::systems::JointStatePublisher">
    </plugin>"""

    gazebo_block = f"""
  <!-- Per-joint position controllers (Gazebo Harmonic built-in).
       Topics: /model/{_MODEL_NAME}/joint/<joint>/0/cmd_pos (gz transport)
       Bridged from ROS2 Float64 via joint_command_bridge. -->
  <gazebo>
{joint_plugins}
{state_publisher_plugin}
  </gazebo>
"""
    return result.stdout.replace('</robot>', gazebo_block + '</robot>')


def generate_launch_description():
    pkg_share = get_package_share_directory('langrobot')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    robot_description = _build_robot_description()

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
            '-name', _MODEL_NAME,
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

    # Bridge camera topics: Gazebo → ROS2.
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

    # Bridge Gazebo model joint states → ROS2 /joint_states.
    # The model is spawned as 'panda'; Gazebo publishes joint state on this topic.
    joint_state_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='joint_state_bridge',
        arguments=[
            f'/world/langrobot_basic/model/{_MODEL_NAME}/joint_state'
            '@sensor_msgs/msg/JointState[gz.msgs.Model',
        ],
        remappings=[
            (f'/world/langrobot_basic/model/{_MODEL_NAME}/joint_state', '/joint_states'),
        ],
        output='screen',
    )

    # Bridge per-joint position commands: ROS2 Float64 → Gazebo Double.
    # ] direction means ROS2 → Gazebo (opposite of camera bridge above).
    # The plugin <topic> is set explicitly in the URDF injection (no /0/ suffix)
    # so this ROS2 topic name is valid.
    joint_command_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='joint_command_bridge',
        arguments=[
            f'/model/{_MODEL_NAME}/joint/{name}/cmd_pos'
            '@std_msgs/msg/Float64]gz.msgs.Double'
            for name in _ARM_JOINTS
        ],
        output='screen',
    )

    controller_node = Node(
        package='langrobot',
        executable='controller_node',
        name='controller_node',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    # Relay: splits /forward_position_controller/commands (Float64MultiArray)
    # into 7 per-joint Float64 topics consumed by the joint_command_bridge.
    joint_relay_node = Node(
        package='langrobot',
        executable='joint_relay_node',
        name='joint_relay_node',
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

    lang_node = Node(
        package='langrobot',
        executable='lang_node',
        name='lang_node',
        output='screen',
    )

    perception_node = Node(
        package='langrobot',
        executable='perception_node',
        name='perception_node',
        output='screen',
    )

    # Delay spawn and bridges 3 s to give Gazebo time to initialise.
    delayed_spawn = TimerAction(period=3.0, actions=[spawn_robot])
    delayed_camera_bridge = TimerAction(period=3.0, actions=[camera_bridge])
    # Joint bridges need the model to be spawned first (3 s).
    delayed_joint_bridges = TimerAction(
        period=5.0,
        actions=[joint_state_bridge, joint_command_bridge],
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        delayed_spawn,
        delayed_camera_bridge,
        delayed_joint_bridges,
        controller_node,
        joint_relay_node,
        rviz_node,
        lang_node,
        perception_node,
    ])
