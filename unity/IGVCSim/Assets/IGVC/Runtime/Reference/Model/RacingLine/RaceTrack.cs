using System;
using System.Collections.Generic;

namespace IGVC.Reference.RacingLine
{
    /// <summary>
    /// Corridor stations with per-station lateral bounds lo[i] &lt;= alpha_i &lt;= hi[i] for the robot axle. A line is a
    /// vector of offsets alpha along the left normal: p_i = P_i + alpha_i Nl_i (linear in alpha, so the geometric
    /// objectives are QPs). Bounds are asymmetric: obstacles split the lane and the route picks the gap.
    /// Blocked stations (no free interval for the axle disc) are pinned to the route/centre offset and listed.
    /// </summary>
    public sealed class RaceTrack
    {
        public readonly Corridor Corridor;
        public readonly int N;
        public readonly double Ds, Length, Clearance;
        public readonly V2[] P, Nl;
        public readonly double[] Lo, Hi, RouteOffset;
        public readonly List<int> Blocked = new List<int>();

        public RaceTrack(Corridor corridor, IList<Capsule> shapes, double clearance, IList<V2> route)
        {
            Corridor = corridor; N = corridor.N; Ds = corridor.Ds; Length = corridor.Length; Clearance = clearance;
            P = corridor.P; Nl = corridor.Nl;
            Lo = new double[N]; Hi = new double[N]; RouteOffset = new double[N];
            shapes = shapes ?? new Capsule[0];
            if (route != null && route.Count > 1) corridor.BoundsFromRoute(route, shapes, clearance, Lo, Hi, RouteOffset);
            else if (!ConnectedGaps(corridor, shapes, clearance, Lo, Hi)) { Disconnected = true; corridor.BoundsFromRoute(null, shapes, clearance, Lo, Hi, RouteOffset); }
            for (int i = 0; i < N; i++) if (Hi[i] - Lo[i] < 1e-9) Blocked.Add(i);
        }
        /// <summary>True when no chain of overlapping gaps closes the loop (bounds then fall back to per-station centre-nearest gaps).</summary>
        public readonly bool Disconnected;
        public const double MinOverlap = .05;

        /// <summary>
        /// Without a route, per-station "centre-nearest gap" can flip sides between neighbouring stations inside a barrel
        /// cluster, which no line can follow. Instead choose one gap per station so consecutive gaps overlap (one
        /// homotopy class round the closed loop), minimising the summed distance of the gaps from the centre line.
        /// Blocked stations (no gap) connect to anything and are pinned to the previous gap's middle.
        /// </summary>
        public static bool ConnectedGaps(Corridor c, IList<Capsule> shapes, double clearance, double[] lo, double[] hi)
        {
            int n = c.N; var gaps = new Interval[n][]; var scratch = new List<Interval>();
            for (int i = 0; i < n; i++) { c.FreeIntervals(i, shapes, clearance, scratch); gaps[i] = scratch.ToArray(); }
            double Cost(Interval v) => v.Lo > 0 ? v.Lo : v.Hi < 0 ? -v.Hi : 0;
            bool Links(Interval[] a, int ia, Interval[] b, int ib) => a.Length == 0 || b.Length == 0 || Math.Min(a[ia].Hi, b[ib].Hi) - Math.Max(a[ia].Lo, b[ib].Lo) >= MinOverlap;
            double bestTotal = double.PositiveInfinity; int[] bestChoice = null;
            int starts = Math.Max(1, gaps[0].Length);
            for (int c0 = 0; c0 < starts; c0++)
            {
                var cost = new double[n][]; var from = new int[n][];
                for (int i = 0; i < n; i++) { int m = Math.Max(1, gaps[i].Length); cost[i] = new double[m]; from[i] = new int[m]; }
                for (int k = 0; k < cost[0].Length; k++) cost[0][k] = k == c0 ? (gaps[0].Length > 0 ? Cost(gaps[0][k]) : 0) : double.PositiveInfinity;
                for (int i = 1; i < n; i++)
                    for (int k = 0; k < cost[i].Length; k++)
                    {
                        double own = gaps[i].Length > 0 ? Cost(gaps[i][k]) : 1, best = double.PositiveInfinity; int arg = -1;
                        for (int j = 0; j < cost[i - 1].Length; j++)
                            if (cost[i - 1][j] < best && Links(gaps[i - 1], j, gaps[i], k)) { best = cost[i - 1][j]; arg = j; }
                        cost[i][k] = best + own; from[i][k] = arg;
                    }
                for (int k = 0; k < cost[n - 1].Length; k++)
                {
                    if (double.IsInfinity(cost[n - 1][k]) || !Links(gaps[n - 1], k, gaps[0], c0) || cost[n - 1][k] >= bestTotal) continue;
                    bestTotal = cost[n - 1][k]; bestChoice = new int[n]; bestChoice[n - 1] = k;
                    for (int i = n - 1; i > 0; i--) bestChoice[i - 1] = from[i][bestChoice[i]];
                }
            }
            if (bestChoice == null) return false;
            double last = 0;
            for (int i = 0; i < n; i++)
            {
                if (gaps[i].Length == 0) { lo[i] = hi[i] = last; continue; }
                var v = gaps[i][bestChoice[i]]; lo[i] = v.Lo; hi[i] = v.Hi; last = .5 * (v.Lo + v.Hi);
            }
            return true;
        }

        /// <summary>Narrows station i's bounds by <paramref name="step"/> on the side the line is closer to (body-contact repair).</summary>
        public void Tighten(int i, double alpha, double step)
        {
            if (Hi[i] - Lo[i] < 2 * step) return;
            if (alpha - Lo[i] < Hi[i] - alpha) Lo[i] += step; else Hi[i] -= step;
        }
        /// <summary>Explicit bounds (tests, or a caller with its own bounds).</summary>
        public RaceTrack(Corridor corridor, double[] lo, double[] hi)
        {
            Corridor = corridor; N = corridor.N; Ds = corridor.Ds; Length = corridor.Length;
            P = corridor.P; Nl = corridor.Nl;
            Lo = (double[])lo.Clone(); Hi = (double[])hi.Clone(); RouteOffset = new double[N];
            for (int i = 0; i < N; i++) if (Hi[i] - Lo[i] < 1e-9) Blocked.Add(i);
        }

        public int Wrap(int i) => ((i % N) + N) % N;
        public double Clamp(int i, double a) => a < Lo[i] ? Lo[i] : a > Hi[i] ? Hi[i] : a;
        public V2 LinePoint(double[] alpha, int i) => P[i] + Nl[i] * alpha[i];
        public V2[] Points(double[] alpha, V2[] into = null)
        {
            into = into ?? new V2[N];
            for (int i = 0; i < N; i++) into[i] = P[i] + Nl[i] * alpha[i];
            return into;
        }
        public double LineLength(double[] alpha)
        {
            double l = 0;
            for (int i = 0; i < N; i++) l += V2.Distance(LinePoint(alpha, i), LinePoint(alpha, Wrap(i + 1)));
            return l;
        }
        /// <summary>The centre-nearest admissible line (clamp(0)); the baseline every optimiser is compared with.</summary>
        public double[] CentreLine()
        {
            var a = new double[N];
            for (int i = 0; i < N; i++) a[i] = Clamp(i, 0);
            return a;
        }
        public double MaxViolation(double[] alpha)
        {
            double w = 0;
            for (int i = 0; i < N; i++) w = Math.Max(w, Math.Max(Lo[i] - alpha[i], alpha[i] - Hi[i]));
            return w;
        }
    }

    /// <summary>Seeded SplitMix64 (no shared state; every optimiser owns one).</summary>
    public sealed class SplitMix
    {
        private ulong s;
        public SplitMix(ulong seed) { s = seed * 0x9E3779B97F4A7C15UL + 0x632BE59BD9B4E019UL; }
        public ulong Next()
        {
            ulong z = s += 0x9E3779B97F4A7C15UL;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
            return z ^ (z >> 31);
        }
        public double NextDouble() => (Next() >> 11) * (1.0 / (1UL << 53));
        public double Range(double a, double b) => a + NextDouble() * (b - a);
        public int Range(int n) => (int)(NextDouble() * n);
        public double Gauss()
        {
            double u1 = Math.Max(1e-12, NextDouble()), u2 = NextDouble();
            return Math.Sqrt(-2 * Math.Log(u1)) * Math.Cos(2 * Math.PI * u2);
        }
    }
}
