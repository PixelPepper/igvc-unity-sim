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


def seed_value(text):
    """A nonnegative int32 course seed, as accepted by the managed runner."""
    if not (text.isascii() and text.isdigit()) or int(text) > 2147483647:
        raise argparse.ArgumentTypeError('seed must be an integer in 0..2147483647')
    return int(text)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('job', type=Path)
    parser.add_argument('--seed', type=seed_value, default=2027,
                        help='Course seed whose generated autonomy.json is run (default 2027)')
    return parser


def commands(workspace, job, seed):
    """(recorder, mission) argument lists; only the mission's course folder depends on the seed."""
    script = workspace/'tools'
    record = [sys.executable, str(script/'record_navigation_episode.py'),
              '--output', str(job/'episode'), '--duration', '660', '--image-hz', '2']
    mission = [sys.executable, str(script/'sensor_course.py'),
               '--mission', str(workspace/f'artifacts/courses/seed-{seed}/autonomy.json'),
               '--report', str(job/'run.json'), '--capture-dir', str(job/'decisions'),
               '--timeout', '600', '--speed', '0.6', '--planning-budget', '0.5',
               '--path-execution', 'checked-path']
    return record, mission


def main():
    args = build_parser().parse_args()
    record, mission = commands(args.workspace, args.job, args.seed)
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
