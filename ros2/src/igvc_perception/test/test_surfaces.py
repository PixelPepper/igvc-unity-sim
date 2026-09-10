import math
import unittest
import numpy as np
from igvc_perception.surfaces import classify_surfaces
from igvc_perception.ground import estimate_ground


K = np.array([[235., 0, 159.5], [0, 235., 119.5], [0, 0, 1.]])


def render(origin=(0., 0., 1.1), pitch=10., yaw=0., ramp=False, block=False):
    """Independent ray intersections against finite surveyed plane patches."""
    p, a = math.radians(pitch), math.radians(yaw)
    rotation = np.array([[0, -math.sin(p), math.cos(p)], [-1, 0, 0],
                         [0, -math.cos(p), -math.sin(p)]])
    rotation = np.array([[math.cos(a), -math.sin(a), 0],
                         [math.sin(a), math.cos(a), 0], [0, 0, 1]]) @ rotation
    origin = np.array(origin, dtype=float)
    rows, cols = np.mgrid[:240, :320]
    rays = np.stack(((cols-159.5)/235, (rows-119.5)/235, np.ones_like(rows)), -1) @ rotation.T
    distance = np.full(rows.shape, np.inf)

    def patch(normal, offset, limits):
        with np.errstate(divide='ignore', invalid='ignore'):
            t = -(origin @ normal + offset) / (rays @ normal)
            world = origin + t[..., None] * rays
        valid = np.isfinite(t) & (t >= .2) & (t <= 10.)
        for axis, low, high in limits:
            valid &= (world[..., axis] >= low) & (world[..., axis] <= high)
        np.minimum(distance, np.where(valid, t, np.inf), out=distance)

    if ramp:
        for low, high, slope, intercept in [(-100, 2, 0, 0), (2, 5, .4/3, -.8/3),
                                            (5, 7, 0, .4), (7, 10, -.4/3, 4/3), (10, 100, 0, 0)]:
            patch(np.array([-slope, 0, 1]), -intercept, [(0, low, high)])
    else:
        patch(np.array([0, 0, 1]), 0, [])
    if block:
        # Broad elevated top plus four vertical walls, blocking line of sight.
        patch(np.array([0, 0, 1]), -.5, [(0, 3, 4), (1, -.65, .65)])
        for x in (3, 4):
            patch(np.array([1, 0, 0]), -x, [(1, -.65, .65), (2, 0, .5)])
        for y in (-.65, .65):
            patch(np.array([0, 1, 0]), -y, [(0, 3, 4), (2, 0, .5)])
    distance[~np.isfinite(distance)] = np.nan
    return distance.astype(np.float32), rotation, origin


def fit(depth, rotation, origin):
    rows, cols = np.mgrid[0:240:4, 0:320:4]
    rays = np.stack(((cols-159.5)/235, (rows-119.5)/235, np.ones_like(rows)), -1)
    world = rays * depth[::4, ::4, None] @ rotation.T + origin
    points = world[(rows >= 160) & np.isfinite(world).all(-1)]
    return estimate_ground(points, origin)


class SurfaceTests(unittest.TestCase):
    def test_flat_rotated_camera(self):
        depth, rotation, origin = render(yaw=37)
        result = classify_surfaces(depth, K, rotation, origin, fit(depth, rotation, origin))
        self.assertEqual(result['grid_world'].shape, (60, 80, 3))
        self.assertEqual(result['grid_world'].dtype, np.float32)
        self.assertGreater(result['ground_mask'].sum(), 1800)
        self.assertEqual(len(result['obstacles']), 0)
        self.assertLess(np.nanmax(np.abs(result['grid_world'][..., 2])), 1e-6)

    def test_ramp_deck_and_descent_connected_from_observations(self):
        for origin in [(0, 0, 1.1), (3, 0, 1.1+.4/3), (6, 0, 1.5), (8, 0, 1.1+.8/3)]:
            with self.subTest(origin=origin):
                depth, rotation, eye = render(origin, ramp=True)
                result = classify_surfaces(depth, K, rotation, eye, fit(depth, rotation, eye))
                self.assertGreater(result['ground_mask'].sum(), 1000)
                self.assertEqual(len(result['obstacles']), 0)
                if origin[0] == 0:
                    ground = result['grid_world'][result['ground_mask']]
                    self.assertTrue(np.any(ground[:, 2] > .39))

    def test_elevated_top_and_walls_not_ground(self):
        depth, rotation, origin = render(block=True)
        result = classify_surfaces(depth, K, rotation, origin, fit(depth, rotation, origin))
        world = result['grid_world']
        top = result['valid_mask'] & (world[..., 2] > .49)
        self.assertGreater(top.sum(), 30)
        self.assertFalse(result['ground_mask'][top].any())
        self.assertGreater(len(result['obstacles']), 100)
        self.assertTrue(np.any(result['obstacles'][:, 2] > .49))

    def test_sparse_deck_crest_uses_observed_deck_tangent(self):
        # A camera behind the origin puts a long deck edge immediately above a
        # crest sample whose shorter derivative follows the incline instead.
        depth, rotation, origin = render((-.525, 0, 1.1), ramp=True)
        result = classify_surfaces(depth, K, rotation, origin, fit(depth, rotation, origin))
        self.assertEqual(len(result['obstacles']), 0)
        world = result['grid_world']
        crest = result['valid_mask'] & (world[..., 0] > 5.8) & (world[..., 0] < 6)
        self.assertGreater(crest.sum(), 20)
        self.assertTrue(result['ground_mask'][crest].all())

    def test_missing_depth_does_not_bridge(self):
        depth, rotation, origin = render()
        # The upper surface region has no adjacency to lower-image seed rows.
        depth[144:160] = np.nan
        result = classify_surfaces(depth, K, rotation, origin, fit(depth, rotation, origin))
        self.assertFalse(result['ground_mask'][:40].any())
        self.assertFalse(result['valid_mask'][36:40].any())
        self.assertTrue(np.isnan(result['grid_world'][36:40]).all())

    def test_invalid_input_and_no_seeds(self):
        depth, rotation, origin = render()
        plane = fit(depth, rotation, origin)
        for image, intrinsics, rot, eye, observed in [
                (depth[:100], K, rotation, origin, plane),
                (depth, K*0, rotation, origin, plane),
                (depth, K, rotation*2, origin, plane),
                (depth, K, rotation, [0, np.nan, 1], plane),
                (depth, K, rotation, origin, {'normal':[0, 0, 2], 'offset':0}),
                (np.full_like(depth, np.nan), K, rotation, origin, plane)]:
            with self.assertRaises(ValueError):
                classify_surfaces(image, intrinsics, rot, eye, observed)


if __name__ == '__main__':
    unittest.main()
