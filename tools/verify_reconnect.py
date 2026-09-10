"""Restart the owned ROS endpoint while one Unity player remains alive."""
import json
from pathlib import Path
import subprocess
import sys
import time
import rclpy
from igvc_sim_bridge.verify_probe import Verify

root = Path(__file__).resolve().parent.parent
supervisor = str(root / 'tools/ros_session.py')
rclpy.init()
node = Verify()
report = {'checks': {}}
def check(name, valid):
    report['checks'][name] = bool(valid)
    print(('PASS ' if valid else 'FAIL ') + name, flush=True)
    assert valid, name
try:
    node.wait(3)
    node.service('pause', False); node.service('estop', False); node.service('reset')
    node.wait(0.5)
    node.wait(1.0, 0.3)
    x_before = node.xy()[0]
    clock_before = node.seconds(node.last['clock'].clock)
    subprocess.run([sys.executable, supervisor, 'stop'], check=True)
    node.wait(1)
    count_before = node.counts['clock']
    odom_before = node.counts['odom']
    subprocess.run([sys.executable, supervisor, 'start'], check=True)
    deadline = time.monotonic() + 25
    while (node.counts['clock'] < count_before + 100 or node.counts['odom'] < odom_before + 20
           or node.seconds(node.last['odom'].header.stamp) < clock_before + 0.7) and time.monotonic() < deadline:
        node.wait(0.2)
    check('clock_reconnected', node.counts['clock'] >= count_before + 100)
    check('odometry_reconnected', node.counts['odom'] >= odom_before + 20)
    check('odometry_is_fresh', node.seconds(node.last['odom'].header.stamp) >= clock_before + 0.7)
    check('same_player_clock_continued', node.seconds(node.last['clock'].clock) > clock_before)
    travel = node.xy()[0] - x_before
    report['disconnect_forward_travel_m'] = travel
    check('disconnect_bounded_travel', -0.02 <= travel <= 0.2)
    check('no_command_replay', abs(node.last['odom'].twist.twist.linear.x) < 1e-6)
    baseline = node.counts['image']; node.wait(2)
    check('images_reconnected', node.counts['image'] - baseline >= 15)
    node.service('reset'); node.wait(0.5)
    check('services_reconnected', abs(node.xy()[0]) < 0.01)
    report['status'] = 'passed'
except Exception as exc:
    report['status'] = 'failed'; report['error'] = str(exc)
    raise
finally:
    (root / 'artifacts/checks/reconnect.json').write_text(json.dumps(report, indent=2))
    node.destroy_node()
    if rclpy.ok(): rclpy.shutdown()
