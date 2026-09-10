"""Bounded read-only capture of observations surrounding an autonomy stop."""
import argparse
from collections import deque
import json
from pathlib import Path
import time
import cv2
import numpy as np
import rclpy
from std_msgs.msg import Bool, String
from sensor_msgs.msg import Image

p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,required=True)
p.add_argument('--duration',type=float,default=120)
args=p.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
rclpy.init()
n=rclpy.create_node('igvc_perception_stop_trace')
events=deque(maxlen=150)
frames=deque(maxlen=12)
state={'enabled':False,'stop':None}
start=time.monotonic()
def status(m):events.append({'wall':time.monotonic()-start,'status':json.loads(m.data)})
def frame(m):
    rgb=np.frombuffer(m.data,np.uint8).reshape(m.height,m.step)[:,:m.width*3].reshape(m.height,m.width,3).copy()
    frames.append((m.header.stamp.sec+m.header.stamp.nanosec*1e-9,rgb))
def enabled(m):
    # Zone handoffs deliberately close the gate with healthy paint; retain only
    # edges preceded by invalid observations for this perception investigation.
    recent_invalid=any(not e['status'].get('valid',False) and time.monotonic()-start-e['wall']<1 for e in events)
    if state['enabled'] and not m.data and state['stop'] is None and recent_invalid:
        state['stop']=time.monotonic()
        (args.output/'before-stop.json').write_text(json.dumps(list(events),indent=2))
        for i,(stamp,rgb) in enumerate(frames):cv2.imwrite(str(args.output/f'frame-{i:02d}-{stamp:.2f}.png'),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        print('Captured autonomy falling edge',flush=True)
    state['enabled']=m.data
n.create_subscription(String,'/perception/lanes/status',status,10)
n.create_subscription(Image,'/camera/color/image_raw',frame,1)
n.create_subscription(Bool,'/sim/autonomy_enabled',enabled,10)
try:
    while time.monotonic()-start<args.duration:
        rclpy.spin_once(n,timeout_sec=.03)
        if state['stop'] and time.monotonic()-state['stop']>2:break
finally:
    (args.output/'trace.json').write_text(json.dumps(list(events),indent=2))
    n.destroy_node();rclpy.shutdown()
