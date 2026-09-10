"""Own exactly one background ROS launch process group in WSL."""
import json
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path(__file__).resolve().parent.parent
action = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else 'probe'
session_name = mode if mode in ('nav', 'perception') else 'ros'
state = root / f'artifacts/session/{session_name}.json'
state.parent.mkdir(parents=True, exist_ok=True)
# All modes share ownership/exclusivity checks; serialize across terminals.
session_lock = (state.parent / 'ros-session.lock').open('a')
fcntl.flock(session_lock, fcntl.LOCK_EX)
log = root / f'artifacts/logs/{session_name}-session.log'
log.parent.mkdir(parents=True, exist_ok=True)


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
        return fields[19] if fields[0] != 'Z' else None
    except FileNotFoundError:
        return None


def running():
    if not state.exists():
        return None
    item = json.loads(state.read_text())
    current = identity(item['pid'])
    return item if current == item['start'] or (current is None and group_running(item['pid'])) else None


def group_running(pgid):
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().split(') ', 1)[1].split()
            if fields[0] != 'Z' and int(fields[2]) == pgid:
                return True
        except (FileNotFoundError, ProcessLookupError):
            continue
    return False


if mode not in ('probe', 'r3a', 'nav', 'perception'):
    raise SystemExit('Expected probe, r3a, nav, or perception session mode')
item = running()
if action == 'start':
    if mode in ('nav', 'perception'):
        sim_state = root / 'artifacts/session/ros.json'
        sim = json.loads(sim_state.read_text()) if sim_state.exists() else {}
        if sim.get('mode') != 'r3a' or identity(sim.get('pid', -1)) != sim.get('start'):
            raise SystemExit('Start the R3-a simulator before navigation or perception')
        other_mode = 'perception' if mode == 'nav' else 'nav'
        other_state = root / f'artifacts/session/{other_mode}.json'
        other = json.loads(other_state.read_text()) if other_state.exists() else {}
        if other.get('start') is not None and (identity(other.get('pid', -1)) == other['start'] or group_running(other.get('pid', -1))):
            raise SystemExit(f'Stop the managed {other_mode} session first; both launch perception publishers')
    if item:
        if item.get('mode', 'probe') != mode:
            raise SystemExit('Another simulator mode is running; stop it before switching')
        print(f"ROS already running: PID {item['pid']}")
        sys.exit(0)
    package, launch_file = {
        'nav': ('igvc_navigation', 'local_navigation.launch.py'),
        'perception': ('igvc_perception', 'perception.launch.py'),
    }.get(mode, ('igvc_sim_bridge', mode + '.launch.py'))
    with log.open('w') as output:
        child = subprocess.Popen(['bash', str(root / 'tools/run_ros.sh'), 'ros2', 'launch',
                                  package, launch_file],
                                 stdout=output, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
    state.write_text(json.dumps({'pid': child.pid, 'start': identity(child.pid), 'mode': mode}))
    time.sleep(2)
    if child.poll() is not None:
        raise SystemExit(f'ROS launch exited; inspect {log}')
    print(f'ROS started: PID {child.pid}')
elif action == 'stop':
    if item:
        for sig, wait in ((signal.SIGINT, 8), (signal.SIGTERM, 3)):
            if not group_running(item['pid']):
                break
            try:
                os.killpg(item['pid'], sig)
            except ProcessLookupError:
                break
            deadline = time.monotonic() + wait
            while group_running(item['pid']) and time.monotonic() < deadline:
                time.sleep(0.1)
        if group_running(item['pid']):
            raise SystemExit('ROS group still running; ownership retained. Inspect session log before retrying.')
        print('ROS session stopped')
    else:
        print('No managed ROS session')
    state.unlink(missing_ok=True)
elif action == 'status':
    print(f"ROS launch running: PID {item['pid']}" if item else 'ROS launch stopped')
else:
    raise SystemExit('Expected start, stop, or status')
