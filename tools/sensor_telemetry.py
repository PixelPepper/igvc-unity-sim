"""Bounded, observation-only stream diagnostics; never issues motion commands."""
from collections import Counter, deque
import json
import math
import time


def percentiles(values):
    values = sorted(values)
    if not values:
        return {'p50': None, 'p95': None, 'p99': None}
    return {name: values[min(len(values)-1, math.ceil(q*len(values))-1)]
            for name, q in (('p50', .5), ('p95', .95), ('p99', .99))}


def bounded_text(value, byte_limit):
    return str(value).encode('utf-8', errors='replace')[:byte_limit].decode('utf-8', errors='ignore')


class SensorTelemetry:
    """Arrival gaps use monotonic wall time; acquisition lag uses simulation time.

    Percentiles describe a bounded recent window, maxima/counters the full run.
    Subscriber arrival is not a measurement of upstream GPU or network latency.
    """
    # Statuses whose last values are retained in a first-failure snapshot.
    SNAPSHOT_STATUSES = ('lanes', 'depth_processing', 'lane_health', 'depth_health', 'lidar_processing')
    SNAPSHOT_STREAMS = ('clock', 'rgb', 'rgb_info', 'depth', 'depth_info', 'scan') + SNAPSHOT_STATUSES
    # Fixed allowlist and global capacity for first-negative-lag raw sensor events.
    NEGATIVE_LAG_STREAMS = ('rgb', 'rgb_info', 'depth', 'depth_info', 'scan')
    NEGATIVE_LAG_CAPACITY = 64

    def __init__(self, clock=time.monotonic, window=4096, event_limit=384, status_byte_limit=4096,
                 snapshot_events=32, snapshot_byte_limit=262144):
        if type(status_byte_limit) is not int or status_byte_limit < 512:
            raise ValueError('status_byte_limit must be an integer >=512 bytes')
        if (type(snapshot_events) is not int or snapshot_events < 0
                or type(snapshot_byte_limit) is not int or snapshot_byte_limit < 4096):
            raise ValueError('snapshot_events >=0 and snapshot_byte_limit >=4096 integers required')
        self.snapshot_events = snapshot_events
        self.snapshot_byte_limit = snapshot_byte_limit
        # At most one immutable snapshot per non-pass verdict kind, stored serialized.
        self.health_snapshots = {'fail': None, 'unknown': None}
        self.clock = clock
        self.started = clock()
        self.window = window
        self.streams = {}
        self.events = deque(maxlen=event_limit)
        self.event_count = 0
        self.sim_ns = None
        self.clock_resets = 0
        self.last_status = {}
        self.reasons = {}
        self.status_byte_limit = status_byte_limit
        self.status_rejections = {}
        # (stream, stamp_ns, clock_stamp_ns, callback_monotonic_s) tuples; never evicted.
        self.negative_lag_events = []
        self.negative_lag_overflow = 0
        self.negative_lag_capture_skips = 0

    def observe_clock(self, stamp_ns):
        if self.sim_ns is not None and stamp_ns < self.sim_ns:
            self.clock_resets += 1
        self.sim_ns = stamp_ns
        self.observe('clock', stamp_ns)

    def observe(self, name, stamp_ns=None):
        now = self.clock()
        stream = self.streams.setdefault(name, dict(count=0, last_wall=None,
            last_stamp_ns=None, max_gap_s=0., stamp_regressions=0, duplicates=0,
            negative_lag_samples=0, gaps=deque(maxlen=self.window),
            lags=deque(maxlen=self.window)))
        if stream['last_wall'] is not None:
            gap = max(0., now-stream['last_wall'])
            stream['gaps'].append(gap)
            stream['max_gap_s'] = max(stream['max_gap_s'], gap)
        if stamp_ns is not None:
            old = stream['last_stamp_ns']
            if old is not None:
                stream['stamp_regressions'] += int(stamp_ns < old)
                stream['duplicates'] += int(stamp_ns == old)
            stream['last_stamp_ns'] = stamp_ns
            if self.sim_ns is not None:
                lag = (self.sim_ns-stamp_ns)/1e9
                if lag >= 0:
                    stream['lags'].append(lag)
                else:
                    stream['negative_lag_samples'] += 1
                    self._capture_negative_lag(name, stamp_ns, now)
        stream['count'] += 1
        stream['last_wall'] = now

    @staticmethod
    def _exact_stamp(value):
        return type(value) is int and 0 <= value < 2**63

    def _capture_negative_lag(self, name, stamp_ns, now):
        """Keep the first allowlisted negative-lag events; observation only, never raises.

        Only explicit type/range checks: no new clock reads and no wrapper around
        the legacy calculations. Values outside the diagnostic contract (non-int or
        out-of-range stamps, non-finite callback time) are counted as skips.
        """
        if type(name) is not str or name not in self.NEGATIVE_LAG_STREAMS:
            return
        clock_ns = self.sim_ns
        finite_now = (type(now) is float and math.isfinite(now) or
                      type(now) is int and -2**63 < now < 2**63)
        if not (self._exact_stamp(stamp_ns) and self._exact_stamp(clock_ns) and finite_now):
            self.negative_lag_capture_skips += 1
        elif len(self.negative_lag_events) < self.NEGATIVE_LAG_CAPACITY:
            self.negative_lag_events.append((name, stamp_ns, clock_ns, now))
        else:
            self.negative_lag_overflow += 1

    def status(self, name, payload):
        self.observe(name)
        rejection = None
        if isinstance(payload, str):
            if len(payload.encode('utf-8', errors='replace')) > self.status_byte_limit:
                rejection = 'status_payload_too_large'
                payload = {'reason': rejection}
            else:
                try:
                    payload = json.loads(payload)
                except (ValueError, RecursionError):
                    # Simulator status is intentionally plain text.
                    pass
        if isinstance(payload, dict):
            reason = bounded_text(payload.get('reason', 'valid' if payload.get('valid') is True else 'unknown'),
                                  min(128, (self.status_byte_limit-180)//6))
        else:
            reason = bounded_text(payload, min(128, (self.status_byte_limit-180)//6))
        if rejection is None:
            try:
                encoded = json.dumps(payload, allow_nan=False, ensure_ascii=False).encode('utf-8')
                if len(encoded) > self.status_byte_limit:
                    rejection = 'status_payload_too_large'
            except (ValueError, TypeError, OverflowError, RecursionError):
                rejection = 'nonfinite_or_unserializable_status'
        if rejection is not None:
            payload = {'valid': False, 'reason': reason, 'telemetry_rejection': rejection}
            rejected = self.status_rejections.setdefault(name, Counter())
            rejected[rejection] += 1
        else:
            # Detach retained evidence from mutable caller objects.
            payload = json.loads(encoded.decode('utf-8'))
        self.last_status[name] = payload
        counts = self.reasons.setdefault(name, Counter())
        # Bound unexpected diagnostic reason cardinality as well as samples.
        counts[reason if reason in counts or len(counts) < 63 else 'other'] += 1
        self.event_count += 1
        self.events.append({'elapsed_s': self.clock()-self.started, 'stream': name,
                            'value': payload})

    def health_summary(self, now=None, max_age_wall_s=1.5, max_acquisition_lag_sim_s=1.5):
        """Fresh /healthy Bools plus acquisition-bearing lane/depth status.

        This is not full-stream health, output-quality validation, or a motion gate.
        Lane status.valid describes visible paint, not whether processing succeeded.
        Missing/stale health, clock, or acquisition evidence stays unknown. Fresh
        negative health, rejected status, or a processing error remains failed.
        """
        now = self.clock() if now is None else now
        checks = {}
        clock_stream = self.streams.get('clock')
        clock_fresh = (clock_stream is not None and
                       now-clock_stream['last_wall'] <= max_age_wall_s and self.sim_ns is not None)
        for name in ('lanes', 'depth_processing'):
            stream = self.streams.get(name)
            payload = self.last_status.get(name)
            age = None if stream is None else max(0., now-stream['last_wall'])
            stamp = payload.get('stamp_ns') if isinstance(payload, dict) else None
            lag = ((self.sim_ns-stamp)/1e9 if clock_fresh and type(stamp) is int and 0 <= stamp < 2**63 else None)
            health_name = 'lane_health' if name == 'lanes' else 'depth_health'
            health_stream = self.streams.get(health_name)
            health = self.last_status.get(health_name)
            health_age = None if health_stream is None else max(0., now-health_stream['last_wall'])
            fresh_health = health_age is not None and health_age <= max_age_wall_s
            fresh_status = age is not None and age <= max_age_wall_s
            error_status = (isinstance(payload, dict) and
                            (payload.get('telemetry_rejection') is not None or
                             payload.get('valid') is False and
                             (name == 'depth_processing' or 'reason' in payload and stamp is None)))
            state, reason = 'unknown', 'missing_status'
            if fresh_health and health is False:
                state, reason = 'fail', 'processing_health_false'
            elif fresh_status and error_status:
                state, reason = 'fail', payload.get('reason', 'processing_failed')
            elif stream is not None:
                if not fresh_status:
                    reason = 'stale_status_receipt'
                elif not fresh_health or health is not True:
                    reason = 'missing_or_stale_processing_health'
                elif not isinstance(payload, dict) or type(payload.get('valid')) is not bool:
                    reason = 'missing_processed_status'
                elif not clock_fresh:
                    reason = 'missing_or_stale_clock'
                elif lag is None or lag < 0 or lag > max_acquisition_lag_sim_s:
                    reason = 'missing_or_stale_acquisition_stamp'
                else:
                    state, reason = 'pass', 'fresh_successful_processing_status'
            checks[name] = dict(status=state, reason=reason, age_wall_s=age, acquisition_lag_sim_s=lag,
                                health_topic=health_name, reported_healthy=health, health_age_wall_s=health_age)
        lane_payload = self.last_status.get('lanes')
        lane_check = checks['lanes']
        visibility = lane_payload.get('valid') if isinstance(lane_payload, dict) else None
        lane_lag = lane_check['acquisition_lag_sim_s']
        visibility_fresh = (lane_check['age_wall_s'] is not None and
                            lane_check['age_wall_s'] <= max_age_wall_s and lane_lag is not None and
                            0 <= lane_lag <= max_acquisition_lag_sim_s)
        lane_visibility = dict(status=('sufficient' if visibility else 'insufficient')
                               if visibility_fresh and type(visibility) is bool else 'unknown',
                               reported_valid=visibility, fresh_acquisition=visibility_fresh,
                               meaning='Lane status.valid means sufficient visible lane points; false can be a legitimate gap.')
        if isinstance(lane_payload, dict):
            lane_visibility.update({key: lane_payload[key] for key in ('current_points', 'components') if key in lane_payload})
        states = {item['status'] for item in checks.values()}
        status = 'fail' if 'fail' in states else 'unknown' if 'unknown' in states else 'pass'
        return dict(status=status, fresh_successful_processing=status == 'pass', checks=checks,
                    lane_detection_visibility=lane_visibility,
                    max_age_wall_s=max_age_wall_s, max_acquisition_lag_sim_s=max_acquisition_lag_sim_s,
                    scope='Latest lane/depth health Bools plus processed acquisition claims; not full stream health, output quality or motion authorization.')

    def capture_health_snapshot(self, verdict, ledger_event, summary, now):
        """Retain subscriber evidence for the first ledger 'fail' and first 'unknown'.

        Call with the status MissionHealthLedger.observe returned, its event, and
        the exact summary/time used for it. Passing samples and later failures
        return immediately without copying. Nothing here alters any verdict.
        """
        if verdict not in self.health_snapshots or self.health_snapshots[verdict] is not None:
            return False  # pass, or already captured: no copying or serialization
        if not isinstance(ledger_event, dict) or ledger_event.get('status') != verdict:
            return False
        try:
            self.health_snapshots[verdict] = self._encode_snapshot(verdict, ledger_event, summary, now)
        except Exception as error:  # evidence capture must never disturb the sampling callback
            self.health_snapshots[verdict] = json.dumps(
                {'schema_version': 1, 'verdict': verdict,
                 'capture_error': bounded_text(type(error).__name__+': '+str(error), 160)})
        return True

    def _encode_snapshot(self, verdict, ledger_event, summary, now):
        streams = {}
        for name in self.SNAPSHOT_STREAMS:
            stream = self.streams.get(name)
            if stream is None:
                continue
            stamp = stream['last_stamp_ns']
            lag = (self.sim_ns-stamp)/1e9 if stamp is not None and self.sim_ns is not None else None
            streams[name] = {'count': stream['count'],
                             'receipt_age_wall_s': None if stream['last_wall'] is None else max(0., now-stream['last_wall']),
                             'last_stamp_ns': stamp, 'acquisition_lag_sim_s': lag,
                             'max_gap_wall_s_so_far': stream['max_gap_s']}
        snapshot = {
            'schema_version': 1, 'verdict': verdict,
            'ledger_sample': {key: ledger_event.get(key) for key in ('monotonic_s', 'odom_stamp_ns', 'status', 'reasons')},
            'clocks': {'monotonic_s': now, 'telemetry_started_monotonic_s': self.started,
                       'telemetry_elapsed_s': now-self.started, 'latest_sim_clock_ns': self.sim_ns,
                       'semantics': 'monotonic_s/started are time.monotonic wall seconds; recent status '
                                    'event elapsed_s = monotonic_s - telemetry_started_monotonic_s; '
                                    'latest_sim_clock_ns is the last received /clock.'},
            'health_summary': summary,
            'source_reported_status': {name: self.last_status[name] for name in self.SNAPSHOT_STATUSES
                                       if name in self.last_status},
            'subscriber_observations': streams,
            'recent_status_events': list(self.events)[-self.snapshot_events:] if self.snapshot_events else [],
            'unavailable': ['node-side processing duration', 'TF wait time', 'node scheduling/CPU',
                            'Unity frame time', 'hardware behavior'],
            'interpretation': 'source_reported_status is what perception nodes published; '
                              'subscriber_observations are receipt/acquisition ages seen here. '
                              'No cause is inferred: an unhealthy Bool does not say why.'}
        # Nonfinite or unserializable content raises here and becomes a capture_error record.
        encoded = json.dumps(snapshot, allow_nan=False, ensure_ascii=False)
        dropped = 0
        while len(encoded.encode('utf-8')) > self.snapshot_byte_limit and snapshot['recent_status_events']:
            snapshot['recent_status_events'].pop(0)  # drop oldest first; keep events nearest the failure
            dropped += 1
            snapshot['recent_status_events_dropped_for_size'] = dropped
            encoded = json.dumps(snapshot, allow_nan=False, ensure_ascii=False)
        if len(encoded.encode('utf-8')) > self.snapshot_byte_limit:
            encoded = json.dumps({'schema_version': 1, 'verdict': verdict,
                                  'capture_error': 'snapshot_exceeds_byte_limit'})
        return encoded  # serialized: later mutation cannot alter the retained copy

    def _negative_lag_report(self):
        # Fresh containers per call: callers cannot mutate retained evidence.
        return {
            'capacity': self.NEGATIVE_LAG_CAPACITY, 'streams': list(self.NEGATIVE_LAG_STREAMS),
            'captured_count': len(self.negative_lag_events),
            'overflow_count': self.negative_lag_overflow,
            'invalid_value_skip_count': self.negative_lag_capture_skips,
            'events': [{'stream': name, 'stamp_ns': stamp, 'latest_clock_stamp_ns': clock_ns,
                        'callback_monotonic_s': now}
                       for name, stamp, clock_ns, now in self.negative_lag_events],
            'accounting': 'Counts cover only allowlisted streams whose observe() call already '
                          'incremented negative_lag_samples. Each such event is exactly one of: '
                          'captured (first capacity valid events, never evicted), overflow (valid '
                          'events after capacity is full) or invalid_value_skip (stamp or clock not an '
                          'int in [0, 2**63), or non-finite callback time), so their sum equals the '
                          'allowlisted negative_lag_samples total.',
            'scope': 'Whole telemetry lifetime from construction; no mission interval tagging. '
                     'callback_monotonic_s is the same clock value (time.monotonic by default) '
                     'observe() already read for that callback;latest_clock_stamp_ns is the last received /clock.',
            'interpretation': 'Callback-local ordering evidence only. It cannot identify transport, '
                              'executor, drop or CPU causes, and does not explain past runs.'}

    def report(self):
        now = self.clock()
        result = {}
        for name, stream in self.streams.items():
            age = max(0., now-stream['last_wall'])
            result[name] = {key: value for key, value in stream.items()
                            if key not in ('gaps', 'lags', 'last_wall')}
            result[name].update(age_wall_s=age,
                max_gap_including_tail_s=max(age, stream['max_gap_s']),
                recent_interarrival_wall_s=percentiles(stream['gaps']),
                recent_acquisition_lag_sim_s=percentiles(stream['lags']))
        return {'schema_version': 1, 'duration_wall_s': now-self.started,
                # Additive fields; schema 1 consumers ignore them.
                'started_monotonic_s': self.started,
                'clock_semantics': 'started_monotonic_s and recent_events elapsed_s origin use this '
                                   'process time.monotonic (same clock as the mission health ledger).',
                'first_health_snapshots': {kind: None if encoded is None else json.loads(encoded)
                                           for kind, encoded in self.health_snapshots.items()},
                'snapshot_limits': {'recent_status_events': self.snapshot_events,
                                    'bytes_each': self.snapshot_byte_limit},
                'clock_resets': self.clock_resets, 'streams': result,
                'latest_status': dict(self.last_status),
                'status_reason_counts': {name: dict(counts) for name, counts in self.reasons.items()},
                'status_rejection_counts': {name: dict(counts) for name, counts in self.status_rejections.items()},
                'processing_health_summary': self.health_summary(now),
                'negative_lag_capture': self._negative_lag_report(),
                'recent_events': list(self.events), 'total_status_events': self.event_count,
                'limits': {'samples_per_stream': self.window, 'status_events': self.events.maxlen,
                           'retained_status_bytes_each': self.status_byte_limit, 'reason_keys_per_stream': 64},
                'interpretation': 'Read-only subscriber evidence. Health means successful perception, '
                    'not raw image receipt. Lag is relative to the latest received simulation clock; '
                    'negative lag counts can reflect callback ordering. No GPU/network cause is inferred.'}


def attach_sensor_telemetry(node):
    """Register bounded subscribers in an existing ROS executor."""
    from rclpy.qos import qos_profile_sensor_data
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import Image, CameraInfo, LaserScan
    from std_msgs.msg import Bool, String
    telemetry = SensorTelemetry()
    def stamp(message):
        return message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
    node.create_subscription(Clock, '/clock', lambda m: telemetry.observe_clock(
        m.clock.sec*1_000_000_000+m.clock.nanosec), qos_profile_sensor_data)
    for name, topic, kind in (
        ('rgb', '/camera/color/image_raw', Image),
        ('rgb_info', '/camera/color/camera_info', CameraInfo),
        ('depth', '/camera/depth/image_raw', Image),
        ('depth_info', '/camera/depth/camera_info', CameraInfo),
        ('scan', '/scan', LaserScan)):
        node.create_subscription(kind, topic,
            lambda m, key=name: telemetry.observe(key, stamp(m)), qos_profile_sensor_data)
    for name, topic in (
        ('lanes', '/perception/lanes/status'), ('depth_processing', '/perception/depth/status'),
        ('lidar_processing', '/perception/lidar/status'), ('simulator', '/sim/status')):
        node.create_subscription(String, topic,
            lambda m, key=name: telemetry.status(key, m.data), 1)
    for name, topic in (('lane_health', '/perception/lanes/healthy'),
                        ('depth_health', '/perception/depth/healthy')):
        node.create_subscription(Bool, topic,
            lambda m, key=name: telemetry.status(key, bool(m.data)), 1)
    return telemetry
