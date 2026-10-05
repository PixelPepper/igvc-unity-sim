from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from diagnose_observed_clearance import diagnose


class ClearanceDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.grid = dict(width=80, height=80, resolution=.1, origin=[-4., -4.],
                         costs=[0]*6400, pose=[0., 0., 0.], goal_footprint=[-1.12,.62,-.52,.52])

    def test_rear_corner_blocks_even_with_free_robot_center(self):
        self.grid['costs'][35*80+29] = 100
        report = diagnose(self.grid)
        self.assertTrue(report['center_passes'])
        self.assertFalse(report['footprint_clear'])
        self.assertEqual(report['blocking_cells'][0]['cell'], [29, 35])
        self.assertEqual(report['sampled_rear_clearance_m'], 0.)

    def test_unknown_rear_space_limits_reverse_without_blocking_current_body(self):
        for i in range(80):
            self.grid['costs'][i*80+20] = -1
        report = diagnose(self.grid)
        self.assertTrue(report['footprint_clear'])
        self.assertGreater(report['sampled_rear_clearance_m'], .5)
        self.assertLess(report['sampled_rear_clearance_m'], 1.)

    def test_free_space_does_not_invent_a_blocker(self):
        report = diagnose(self.grid)
        self.assertTrue(report['footprint_clear'])
        self.assertEqual(report['blocking_cell_count'], 0)
        self.assertAlmostEqual(report['sampled_rear_clearance_m'], 1.8)

    def test_incomplete_grid_rejected(self):
        self.grid['costs'].pop()
        with self.assertRaises(ValueError):
            diagnose(self.grid)
