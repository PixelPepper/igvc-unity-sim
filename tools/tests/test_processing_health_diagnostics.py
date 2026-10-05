"""Processing-health diagnosis: evidence coverage, undetermined causes and incomplete input."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import diagnose_processing_health as diag  # noqa: E402


def run_fixture(ring_start_mono=500.0, status_start_elapsed=400.0):
    stream = {'max_gap_s': .26, 'recent_interarrival_wall_s': {'p50': .1}, 'negative_lag_samples': 0}
    return {
        'mission_health_interval': {
            'passed': False, 'totals': {'pass': 9, 'fail': 1, 'unknown': 0},
            'reason_counts': {'lanes:processing_health_false': 1},
            'first_fail': {'monotonic_s': 120.0, 'odom_stamp_ns': 20_000_000_000},
            'start': {'monotonic_s': 100.0},
            'recent_events': [{'monotonic_s': ring_start_mono, 'odom_stamp_ns': 1}]},
        'sensor_health': {
            'streams': {'clock': stream, 'rgb': stream, 'depth': stream},
            'status_reason_counts': {'lanes': {'valid': 9, 'waiting_for_depth_ground_or_rgb_tf': 1}},
            'recent_events': [{'elapsed_s': status_start_elapsed}],
            'processing_health_summary': {'checks': {'depth_processing': {'acquisition_lag_sim_s': .3}}}},
        'trajectory': [[19.9, 0, 0, 0], [19.92, 0, 0, 0], [20.4, 0, 0, 0]],
        'decisions': [
            {'phase': 'requested', 'sequence': 1, 'monotonic_s': 119.0, 'odom_stamp_ns': 19_000_000_000,
             'input_metadata': {'lane_age_wall_s': .1, 'grid_age_wall_s': .5}},
            {'phase': 'evaluated', 'sequence': 1, 'monotonic_s': 119.2, 'odom_stamp_ns': 19_200_000_000},
            {'phase': 'requested', 'sequence': 2, 'monotonic_s': 121.0, 'odom_stamp_ns': 21_100_000_000}]}


class DiagnoseTest(unittest.TestCase):
    def test_wait_reasons_do_not_establish_cause_when_rings_are_evicted(self):
        report = diag.diagnose(run_fixture())
        self.assertEqual(report['first_failure_cause'], diag.UNDETERMINED)
        self.assertIn('descriptive_only', report['whole_run_status_reason_counts'])
        joined = ' '.join(report['unavailable'])
        self.assertIn('per-sample health ledger at first failure', joined)
        self.assertIn('per-message perception status events at first failure', joined)

    def test_status_alignment_is_unknown_without_a_recorded_telemetry_origin(self):
        # Ledger covers the failure, but status elapsed_s has no exported origin;
        # the mission arm time must not be substituted for it.
        report = diag.diagnose(run_fixture(ring_start_mono=110.0, status_start_elapsed=5.0))
        self.assertEqual(report['retained_event_coverage'],
                         {'health_ledger': 'covers_failure', 'status_events': 'alignment_unknown'})
        self.assertEqual(report['first_failure_cause'], diag.UNDETERMINED)

    def test_mixed_coverage_without_odometry_claims_only_status_events(self):
        run = run_fixture(ring_start_mono=500.0, status_start_elapsed=5.0)
        run['sensor_health'][diag.TELEMETRY_ORIGIN_KEY] = 110.0
        run['trajectory'] = []
        report = diag.diagnose(run)
        self.assertEqual(report['retained_event_coverage'],
                         {'health_ledger': 'evicted_before_failure', 'status_events': 'covers_failure'})
        self.assertIn('status events retained', report['first_failure_cause'])
        self.assertIsNone(report['odometry_sim_stamps'])
        self.assertIn('odometry trajectory', report['unavailable'])
        self.assertIn('per-sample health ledger at first failure', ' '.join(report['unavailable']))

    def test_incomplete_run_reports_unavailable_instead_of_raising_or_zero_gaps(self):
        run = run_fixture()
        del run['sensor_health']['streams']['depth'], run['sensor_health']['recent_events']
        run['trajectory'] = [[19.9, 0, 0, 0]]
        run['decisions'].append({'phase': 'requested'})
        report = diag.diagnose(run)
        joined = ' '.join(report['unavailable'])
        for missing in ('stream telemetry: depth', 'odometry trajectory', 'status events at first failure'):
            self.assertIn(missing, joined)
        self.assertEqual(report['retained_event_coverage']['status_events'], 'unavailable')
        self.assertIsNone(report['odometry_sim_stamps'])
        self.assertEqual(diag.diagnose({})['first_failure_cause'], 'undetermined: health ledger unavailable')

    def test_missing_first_fail_is_judged_against_the_failure_total(self):
        cases = {1: 'contradiction: totals report 1 failing samples but first_fail is missing',
                 0: 'no failing health sample recorded',
                 None: 'undetermined: first_fail missing and failing-sample count unavailable'}
        for fail, expected in cases.items():
            run = run_fixture()
            run['mission_health_interval']['first_fail'] = None
            run['mission_health_interval']['totals']['fail'] = fail
            self.assertEqual(diag.diagnose(run)['first_failure_cause'], expected, fail)

    def test_decision_window_and_odometry_scope(self):
        report = diag.diagnose(run_fixture())
        self.assertEqual([d['sequence'] for d in report['decision_inputs_near_failure']], [1, 2])
        self.assertIsNone(report['decision_inputs_near_failure'][1]['lane_age_wall_s'])
        self.assertAlmostEqual(report['odometry_sim_stamps']['max_gap_sim_s_near_failure'], 0.48, places=3)
        self.assertIn('cannot exclude', report['odometry_sim_stamps']['scope'])

    def test_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            run, out = Path(directory)/'run.json', Path(directory)/'out.json'
            run.write_text('{}', encoding='utf-8')
            out.write_text('kept', encoding='utf-8')
            self.assertEqual(diag.main(['--run', str(run), '--output', str(out)]), 1)
            self.assertEqual(out.read_text(encoding='utf-8'), 'kept')


if __name__ == '__main__':
    unittest.main()
