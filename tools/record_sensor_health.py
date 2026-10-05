"""Record bounded timing/status without commands. Exit 0 means a report was saved.

The separate processing_health_summary requires fresh lane/depth /healthy Bools
and acquisition-bearing processed statuses. Lane detection visibility is separate:
status.valid can be false in legitimate gaps. Recording success does not assert
full stream health.
"""
import argparse
import json
import math
from pathlib import Path
import time
from sensor_telemetry import attach_sensor_telemetry


def record(duration, output, ros, attach=attach_sensor_telemetry, clock=time.monotonic):
    """Collect and save evidence; always release ROS after successful init."""
    ros.init()
    node = None
    try:
        node = ros.create_node('igvc_sensor_health_recorder')
        telemetry = attach(node)
        deadline = clock()+duration
        outcome = 'duration_elapsed'
        try:
            while ros.ok() and clock() < deadline:
                ros.spin_once(node, timeout_sec=.05)
            if not ros.ok():
                outcome = 'ros_stopped'
        except KeyboardInterrupt:
            outcome = 'interrupted'
        report = telemetry.report()
        report.update(requested_duration_s=duration, recording_status='recorded', collection_outcome=outcome,
                      recording_success_meaning='Report saved; does not assert sensor or perception health.')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
        return report
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            # A ROS signal handler may already have shut the context down.
            ros.try_shutdown()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=60.)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or not 0 < args.duration <= 3600:
        parser.error('duration must be in (0, 3600] seconds')
    import rclpy
    report = record(args.duration, args.output, rclpy)
    print(json.dumps({'output': str(args.output), 'duration_wall_s': report['duration_wall_s'],
                      'recording_status': report['recording_status'],
                      'processing_health_summary': report['processing_health_summary'],
                      'stream_counts': {k: v['count'] for k, v in report['streams'].items()}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
