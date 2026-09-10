import math
import unittest
from igvc_gps.geodesy import A, F, LocalFrame, ecef, geodetic


class GeodesyChecks(unittest.TestCase):
    def test_reference_axes(self):
        for lla, expected in [((0, 0, 0), (A, 0, 0)), ((0, 90, 0), (0, A, 0)),
                              ((90, 0, 0), (0, 0, A*(1-F)))]:
            self.assertLess(math.dist(ecef(*lla), expected), 1e-8)

    def test_round_trip_global_and_poles(self):
        for lat, lon, alt in [(42, -83, 0), (-43, 170, 1400), (89.999, -179, -30), (90, 0, 10)]:
            recovered = geodetic(*ecef(lat, lon, alt))
            self.assertLess(math.dist(ecef(*recovered), ecef(lat, lon, alt)), 1e-6)

    def test_local_course_and_reset(self):
        frame = LocalFrame(dict(latitude=42., longitude=-83., altitude=0.))
        for point in [(0, 0, 0), (2, 0, 0), (6, 0, 0), (-50, 30, 1), (1000, -1000, 50)]:
            self.assertLess(math.dist(frame.to_enu(*frame.to_geodetic(*point)), point), 1e-6)
        self.assertGreater(frame.to_geodetic(6, 0)[1], -83)
        self.assertGreater(frame.to_geodetic(0, 6)[0], 42)

    def test_invalid(self):
        for lla in [(91, 0, 0), (0, 181, 0), (0, 0, float('nan'))]:
            with self.assertRaises(ValueError):
                ecef(*lla)


if __name__ == '__main__':
    unittest.main()
