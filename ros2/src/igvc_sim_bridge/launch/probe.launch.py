from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('port', default_value='10000'),
        Node(package='ros_tcp_endpoint', executable='default_server_endpoint',
             parameters=[{'ROS_IP': '0.0.0.0', 'ROS_TCP_PORT': LaunchConfiguration('port')}],
             output='screen'),
        Node(package='igvc_sim_bridge', executable='probe_adapter', output='screen'),
        Node(package='rviz2', executable='rviz2',
             arguments=['-d', PathJoinSubstitution([FindPackageShare('igvc_sim_bridge'), 'rviz', 'probe.rviz'])],
             parameters=[{'use_sim_time': True}], condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
