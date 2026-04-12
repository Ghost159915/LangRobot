import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _build_robot_description(pkg_share: str) -> str:
    """Generate the robot URDF by running xacro on the franka description,
    then append a ros2_control section and the gz_ros2_control Gazebo plugin.

    The franka_description package uses FR3-named joints (fr3_joint1–7) and has
    no ros2_control or Gazebo joint-control plugin of its own.  We inject both
    here so gz_ros2_control can drive the arm from ROS 2.
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
        raise RuntimeError(
            f'xacro produced no output.\nstderr: {result.stderr}'
        )

    controllers_yaml = os.path.join(pkg_share, 'config', 'fr3_controllers.yaml')

    # Initial joint positions = Franka home pose (avoids gravity collapse at t=0).
    ros2_control_block = f"""
  <!-- gz_ros2_control hardware interface — injected at launch time -->
  <ros2_control name="GazeboSystem" type="system">
    <hardware>
      <plugin>gz_ros2_control/GazeboSimSystem</plugin>
    </hardware>
    <joint name="fr3_joint1">
      <command_interface name="position"/>
      <state_interface name="position"><param name="initial_value">0.0</param></state_interface>
      <state_interface name="velocity"/>
    </joint>
    <joint name="fr3_joint2">
      <command_interface name="position"/>
      <state_interface name="position"><param name="initial_value">-0.7854</param></state_interface>
      <state_interface name="velocity"/>
    </joint>
    <joint name="fr3_joint3">
      <command_interface name="position"/>
      <state_interface name="position"><param name="initial_value">0.0</param></state_interface>
      <state_interface name="velocity"/>
    </joint>
    <joint name="fr3_joint4">
      <command_interface name="position"/>
      <state_interface name="position"><param name="initial_value">-2.3562</param></state_interface>
      <state_interface name="velocity"/>
    </joint>
    <joint name="fr3_joint5">
      <command_interface name="position"/>
      <state_interface name="position"><param name="initial_value">0.0</param></state_interface>
      <state_interface name="velocity"/>
    </joint>
    <joint name="fr3_joint6">
      <command_interface name="position"/>
      <state_interface name="position"><param name="initial_value">1.5708</param></state_interface>
      <state_interface name="velocity"/>
    </joint>
    <joint name="fr3_joint7">
      <command_interface name="position"/>
      <state_interface name="position"><param name="initial_value">0.7854</param></state_interface>
      <state_interface name="velocity"/>
    </joint>
  </ros2_control>
  <gazebo>
    <plugin filename="gz_ros2_control-system"
            name="gz_ros2_control::GazeboSimROS2ControlPlugin">
      <parameters>{controllers_yaml}</parameters>
    </plugin>
  </gazebo>
"""
    return result.stdout.replace('</robot>', ros2_control_block + '</robot>')


def generate_launch_description():
    pkg_share = get_package_share_directory('langrobot')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Ensure Gazebo can locate ROS2 system plugins (e.g. gz_ros2_control-system).
    # The library lives in /opt/ros/jazzy/lib but GZ_SIM_SYSTEM_PLUGIN_PATH is
    # not always set there after 'source install/setup.bash'.
    _ros_lib = '/opt/ros/jazzy/lib'
    _gz_path = os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', '')
    if _ros_lib not in _gz_path:
        os.environ['GZ_SIM_SYSTEM_PLUGIN_PATH'] = (
            f'{_ros_lib}:{_gz_path}' if _gz_path else _ros_lib
        )

    robot_description = _build_robot_description(pkg_share)

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
            '-name', 'panda',
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

    # Bridge camera topics from Gazebo → ROS2.
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

    controller_node = Node(
        package='langrobot',
        executable='controller_node',
        name='controller_node',
        parameters=[{'use_sim_time': use_sim_time}],
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

    # Spawn ros2_control controllers.
    # gz_ros2_control starts controller_manager when the robot is loaded (~3s).
    # Add extra margin so controller_manager is ready before spawners run.
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    forward_position_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['forward_position_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # Delay spawn and bridges 3 s to give Gazebo time to initialise.
    delayed_spawn = TimerAction(period=3.0, actions=[spawn_robot])
    delayed_camera_bridge = TimerAction(period=3.0, actions=[camera_bridge])
    # Controllers spawned at 10 s: robot spawns at 3 s, gz_ros2_control needs
    # a few seconds to start controller_manager after the model loads.
    delayed_controllers = TimerAction(
        period=10.0,
        actions=[joint_state_broadcaster_spawner, forward_position_controller_spawner],
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        delayed_spawn,
        delayed_camera_bridge,
        delayed_controllers,
        controller_node,
        rviz_node,
        lang_node,
        perception_node,
    ])
