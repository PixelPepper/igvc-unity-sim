using System;
using System.Collections.Generic;

namespace IGVC.Reference.RacingLine
{
    /// <summary>Behavioural checks: QP optimality, line admissibility and ordering, lap-sim limits and an analytic circle.</summary>
    public static class RacingLineChecks
    {
        public static void Run(CheckContext c)
        {
            BoxQpChecks(c);
            CircleChecks(c);
            StudyChecks(c, "stadium", SyntheticCourses.Stadium(), 2.2, true);
            StudyChecks(c, "stadium+barrels", SyntheticCourses.Stadium(obstacles: new[] { SyntheticCourses.Barrel("b1", 5, 0), SyntheticCourses.Barrel("b2", -3, 16.9), SyntheticCourses.Barrel("b3", 15.5, 9) }), 2.2, false);
            if (c.Course != null) StudyChecks(c, "real course", c.Course, 2.2, false);
        }

        private static void BoxQpChecks(CheckContext c)
        {
            var rng = new SplitMix(11); double worstKkt = 0, worstGap = 0; bool better = true;
            foreach (int n in new[] { 5, 8, 8, 12, 40, 200 })
                for (int rep = 0; rep < (n <= 12 ? 6 : 2); rep++)
                {
                    var qp = new BoxQP(n); var idx = new int[3]; var cs = new V2[3];
                    for (int i = 0; i < n; i++)
                    {
                        for (int a = 0; a < 3; a++) { idx[a] = (i + a) % n; cs[a] = new V2(rng.Gauss(), rng.Gauss()); }
                        qp.AddResidual(new V2(rng.Gauss() * 3, rng.Gauss() * 3), idx, cs, 3, rng.Range(.2, 2));
                    }
                    for (int i = 0; i < n; i++) qp.H[i, i] += 1e-3;
                    var lo = new double[n]; var hi = new double[n]; var x = new double[n];
                    for (int i = 0; i < n; i++) { double m = rng.Range(-1, 1), w = rng.Range(0, 1); lo[i] = m - w; hi[i] = m + (rng.NextDouble() < .1 ? -w : w); }
                    qp.Solve(x, lo, hi, 500, 1e-11);
                    worstKkt = Math.Max(worstKkt, qp.KktViolation(x, lo, hi));
                    if (n > 12) continue;
                    // Brute-force reference: projected gradient with step 1/L for many iterations on the dense matrix.
                    double lip = 0; for (int i = 0; i < n; i++) { double s = 0; for (int j = 0; j < n; j++) s += Math.Abs(qp.H[i, j]); lip = Math.Max(lip, s); }
                    var y = new double[n]; var g = new double[n];
                    for (int it = 0; it < 60000; it++)
                    {
                        for (int i = 0; i < n; i++) { double s = qp.G[i]; for (int j = 0; j < n; j++) s += qp.H[i, j] * y[j]; g[i] = s; }
                        for (int i = 0; i < n; i++) y[i] = Math.Min(hi[i], Math.Max(lo[i], y[i] - g[i] / lip));
                    }
                    double fq = Dense(qp, x), fp = Dense(qp, y);
                    worstGap = Math.Max(worstGap, Math.Abs(fq - fp) / Math.Max(1, Math.Abs(fp)));
                    if (fq > fp + 1e-8) better = false;
                }
            c.Note("BoxQP worst KKT violation " + worstKkt.ToString("0.0e0") + ", worst objective gap to projected gradient " + worstGap.ToString("0.0e0"));
            c.Check(worstKkt <= 1e-6, "BoxQP satisfies KKT on random cyclic box QPs (incl. pinned variables)");
            c.Check(worstGap <= 1e-7 && better, "BoxQP matches a dense projected-gradient solution on small QPs");
        }
        private static double Dense(BoxQP qp, double[] x)
        {
            double f = 0;
            for (int i = 0; i < qp.N; i++) { double s = 0; for (int j = 0; j < qp.N; j++) s += qp.H[i, j] * x[j]; f += x[i] * (.5 * s + qp.G[i]); }
            return f;
        }

        private static void CircleChecks(CheckContext c)
        {
            var r = new RobotLimits(); bool ok = true; string detail = "";
            foreach (double radius in new[] { 4.0, 1.0, .4 })
            {
                var pts = new List<V2>(); var hw = new List<double>(); var painted = new List<bool>();
                int m = (int)Math.Ceiling(2 * Math.PI * radius / .01);
                for (int i = 0; i < m; i++) { pts.Add(V2.FromAngle(2 * Math.PI * i / m - Math.PI / 2) * radius + new V2(0, radius)); hw.Add(radius * .3); painted.Add(true); }
                var cor = new Corridor(CourseGeometry.Create(pts, hw, painted, radius * .6, null, null, 0, "circle"));
                var lap = LapSim.Simulate(cor.P, r, 2.2);
                double k = 1 / radius, cap = Math.Min(Math.Min(2.2, Math.Sqrt(r.MaxLateral / k)), Math.Min(r.WheelSpeedCap(k), r.MaxYawRate / k));
                double expected = 2 * Math.PI * radius / cap, err = Math.Abs(lap.LapTime - expected) / expected;
                detail += " r=" + radius + ": " + lap.LapTime.ToString("0.000") + " s vs " + expected.ToString("0.000") + " s;";
                ok &= err < .005 && LimitsHold(lap, r, 2.2, out _);
            }
            c.Note("circle laps:" + detail);
            c.Check(ok, "LapSim on circles equals 2 pi r / min(ceiling, lateral, wheel, yaw-rate caps) (wheel, lateral and yaw caps each binding once)");
        }

        /// <summary>Every sample within speed, wheel, yaw-rate, lateral and friction-ellipse limits.</summary>
        public static bool LimitsHold(LapResult lap, RobotLimits r, double ceiling, out string why)
        {
            const double tol = 1e-4; why = null;
            for (int i = 0; i < lap.N; i++)
            {
                double v = lap.V[i];
                if (v > Math.Min(ceiling, r.MaxSpeed) + tol) why = "ceiling";
                else if (lap.WheelOuter[i] > r.MaxSpeed + tol) why = "wheel";
                else if (lap.YawRate[i] > r.MaxYawRate + tol) why = "yaw rate";
                else if (Math.Abs(lap.ALat[i]) > r.MaxLateral + tol) why = "lateral";
                else if (lap.ALong[i] > r.MaxAccel + tol || lap.ALong[i] < -r.MaxBrake - tol) why = "longitudinal";
                else if (lap.Usage[i] > 1 + tol) why = "friction ellipse";
                if (why != null) { why += " at " + i; return false; }
            }
            return true;
        }

        private static void StudyChecks(CheckContext c, string name, CourseGeometry course, double ceiling, bool clean)
        {
            var watch = System.Diagnostics.Stopwatch.StartNew();
            var cor = new Corridor(course); var shapes = course.Shapes(); var limits = new RobotLimits();
            var study = new RacingLineStudy(cor, shapes, limits) { SpeedCeiling = ceiling, GaGenerations = clean ? 30 : 60, DescentIterations = clean ? 40 : 80 };
            foreach (var _ in study.CompareAll()) { }
            c.Note(name + ": " + cor.Length.ToString("0.0") + " m, " + cor.N + " stations, " + shapes.Length + " obstacles, blocked stations " + study.BlockedStations + ", optimiser time " + watch.ElapsedMilliseconds + " ms");
            foreach (var line in study.Summary()) c.Note(name + " | " + line);
            var row = new Dictionary<LineMethod, LineRow>();
            foreach (var r in study.Comparison) row[r.Method] = r;
            c.Check(row.Count == 6, name + ": all six line methods produced a line");

            bool inside = true, limitsOk = true; string why = "";
            for (int m = 0; m < 6; m++)
            {
                var a = study.LineOf((LineMethod)m);
                inside &= study.Track.MaxViolation(a) <= 1e-9;
                var pts = study.Track.Points(a);
                if (!LimitsHold(LapSim.Simulate(pts, limits, ceiling), limits, ceiling, out string w1)) { limitsOk = false; why += RacingLineStudy.Names[m] + " flying " + w1 + "; "; }
                var standing = LapSim.Simulate(pts, limits, ceiling, null, true, true);
                if (!LimitsHold(standing, limits, ceiling, out string w2) || standing.V[0] != 0) { limitsOk = false; why += RacingLineStudy.Names[m] + " standing " + w2 + "; "; }
            }
            c.Check(inside, name + ": every line stays within its per-station bounds [lo, hi]");
            c.Check(limitsOk, name + ": lap sim respects ceiling, wheel, yaw-rate, lateral, accel/brake and ellipse limits at every sample (flying and standing) " + why);

            LineRow centre = row[LineMethod.Centre], shortest = row[LineMethod.Shortest], minc = row[LineMethod.MinCurvature], comp = row[LineMethod.Compromise];
            // The QP minimises mean-square curvature; its peak can exceed a constant-radius centre arc (open stadium), so
            // max |k| is only required to drop where the centre line has to dodge obstacles.
            c.Check(minc.MeanSqKappa < centre.MeanSqKappa && minc.LapTime <= centre.LapTime + 1e-9 && (clean || minc.MaxKappa < centre.MaxKappa), name + ": min-curvature line has lower mean-square |k|" + (clean ? "" : " and max |k|") + " and lap time <= centre line (max |k| " + minc.MaxKappa.ToString("0.000") + " vs " + centre.MaxKappa.ToString("0.000") + ")");
            c.Check(shortest.Length <= centre.Length + 1e-9, name + ": shortest line is no longer than the centre line");
            c.Check(comp.LapTime <= minc.LapTime + 1e-9 && comp.Length >= shortest.Length - .02 && comp.Length <= minc.Length + .02, name + ": compromise is no slower than min-curvature and its length lies between shortest and min-curvature");
            c.Check(study.GA.BestTime <= study.GA.SeedTime + 1e-12 && Math.Abs(study.GA.SeedTime - minc.LapTime) < 1e-9 && row[LineMethod.Genetic].LapTime <= minc.LapTime + 1e-9, name + ": GA starts exactly at its min-curvature seed and never gets worse");
            c.Check(study.Descent.Time <= study.Descent.StartTime + 1e-12 && row[LineMethod.GradientDescent].LapTime <= minc.LapTime + 1e-9, name + ": lap-time descent never worse than its seed line");
            bool mono = true; for (int k = 1; k < study.GA.BestHistory.Count; k++) mono &= study.GA.BestHistory[k] <= study.GA.BestHistory[k - 1] + 1e-12;
            c.Check(mono, name + ": GA best lap time is monotone over generations (elitism)");

            if (clean)
            {
                var again = new RacingLineStudy(cor, shapes, limits) { SpeedCeiling = ceiling, GaGenerations = 30, DescentIterations = 40 };
                foreach (var _ in again.CompareAll()) { }
                bool same = true;
                for (int m = 0; m < 6; m++) same &= again.Comparison[m].LapTime == study.Comparison[m].LapTime;
                c.Check(same, name + ": every method is deterministic for a fixed seed");
                again.Seed = 99; again.Method = LineMethod.Genetic; foreach (var _ in again.Run()) { }
                c.Note(name + ": GA seed 99 lap " + again.Lap.LapTime.ToString("0.000") + " s vs seed 1 " + row[LineMethod.Genetic].LapTime.ToString("0.000") + " s");
                c.Check(study.BlockedStations == 0, name + ": open stadium has no blocked stations");
            }
            else
            {
                var tr = study.Track; bool linked = true;
                for (int i = 0; i < tr.N && !tr.Disconnected; i++)
                {
                    int j = tr.Wrap(i + 1);
                    if (tr.Blocked.Contains(i) || tr.Blocked.Contains(j)) continue;
                    linked &= Math.Min(tr.Hi[i], tr.Hi[j]) - Math.Max(tr.Lo[i], tr.Lo[j]) >= RaceTrack.MinOverlap - 1e-9;
                }
                c.Check(!tr.Disconnected && linked, name + ": without a route, consecutive station gaps overlap all round the loop (one consistent side per obstacle)");
                c.Check(study.LineContactStations.Count == 0, name + ": selected line clears the whole body at every station after bound repair (" + study.RepairedStations + " stations narrowed)");
            }
            if (clean)
            {
                // Bound repair: with a disc smaller than the body half-width the min-curvature line hits the lane edge;
                // repair must narrow the bounds until the whole body clears (and stay inside the original bounds).
                var narrow = new Corridor(SyntheticCourses.Stadium(halfWidth: 1.6));
                var raw = new RacingLineStudy(narrow, shapes, limits) { SpeedCeiling = ceiling, ExtraMargin = -.4, BodyRepair = false };
                foreach (var _ in raw.Run()) { }
                var fixedUp = new RacingLineStudy(narrow, shapes, limits) { SpeedCeiling = ceiling, ExtraMargin = -.4 };
                foreach (var _ in fixedUp.Run()) { }
                bool subset = true; for (int i = 0; i < narrow.N; i++) subset &= fixedUp.Lo[i] >= raw.Lo[i] - 1e-12 && fixedUp.Hi[i] <= raw.Hi[i] + 1e-12;
                c.Note(name + ": thin-disc line body contacts " + raw.LineContactStations.Count + " -> " + fixedUp.LineContactStations.Count + " after repair (" + fixedUp.RepairedStations + " stations, " + fixedUp.RepairIterations + " passes)");
                c.Check(raw.LineContactStations.Count > 0 && fixedUp.LineContactStations.Count == 0 && subset, name + ": body repair removes whole-body contacts of the min-curvature line by narrowing (never widening) its bounds");
            }
            if (name == "stadium+barrels")
            {
                // A planner route passing the first barrel on the left must select the left gap there.
                var routed = new RacingLineStudy(cor, shapes, limits) { SpeedCeiling = ceiling };
                routed.SetRoute(new List<V2> { new V2(-10, 0), new V2(0, 0), new V2(5, 1.6), new V2(10, 0), new V2(18, 8), new V2(10, 16), new V2(-10, 16), new V2(-18, 8), new V2(-10, 0) });
                foreach (var _ in routed.Run()) { }
                int st = (int)Math.Round(5 / cor.Ds);
                c.Check(routed.Lo[st] > 0, name + ": a planner route on the left of a barrel selects the left gap (lo " + routed.Lo[st].ToString("0.00") + " m)");
            }
        }
    }
}
