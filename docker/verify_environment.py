"""Fail if the container uses wrong OS/ROS or has missing installed URDF assets."""
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory
import xacro

release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
assert release['VERSION_ID'].strip('"') == '24.04', release
assert os.environ['ROS_DISTRO'] == 'jazzy'
packages = ['igvc_description', 'igvc_sim_bridge', 'igvc_navigation', 'igvc_perception',
            'igvc_gps', 'igvc_lane_layer', 'ros_tcp_endpoint', 'rviz2', 'nav2_bringup']
origins = {name: get_package_share_directory(name) for name in packages}
description = ET.fromstring(xacro.process_file(str(Path(origins['igvc_description']) / 'urdf/r3_a.urdf.xacro')).toxml())
count = 0
for mesh in description.findall('.//mesh'):
    uri = mesh.attrib['filename']
    assert uri.startswith('package://'), uri
    package, relative = uri[len('package://'):].split('/', 1)
    assert (Path(get_package_share_directory(package)) / relative).is_file(), uri
    count += 1
assert count > 0
print(json.dumps({'passed': True, 'ubuntu': '24.04', 'ros': os.environ['ROS_DISTRO'],
                  'packages': origins, 'resolved_meshes': count}, indent=2))
