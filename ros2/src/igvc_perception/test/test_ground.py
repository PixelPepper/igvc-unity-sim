import unittest
import numpy as np
from igvc_perception.ground import estimate_ground, terrain_obstacles


class GroundTests(unittest.TestCase):
    def plane(self, height=0., angle=0., noise=0.):
        x, y = np.meshgrid(np.linspace(1, 5, 32), np.linspace(-2, 2, 25))
        z = height + np.tan(np.deg2rad(angle))*x
        z += np.random.default_rng(9).normal(0, noise, z.shape)
        return np.column_stack((x.ravel(), y.ravel(), z.ravel()))

    def test_flat_and_elevated_are_not_tied_to_zero(self):
        for height in [0., .195, 1.]:
            plane = estimate_ground(self.plane(height), [0, 0, height+1.1])
            np.testing.assert_allclose(plane['normal'], [0, 0, 1], atol=1e-8)
            self.assertAlmostEqual(plane['offset'], -height)
            self.assertEqual(plane['inlier_fraction'], 1.)

    def test_noisy_slope_outliers_and_barrel_classification(self):
        ground = self.plane(.195, 10, .008)
        rng = np.random.default_rng(7)
        outliers = rng.uniform([1, -2, 1.5], [5, 2, 3], (180, 3))
        camera = [0, 0, 1.295]
        result = estimate_ground(np.vstack((ground, outliers)), camera)
        self.assertAlmostEqual(result['slope_deg'], 10, delta=.2)
        self.assertGreater(result['inlier_fraction'], .8)
        self.assertLess(result['rms_m'], .012)
        normal = np.asarray(result['normal'])
        foot = np.array([3., 0, 0.195+3*np.tan(np.deg2rad(10))])
        box = foot + .5*normal
        points = terrain_obstacles(np.array([foot, box, foot-.3*normal]), camera, result)
        np.testing.assert_allclose(points, [box], atol=1e-6)

    def test_mixed_equal_levels_rejected(self):
        low = self.plane()
        high = self.plane(.4)
        with self.assertRaises(ValueError):
            estimate_ground(np.vstack((low, high)), [0, 0, 1.2])

    def test_wall_and_excessive_slope_rejected(self):
        wall = self.plane()
        wall[:, [0, 2]] = wall[:, [2, 0]]
        for points in [wall, self.plane(angle=30)]:
            with self.assertRaises(ValueError):
                estimate_ground(points, [0, 0, 1.2])

    def test_degenerate_small_support_and_nonfinite_rejected(self):
        line = np.column_stack((np.linspace(1, 5, 300), np.zeros((300, 2))))
        bad = self.plane()
        bad[0, 0] = np.nan
        for points in [line, self.plane()*.01, bad, np.zeros((99, 3))]:
            with self.assertRaises(ValueError):
                estimate_ground(points, [0, 0, 1.1])

    def test_majority_occlusion_has_no_zero_plane_fallback(self):
        ground = self.plane()[:200]
        wall = self.plane()
        wall[:, [0, 2]] = wall[:, [2, 0]]
        with self.assertRaisesRegex(ValueError, 'No confident'):
            estimate_ground(np.vstack((ground, wall)), [0, 0, 1.1])

    def test_clearance_range_and_determinism(self):
        points = np.tile(self.plane(.195, 10, .004), (3, 1))
        first = estimate_ground(points, [0, 0, 1.295])
        self.assertEqual(first, estimate_ground(points, [0, 0, 1.295]))
        for camera in [[0, 0, .2], [0, 0, 3.]]:
            with self.assertRaises(ValueError):
                estimate_ground(self.plane(), camera)

    def test_obstacle_range_and_empty(self):
        plane = estimate_ground(self.plane(), [0, 0, 1.1])
        p = terrain_obstacles([[2, 0, .5], [11, 0, .5], [2, 0, 2.]], [0, 0, 1.1], plane)
        np.testing.assert_allclose(p, [[2, 0, .5]])
        self.assertEqual(terrain_obstacles(np.empty((0, 3)), [0, 0, 1.1], plane).shape, (0, 3))


if __name__ == '__main__':
    unittest.main()
