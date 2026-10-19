"""Fail if the container uses wrong OS/ROS, misses installed assets/tools, or cannot start RViz."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_prefix, get_package_share_directory
import xacro

ROOT = Path(__file__).resolve().parent.parent
release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
assert release['VERSION_ID'].strip('"') == '24.04', release
assert os.environ['ROS_DISTRO'] == 'jazzy'
packages = ['igvc_description', 'igvc_sim_bridge', 'igvc_navigation', 'igvc_perception',
            'igvc_gps', 'igvc_lane_layer', 'ros_tcp_endpoint', 'rviz2', 'nav2_bringup',
            'nav2_smac_planner', 'nav2_mppi_controller']
origins = {name: get_package_share_directory(name) for name in packages}
mppi_share = Path(origins['nav2_mppi_controller'])
apt_mppi = subprocess.run(['dpkg-query', '-W', '-f=${Version}', 'ros-jazzy-nav2-mppi-controller'],
                          capture_output=True, text=True, check=True).stdout.strip().split('-', 1)[0]
assert apt_mppi == '1.3.13', apt_mppi
overlay_mppi = ET.parse(mppi_share / 'package.xml').getroot().findtext('version')
assert overlay_mppi == '1.3.13', overlay_mppi
marker = (mppi_share / 'igvc-footprint-cost-critic-v1').read_text(encoding='utf-8')
assert marker == 'igvc-footprint-cost-critic-v1\nupstream_commit=f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501\n', marker
description = ET.fromstring(xacro.process_file(str(Path(origins['igvc_description']) / 'urdf/r3_a.urdf.xacro')).toxml())
count = 0
for mesh in description.findall('.//mesh'):
    uri = mesh.attrib['filename']
    assert uri.startswith('package://'), uri
    package, relative = uri[len('package://'):].split('/', 1)
    assert (Path(get_package_share_directory(package)) / relative).is_file(), uri
    count += 1
assert count > 0

# Import (never run) the mission tools the image ships; learning is a namespace package.
sys.path.insert(0, str(ROOT / 'tools'))
importlib.import_module('sensor_course')
importlib.import_module('learning.learned_scorer')
sandbox_profile = importlib.import_module('sandbox_profile')
assert sandbox_profile.DEFAULTS['controller'] == 'rpp', sandbox_profile.DEFAULTS
nav_profile, baseline = sandbox_profile.build_profile({})
assert baseline == ROOT / 'docs/evidence/navigation-2026-10-01-success/profile.yaml' and baseline.is_file(), baseline
follow_path = nav_profile['controller_server']['ros__parameters']['FollowPath']
assert follow_path['desired_linear_vel'] == sandbox_profile.DEFAULTS['speed_mps'], follow_path
competition = ROOT / 'config/competition/igvc-2027-autonav.json'
assert competition.is_file(), competition
json.loads(competition.read_text(encoding='utf-8'))
assert not (ROOT / 'artifacts').exists(), 'trained models must not ship in the image'

rviz_config = Path(origins['igvc_sim_bridge']) / 'rviz/nav.rviz'
assert rviz_config.is_file() and rviz_config.stat().st_size > 0, rviz_config
rviz = Path(get_package_prefix('rviz2')) / 'lib/rviz2/rviz2'
assert rviz.is_file() and os.access(rviz, os.X_OK), rviz
smoke = subprocess.run([str(rviz), '--help'], env=os.environ | {'QT_QPA_PLATFORM': 'offscreen'},
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20)
assert smoke.returncode == 0, (smoke.returncode, smoke.stdout[-2000:], smoke.stderr[-2000:])
print(json.dumps({'passed': True, 'ubuntu': '24.04', 'ros': os.environ['ROS_DISTRO'],
                  'packages': origins, 'resolved_meshes': count, 'rpp_profile': str(baseline),
                  'competition': str(competition), 'rviz_config': str(rviz_config),
                  'rviz_help_exit': smoke.returncode}, indent=2))
