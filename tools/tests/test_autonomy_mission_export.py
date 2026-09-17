"""Check the fixture-to-autonomy data boundary and regional destinations."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_autonomy_mission import export_mission, LocalFrame
from generate_course_variant import generate


class AutonomyMissionExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.course, cls.mission = generate(2027, 'normal')

    def test_allowlist_and_origin(self):
        source = copy.deepcopy(self.mission)
        source['origin']['route'] = {'obstacles': [1, 2, 3]}
        result = export_mission(source, self.course)
        self.assertEqual(set(result), {'schema_version', 'origin', 'goals', 'max_speed_mps'})
        self.assertEqual(result['origin'], self.mission['origin'])
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['max_speed_mps'], 2.2)
        for goal in result['goals']:
            self.assertEqual(set(goal), {'latitude', 'longitude', 'altitude', 'radius_m'})
        for forbidden in ('dense_xy', 'route_s_m', 'yaw', 'obstacles', 'ramps', 'course_sha256', 'mode'):
            self.assertNotIn('"' + forbidden + '"', json.dumps(result))

    def test_coarse_full_loop_and_finish(self):
        result = export_mission(self.mission, self.course)
        self.assertTrue(6 <= len(result['goals']) <= 8)
        frame = LocalFrame(result['origin'])
        points = [(0., 0.)] + [frame.to_enu(g['latitude'], g['longitude'], g['altitude'])[:2]
                               for g in result['goals']]
        self.assertTrue(all(math.dist(a, b) > 20. for a, b in zip(points, points[1:])))
        self.assertGreater(points[1][0], 20.)
        self.assertGreater(points[2][1], 20.)
        self.assertGreater(points[3][1], 40.)
        self.assertLess(points[4][0], 0.)
        self.assertLess(points[5][0], 0.)
        for key in ('latitude', 'longitude', 'altitude'):
            self.assertEqual(result['goals'][-1][key], self.mission['origin'][key])
        self.assertTrue(all(g['radius_m'] == 2. for g in result['goals'][:-1]))
        self.assertEqual(result['goals'][-1]['radius_m'], .4)

    def test_determinism_no_mutation_or_obstacle_dependence(self):
        before = copy.deepcopy((self.mission, self.course))
        expected = export_mission(self.mission, self.course)
        self.assertEqual(expected, export_mission(self.mission, self.course))
        self.assertEqual(before, (self.mission, self.course))
        mission, course = before
        mission['route'] = {'dense_xy': [[999, 999]]}
        mission['waypoints'] = []
        course['obstacles'] = []
        course['guide_route_xy'] = [[999, 999]]
        course['ramps'] = []
        self.assertEqual(expected, export_mission(mission, course))

    def test_cli_and_mission_only(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / 'mission.json', Path(temp) / 'autonomy.json'
            source.write_text(json.dumps(self.mission), encoding='utf-8')
            subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] /
                           'export_autonomy_mission.py'), '--mission', str(source),
                           '--output', str(output)], check=True, capture_output=True)
            self.assertEqual(json.loads(output.read_text()), export_mission(self.mission))
            self.assertEqual(json.loads(source.read_text())['origin'], self.mission['origin'])

    def test_rejects_invalid_source(self):
        for points in ([], [(0., 0.)] * 3, [(0., 0.), (math.nan, 2.), (0., 0.)],
                       [(0., 0.), (2., 3.), (4., 5.)]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                export_mission({'origin': self.mission['origin'], 'route': {'dense_xy': points}})


if __name__ == '__main__':
    unittest.main()
