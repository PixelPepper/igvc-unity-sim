"""First-verdict health snapshots survive ring eviction without changing any verdict."""

import copy
import json
from pathlib import Path
import sys
import unittest

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

    def step(self, lane_healthy=True, depth_healthy=True, lane_reason=None, health=True):
        self.now += .1
        self.odom_ns += 100_000_000
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
        self.assertLessEqual(len(json.dumps(snap, ensure_ascii=False).encode('utf-8')), 4096 + 64)
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

    def test_mismatched_verdict_or_event_is_not_captured(self):
        rig = Rig()
        rig.step()
        event = dict(rig.ledger.events[-1])
        self.assertFalse(rig.telemetry.capture_health_snapshot('fail', event, {}, rig.now))  # event says pass
        self.assertFalse(rig.telemetry.capture_health_snapshot('pass', event, {}, rig.now))
        self.assertEqual(rig.telemetry.health_snapshots, {'fail': None, 'unknown': None})


class DiagnosticSnapshotTest(unittest.TestCase):
    def run_record(self):
        rig = Rig()
        rig.step()
        rig.step(lane_healthy=False, lane_reason='waiting_for_depth_ground_or_rgb_tf')
        for _ in range(20):
            rig.step()
        interval, report = rig.finish()
        return {'mission_health_interval': interval, 'sensor_health': report}

    def test_bound_snapshot_is_exposed_without_inferring_cause(self):
        result = diag.diagnose(self.run_record())
        check = result['first_verdict_snapshots']['fail']
        self.assertTrue(check['valid'])
        self.assertEqual(result['first_failure_cause'], diag.SNAPSHOT_RETAINED)
        self.assertIn('does not establish why', check['interpretation'])
        self.assertEqual(result['retained_event_coverage']['status_events'], 'evicted_before_failure')

    def test_mismatched_or_malformed_snapshot_is_not_first_failure_evidence(self):
        for corrupt in ('odom', 'kind', 'error'):
            run = self.run_record()
            snap = run['sensor_health']['first_health_snapshots']['fail']
            if corrupt == 'odom':
                snap['ledger_sample']['odom_stamp_ns'] += 1
            elif corrupt == 'kind':
                snap['verdict'] = 'unknown'
            else:
                snap['capture_error'] = 'snapshot_exceeds_byte_limit'
            result = diag.diagnose(run)
            self.assertFalse(result['first_verdict_snapshots']['fail']['valid'], corrupt)
            self.assertEqual(result['first_failure_cause'], diag.UNDETERMINED, corrupt)

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
