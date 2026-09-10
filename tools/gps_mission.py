"""Editable synthetic WGS84 missions. Run inside sourced ROS 2 for live execution."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

PACKAGE = Path(__file__).resolve().parents[1] / 'ros2/src/igvc_gps'
sys.path.insert(0, str(PACKAGE))
from igvc_gps.geodesy import LocalFrame


def read_mission(path, origin):
    mission = json.loads(Path(path).read_text())
    if mission['origin'] != origin:
        raise ValueError('Mission origin differs from configured GPS origin')
    frame = LocalFrame(origin)
    points = []
    for p in mission['waypoints']:
        x, y, z = frame.to_enu(p['latitude'], p['longitude'], p['altitude'])
        yaw = p['yaw']
        if not isinstance(p['name'], str) or not p['name'] or not math.isfinite(yaw):
            raise ValueError('Named waypoint and finite yaw required')
        if math.hypot(x, y) > 100 or abs(z) > 1:
            raise ValueError('Demo mission limited to 100 m horizontally and 1 m vertically from origin')
        points.append((p['name'], x, y, yaw))
    if not 1 <= len(points) <= 200:
        raise ValueError('Mission requires 1 to 200 waypoints')
    return points


def run(points, origin, timeout):
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.signals import SignalHandlerOptions
    from rclpy.qos import QoSProfile, DurabilityPolicy
    from sensor_msgs.msg import NavSatFix
    from std_msgs.msg import String, Bool
    from std_srvs.srv import SetBool
    from nav2_msgs.action import NavigateToPose

    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('igvc_gps_mission')
    gate = node.create_client(SetBool, '/sim/set_autonomy')
    client = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    state = {'fix_time': 0., 'stamp': None, 'origin': None, 'enabled': None,
             'armed': False, 'takeover': False}
    handle = None
    gate_requested = False

    def fix_cb(msg):
        stamp = (msg.header.stamp.sec, msg.header.stamp.nanosec)
        if (msg.status.status >= 0 and msg.header.frame_id == 'gps_link'
                and all(math.isfinite(v) for v in (msg.latitude, msg.longitude, msg.altitude))
                and stamp != state['stamp']):
            if state['stamp'] is not None and stamp < state['stamp'] and state['armed']:
                state['takeover'] = True  # Reset/time reversal invalidates this mission.
            state['stamp'], state['fix_time'] = stamp, time.monotonic()

    def origin_cb(msg):
        try:
            state['origin'] = json.loads(msg.data)
        except ValueError:
            state['origin'] = None

    def enabled_cb(msg):
        state['enabled'] = msg.data
        if gate_requested and msg.data:
            state['armed'] = True
        if state['armed'] and not msg.data:
            state['takeover'] = True

    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(NavSatFix, '/gps/fix', fix_cb, 10)
    node.create_subscription(String, '/gps/origin', origin_cb, qos)
    node.create_subscription(Bool, '/sim/autonomy_enabled', enabled_cb, qos)

    def healthy():
        if state['takeover']:
            raise RuntimeError('Manual takeover, safety stop or simulation reset: mission terminated; no automatic resume')
        if time.monotonic() - state['fix_time'] > 3:
            raise RuntimeError('GPS stale for more than 3 seconds; mission canceled')
        if state['origin'] != origin:
            raise RuntimeError('Published GPS origin does not match mission origin')

    def wait(future, seconds, monitor=False):
        end = time.monotonic() + seconds
        while not future.done() and time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.05)
            if monitor:
                healthy()
        if not future.done():
            raise RuntimeError('ROS operation exceeded wall-time deadline')
        return future.result()

    try:
        end = time.monotonic() + 20
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.1)
            if (gate.service_is_ready() and client.server_is_ready()
                    and state['enabled'] is not None and state['origin'] == origin
                    and time.monotonic() - state['fix_time'] < 3):
                break
        else:
            raise RuntimeError('GPS, matching origin, autonomy state, gate or Nav2 unavailable after 20 seconds')
        if state['enabled']:
            raise RuntimeError('Autonomy already active; cancel the existing task before starting a mission')
        # Allow endpoint registrations to settle after all streams arrive.
        end = time.monotonic() + 1
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.05)
        healthy()
        for name, x, y, yaw in points:
            healthy()
            goal = NavigateToPose.Goal()
            goal.pose.header.frame_id = 'odom'
            goal.pose.pose.position.x, goal.pose.pose.position.y = x, y
            goal.pose.pose.orientation.z = math.sin(yaw / 2)
            goal.pose.pose.orientation.w = math.cos(yaw / 2)
            handle = wait(client.send_goal_async(goal), 10, True)
            if not handle.accepted:
                raise RuntimeError('Nav2 rejected waypoint ' + name)
            if not state['armed']:
                gate_requested = True
                response = wait(gate.call_async(SetBool.Request(data=True)), 5, True)
                if not response.success:
                    raise RuntimeError('Autonomy gate refused: ' + response.message)
                end = time.monotonic() + 3
                while state['enabled'] is not True and time.monotonic() < end:
                    rclpy.spin_once(node, timeout_sec=.05)
                    healthy()
                if state['enabled'] is not True:
                    raise RuntimeError('No autonomy-enabled confirmation')
                healthy()
                state['armed'] = True
            print(f'{name}: odom ({x:.3f}, {y:.3f}), yaw {yaw:.3f}', flush=True)
            result = wait(handle.get_result_async(), timeout, True)
            healthy()
            if result.status != 4:
                raise RuntimeError(f'Waypoint {name} failed with action status {result.status}')
            handle = None
        print('Mission succeeded', flush=True)
    finally:
        # Disable first so cleanup does not depend on Nav2 cancellation latency.
        if gate_requested and gate.service_is_ready():
            try:
                wait(gate.call_async(SetBool.Request(data=False)), 3)
            except Exception as exc:
                print('Gate cleanup failed: ' + str(exc), file=sys.stderr)
        if handle is not None and handle.accepted:
            try:
                wait(handle.cancel_goal_async(), 3)
            except Exception as exc:
                print('Goal cancellation failed: ' + str(exc), file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'list', 'run'])
    parser.add_argument('mission', type=Path)
    parser.add_argument('--origin', type=Path, default=PACKAGE / 'config/origin.json')
    parser.add_argument('--goal-timeout', type=float, default=90.)
    args = parser.parse_args()
    if not math.isfinite(args.goal_timeout) or not 1 <= args.goal_timeout <= 300:
        parser.error('Goal timeout must be 1 to 300 seconds')
    origin = json.loads(args.origin.read_text())
    if args.command == 'init':
        frame = LocalFrame(origin)
        points = []
        for x in (2., 4., 6.):
            lat, lon, alt = frame.to_geodetic(x, 0., 0.)
            points.append(dict(name=f'forward_{int(x)}m', latitude=lat, longitude=lon, altitude=alt, yaw=0.))
        with args.mission.open('x') as out:
            json.dump(dict(origin=origin, note='Editable geometric demo; requires live lane and obstacle qualification.', waypoints=points), out, indent=2)
    points = read_mission(args.mission, origin)
    if args.command == 'run':
        if 'route' in json.loads(args.mission.read_text()):
            raise ValueError('Audited full-loop missions require tools/igvc.ps1 loop-run; GPS preview is available with list')
        run(points, origin, args.goal_timeout)
    else:
        for name, x, y, yaw in points:
            print(f'{name}: east={x:.6f} north={y:.6f} yaw={yaw:.6f}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Mission interrupted; cleanup requested', file=sys.stderr)
        sys.exit(130)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
