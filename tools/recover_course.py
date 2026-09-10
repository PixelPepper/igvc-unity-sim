"""Explicit bounded Nav2 backup for a paused full-course observer; never skips goals."""
import rclpy
from rclpy.action import ActionClient
from nav2_msgs.action import BackUp
from std_srvs.srv import SetBool
from pathlib import Path
import json
import time
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--distance',type=float,default=.3)
args=parser.parse_args()
if not 0<args.distance<=.5:parser.error('Recovery is limited to 0.5 m')
root=Path(__file__).resolve().parents[1]
report=json.loads((root/'artifacts/checks/full-course-live.json').read_text())
if report['status']!='paused' or report.get('audit_error'):raise RuntimeError('Requires paused valid full-course observer')
rclpy.init();node=rclpy.create_node('igvc_explicit_backup');gate=node.create_client(SetBool,'/sim/set_autonomy')
action=ActionClient(node,BackUp,'/backup');handle=None
def wait(f,timeout):
    rclpy.spin_until_future_complete(node,f,timeout_sec=timeout)
    if not f.done():raise RuntimeError('ROS operation timeout')
    return f.result()
try:
    if not gate.wait_for_service(timeout_sec=5) or not action.wait_for_server(timeout_sec=5):raise RuntimeError('Recovery unavailable')
    result=wait(gate.call_async(SetBool.Request(data=True)),5)
    if not result.success:raise RuntimeError(result.message)
    goal=BackUp.Goal();goal.target.x=-args.distance;goal.speed=.1;goal.time_allowance.sec=12
    handle=wait(action.send_goal_async(goal),5)
    if not handle.accepted:raise RuntimeError('Backup rejected')
    result=wait(handle.get_result_async(),15)
    record={'wall':time.time(),'waypoint':report['active_waypoint'],'requested_backup_m':args.distance,'action_status':result.status}
    with (root/'artifacts/checks/explicit-recoveries.jsonl').open('a') as out:out.write(json.dumps(record)+'\n')
    print(json.dumps(record))
    if result.status!=4:raise RuntimeError('Collision-checked backup failed')
finally:
    wait(gate.call_async(SetBool.Request(data=False)),5)
    if handle is not None and handle.accepted:wait(handle.cancel_goal_async(),5)
    node.destroy_node();rclpy.shutdown()
