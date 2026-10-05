using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace IGVC.Reference.RacingLine
{
    public sealed class LineRow
    {
        public LineMethod Method;
        public string Name, Note = "";
        public double LapTime, StandingLap, Length, MaxKappa, MeanSqKappa, Millis;
        public int Iterations, FootprintContacts;
    }

    /// <summary>
    /// Racing-line study on the WORLD corridor (reference only, not autonomy). Bounds come from
    /// Corridor.BoundsFromRoute with the axle disc (inscribed radius + ExtraMargin); a planner route picks the side of
    /// each obstacle, null = the gap nearest the centre. Lap times are LOWER BOUNDS under assumed RobotLimits.
    /// The 1.7 m body is not in the bounds (disc only): every line is re-checked with the whole-body footprint.
    /// </summary>
    public sealed class RacingLineStudy
    {
        public static readonly string[] Names = { "Centre", "Shortest", "Min curvature", "Compromise", "Genetic", "Lap-time descent" };
        public readonly Corridor Corridor;
        public readonly Capsule[] Shapes;
        public readonly RobotLimits Limits;
        public LineMethod Method = LineMethod.MinCurvature;
        /// <summary>SpeedCeiling (m/s) caps the lap sim; CompromiseWeight 0 = sweep GeometricLines.CompromiseEps on lap time (see ChosenCompromiseEps).</summary>
        public double SpeedCeiling = 2.2, ExtraMargin = .1, CompromiseWeight;
        public ulong Seed = 1;
        public int GaGenerations = 120, GaPopulation = 40, DescentIterations = 120;
        public double GaKnotSpacing = 3, DescentKnotSpacing = 1.5;
        /// <summary>Narrow the disc bounds where the min-curvature line's whole body would touch (see RepairBounds).</summary>
        public bool BodyRepair = true;
        public int RepairedStations { get; private set; }
        public int RepairIterations { get; private set; }

        public RaceTrack Track { get; private set; }
        public double[] Lo, Hi, Alpha;
        public V2[] Line;
        public LapResult Lap, StandingLap;
        public int BlockedStations;
        public double ChosenCompromiseEps { get; private set; }
        /// <summary>Stations of the selected line where the whole body (yaw = line tangent) touches an edge or obstacle.</summary>
        public readonly List<int> LineContactStations = new List<int>();
        public IReadOnlyList<LineRow> Comparison => rows;
        public LineGA GA { get; private set; }
        public LapTimeDescent Descent { get; private set; }

        private readonly List<LineRow> rows = new List<LineRow>();
        private readonly Dictionary<LineMethod, double[]> lines = new Dictionary<LineMethod, double[]>();
        private IList<V2> route;
        private string key;
        private BoxQP qp;
        private bool repaired;

        public RacingLineStudy(Corridor corridor, Capsule[] shapes, RobotLimits limits)
        {
            Corridor = corridor; Shapes = shapes ?? new Capsule[0]; Limits = limits ?? new RobotLimits();
        }

        public void SetRoute(IList<V2> route) { this.route = route == null ? null : new List<V2>(route); key = null; }

        /// <summary>Rebuilds bounds and forgets cached lines when the route, margin or ceiling changed.</summary>
        private void Ensure()
        {
            string k = ExtraMargin.ToString("R") + "|" + SpeedCeiling.ToString("R") + "|" + CompromiseWeight.ToString("R") + "|" + Seed + "|" + GaGenerations + "|" + DescentIterations + "|" + BodyRepair;
            if (Track != null && k == key) return;
            bool boundsChanged = Track == null || key == null || Track.Clearance != Limits.InscribedRadius + ExtraMargin || BodyRepair != repaired;
            repaired = BodyRepair;
            key = k; lines.Clear(); rows.Clear(); GA = null; Descent = null;
            if (boundsChanged)
            {
                Track = new RaceTrack(Corridor, Shapes, Limits.InscribedRadius + ExtraMargin, route);
                Lo = Track.Lo; Hi = Track.Hi; BlockedStations = Track.Blocked.Count; qp = new BoxQP(Track.N);
                if (BodyRepair) RepairBounds();
            }
        }

        /// <summary>
        /// Body-aware bounds: the axle-disc bounds ignore the 1.7 m body, whose corners swing out when the line turns
        /// or jinks round a barrel. Solve the min-curvature line, find stations where the whole footprint (yaw = line
        /// tangent) touches, narrow the bounds there (+-3 stations, on the side the line hugs) and repeat.
        /// </summary>
        private void RepairBounds()
        {
            var touched = new HashSet<int>(); var hits = new List<int>(); RepairIterations = 0;
            for (int it = 0; it < 12; it++)
            {
                var a = GeometricLines.Solve(Track, 1, 0, qp, out _);
                if (BodyContacts(Track.Points(a), hits) == 0) break;
                RepairIterations++;
                foreach (int i in hits)
                    for (int j = -3; j <= 3; j++) { int s = Track.Wrap(i + j); Track.Tighten(s, a[s], .08); touched.Add(s); }
            }
            RepairedStations = touched.Count;
        }

        public double[] LineOf(LineMethod m) => lines.TryGetValue(m, out var a) ? a : null;

        public IEnumerable<string> Run()
        {
            Ensure();
            foreach (var s in Compute(Method)) yield return s;
            Select(Method);
            yield return Names[(int)Method] + ": " + Lap.LapTime.ToString("0.00") + " s flying lap (lower bound)";
        }

        public IEnumerable<string> CompareAll()
        {
            Ensure();
            for (int m = 0; m <= (int)LineMethod.GradientDescent; m++)
                foreach (var s in Compute((LineMethod)m)) yield return s;
            Select(Method);
            yield return "comparison complete";
        }

        private IEnumerable<string> Compute(LineMethod m)
        {
            if (lines.ContainsKey(m)) yield break;
            var tr = Track; var watch = Stopwatch.StartNew(); int iterations = 0; string note = "";
            double[] alpha = null;
            switch (m)
            {
                case LineMethod.Centre: alpha = tr.CentreLine(); break;
                case LineMethod.Shortest: alpha = GeometricLines.Solve(tr, 0, 1, qp, out iterations); note = "QP"; break;
                case LineMethod.MinCurvature: alpha = GeometricLines.Solve(tr, 1, 0, qp, out iterations); note = "QP"; break;
                case LineMethod.Compromise:
                    if (CompromiseWeight > 0) { alpha = GeometricLines.Solve(tr, 1, CompromiseWeight, qp, out iterations); ChosenCompromiseEps = CompromiseWeight; }
                    else
                    {
                        double best = double.MaxValue; var scratch = LapSim.Alloc(tr.N);
                        foreach (var e in GeometricLines.CompromiseEps)
                        {
                            var a = GeometricLines.Solve(tr, 1, e, qp, out int it); iterations += it;
                            double t = LapSim.LapTime(tr.Points(a), Limits, SpeedCeiling, scratch);
                            if (t < best) { best = t; alpha = a; ChosenCompromiseEps = e; }
                            yield return "compromise eps " + e.ToString("0.#####") + ": " + t.ToString("0.00") + " s";
                        }
                    }
                    note = "eps " + ChosenCompromiseEps.ToString("0.#####");
                    break;
                case LineMethod.Genetic:
                case LineMethod.GradientDescent:
                    if (!lines.ContainsKey(LineMethod.MinCurvature)) foreach (var s in Compute(LineMethod.MinCurvature)) yield return s;
                    var seedLine = lines[LineMethod.MinCurvature];
                    watch.Restart();
                    if (m == LineMethod.Genetic)
                    {
                        GA = new LineGA(tr, Limits, SpeedCeiling, seedLine, Seed, KnotLine.KnotCountFor(tr, GaKnotSpacing)) { Population = GaPopulation, MaxGenerations = GaGenerations };
                        GA.Init();
                        while (!GA.Done) { GA.Step(); yield return "GA gen " + GA.Generation + "/" + GA.MaxGenerations + " best " + GA.BestTime.ToString("0.000") + " s"; }
                        alpha = GA.BestStations(); iterations = GA.Generation; note = "seed min-curv " + GA.SeedTime.ToString("0.00") + " s, " + GA.Evaluations + " laps";
                    }
                    else
                    {
                        Descent = new LapTimeDescent(tr, Limits, SpeedCeiling, seedLine, KnotLine.KnotCountFor(tr, DescentKnotSpacing)) { MaxIterations = DescentIterations };
                        while (Descent.Iterate()) yield return "descent it " + Descent.Iteration + " " + Descent.Time.ToString("0.000") + " s";
                        alpha = Descent.Stations(); iterations = Descent.Iteration; note = "seed min-curv " + Descent.StartTime.ToString("0.00") + " s, " + Descent.Evaluations + " laps";
                    }
                    break;
            }
            double ms = watch.Elapsed.TotalMilliseconds;
            lines[m] = alpha;
            var pts = tr.Points(alpha);
            var lap = LapSim.Simulate(pts, Limits, SpeedCeiling);
            var row = new LineRow
            {
                Method = m, Name = Names[(int)m], Note = note, LapTime = lap.LapTime, Length = lap.Length, MaxKappa = lap.MaxKappa, MeanSqKappa = lap.MeanSqKappa, Millis = ms, Iterations = iterations,
                StandingLap = LapSim.Simulate(pts, Limits, SpeedCeiling, null, false, true).LapTime, FootprintContacts = BodyContacts(pts, null),
            };
            rows.RemoveAll(r => r.Method == m); rows.Add(row); rows.Sort((a, b) => a.Method.CompareTo(b.Method));
            yield return row.Name + " " + row.LapTime.ToString("0.00") + " s";
        }

        private void Select(LineMethod m)
        {
            Alpha = lines[m]; Line = Track.Points(Alpha);
            Lap = LapSim.Simulate(Line, Limits, SpeedCeiling);
            StandingLap = LapSim.Simulate(Line, Limits, SpeedCeiling, null, true, true);
            BodyContacts(Line, LineContactStations);
        }

        /// <summary>Whole-body footprint at every station of a line, yaw = local line tangent.</summary>
        public int BodyContacts(V2[] pts, List<int> stations)
        {
            stations?.Clear(); int n = pts.Length, count = 0, hint = -1;
            for (int i = 0; i < n; i++)
            {
                double yaw = (pts[(i + 1) % n] - pts[(i - 1 + n) % n]).Angle;
                if (Corridor.FootprintContact(pts[i], yaw, Limits, Shapes, ref hint) != null) { count++; stations?.Add(i); }
            }
            return count;
        }

        public string[] Summary()
        {
            var s = new List<string> { "Reference (full course knowledge) - not autonomy. Lap times are lower bounds under ASSUMED limits (accel " + Limits.MaxAccel + ", brake " + Limits.MaxBrake + ", lateral " + Limits.MaxLateral + " m/s^2, yaw " + Limits.MaxYawRate + " rad/s)." };
            if (Track != null)
                s.Add("Bounds: axle disc " + Track.Clearance.ToString("0.00") + " m, " + (route == null ? (Track.Disconnected ? "centre-nearest gaps (no connected gap chain!)" : "connected gaps nearest the centre") : "gaps chosen by planner route") + (BodyRepair ? ", body repair narrowed " + RepairedStations + " stations in " + RepairIterations + " passes" : "") + ", blocked stations " + BlockedStations + (BlockedStations > 0 ? " (at s = " + BlockedSpans() + ")" : ""));
            if (Lap != null)
            {
                s.Add(Names[(int)Method] + ": flying " + Lap.LapTime.ToString("0.00") + " s, standing " + StandingLap.LapTime.ToString("0.00") + " s, " + Lap.Length.ToString("0.0") + " m, ceiling " + SpeedCeiling.ToString("0.0#") + " m/s, max |k| " + Lap.MaxKappa.ToString("0.00") + "/m, " + Lap.BrakeZones + " braking zones");
                s.Add("Whole-body contacts along the line: " + LineContactStations.Count + " of " + Lap.N + " stations");
            }
            foreach (var r in rows)
                s.Add(r.Name.PadRight(17) + r.LapTime.ToString("0.00").PadLeft(8) + " s " + r.Length.ToString("0.0").PadLeft(7) + " m  |k|max " + r.MaxKappa.ToString("0.00") + "  " + r.Millis.ToString("0") + " ms  it " + r.Iterations + "  body hits " + r.FootprintContacts + (r.Note.Length > 0 ? "  (" + r.Note + ")" : ""));
            return s.ToArray();
        }

        private string BlockedSpans()
        {
            var parts = new List<string>(); var b = Track.Blocked;
            for (int k = 0; k < b.Count && parts.Count < 6; k++)
            {
                int start = b[k]; while (k + 1 < b.Count && b[k + 1] == b[k] + 1) k++;
                parts.Add(Corridor.S[start].ToString("0.0") + (b[k] != start ? "-" + Corridor.S[b[k]].ToString("0.0") : ""));
            }
            return string.Join(", ", parts);
        }
    }
}
