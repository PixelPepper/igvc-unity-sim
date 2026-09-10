import unittest
import numpy as np
from igvc_perception.surface_projection import project_observed


K = np.array([[400., 0., 320.], [0., 400., 240.], [0., 0., 1.]])


class SurfaceProjectionTests(unittest.TestCase):
    def test_sloped_observations_keep_distinct_optical_z(self):
        points = np.array([[-1., 0., 4.], [0., 0., 5.], [1., 0., 6.]])
        pixels = (points @ K.T)[:, :2] / points[:, 2, None]
        result = project_observed(pixels, K, np.eye(3), np.zeros(3), points)
        np.testing.assert_allclose(result, points, atol=1e-6)
        self.assertEqual(result.dtype, np.float32)

    def test_raised_world_surface_and_camera_pose(self):
        # Optical forward maps world +X, optical down maps world -Z.
        rotation = np.array([[0., 0., 1.], [-1., 0., 0.], [0., -1., 0.]])
        origin = np.array([2., 1., 1.2])
        world = np.array([[5., 1., .4], [6., .5, .4]])
        optical = (world-origin) @ rotation
        pixels = (optical @ K.T)[:, :2] / optical[:, 2, None]
        np.testing.assert_allclose(project_observed(pixels, K, rotation, origin, world), world, atol=1e-6)

    def test_query_ray_uses_local_observed_depth(self):
        result = project_observed([[324., 240.]], K, np.eye(3), [0., 0., 0.], [[0., 0., 5.]], 4.)
        np.testing.assert_allclose(result, [[.05, 0., 5.]], atol=1e-6)
        self.assertEqual(len(project_observed([[324.01, 240.]], K, np.eye(3), [0., 0., 0.], [[0., 0., 5.]], 4.)), 0)

    def test_ineligible_foreground_occludes_eligible_background(self):
        points = np.array([[0., 0., 7.], [0., 0., 2.]])
        for order in ([0, 1], [1, 0]):
            result = project_observed([[320., 240.]], K, np.eye(3), np.zeros(3), points[order],
                                     eligible_mask=np.array([True, False])[order])
            self.assertEqual(len(result), 0)
        visible = project_observed([[320., 240.]], K, np.eye(3), np.zeros(3), points)
        np.testing.assert_allclose(visible, [[0., 0., 2.]])

    def test_near_ineligible_support_does_not_search_behind_it(self):
        points = [[0., 0., 2.], [.07, 0., 7.]]
        result = project_observed([[320., 240.]], K, np.eye(3), np.zeros(3), points,
                                 eligible_mask=np.array([False, True]))
        self.assertEqual(len(result), 0)

    def test_unsupported_and_out_of_view_queries(self):
        result = project_observed([[400., 240.], [-1., 240.], [640., 240.]], K, np.eye(3),
                                 np.zeros(3), [[0., 0., 3.]])
        self.assertEqual(result.shape, (0, 3))

    def test_nonfinite_and_out_of_range_observations_are_discarded(self):
        points = [[np.nan, 0., 1.], [0., 0., np.inf], [0., 0., -.5], [0., 0., .19], [0., 0., 10.1]]
        self.assertEqual(len(project_observed([[320., 240.]], K, np.eye(3), np.zeros(3), points)), 0)

    def test_invalid_inputs(self):
        args = dict(pixels=[[320., 240.]], k=K, rotation=np.eye(3), origin=np.zeros(3), world_points=[[0., 0., 2.]])
        for override in (dict(pixels=[[np.nan, 0.]]), dict(world_points=[1., 2., 3.]),
                         dict(k=np.zeros((3, 3))), dict(rotation=np.diag([1., 1., -1.])),
                         dict(origin=[0., 0.]), dict(max_pixel_distance=-1.),
                         dict(max_pixel_distance=np.nan), dict(eligible_mask=[1]),
                         dict(eligible_mask=np.array([True, False]))):
            with self.subTest(override=override), self.assertRaises(ValueError):
                project_observed(**(args | override))

    def test_empty_observations(self):
        self.assertEqual(project_observed([[320., 240.]], K, np.eye(3), np.zeros(3), np.empty((0, 3))).shape, (0, 3))


if __name__ == '__main__':
    unittest.main()
