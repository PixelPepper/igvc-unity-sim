"""Stop and pause owned course, then save its exact pose/clock for a rebuild."""
import json
from pathlib import Path
import re
import time
import math
import rclpy
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from std_srvs.srv import SetBool
rclpy.init();n=rclpy.create_node('igvc_save_checkpoint');state={}
def odom(m):
    p=m.pose.pose.position;q=m.pose.pose.orientation
    state.update(x=p.x,y=p.y,yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))
def status(m):
    match=re.search(r'run=(\d+)',m.data)
    if match:state['run_id']=int(match[1])
n.create_subscription(Odometry,'/odom',odom,10)
n.create_subscription(Clock,'/clock',lambda m:state.update(sim_time=m.clock.sec+m.clock.nanosec*1e-9),10)
n.create_subscription(String,'/sim/status',status,10)
def spin(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.03)
def call(name,value):
    c=n.create_client(SetBool,name)
    if not c.wait_for_service(timeout_sec=5):raise RuntimeError('Service unavailable: '+name)
    f=c.call_async(SetBool.Request(data=value));rclpy.spin_until_future_complete(n,f,timeout_sec=5)
    if not f.done() or not f.result().success:raise RuntimeError('Service failed: '+name)
try:
    spin(2);call('/sim/set_autonomy',False);spin(.5);call('/sim/pause',True);spin(1)
    if len(state)!=5:raise RuntimeError('Missing checkpoint fields')
    path=Path(__file__).resolve().parents[1]/'artifacts/checks/stopped-course-checkpoint.json'
    path.write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
finally:n.destroy_node();rclpy.shutdown()
