#!/usr/bin/env python3
"""Motion-producing course boundary check. Resets the robot before and after."""
import json
import math
import re
import time
from pathlib import Path
import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from verify_navigation import Verify, yaw

rclpy.init()
v = Verify()
status = ['']
v.node.create_subscription(String, '/sim/status', lambda m: status.__setitem__(0, m.data), 10)
report = {'status': 'failed', 'checks': {}}

def drive(seconds, speed=0., turn=0.):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if time.monotonic() - v.last_odom > 1:
            raise RuntimeError('Lost odometry')
        msg = Twist(); msg.linear.x = speed; msg.angular.z = turn
        v.teleop.publish(msg)
        v.wait(.04)

try:
    v.wait(3)
    v.reset()
    end = time.monotonic() + 8
    while yaw(v.odom.pose.pose.orientation) < math.pi/2-.025:
        if time.monotonic() > end: raise RuntimeError('Turn timeout')
        drive(.04, turn=.4)
    drive(.5)
    report['heading'] = yaw(v.odom.pose.pose.orientation)
    drive(5, speed=.8)
    p = v.xy()
    drive(1, speed=.8)
    q = v.xy()
    report['blocked_pose'] = list(q)
    report['status_text'] = status[0]
    match = re.search(r'line_blocks=(\d+)', status[0])
    report['checks']['guard_engaged'] = bool(match and int(match.group(1)) > 0)
    report['checks']['continued_command_cannot_cross'] = math.dist(p, q) < .01 and v.stopped()
    drive(1, speed=-.4)
    report['checks']['can_reverse_away'] = math.dist(q, v.xy()) > .2
    report['status'] = 'passed' if all(report['checks'].values()) else 'failed'
finally:
    v.teleop.publish(Twist())
    v.reset()
    (Path(__file__).resolve().parents[1]/'artifacts/checks/lane-guard-live.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
    v.node.destroy_node(); rclpy.shutdown()
if report['status'] != 'passed': raise SystemExit(1)
