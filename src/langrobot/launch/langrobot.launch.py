import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('langrobot')

    try:
        franka_pkg = get_package_share_directory('franka_description')
    except Exception:
        raise RuntimeError(
            'franka_description package not found.\n'
            'Run: sudo apt install ros-jazzy-franka-description\n'
            'Or build from source — see scripts/bootstrap.sh Step 4.'
        )

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    robot_description = Command([
        'xacro ',
        os.path.join(franka_pkg, 'robots', 'panda', 'panda.urdf.xacro'),
        ' hand:=true',
        ' gazebo:=ignition',
    ])

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

    controller_node = Node(
        package='langrobot',
        executable='controller_node',
        name='controller_node',
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    # Delay spawn 3 seconds to give Gazebo time to initialise
    delayed_spawn = TimerAction(period=3.0, actions=[spawn_robot])

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher,
        gazebo,
        clock_bridge,
        delayed_spawn,
        controller_node,
    ])
