using System;
using System.Collections.Generic;

namespace IGVC.Reference
{
    public static class GeometryChecks
    {
        public static void Run(CheckContext c)
        {
            var course = SyntheticCourses.Stadium();
            var cor = new Corridor(course);
            double expected = 20 * 2 + 2 * Math.PI * 8;
            c.Check(Math.Abs(cor.Length - expected) < .15, "corridor length matches stadium perimeter");
            c.Check(Math.Abs(cor.Kappa[cor.N / 4] - 1.0 / 8) < .01, "left arc curvature is +1/r");
            c.Check(Math.Abs(cor.Kappa[2]) < 1e-6, "straight curvature is zero");
            cor.Project(cor.P[8] + cor.Nl[8] * 1.5, out double ps, out double pd);
            c.Check(Math.Abs(pd - 1.5) < 1e-6 && Math.Abs(ps - cor.S[8]) < 1e-6, "projection on a straight recovers arc length and left offset");

            var rng = new Random(7); bool agree = true;
            for (int k = 0; k < 300 && agree; k++)
            {
                var cap = new Capsule(new V2(rng.NextDouble() * 4 - 2, rng.NextDouble() * 4 - 2), new V2(rng.NextDouble() * 4 - 2, rng.NextDouble() * 4 - 2), rng.NextDouble());
                var p = new V2(rng.NextDouble() * 6 - 3, rng.NextDouble() * 6 - 3); var n = V2.FromAngle(rng.NextDouble() * 6.3);
                bool any = cap.LineInterval(p, n, .2, out double ilo, out double ihi);
                for (double d = -8; d <= 8; d += .01)
                {
                    bool inside = Capsule.SegmentDistance(p + n * d, cap.A, cap.B) <= cap.R + .2;
                    bool claimed = any && d >= ilo - 1e-9 && d <= ihi + 1e-9;
                    double edge = Math.Abs(Capsule.SegmentDistance(p + n * d, cap.A, cap.B) - cap.R - .2);
                    if (inside != claimed && edge > .02) { agree = false; break; }
                }
            }
            c.Check(agree, "capsule line interval equals brute-force membership (300 random cases)");

            var barrel = SyntheticCourses.Barrel("b", 5, 0);
            var withBarrel = new Corridor(SyntheticCourses.Stadium(obstacles: barrel));
            var shapes = withBarrel.Course.Shapes(); var free = new List<Interval>();
            int station = (int)Math.Round(5 / withBarrel.Ds);
            withBarrel.FreeIntervals(station, shapes, .52, free);
            c.Check(free.Count == 2 && Math.Abs(free[0].Hi + .82) < .02 && Math.Abs(free[1].Lo - .82) < .02 && Math.Abs(free[0].Lo + 2.48) < 1e-6, "barrel splits the lane into two intervals with exact clearance");

            var lo = new double[withBarrel.N]; var hi = new double[withBarrel.N];
            var leftRoute = new List<V2> { new V2(0, 1.6), new V2(10, 1.6) };
            int blocked = withBarrel.BoundsFromRoute(leftRoute, shapes, .52, lo, hi);
            c.Check(blocked == 0 && lo[station] > .8 && hi[station] > 2.4, "route homotopy selects the left gap");
            withBarrel.BoundsFromRoute(null, shapes, .52, lo, hi);
            c.Check(hi[station] < -.8 || lo[station] > .8, "without a route a gap (not the blocked centre) is chosen");

            var grid = Rasterizer.Rasterize(withBarrel, shapes);
            c.Check(grid.IsFree(grid.StartCell) && grid.IsFree(grid.GoalCell) && grid.StartCell != grid.GoalCell, "grid start and goal are free and distinct");
            c.Check(grid.Code[grid.CellOf(new V2(5, 0))] == OccupancyGrid.Obstacle && grid.Code[grid.CellOf(new V2(5, 1.6))] == OccupancyGrid.Free, "barrel centre blocked, side gap free");
            c.Check(grid.Code[grid.CellOf(new V2(0, 0))] == OccupancyGrid.Seam && grid.Code[grid.CellOf(new V2(0, 2.6))] != OccupancyGrid.Free, "seam closes the loop and the inflated edge is blocked");

            int hint = -1;
            c.Check(cor.FootprintContact(new V2(2, 0), 0, new RobotLimits(), new Capsule[0], ref hint) == null, "footprint clear on the centre line");
            hint = -1;
            c.Check(cor.FootprintContact(new V2(2, 2.6), 0, new RobotLimits(), new Capsule[0], ref hint) == "lane edge", "footprint detects lane-edge contact");
            hint = -1;
            c.Check(withBarrel.FootprintContact(new V2(5.5, 0), 0, new RobotLimits(), shapes, ref hint) == "obstacle", "footprint detects a barrel under the body");

            if (c.Course == null) { c.Note("no frozen course; real-course geometry checks skipped"); return; }
            var real = new Corridor(c.Course); var realShapes = c.Course.Shapes();
            hint = -1;
            c.Check(real.Length > 50 && real.FootprintContact(new V2(0, 0), real.HeadingAt(0), new RobotLimits(), realShapes, ref hint) == null, "real course: spawn pose is whole-body clear");
            var realGrid = Rasterizer.Rasterize(real, realShapes);
            c.Check(realGrid.IsFree(realGrid.StartCell) && realGrid.IsFree(realGrid.GoalCell), "real course: grid start/goal free");
            var rl = new double[real.N]; var rh = new double[real.N];
            c.Note("real course " + c.Course.Identity + ": length " + real.Length.ToString("0.0") + " m, " + real.N + " stations, grid " + realGrid.W + "x" + realGrid.H
                + ", stations blocked for the inscribed disc: " + real.BoundsFromRoute(null, realShapes, new RobotLimits().InscribedRadius, rl, rh));
        }
    }
}
