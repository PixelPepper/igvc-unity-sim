"""Navigation only: existing simulator owns clock, odometry, sensors and TF."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = Path(get_package_share_directory('igvc_navigation'))
    params = LaunchConfiguration('params_file')
    names = ['planner_server', 'controller_server', 'behavior_server', 'bt_navigator']
    nodes = []
    for package, executable in [('nav2_planner', 'planner_server'),
                                ('nav2_controller', 'controller_server'),
                                ('nav2_behaviors', 'behavior_server'),
                                ('nav2_bt_navigator', 'bt_navigator')]:
        overrides = {'use_sim_time': True}
        if executable == 'bt_navigator':
            overrides['default_nav_to_pose_bt_xml'] = str(share / 'behavior_trees/local_goal.xml')
            overrides['default_nav_through_poses_bt_xml'] = str(share / 'behavior_trees/local_through.xml')
        nodes.append(Node(package=package, executable=executable, name=executable,
                          output='screen', parameters=[params, overrides],
                          remappings=[('cmd_vel', '/cmd_vel/nav')]))
    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=str(share / 'config/local_navigation.yaml')),
        DeclareLaunchArgument('autostart', default_value='true'),
        *nodes,
        Node(package='igvc_perception', executable='lane_detector', output='screen'),
        Node(package='igvc_perception', executable='depth_processor', output='screen'),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_igvc_navigation', output='screen',
             parameters=[{'use_sim_time': True, 'autostart': LaunchConfiguration('autostart'),
                          'node_names': names, 'bond_timeout': 4.0}]),
    ])
