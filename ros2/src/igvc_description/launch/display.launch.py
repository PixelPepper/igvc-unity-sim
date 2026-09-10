"""Standalone description viewer; never launch with the probe TF authority."""
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from pathlib import Path
import xacro


def setup(context):
    share = Path(get_package_share_directory('igvc_description'))
    description = xacro.process_file(str(share / 'urdf/r3_a.urdf.xacro')).toxml()
    publisher = 'joint_state_publisher'
    if LaunchConfiguration('gui').perform(context).lower() == 'true':
        try:
            get_package_share_directory('joint_state_publisher_gui')
            publisher = 'joint_state_publisher_gui'
        except PackageNotFoundError:
            pass
    sim_time = LaunchConfiguration('use_sim_time').perform(context).lower() == 'true'
    return [
        LogInfo(msg='Description viewer: provisional collisions; joint publisher=' + publisher),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': description, 'use_sim_time': sim_time}], output='screen'),
        Node(package=publisher, executable=publisher, parameters=[{'use_sim_time': sim_time}], output='screen'),
        Node(package='rviz2', executable='rviz2', arguments=['-d', str(share / 'rviz/description.rviz')],
             parameters=[{'use_sim_time': sim_time}], condition=IfCondition(LaunchConfiguration('rviz'))),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('rviz', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('use_sim_time', default_value='false', choices=['true', 'false']),
        OpaqueFunction(function=setup),
    ])
