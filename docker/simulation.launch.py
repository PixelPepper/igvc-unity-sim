"""Container owns one ROS graph; Unity remains a separate Windows process."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(
            Path(get_package_share_directory(package)) / 'launch' / filename)))
        for package, filename in [
            ('igvc_sim_bridge', 'r3a.launch.py'),
            ('igvc_navigation', 'local_navigation.launch.py'),
        ]
    ])
