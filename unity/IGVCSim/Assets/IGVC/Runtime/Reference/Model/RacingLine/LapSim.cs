using System;

namespace IGVC.Reference.RacingLine
{
    /// <summary>Everything the lap simulator knows about one line (per point: segment i runs from point i to i+1).</summary>
    public sealed class LapResult
    {
        public int N;
        public V2[] Pts;
        public double[] Kappa, Ds, VMax, V, ALong, ALat, YawRate, WheelOuter, Usage, T;
        public bool[] Braking;
        public double LapTime, Length, MinSpeed, MaxSpeed, MaxKappa, MeanSqKappa, MaxUsage, Ceiling;
        /// <summary>Standing lap only: speed when the line closes at point 0 again.</summary>
        public double EndV;
        public int BrakeZones;
        /// <summary>True when the lap starts from rest at point 0 (an open lap); false = flying (periodic) lap.</summary>
        public bool Standing;
    }

    /// <summary>
    /// Point-mass lap-time LOWER BOUND for the R3-a under the (partly assumed) RobotLimits. Speed caps per point:
    /// <code>v &lt;= min(ceiling, MaxSpeed, sqrt(MaxLateral/|k|), WheelSpeedCap(k), MaxYawRate/|k|)</code>
    /// and a friction ellipse (a_lat/MaxLateral)^2 + (a_long/(MaxAccel | MaxBrake))^2 &lt;= 1 at both ends of every
    /// segment. Forward (acceleration) and backward (braking) passes as in a quasi-steady-state lap simulator; the flying
    /// lap runs each pass twice round the loop so it is periodic. No drag, power or slip: the robot cannot beat this
    /// under these limits, but the limits themselves are not calibrated drivetrain data.
    /// </summary>
    public static class LapSim
    {
        const double Tol = 1e-6;

        public static double Cap(double kappa, RobotLimits r, double ceiling)
        {
            double k = Math.Abs(kappa), v = Math.Min(ceiling, r.MaxSpeed);
            v = Math.Min(v, r.WheelSpeedCap(k));
            if (k > 1e-9) v = Math.Min(v, Math.Min(Math.Sqrt(r.MaxLateral / k), r.MaxYawRate / k));
            return v;
        }

        public static LapResult Alloc(int n) => new LapResult
        {
            N = n, Pts = new V2[n], Kappa = new double[n], Ds = new double[n], VMax = new double[n], V = new double[n],
            ALong = new double[n], ALat = new double[n], YawRate = new double[n], WheelOuter = new double[n], Usage = new double[n],
            T = new double[n], Braking = new bool[n],
        };

        /// <summary>Lap time only (the GA / descent hot path); reuses <paramref name="scratch"/>.</summary>
        public static double LapTime(V2[] pts, RobotLimits r, double ceiling, LapResult scratch) => Simulate(pts, r, ceiling, scratch, false).LapTime;

        public static LapResult Simulate(V2[] pts, RobotLimits r, double ceiling, LapResult res = null, bool channels = true, bool standing = false)
        {
            int n = pts.Length;
            if (res == null || res.N != n) res = Alloc(n);
            res.Standing = standing; res.Ceiling = ceiling;
            if (channels) Array.Copy(pts, res.Pts, n);
            for (int i = 0; i < n; i++)
            {
                // +-2 stencil: exact on circles, and centimetre wiggles of a clamped line do not read as tight corners.
                V2 a = pts[i < 2 ? i - 2 + n : i - 2], b = pts[i], c = pts[i + 2 >= n ? i + 2 - n : i + 2], d = pts[i + 1 == n ? 0 : i + 1];
                double k = Corridor.Curvature(a, b, c);
                res.Kappa[i] = k;
                res.Ds[i] = Math.Max(1e-3, V2.Distance(b, d));
                res.VMax[i] = Cap(k, r, ceiling);
            }
            if (standing)
            {
                // Open lap 0..n (point n = point 0 again, reached at speed): v(0) = 0, end unconstrained.
                var k = new double[n + 1]; var ds = new double[n + 1]; var vmax = new double[n + 1]; var fw = new double[n + 1]; var v = new double[n + 1];
                for (int i = 0; i <= n; i++) { k[i] = res.Kappa[i % n]; ds[i] = res.Ds[i % n]; vmax[i] = res.VMax[i % n]; }
                vmax[0] = 0;
                Open(n + 1, k, ds, vmax, fw, v, r);
                Array.Copy(v, res.V, n); res.EndV = v[n];
                res.LapTime = Time(v, ds, n, false);
            }
            else
            {
                Closed(n, res.Kappa, res.Ds, res.VMax, res.ALong, res.V, r);
                res.LapTime = Time(res.V, res.Ds, n, true);
            }
            if (channels) Channels(res, r);
            return res;
        }

        static double Time(double[] v, double[] ds, int n, bool closed)
        {
            double t = 0;
            for (int i = 0; i < n; i++) t += 2 * ds[i] / Math.Max(1e-9, v[i] + v[closed ? (i + 1) % n : i + 1]);
            return t;
        }

        static double Forward(double v, double k0, double k1, double ds, double vmax1, RobotLimits r)
        {
            double vv = v * v, lat = k0 * vv / r.MaxLateral, bud = 1 - lat * lat;
            double aT = (bud > 0 ? Math.Sqrt(bud) : 0) * r.MaxAccel;
            double v1 = Math.Min(vmax1, Math.Sqrt(vv + 2 * aT * ds));
            if (v1 > v && !Feasible(v, v1, k0, k1, ds, r)) v1 = Bisect(v, v1, k0, k1, ds, r, true);
            return v1;
        }
        static double Backward(double v, double k0, double k1, double ds, double vmax0, RobotLimits r)
        {
            double vv = v * v, lat = k1 * vv / r.MaxLateral, bud = 1 - lat * lat;
            double aB = (bud > 0 ? Math.Sqrt(bud) : 0) * r.MaxBrake;
            double v0 = Math.Min(vmax0, Math.Sqrt(vv + 2 * aB * ds));
            if (v0 > v && !Feasible(v0, v, k0, k1, ds, r)) v0 = Bisect(v, v0, k0, k1, ds, r, false);
            return v0;
        }
        /// <summary>Largest feasible free end speed in [fixed, hi] (accel: free = end; brake: free = start).</summary>
        static double Bisect(double fix, double hi, double k0, double k1, double ds, RobotLimits r, bool accel)
        {
            double lo = fix;
            for (int it = 0; it < 40; it++)
            {
                double mid = .5 * (lo + hi);
                if (accel ? Feasible(fix, mid, k0, k1, ds, r) : Feasible(mid, fix, k0, k1, ds, r)) lo = mid; else hi = mid;
            }
            return lo;
        }

        static void Closed(int n, double[] k, double[] ds, double[] vmax, double[] fw, double[] V, RobotLimits r)
        {
            int i0 = 0;
            for (int i = 1; i < n; i++) if (vmax[i] < vmax[i0]) i0 = i;
            double v = vmax[i0]; fw[i0] = v; int prev = i0;
            for (int step = 1; step <= 2 * n; step++)
            {
                int i = prev + 1 == n ? 0 : prev + 1;
                v = Forward(v, k[prev], k[i], ds[prev], vmax[i], r);
                fw[i] = step > n ? Math.Min(fw[i], v) : v; prev = i;
            }
            v = vmax[i0]; V[i0] = Math.Min(fw[i0], v); int next = i0;
            for (int step = 1; step <= 2 * n; step++)
            {
                int i = next == 0 ? n - 1 : next - 1;
                v = Backward(v, k[i], k[next], ds[i], vmax[i], r);
                V[i] = step > n ? Math.Min(V[i], v) : v; next = i;
            }
            for (int i = 0; i < n; i++) V[i] = Math.Min(V[i], fw[i]);
        }

        static void Open(int m, double[] k, double[] ds, double[] vmax, double[] fw, double[] V, RobotLimits r)
        {
            fw[0] = vmax[0];
            for (int i = 1; i < m; i++) fw[i] = Forward(fw[i - 1], k[i - 1], k[i], ds[i - 1], vmax[i], r);
            V[m - 1] = fw[m - 1];
            for (int i = m - 2; i >= 0; i--) V[i] = Math.Min(fw[i], Backward(V[i + 1], k[i], k[i + 1], ds[i], vmax[i], r));
        }

        /// <summary>Friction-ellipse usage of a segment v0 -&gt; v1 at its start or end (&lt;= 1 is feasible).</summary>
        public static double Usage(double v0, double v1, double k0, double k1, double ds, RobotLimits r, bool atStart)
        {
            double a = (v1 * v1 - v0 * v0) / (2 * ds), v = atStart ? v0 : v1, k = atStart ? k0 : k1;
            double lat = k * v * v / r.MaxLateral, lon = a >= 0 ? a / r.MaxAccel : -a / r.MaxBrake;
            return lat * lat + lon * lon;
        }
        static bool Feasible(double v0, double v1, double k0, double k1, double ds, RobotLimits r)
            => Usage(v0, v1, k0, k1, ds, r, true) <= 1 + Tol && Usage(v0, v1, k0, k1, ds, r, false) <= 1 + Tol;

        static void Channels(LapResult res, RobotLimits r)
        {
            int n = res.N; double t = 0, len = 0;
            res.MinSpeed = double.MaxValue; res.MaxSpeed = 0; res.MaxKappa = 0; res.MeanSqKappa = 0; res.MaxUsage = 0; res.BrakeZones = 0;
            for (int i = 0; i < n; i++)
            {
                int nx = (i + 1) % n;
                double v0 = res.V[i], v1 = res.Standing && nx == 0 ? res.EndV : res.V[nx], k = res.Kappa[i], ds = res.Ds[i];
                res.T[i] = t; t += 2 * ds / Math.Max(1e-9, v0 + v1); len += ds;
                res.ALong[i] = (v1 * v1 - v0 * v0) / (2 * ds);
                res.ALat[i] = k * v0 * v0; res.YawRate[i] = Math.Abs(k) * v0; res.WheelOuter[i] = v0 * (1 + Math.Abs(k) * r.TrackWidth / 2);
                res.Usage[i] = Math.Max(Usage(v0, v1, k, res.Kappa[nx], ds, r, true), Usage(v0, v1, k, res.Kappa[nx], ds, r, false));
                res.Braking[i] = res.ALong[i] < -.05;
                res.MinSpeed = Math.Min(res.MinSpeed, v0); res.MaxSpeed = Math.Max(res.MaxSpeed, v0);
                res.MaxKappa = Math.Max(res.MaxKappa, Math.Abs(k)); res.MeanSqKappa += k * k * ds; res.MaxUsage = Math.Max(res.MaxUsage, res.Usage[i]);
            }
            for (int i = 0; i < n; i++) if (res.Braking[i] && !res.Braking[(i - 1 + n) % n]) res.BrakeZones++;
            res.Length = len; res.MeanSqKappa /= Math.Max(1e-9, len);
        }
    }
}
