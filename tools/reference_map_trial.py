#!/usr/bin/env python3
"""One bounded, diagnostic sensor-led trial on the reference-map drive player (T-0090).

Run inside the ROS environment AFTER tools/reference-map.ps1 has started the player and its own managed r3a
session (the launcher owns those and the simulator locks). This driver owns only what it starts here: the
managed navigation session and the UNCHANGED tools/sensor_course.py mission child.

Order: refuse an existing nav session -> autonomy gate off + pose reset -> sensor smoke (clock, RGB, depth,
lidar, odom actually received; first RGB saved) -> profile + nav start -> clock admission (use_sim_time on every
perception node) -> mission child with speed <= 0.6 m/s and timeout <= 180 s -> gate off -> nav stop.
Motion is refused without a positive clock and all four sensor streams. No retry. Every outcome is written to
<run>/trial-report.json; the exit code is 0 only when the mission child exited 0 and cleanup was confirmed.
This is diagnostic progress/health evidence only: there is no full-lap audit for this map.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))

MAX_SPEED = .6
MAX_TIMEOUT = 180.
SMOKE_TOPICS = ('/clock', '/camera/color/image_raw', '/camera/depth/image_raw', '/scan', '/odom')


def bounded_settings(speed, timeout):
    """Validated fixed trial bounds; anything outside them is refused, never clamped."""
    for value in (speed, timeout):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Speed and timeout must be finite numbers')
    if not 0 < speed <= MAX_SPEED:
        raise ValueError(f'Speed must be within (0, {MAX_SPEED}] m/s')
    if not 0 < timeout <= MAX_TIMEOUT:
        raise ValueError(f'Timeout must be within (0, {MAX_TIMEOUT}] s')
    return dict(speed_mps=float(speed)), float(timeout)


def mission_command(python, mission, folder, settings, timeout):
    """sandbox_profile.mission_argv with the trial's own --timeout (the default 600 s is replaced)."""
    from sandbox_profile import mission_argv
    argv = mission_argv(python, mission, folder, settings)
    index = argv.index('--timeout')
    argv[index+1] = str(int(math.ceil(timeout)))
    return argv


def evaluate_smoke(counts, latest_clock_ns):
    """Motion is allowed only with a positive simulation clock and every stream actually received."""
    missing = [topic for topic in SMOKE_TOPICS if counts.get(topic, 0) < 1]
    ok = not missing and isinstance(latest_clock_ns, int) and latest_clock_ns > 0
    return dict(ok=ok, missing=missing, latest_clock_ns=latest_clock_ns, counts=dict(counts))


def evaluate_admission(evidence, nodes):
    """Same rule as sandbox_session.admit_clock: exactly Boolean true use_sim_time on every node."""
    if not isinstance(evidence, dict) or not isinstance(evidence.get('nodes'), list):
        return False
    observed = {item.get('node'): item for item in evidence['nodes'] if isinstance(item, dict)}
    return evidence.get('admitted') is True and all(
        observed.get(name, {}).get('status') == 'true' and observed[name].get('value') is True for name in nodes)


def write(path, data):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data, indent=2, default=str)+'\n')
    os.replace(temporary, path)


def sensor_smoke(folder, wait_s=20.):
    """Subscribe read-only; count messages, keep the newest clock, save the first RGB frame."""
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import Image, LaserScan
    from nav_msgs.msg import Odometry
    import numpy as np
    counts = {topic: 0 for topic in SMOKE_TOPICS}; clock = {'ns': None}; first = {}
    node = rclpy.create_node('reference_map_trial_smoke')

    def counter(topic):
        def callback(msg):
            counts[topic] += 1
            if topic == '/clock':
                clock['ns'] = msg.clock.sec*1_000_000_000+msg.clock.nanosec
            if topic == '/camera/color/image_raw' and 'rgb' not in first:
                first['rgb'] = msg
        return callback
    types = {'/clock': Clock, '/camera/color/image_raw': Image, '/camera/depth/image_raw': Image, '/scan': LaserScan, '/odom': Odometry}
    for topic, kind in types.items():
        node.create_subscription(kind, topic, counter(topic), qos_profile_sensor_data if topic != '/odom' else 10)
    deadline = time.monotonic()+wait_s
    while time.monotonic() < deadline and evaluate_smoke(counts, clock['ns'])['missing']:
        rclpy.spin_once(node, timeout_sec=.1)
    for _ in range(10):
        rclpy.spin_once(node, timeout_sec=.05)
    result = evaluate_smoke(counts, clock['ns'])
    if 'rgb' in first:
        msg = first['rgb']
        rgb = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)[:, :msg.width*3].reshape(msg.height, msg.width, 3)
        import cv2
        path = folder/'first-rgb.png'
        cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        result['first_rgb'] = str(path)
    node.destroy_node()
    return result


def nav(action, profile=None):
    argv = [sys.executable, str(ROOT/'tools/ros_session.py'), action, 'nav']+(['--params-file', str(profile)] if profile else [])
    result = subprocess.run(argv, capture_output=True, text=True, timeout=35)
    return result.returncode, (result.stdout+result.stderr)[-800:]


def stop_child(child, log):
    """SIGINT to the mission's own process group, then bounded SIGTERM/SIGKILL; confirm it is reaped."""
    for sig, wait in ((signal.SIGINT, 15), (signal.SIGTERM, 5), (signal.SIGKILL, 5)):
        if child.poll() is not None:
            break
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            break
        log.append(f'sent {sig.name} to mission group {child.pid}')
        try:
            child.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            continue
    return child.poll() is not None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--mission', type=Path, required=True)
    parser.add_argument('--speed', type=float, default=MAX_SPEED)
    parser.add_argument('--timeout', type=float, default=MAX_TIMEOUT)
    args = parser.parse_args(argv)
    settings, timeout = bounded_settings(args.speed, args.timeout)
    folder = args.run_dir.resolve(); folder.mkdir(parents=True, exist_ok=True)
    report = dict(task='T-0090', kind='diagnostic sensor-led trial (no full-lap audit)', settings=settings, timeout_s=timeout,
                  mission=str(args.mission), mission_sha256=hashlib.sha256(args.mission.read_bytes()).hexdigest(),
                  started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), log=[])
    from sandbox_session import CLOCK_NODES, RosControl, session_dir
    from sandbox_profile import build_profile
    import yaml
    from sensor_course import destinations
    destinations(json.loads(args.mission.read_text()))   # sanitized schema only
    nav_owned = False; child = None; exit_code = 1; cleanup_ok = True
    if (session_dir(ROOT)/'nav.json').exists():
        report['refused'] = 'an existing managed navigation session is present; it is never claimed'
        write(folder/'trial-report.json', report); return 2
    ros = RosControl()
    try:
        ros.disable(); ros.reset_pose(); report['log'].append('autonomy gate off; pose reset')
        smoke = sensor_smoke(folder); report['sensor_smoke'] = smoke; write(folder/'sensor-smoke.json', smoke)
        if not smoke['ok']:
            report['refused'] = 'sensor smoke failed: no motion'
            return 2
        profile, baseline = build_profile(settings)
        profile_path = folder/'profile.yaml'; profile_path.write_text(yaml.safe_dump(profile, sort_keys=False))
        report['profile'] = dict(path=str(profile_path), baseline=str(baseline))
        try:
            code, output = nav('start', profile_path)
        except (subprocess.TimeoutExpired, OSError) as exc:
            code, output = -1, type(exc).__name__+': '+str(exc)
        report['nav_start'] = dict(code=code, output=output)
        state = session_dir(ROOT)/'nav.json'
        receipt = code == 0 and 'ROS started: PID' in output
        if receipt:
            nav_owned = True   # only a fresh-start receipt from this call establishes ownership
            report['nav_owned_state'] = json.loads(state.read_text()) if state.exists() else None
        else:
            if state.exists():
                # Unreceipted group (failed/timed-out start or 'already running'): never claimed or stopped here;
                # exit 3 makes the launcher hold its locks for root.
                cleanup_ok = False
                report['nav_unreceipted_state'] = json.loads(state.read_text())
                report['log'].append('navigation state present without a fresh-start receipt; not stopped; root must inspect')
            report['refused'] = 'navigation did not start with a fresh-start receipt'
            return 2
        try:
            evidence = ros.verify_sim_time()
        except Exception as exc:   # record the failure itself; never fabricate admission
            evidence = dict(admitted=False, nodes=[], error=type(exc).__name__+': '+str(exc))
        evidence['admitted'] = evaluate_admission(evidence, CLOCK_NODES)
        write(folder/'clock-admission.json', evidence); report['clock_admitted'] = evidence['admitted']
        if not evidence['admitted']:
            report['refused'] = 'clock admission failed: no motion'
            return 2
        argv_mission = mission_command(sys.executable, args.mission.resolve(), folder, settings, timeout)
        report['mission_argv'] = argv_mission
        with (folder/'mission.log').open('w') as log:
            child = subprocess.Popen(argv_mission, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        report['mission_pid'] = child.pid
        try:
            exit_code = child.wait(timeout=timeout+30)
        except subprocess.TimeoutExpired:
            report['log'].append('mission exceeded its bound; cancelling')
            if not stop_child(child, report['log']):
                cleanup_ok = False
            exit_code = 124
        report['mission_exit'] = exit_code
        return 0 if exit_code == 0 else 1
    finally:
        if child is not None and child.poll() is None and not stop_child(child, report['log']):
            cleanup_ok = False
        try:
            ros.disable(); report['log'].append('autonomy gate off before navigation stop')
        except Exception as exc:
            cleanup_ok = False; report['log'].append('gate disable failed: '+str(exc))
        if nav_owned:
            try:
                code, output = nav('stop')
            except (subprocess.TimeoutExpired, OSError) as exc:
                code, output = -1, type(exc).__name__+': '+str(exc)
            report['nav_stop'] = dict(code=code, output=output)
            if code != 0:
                cleanup_ok = False
        tail_failed = False
        try:
            ros.close()
        except Exception as exc:   # conservative: an unclean shutdown must not look like an ordinary failure
            tail_failed = True; report['log'].append('ros close failed: '+str(exc))
        try:
            report['cleanup_confirmed'] = cleanup_ok and not tail_failed
            report['run_report'] = str(folder/'run.json') if (folder/'run.json').exists() else None
            report['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            write(folder/'trial-report.json', report)
        except Exception:
            tail_failed = True
        if not cleanup_ok or tail_failed:
            print('CLEANUP NOT CONFIRMED: launcher must keep its locks for root; inspect trial-report.json', file=sys.stderr)
            os._exit(3)


if __name__ == '__main__':
    raise SystemExit(main())
