"""Interactive native viewer for the successful experimental six-destination setup."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent


def stop_child(child):
    if child.poll() is None:
        os.killpg(child.pid, signal.SIGINT)
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke-test', action='store_true')
    args = parser.parse_args()
    folder = ROOT / 'artifacts/latest-run' / datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True)
    course = ROOT / 'artifacts/courses/seed-2027'
    with (folder / 'rviz.log').open('w') as log:
        rviz = subprocess.Popen(
            ['rviz2', '-d', str(ROOT / 'ros2/src/igvc_sim_bridge/rviz/nav.rviz'),
             '--ros-args', '-p', 'use_sim_time:=true'], stdout=log,
            stderr=subprocess.STDOUT, start_new_session=True)
        try:
            time.sleep(8)
            if rviz.poll() is not None:
                raise RuntimeError(f'RViz exited; inspect {folder / "rviz.log"}')
            if args.smoke_test:
                # Verify live transport, not only a surviving GUI process.
                import rclpy
                from sensor_msgs.msg import Image
                from nav_msgs.msg import Odometry
                rclpy.init()
                node = rclpy.create_node('latest_shortcut_smoke_test')
                seen = set()
                subscriptions = [node.create_subscription(kind, topic,
                    lambda msg, key=topic: seen.add(key), 10)
                    for kind, topic in [(Odometry, '/odom'), (Image, '/camera/color/image_raw')]]
                deadline = time.monotonic() + 20
                while len(seen) < 2 and time.monotonic() < deadline:
                    rclpy.spin_once(node, timeout_sec=0.2)
                node.destroy_node()
                rclpy.shutdown()
                if len(seen) != 2:
                    raise RuntimeError(f'Missing live sensor messages; received {sorted(seen)}')
                print(f'RViz stayed open and live odometry/RGB arrived. Logs: {folder}', flush=True)
                return
            print('\nSeed 2027 | checked-path/RPP | 0.6 m/s | body clearance weight 3')
            print('Fresh simulation using the successful configuration, not a recorded replay.')
            print('RViz: Move Camera tool; left-drag orbit, middle-drag pan, wheel zoom.')
            answer = input('Press Enter to start the lap, or Q then Enter to close: ').strip().lower()
            if answer != 'q':
                mission = subprocess.Popen([
                    sys.executable, str(ROOT / 'tools/sensor_course.py'),
                    '--mission', str(course / 'autonomy.json'), '--report', str(folder / 'run.json'),
                    '--capture-dir', str(folder / 'decisions'), '--timeout', '600', '--speed', '0.6',
                    '--planning-budget', '0.5', '--path-execution', 'checked-path',
                    '--body-clearance-weight', '3'], start_new_session=True)
                try:
                    result = mission.wait()
                finally:
                    stop_child(mission)
                print(f'Mission exit: {result}. Results: {folder}')
                if (folder / 'run.json').exists():
                    subprocess.run([sys.executable, str(ROOT / 'tools/audit_sensor_run.py'),
                        '--run', str(folder / 'run.json'), '--course', str(course / 'course.json'),
                        '--mission', str(course / 'autonomy.json'), '--output', str(folder / 'audit.json')],
                        check=False)
                input('Press Enter to close Unity and RViz: ')
        finally:
            stop_child(rviz)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nClosing this viewer session.', flush=True)
