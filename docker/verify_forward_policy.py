"""Bounded live command-gate test; run at a clear, stopped start pose."""
import argparse
import json
import time
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_srvs.srv import SetBool

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report', required=True)
args = parser.parse_args()
rclpy.init()
node = rclpy.create_node('verify_forward_policy')
gate = node.create_client(SetBool, '/sim/set_autonomy')
zone = node.create_client(SetBool, '/sim/set_unmarked_mode')
publisher = node.create_publisher(Twist, '/cmd_vel/nav', 1)
samples = []
poses = []
node.create_subscription(Twist, '/cmd_vel', lambda m: samples.append((m.linear.x, m.angular.z)), 10)
node.create_subscription(Odometry, '/odom', lambda m: poses.append((m.pose.pose.position.x,m.pose.pose.position.y)), 10)
checks = {}


def spin(seconds):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=.02)


def mode(client, value):
    if not client.wait_for_service(timeout_sec=3):
        raise RuntimeError('Mode service unavailable')
    future = client.call_async(SetBool.Request(data=value))
    end = time.monotonic()+3
    while not future.done() and time.monotonic() < end:
        spin(.05)
    if not future.done() or not future.result().success:
        raise RuntimeError('Mode change failed')


try:
    discovery_deadline = time.monotonic()+10
    while not poses and time.monotonic() < discovery_deadline:
        spin(.1)
    if not poses or abs(poses[-1][0])>.4 or abs(poses[-1][1])>.4:
        raise RuntimeError('Test requires a clear start pose within .4 m of origin')
    mode(gate, False); mode(zone, True); mode(gate, True)
    for name, linear, angular, blocked in (
            ('fast_reverse_stops', -.2, 0., True), ('pivot_stops', 0., .4, True),
            ('slow_backup_passes', -.1, 0., False), ('reverse_turn_stops', -.1, .2, True),
            ('tight_turn_stops', .05, .5, True), ('forward_passes', .2, 0., False)):
        samples.clear()
        message = Twist(); message.linear.x = linear; message.angular.z = angular
        for _ in range(8):
            publisher.publish(message); spin(.05)
        checks[name] = bool(samples) and (all(abs(v)<1e-6 and abs(w)<1e-6 for v,w in samples)
                                         if blocked else any(v*linear>0.005 for v,w in samples))
        publisher.publish(Twist()); spin(.15)
finally:
    publisher.publish(Twist())
    mode(gate, False); mode(zone, False)
    report = {'passed': len(checks)==6 and all(checks.values()), 'checks': checks}
    path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    node.destroy_node();rclpy.shutdown()
if not report['passed']:
    raise SystemExit(1)
