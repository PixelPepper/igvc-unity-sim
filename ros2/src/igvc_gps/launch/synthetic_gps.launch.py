from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def generate_launch_description():
    origin = str(Path(get_package_share_directory('igvc_gps')) / 'config/origin.json')
    return LaunchDescription([
        DeclareLaunchArgument('origin_file', default_value=origin),
        Node(package='igvc_gps', executable='synthetic_gps', output='screen',
             parameters=[{'use_sim_time': True, 'origin_file': LaunchConfiguration('origin_file')}])])
