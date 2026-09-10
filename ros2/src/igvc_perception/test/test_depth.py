import unittest
import numpy as np
from igvc_perception.depth import depth_points, obstacle_points


class DepthTests(unittest.TestCase):
    def setUp(self):
        self.k = np.array([[100., 0, 160], [0, 100., 120], [0, 0, 1.]])

    def image(self):
        return np.full((240, 320), np.nan, np.float32)

    def test_off_axis_depth_is_z_not_radial_range(self):
        depth = self.image()
        depth[120, 260] = 2
        points = depth_points(depth, self.k, stride=1)
        np.testing.assert_allclose(points, [[2, 0, 2]])
        self.assertGreater(np.linalg.norm(points[0]), 2)

    def test_top_to_bottom_rows_map_to_optical_down(self):
        depth = self.image()
        depth[20, 160] = depth[220, 160] = 1
        np.testing.assert_allclose(depth_points(depth, self.k, 1), [[0, -1, 1], [0, 1, 1]])

    def test_invalid_and_out_of_range_values_drop(self):
        depth = self.image()
        depth[120, 156:165] = [np.nan, np.inf, -np.inf, -.1, 0, .19, .2, 10, 10.01]
        points = depth_points(depth, self.k, 1)
        self.assertEqual(points.shape, (2, 3))
        np.testing.assert_allclose(points[:, 2], [.2, 10])
        self.assertTrue(np.isfinite(points).all())

    def test_stride_and_empty_output_shape(self):
        depth = self.image()
        self.assertEqual(depth_points(depth, self.k).shape, (0, 3))
        depth[:] = 1
        self.assertEqual(depth_points(depth, self.k).shape, (60*80, 3))
        self.assertEqual(depth_points(depth, self.k).dtype, np.float32)

    def test_dimensions_intrinsics_and_stride_validation(self):
        for image in [np.ones((480, 640), np.float32), np.ones((240, 320), np.uint16)]:
            with self.assertRaises(ValueError):
                depth_points(image, self.k)
        for k in [np.zeros((3, 3)), self.k*np.nan, np.eye(2),
                  [[100, 0, 320], [0, 100, 120], [0, 0, 1]]]:
            with self.assertRaises(ValueError):
                depth_points(self.image(), k)
        for stride in [0, -1, 1.5, True]:
            with self.assertRaises(ValueError):
                depth_points(self.image(), self.k, stride)

    def test_pitch_transform_excludes_ground_retains_box(self):
        angle = np.deg2rad(10)
        tilt = np.array([[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]])
        rotation = tilt @ np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0.]])
        origin = np.array([1., 2., 1.2])
        world = np.array([[4, 2, 0], [4, 2, .5], [4, 2, 2.]])
        optical = (world-origin) @ rotation
        np.testing.assert_allclose(obstacle_points(optical, rotation, origin), [[4, 2, .5]], atol=1e-6)

    def test_height_range_and_nonfinite_obstacles(self):
        points = np.array([[0, 0, 1], [10, 0, 1], [0, 0, np.nan], [0, 0, -1], [0, 0, 1.9]])
        np.testing.assert_allclose(obstacle_points(points, np.eye(3), [0, 0, 0]), [[0, 0, 1]])
        self.assertEqual(obstacle_points(np.empty((0, 3)), np.eye(3), [0, 0, 0]).shape, (0, 3))

    def test_bad_transform_rejected(self):
        for rotation, origin in [(np.eye(3)*2, [0, 0, 0]), (np.diag([-1, 1, 1]), [0, 0, 0]),
                                 (np.eye(3), [0, np.inf, 0])]:
            with self.assertRaises(ValueError):
                obstacle_points([[0, 0, 1]], rotation, origin)


if __name__ == '__main__':
    unittest.main()
