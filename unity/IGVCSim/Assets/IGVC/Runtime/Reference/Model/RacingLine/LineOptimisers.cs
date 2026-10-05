using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace IGVC.Reference.RacingLine
{
    /// <summary>
    /// Bound-constrained convex QP  min 0.5 x'Hx + g'x  s.t. lo &lt;= x &lt;= hi by projected Newton (Bertsekas 1982):
    /// variables on a bound with the gradient pushing outwards are frozen, a Newton step is taken on the free ones
    /// (envelope Cholesky of the free sub-Hessian) and an Armijo search runs along the projection arc. H must be cyclic
    /// penta-diagonal (entries only for cyclic index distance &lt;= 2), which every line objective here is: O(N) per factorisation.
    /// </summary>
    public sealed class BoxQP
    {
        public readonly int N;
        public readonly double[,] H;
        public readonly double[] G;
        public int Iterations { get; private set; }
        public int Factorisations { get; private set; }
        private readonly double[,] l;
        private readonly double[] grad, dir, trial, rhs;
        private readonly int[] free, first;

        public BoxQP(int n)
        {
            N = n; H = new double[n, n]; G = new double[n]; l = new double[n, n];
            grad = new double[n]; dir = new double[n]; trial = new double[n]; rhs = new double[n]; free = new int[n]; first = new int[n];
        }
        public void Clear() { Array.Clear(H, 0, H.Length); Array.Clear(G, 0, G.Length); }

        private double Hx(double[] x, int i)
        {
            double s = 0;
            for (int j = Math.Max(0, i - 2); j <= Math.Min(N - 1, i + 2); j++) s += H[i, j] * x[j];
            if (i < 2) for (int j = N - 2; j < N; j++) if (j > i + 2) s += H[i, j] * x[j];
            if (i >= N - 2) for (int j = 0; j < 2; j++) if (j < i - 2) s += H[i, j] * x[j];
            return s;
        }
        public double Objective(double[] x)
        {
            double f = 0;
            for (int i = 0; i < N; i++) f += x[i] * (.5 * Hx(x, i) + G[i]);
            return f;
        }
        public void Gradient(double[] x, double[] g) { for (int i = 0; i < N; i++) g[i] = G[i] + Hx(x, i); }

        /// <summary>Solves in place (x is the warm start, clamped first). Returns the final objective.</summary>
        public double Solve(double[] x, double[] lo, double[] hi, int maxIter = 200, double tol = 1e-9)
        {
            for (int i = 0; i < N; i++) x[i] = Math.Min(hi[i], Math.Max(lo[i], x[i]));
            double f = Objective(x);
            Iterations = 0; Factorisations = 0;
            for (int it = 0; it < maxIter; it++)
            {
                Iterations = it + 1;
                Gradient(x, grad);
                int nf = 0; double pg = 0;
                for (int i = 0; i < N; i++)
                {
                    bool bound = (x[i] <= lo[i] + 1e-12 && grad[i] > 0) || (x[i] >= hi[i] - 1e-12 && grad[i] < 0) || hi[i] - lo[i] < 1e-12;
                    if (!bound) { free[nf++] = i; pg = Math.Max(pg, Math.Abs(grad[i])); }
                }
                if (pg < tol || !FactorFree(nf)) break;
                for (int a = 0; a < nf; a++) rhs[a] = -grad[free[a]];
                SolveFactored(nf, rhs);
                Array.Clear(dir, 0, N);
                for (int a = 0; a < nf; a++) dir[free[a]] = rhs[a];
                double t = 1; bool accepted = false;
                for (int ls = 0; ls < 40; ls++)
                {
                    double decrease = 0;
                    for (int i = 0; i < N; i++)
                    {
                        double v = Math.Min(hi[i], Math.Max(lo[i], x[i] + t * dir[i]));
                        trial[i] = v; decrease += grad[i] * (v - x[i]);
                    }
                    double ft = Objective(trial);
                    if (ft <= f + 1e-4 * decrease + 1e-15)
                    {
                        Array.Copy(trial, x, N);
                        bool small = f - ft < 1e-14 * Math.Max(1, Math.Abs(f));
                        f = ft; accepted = true;
                        if (small && t == 1) it = maxIter; // exact Newton step changed nothing: converged
                        break;
                    }
                    t *= .5;
                }
                if (!accepted) break;
            }
            return f;
        }

        // Envelope (skyline) Cholesky of the free sub-matrix: fill-in stays inside each row's envelope.
        private bool FactorFree(int nf)
        {
            Factorisations++;
            for (int a = 0; a < nf; a++)
            {
                int ia = free[a], f = a;
                for (int b = 0; b < a; b++) if (H[ia, free[b]] != 0) { f = b; break; }
                first[a] = f;
                for (int b = f; b <= a; b++) l[a, b] = H[ia, free[b]];
            }
            for (int a = 0; a < nf; a++)
            {
                int fa = first[a];
                for (int b = fa; b < a; b++)
                {
                    double s = l[a, b];
                    for (int k = Math.Max(fa, first[b]); k < b; k++) s -= l[a, k] * l[b, k];
                    l[a, b] = s / l[b, b];
                }
                double d = l[a, a];
                for (int k = fa; k < a; k++) d -= l[a, k] * l[a, k];
                if (d <= 1e-14) return false;
                l[a, a] = Math.Sqrt(d);
            }
            return true;
        }
        private void SolveFactored(int nf, double[] b)
        {
            for (int a = 0; a < nf; a++)
            {
                double s = b[a];
                for (int k = first[a]; k < a; k++) s -= l[a, k] * b[k];
                b[a] = s / l[a, a];
            }
            for (int a = nf - 1; a >= 0; a--)
            {
                double s = b[a] / l[a, a]; b[a] = s;
                for (int k = first[a]; k < a; k++) b[k] -= l[a, k] * s;
            }
        }

        /// <summary>Adds w |r|^2 for the 2-D residual r = d + sum_j c_j x_idx[j] (H += 2w c c', g += 2w c d).</summary>
        public void AddResidual(V2 d, int[] idx, V2[] c, int count, double w)
        {
            for (int a = 0; a < count; a++)
            {
                G[idx[a]] += 2 * w * V2.Dot(c[a], d);
                for (int b = 0; b < count; b++) H[idx[a], idx[b]] += 2 * w * V2.Dot(c[a], c[b]);
            }
        }

        /// <summary>Largest violation of grad = 0 (free), grad &gt;= 0 (at lo), grad &lt;= 0 (at hi).</summary>
        public double KktViolation(double[] x, double[] lo, double[] hi)
        {
            Gradient(x, grad);
            double worst = 0;
            for (int i = 0; i < N; i++)
            {
                double g = grad[i];
                bool atLo = x[i] <= lo[i] + 1e-7, atHi = x[i] >= hi[i] - 1e-7;
                worst = Math.Max(worst, atLo && atHi ? 0 : atLo ? Math.Max(0, -g) : atHi ? Math.Max(0, g) : Math.Abs(g));
            }
            return worst;
        }
    }

    /// <summary>Line methods in table order.</summary>
    public enum LineMethod { Centre, Shortest, MinCurvature, Compromise, Genetic, GradientDescent }

    /// <summary>
    /// Geometric lines as QPs in the offsets alpha (p_i = P_i + alpha_i Nl_i is linear in alpha):
    /// shortest = min sum |p_{i+1} - p_i|^2; minimum curvature = min sum |p_{i-1} - 2 p_i + p_{i+1}|^2 (the discrete second
    /// derivative is kappa ds^2 n); compromise = curvature + eps * length with eps swept on the simulated lap time.
    /// Bounds are the track's asymmetric per-station [lo, hi].
    /// </summary>
    public static class GeometricLines
    {
        /// <summary>
        /// Sweep for the compromise weight. Station spacing here is ~0.5 m (not the sandbox's 4 m), so the length term
        /// dominates much earlier; 0 is included so the compromise is never slower than min-curvature.
        /// </summary>
        public static readonly double[] CompromiseEps = { 0, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, .1, .3, 1 };

        public static void BuildObjective(BoxQP qp, RaceTrack tr, double wCurv, double wLen)
        {
            qp.Clear();
            int n = tr.N; var idx = new int[3]; var c = new V2[3];
            if (wCurv > 0)
                for (int i = 0; i < n; i++)
                {
                    int a = tr.Wrap(i - 1), b = i, d = tr.Wrap(i + 1);
                    idx[0] = a; idx[1] = b; idx[2] = d; c[0] = tr.Nl[a]; c[1] = tr.Nl[b] * -2; c[2] = tr.Nl[d];
                    qp.AddResidual(tr.P[a] - tr.P[b] * 2 + tr.P[d], idx, c, 3, wCurv);
                }
            if (wLen > 0)
                for (int i = 0; i < n; i++)
                {
                    int b = tr.Wrap(i + 1);
                    idx[0] = i; idx[1] = b; c[0] = -tr.Nl[i]; c[1] = tr.Nl[b];
                    qp.AddResidual(tr.P[b] - tr.P[i], idx, c, 2, wLen);
                }
            for (int i = 0; i < n; i++) qp.H[i, i] += 1e-9; // keeps H strictly positive definite on degenerate shapes
        }

        public static double[] Solve(RaceTrack tr, double wCurv, double wLen, BoxQP qp, out int iterations)
        {
            BuildObjective(qp, tr, wCurv, wLen);
            var x = tr.CentreLine();
            qp.Solve(x, tr.Lo, tr.Hi);
            iterations = qp.Iterations;
            return x;
        }
    }

    /// <summary>
    /// Low-dimensional line for the sampling optimisers: K knots of a lateral DELTA, periodic uniform Catmull-Rom,
    /// added to a base line and clamped to [lo, hi] at every station. Zero knots reproduce the base exactly, so a
    /// search seeded at zero can only improve on its seed line; any genome is a valid line by construction.
    /// </summary>
    public sealed class KnotLine
    {
        public readonly RaceTrack Track;
        public readonly int K;
        public readonly double[] Base, KnotLo, KnotHi;
        private readonly double[] alpha;
        private readonly V2[] pts;

        public KnotLine(RaceTrack tr, int k, double[] baseLine)
        {
            Track = tr; K = k; Base = new double[tr.N]; KnotLo = new double[k]; KnotHi = new double[k];
            for (int i = 0; i < tr.N; i++) Base[i] = tr.Clamp(i, baseLine == null ? 0 : baseLine[i]);
            for (int j = 0; j < k; j++)
            {
                int i = Math.Min(tr.N - 1, (int)Math.Round(j * tr.N / (double)k));
                // Delta range wide enough to reach either bound from the base; the station clamp keeps the line valid.
                double span = Math.Max(.05, tr.Hi[i] - tr.Lo[i]);
                KnotLo[j] = tr.Lo[i] - Base[i] - .25 * span; KnotHi[j] = tr.Hi[i] - Base[i] + .25 * span;
            }
            alpha = new double[tr.N]; pts = new V2[tr.N];
        }
        public static int KnotCountFor(RaceTrack tr, double spacing) => Math.Max(16, Math.Min(160, (int)Math.Round(tr.Length / spacing)));
        public double Span(int j) => .5 * (KnotHi[j] - KnotLo[j]);

        public double[] Expand(double[] knots, double[] into = null)
        {
            var tr = Track; into = into ?? new double[tr.N];
            for (int i = 0; i < tr.N; i++)
            {
                double u = i * K / (double)tr.N; int j = (int)Math.Floor(u); double f = u - j;
                double p0 = knots[(j - 1 + K) % K], p1 = knots[j % K], p2 = knots[(j + 1) % K], p3 = knots[(j + 2) % K];
                double v = .5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f * f * f);
                into[i] = tr.Clamp(i, Base[i] + v);
            }
            return into;
        }
        public V2[] Points(double[] knots) { Expand(knots, alpha); return Track.Points(alpha, pts); }
        public void Clamp(double[] knots) { for (int j = 0; j < K; j++) knots[j] = Math.Min(KnotHi[j], Math.Max(KnotLo[j], knots[j])); }
    }

    /// <summary>
    /// Genetic algorithm on the knot deltas; fitness = simulated lap time (lower is better). Elitism (best E copied
    /// unchanged, so the best never gets worse), tournament selection, two-point circular crossover, Gaussian gene
    /// jitter and a smooth "bump" mutation that moves a whole corner's line. Individual 0 is the zero delta (the seed
    /// line), the rest are random smooth perturbations of it.
    /// </summary>
    public sealed class LineGA
    {
        public int Population = 40, Elite = 2, Tournament = 3, MaxGenerations = 120;
        public double CrossoverRate = .9, GeneMutation = .08, BumpRate = .35, InitScale = .35;
        public readonly KnotLine Line;
        public readonly RobotLimits Limits;
        public readonly double Ceiling;
        public int Generation { get; private set; }
        public double[] Best { get; private set; }
        public double BestTime { get; private set; } = double.MaxValue;
        public double SeedTime { get; private set; }
        public readonly List<double> BestHistory = new List<double>(), MeanHistory = new List<double>();
        public long Evaluations { get; private set; }
        public double Millis { get; private set; }
        public bool Done => Generation >= MaxGenerations;
        private double[][] pop, next;
        private double[] fit, nextFit;
        private readonly SplitMix rng;
        private readonly LapResult scratch;

        public LineGA(RaceTrack tr, RobotLimits limits, double ceiling, double[] seedLine, ulong seed, int knots)
        {
            Line = new KnotLine(tr, knots, seedLine); Limits = limits; Ceiling = ceiling;
            rng = new SplitMix(seed); scratch = LapSim.Alloc(tr.N);
        }

        public void Init()
        {
            var sw = Stopwatch.StartNew(); int k = Line.K;
            pop = new double[Population][]; next = new double[Population][]; fit = new double[Population]; nextFit = new double[Population];
            for (int p = 0; p < Population; p++)
            {
                var g = new double[k];
                if (p > 0)
                {
                    for (int j = 0; j < k; j++) g[j] = rng.Range(-1, 1) * InitScale * Line.Span(j);
                    for (int pass = 0; pass < 2; pass++)
                    {
                        var c = (double[])g.Clone();
                        for (int j = 0; j < k; j++) g[j] = .5 * c[j] + .25 * (c[(j - 1 + k) % k] + c[(j + 1) % k]);
                    }
                    Line.Clamp(g);
                }
                pop[p] = g; next[p] = new double[k]; fit[p] = Evaluate(g);
            }
            SeedTime = fit[0]; Generation = 0; Record();
            Millis += sw.Elapsed.TotalMilliseconds;
        }
        public double Evaluate(double[] g) { Evaluations++; return LapSim.LapTime(Line.Points(g), Limits, Ceiling, scratch); }
        private void Record()
        {
            int bi = 0; double mean = 0;
            for (int p = 0; p < Population; p++) { mean += fit[p]; if (fit[p] < fit[bi]) bi = p; }
            if (fit[bi] < BestTime || Best == null) { BestTime = fit[bi]; Best = (double[])pop[bi].Clone(); }
            BestHistory.Add(fit[bi]); MeanHistory.Add(mean / Population);
        }
        private int Select()
        {
            int best = rng.Range(Population);
            for (int t = 1; t < Tournament; t++) { int c = rng.Range(Population); if (fit[c] < fit[best]) best = c; }
            return best;
        }
        /// <summary>One generation; returns the best lap time so far.</summary>
        public double Step()
        {
            if (pop == null) Init();
            var sw = Stopwatch.StartNew(); int k = Line.K;
            var order = new int[Population];
            for (int i = 0; i < Population; i++) order[i] = i;
            Array.Sort(order, (a, b) => fit[a] != fit[b] ? fit[a].CompareTo(fit[b]) : a.CompareTo(b));
            for (int e = 0; e < Elite; e++) { Array.Copy(pop[order[e]], next[e], k); nextFit[e] = fit[order[e]]; }
            for (int p = Elite; p < Population; p++)
            {
                var a = pop[Select()]; var child = next[p];
                Array.Copy(a, child, k);
                if (rng.NextDouble() < CrossoverRate)
                {
                    var b = pop[Select()];
                    int c1 = rng.Range(k), len = 1 + rng.Range(k - 1);
                    for (int t = 0; t < len; t++) { int j = (c1 + t) % k; child[j] = b[j]; }
                }
                for (int j = 0; j < k; j++) if (rng.NextDouble() < GeneMutation) child[j] += rng.Gauss() * .2 * Line.Span(j);
                if (rng.NextDouble() < BumpRate)
                {
                    int c = rng.Range(k); double amp = rng.Gauss() * .4 * Line.Span(c), width = rng.Range(.8, 2.5);
                    for (int t = -4; t <= 4; t++) child[(c + t + k) % k] += amp * Math.Exp(-(t * t) / (2 * width * width));
                }
                Line.Clamp(child);
                nextFit[p] = Evaluate(child);
            }
            var tp = pop; pop = next; next = tp; var tf = fit; fit = nextFit; nextFit = tf;
            Generation++; Record();
            Millis += sw.Elapsed.TotalMilliseconds;
            return BestTime;
        }
        public double[] BestStations() => Line.Expand(Best);
    }

    /// <summary>
    /// Projected descent on the simulated lap time over the knot deltas. Central finite differences give the gradient
    /// (2K lap simulations per iteration); the step (metres, on the largest component) is accepted only if the lap time
    /// drops, grows 1.5x after a success and halves after a failure. Starts at zero delta, i.e. exactly its seed line.
    /// </summary>
    public sealed class LapTimeDescent
    {
        public double StepSize = .3, MinStep = .005, MaxStep = 1.0, FdH = .03;
        public int MaxIterations = 120;
        public readonly KnotLine Line;
        public readonly RobotLimits Limits;
        public readonly double Ceiling;
        public double[] Knots { get; private set; }
        public double Time { get; private set; }
        public double StartTime { get; private set; }
        public int Iteration { get; private set; }
        public long Evaluations { get; private set; }
        public double Millis { get; private set; }
        public bool Done { get; private set; }
        public readonly List<double> History = new List<double>();
        private readonly double[] grad, trialK;
        private readonly LapResult scratch;

        public LapTimeDescent(RaceTrack tr, RobotLimits limits, double ceiling, double[] seedLine, int knots)
        {
            Line = new KnotLine(tr, knots, seedLine); Limits = limits; Ceiling = ceiling;
            Knots = new double[Line.K]; grad = new double[Line.K]; trialK = new double[Line.K]; scratch = LapSim.Alloc(tr.N);
            Time = StartTime = Eval(Knots); History.Add(Time);
        }
        private double Eval(double[] k) { Evaluations++; return LapSim.LapTime(Line.Points(k), Limits, Ceiling, scratch); }

        /// <summary>One iteration; false when converged.</summary>
        public bool Iterate()
        {
            if (Done) return false;
            var sw = Stopwatch.StartNew(); int K = Line.K; double gmax = 0;
            for (int j = 0; j < K; j++)
            {
                double x = Knots[j];
                Knots[j] = Math.Min(x + FdH, Line.KnotHi[j]); double hp = Knots[j] - x, fp = Eval(Knots);
                Knots[j] = Math.Max(x - FdH, Line.KnotLo[j]); double hm = x - Knots[j], fm = Eval(Knots);
                Knots[j] = x;
                grad[j] = hp + hm > 1e-9 ? (fp - fm) / (hp + hm) : 0;
                if ((x >= Line.KnotHi[j] - 1e-6 && grad[j] < 0) || (x <= Line.KnotLo[j] + 1e-6 && grad[j] > 0)) grad[j] = 0;
                gmax = Math.Max(gmax, Math.Abs(grad[j]));
            }
            bool improved = false;
            if (gmax > 1e-12)
                while (StepSize >= MinStep)
                {
                    for (int j = 0; j < K; j++) trialK[j] = Knots[j] - StepSize * grad[j] / gmax;
                    Line.Clamp(trialK);
                    double t = Eval(trialK);
                    if (t < Time - 1e-9) { Array.Copy(trialK, Knots, K); Time = t; StepSize = Math.Min(MaxStep, StepSize * 1.5); improved = true; break; }
                    StepSize *= .5;
                }
            Iteration++; History.Add(Time);
            if (!improved || Iteration >= MaxIterations) Done = true;
            Millis += sw.Elapsed.TotalMilliseconds;
            return !Done;
        }
        public double[] Stations() => Line.Expand(Knots);
    }
}
