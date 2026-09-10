#!/usr/bin/env python3
"""Briefly suspend this session's lane detector to test fail-closed authority."""
import json
import argparse
import os
from pathlib import Path
import signal
import time
import rclpy
from std_msgs.msg import Bool
from verify_navigation import Verify

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sensor',choices=('lanes','depth'),default='lanes')
args=parser.parse_args()
executable='depth_processor' if args.sensor=='depth' else 'lane_detector'
session=json.loads((root/'artifacts/session/nav.json').read_text())
pid=session['pid']
candidates=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit(): continue
    try:
        cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ')
        if ('/igvc_perception/'+executable+' ').encode() in cmd and os.getpgid(int(p.name))==pid:
            candidates.append(int(p.name))
    except (OSError, ProcessLookupError): pass
if len(candidates)!=1: raise RuntimeError('Expected one owned '+executable)
lane_pid=candidates[0]
rclpy.init(); v=Verify(); mode=[None]
health={'lanes':0.,'depth':0.}
v.node.create_subscription(Bool,'/perception/lanes/valid',lambda m:health.update(lanes=time.monotonic()) if m.data else None,10)
v.node.create_subscription(Bool,'/perception/depth/healthy',lambda m:health.update(depth=time.monotonic()) if m.data else None,10)
v.node.create_subscription(Bool,'/sim/autonomy_enabled',lambda m: mode.__setitem__(0,m.data),10)
report={'status':'failed','checks':{}}
try:
    deadline=time.monotonic()+25
    while time.monotonic()<deadline and not all(time.monotonic()-t<.5 for t in health.values()):v.wait(.1)
    if not all(time.monotonic()-t<.5 for t in health.values()):raise RuntimeError('Perception did not become ready')
    v.service('gate',True); v.wait(.2)
    report['checks']['fresh_perception_allows_enable']=mode[0] is True
    os.kill(lane_pid,signal.SIGSTOP)
    v.wait(1.5)
    report['checks']['stale_'+args.sensor+'_latches_manual']=mode[0] is False and v.stopped()
    if args.sensor=='depth':
        report['checks']['depth_loss_invalidates_lane_projection']=time.monotonic()-health['lanes']>.75
    os.kill(lane_pid,signal.SIGCONT)
    v.wait(2)
    report['checks']['recovery_does_not_rearm']=mode[0] is False and v.stopped()
    if args.sensor=='depth':
        report['checks']['fresh_ground_restores_lane_projection']=time.monotonic()-health['lanes']<.5
    report['status']='passed' if all(report['checks'].values()) else 'failed'
finally:
    os.kill(lane_pid,signal.SIGCONT)
    v.service('gate',False)
    (root/('artifacts/checks/'+('depth' if args.sensor=='depth' else 'lane')+'-watchdog-live.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report)); v.node.destroy_node(); rclpy.shutdown()
if report['status']!='passed':raise SystemExit(1)
