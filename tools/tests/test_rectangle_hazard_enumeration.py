"""Hazard-bit rectangle checks must decide exactly like the scalar cell scan.

Grids are deterministic synthetic fixtures; no capture or course data is read.
"""

import math
from pathlib import Path
import random
import sys
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from sensor_route_policy import _rectangle_clear

UNKNOWN, INFLATED, LETHAL = -1, 99, 100
# Asymmetric body: long rear overhang behind the front axle, offset sideways.
BODY = (-.80, .30, -.33, .37)


def hazard_bits(costs, width, height):
    """Per-row bitsets of unknown/lethal cells, as the route search supplies."""
    return [sum(1 << ix for ix in range(width)
                if not 0 <= costs[iy*width+ix] < 100)
            for iy in range(height)]


def both(x, y, yaw, bounds, costs, width, height, resolution=.1, origin=(0., 0.)):
    rows = hazard_bits(costs, width, height)
    costs_before, rows_before = list(costs), list(rows)
    scalar = _rectangle_clear(x, y, yaw, bounds, costs, width, height,
                              resolution, origin)
    bitset = _rectangle_clear(x, y, yaw, bounds, costs, width, height,
                              resolution, origin, rows)
    assert costs == costs_before and rows == rows_before, 'inputs mutated'
    return scalar, bitset


class RectangleHazardEnumerationTest(unittest.TestCase):
    def assertSame(self, *args, expected=None, **kwargs):
        scalar, bitset = both(*args, **kwargs)
        self.assertEqual(scalar, bitset)
        if expected is not None:
            self.assertEqual(bitset, expected)
        return bitset

    def test_empty_grid_is_clear_at_any_heading(self):
        width = height = 40
        costs = [0] * (width*height)
        for k in range(16):
            self.assertSame(2., 2., k*math.pi/8, BODY, costs, width, height,
                            expected=True)

    def test_inflated_99_is_not_a_footprint_hazard_but_100_and_unknown_are(self):
        width = height = 40
        for value, expected in ((INFLATED, True), (LETHAL, False), (UNKNOWN, False),
                                (-7, False), (250, False), (98, True)):
            costs = [0] * (width*height)
            costs[20*width+20] = value
            self.assertSame(2.05, 2.05, .3, BODY, costs, width, height,
                            expected=expected)

    def test_dense_rows_reject(self):
        width = height = 40
        costs = [LETHAL] * (width*height)
        self.assertSame(2., 2., .7, BODY, costs, width, height, expected=False)
        costs = [UNKNOWN if (i % 3) else 0 for i in range(width*height)]
        self.assertSame(2., 2., -1.1, BODY, costs, width, height, expected=False)

    def test_row_hazards_outside_the_column_span_are_ignored(self):
        # Body covers x in [1.8, 2.4]; set bits left of the span must not count.
        width = height = 40
        costs = [0] * (width*height)
        row = 20
        for ix in (0, 6, 7, 8, 25, 39):
            costs[row*width+ix] = LETHAL
        bounds = (-.3, .3, -.05, .05)
        self.assertSame(2.1, 2.05, 0., bounds, costs, width, height, expected=True)
        self.assertSame(2.1, 2.05, math.pi/4, bounds, costs, width, height)
        costs[row*width+21] = UNKNOWN
        self.assertSame(2.1, 2.05, 0., bounds, costs, width, height, expected=False)

    def test_exact_edge_contact_collides_and_gap_is_clear(self):
        # Unit cells: hazard square [5,6]x[5,6]; body x-extent [x-1, x+1].
        width = height = 12
        costs = [0] * (width*height)
        costs[5*width+5] = LETHAL
        bounds = (-1., 1., -.5, .5)
        self.assertSame(4., 5.5, 0., bounds, costs, width, height,
                        resolution=1., expected=False)
        self.assertSame(3.75, 5.5, 0., bounds, costs, width, height,
                        resolution=1., expected=True)
        # Corner touches the square's corner exactly.
        self.assertSame(4., 4.5, 0., (-1., 1., -.5, .5), costs, width, height,
                        resolution=1., expected=False)

    def test_rotated_body_spares_cell_inside_its_bounding_box(self):
        # A 45-degree thin body leaves bounding-box corners empty.
        width = height = 20
        costs = [0] * (width*height)
        costs[7*width+12] = LETHAL
        costs[12*width+8] = LETHAL
        self.assertSame(10., 10., math.pi/4, (-3., 3., -.2, .2), costs,
                        width, height, resolution=1., expected=True)
        # Same row: the first set bit misses the body and a later one hits it.
        costs[12*width+12] = LETHAL
        self.assertSame(10., 10., math.pi/4, (-3., 3., -.2, .2), costs,
                        width, height, resolution=1., expected=False)

    def test_grid_boundary(self):
        width = height = 10
        costs = [0] * (width*height)
        bounds = (-1., 1., -1., 1.)
        # Touching the last cell index is inside; one past is outside.
        self.assertSame(8.5, 5., 0., bounds, costs, width, height,
                        resolution=1., expected=True)
        self.assertSame(9., 5., 0., bounds, costs, width, height,
                        resolution=1., expected=False)
        self.assertSame(.99, 5., 0., bounds, costs, width, height,
                        resolution=1., expected=False)
        self.assertSame(5., 5., 0., bounds, costs, width, height,
                        resolution=1., origin=(-10., 0.), expected=False)
        costs[5*width+9] = LETHAL
        self.assertSame(8.5, 5., 0., bounds, costs, width, height,
                        resolution=1., expected=False)

    def test_wide_grid_rows_beyond_machine_word(self):
        width, height = 300, 30
        costs = [0] * (width*height)
        for ix in (70, 130, 200, 290):
            costs[15*width+ix] = LETHAL
        for x in (7.05, 13.05, 20.05, 25.):
            self.assertSame(x, 1.55, .2, BODY, costs, width, height)

    def test_random_grids_match_scalar_check(self):
        rng = random.Random(57)
        outcomes = set()
        for density in (0., .002, .02, .1, .3, .7):
            width, height = rng.randint(30, 90), rng.randint(30, 70)
            costs = []
            for _ in range(width*height):
                r = rng.random()
                if r < density/2:
                    costs.append(LETHAL)
                elif r < density:
                    costs.append(UNKNOWN)
                elif r < density + .05:
                    costs.append(INFLATED)
                else:
                    costs.append(rng.randint(0, 98))
            origin = (rng.uniform(-3, 3), rng.uniform(-3, 3))
            resolution = rng.choice((.05, .1, .25))
            rows = hazard_bits(costs, width, height)
            costs_before, rows_before = list(costs), list(rows)
            for _ in range(150):
                x = origin[0] + rng.uniform(-.5, width*resolution+.5)
                y = origin[1] + rng.uniform(-.5, height*resolution+.5)
                yaw = rng.uniform(-math.pi, math.pi)
                bounds = rng.choice((BODY, (-.2, .9, -.1, .45),
                                     (-1.4, .1, -.5, .2)))
                args = (x, y, yaw, bounds, costs, width, height, resolution, origin)
                scalar = _rectangle_clear(*args)
                self.assertEqual(_rectangle_clear(*args, rows), scalar, args[:4])
                outcomes.add(scalar)
            self.assertEqual((costs, rows), (costs_before, rows_before))
        self.assertEqual(outcomes, {True, False})


if __name__ == '__main__':
    unittest.main()
