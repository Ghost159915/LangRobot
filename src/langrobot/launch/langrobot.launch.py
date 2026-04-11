import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('langrobot')

    try:
        franka_pkg = get_package_share_directory('franka_description')
    except Exception:
        raise RuntimeError(
            'franka_description package not found.\n'
            'Run: bash fix_franka.sh  then  colcon build --symlink-install\n'
            'See scripts/bootstrap.sh Step 4.'
        )

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    robot_description = Command([
        'xacro ',
        os.path.join(franka_pkg, 'robots', 'panda', 'panda.urdf.xacro'),
        ' hand:=true',
        ' gazebo:=true',
    ])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{
            # Explicitly cast Xacro output to string — prevents Jazzy YAML parser crash
            'robot_description': ParameterValue(robot_description, value_type=str),
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
    # Gazebo rgbd_camera sensor with <topic>camera</topic> publishes:
    #   /camera/image          (gz.msgs.Image)
    #   /camera/depth_image    (gz.msgs.Image)
    #   /camera/camera_info    (gz.msgs.CameraInfo)
    # Remapping renames /camera/image → /camera/rgb_image to match the spec.
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

    # Delay spawn and camera bridge 3 seconds to give Gazebo time to initialise.
    # Without the delay the bridge logs noisy "No publisher" errors until topics appear.
    delayed_spawn = TimerAction(period=3.0, actions=[spawn_robot])
    delayed_camera_bridge = TimerAction(period=3.0, actions=[camera_bridge])

    # lang_node: no use_sim_time — talks to Ollama via wall-clock HTTP, not sim time.
    lang_node = Node(
        package='langrobot',
        executable='lang_node',
        name='lang_node',
        output='screen',
    )

    # perception_node: no use_sim_time — processes camera frames in real time.
    perception_node = Node(
        package='langrobot',
        executable='perception_node',
        name='perception_node',
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        delayed_camera_bridge,
        delayed_spawn,
        controller_node,
        rviz_node,
        lang_node,
        perception_node,
    ])
