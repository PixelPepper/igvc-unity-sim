"""T-0091 r3 rule-dimensioned geometry: variants, issue-specific checks and negative controls."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reference_rules_geometry as G

COARSE = .1                                     # coarse raster keeps the controls quick


class ReferenceRulesGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo, cls.drums, cls.ramp, cls.starts = G.build('rules-485')
        cls.rep = G.measure(cls.geo, cls.drums, cls.ramp, cls.starts, grid=COARSE)

    def test_rule_constants(self):
        self.assertAlmostEqual(G.FIELD_W, 36.576); self.assertAlmostEqual(G.FIELD_H, 30.48)
        self.assertAlmostEqual(G.PASS, 1.524)
        for w in (G.W_RIGHT, G.W_CORRIDOR, G.W_NML):
            self.assertTrue(G.LANE_MIN <= w <= G.LANE_MAX)
        self.assertLessEqual(G.RAMP_RISE/G.RAMP_RUN, .15)

    def test_mission_run_and_closed_loop_lengths(self):
        self.assertAlmostEqual(self.rep['north_to_south_start_ft'], 485, delta=1)
        self.assertTrue(480*G.FT <= self.rep['lap_length_m'] <= G.CLOSED_MAX+1e-9)

    def test_authorized_geometry_has_no_issues_and_discloses_the_footprint(self):
        self.assertEqual(self.rep['issues'], [])
        self.assertTrue(self.rep['authorized_geometry_met'])
        self.assertEqual(len(self.rep['authorized_deviations']), 1)
        self.assertIn('120 x 100', self.rep['authorized_deviations'][0])
        self.assertIs(self.rep['full_rule_compliance'], False)

    def test_width_meets_ten_feet_without_tolerance(self):
        width = self.rep['usable_width_taped_m']
        self.assertGreaterEqual(width['min'], G.LANE_MIN)
        self.assertLessEqual(width['max'], G.LANE_MAX)

    def test_radius_is_the_osculating_radius_and_fails_on_a_kink(self):
        self.assertIn('osculating', self.rep['radius']['interpretation'])
        self.assertGreaterEqual(self.rep['radius']['nominal_min_m'], G.PASS)
        self.assertFalse(self.rep['radius']['fold'])
        p = self.geo['p'].copy(); i = len(p)//3
        p[i-5:i+5] += np.array([0., .8])            # sharp 0.8 m bump over 0.2 m
        self.assertLess(G.osculating_radius(p).min(), G.PASS)

    def test_shape_regression_accepts_proposal_and_rejects_a_hairpin(self):
        self.assertEqual(G.shape_check(self.geo)['issues'], [])
        geo = copy.copy(self.geo); p = self.geo['p'].copy()
        top = np.flatnonzero(self.geo['sec'] == 'top')
        x = p[top, 0]
        p[top, 1] -= 6*np.abs(np.sin((x-x.min())/(x.max()-x.min())*3*np.pi))   # deep repeated dips
        geo['p'] = p
        issues = G.shape_check(geo)['issues']
        self.assertTrue(any('top connector' in i for i in issues), issues)

    def test_witness_length_is_never_gated(self):
        self.assertIn('grid estimate', self.rep['witness']['note'])
        self.assertTrue(self.rep['witness']['goals_in_order'])
        self.assertFalse(any('witness' in i and 'outside' in i for i in self.rep['issues']))

    def test_field_variant_failures_are_reported(self):
        geo, drums, ramp, starts = G.build('field-120x100')
        rep = G.measure(geo, drums, ramp, starts, grid=COARSE)
        self.assertEqual(rep['authorized_deviations'], [])
        self.assertTrue(any(i.startswith('north-to-south nominal run') for i in rep['issues']))
        self.assertTrue(any(i.startswith('closed nominal loop') for i in rep['issues']))
        self.assertIn('drums overlap', rep['issues'])

    def test_negative_control_blocked_lane(self):
        drums = copy.deepcopy(self.drums)
        p, _, nrm, w, _ = G.frame(self.geo, self.starts['north']+400)
        for k in range(-3, 4):
            c = p+nrm*k*.5
            drums.append(dict(id=f'block{k}', group='block', colour='Yellow', intended='centre', side=None,
                              passage=None, x=float(c[0]), y=float(c[1])))
        rep = G.measure(self.geo, drums, self.ramp, self.starts, grid=COARSE)
        self.assertFalse(rep['corridor_loop_connected'])
        self.assertTrue(any(i.startswith('block') for i in rep['issues']))

    def test_negative_control_goal_order(self):
        meta = G.metadata(self.geo, self.starts)
        meta['goals'] = meta['goals'][::-1]
        rep = G.measure(self.geo, self.drums, self.ramp, self.starts, grid=COARSE, meta=meta)
        self.assertFalse(rep['witness']['goals_in_order'])

    def test_metadata_carries_no_course_geometry(self):
        meta = G.metadata(self.geo, self.starts)
        self.assertEqual(set(meta), {'frame', 'spawn', 'odom_from_field', 'goals'})
        self.assertEqual(meta['goals'][-1]['name'], 'south start/finish')
        for goal in meta['goals']:
            self.assertEqual(set(goal), {'name', 'field_xy', 'radius_m'})

    def test_drum_inventory(self):
        colours = {c: sum(d['colour'] == c for d in self.drums) for c in ('Yellow', 'Red', 'Green', 'Black')}
        self.assertEqual(colours, {'Yellow': 77-len(G.NML_OMITTED), 'Red': 6, 'Green': 6, 'Black': 6})


if __name__ == '__main__':
    unittest.main()
