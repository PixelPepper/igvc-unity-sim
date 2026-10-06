using System;
using System.Collections.Generic;

namespace IGVC.Reference.Teacher
{
    public sealed class CandLabel
    {
        public string Source = ""; public V2 End; public double PathLength, Cost, Regret = double.NaN, Score = double.NaN;
        public bool StraightLine; public string EndCell = "free";
        /// <summary>path-v3 corridor target, separate from the legacy Cost/Regret: Corridor marks a candidate that has one;
        /// TargetCostM is NaN unless TargetStatus is line_of_sight or grid_path.</summary>
        public bool Corridor; public string TargetStatus = "";
        public double StraightM = double.NaN, EntryPathM = double.NaN, TargetCostM = double.NaN;
        public bool TargetAvailable => TargetStatus == Labeler.LineOfSight || TargetStatus == Labeler.GridPath;
    }
    public sealed class ExecLabel { public double HorizonS, PathLength, Progress, Cost, Regret; public V2 After; }

    public sealed class SnapshotLabel
    {
        public int Index, Dest; public double Stamp, Yaw; public V2 Robot, Destination;
        public readonly List<string> Flags = new List<string>();
        public string RobotCell = "free";
        public double CostToGo = double.NaN, LocalGoalYaw = double.NaN, Bearing = double.NaN, HeadingError = double.NaN, LocalGoalCost = double.NaN, Lookahead;
        public V2 LocalGoal; public List<V2> Preview = new List<V2>();
        public double[] Speeds;
        public CandLabel Plan; public List<CandLabel> Candidates; public int BestCandidate = -1;
        public double RegretM = double.NaN, RegretVsTeacherM = double.NaN;
        public ExecLabel Executed;
        public double OutcomeProgressTeacher = double.NaN, OutcomeProgressLogged = double.NaN; public string Action = ""; public int Admitted = -1;
        /// <summary>Ranking regret: vs best candidate when candidates exist (v2), else the plan vs the teacher local goal.</summary>
        public double Primary => !double.IsNaN(RegretM) ? RegretM : RegretVsTeacherM;
    }

    public sealed class SideInfo
    {
        public string Id, Kind, TeacherApproach, TeacherStall, Robot; public double FromRobotEnd, RobotMinClear;
    }

    public sealed class Trap
    {
        public double Start, End, Progress, EndYaw, TeacherHeading = double.NaN, CostAtEnd = double.NaN; public int Dest; public bool EndsRun;
        public V2 StartPos, EndPos, ApproachPos; public List<V2> TeacherRoute = new List<V2>(), ApproachRoute = new List<V2>();
        public readonly List<SideInfo> Sides = new List<SideInfo>();
        public string Verdict = "";
        public double Duration => End - Start;
    }

    public sealed class DestInfo { public int Index, GoalCell = -1, Reached, Uses; public V2 Point; public double Snap = double.NaN, Mismatch; public bool Reachable; }

    public sealed class RunLabels
    {
        public RunIn Run; public readonly List<SnapshotLabel> Labels = new List<SnapshotLabel>();
        public readonly List<DestInfo> Destinations = new List<DestInfo>(); public readonly List<Trap> Traps = new List<Trap>();
        public SpeedProfile[] Speeds;
        public bool AllReachable { get { foreach (var d in Destinations) if (!d.Reachable) return false; return Destinations.Count > 0; } }
        public double MaxMismatch { get { double m = 0; foreach (var d in Destinations) m = Math.Max(m, d.Mismatch); return m; } }
        public List<string> Lines = new List<string>(); public string Summary = "", TrapsJson = "";
        /// <summary>path-v3 corridor target counts by status (ordinal order of <see cref="Labeler.TargetStatuses"/>), searches, expanded cells.</summary>
        public int CorridorCandidates, CorridorSearches, CorridorExpanded; public int[] CorridorStatus = new int[Labeler.TargetStatuses.Length];
        public int Count(string status) => CorridorStatus[Array.IndexOf(Labeler.TargetStatuses, status)];
    }

    /// <summary>Labels every saved decision of a finished run with the full-knowledge teacher (offline only).</summary>
    public sealed class Labeler
    {
        public readonly HindsightTeacher T; public readonly LabelOptions O;
        public Labeler(HindsightTeacher teacher, LabelOptions options = null) { T = teacher; O = options ?? new LabelOptions(); }

        public RunLabels Label(RunIn run)
        {
            var res = new RunLabels { Run = run };
            res.Speeds = new SpeedProfile[O.SpeedCeilings.Length];
            for (int k = 0; k < res.Speeds.Length; k++) res.Speeds[k] = T.Speed(O.SpeedCeilings[k]);
            var snaps = new List<SnapshotIn>(run.Snapshots); snaps.Sort((a, b) => a.Index.CompareTo(b.Index));
            // Destinations: autonomy goals (converted lat/lon) when present, else the first snapshot's odom destination.
            var dests = new SortedDictionary<int, DestInfo>();
            for (int i = 0; i < run.Goals.Count; i++) dests[i] = new DestInfo { Index = i, Point = run.Goals[i] };
            foreach (var s in snaps)
            {
                if (!dests.TryGetValue(s.DestinationIndex, out var d)) dests[s.DestinationIndex] = d = new DestInfo { Index = s.DestinationIndex, Point = s.Destination };
                d.Mismatch = Math.Max(d.Mismatch, V2.Distance(d.Point, s.Destination)); d.Uses++;
            }
            foreach (var d in dests.Values)
            {
                d.GoalCell = T.GoalCell(d.Point, out d.Snap); var f = T.Field(d.GoalCell);
                d.Reached = HindsightTeacher.Reached(f); d.Reachable = d.GoalCell >= 0 && d.Reached >= T.FreeCells / 2;
                res.Destinations.Add(d);
            }
            if (O.CorridorCost != LabelOptions.PathV3 && O.CorridorCost != LabelOptions.StraightV1) throw new ArgumentException("unknown corridor label mode " + O.CorridorCost);
            foreach (var s in snaps) res.Labels.Add(LabelOne(run, s, snaps, dests, res.Speeds, res));
            FindTraps(run, snaps, res);
            foreach (var l in res.Labels) res.Lines.Add(LabelJson(l));
            res.Summary = SummaryJson(res); res.TrapsJson = TrapsJson(res);
            return res;
        }

        private SnapshotLabel LabelOne(RunIn run, SnapshotIn s, List<SnapshotIn> snaps, SortedDictionary<int, DestInfo> dests, SpeedProfile[] speeds, RunLabels res)
        {
            var L = new SnapshotLabel { Index = s.Index, Dest = s.DestinationIndex, Stamp = s.StampS, Robot = s.Robot, Yaw = s.Yaw, Destination = s.Destination, Lookahead = s.Lookahead, Action = s.Action, Admitted = s.Admitted };
            var f = T.FieldFor(s.Destination);
            if (dests.TryGetValue(s.DestinationIndex, out var di) && V2.Distance(di.Point, s.Destination) > .25) L.Flags.Add("destination_mismatch");
            if (f == null) L.Flags.Add("destination_unreachable");
            L.RobotCell = CellName(T.CodeAt(s.Robot));
            if (L.RobotCell == "obstacle") L.Flags.Add("robot_in_cspace_obstacle");
            else if (L.RobotCell == "outside") L.Flags.Add("robot_outside_lane_cspace");
            L.CostToGo = T.CostToGo(f, s.Robot);
            if (f != null && double.IsNaN(L.CostToGo)) L.Flags.Add("destination_unreachable_from_robot");
            var route = T.Route(f, s.Robot, Math.Max(s.Lookahead, O.PreviewM) + 1);
            if (route.Count > 1)
            {
                double arc = Math.Min(s.Lookahead, HindsightTeacher.Length(route));
                L.LocalGoal = HindsightTeacher.Along(route, arc); L.LocalGoalYaw = HindsightTeacher.YawAlong(route, arc);
                V2 to = L.LocalGoal - s.Robot; L.Bearing = to.SqrLength > 1e-12 ? to.Angle : L.LocalGoalYaw;
                L.HeadingError = HindsightTeacher.WrapAngle(L.Bearing - s.Yaw);
                L.LocalGoalCost = arc + T.CostToGo(f, L.LocalGoal);
                L.Preview = HindsightTeacher.Resample(route, 1, s.Lookahead);
            }
            else { L.LocalGoal = s.Robot; L.LocalGoalCost = L.CostToGo; }
            L.Speeds = new double[speeds.Length];
            for (int k = 0; k < speeds.Length; k++) L.Speeds[k] = speeds[k].At(s.Robot, out _);
            if (s.Plan != null) { L.Plan = Cand(s, s.Plan, f); L.Plan.Regret = L.RegretVsTeacherM = L.Plan.Cost - L.LocalGoalCost; if (L.Plan.EndCell != "free") L.Flags.Add("plan_endpoint_in_cspace"); }
            if (s.Candidates != null && s.Candidates.Count > 0)
            {
                L.Candidates = new List<CandLabel>(); double best = double.PositiveInfinity;
                foreach (var c in s.Candidates) L.Candidates.Add(Cand(s, c, f));
                for (int k = 0; k < L.Candidates.Count; k++) if (L.Candidates[k].Cost < best) { best = L.Candidates[k].Cost; L.BestCandidate = k; }
                foreach (var cl in L.Candidates) cl.Regret = cl.Cost - best;
                if (L.Plan != null && L.BestCandidate >= 0) L.RegretM = L.Plan.Cost - best;
                // Additive only: legacy costs, regrets and the best candidate above are final before this runs.
                if (O.CorridorCost == LabelOptions.PathV3) CorridorTargets(s, L, f, res);
            }
            L.Executed = Executed(run, s, snaps, f, L.CostToGo);
            if (s.HasAfter) { L.OutcomeProgressTeacher = L.CostToGo - T.CostToGo(f, s.After); L.OutcomeProgressLogged = s.ProgressM; }
            return L;
        }

        private CandLabel Cand(SnapshotIn s, CandidateIn c, double[] f)
        {
            var cl = new CandLabel { Source = c.Source ?? "", End = c.End, Score = c.Score, EndCell = CellName(T.CodeAt(c.End)) };
            if (!double.IsNaN(c.PathLength)) cl.PathLength = c.PathLength;
            else if (c.Path != null && c.Path.Count > 1) cl.PathLength = HindsightTeacher.Length(c.Path) + V2.Distance(c.Path[c.Path.Count - 1], c.End);
            else { cl.PathLength = V2.Distance(s.Robot, c.End); cl.StraightLine = true; }
            cl.Cost = cl.PathLength + T.CostToGo(f, c.End);
            return cl;
        }

        public const string CorridorSource = "corridor";
        public const string LineOfSight = "line_of_sight", GridPath = "grid_path", Disconnected = "disconnected", SearchLimited = "search_limited",
            BlockedRobot = "blocked_robot", BlockedEntry = "blocked_entry", EntryNoCostToGo = "entry_no_cost_to_go";
        /// <summary>Every corridor_target status; only the first two carry a cost.</summary>
        public static readonly string[] TargetStatuses = { LineOfSight, GridPath, Disconnected, SearchLimited, BlockedRobot, BlockedEntry, EntryNoCostToGo };
        /// <summary>
        /// path-v3: a separate corridor target for each lane-corridor candidate (source corridor, no logged path), leaving
        /// its legacy Cost/Regret untouched. Robot and entry must lie in free C-space cells (never snapped); the leg is
        /// the straight line when every intersected cell is free, else the grid shortest path (one Dijkstra per snapshot,
        /// fixed <see cref="LabelOptions.CorridorSearchCapM"/>). The entry's cost-to-go must come from its own cell.
        /// Unavailable targets keep a status and NaN cost (written as null): no penalty is ever invented.
        /// Approximation: a line-of-sight leg is Euclidean, a detour leg octile (up to ~8% longer than any-angle), so a
        /// detour target is an upper bound on the true C-space distance. Corridor candidates with a logged path are
        /// not given a target (no corridor_target is written); a path-v3 dataset build aborts on them (fail closed).
        /// </summary>
        private void CorridorTargets(SnapshotIn s, SnapshotLabel L, double[] f, RunLabels res)
        {
            var idx = new List<int>(); var targets = new List<V2>(); var ctg = new double[L.Candidates.Count];
            bool robotFree = T.CodeAt(s.Robot) == OccupancyGrid.Free, unavailable = false;
            for (int k = 0; k < L.Candidates.Count; k++)
            {
                var cl = L.Candidates[k]; if (cl.Source != CorridorSource || !cl.StraightLine) continue;
                cl.Corridor = true; cl.StraightM = cl.PathLength; res.CorridorCandidates++;
                ctg[k] = T.CostToGo(f, cl.End, out _, out bool snapped);
                if (!robotFree) cl.TargetStatus = BlockedRobot;
                else if (T.CodeAt(cl.End) != OccupancyGrid.Free) cl.TargetStatus = BlockedEntry;
                else if (snapped || double.IsNaN(ctg[k]) || double.IsInfinity(ctg[k])) cl.TargetStatus = EntryNoCostToGo;
                else if (T.SegmentFree(s.Robot, cl.End)) { cl.TargetStatus = LineOfSight; cl.EntryPathM = cl.StraightM; }
                else { idx.Add(k); targets.Add(cl.End); }
            }
            if (idx.Count > 0)
            {
                var path = T.PathFrom(s.Robot, targets, O.CorridorSearchCapM, out var reach, out int expanded);
                res.CorridorSearches++; res.CorridorExpanded += expanded;
                for (int j = 0; j < idx.Count; j++)
                {
                    var cl = L.Candidates[idx[j]];
                    switch (reach[j])
                    {
                        case HindsightTeacher.Reach.Reached: cl.TargetStatus = GridPath; cl.EntryPathM = path[j]; break;
                        case HindsightTeacher.Reach.Disconnected: cl.TargetStatus = Disconnected; break;
                        case HindsightTeacher.Reach.SearchLimited: cl.TargetStatus = SearchLimited; break;
                        case HindsightTeacher.Reach.BlockedStart: cl.TargetStatus = BlockedRobot; break;
                        default: cl.TargetStatus = BlockedEntry; break;
                    }
                }
            }
            for (int k = 0; k < L.Candidates.Count; k++)
            {
                var cl = L.Candidates[k]; if (!cl.Corridor) continue;
                res.CorridorStatus[Array.IndexOf(TargetStatuses, cl.TargetStatus)]++;
                if (cl.TargetAvailable) cl.TargetCostM = cl.EntryPathM + ctg[k]; else unavailable = true;
            }
            if (unavailable) L.Flags.Add("corridor_target_unavailable");
        }

        private ExecLabel Executed(RunIn run, SnapshotIn s, List<SnapshotIn> snaps, double[] f, double costHere)
        {
            int n = run.TrajT.Length; if (n < 2 || double.IsNaN(s.StampS) || f == null) return null;
            double t0 = s.StampS, t1 = Math.Min(t0 + O.HorizonS, run.TrajT[n - 1]);
            foreach (var o in snaps) if (o.StampS > t0 && o.DestinationIndex != s.DestinationIndex && !double.IsNaN(o.StampS)) { t1 = Math.Min(t1, o.StampS); break; }
            int i0 = Lower(run.TrajT, t0); if (i0 >= n || t1 <= t0) return null;
            double len = 0; int i = i0;
            for (; i + 1 < n && run.TrajT[i + 1] <= t1; i++) len += V2.Distance(run.TrajP[i], run.TrajP[i + 1]);
            var after = run.TrajP[i]; double cost = T.CostToGo(f, after);
            return new ExecLabel { HorizonS = run.TrajT[i] - run.TrajT[i0], PathLength = len, After = after, Cost = len + cost, Progress = costHere - cost, Regret = len + cost - costHere };
        }

        // ---- traps: executed progress (teacher cost-to-go decrease) stalls ----
        private void FindTraps(RunIn run, List<SnapshotIn> snaps, RunLabels res)
        {
            int n = run.TrajT.Length; if (n < 2) return;
            var timed = snaps.FindAll(s => !double.IsNaN(s.StampS)); timed.Sort((a, b) => a.StampS.CompareTo(b.StampS));
            if (timed.Count == 0) return;
            var dest = new int[n]; var fv = new double[n]; var fieldOf = new Dictionary<int, double[]>(); int k = 0;
            for (int i = 0; i < n; i++)
            {
                while (k + 1 < timed.Count && timed[k + 1].StampS <= run.TrajT[i]) k++;
                dest[i] = timed[k].DestinationIndex;
                if (!fieldOf.TryGetValue(dest[i], out var f)) fieldOf[dest[i]] = f = T.FieldFor(timed[k].Destination);
                fv[i] = T.CostToGo(f, run.TrajP[i]);
            }
            double W = O.StallWindowS, last = run.TrajT[n - 1], nextSample = double.NegativeInfinity;
            var windows = new List<double[]>(); // start, end, startIndex
            for (int i = 0; i < n; i++)
            {
                double t = run.TrajT[i]; if (t < nextSample) continue; nextSample = t + .5;
                double end = Math.Min(t + W, last); bool tail = t + W > last;
                if (end - t < (tail ? Math.Min(W, 10) : W - 1e-6)) continue;
                double min = fv[i]; bool switched = false;
                for (int j = i; j < n && run.TrajT[j] <= end; j++) { if (dest[j] != dest[i]) { switched = true; break; } if (fv[j] < min) min = fv[j]; }
                if (switched || double.IsNaN(fv[i])) continue;
                if (fv[i] - min < O.StallProgressM) windows.Add(new[] { t, end, i });
            }
            Trap cur = null;
            foreach (var w in windows)
            {
                if (cur != null && w[0] <= cur.End + 1e-9 && dest[(int)w[2]] == cur.Dest) { cur.End = Math.Max(cur.End, w[1]); continue; }
                cur = new Trap { Start = w[0], End = w[1], Dest = dest[(int)w[2]] }; res.Traps.Add(cur);
            }
            foreach (var tr in res.Traps) Describe(run, tr, fieldOf[tr.Dest], dest, fv);
        }

        private void Describe(RunIn run, Trap tr, double[] f, int[] dest, double[] fv)
        {
            int n = run.TrajT.Length, a = Lower(run.TrajT, tr.Start), b = Math.Min(n - 1, Lower(run.TrajT, tr.End + 1e-9));
            if (b > 0 && run.TrajT[b] > tr.End + 1e-9) b--;
            tr.StartPos = run.TrajP[a]; tr.EndPos = run.TrajP[b]; tr.EndYaw = run.TrajYaw[b]; tr.EndsRun = b == n - 1;
            double minF = double.PositiveInfinity; for (int i = a; i <= b; i++) if (fv[i] < minF) minF = fv[i];
            tr.Progress = fv[a] - minF; tr.CostAtEnd = fv[b];
            int ap = Lower(run.TrajT, tr.Start - O.StallWindowS); if (ap >= n) ap = a; tr.ApproachPos = run.TrajP[ap];
            var route = T.Route(f, tr.EndPos, O.PreviewM + 1); tr.TeacherRoute = HindsightTeacher.Resample(route, .5, O.PreviewM);
            if (route.Count > 1) { V2 g = HindsightTeacher.Along(route, 3) - tr.EndPos; tr.TeacherHeading = g.SqrLength > 1e-12 ? g.Angle : double.NaN; }
            var approach = T.Route(f, tr.ApproachPos, 2 * O.PreviewM + 1); tr.ApproachRoute = HindsightTeacher.Resample(approach, .5, 2 * O.PreviewM);
            var robotPath = new List<V2>(); for (int i = ap; i <= b; i++) robotPath.Add(run.TrajP[i]);
            var obs = T.Course.Obstacles; var order = new List<int>();
            for (int i = 0; i < obs.Length; i++)
            {
                var c = obs[i].Shape; double dEnd = c.Distance(tr.EndPos);
                if (dEnd < 4 || Near(tr.TeacherRoute, c) < 1.5 || Near(tr.ApproachRoute, c) < 1.5 && Near(robotPath, c) < 2.5) order.Add(i);
            }
            order.Sort((i, j) => { int r = obs[i].Shape.Distance(tr.EndPos).CompareTo(obs[j].Shape.Distance(tr.EndPos)); return r != 0 ? r : string.CompareOrdinal(obs[i].Id, obs[j].Id); });
            var differ = new List<string>();
            foreach (int i in order)
            {
                var c = obs[i].Shape;
                var si = new SideInfo { Id = obs[i].Id, Kind = obs[i].Kind, FromRobotEnd = c.Distance(tr.EndPos), TeacherApproach = Side(approach, c, 2.5), TeacherStall = Side(route, c, 2.5), Robot = Side(robotPath, c, 2.5), RobotMinClear = Near(robotPath, c) };
                tr.Sides.Add(si);
                if (si.TeacherApproach != "far" && si.Robot != "far" && si.TeacherApproach != si.Robot) differ.Add(si.Id + " (teacher " + si.TeacherApproach + ", robot " + si.Robot + ")");
            }
            tr.Verdict = differ.Count == 0 ? "robot was on the teacher's side of every nearby obstacle" : "robot on the other side of " + string.Join(", ", differ);
        }

        private static double Near(IList<V2> pts, Capsule c) { double m = double.PositiveInfinity; foreach (var p in pts) m = Math.Min(m, c.Distance(p)); return m; }
        /// <summary>Compass side of the obstacle on which a path passes (closest approach), or "far".</summary>
        public static string Side(IList<V2> pts, Capsule c, double within)
        {
            double best = double.PositiveInfinity; V2 bp = default;
            foreach (var p in pts) { double d = c.Distance(p); if (d < best) { best = d; bp = p; } }
            if (best > within) return "far";
            V2 ab = c.B - c.A; double l2 = ab.SqrLength, t = l2 > 1e-18 ? Math.Max(0, Math.Min(1, V2.Dot(bp - c.A, ab) / l2)) : 0;
            V2 v = bp - (c.A + ab * t);
            return Math.Abs(v.X) >= Math.Abs(v.Y) ? (v.X >= 0 ? "east" : "west") : (v.Y >= 0 ? "north" : "south");
        }
        private static int Lower(double[] a, double t) { int lo = 0, hi = a.Length; while (lo < hi) { int m = (lo + hi) / 2; if (a[m] < t) lo = m + 1; else hi = m; } return lo; }
        private static string CellName(byte code) => code == OccupancyGrid.Free ? "free" : code == OccupancyGrid.Obstacle ? "obstacle" : "outside";

        // ---- JSON ----
        private string LabelJson(SnapshotLabel l)
        {
            var j = new JsonOut().O();
            j.K("schema_version").I(1).K("corridor_label").S(O.CorridorCost).K("index").I(l.Index).K("destination_index").I(l.Dest).K("stamp_s").N(l.Stamp, 3);
            j.K("robot").A().N(l.Robot.X).N(l.Robot.Y).N(l.Yaw).EA().K("destination").P(l.Destination).K("robot_cell").S(l.RobotCell);
            j.K("flags").A(); foreach (var f in l.Flags) j.S(f); j.EA();
            j.K("teacher").O().K("cost_to_go_m").N(l.CostToGo).K("lookahead_m").N(l.Lookahead).K("local_goal").P(l.LocalGoal).K("local_goal_yaw").N(l.LocalGoalYaw)
                .K("bearing_rad").N(l.Bearing).K("heading_error_rad").N(l.HeadingError).K("local_goal_cost_m").N(l.LocalGoalCost).K("route").Pts(l.Preview).EO();
            j.K("teacher_speed_mps").O(); for (int k = 0; k < l.Speeds.Length; k++) j.K(O.SpeedCeilings[k].ToString("0.0#", System.Globalization.CultureInfo.InvariantCulture)).N(l.Speeds[k], 3); j.EO();
            j.K("plan"); CandJson(j, l.Plan);
            j.K("candidates"); if (l.Candidates == null) j.Null(); else { j.A(); foreach (var c in l.Candidates) CandJson(j, c); j.EA(); }
            j.K("best_candidate").I(l.BestCandidate).K("regret_m").N(l.RegretM).K("regret_vs_teacher_m").N(l.RegretVsTeacherM);
            j.K("executed"); if (l.Executed == null) j.Null(); else { var e = l.Executed; j.O().K("source").S("trajectory").K("horizon_s").N(e.HorizonS, 2).K("after").P(e.After).K("path_length_m").N(e.PathLength).K("progress_m").N(e.Progress).K("teacher_cost_m").N(e.Cost).K("regret_vs_teacher_m").N(e.Regret).EO(); }
            j.K("action").S(l.Action).K("admitted"); if (l.Admitted < 0) j.Null(); else j.B(l.Admitted == 1);
            j.K("outcome_progress_teacher_m").N(l.OutcomeProgressTeacher).K("outcome_progress_logged_m").N(l.OutcomeProgressLogged);
            return j.EO().ToString();
        }
        /// <summary>One candidate as written in labels.jsonl; <paramref name="legacyOnly"/> omits the additive corridor_target.</summary>
        public static string CandidateJson(CandLabel c, bool legacyOnly = false) { var j = new JsonOut(); CandJson(j, c, legacyOnly); return j.ToString(); }
        private static void CandJson(JsonOut j, CandLabel c, bool legacyOnly = false)
        {
            if (c == null) { j.Null(); return; }
            j.O().K("source").S(c.Source).K("endpoint").P(c.End).K("endpoint_cell").S(c.EndCell).K("path_length_m").N(c.PathLength).K("straight_line").B(c.StraightLine)
                .K("score").N(c.Score).K("teacher_cost_m").N(c.Cost).K("regret_m").N(c.Regret);
            if (c.Corridor && !legacyOnly)
                j.K("corridor_target").O().K("status").S(c.TargetStatus).K("entry_straight_m").N(c.StraightM).K("entry_path_m").N(c.EntryPathM).K("cost_m").N(c.TargetCostM).EO();
            j.EO();
        }
        private static void Stat(JsonOut j, string key, IEnumerable<double> values)
        {
            int n = 0; double sum = 0, max = double.NegativeInfinity, min = double.PositiveInfinity;
            foreach (var v in values) { if (double.IsNaN(v) || double.IsInfinity(v)) continue; n++; sum += v; max = Math.Max(max, v); min = Math.Min(min, v); }
            j.K(key).O().K("n").I(n).K("mean").N(n > 0 ? sum / n : double.NaN).K("min").N(n > 0 ? min : double.NaN).K("max").N(n > 0 ? max : double.NaN).EO();
        }
        private string SummaryJson(RunLabels r)
        {
            var j = new JsonOut().O();
            j.K("schema_version").I(1).K("kind").S("hindsight_teacher_labels")
             .K("warning").S("Derived from WORLD course geometry: offline training/evaluation labels only; never an input to the running robot.")
             .K("run").S(r.Run.Name).K("course").S(r.Run.Course.Identity).K("run_status").S(r.Run.Status).K("run_reason").S(r.Run.Reason)
             .K("outcome_schema").I(r.Run.OutcomeSchema).K("executed_source").S("trajectory").K("horizon_s").N(O.HorizonS)
             .K("corridor_label").S(O.CorridorCost);
            if (O.CorridorCost == LabelOptions.PathV3)
            {
                j.K("corridor_targets").O().K("candidates").I(r.CorridorCandidates).K("status").O();
                for (int k = 0; k < TargetStatuses.Length; k++) j.K(TargetStatuses[k]).I(r.CorridorStatus[k]);
                j.EO().K("search_cap_m").N(O.CorridorSearchCapM).K("searches").I(r.CorridorSearches).K("expanded_cells").I(r.CorridorExpanded).EO();
            }
            j.K("grid").O().K("cell_m").N(T.Cell).K("width").I(T.Grid.W).K("height").I(T.Grid.H).K("clearance_m").N(T.Grid.Clearance).K("free_cells").I(T.FreeCells).K("seam").B(false).EO();
            j.K("speed").A(); foreach (var s in r.Speeds) j.O().K("ceiling_mps").N(s.Ceiling).K("lap_time_s").N(s.LapTime, 2).K("blocked_stations").I(s.BlockedStations).EO(); j.EA();
            j.K("destinations").A();
            foreach (var d in r.Destinations) j.O().K("index").I(d.Index).K("odom").P(d.Point).K("goal_cell_snap_m").N(d.Snap).K("reachable").B(d.Reachable).K("reached_cells").I(d.Reached).K("snapshots").I(d.Uses).K("max_snapshot_mismatch_m").N(d.Mismatch).EO();
            j.EA().K("all_destinations_reachable").B(r.AllReachable);
            j.K("snapshots").I(r.Run.Snapshots.Count).K("labelled").I(r.Labels.Count);
            var flags = new SortedDictionary<string, int>(StringComparer.Ordinal);
            foreach (var l in r.Labels) foreach (var f in l.Flags) flags[f] = flags.TryGetValue(f, out int c) ? c + 1 : 1;
            j.K("flags").O(); foreach (var kv in flags) j.K(kv.Key).I(kv.Value); j.EO();
            j.K("regret").O();
            Stat(j, "plan_vs_teacher_m", r.Labels.ConvertAll(l => l.RegretVsTeacherM));
            Stat(j, "plan_vs_best_candidate_m", r.Labels.ConvertAll(l => l.RegretM));
            Stat(j, "executed_vs_teacher_m", r.Labels.ConvertAll(l => l.Executed?.Regret ?? double.NaN));
            Stat(j, "executed_progress_m", r.Labels.ConvertAll(l => l.Executed?.Progress ?? double.NaN));
            Stat(j, "heading_error_abs_rad", r.Labels.ConvertAll(l => Math.Abs(l.HeadingError)));
            j.EO();
            var worst = r.Labels.FindAll(l => !double.IsNaN(l.Primary));
            worst.Sort((a, b) => { int c = b.Primary.CompareTo(a.Primary); return c != 0 ? c : a.Index.CompareTo(b.Index); });
            j.K("worst").A();
            for (int i = 0; i < Math.Min(O.Worst, worst.Count); i++)
            {
                var l = worst[i];
                j.O().K("index").I(l.Index).K("destination_index").I(l.Dest).K("robot").A().N(l.Robot.X).N(l.Robot.Y).N(l.Yaw).EA().K("regret_m").N(l.Primary)
                 .K("plan_endpoint"); if (l.Plan == null) j.Null(); else j.P(l.Plan.End);
                j.K("teacher_local_goal").P(l.LocalGoal).K("heading_error_rad").N(l.HeadingError).K("flags").A(); foreach (var f in l.Flags) j.S(f); j.EA().EO();
            }
            j.EA();
            j.K("traps").A(); foreach (var t in r.Traps) j.O().K("start_s").N(t.Start, 2).K("duration_s").N(t.Duration, 1).K("destination_index").I(t.Dest).K("end").P(t.EndPos).K("ends_run").B(t.EndsRun).K("verdict").S(t.Verdict).EO(); j.EA();
            return j.EO().ToString();
        }
        private string TrapsJson(RunLabels r)
        {
            var j = new JsonOut().O().K("schema_version").I(1).K("run").S(r.Run.Name)
                .K("definition").S("teacher cost-to-go decreases by < " + O.StallProgressM + " m over a " + O.StallWindowS + " s trajectory window (same destination)")
                .K("traps").A();
            foreach (var t in r.Traps)
            {
                j.O().K("start_s").N(t.Start, 2).K("end_s").N(t.End, 2).K("duration_s").N(t.Duration, 1).K("destination_index").I(t.Dest).K("progress_m").N(t.Progress)
                 .K("start").P(t.StartPos).K("end").A().N(t.EndPos.X).N(t.EndPos.Y).N(t.EndYaw).EA().K("ends_run").B(t.EndsRun).K("run_reason").S(t.EndsRun ? r.Run.Reason : null)
                 .K("teacher_cost_to_go_at_end_m").N(t.CostAtEnd).K("teacher_heading_at_end_rad").N(t.TeacherHeading)
                 .K("teacher_route_from_end").Pts(t.TeacherRoute).K("approach_pose").P(t.ApproachPos).K("teacher_route_from_approach").Pts(t.ApproachRoute)
                 .K("obstacles").A();
                foreach (var s in t.Sides) j.O().K("id").S(s.Id).K("kind").S(s.Kind).K("distance_from_end_m").N(s.FromRobotEnd).K("teacher_side_from_approach").S(s.TeacherApproach).K("teacher_side_from_end").S(s.TeacherStall).K("robot_side").S(s.Robot).K("robot_min_clearance_m").N(s.RobotMinClear).EO();
                j.EA().K("verdict").S(t.Verdict).EO();
            }
            return j.EA().EO().ToString();
        }

        private static string F(double v, string fmt) => v.ToString(fmt, System.Globalization.CultureInfo.InvariantCulture);
        /// <summary>One-line human summary of a trap (CLI and check NOTE).</summary>
        public static string Describe(Trap t)
        {
            var parts = new List<string>();
            foreach (var s in t.Sides) parts.Add(s.Id + " teacher " + s.TeacherApproach + "/" + s.TeacherStall + " robot " + s.Robot);
            return "stall " + F(t.Start, "0.0") + "-" + F(t.End, "0.0") + " s (" + F(t.Duration, "0") + " s) dest " + t.Dest + " at " + t.EndPos + " yaw " + F(t.EndYaw, "0.00")
                + (t.EndsRun ? " [ends run]" : "") + "; teacher heading " + F(t.TeacherHeading, "0.00") + " to " + (t.TeacherRoute.Count > 0 ? t.TeacherRoute[Math.Min(t.TeacherRoute.Count - 1, 8)].ToString() : "-")
                + "; sides (teacher approach/end vs robot): " + string.Join("; ", parts) + "; " + t.Verdict;
        }
    }
}
