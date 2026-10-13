"""Rules-course mission: reads only spawn/goal metadata, emits the sensor_course schema, rejects leaks/bad goals."""
import copy
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_rules_mission import GOAL_NAMES, ODOM, build, field_to_odom, validate
from sensor_course import destinations

META = dict(frame='field metres, x east, y north, origin field SW corner',
            spawn=dict(field_xy=[41.0, 31.7], heading='north'), odom_from_field=ODOM,
            goals=[dict(name=n, field_xy=[10.+i, 20.+i], radius_m=3. if i == 0 else 2.) for i, n in enumerate(GOAL_NAMES)])


class ReferenceRulesMissionTests(unittest.TestCase):
    def test_spawn_is_origin_and_axes(self):
        self.assertEqual(field_to_odom(META, 41.0, 31.7), (0., 0.))
        x, y = field_to_odom(META, 41.0, 34.7)        # 3 m north = 3 m forward
        self.assertAlmostEqual(x, 3.); self.assertAlmostEqual(y, 0.)
        x, y = field_to_odom(META, 38.0, 31.7)        # 3 m west = 3 m to the robot's left
        self.assertAlmostEqual(x, 0.); self.assertAlmostEqual(y, 3.)

    def test_schema_is_accepted_by_sensor_course(self):
        mission = build(META)
        self.assertEqual(set(mission), {'schema_version', 'origin', 'goals', 'max_speed_mps'})
        parsed = destinations(json.loads(json.dumps(mission)))
        self.assertEqual(len(parsed), 6)
        for (gx, gy, radius), goal in zip(parsed, META['goals']):
            x, y = field_to_odom(META, *goal['field_xy'])
            self.assertAlmostEqual(gx, x, places=4); self.assertAlmostEqual(gy, y, places=4)
            self.assertEqual(radius, goal['radius_m'])

    def test_no_geometry_is_exported(self):
        text = json.dumps(build(META))
        for forbidden in ('route', 'heading', 'yaw', 'boundary', 'obstacle', 'tape', 'drum', 'centreline', 'centerline'):
            self.assertNotIn(forbidden, text)

    def test_rejects_geometry_leak_extra_keys(self):
        for mutate in (lambda m: m.update(drums=[]), lambda m: m['goals'][0].update(heading=0.),
                       lambda m: m['spawn'].update(yaw=0.)):
            meta = copy.deepcopy(META); mutate(meta)
            with self.assertRaises(ValueError):
                validate(meta)

    def test_rejects_nonfinite_and_wrong_goals(self):
        cases = []
        m = copy.deepcopy(META); m['goals'][2]['field_xy'] = [math.nan, 1.]; cases.append(m)
        m = copy.deepcopy(META); m['spawn']['field_xy'] = [math.inf, 1.]; cases.append(m)
        m = copy.deepcopy(META); m['goals'] = m['goals'][::-1]; cases.append(m)
        m = copy.deepcopy(META); m['goals'] = m['goals'][:5]; cases.append(m)
        m = copy.deepcopy(META); m['goals'][1]['radius_m'] = 0; cases.append(m)
        m = copy.deepcopy(META); m['goals'][1]['radius_m'] = True; cases.append(m)
        m = copy.deepcopy(META); m['odom_from_field'] = 'odom_x = x'; cases.append(m)
        for meta in cases:
            with self.assertRaises(ValueError):
                validate(meta)

    def test_rejects_bad_speed(self):
        for speed in (0, -1, math.nan, 3.):
            with self.assertRaises(ValueError):
                build(META, max_speed=speed)


if __name__ == '__main__':
    unittest.main()
