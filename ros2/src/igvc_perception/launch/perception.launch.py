"""Observed camera processing only; no planner or autonomous commands."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='igvc_perception', executable='depth_processor', output='screen'),
        Node(package='igvc_perception', executable='lane_detector', output='screen'),
    ])
