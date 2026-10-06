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
        /// <summary>The robot is boxed in by four overlapping barricades: every entry outside is disconnected from it.</summary>
        public static CourseGeometry BoxCourse() => SyntheticCourses.Stadium(40, 8, 3, .25,
            new CourseObstacle { Id = "e", Kind = "barricade", X = 2.5, Y = 0, Yaw = Math.PI / 2, Length = 5.4, Width = .4 },
            new CourseObstacle { Id = "w", Kind = "barricade", X = -2.5, Y = 0, Yaw = Math.PI / 2, Length = 5.4, Width = .4 },
            new CourseObstacle { Id = "n", Kind = "barricade", X = 0, Y = 2.5, Yaw = 0, Length = 5.4, Width = .4 },
            new CourseObstacle { Id = "s", Kind = "barricade", X = 0, Y = -2.5, Yaw = 0, Length = 5.4, Width = .4 });
        public static readonly V2 BehindWall = new V2(4, -1.5), InView = new V2(3.5, 2), InWall = new V2(3, -1.5);

        public static RunIn CorridorRun(CourseGeometry course, string name, params V2[] entries) => CorridorRun(course, name, new V2(0, 0), entries);
        public static RunIn CorridorRun(CourseGeometry course, string name, V2 robot, params V2[] entries)
        {
            var run = new RunIn { Name = name, Course = course, Status = "stopped", Reason = "synthetic" };
            run.Goals.Add(new V2(16, 0));
            var s = new SnapshotIn { Index = 1, DestinationIndex = 0, Robot = robot, Yaw = 0, Destination = new V2(16, 0), StampS = 10, Action = "sent_goal" };
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
            var inv = System.Globalization.CultureInfo.InvariantCulture; string F1(double v) => v.ToString("0.00", inv);
            LabelOptions V1() => new LabelOptions { SpeedCeilings = new[] { .6 } };
            LabelOptions V3(double cap = 60) => new LabelOptions { SpeedCeilings = new[] { .6 }, CorridorCost = LabelOptions.PathV3, CorridorSearchCapM = cap };
            c.Check(new LabelOptions().CorridorCost == LabelOptions.StraightV1, "teacher corridor: default label mode is the legacy straight-v1");
            var teacher = new HindsightTeacher(WallCourse());
            var v1 = new Labeler(teacher, V1()).Label(CorridorRun(WallCourse(), "synthetic-wall", BehindWall, InView));
            var v3 = new Labeler(teacher, V3()).Label(CorridorRun(WallCourse(), "synthetic-wall", BehindWall, InView));
            CandLabel a1 = v1.Labels[0].Candidates[0], b1 = v1.Labels[0].Candidates[1], a3 = v3.Labels[0].Candidates[0], b3 = v3.Labels[0].Candidates[1];

            // Genuine detour vs free line.
            c.Check(a3.TargetStatus == Labeler.GridPath && a3.EntryPathM > a3.StraightM + 1 && a3.TargetCostM > a3.Cost + 1,
                "teacher path-v3: wall across the straight line gives a grid detour (" + F1(a3.StraightM) + " m straight, " + F1(a3.EntryPathM) + " m path)");
            c.Check(b3.TargetStatus == Labeler.LineOfSight && b3.TargetCostM == b3.Cost && b3.EntryPathM == b3.StraightM,
                "teacher path-v3: an entry in plain view keeps the straight-line cost (" + F1(b3.TargetCostM) + " m)");
            c.Check(a1.Cost < b1.Cost - .2 && b3.TargetCostM < a3.TargetCostM - .2,
                "teacher path-v3: corridor target prefers the reachable entry (" + F1(b3.TargetCostM) + " vs " + F1(a3.TargetCostM) + " m); legacy preferred the walled one (" + F1(a1.Cost) + " vs " + F1(b1.Cost) + " m)");

            // Mixed route/corridor group: every legacy number (costs, regrets, best, plan regret) is unchanged.
            SnapshotLabel l1 = v1.Labels[0], l3 = v3.Labels[0];
            bool same = l1.Candidates.Count == l3.Candidates.Count && l1.BestCandidate == l3.BestCandidate && l1.RegretM.Equals(l3.RegretM)
                && Labeler.CandidateJson(l1.Plan) == Labeler.CandidateJson(l3.Plan, true);
            for (int k = 0; same && k < l1.Candidates.Count; k++)
                same = Labeler.CandidateJson(l1.Candidates[k]) == Labeler.CandidateJson(l3.Candidates[k], true) && l1.Candidates[k].Regret.Equals(l3.Candidates[k].Regret);
            c.Check(same && l1.Candidates[2].Source == "grid" && !v1.Lines[0].Contains("corridor_target") && v3.Lines[0].Contains("\"corridor_target\":")
                && v3.Lines[0].Contains("\"corridor_label\":\"path-v3\"") && v1.Summary.Contains("\"corridor_label\":\"straight-v1\""),
                "teacher path-v3: mixed group legacy costs/regrets/best/plan regret identical to straight-v1; target fields additive, mode recorded");

            // Blocked endpoints never gain a connection (the old code skipped 1 m or snapped through the wall).
            var bad = new Labeler(teacher, V3()).Label(CorridorRun(WallCourse(), "synthetic-in-wall", InWall, new V2(4.2, -1.5), BehindWall)).Labels[0];
            var badEntry = new Labeler(teacher, V3()).Label(CorridorRun(WallCourse(), "synthetic-entry-in-wall", InWall, InView)).Labels[0];
            c.Check(teacher.CodeAt(InWall) != OccupancyGrid.Free && bad.Candidates[0].TargetStatus == Labeler.BlockedRobot
                && bad.Candidates[1].TargetStatus == Labeler.BlockedRobot && double.IsNaN(bad.Candidates[0].TargetCostM)
                && !teacher.SegmentFree(InWall, new V2(4.2, -1.5)) && bad.Flags.Contains("corridor_target_unavailable"),
                "teacher path-v3: a robot inside the wall gets blocked_robot, no cost, no line of sight");
            c.Check(badEntry.Candidates[0].TargetStatus == Labeler.BlockedEntry && double.IsNaN(badEntry.Candidates[0].TargetCostM)
                && badEntry.Candidates[1].TargetStatus == Labeler.LineOfSight,
                "teacher path-v3: an entry inside the wall gets blocked_entry and no cost; the free entry is unaffected");

            // A search cutoff is unknown, not disconnected; a sealed box is proven disconnected; no penalty is invented.
            var capped = new Labeler(teacher, V3(2)).Label(CorridorRun(WallCourse(), "synthetic-capped", BehindWall, InView));
            var ca = capped.Labels[0].Candidates[0];
            c.Check(ca.TargetStatus == Labeler.SearchLimited && double.IsNaN(ca.TargetCostM) && capped.Labels[0].Candidates[1].TargetStatus == Labeler.LineOfSight
                && capped.Summary.Contains("\"search_limited\":1") && capped.Summary.Contains("\"disconnected\":0"),
                "teacher path-v3: a 2 m search cap leaves the detoured entry search_limited (not disconnected, no cost)");
            var box = new Labeler(new HindsightTeacher(BoxCourse()), V3()).Label(CorridorRun(BoxCourse(), "synthetic-box", new V2(5, 0), new V2(-5, 0)));
            var bl = box.Labels[0];
            c.Check(bl.Candidates[0].TargetStatus == Labeler.Disconnected && bl.Candidates[1].TargetStatus == Labeler.Disconnected
                && double.IsNaN(bl.Candidates[0].TargetCostM) && !double.IsNaN(bl.Candidates[0].Cost) && bl.Flags.Contains("corridor_target_unavailable")
                && box.Summary.Contains("\"disconnected\":2") && box.Lines[0].Contains("\"status\":\"disconnected\"") && box.Lines[0].Contains("\"cost_m\":null"),
                "teacher path-v3: boxed-in robot: both entries proven disconnected, null target cost, legacy cost kept (" + F1(bl.Candidates[0].Cost) + " m)");

            // Supercover: a free segment never touches a non-free point (dense sampling) and is at least as strict as half-cell sampling.
            var rng = new Random(45); int crossed = 0, stricter = 0, free = 0; double cs = teacher.Cell;
            for (int i = 0; i < 3000; i++)
            {
                V2 p = new V2(-6 + 14 * rng.NextDouble(), -4 + 8 * rng.NextDouble()), q = new V2(-6 + 14 * rng.NextDouble(), -4 + 8 * rng.NextDouble());
                bool seg = teacher.SegmentFree(p, q); double len = V2.Distance(p, q);
                int dense = Math.Max(1, (int)Math.Ceiling(len / (cs / 25))), half = Math.Max(1, (int)Math.Ceiling(len / (cs / 2)));
                bool denseFree = true, halfFree = true;
                for (int k = 0; k <= dense && denseFree; k++) denseFree = teacher.CodeAt(V2.Lerp(p, q, (double)k / dense)) == OccupancyGrid.Free;
                for (int k = 0; k <= half && halfFree; k++) halfFree = teacher.CodeAt(V2.Lerp(p, q, (double)k / half)) == OccupancyGrid.Free;
                if (seg) { free++; if (!denseFree) crossed++; }
                if (halfFree && !seg) stricter++;
            }
            c.Check(crossed == 0 && free > 100, "teacher path-v3: " + free + " free segments never cross a blocked point; " + stricter + " half-cell-free segments rejected");

            var again = new Labeler(new HindsightTeacher(WallCourse()), V3()).Label(CorridorRun(WallCourse(), "synthetic-wall", BehindWall, InView));
            c.Check(again.Lines[0] == v3.Lines[0] && again.Summary == v3.Summary, "teacher path-v3: corridor labels identical across two runs");
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
