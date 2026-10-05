"""Processing-health diagnosis: reason classification, evicted-buffer reporting, margin."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import diagnose_processing_health as diag  # noqa: E402


def run_fixture(lane_reasons, depth_reasons, ring_start_mono=500.0):
    stream = {'max_gap_s': .26, 'recent_interarrival_wall_s': {'p50': .1}, 'negative_lag_samples': 0}
    return {
        'mission_health_interval': {
            'passed': False, 'totals': {'pass': 9, 'fail': 1, 'unknown': 0},
            'reason_counts': {'lanes:processing_health_false': 1},
            'first_fail': {'monotonic_s': 120.0, 'odom_stamp_ns': 20_000_000_000},
            'start': {'monotonic_s': 100.0},
            'recent_events': [{'monotonic_s': ring_start_mono, 'odom_stamp_ns': 400_000_000_000}]},
        'sensor_health': {
            'streams': {'clock': stream, 'rgb': stream, 'depth': stream},
            'status_reason_counts': {'lanes': lane_reasons, 'depth_processing': depth_reasons,
                                     'lane_health': {'False': 1, 'True': 9}},
            'recent_events': [{'elapsed_s': ring_start_mono-100.0}],
            'processing_health_summary': {'checks': {'depth_processing': {'acquisition_lag_sim_s': .3}}}},
        'trajectory': [[19.9, 0, 0, 0], [19.92, 0, 0, 0], [20.4, 0, 0, 0]],
        'decisions': [
            {'phase': 'requested', 'sequence': 1, 'monotonic_s': 119.0, 'odom_stamp_ns': 19_000_000_000,
             'input_metadata': {'lane_age_wall_s': .1, 'grid_age_wall_s': .5}},
            {'phase': 'requested', 'sequence': 2, 'monotonic_s': 121.0, 'odom_stamp_ns': 21_100_000_000,
             'input_metadata': {'lane_age_wall_s': .1, 'grid_age_wall_s': .5}}]}


class DiagnoseTest(unittest.TestCase):
    def test_pairing_waits_without_faults_are_not_called_algorithm_defects(self):
        report = diag.diagnose(run_fixture({'valid': 9, 'unknown': 3, 'waiting_for_depth_ground_or_rgb_tf': 1},
                                           {'valid': 9, 'no_new_pair': 1}))
        self.assertEqual(report['finding'], 'pairing/freshness wait, no processing fault recorded')
        self.assertEqual(report['status_reasons']['lanes']['benign'], {'valid': 9, 'unknown': 3})

    def test_exception_reason_is_reported_as_processing_fault(self):
        report = diag.diagnose(run_fixture({'valid': 9, 'tf_acquisition_stamp': 1}, {'valid': 9}))
        self.assertEqual(report['status_reasons']['lanes']['processing_fault'], {'tf_acquisition_stamp': 1})
        self.assertIn('processing fault', report['finding'])

    def test_evicted_rings_are_listed_as_unavailable_not_guessed(self):
        report = diag.diagnose(run_fixture({'valid': 1}, {'valid': 1}, ring_start_mono=500.0))
        joined = ' '.join(report['unavailable'])
        self.assertIn('per-sample health ledger at failure', joined)
        self.assertIn('per-message perception status', joined)
        covered = diag.diagnose(run_fixture({'valid': 1}, {'valid': 1}, ring_start_mono=110.0))
        self.assertFalse(any('per-sample health ledger' in item for item in covered['unavailable']))

    def test_margin_and_odometry_gap(self):
        report = diag.diagnose(run_fixture({'no_new_exact_stamp_pair': 1}, {'valid': 1}))
        self.assertAlmostEqual(report['freshness_margin']['margin_after_one_idle_tick_sim_s']['depth_processing'], 0.0)
        self.assertAlmostEqual(report['odometry']['max_gap_sim_s_near_failure'], 0.48, places=3)
        self.assertEqual([d['sequence'] for d in report['decision_inputs_near_failure']], [1, 2])


if __name__ == '__main__':
    unittest.main()
