using System;
using System.Collections.Generic;
using System.IO;

namespace IGVC.Reference.Teacher
{
    /// <summary>Behavioural checks of the hindsight teacher (synthetic dead end, descent, determinism, geodesy, real run).</summary>
    public static class TeacherChecks
    {
        /// <summary>Set by the dotnet harness (JSON/gzip I/O lives outside the model); null in Unity = real-run checks skipped.</summary>
        public static Func<string, RunIn> RunLoader;
        public static string RealRunDir;

        public static void Run(CheckContext c)
        {
            DeadEnd(c);
            CorridorPath(c);
            Geodesy(c);
            Real(c);
        }

        /// <summary>Lane split by a long divider; the left sub-lane is capped (dead end), the right one is open.</summary>
        public static CourseGeometry DeadEndCourse() => SyntheticCourses.Stadium(40, 8, 3, .25,
            new CourseObstacle { Id = "divider", Kind = "barricade", X = 5, Y = 0, Yaw = 0, Length = 8, Width = .4 },
            new CourseObstacle { Id = "cap", Kind = "barricade", X = 8, Y = 1.8, Yaw = Math.PI / 2, Length = 2, Width = .4 });

        public static RunIn DeadEndRun()
        {
            var run = new RunIn { Name = "synthetic-dead-end", Course = DeadEndCourse(), Status = "stopped", Reason = "synthetic" };
            run.Goals.Add(new V2(16, 0));
            V2 pocket = new V2(5, 1.6), open = new V2(5, -1.6);
            for (int k = 0; k < 3; k++)
            {
                var s = new SnapshotIn { Index = k + 1, DestinationIndex = 0, Robot = new V2(k * .1, 0), Yaw = 0, Destination = new V2(16, 0), StampS = 10 + k, Action = "sent_goal" };
                s.Candidates = new List<CandidateIn> { new CandidateIn { End = pocket, Source = "lane" }, new CandidateIn { End = open, Source = "gps" } };
                s.Plan = new CandidateIn { End = k == 1 ? open : pocket, Source = k == 1 ? "gps" : "lane" };
                run.Snapshots.Add(s);
            }
            // Robot drives into the pocket and sits there for 30 s (a trap), sampled at 10 Hz.
            var t = new List<double>(); var p = new List<V2>(); var yaw = new List<double>();
            for (int i = 0; i <= 400; i++)
            {
                double time = 10 + i * .1; V2 q = time < 20 ? V2.Lerp(new V2(0, 0), new V2(6, 1.6), (time - 10) / 10) : new V2(6, 1.6);
                t.Add(time); p.Add(q); yaw.Add(.26);
            }
            run.TrajT = t.ToArray(); run.TrajP = p.ToArray(); run.TrajYaw = yaw.ToArray();
            return run;
        }

        static void DeadEnd(CheckContext c)
        {
            var run = DeadEndRun();
            var options = new LabelOptions { SpeedCeilings = new[] { .6 } };
            var teacher = new HindsightTeacher(run.Course);
            var res = new Labeler(teacher, options).Label(run);
            var l = res.Labels[0];
            c.Check(l.Candidates.Count == 2 && l.BestCandidate == 1 && l.Candidates[0].Cost > l.Candidates[1].Cost + 2, "teacher: open side strictly preferred over dead end (" + l.Candidates[0].Cost.ToString("0.0") + " vs " + l.Candidates[1].Cost.ToString("0.0") + " m)");
            c.Check(l.RegretM > 2 && res.Labels[1].RegretM == 0, "teacher: choosing the dead end has regret, the open side none");
            c.Check(l.LocalGoal.Y < -.5 && Math.Abs(l.HeadingError) < Math.PI / 2, "teacher: local goal on the open side, ahead of the robot");
            var f = teacher.FieldFor(new V2(16, 0)); var cells = new List<int>();
            var route = teacher.Route(f, new V2(0, 0), double.PositiveInfinity, cells);
            bool down = cells.Count > 10; for (int i = 1; i < cells.Count; i++) down &= f[cells[i]] < f[cells[i - 1]];
            c.Check(down && f[cells[cells.Count - 1]] == 0, "teacher: cost-to-go strictly decreases along the route to the goal (" + cells.Count + " cells)");
            c.Check(res.Traps.Count == 1 && res.Traps[0].Duration >= 25 && Labeler.Side(res.Traps[0].ApproachRoute, run.Course.Obstacles[0].Shape, 2.5) == "south", "teacher: dead-end stall reported as a trap, teacher passes the divider to the south");
            var again = new Labeler(new HindsightTeacher(DeadEndCourse()), options).Label(DeadEndRun());
            bool same = again.Lines.Count == res.Lines.Count && again.Summary == res.Summary && again.TrapsJson == res.TrapsJson;
            for (int i = 0; same && i < res.Lines.Count; i++) same = res.Lines[i] == again.Lines[i];
            c.Check(same, "teacher: labels identical across two runs");
        }

        /// <summary>A wall crosses the straight line to corridor entry A (open behind it via a gap near the north edge);
        /// entry B is in plain view. A route candidate with a logged path rides along.</summary>
        public static CourseGeometry WallCourse() => SyntheticCourses.Stadium(40, 8, 3, .25,
            new CourseObstacle { Id = "wall", Kind = "barricade", X = 3, Y = -1.5, Yaw = Math.PI / 2, Length = 4, Width = .4 });
        /// <summary>The robot is boxed in by four barricades: every entry outside is unreachable from it.</summary>
        public static CourseGeometry BoxCourse() => SyntheticCourses.Stadium(40, 8, 3, .25,
            new CourseObstacle { Id = "e", Kind = "barricade", X = 1.5, Y = 0, Yaw = Math.PI / 2, Length = 3.4, Width = .4 },
            new CourseObstacle { Id = "w", Kind = "barricade", X = -1.5, Y = 0, Yaw = Math.PI / 2, Length = 3.4, Width = .4 },
            new CourseObstacle { Id = "n", Kind = "barricade", X = 0, Y = 1.5, Yaw = 0, Length = 3.4, Width = .4 },
            new CourseObstacle { Id = "s", Kind = "barricade", X = 0, Y = -1.5, Yaw = 0, Length = 3.4, Width = .4 });
        public static readonly V2 BehindWall = new V2(4, -1.5), InView = new V2(3.5, 2);

        public static RunIn CorridorRun(CourseGeometry course, string name, params V2[] entries)
        {
            var run = new RunIn { Name = name, Course = course, Status = "stopped", Reason = "synthetic" };
            run.Goals.Add(new V2(16, 0));
            var s = new SnapshotIn { Index = 1, DestinationIndex = 0, Robot = new V2(0, 0), Yaw = 0, Destination = new V2(16, 0), StampS = 10, Action = "sent_goal" };
            s.Candidates = new List<CandidateIn>();
            foreach (var e in entries) s.Candidates.Add(new CandidateIn { End = e, Source = Labeler.CorridorSource, Score = 1 });
            // Route candidate with a logged path straight through the wall: its label must not depend on the corridor version.
            s.Candidates.Add(new CandidateIn { End = new V2(5, -1), Source = "grid", Path = new List<V2> { new V2(0, 0), new V2(2.5, -.5), new V2(5, -1) } });
            s.Plan = new CandidateIn { End = entries[0], Source = "observed_lane_corridor" };
            run.Snapshots.Add(s);
            run.TrajT = new[] { 10.0, 11 }; run.TrajP = new[] { new V2(0, 0), new V2(.5, 0) }; run.TrajYaw = new[] { 0.0, 0 };
            return run;
        }

        static void CorridorPath(CheckContext c)
        {
            var o1 = new LabelOptions { SpeedCeilings = new[] { .6 }, CorridorCost = LabelOptions.StraightV1 };
            var o2 = new LabelOptions { SpeedCeilings = new[] { .6 } };
            var teacher = new HindsightTeacher(WallCourse());
            var v1 = new Labeler(teacher, o1).Label(CorridorRun(WallCourse(), "synthetic-wall", BehindWall, InView));
            var v2 = new Labeler(teacher, o2).Label(CorridorRun(WallCourse(), "synthetic-wall", BehindWall, InView));
            CandLabel a1 = v1.Labels[0].Candidates[0], b1 = v1.Labels[0].Candidates[1], a2 = v2.Labels[0].Candidates[0], b2 = v2.Labels[0].Candidates[1];
            string F1(double v) => v.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture);
            c.Check(!a2.LineOfSight && !a2.EntryUnreachable && a2.EntryPathM > a2.StraightM + 1 && a2.Cost > a1.Cost + 1,
                "teacher path-v2: wall across the straight line makes the entry leg longer (" + F1(a2.StraightM) + " m straight, " + F1(a2.EntryPathM) + " m grid path)");
            c.Check(b2.LineOfSight && b2.Cost == b1.Cost && b2.EntryPathM == b2.StraightM, "teacher path-v2: an entry in plain view keeps its straight-line cost (" + F1(b2.Cost) + " m)");
            // Within the corridor group (build_dataset --kind corridor ranks corridor candidates only).
            c.Check(a1.Cost < b1.Cost - .2 && b2.Cost < a2.Cost - .2 && a2.Regret > b2.Regret,
                "teacher path-v2: prefers the reachable entry in view (" + F1(b2.Cost) + " vs " + F1(a2.Cost) + " m); straight-v1 preferred the one behind the wall (" + F1(a1.Cost) + " vs " + F1(b1.Cost) + " m)");
            bool routeSame = Labeler.CandidateJson(v1.Labels[0].Candidates[2]) == Labeler.CandidateJson(v2.Labels[0].Candidates[2]) && v1.Labels[0].Candidates[2].Cost > 0
                && Labeler.CandidateJson(v1.Labels[0].Plan) == Labeler.CandidateJson(v2.Labels[0].Plan);
            c.Check(routeSame && v2.Lines[0].Contains("\"corridor_cost\":\"path-v2\"") && v1.Summary.Contains("\"corridor_cost\":\"straight-v1\""),
                "teacher path-v2: route candidate and plan labels byte-identical to straight-v1; label version recorded");
            var again = new Labeler(new HindsightTeacher(WallCourse()), o2).Label(CorridorRun(WallCourse(), "synthetic-wall", BehindWall, InView));
            c.Check(again.Lines[0] == v2.Lines[0] && again.Summary == v2.Summary, "teacher path-v2: corridor labels identical across two runs");

            var box = new Labeler(new HindsightTeacher(BoxCourse()), o2).Label(CorridorRun(BoxCourse(), "synthetic-box", new V2(5, 0), new V2(-5, 0)));
            var bl = box.Labels[0]; var e0 = bl.Candidates[0];
            double ctg = e0.Cost - e0.StraightM - o2.UnreachablePenaltyM;
            c.Check(e0.EntryUnreachable && bl.Candidates[1].EntryUnreachable && bl.Flags.Contains("corridor_entry_unreachable") && box.CorridorUnreachable == 2
                && !double.IsNaN(e0.Cost) && !double.IsInfinity(e0.Cost) && Math.Abs(ctg - 11) < 1.5 && box.Summary.Contains("\"unreachable\":2"),
                "teacher path-v2: boxed-in robot gets a finite " + F1(o2.UnreachablePenaltyM) + " m penalty and a flag on both entries (" + F1(e0.Cost) + " m)");
        }

        static void Geodesy(CheckContext c)
        {
            var o = new GeoOrigin { Latitude = 42, Longitude = -83, Altitude = 0 }; double worst = 0;
            foreach (var p in new[] { new V2(-30, 5), new V2(24.8, .29), new V2(150, -80), new V2(0, 0) })
            {
                Geo.ToGeodetic(o, p.X, p.Y, 0, out double lat, out double lon, out double alt);
                worst = Math.Max(worst, V2.Distance(p, Geo.ToOdom(o, lat, lon, alt)));
            }
            // Goal 0 of the seed-2027 autonomy.json and its odom destination as recorded in snapshot input.
            V2 g = Geo.ToOdom(o, 42.00000258906408, -82.99970066766718, 4.8148445785045624e-05);
            double err = V2.Distance(g, new V2(24.799910735247174, 0.28761919485052123));
            c.Check(worst < 1e-6 && err < 1e-3, "teacher: lat/lon to odom round-trips (" + worst.ToString("0e0") + " m) and matches a recorded destination (" + err.ToString("0.0e0") + " m)");
        }

        static void Real(CheckContext c)
        {
            if (RunLoader == null || RealRunDir == null || !Directory.Exists(RealRunDir)) { c.Note("teacher: real run not available, skipped"); return; }
            var run = RunLoader(RealRunDir);
            var res = new Labeler(new HindsightTeacher(run.Course)).Label(run);
            c.Check(res.AllReachable && res.Destinations.Count == 6, "teacher: all " + res.Destinations.Count + " destinations of " + run.Name + " reachable");
            c.Check(res.Labels.Count == run.Snapshots.Count && res.Lines.Count > 0, "teacher: labels for every snapshot (" + res.Labels.Count + ")");
            c.Check(res.MaxMismatch < .05, "teacher: autonomy lat/lon goals match snapshot destinations (max " + res.MaxMismatch.ToString("0.000") + " m)");
            Trap best = null; double bd = double.PositiveInfinity;
            foreach (var t in res.Traps) { double d = V2.Distance(t.EndPos, new V2(-7.3, 21.2)); if (d < bd) { bd = d; best = t; } }
            if (best == null || bd > 2) c.Note("teacher: no stall found near (-7.3, 21.2) in " + run.Name);
            else c.Note("teacher trap near (-7.3, 21.2) in " + run.Name + ": " + Labeler.Describe(best));
        }
    }
}
