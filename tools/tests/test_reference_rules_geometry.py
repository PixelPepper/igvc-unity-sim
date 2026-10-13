"""T-0091 r2 rule-dimensioned geometry: constants, variants, measured report and negative controls."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reference_rules_geometry as G

COARSE = .1                                     # coarse raster keeps the controls quick


class ReferenceRulesGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geo, cls.drums, cls.ramp, cls.starts = G.build('length-500ft')
        cls.rep = G.measure(cls.geo, cls.drums, cls.ramp, cls.starts, grid=COARSE)

    def test_rule_constants(self):
        self.assertAlmostEqual(G.FIELD_W, 36.576); self.assertAlmostEqual(G.FIELD_H, 30.48)
        self.assertAlmostEqual(G.PASS, 1.524)
        for w in (G.W_RIGHT, G.W_CORRIDOR, G.W_NML):
            self.assertTrue(G.LANE_MIN <= w <= G.LANE_MAX)
        self.assertLessEqual(G.RAMP_RISE/G.RAMP_RUN, .15)

    def test_length_variant_measures_its_target_and_states_its_footprint(self):
        self.assertTrue(G.LAP_RANGE[0] <= self.rep['lap_length_m'] <= G.LAP_RANGE[1])
        self.assertGreater(self.rep['field_ft'][0], 120)
        self.assertTrue(any('footprint' in issue for issue in self.rep['issues']))
        self.assertFalse(self.rep['measured_constraints_met'])

    def test_width_is_measured_not_the_construction_offset(self):
        width = self.rep['usable_width_taped_m']
        self.assertGreaterEqual(width['min'], G.LANE_MIN-.005)
        self.assertNotEqual(width['method'], '')
        self.assertLess(width['max'], G.W_CORRIDOR+.8)

    def test_witness_is_reported_as_an_estimate_not_a_gate(self):
        self.assertIn('grid estimate', self.rep['witness']['note'])
        self.assertFalse(any('witness' in i and 'ft' in i for i in self.rep['issues']))

    def test_field_variant_is_reported_short(self):
        geo, drums, ramp, starts = G.build('field-120x100')
        self.assertLess(geo['length'], G.LAP_RANGE[0])
        self.assertEqual(geo['field'], (G.FIELD_W, G.FIELD_H))

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
        self.assertEqual(len(meta['goals']), 6)
        for goal in meta['goals']:
            self.assertEqual(set(goal), {'name', 'field_xy', 'radius_m'})

    def test_drum_inventory(self):
        colours = {c: sum(d['colour'] == c for d in self.drums) for c in ('Yellow', 'Red', 'Green', 'Black')}
        self.assertEqual(colours, {'Yellow': 77-len(G.NML_OMITTED), 'Red': 6, 'Green': 6, 'Black': 6})


if __name__ == '__main__':
    unittest.main()
