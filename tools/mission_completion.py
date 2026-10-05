"""Bounded, observation-only evidence of how a sensor-led mission finishes.

The mission calls this recorder to *describe* what already happened: each
destination arrival decision, the final mission-loop samples before it, each
cleanup phase in order, and the recorded trajectory endpoint. It never
changes arrival radius, ordering, waits, commands or recording. Telemetry is
subscriber evidence of reported odometry, not proof of continuous physical
stopping. Values that are missing, nonfinite or malformed are stored as null
and named in `unavailable`; nothing is interpolated or invented.
"""
from collections import deque
import math

SCHEMA_VERSION = 1


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _finite_or_none(value):
    """Derived values that overflow (huge but finite inputs) become null, keeping JSON finite."""
    return value if _finite(value) else None


def _stamp(value):
    return value if type(value) is int and 0 <= value < 2**63 else None


def _index(value):
    return value if type(value) is int and value >= 0 else None


def _pose(value):
    try:
        pose = tuple(value)
    except TypeError:
        return None
    return pose if len(pose) == 3 and all(_finite(v) for v in pose) else None


class MissionCompletionRecorder:
    """Retains at most `loop_samples` loop samples, one arrival per destination and `phase_limit` phases."""

    def __init__(self, goals, *, loop_samples=64, phase_limit=16):
        if type(loop_samples) is not int or loop_samples < 2 or type(phase_limit) is not int or phase_limit < 4:
            raise ValueError('loop_samples >= 2 and phase_limit >= 4 integers required')
        self.goals = []
        for goal in goals:
            x, y, radius = goal
            if not all(_finite(v) for v in (x, y, radius)):
                raise ValueError('goals must be finite (x, y, radius)')
            self.goals.append((float(x), float(y), float(radius)))
        self.loop = deque(maxlen=loop_samples)
        self.loop_count = 0
        self._last_loop_s = None
        self.arrivals = []
        self.phases = []
        self.phase_limit = phase_limit
        self.dropped_phases = 0

    def _goal(self, index):
        # After the final arrival the mission's destination index equals len(goals);
        # cleanup samples are then measured against the final goal. Larger indices are invalid.
        if index is None or not self.goals or index > len(self.goals):
            return None
        return self.goals[min(index, len(self.goals)-1)]

    def _sample(self, now, pose, odom_stamp_ns, odom_receipt_s, destination_index, trajectory_index):
        now = now if _finite(now) else None
        pose, stamp = _pose(pose), _stamp(odom_stamp_ns)
        index, trajectory = _index(destination_index), _index(trajectory_index)
        goal = self._goal(index)
        sample = {'monotonic_s': now, 'pose': list(pose) if pose else None, 'odom_stamp_ns': stamp,
                  'odom_receipt_age_s': (_finite_or_none(now-odom_receipt_s) if now is not None and _finite(odom_receipt_s) else None),
                  'destination_index': index, 'trajectory_index': trajectory,
                  'goal_distance_m': _finite_or_none(math.hypot(goal[0]-pose[0], goal[1]-pose[1])) if pose and goal else None}
        missing = sorted(key for key, value in sample.items() if value is None)
        if missing:
            sample['unavailable'] = missing
        return sample

    def observe_loop(self, now, pose, odom_stamp_ns, odom_receipt_s, destination_index, trajectory_index):
        """One mission-loop evaluation; loop_dt_s is wall time since the previous evaluation."""
        sample = self._sample(now, pose, odom_stamp_ns, odom_receipt_s, destination_index, trajectory_index)
        now = sample['monotonic_s']
        sample['loop_dt_s'] = (_finite_or_none(now-self._last_loop_s) if now is not None and self._last_loop_s is not None
                             else None)
        self._last_loop_s = now  # an invalid evaluation breaks the chain: no interval spans it
        self.loop.append(sample)
        self.loop_count += 1

    def arrival(self, now, pose, odom_stamp_ns, odom_receipt_s, destination_index, trajectory_index):
        """The arrival decision for a destination, using the exact pose the mission compared to its radius."""
        sample = self._sample(now, pose, odom_stamp_ns, odom_receipt_s, destination_index, trajectory_index)
        index = sample['destination_index']
        # Only real destinations (index < len(goals)) count, once each, so at most len(goals) arrivals.
        if index is None or index >= len(self.goals) or any(a['destination_index'] == index for a in self.arrivals):
            return
        goal = self.goals[index]
        sample.update(radius_m=goal[2], final=index == len(self.goals)-1)
        self.arrivals.append(sample)

    def phase(self, name, now, pose, odom_stamp_ns, odom_receipt_s, destination_index, trajectory_index,
              *, ok=True, error=None):
        """An ordered finish/cleanup step, recorded after it returned (or failed)."""
        if len(self.phases) >= self.phase_limit:
            self.dropped_phases += 1
            return
        sample = self._sample(now, pose, odom_stamp_ns, odom_receipt_s, destination_index, trajectory_index)
        sample.update(name=str(name)[:64], ok=bool(ok))
        if error is not None:
            sample['error'] = str(error)[:200]
        self.phases.append(sample)

    def report(self, trajectory):
        """JSON-safe summary; `trajectory` rows are [stamp_s, x, y, yaw] as recorded by the mission."""
        endpoint = {'trajectory_index': None, 'odom_stamp_s': None, 'pose': None, 'final_goal_distance_m': None}
        if isinstance(trajectory, list) and trajectory:
            row = trajectory[-1]
            pose = _pose(row[1:4]) if isinstance(row, (list, tuple)) and len(row) >= 4 else None
            stamp = row[0] if isinstance(row, (list, tuple)) and row and _finite(row[0]) else None
            final = self.goals[-1] if self.goals else None
            endpoint.update(trajectory_index=len(trajectory)-1, odom_stamp_s=stamp, pose=list(pose) if pose else None,
                            final_goal_distance_m=(_finite_or_none(math.hypot(final[0]-pose[0], final[1]-pose[1]))
                                                   if pose and final else None))
        missing = sorted(key for key, value in endpoint.items() if value is None)
        if missing:
            endpoint['unavailable'] = missing
        final_arrival = next((a for a in self.arrivals if a['final']), None)
        after = None
        if final_arrival:
            arrival_pose, end_pose = final_arrival['pose'], endpoint['pose']
            arrival_index, end_index = final_arrival['trajectory_index'], endpoint['trajectory_index']
            after = {'moved_m': (_finite_or_none(math.hypot(end_pose[0]-arrival_pose[0], end_pose[1]-arrival_pose[1]))
                                 if arrival_pose and end_pose else None),
                     'trajectory_samples': (end_index-arrival_index
                                            if arrival_index is not None and end_index is not None else None),
                     'goal_distance_change_m': (_finite_or_none(endpoint['final_goal_distance_m']-final_arrival['goal_distance_m'])
                                                if endpoint['final_goal_distance_m'] is not None
                                                and final_arrival['goal_distance_m'] is not None else None)}
        dts = [s['loop_dt_s'] for s in self.loop if s['loop_dt_s'] is not None]
        return {'schema_version': SCHEMA_VERSION,
                'arrivals': list(self.arrivals), 'final_arrival': final_arrival,
                'loop_samples': list(self.loop), 'loop_samples_total': self.loop_count,
                'loop_samples_retained': len(self.loop),
                'loop_dt_s': ({'count': len(dts), 'min': min(dts), 'max': max(dts), 'mean': _finite_or_none(sum(dts)/len(dts))}
                              if dts else None),
                'phases': list(self.phases), 'phases_dropped': self.dropped_phases,
                'endpoint': endpoint, 'after_final_arrival': after,
                'interpretation': 'Mission-loop and cleanup evidence from received odometry. loop_dt_s is wall time '
                                  'between loop evaluations near the finish (the last retained samples only). '
                                  'Not proof of continuous physical stopping; nulls are unavailable values.'}
