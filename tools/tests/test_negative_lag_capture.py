import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sensor_telemetry import SensorTelemetry


RAW = ('rgb', 'rgb_info', 'depth', 'depth_info', 'scan')
SECOND = 1_000_000_000


class CountingClock:
    """Distinct readings so the recorded callback time identifies one clock read."""
    def __init__(self, start=10.):
        self.value = start
        self.calls = 0

    def __call__(self):
        self.calls += 1
        self.value += .25
        return self.value


def capture(telemetry):
    return telemetry.report()['negative_lag_capture']


class NegativeLagCaptureTests(unittest.TestCase):
    def test_first_event_keeps_exact_stamps_and_the_observe_callback_time(self):
        clock = CountingClock()
        telemetry = SensorTelemetry(clock=clock)
        telemetry.observe_clock(5*SECOND)
        before = clock.calls
        telemetry.observe('depth', 5*SECOND+7)
        callback_time = clock.value
        self.assertEqual(clock.calls-before, 1)  # no extra clock read for capture
        section = capture(telemetry)
        self.assertEqual(section['events'], [{'stream': 'depth', 'stamp_ns': 5*SECOND+7,
                                              'latest_clock_stamp_ns': 5*SECOND,
                                              'callback_monotonic_s': callback_time}])
        self.assertEqual((section['capacity'], section['captured_count'], section['overflow_count'],
                          section['invalid_value_skip_count']), (64, 1, 0, 0))
        self.assertEqual(section['streams'], list(RAW))
        json.dumps(section, allow_nan=False)

    def test_positive_zero_unclocked_and_unknown_streams_are_not_captured(self):
        telemetry = SensorTelemetry(clock=lambda: 1.)
        telemetry.observe('rgb', 9*SECOND)        # no clock received yet
        telemetry.observe('scan')                 # no stamp
        telemetry.observe_clock(10*SECOND)
        telemetry.observe('rgb', 9*SECOND)        # positive lag
        telemetry.observe('depth', 10*SECOND)     # zero lag
        telemetry.observe('imu', 11*SECOND)       # negative, not allowlisted
        telemetry.observe('lanes', 11*SECOND)     # negative, status stream
        telemetry.status('depth_processing', {'valid': True})
        report = telemetry.report()
        self.assertEqual(report['streams']['imu']['negative_lag_samples'], 1)
        self.assertEqual(report['streams']['lanes']['negative_lag_samples'], 1)
        self.assertEqual(report['streams']['rgb']['negative_lag_samples'], 0)
        section = report['negative_lag_capture']
        self.assertEqual((section['captured_count'], section['overflow_count'],
                          section['invalid_value_skip_count'], section['events']), (0, 0, 0, []))

    def test_mixed_streams_keep_global_first_64_and_count_exact_overflow(self):
        telemetry = SensorTelemetry(clock=lambda: 2.)
        telemetry.observe_clock(SECOND)
        sent = []
        for i in range(70):
            name = RAW[i % len(RAW)]
            telemetry.observe(name, SECOND+1+i)
            sent.append((name, SECOND+1+i))
        telemetry.observe('imu', 3*SECOND)        # not allowlisted: not overflow
        telemetry.observe('rgb', 2.5*SECOND)      # malformed after saturation: skip, not overflow
        section = capture(telemetry)
        self.assertEqual([(e['stream'], e['stamp_ns']) for e in section['events']], sent[:64])
        self.assertEqual({e['stream'] for e in section['events']}, set(RAW))
        self.assertEqual((section['captured_count'], section['overflow_count'],
                          section['invalid_value_skip_count']), (64, 6, 1))
        negatives = sum(telemetry.report()['streams'][name]['negative_lag_samples'] for name in RAW)
        self.assertEqual(negatives, 64+6+1)

    def test_malformed_diagnostic_values_accepted_by_legacy_code_are_skipped(self):
        readings = iter([0., 1., 2., float('nan'), 4., 5., 6., float('inf'), 8., 9., 10.])
        telemetry = SensorTelemetry(clock=lambda: next(readings))
        telemetry.observe_clock(10)               # 1.
        telemetry.observe('rgb', 10.5)            # 2. float stamp
        telemetry.observe('rgb', 20)              # nan callback time
        telemetry.observe('depth', 2**63)         # 4. stamp out of range
        telemetry.observe('scan', float('nan'))   # 5. nan stamp (legacy counts as negative)
        telemetry.observe('rgb_info', True)       # 6. bool stamp with positive lag: not negative
        telemetry.observe('depth_info', 30)       # inf callback time
        telemetry.observe_clock(-10)              # 8. clock outside stamp range
        telemetry.observe('scan', 5)              # 9. lag negative, clock invalid
        report = telemetry.report()
        counts = {name: report['streams'][name]['negative_lag_samples'] for name in RAW}
        self.assertEqual(counts, {'rgb': 2, 'rgb_info': 0, 'depth': 1, 'depth_info': 1, 'scan': 2})
        section = report['negative_lag_capture']
        self.assertEqual((section['captured_count'], section['overflow_count'],
                          section['invalid_value_skip_count']), (0, 0, 6))
        self.assertEqual(report['clock_resets'], 1)

    def test_bool_stamp_with_negative_lag_is_skipped(self):
        telemetry = SensorTelemetry(clock=lambda: 0.)
        telemetry.observe_clock(0)
        telemetry.observe('rgb', True)
        self.assertEqual(telemetry.report()['streams']['rgb']['negative_lag_samples'], 1)
        self.assertEqual(capture(telemetry)['invalid_value_skip_count'], 1)
        self.assertEqual(capture(telemetry)['events'], [])

    def test_report_section_is_detached_from_retained_events(self):
        telemetry = SensorTelemetry(clock=lambda: 3.)
        telemetry.observe_clock(SECOND)
        telemetry.observe('scan', SECOND+1)
        first = telemetry.report()
        first['negative_lag_capture']['events'][0]['stamp_ns'] = -1
        first['negative_lag_capture']['events'].append({'stream': 'fake'})
        first['negative_lag_capture']['streams'].append('fake')
        second = capture(telemetry)
        self.assertEqual(second['events'], [{'stream': 'scan', 'stamp_ns': SECOND+1,
                                             'latest_clock_stamp_ns': SECOND,
                                             'callback_monotonic_s': 3.}])
        self.assertEqual(second['streams'], list(RAW))

    def test_saturation_leaves_legacy_health_and_counters_unchanged(self):
        now = [0.]
        telemetry = SensorTelemetry(clock=lambda: now[0], window=8)
        telemetry.observe_clock(10*SECOND)
        for i in range(200):
            now[0] = i*.001
            telemetry.observe(RAW[i % len(RAW)], 10*SECOND+1+i)
        telemetry.observe('rgb', 10*SECOND-SECOND//2)   # one positive lag of .5 s
        telemetry.observe('rgb', 10*SECOND-SECOND//2)   # duplicate
        telemetry.observe('rgb', 10*SECOND-SECOND)      # regression, lag 1 s
        now[0] = 1.
        telemetry.observe_clock(10*SECOND)
        for name, health in (('lanes', 'lane_health'), ('depth_processing', 'depth_health')):
            telemetry.status(name, {'valid': True, 'stamp_ns': 10*SECOND-SECOND//10})
            telemetry.status(health, True)
        summary = telemetry.health_summary(1.)
        self.assertEqual(summary['status'], 'pass')
        self.assertFalse(telemetry.capture_health_snapshot('pass', {'status': 'pass'}, summary, 1.))
        self.assertTrue(telemetry.capture_health_snapshot('fail', {'status': 'fail'}, summary, 1.))
        report = telemetry.report()
        self.assertEqual(report['schema_version'], 1)
        self.assertEqual(report['processing_health_summary']['status'], 'pass')
        rgb = report['streams']['rgb']
        self.assertEqual((rgb['count'], rgb['negative_lag_samples'], rgb['duplicates'],
                          rgb['stamp_regressions']), (43, 40, 1, 2))
        self.assertEqual(rgb['recent_acquisition_lag_sim_s'], {'p50': .5, 'p95': 1., 'p99': 1.})
        self.assertEqual(sum(report['streams'][n]['negative_lag_samples'] for n in RAW), 200)
        self.assertEqual(report['streams']['scan']['recent_acquisition_lag_sim_s']['p50'], None)
        snapshot = report['first_health_snapshots']['fail']
        self.assertEqual(snapshot['subscriber_observations']['rgb']['count'], 43)
        self.assertNotIn('negative_lag_capture', snapshot)
        section = report['negative_lag_capture']
        self.assertEqual((section['captured_count'], section['overflow_count'],
                          section['invalid_value_skip_count']), (64, 136, 0))
        json.dumps(report, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
