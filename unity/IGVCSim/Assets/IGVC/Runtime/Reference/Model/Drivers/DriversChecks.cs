using System;
using System.Collections.Generic;
using IGVC.Reference.RacingLine;

namespace IGVC.Reference.Drivers
{
    /// <summary>Behavioural checks: diff-drive limits, sensors, lap completion without whole-body contact, bounds, determinism, training.</summary>
    public static class DriversChecks
    {
        public static void Run(CheckContext c)
        {
            ModelChecks(c);
            var barrels = new[] { SyntheticCourses.Barrel("b1", 5, 0), SyntheticCourses.Barrel("b2", -3, 16.9), SyntheticCourses.Barrel("b3", 15.5, 9) };
            TrackerChecks(c, "stadium", SyntheticCourses.Stadium(), 1.0, true);
            TrackerChecks(c, "stadium+barrels", SyntheticCourses.Stadium(obstacles: barrels), 1.0, false);
            NeuralChecks(c);
            if (c.Course != null) RealCourse(c);
        }

        private static void ModelChecks(CheckContext c)
        {
            var r = new RobotLimits(); var s = new RobotState { Heading = 0 };
            bool wheels = true, accel = true;
            double prevL = 0, prevR = 0;
            for (int k = 0; k < 400; k++)
            {
                double v = k < 200 ? 5 : -5, w = k % 50 < 25 ? 3 : -3;
                DiffDrive.Step(ref s, v, w, .05, r);
                wheels &= Math.Abs(s.WheelL) <= r.MaxSpeed + 1e-9 && Math.Abs(s.WheelR) <= r.MaxSpeed + 1e-9 && s.V >= -r.MaxReverse - 1e-9 && Math.Abs(s.Omega) <= r.MaxYawRate + 1e-9;
                accel &= Math.Abs(s.WheelL - prevL) <= Math.Max(r.MaxAccel, r.MaxBrake) * .05 + 1e-9 && Math.Abs(s.WheelR - prevR) <= Math.Max(r.MaxAccel, r.MaxBrake) * .05 + 1e-9;
                prevL = s.WheelL; prevR = s.WheelR;
            }
            c.Check(wheels && accel, "diff drive keeps wheel ceiling, reverse limit, yaw-rate limit and wheel acceleration limits under saturating commands");
            s = new RobotState();
            var pts = new List<V2>();
            for (int k = 0; k < 2000; k++) { DiffDrive.Step(ref s, .8, .4, .02, r); if (k > 400) pts.Add(s.Pos); }
            V2 centre = new V2(0, 0); foreach (var p in pts) centre += p / pts.Count;
            double rad = 0; foreach (var p in pts) rad += V2.Distance(p, centre) / pts.Count;
            c.Check(Math.Abs(rad - 2) < .02, "steady (v, omega) = (0.8, 0.4) drives a 2 m circle (" + rad.ToString("0.000") + " m)");

            var cor = new Corridor(SyntheticCourses.Stadium(obstacles: SyntheticCourses.Barrel("b", 5, 0)));
            var world = new DriveWorld(cor, cor.Course.Shapes(), r);
            double left = world.Raycast(new V2(0, 0), new V2(0, 1), 5, world.Far[0]);
            double ahead = world.Raycast(new V2(0, 0), new V2(1, 0), 8, world.Far[0]);
            c.Check(Math.Abs(left - 3) < .1 && Math.Abs(ahead - 4.7) < .05, "sphere-traced rays hit the lane edge (" + left.ToString("0.00") + " m) and the barrel (" + ahead.ToString("0.00") + " m)");
        }

        private static DriversStudy Drive(Corridor cor, Capsule[] shapes, RacingLineStudy line, double ceiling, double[] genome = null)
        {
            var d = new DriversStudy(cor, shapes, line.Limits, line) { SpeedCeiling = ceiling, NeuralGenome = genome };
            d.Restart(); d.RunToEnd();
            return d;
        }

        private static void TrackerChecks(CheckContext c, string name, CourseGeometry course, double ceiling, bool determinism)
        {
            var watch = System.Diagnostics.Stopwatch.StartNew();
            var cor = new Corridor(course); var shapes = course.Shapes(); var limits = new RobotLimits();
            var line = new RacingLineStudy(cor, shapes, limits) { SpeedCeiling = ceiling };
            foreach (var _ in line.Run()) { }
            var d = Drive(cor, shapes, line, ceiling);
            foreach (var l in d.Summary()) c.Note(name + " @" + ceiling + " | " + l);
            bool all = true;
            foreach (var g in d.Ghosts) all &= g.Completed && g.Contacts == 0;
            c.Check(all, name + ": pure pursuit, Stanley and MPC each complete a lap at " + ceiling + " m/s with zero whole-body contacts");

            // Lower bound: fastest standing lap over every line method with the bare inscribed-disc bounds.
            var bound = new RacingLineStudy(cor, shapes, limits) { SpeedCeiling = ceiling, ExtraMargin = 0, GaGenerations = 15, DescentIterations = 20 };
            foreach (var _ in bound.CompareAll()) { }
            double lb = double.MaxValue; foreach (var row in bound.Comparison) lb = Math.Min(lb, row.StandingLap);
            bool slower = true; foreach (var g in d.Ghosts) slower &= !g.Completed || g.LapTime >= lb - 1e-6;
            c.Check(slower, name + ": no ghost beats the lap-time lower bound for the same limits (" + lb.ToString("0.00") + " s)");

            if (determinism)
            {
                var again = Drive(cor, shapes, line, ceiling); bool same = true;
                for (int i = 0; i < d.Ghosts.Count; i++)
                {
                    Ghost a = d.Ghosts[i], b = again.Ghosts[i];
                    same &= a.LapTime == b.LapTime && a.Contacts == b.Contacts && a.MinClearance == b.MinClearance && a.MeanCte == b.MeanCte && a.MaxSpeed == b.MaxSpeed;
                }
                c.Check(same, name + ": same inputs give identical ghost metrics");
            }
            c.Note(name + ": driver checks " + watch.ElapsedMilliseconds + " ms");
        }

        private static void NeuralChecks(CheckContext c)
        {
            var watch = System.Diagnostics.Stopwatch.StartNew();
            var cor = new Corridor(SyntheticCourses.Stadium()); var limits = new RobotLimits();
            var line = new RacingLineStudy(cor, new Capsule[0], limits) { SpeedCeiling = 1.0 };
            var d = new DriversStudy(cor, new Capsule[0], limits, line) { SpeedCeiling = 1.0 };
            string last = ""; int items = 0;
            foreach (var l in d.TrainNeural(4, 7)) { last = l; items++; }
            var ga = d.Trainer.GA;
            c.Note("neural: " + last + "; best per generation " + string.Join(", ", ga.BestHistory.ConvertAll(x => x.ToString("0.0"))) + "; " + items + " frame steps, " + watch.ElapsedMilliseconds + " ms");
            c.Check(ga.BestFitness > ga.BestHistory[0] + 1e-9, "neuroevolution: a short seeded budget improves best fitness over generation 0");
            bool mono = true; for (int k = 1; k < ga.BestHistory.Count; k++) mono &= ga.BestHistory[k] >= ga.BestHistory[k - 1] - 1e-12;
            c.Check(mono, "neuroevolution: best fitness never decreases (elitism, deterministic episodes)");
            var d2 = new DriversStudy(cor, new Capsule[0], limits, line) { SpeedCeiling = 1.0 };
            foreach (var _ in d2.TrainNeural(4, 7)) { }
            c.Check(d2.Trainer.GA.BestFitness == ga.BestFitness, "neuroevolution is deterministic for a seed");
            d.Restart(); d.RunToEnd();
            foreach (var l in d.Summary()) c.Note("neural stadium | " + l);
        }

        private static void RealCourse(CheckContext c)
        {
            var course = c.Course; var cor = new Corridor(course); var shapes = course.Shapes(); var limits = new RobotLimits();
            foreach (double ceiling in new[] { .6, 1.2, 1.8, 2.2 })
            {
                var watch = System.Diagnostics.Stopwatch.StartNew();
                var line = new RacingLineStudy(cor, shapes, limits) { SpeedCeiling = ceiling };
                foreach (var _ in line.Run()) { }
                var d = Drive(cor, shapes, line, ceiling);
                c.Note("real course @" + ceiling + " m/s: reference line " + line.Lap.LapTime.ToString("0.00") + " s flying, " + line.LineContactStations.Count + " body contacts along it, blocked stations " + line.BlockedStations + "; drive " + watch.ElapsedMilliseconds + " ms");
                foreach (var l in d.Summary()) c.Note("real course @" + ceiling + " | " + l);
                if (ceiling == .6)
                {
                    var pp = d.Ghosts[0];
                    c.Check(pp.Completed && pp.Contacts == 0, "real course: pure pursuit completes a lap at 0.6 m/s with zero whole-body contacts");
                }
            }
        }
    }
}
