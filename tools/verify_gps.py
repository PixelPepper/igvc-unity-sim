#!/usr/bin/env python3
"""Read-only GPS/odometry correspondence and mission endpoint snapshot."""
import json
import math
from pathlib import Path
import time
import rclpy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import String, Bool
from rclpy.qos import QoSProfile, DurabilityPolicy
from igvc_gps.geodesy import LocalFrame

root = Path(__file__).resolve().parents[1]
origin = json.loads((root/'ros2/src/igvc_gps/config/origin.json').read_text())
frame = LocalFrame(origin)
rclpy.init(); n = rclpy.create_node('igvc_gps_verifier')
odoms = {}; fixes = []; state = {}
def stamp(m): return (m.header.stamp.sec, m.header.stamp.nanosec)
def odom(m):
    odoms[stamp(m)] = m
    state['pose'] = [m.pose.pose.position.x, m.pose.pose.position.y]
    state['speed'] = [m.twist.twist.linear.x, m.twist.twist.angular.z]
n.create_subscription(Odometry, '/odom', odom, 100)
n.create_subscription(NavSatFix, '/gps/fix', fixes.append, 100)
n.create_subscription(String, '/sim/status', lambda m: state.update(sim_status=m.data), 10)
n.create_subscription(Bool, '/sim/autonomy_enabled', lambda m: state.update(autonomy=m.data), QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
end = time.monotonic()+6
while time.monotonic()<end: rclpy.spin_once(n, timeout_sec=.05)
errors=[]
for m in fixes:
    if stamp(m) in odoms:
        p=odoms[stamp(m)].pose.pose.position
        errors.append(math.dist(frame.to_enu(m.latitude,m.longitude,m.altitude),(p.x,p.y,p.z)))
checks={'matching_acquisition_stamps':len(errors)>20, 'ideal_gps_matches_odom':bool(errors) and max(errors)<1e-5,
        'valid_gps_frame':bool(fixes) and all(m.header.frame_id=='gps_link' and m.status.status>=0 for m in fixes),
        'six_metre_endpoint':math.dist(state.get('pose',[999,999]),[6,0])<.25,
        'manual_and_stationary':state.get('autonomy') is False and max(map(abs,state.get('speed',[999])))<.005}
report={'status':'passed' if all(checks.values()) else 'failed','checks':checks,'fix_count':len(fixes),'matched_count':len(errors),'max_enu_error_m':max(errors,default=None),'state':state}
(root/'artifacts/checks/gps-live.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report)); n.destroy_node(); rclpy.shutdown()
if report['status']!='passed': raise SystemExit(1)
