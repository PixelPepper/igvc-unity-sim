"""Bounded Linux scheduler/clock evidence independent of ROS callbacks."""
import argparse
import json
import time
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--duration',type=float,default=60);p.add_argument('--report',type=Path,required=True)
a=p.parse_args()
if not 5<=a.duration<=180:p.error('duration must be 5..180 seconds')
start=time.monotonic();previous=start;raw=time.clock_gettime(time.CLOCK_MONOTONIC_RAW);wall=time.time()
events=[];maximum=0;count=0
while time.monotonic()-start<a.duration:
    time.sleep(.02)
    now=time.monotonic();r=time.clock_gettime(time.CLOCK_MONOTONIC_RAW);w=time.time()
    dt=now-previous;maximum=max(maximum,dt);count+=1
    if dt>.1 or abs((w-wall)-dt)>.05:events.append(dict(elapsed=now-start,unix=w,monotonic_gap=dt,raw_gap=r-raw,wall_gap=w-wall))
    previous=now;raw=r;wall=w
result=dict(duration=time.monotonic()-start,samples=count,max_gap=maximum,gaps=events)
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
