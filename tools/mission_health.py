"""ROS-independent sampled processing-health evidence for one armed mission."""
from collections import Counter, deque
import copy
import math


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _stamp(value):
    return type(value) is int and 0 <= value < 2**63


def _reason(value):
    return str(value).encode('utf-8', errors='replace')[:160].decode('utf-8', errors='ignore')


def _summary(value):
    """Validate the actual SensorTelemetry.health_summary processing contract."""
    if not isinstance(value, dict):
        return 'unknown', ['missing_health_summary'], None
    limits = {key: value.get(key) for key in ('max_age_wall_s', 'max_acquisition_lag_sim_s')}
    checks = value.get('checks')
    if (not all(_finite(v) and v >= 0 for v in limits.values())
            or not isinstance(checks, dict)
            or set(checks) != {'lanes', 'depth_processing'}):
        return 'unknown', ['invalid_health_summary'], None
    states, reasons = [], []
    for name, topic in (('lanes', 'lane_health'), ('depth_processing', 'depth_health')):
        check = checks[name]
        if (not isinstance(check, dict) or check.get('status') not in ('pass', 'fail', 'unknown')
                or check.get('health_topic') != topic or 'reason' not in check
                or check.get('reported_healthy') is not None
                   and type(check['reported_healthy']) is not bool):
            return 'unknown', ['invalid_health_summary'], None
        for key in ('age_wall_s', 'health_age_wall_s', 'acquisition_lag_sim_s'):
            number = check.get(key)
            # A negative acquisition lag is a legitimate unknown from telemetry.
            if number is not None and (not _finite(number)
                    or key != 'acquisition_lag_sim_s' and number < 0):
                return 'unknown', ['nonfinite_or_invalid_health_summary'], None
        state = check['status']
        if state == 'pass' and (check.get('reported_healthy') is not True
                or check['reason'] != 'fresh_successful_processing_status'
                or not all(_finite(check.get(key)) and 0 <= check[key] <= limit
                    for key, limit in (('age_wall_s', limits['max_age_wall_s']),
                        ('health_age_wall_s', limits['max_age_wall_s']),
                        ('acquisition_lag_sim_s', limits['max_acquisition_lag_sim_s'])))):
            return 'unknown', ['inconsistent_passing_health_summary'], None
        states.append(state)
        if state != 'pass':
            reasons.append(name+':'+_reason(check['reason']))
    status = 'fail' if 'fail' in states else 'unknown' if 'unknown' in states else 'pass'
    if (value.get('status') != status
            or value.get('fresh_successful_processing') is not (status == 'pass')):
        return 'unknown', ['inconsistent_health_summary_status'], None
    return status, reasons, limits


class MissionHealthLedger:
    """Sample with a steady wall clock; odometry stamps bind the sim interval.

    begin/observe/end accept caller times, so this module has no ROS, clock,
    costmap, route or WORLD dependencies. No failure or unknown is forgotten when
    bounded recent events roll over. Sampling gaps include first and tail gaps.
    """
    def __init__(self, *, max_gap_s=.25, event_limit=384):
        if (not _finite(max_gap_s) or max_gap_s <= 0
                or type(event_limit) is not int or event_limit < 1):
            raise ValueError('Positive finite sampling bound and history limit required')
        self.max_gap_s = float(max_gap_s)
        self.events = deque(maxlen=event_limit)
        self.active = False
        self.start = self.finish = None
        self.first_sample = self.last_sample = None
        self.totals = {'pass': 0, 'fail': 0, 'unknown': 0}
        self.valid_sample_count = 0
        self.max_interior_gap_s = 0.
        self.reason_counts, self.integrity_errors = Counter(), Counter()
        self.health_limits = None
        self.first_fail = self.first_unknown = None
        self._ended_report = None

    def begin(self, now, odom_stamp_ns):
        if self.start is not None:
            raise ValueError('A ledger records one mission interval')
        if not _finite(now) or not _stamp(odom_stamp_ns):
            raise ValueError('Finite wall time and nonnegative integer odometry stamp required')
        self.start = {'monotonic_s': float(now), 'odom_stamp_ns': odom_stamp_ns}
        self.active = True

    def _count_reason(self, reason):
        reason = _reason(reason)
        # Fixed cardinality as well as fixed per-value size.
        key = reason if reason in self.reason_counts or len(self.reason_counts) < 63 else 'other'
        self.reason_counts[key] += 1

    def observe(self, summary, now, odom_stamp_ns):
        """Return recorded status; ignore timer ticks outside the armed interval."""
        if not self.active:
            return None
        status, reasons, limits = _summary(summary)
        previous = self.last_sample or self.start
        integrity = []
        if not _finite(now) or not _stamp(odom_stamp_ns):
            integrity.append('invalid_sample_boundary')
        else:
            if not _finite(now-previous['monotonic_s']):
                integrity.append('invalid_sample_elapsed')
            if now < previous['monotonic_s']:
                integrity.append('wall_clock_regression')
            elif self.last_sample is not None and now == previous['monotonic_s']:
                integrity.append('duplicate_wall_sample')
            if odom_stamp_ns < previous['odom_stamp_ns']:
                integrity.append('odom_clock_regression')
        if integrity:
            status = 'unknown'
            reasons.extend(integrity)
            self.integrity_errors.update(integrity)
        else:
            boundary = {'monotonic_s': float(now), 'odom_stamp_ns': odom_stamp_ns}
            if self.first_sample is None:
                self.first_sample = boundary
            else:
                self.max_interior_gap_s = max(self.max_interior_gap_s,
                    now-self.last_sample['monotonic_s'])
            self.last_sample = boundary
            self.valid_sample_count += 1
        if limits is not None:
            if self.health_limits is None:
                self.health_limits = limits
            elif limits != self.health_limits:
                status = 'unknown'
                reasons.append('processing_health_limits_changed')
        self.totals[status] += 1
        for reason in reasons:
            self._count_reason(reason)
        event = {'monotonic_s': float(now) if _finite(now) else None,
                 'odom_stamp_ns': odom_stamp_ns if _stamp(odom_stamp_ns) else None,
                 'status': status, 'reasons': [_reason(r) for r in reasons]}
        self.events.append(event)
        if status == 'fail' and self.first_fail is None:
            self.first_fail = copy.deepcopy(event)
        if status == 'unknown' and self.first_unknown is None:
            self.first_unknown = copy.deepcopy(event)
        return status

    def end(self, now, odom_stamp_ns):
        """Finish after covered motion stops; repeated calls return original evidence."""
        if self._ended_report is not None:
            return copy.deepcopy(self._ended_report)
        if self.start is None:
            raise ValueError('begin must bind the mission before end')
        self.active = False
        previous = self.last_sample or self.start
        if not _finite(now) or not _stamp(odom_stamp_ns):
            self.integrity_errors['invalid_end_boundary'] += 1
        else:
            if now < previous['monotonic_s']:
                self.integrity_errors['wall_clock_regression'] += 1
            if odom_stamp_ns < previous['odom_stamp_ns']:
                self.integrity_errors['odom_clock_regression'] += 1
            self.finish = {'monotonic_s': float(now), 'odom_stamp_ns': odom_stamp_ns}
        elapsed = None if self.finish is None else self.finish['monotonic_s']-self.start['monotonic_s']
        elapsed_sim = None if self.finish is None else (self.finish['odom_stamp_ns']-self.start['odom_stamp_ns'])/1e9
        if not _finite(elapsed) or elapsed <= 0 or not _finite(elapsed_sim) or elapsed_sim <= 0:
            self.integrity_errors['invalid_elapsed_interval'] += 1
        first_gap = (None if self.first_sample is None else
                     self.first_sample['monotonic_s']-self.start['monotonic_s'])
        tail_gap = (None if self.finish is None or self.last_sample is None else
                    self.finish['monotonic_s']-self.last_sample['monotonic_s'])
        first_gap = first_gap if _finite(first_gap) else None
        tail_gap = tail_gap if _finite(tail_gap) else None
        gaps = [first_gap, self.max_interior_gap_s, tail_gap]
        maximum = max(gaps) if all(_finite(v) and v >= 0 for v in gaps) else None
        # Tiny arithmetic tolerance avoids false failures at an exact bound.
        covered = (not self.integrity_errors and self.valid_sample_count >= 2
                   and maximum is not None and maximum <= self.max_gap_s+1e-9)
        passed = covered and self.totals['fail'] == self.totals['unknown'] == 0
        failures = list(self.integrity_errors)
        if self.valid_sample_count < 2:
            failures.append('fewer_than_two_distinct_samples')
        if maximum is None or maximum > self.max_gap_s+1e-9:
            failures.append('sampling_coverage_incomplete')
        if self.totals['fail']:
            failures.append('processing_failure_observed')
        if self.totals['unknown']:
            failures.append('unknown_processing_health_observed')
        self._ended_report = dict(schema_version=1,
            scope='Sampled lane/depth processing health over the armed mission interval; '
                  'coverage is bounded by max_gap_s. Not continuous physical health, '
                  'raw-stream quality, perception accuracy or motion authorization.',
            completed=True, passed=passed, coverage_complete=covered,
            status='pass' if passed else 'fail' if self.totals['fail'] or self.integrity_errors else 'unknown',
            start=self.start, end=self.finish,
            elapsed_wall_s=elapsed if _finite(elapsed) else None,
            elapsed_sim_s=elapsed_sim if _finite(elapsed_sim) else None,
            sample_count=sum(self.totals.values()), valid_sample_count=self.valid_sample_count,
            totals=dict(self.totals), latched_fail=bool(self.totals['fail']),
            latched_unknown=bool(self.totals['unknown']),
            max_gap_s=self.max_gap_s, first_gap_s=first_gap, tail_gap_s=tail_gap,
            max_interior_gap_s=self.max_interior_gap_s, max_gap_including_bounds_s=maximum,
            first_sample=self.first_sample, last_sample=self.last_sample,
            health_limits=self.health_limits, reason_counts=dict(self.reason_counts),
            integrity_errors=dict(self.integrity_errors), failure_reasons=failures,
            first_fail=self.first_fail, first_unknown=self.first_unknown,
            recent_events=list(self.events), event_limit=self.events.maxlen)
        return copy.deepcopy(self._ended_report)
