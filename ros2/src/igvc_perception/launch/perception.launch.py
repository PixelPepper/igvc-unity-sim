"""Observed camera processing only; no planner or autonomous commands."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Image stamps come from the simulator /clock; compare them on that clock.
    return LaunchDescription([
        Node(package='igvc_perception', executable='depth_processor', output='screen',
             parameters=[{'use_sim_time': True}]),
        Node(package='igvc_perception', executable='lane_detector', output='screen',
             parameters=[{'use_sim_time': True}]),
    ])
