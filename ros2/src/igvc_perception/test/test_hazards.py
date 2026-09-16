import unittest
import cv2
import numpy as np
from igvc_perception.hazards import hazard_pixels


class HazardTests(unittest.TestCase):
    def ground(self):
        return np.full((480, 640, 3), (100, 105, 110), np.uint8)

    def test_perspective_bowl_and_pixel_budget(self):
        rgb = self.ground()
        cv2.ellipse(rgb, (320, 360), (85, 20), 10, 0, 360, (12, 12, 12), -1)
        pixels, mask, count = hazard_pixels(rgb)
        self.assertEqual(count, 1)
        self.assertGreater(len(pixels), 30)
        self.assertLessEqual(len(pixels), 1500)
        self.assertTrue(np.isfinite(pixels).all())
        self.assertEqual(mask.dtype, np.uint8)
        self.assertEqual(mask[360, 320], 255)

    def test_uniform_asphalt_and_dark_sky_rejected(self):
        rgb = self.ground()
        rgb[:280] = 12
        self.assertEqual(hazard_pixels(rgb)[2], 0)
        self.assertEqual(hazard_pixels(self.ground())[2], 0)

    def test_orange_barrel_dark_band_and_white_barricade_rejected(self):
        rgb = self.ground()
        cv2.rectangle(rgb, (100, 280), (220, 420), (220, 80, 20), -1)
        cv2.rectangle(rgb, (100, 325), (220, 340), (12, 12, 12), -1)
        cv2.rectangle(rgb, (350, 300), (600, 320), (245, 245, 245), -1)
        self.assertEqual(hazard_pixels(rgb)[2], 0)

    def test_border_robot_and_border_text_rejected(self):
        rgb = self.ground()
        cv2.rectangle(rgb, (200, 430), (450, 479), (12, 12, 12), -1)
        cv2.putText(rgb, 'TEST', (0, 479), cv2.FONT_HERSHEY_SIMPLEX, 1, (12, 12, 12), 2)
        self.assertEqual(hazard_pixels(rgb)[2], 0)

    def test_colored_barrel_shadow_rejected_but_separate_bowl_retained(self):
        colors = {'red': (210, 30, 55), 'orange': (210, 90, 30),
                  'blue': (30, 55, 210), 'green': (30, 170, 55),
                  'yellow': (230, 210, 30)}
        for name, color in colors.items():
            with self.subTest(color=name):
                rgb = self.ground()
                cv2.rectangle(rgb, (100, 280), (220, 370), color, -1)
                cv2.rectangle(rgb, (100, 310), (220, 325), (245, 245, 245), -1)
                cv2.ellipse(rgb, (165, 380), (45, 12), 0, 0, 360, (12, 12, 12), -1)
                cv2.ellipse(rgb, (440, 380), (45, 12), 0, 0, 360, (12, 12, 12), -1)
                _, mask, count = hazard_pixels(rgb)
                self.assertEqual(count, 1)
                self.assertEqual(mask[380, 165], 0)
                self.assertEqual(mask[380, 440], 255)

    def test_broad_dark_patch_and_thin_stroke_rejected(self):
        rgb = self.ground()
        cv2.rectangle(rgb, (30, 290), (260, 430), (12, 12, 12), -1)
        cv2.line(rgb, (320, 370), (600, 370), (12, 12, 12), 4)
        self.assertEqual(hazard_pixels(rgb)[2], 0)

    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):
            hazard_pixels(np.zeros((20, 20), np.uint8))


if __name__ == '__main__':
    unittest.main()
