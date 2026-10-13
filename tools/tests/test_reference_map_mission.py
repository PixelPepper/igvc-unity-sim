"""Reference-map mission: sanitized schema accepted by sensor_course, exact pixel->odom transform."""
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reference_map_mission as mission_module
from reference_map_mission import DESTINATIONS_PX, build, pixel_to_odom
from sensor_course import destinations


class ReferenceMapMissionTests(unittest.TestCase):
    def test_spawn_is_origin_and_axes(self):
        self.assertEqual(pixel_to_odom(960.5, 439), (0., 0.))
        x, y = pixel_to_odom(960.5, 439-100)          # 100 px up the image = 3.5 m forward
        self.assertAlmostEqual(x, 3.5); self.assertAlmostEqual(y, 0.)
        x, y = pixel_to_odom(960.5-100, 439)          # 100 px left = 3.5 m to the robot's left
        self.assertAlmostEqual(x, 0.); self.assertAlmostEqual(y, 3.5)

    def test_schema_is_accepted_by_sensor_course_and_round_trips(self):
        mission = build()
        self.assertEqual(set(mission), {'schema_version', 'origin', 'goals', 'max_speed_mps'})
        parsed = destinations(json.loads(json.dumps(mission)))
        self.assertEqual(len(parsed), 6)
        for (gx, gy, radius), (_, (px, py), r) in zip(parsed, DESTINATIONS_PX):
            x, y = pixel_to_odom(px, py)
            self.assertAlmostEqual(gx, x, places=4); self.assertAlmostEqual(gy, y, places=4)
            self.assertEqual(radius, r)

    def test_no_geometry_or_heading_is_exported(self):
        mission = build()
        for goal in mission['goals']:
            self.assertEqual(set(goal), {'latitude', 'longitude', 'altitude', 'radius_m'})
        text = json.dumps(mission)
        for forbidden in ('route', 'heading', 'yaw', 'boundary', 'obstacle', 'tape', 'drum', 'centerline'):
            self.assertNotIn(forbidden, text)

    def test_destination_order_drives_top_then_left_then_bottom(self):
        xs = [pixel_to_odom(px, py) for _, (px, py), _ in DESTINATIONS_PX]
        self.assertGreater(xs[0][0], 0)                    # top-right gate is ahead (north)
        self.assertTrue(all(y > 20 for _, y in xs[1:5]))  # stars are far to the left (No Man's Land)
        self.assertLess(xs[5][0], 0)                       # south finish is behind the spawn

    def test_rejects_bad_inputs(self):
        for bad in ((math.nan, 1.), (1., math.inf), (-1., 5.), (5., 2000.)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pixel_to_odom(*bad)
        for speed in (0, -1, 3., math.nan):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                build(max_speed=speed)

    def test_cli_writes_mission(self):
        out = Path(mission_module.ROOT)/'artifacts'/'agents'/'T-0090'/'test-autonomy.json'
        try:
            self.assertEqual(mission_module.main(['--out', str(out)]), 0)
            self.assertEqual(len(destinations(json.loads(out.read_text()))), 6)
        finally:
            if out.exists():
                out.unlink()


if __name__ == '__main__':
    unittest.main()
