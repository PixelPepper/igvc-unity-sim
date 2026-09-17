"""Behavioral checks of the sparse mission boundary without ROS or a simulator."""
import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_autonomy_mission import export_mission
from sensor_course import destinations


class SensorMissionContractTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            'origin': {'latitude': 42., 'longitude': -83., 'altitude': 0.},
            'route': {'dense_xy': [(0., 0.), (30., 0.), (30., 45.),
                                   (-10., 45.), (-10., 0.), (0., 0.)]},
        }
        self.config = export_mission(self.source)

    def test_accepts_exported_sparse_destinations(self):
        points = destinations(self.config)
        self.assertEqual(len(points), len(self.config['goals']))
        self.assertTrue(all(math.isfinite(v) for point in points for v in point))
        self.assertGreater(points[0][0], 20.)
        self.assertTrue(all(point[2] == 2. for point in points[:-1]))
        self.assertEqual(points[-1], (0., 0., .4))

    def test_rejects_privileged_route_heading_and_obstacle_fields(self):
        privileged = {
            'route': {'dense_xy': [[0., 0.], [1., 2.]]},
            'dense_xy': [[0., 0.], [1., 2.]],
            'route_s_m': 17.,
            'yaw': math.pi,
            'obstacles': [{'x': 1., 'y': 2.}],
            'mode': 'unmarked',
            'ramp_checkpoint': 'approach',
            'course_sha256': 'not-runtime-input',
        }
        for key, value in privileged.items():
            for location in ('mission', 'goal', 'origin'):
                with self.subTest(key=key, location=location):
                    config = copy.deepcopy(self.config)
                    target = (config if location == 'mission' else config['origin']
                              if location == 'origin' else config['goals'][0])
                    target[key] = value
                    with self.assertRaises(ValueError):
                        destinations(config)
        with self.assertRaises(ValueError):
            destinations(self.source)

    def test_rejects_invalid_radii(self):
        for radius in (-1., 0., .35, .399, 5.001, math.inf, -math.inf, math.nan, None, '2', True):
            with self.subTest(radius=radius):
                config = copy.deepcopy(self.config)
                config['goals'][0]['radius_m'] = radius
                with self.assertRaises(ValueError):
                    destinations(config)

    def test_rejects_malformed_origin_values(self):
        for key, value in (('latitude', None), ('longitude', '42'), ('altitude', True),
                           ('latitude', math.nan), ('latitude', 91.), ('longitude', -181.),
                           ('world_frame', {'route': [1, 2]}), ('axes', ['x', 'y']),
                           ('model', None), ('noise_stddev_m', -1.), ('noise_stddev_m', math.inf)):
            with self.subTest(key=key, value=value):
                config = copy.deepcopy(self.config)
                config['origin'][key] = value
                with self.assertRaises(ValueError):
                    destinations(config)
        for origin in (None, [], {}, {'latitude': 42., 'longitude': -83.}):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                destinations({**self.config, 'origin': origin})

    def test_rejects_malformed_mission_values(self):
        for config in (None, [], {**self.config, 'schema_version': True},
                       {**self.config, 'goals': None}, {**self.config, 'goals': [None]},
                       {**self.config, 'max_speed_mps': '2.2'},
                       {**self.config, 'max_speed_mps': math.nan}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                destinations(config)


if __name__ == '__main__':
    unittest.main()
