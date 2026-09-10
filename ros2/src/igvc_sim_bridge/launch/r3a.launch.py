"""CAD robot in ideal motion mode. Joint states come only from Unity."""
from pathlib import Path
import json
from igvc_sim_bridge.suspension_description import with_caster_suspension
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    share = Path(get_package_share_directory('igvc_description'))
    description = xacro.process_file(str(share / 'urdf/r3_a.urdf.xacro')).toxml()
    suspension = json.loads((share / 'config/caster_suspension.json').read_text())
    description = with_caster_suspension(description, suspension['joint_limit_m'])
    return LaunchDescription([
        Node(package='ros_tcp_endpoint', executable='default_server_endpoint',
             parameters=[{'ROS_IP': '0.0.0.0', 'ROS_TCP_PORT': 10000}], output='screen'),
        Node(package='igvc_sim_bridge', executable='probe_adapter',
             parameters=[{'r3a_mode': True, 'require_lanes': True, 'require_depth': True}], output='screen'),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': description, 'use_sim_time': True}], output='screen'),
        Node(package='igvc_gps', executable='synthetic_gps', output='screen',
             parameters=[{'use_sim_time': True, 'origin_file': str(Path(get_package_share_directory('igvc_gps')) / 'config/origin.json')}]),
    ])
