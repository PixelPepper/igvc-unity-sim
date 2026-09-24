import math
import unittest
import numpy as np
from igvc_perception.scan_ground import filter_ground_returns


class ScanGroundTests(unittest.TestCase):
    def patch(self, x=1., z=0., slope=0.):
        xx, yy = np.meshgrid(np.linspace(-.2, .2, 5), np.linspace(-.2, .2, 5))
        return np.column_stack((x+xx.ravel(), yy.ravel(), z+slope*xx.ravel()))

    def apply(self, points, flags=None, origin=(0., 0., 0.), rotation=None, ranges=(1.,)):
        if points is not None and flags is None:
            flags = np.ones(len(points), dtype=bool)
        return filter_ground_returns(ranges, 0., .1, .1, 10.,
            np.eye(3) if rotation is None else rotation, origin, points, flags)

    def test_flat_and_sloped_ground_returns_become_nan_not_clearing_infinity(self):
        for slope in (0., .2, -.2):
            result, diagnostics = self.apply(self.patch(slope=slope))
            self.assertTrue(np.isnan(result[0]))
            self.assertEqual(diagnostics['removed_ground'], 1)
        self.assertFalse(np.isinf(result[0]))

    def test_pitched_lidar_and_raised_world_surface_use_acquisition_transform(self):
        pitch = .2
        rotation = np.array([[math.cos(pitch), 0., math.sin(pitch)], [0., 1., 0.],
                             [-math.sin(pitch), 0., math.cos(pitch)]])
        distance = 1./math.sin(pitch)
        x = distance*math.cos(pitch)
        result, _ = self.apply(self.patch(x=x, z=2.), origin=(0., 0., 3.),
                               rotation=rotation, ranges=(distance,))
        self.assertTrue(np.isnan(result[0]))

    def test_elevated_obstacle_and_unknown_surface_are_preserved(self):
        result, _ = self.apply(self.patch(), origin=(0., 0., .25))
        self.assertEqual(result[0], 1.)
        points = self.patch()
        result, _ = self.apply(points, flags=np.zeros(len(points), dtype=bool))
        self.assertEqual(result[0], 1.)

    def test_nearby_nonground_observation_preserves_ambiguous_hit(self):
        points = np.vstack((self.patch(), [[1.05, 0., .08]]))
        flags = np.r_[np.ones(25, dtype=bool), False]
        result, diagnostics = self.apply(points, flags)
        self.assertEqual(result[0], 1.)
        self.assertEqual(diagnostics['ambiguous_returns'], 1)

    def test_missing_sparse_narrow_far_and_discontinuous_support_fail_closed(self):
        line = np.column_stack((np.linspace(.8, 1.2, 10), np.zeros((10, 2))))
        discontinuous = self.patch()
        discontinuous[:12, 2] += .15
        for points in (None, self.patch()[:2], line, self.patch(x=2.), discontinuous):
            result, _ = self.apply(points)
            self.assertEqual(result[0], 1.)

    def test_outside_support_polygon_cannot_extrapolate_over_edge(self):
        triangle = np.array([[.8, -.2, 0.], [.8, .05, 0.], [1.05, -.2, 0.]])
        result, _ = self.apply(triangle)
        self.assertEqual(result[0], 1.)

    def test_sparse_depth_rows_can_support_hit_with_nearby_ground_match(self):
        rows = np.array([[x, y, 0.] for x in (.9, 1.4) for y in (-.2, 0., .2)])
        result, _ = self.apply(rows)
        self.assertTrue(np.isnan(result[0]))

    def test_wider_plane_support_does_not_relax_nearest_match_distance(self):
        rows = np.array([[x, y, 0.] for x in (.6, 1.4) for y in (-.2, 0., .2)])
        result, _ = self.apply(rows)
        self.assertEqual(result[0], 1.)

    def test_multiple_supported_heights_do_not_form_a_false_road_patch(self):
        points = self.patch()
        other = self.patch(x=1.35, z=.18)
        result, _ = self.apply(np.vstack((points, other)))
        self.assertEqual(result[0], 1.)

    def test_raw_invalid_ranges_and_input_array_are_preserved(self):
        raw = np.array([1., np.inf, np.nan, .01, 11.])
        before = raw.copy()
        result, _ = self.apply(self.patch(), ranges=raw)
        np.testing.assert_equal(raw, before)
        np.testing.assert_equal(result[1:], before[1:])

    def test_improper_transform_is_rejected(self):
        with self.assertRaises(ValueError):
            self.apply(self.patch(), rotation=np.zeros((3, 3)))
