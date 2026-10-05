"""First-verdict health snapshots survive ring eviction without changing any verdict."""

import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sensor_telemetry import SensorTelemetry  # noqa: E402
from mission_health import MissionHealthLedger  # noqa: E402
import diagnose_processing_health as diag  # noqa: E402


class Rig:
    """Real telemetry + ledger on a fake monotonic clock, sampled like sensor_course."""

    def __init__(self, capture=True, event_limit=8, **telemetry_options):
        self.now = 100.0
        self.telemetry = SensorTelemetry(clock=lambda: self.now, event_limit=event_limit, **telemetry_options)
        self.ledger = MissionHealthLedger(max_gap_s=.25, event_limit=event_limit)
        self.capture = capture
        self.odom_ns = 50_000_000_000
        self.ledger.begin(self.now, self.odom_ns)

    def step(self, lane_healthy=True, depth_healthy=True, lane_reason=None, health=True, odom_step=100_000_000):
        self.now += .1
        self.odom_ns += odom_step
        stamp = self.odom_ns - 200_000_000
        self.telemetry.observe_clock(self.odom_ns)
        self.telemetry.observe('depth', stamp)
        lanes = {'valid': True, 'stamp_ns': stamp} if lane_reason is None else {'valid': False, 'reason': lane_reason}
        self.telemetry.status('lanes', lanes)
        self.telemetry.status('depth_processing', {'valid': True, 'stamp_ns': stamp})
        if health:
            self.telemetry.status('lane_health', lane_healthy)
            self.telemetry.status('depth_health', depth_healthy)
        summary = self.telemetry.health_summary(now=self.now)
        verdict = self.ledger.observe(summary, self.now, self.odom_ns)
        if self.capture and verdict in ('fail', 'unknown'):
            self.telemetry.capture_health_snapshot(verdict, self.ledger.events[-1], summary, self.now)
        return verdict

    def finish(self):
        self.now += .1
        return self.ledger.end(self.now, self.odom_ns), self.telemetry.report()


class CaptureTest(unittest.TestCase):
    def test_first_failure_survives_eviction_of_both_rings(self):
        rig = Rig()
        for _ in range(3):
            self.assertEqual(rig.step(), 'pass')
        self.assertEqual(rig.step(lane_healthy=False, lane_reason='waiting_for_depth_ground_or_rgb_tf'), 'fail')
        failed_at = rig.now
        for _ in range(40):  # far beyond both 8-entry rings
            rig.step()
        interval, report = rig.finish()
        self.assertGreater(interval['recent_events'][0]['monotonic_s'], failed_at)   # ledger ring evicted
        self.assertGreater(report['recent_events'][0]['elapsed_s'] + report['started_monotonic_s'], failed_at)
        snap = report['first_health_snapshots']['fail']
        self.assertEqual(snap['ledger_sample'], {k: interval['first_fail'][k] for k in diag.LEDGER_SAMPLE_KEYS})
        self.assertEqual(snap['source_reported_status']['lanes']['reason'], 'waiting_for_depth_ground_or_rgb_tf')
        self.assertIs(snap['source_reported_status']['lane_health'], False)
        self.assertEqual(snap['clocks']['monotonic_s'], failed_at)
        self.assertEqual(snap['clocks']['telemetry_elapsed_s'], failed_at - report['started_monotonic_s'])
        self.assertEqual(snap['clocks']['latest_sim_clock_ns'], interval['first_fail']['odom_stamp_ns'])
        self.assertAlmostEqual(snap['subscriber_observations']['depth']['acquisition_lag_sim_s'], .2)
        self.assertIsNone(report['first_health_snapshots']['unknown'])
        json.dumps(report, allow_nan=False)

    def test_unknown_then_fail_are_separate_and_later_failures_do_not_overwrite(self):
        rig = Rig()
        rig.step()
        self.assertEqual(rig.step(), 'pass')
        rig.now += 2.0  # health Bools go stale: unknown
        self.assertEqual(rig.step(health=False), 'unknown')
        self.assertEqual(rig.step(depth_healthy=False), 'fail')
        first_fail_odom = rig.odom_ns
        self.assertEqual(rig.step(lane_healthy=False), 'fail')
        interval, report = rig.finish()
        snaps = report['first_health_snapshots']
        self.assertEqual(snaps['unknown']['ledger_sample']['status'], 'unknown')
        self.assertEqual(snaps['fail']['ledger_sample']['odom_stamp_ns'], first_fail_odom)
        self.assertIs(snaps['fail']['source_reported_status']['depth_health'], False)

    def test_retained_snapshot_is_immutable(self):
        rig = Rig()
        rig.step()
        rig.step(lane_healthy=False)
        _, report = rig.finish()
        original = copy.deepcopy(report['first_health_snapshots'])
        report['first_health_snapshots']['fail']['ledger_sample']['status'] = 'pass'
        rig.telemetry.last_status['lanes']['valid'] = 'mutated'
        rig.ledger.first_fail['status'] = 'pass'
        self.assertEqual(rig.telemetry.report()['first_health_snapshots'], original)

    def test_snapshot_size_is_bounded_and_rejected_status_stays_visible(self):
        rig = Rig(event_limit=64, snapshot_events=64, snapshot_byte_limit=4096)
        for _ in range(30):
            rig.step()
        rig.telemetry.status('lanes', 'x' * 9000)  # oversize raw payload is rejected, not retained
        rig.now += .05
        summary = rig.telemetry.health_summary(now=rig.now)
        verdict = rig.ledger.observe(summary, rig.now, rig.odom_ns)
        self.assertEqual(verdict, 'fail')
        rig.telemetry.capture_health_snapshot(verdict, rig.ledger.events[-1], summary, rig.now)
        snap = rig.telemetry.report()['first_health_snapshots']['fail']
        self.assertLessEqual(len(json.dumps(snap, ensure_ascii=False).encode('utf-8')), 4096)
        self.assertGreater(snap['recent_status_events_dropped_for_size'], 0)
        self.assertEqual(snap['source_reported_status']['lanes']['telemetry_rejection'], 'status_payload_too_large')

    def test_capture_never_changes_ledger_verdicts_or_copies_on_pass(self):
        script = [{}] * 3 + [{'lane_healthy': False}] + [{}] * 5 + [{'health': False}] + [{}] * 3
        results = []
        for capture in (False, True):
            rig = Rig(capture=capture)
            verdicts = [rig.step(**kwargs) for kwargs in script]
            interval, _ = rig.finish()
            results.append((verdicts, interval))
        self.assertEqual(results[0], results[1])
        clean = Rig()
        for _ in range(5):
            clean.step()
        self.assertEqual(clean.telemetry.health_snapshots, {'fail': None, 'unknown': None})

    def test_pass_and_already_captured_verdicts_do_no_serialization(self):
        rig = Rig()
        rig.step()
        with patch('sensor_telemetry.json.dumps', side_effect=AssertionError('serialized')) as dumps:
            self.assertFalse(rig.telemetry.capture_health_snapshot('pass', rig.ledger.events[-1], {}, rig.now))
        dumps.assert_not_called()
        self.assertEqual(rig.step(lane_healthy=False), 'fail')  # first fail captured normally
        self.assertEqual(rig.step(depth_healthy=False), 'fail')
        with patch('sensor_telemetry.json.dumps', side_effect=AssertionError('serialized')) as dumps:
            # Second fail: the slot is already filled, so capture must return before any copying.
            self.assertFalse(rig.telemetry.capture_health_snapshot('fail', rig.ledger.events[-1], {}, rig.now))
        dumps.assert_not_called()

    def test_capture_errors_are_recorded_never_raised(self):
        rig = Rig()
        rig.step()
        rig.telemetry.sim_ns = float('nan')  # nonfinite clock makes the snapshot unserializable
        event = {'monotonic_s': rig.now, 'odom_stamp_ns': 1, 'status': 'fail', 'reasons': ['x']}
        self.assertTrue(rig.telemetry.capture_health_snapshot('fail', event, {'status': 'fail'}, rig.now))
        snap = rig.telemetry.report()['first_health_snapshots']['fail']
        self.assertEqual(set(snap), {'schema_version', 'verdict', 'capture_error'})
        self.assertIn('ValueError', snap['capture_error'])

    def test_mismatched_verdict_or_event_is_not_captured(self):
        rig = Rig()
        rig.step()
        event = dict(rig.ledger.events[-1])
        self.assertFalse(rig.telemetry.capture_health_snapshot('fail', event, {}, rig.now))  # event says pass
        self.assertFalse(rig.telemetry.capture_health_snapshot('pass', event, {}, rig.now))
        self.assertEqual(rig.telemetry.health_snapshots, {'fail': None, 'unknown': None})


class DiagnosticSnapshotTest(unittest.TestCase):
    def run_record(self, odom_step=None):
        rig = Rig()
        rig.step()
        if odom_step is None:
            rig.step(lane_healthy=False, lane_reason='waiting_for_depth_ground_or_rgb_tf')
        else:
            self.assertEqual(rig.step(odom_step=odom_step), 'unknown')  # integrity unknown, passing summary
        for _ in range(20):
            rig.step()
        interval, report = rig.finish()
        return {'mission_health_interval': interval, 'sensor_health': report}

    def diagnose_fail(self, run):
        result = diag.diagnose(run)
        return result, result['first_verdict_snapshots']['fail']

    def test_bound_snapshot_is_exposed_and_cause_stays_undetermined(self):
        result, check = self.diagnose_fail(self.run_record())
        self.assertTrue(check['valid'], check)
        self.assertEqual(result['first_failure_evidence'], 'bound_snapshot_retained')
        self.assertEqual(result['first_failure_cause'], diag.UNDETERMINED)
        self.assertIn('does not establish why', check['interpretation'])
        self.assertEqual(result['retained_event_coverage']['status_events'], 'evicted_before_failure')

    def test_incomplete_or_corrupt_snapshots_are_rejected(self):
        def empty_identities(run, snap):
            snap['ledger_sample'] = {}
            run['mission_health_interval']['first_fail'] = {}

        def float_odom(run, snap):
            for sample in (snap['ledger_sample'], run['mission_health_interval']['first_fail']):
                sample['odom_stamp_ns'] = float(sample['odom_stamp_ns'])

        def shift(section, key, value=None, delta=None):
            def corrupt(run, snap):
                snap[section][key] = snap[section][key] + delta if delta is not None else value
            return corrupt

        def drop(key, where='snapshot'):
            def corrupt(run, snap):
                (run['sensor_health'] if where == 'health' else snap).pop(key)
            return corrupt

        corruptions = {
            'empty identities': empty_identities,
            'float odom both sides': float_odom,
            'odom mismatch': shift('ledger_sample', 'odom_stamp_ns', delta=1),
            'clock monotonic': shift('clocks', 'monotonic_s', delta=1.0),
            'clock origin': shift('clocks', 'telemetry_started_monotonic_s', value=0.0),
            'clock elapsed': shift('clocks', 'telemetry_elapsed_s', value=0.0),
            'origin not exported': drop('started_monotonic_s', 'health'),
            'summary not failing': shift('health_summary', 'status', value='pass'),
            'missing summary': drop('health_summary'),
            'missing statuses': drop('source_reported_status'),
            'missing observations': drop('subscriber_observations'),
            'missing events': drop('recent_status_events'),
            'wrong kind': lambda run, snap: snap.__setitem__('verdict', 'unknown'),
            'capture error': lambda run, snap: snap.__setitem__('capture_error', 'snapshot_exceeds_byte_limit'),
        }
        for name, corrupt in corruptions.items():
            run = self.run_record()
            corrupt(run, run['sensor_health']['first_health_snapshots']['fail'])
            result, check = self.diagnose_fail(run)
            self.assertFalse(check['valid'], name)
            self.assertTrue(result['first_failure_evidence'].startswith('no_valid_snapshot'), name)
            self.assertTrue(result['first_failure_cause'].startswith(('undetermined', 'contradiction')), name)

    def test_contradiction_is_kept_when_ledger_lacks_first_fail(self):
        run = self.run_record()
        run['mission_health_interval']['first_fail'] = None
        result, check = self.diagnose_fail(run)
        self.assertEqual(result['first_failure_cause'],
                         'contradiction: totals report 1 failing samples but first_fail is missing')
        self.assertEqual(check['reason'], 'ledger_first_fail_missing_or_incomplete')

    def test_integrity_unknown_with_passing_summary_is_valid_unknown_evidence(self):
        run = self.run_record(odom_step=-500_000_000)
        check = diag.diagnose(run)['first_verdict_snapshots']['unknown']
        self.assertTrue(check['valid'], check)
        self.assertEqual(check['summary_status'], 'pass')
        self.assertIn('odom_clock_regression', check['ledger_sample']['reasons'])

    def test_schema_one_run_without_snapshots_keeps_historical_result(self):
        run = self.run_record()
        for key in ('first_health_snapshots', 'started_monotonic_s', 'clock_semantics', 'snapshot_limits'):
            del run['sensor_health'][key]
        result = diag.diagnose(run)
        self.assertEqual(result['first_failure_cause'], diag.UNDETERMINED)
        self.assertEqual(result['retained_event_coverage']['status_events'], 'alignment_unknown')
        self.assertEqual(result['first_verdict_snapshots']['fail'], {'valid': False, 'reason': 'absent'})


if __name__ == '__main__':
    unittest.main()
