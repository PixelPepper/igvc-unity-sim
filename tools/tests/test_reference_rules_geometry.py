"""T-0091 rule-dimensioned geometry prototype: closure, bounds, layout counts and geometry-free metadata."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reference_rules_geometry as G


class ReferenceRulesGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theta, cls.geo, cls.drums, cls.ramp, cls.starts = G.build()

    def test_field_and_rule_constants(self):
        self.assertAlmostEqual(G.FIELD_W, 36.576); self.assertAlmostEqual(G.FIELD_H, 30.48)
        self.assertAlmostEqual(G.PASS, 1.524)
        for w in (G.W_RIGHT, G.W_CORRIDOR, G.W_NML):
            self.assertTrue(G.LANE_MIN <= w <= G.LANE_MAX)
        self.assertLessEqual(self.ramp['grade'], .15)
        self.assertGreaterEqual(G.R_WAVE, G.PASS)

    def test_centreline_closes_at_the_solved_nominal_length(self):
        self.assertLess(self.geo['closure'], 1e-6)
        self.assertAlmostEqual(self.geo['length'], G.TARGET_LAP, places=3)
        self.assertAlmostEqual(G.lap_length(self.theta), self.geo['length'], places=6)

    def test_solver_is_deterministic(self):
        self.assertEqual(G.solve_theta(), self.theta)

    def test_inner_edge_does_not_fold(self):
        k = self.geo['k']; curved = k != 0
        self.assertGreater((1/abs(k[curved])-self.geo['w'][curved]/2).min(), 0)

    def test_drum_inventory_and_reported_omissions(self):
        colours = {c: sum(d['colour'] == c for d in self.drums) for c in ('Yellow', 'Red', 'Green', 'Black')}
        self.assertEqual(colours, {'Yellow': 77-len(G.NML_OMITTED), 'Red': 6, 'Green': 6, 'Black': 6})
        self.assertTrue(all(d['intended'] in ('centre', 'side', 'boundary', 'flank') for d in self.drums))

    def test_metadata_carries_no_course_geometry(self):
        meta = G.metadata(self.geo, self.starts)
        self.assertEqual(set(meta), {'frame', 'spawn', 'odom_from_field', 'goals'})
        self.assertEqual(len(meta['goals']), 6)
        for goal in meta['goals']:
            self.assertEqual(set(goal), {'name', 'field_xy', 'radius_m'})


if __name__ == '__main__':
    unittest.main()
