"""Run one bounded mission with a read-only acquisition recorder in the same ROS environment."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys


def finish(child, grace):
    if child.poll() is None:
        os.killpg(child.pid, signal.SIGINT)
    try:
        return child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            return child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            return child.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('job', type=Path)
    args = parser.parse_args()
    script = args.workspace/'tools'
    record = [sys.executable, str(script/'record_navigation_episode.py'),
              '--output', str(args.job/'episode'), '--duration', '660', '--image-hz', '2']
    mission = [sys.executable, str(script/'sensor_course.py'),
               '--mission', str(args.workspace/'artifacts/courses/seed-2027/autonomy.json'),
               '--report', str(args.job/'run.json'), '--capture-dir', str(args.job/'decisions'),
               '--timeout', '600', '--speed', '0.6', '--planning-budget', '0.5',
               '--path-execution', 'checked-path']
    result = {'mission_exit': None, 'recorder_exit': None, 'mission_timed_out': False}
    running = None
    with (args.job/'recorder.log').open('x') as log:
        recorder = subprocess.Popen(record, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            running = subprocess.Popen(mission, stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                result['mission_exit'] = running.wait(timeout=660)
            except subprocess.TimeoutExpired:
                result['mission_timed_out'] = True
                finish(running, 10)
                result['mission_exit'] = 124
        finally:
            if running is not None and running.poll() is None:
                finish(running, 10)
            result['recorder_exit'] = finish(recorder, 30)
            (args.job/'recording-processes.json').write_text(json.dumps(result, indent=2)+'\n')
    return result['mission_exit'] if result['mission_exit'] is not None else 1


if __name__ == '__main__':
    raise SystemExit(main())
