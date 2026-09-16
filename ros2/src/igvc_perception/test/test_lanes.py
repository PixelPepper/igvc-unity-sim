import unittest
import cv2
import numpy as np
from igvc_perception.lanes import lane_pixels, project_ground


class LaneGeometryTests(unittest.TestCase):
    def test_gray_road_and_horizontal_barrel_band_rejected(self):
        image = np.full((480, 640, 3), 145, np.uint8)
        cv2.rectangle(image, (230, 280), (410, 400), (210, 55, 30), -1)
        cv2.rectangle(image, (230, 315), (410, 335), (255, 255, 255), -1)
        self.assertEqual(len(lane_pixels(image)[0]), 0)

    def test_paint_touching_barrel_band_keeps_paint_only(self):
        colors = {'red': (210, 30, 55), 'orange': (210, 90, 30),
                  'blue': (30, 55, 210), 'green': (30, 170, 55),
                  'yellow': (230, 210, 30)}
        for name, color in colors.items():
            with self.subTest(color=name):
                image = np.full((480, 640, 3), 145, np.uint8)
                cv2.line(image, (30, 430), (240, 325), (245, 245, 245), 4)
                cv2.rectangle(image, (230, 280), (410, 400), color, -1)
                cv2.rectangle(image, (230, 315), (410, 335), (245, 245, 245), -1)
                pixels, mask, count = lane_pixels(image)
                self.assertGreater(len(pixels), 100)
                self.assertEqual(count, 1)
                self.assertGreater(np.count_nonzero(mask[:, :220]), 100)
                self.assertEqual(np.count_nonzero(mask[315:336, 230:411]), 0)

    def test_converging_lane_paint_is_retained(self):
        image = np.full((480, 640, 3), 110, np.uint8)
        cv2.line(image, (95, 479), (270, 235), (245, 245, 245), 8)
        cv2.line(image, (540, 479), (370, 235), (245, 245, 245), 8)
        points, _, components = lane_pixels(image)
        self.assertEqual(components, 2)
        self.assertGreater(len(points), 100)

    def test_thin_paint_above_midpoint_with_downward_camera(self):
        image = np.full((480, 640, 3), (100, 105, 110), np.uint8)
        cv2.line(image, (80, 260), (240, 215), (245, 245, 245), 2)
        points, _, components = lane_pixels(image)
        self.assertEqual(components, 1)
        self.assertGreater(len(points), 60)
        self.assertLess(points[:, 1].max(), 264)
        # The same elevated pixels are valid ground rays at ten degrees down.
        a = np.pi/18
        tilt = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
        rotation = tilt @ np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0.]])
        k = np.array([[471, 0, 320], [0, 471, 240], [0, 0, 1.]])
        self.assertGreater(len(project_ground(points, k, rotation, (0, 0, 1.1))), 0)

    def test_one_pixel_paint_survives_without_accepting_speckles(self):
        image = np.full((480, 640, 3), (100, 105, 110), np.uint8)
        cv2.line(image, (350, 230), (620, 290), (245, 245, 245), 1)
        # Separated high-value asphalt noise must still fail component tests.
        image[330:450:9, 40:280:9] = 245
        pixels, mask, count = lane_pixels(image)
        self.assertEqual(count, 1)
        self.assertGreater(len(pixels), 100)
        self.assertEqual(np.count_nonzero(mask[330:]), 0)

    def test_nearly_horizontal_turn_paint_retained_with_barrel_rejected(self):
        image = np.full((480, 640, 3), 145, np.uint8)
        cv2.rectangle(image, (40, 280), (160, 400), (210, 55, 30), -1)
        cv2.rectangle(image, (40, 325), (160, 345), (255, 255, 255), -1)
        cv2.line(image, (280, 295), (639, 360), (245, 245, 245), 8)
        points, mask, components = lane_pixels(image)
        self.assertEqual(components, 1)
        self.assertGreater(len(points), 100)
        self.assertEqual(np.count_nonzero(mask[:, 40:161]), 0)

    def test_curved_paint_retained_but_bright_solid_blob_rejected(self):
        image = np.full((480, 640, 3), 145, np.uint8)
        cv2.ellipse(image, (150, 350), (100, 65), 0, -90, 90, (245, 245, 245), 8)
        cv2.rectangle(image, (400, 300), (500, 400), (245, 245, 245), -1)
        _, mask, components = lane_pixels(image)
        self.assertEqual(components, 1)
        self.assertGreater(np.count_nonzero(mask[:, :300]), 100)
        self.assertEqual(np.count_nonzero(mask[:, 400:501]), 0)

    def test_level_optical_camera_projects_known_3_and_8_metre_points(self):
        k = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1.]])
        # optical right->world-Y, down->world-Z, forward->world+X.
        rotation = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0.]])
        points = project_ground(np.array([[320, 240+500/3], [320, 240+500/8]]),
                                k, rotation, (0, 0, 1.195), .195)
        np.testing.assert_allclose(points, [[3, 0, .195], [8, 0, .195]], atol=1e-6)

    def test_horizon_and_sky_do_not_project(self):
        k = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1.]])
        rotation = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0.]])
        self.assertEqual(len(project_ground(np.array([[320, 240], [320, 100]]), k, rotation, (0, 0, 1))), 0)

    def test_pitched_camera_preserves_ground_targets(self):
        angle = .25
        k = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1.]])
        tilt = np.array([[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]])
        rotation = tilt @ np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0.]])
        origin = np.array([0, 0, 1.2])
        expected = np.array([[3, .6, 0], [8, -.8, 0]])
        optical = (expected-origin) @ rotation
        pixels = optical @ k.T
        pixels = pixels[:, :2]/pixels[:, 2:]
        np.testing.assert_allclose(project_ground(pixels, k, rotation, origin, 0), expected, atol=1e-6)


if __name__ == '__main__':
    unittest.main()
