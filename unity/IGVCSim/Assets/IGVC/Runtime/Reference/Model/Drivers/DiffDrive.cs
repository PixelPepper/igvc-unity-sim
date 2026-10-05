using System;
using System.Collections.Generic;

namespace IGVC.Reference.Drivers
{
    /// <summary>Copyable robot state at the driven axle (rollouts copy it). Wheel speeds are the actual, rate-limited ones.</summary>
    public struct RobotState
    {
        public V2 Pos;
        public double Heading, V, Omega, WheelL, WheelR;
        /// <summary>Corridor station hint for windowed projection.</summary>
        public int Hint;
        public V2 Forward => V2.FromAngle(Heading);
    }

    /// <summary>
    /// Differential drive (unicycle at the axle). Commands (v, omega) are saturated like a velocity smoother would:
    /// reverse limit, yaw-rate limit, lateral limit |v omega| &lt;= MaxLateral, then both wheel targets scaled so neither
    /// exceeds the wheel ceiling (curvature kept). Each wheel then moves towards its target at MaxAccel (speeding up)
    /// or MaxBrake (slowing down). Casters, slip and motor dynamics are not modelled.
    /// </summary>
    public static class DiffDrive
    {
        public static void Targets(RobotLimits r, double v, double w, out double vl, out double vr)
        {
            v = Math.Max(-r.MaxReverse, Math.Min(r.MaxSpeed, v));
            w = Math.Max(-r.MaxYawRate, Math.Min(r.MaxYawRate, w));
            if (Math.Abs(v) > 1e-6) { double wl = r.MaxLateral / Math.Abs(v); w = Math.Max(-wl, Math.Min(wl, w)); }
            double half = r.TrackWidth / 2;
            vl = v - w * half; vr = v + w * half;
            double s = Math.Max(1, Math.Max(Math.Abs(vl), Math.Abs(vr)) / r.MaxSpeed);
            vl /= s; vr /= s;
        }

        public static void Step(ref RobotState s, double vCmd, double wCmd, double dt, RobotLimits r)
        {
            Targets(r, vCmd, wCmd, out double tl, out double tr);
            s.WheelL = Wheel(s.WheelL, tl, dt, r); s.WheelR = Wheel(s.WheelR, tr, dt, r);
            double v = .5 * (s.WheelL + s.WheelR), w = (s.WheelR - s.WheelL) / r.TrackWidth;
            if (Math.Abs(w) < 1e-9) s.Pos += V2.FromAngle(s.Heading) * (v * dt);
            else
            {
                double h1 = s.Heading + w * dt, rad = v / w;
                s.Pos += new V2(Math.Sin(h1) - Math.Sin(s.Heading), Math.Cos(s.Heading) - Math.Cos(h1)) * rad;
            }
            s.Heading = Wrap(s.Heading + w * dt); s.V = v; s.Omega = w;
        }
        private static double Wheel(double cur, double target, double dt, RobotLimits r)
        {
            bool speedingUp = Math.Abs(target) > Math.Abs(cur) && target * cur >= 0;
            double lim = (speedingUp ? r.MaxAccel : r.MaxBrake) * dt, d = target - cur;
            return cur + Math.Max(-lim, Math.Min(lim, d));
        }
        public static double Wrap(double a)
        {
            while (a > Math.PI) a -= 2 * Math.PI;
            while (a < -Math.PI) a += 2 * Math.PI;
            return a;
        }
    }

    /// <summary>The reference line as a closed polyline with arc length, heading, curvature and a speed plan.</summary>
    public sealed class RefPath
    {
        public readonly int N;
        public readonly V2[] P;
        public readonly double[] S, Kappa, Speed;
        public readonly double Length;

        public RefPath(V2[] pts, double[] kappa, double[] speed)
        {
            N = pts.Length; P = (V2[])pts.Clone(); Kappa = (double[])kappa.Clone(); Speed = (double[])speed.Clone(); S = new double[N];
            for (int i = 1; i < N; i++) S[i] = S[i - 1] + V2.Distance(P[i - 1], P[i]);
            Length = S[N - 1] + V2.Distance(P[N - 1], P[0]);
        }
        public int Wrap(int i) => ((i % N) + N) % N;
        public double WrapS(double s) { s %= Length; return s < 0 ? s + Length : s; }
        private double SegLen(int i) => i == N - 1 ? Length - S[i] : S[i + 1] - S[i];
        private int lastSeg; // search start only; results do not depend on it
        private int Seg(double s, out double t)
        {
            s = WrapS(s);
            int lo = -1;
            for (int k = 0; k < 4 && lo < 0; k++) { int i = Wrap(lastSeg + k - 1); if (S[i] <= s && (i == N - 1 || S[i + 1] > s)) lo = i; }
            if (lo < 0)
            {
                lo = 0; int hi = N - 1;
                while (lo < hi) { int mid = (lo + hi + 1) / 2; if (S[mid] <= s) lo = mid; else hi = mid - 1; }
            }
            lastSeg = lo;
            double len = SegLen(lo); t = len > 1e-12 ? (s - S[lo]) / len : 0; return lo;
        }
        public V2 PointAt(double s) { int i = Seg(s, out double t); return V2.Lerp(P[i], P[Wrap(i + 1)], t); }
        public double HeadingAt(double s) { int i = Seg(s, out _); return (P[Wrap(i + 1)] - P[i]).Angle; }
        public double KappaAt(double s) { int i = Seg(s, out double t); return Kappa[i] + (Kappa[Wrap(i + 1)] - Kappa[i]) * t; }
        public double SpeedAt(double s) { int i = Seg(s, out double t); return Speed[i] + (Speed[Wrap(i + 1)] - Speed[i]) * t; }

        /// <summary>Closest segment (windowed around hint when hint &gt;= 0). e = signed lateral offset, left positive.</summary>
        public int Project(V2 p, int hint, out double s, out double e, int window = 12)
        {
            int from = hint < 0 ? 0 : hint - window, to = hint < 0 ? N - 1 : hint + window, best = 0;
            double bestD2 = double.PositiveInfinity, bestT = 0;
            for (int j = from; j <= to; j++)
            {
                int i = Wrap(j); V2 a = P[i], ab = P[Wrap(i + 1)] - a; double l2 = ab.SqrLength;
                double t = l2 > 1e-18 ? Math.Max(0, Math.Min(1, V2.Dot(p - a, ab) / l2)) : 0;
                double d2 = (a + ab * t - p).SqrLength;
                if (d2 < bestD2) { bestD2 = d2; best = i; bestT = t; }
            }
            V2 sa = P[best], sb = P[Wrap(best + 1)];
            s = WrapS(S[best] + bestT * SegLen(best)); e = Math.Sign(V2.Cross(sb - sa, p - sa)) * Math.Sqrt(bestD2);
            return best;
        }
    }

    /// <summary>
    /// Static scene for the drivers: corridor + capsule obstacles with per-station near lists (so footprint and
    /// clearance queries touch a handful of obstacles), and a sampled signed road field for sphere-traced range sensors.
    /// </summary>
    public sealed class DriveWorld
    {
        public const double Cell = .2;
        public readonly Corridor Corridor;
        public readonly Capsule[] Shapes;
        public readonly RobotLimits Limits;
        public readonly Capsule[][] Near;
        /// <summary>Obstacles within range-sensor reach of each station.</summary>
        public readonly Capsule[][] Far;
        public readonly double X0, Y0, Reach;
        public readonly int Nx, Ny;
        private readonly float[] field;

        public DriveWorld(Corridor corridor, Capsule[] shapes, RobotLimits limits)
        {
            Corridor = corridor; Shapes = shapes ?? new Capsule[0]; Limits = limits;
            Near = new Capsule[corridor.N][]; Far = new Capsule[corridor.N][];
            var list = new List<Capsule>();
            for (int i = 0; i < corridor.N; i++)
            {
                list.Clear();
                // Any body point is within the circumscribed radius of the axle; the axle within the half width (+ slack) of P[i].
                double reach = corridor.HalfWidth[i] + limits.CircumscribedRadius + corridor.Ds + .5;
                foreach (var c in Shapes) if (c.Distance(corridor.P[i]) <= reach) list.Add(c);
                Near[i] = list.ToArray(); list.Clear();
                foreach (var c in Shapes) if (c.Distance(corridor.P[i]) <= corridor.HalfWidth[i] + NeuralDriver.SensorRange + corridor.Ds) list.Add(c);
                Far[i] = list.ToArray();
            }

            double maxW = 0, minX = double.MaxValue, minY = double.MaxValue, maxX = double.MinValue, maxY = double.MinValue;
            for (int i = 0; i < corridor.N; i++)
            {
                maxW = Math.Max(maxW, corridor.HalfWidth[i]); var p = corridor.P[i];
                minX = Math.Min(minX, p.X); maxX = Math.Max(maxX, p.X); minY = Math.Min(minY, p.Y); maxY = Math.Max(maxY, p.Y);
            }
            Reach = maxW + 2;
            X0 = minX - Reach; Y0 = minY - Reach;
            Nx = (int)Math.Ceiling((maxX + Reach - X0) / Cell) + 1; Ny = (int)Math.Ceiling((maxY + Reach - Y0) / Cell) + 1;
            field = new float[Nx * Ny];
            var d2 = new double[Nx * Ny]; var w = new double[Nx * Ny];
            for (int k = 0; k < d2.Length; k++) d2[k] = double.MaxValue;
            for (int i = 0; i < corridor.N; i++)
            {
                int j = corridor.Wrap(i + 1); V2 a = corridor.P[i], b = corridor.P[j], ab = b - a; double l2 = Math.Max(1e-12, ab.SqrLength);
                int x0 = Math.Max(0, (int)Math.Floor((Math.Min(a.X, b.X) - Reach - X0) / Cell)), x1 = Math.Min(Nx - 1, (int)Math.Ceiling((Math.Max(a.X, b.X) + Reach - X0) / Cell));
                int y0 = Math.Max(0, (int)Math.Floor((Math.Min(a.Y, b.Y) - Reach - Y0) / Cell)), y1 = Math.Min(Ny - 1, (int)Math.Ceiling((Math.Max(a.Y, b.Y) + Reach - Y0) / Cell));
                for (int y = y0; y <= y1; y++)
                    for (int x = x0; x <= x1; x++)
                    {
                        var p = new V2(X0 + x * Cell, Y0 + y * Cell);
                        double t = Math.Max(0, Math.Min(1, V2.Dot(p - a, ab) / l2)), dd = (a + ab * t - p).SqrLength;
                        int idx = y * Nx + x;
                        if (dd < d2[idx]) { d2[idx] = dd; w[idx] = corridor.HalfWidth[i] + (corridor.HalfWidth[j] - corridor.HalfWidth[i]) * t; }
                    }
            }
            for (int k = 0; k < field.Length; k++) field[k] = d2[k] == double.MaxValue ? (float)-Reach : (float)(w[k] - Math.Sqrt(d2[k]));
        }

        /// <summary>Bilinear signed road field (m, positive inside the lane).</summary>
        public double Road(V2 p)
        {
            double fx = (p.X - X0) / Cell, fy = (p.Y - Y0) / Cell;
            if (fx < 0 || fy < 0 || fx >= Nx - 1 || fy >= Ny - 1) return -Reach;
            int x = (int)fx, y = (int)fy; double tx = fx - x, ty = fy - y; int i = y * Nx + x;
            double a = field[i] + (field[i + 1] - field[i]) * tx, b = field[i + Nx] + (field[i + Nx + 1] - field[i + Nx]) * tx;
            return a + (b - a) * ty;
        }

        /// <summary>Distance along unit dir to the first lane edge or obstacle (sphere tracing the min of both fields).</summary>
        public double Raycast(V2 p, V2 dir, double maxDist, IList<Capsule> near)
        {
            double Sdf(V2 q)
            {
                double v = Road(q);
                for (int k = 0; k < near.Count; k++) v = Math.Min(v, Capsule.SegmentDistance(q, near[k].A, near[k].B) - near[k].R);
                return v;
            }
            if (Sdf(p) <= 0) return 0;
            double s = 0, prev = 0;
            for (int it = 0; it < 64 && s < maxDist; it++)
            {
                double v = Sdf(p + dir * s);
                if (v <= 0)
                {
                    double lo = prev, hi = s;
                    for (int b = 0; b < 8; b++) { double mid = .5 * (lo + hi); if (Sdf(p + dir * mid) > 0) lo = mid; else hi = mid; }
                    return .5 * (lo + hi);
                }
                prev = s; s += Math.Max(v * .9, .03);
            }
            return maxDist;
        }

        public int Station(V2 p, int hint, int window = 6) => Corridor.Project(p, out _, out _, hint, window);

        /// <summary>
        /// Authoritative whole-body contact: Corridor.FootprintContact (near obstacles), called only when the cheaper
        /// perimeter clearance (same samples, plus obstacles under the body) is within ContactGate of touching.
        /// </summary>
        public string Contact(V2 axle, double yaw, ref int hint, out double clearance)
        {
            clearance = Clearance(axle, yaw, ref hint);
            if (clearance > ContactGate) return null;
            int h = hint;
            return Corridor.FootprintContact(axle, yaw, Limits, Near[hint], ref h);
        }
        public string Contact(V2 axle, double yaw, ref int hint) => Contact(axle, yaw, ref hint, out _);
        public const double ContactGate = .05;

        /// <summary>
        /// Smallest distance (m) from the padded body perimeter (0.1 m samples) to a lane edge or obstacle; negative =
        /// outside the lane, 0 = an obstacle lies under the body.
        /// </summary>
        public double Clearance(V2 axle, double yaw, ref int hint)
        {
            hint = Station(axle, hint);
            var near = Near[hint]; V2 f = V2.FromAngle(yaw), l = f.Perp;
            double front = Limits.Front + Limits.Padding, rear = Limits.Rear + Limits.Padding, half = Limits.HalfWidth + Limits.Padding;
            int along = (int)Math.Ceiling((front + rear) / .1), across = (int)Math.Ceiling(2 * half / .1);
            double best = double.MaxValue;
            for (int k = 0; k < 2 * (along + across); k++)
            {
                double x, y;
                if (k < along) { x = -rear + (front + rear) * k / along; y = half; }
                else if (k < 2 * along) { x = -rear + (front + rear) * (k - along) / along; y = -half; }
                else if (k < 2 * along + across) { x = front; y = -half + 2 * half * (k - 2 * along) / across; }
                else { x = -rear; y = -half + 2 * half * (k - 2 * along - across) / across; }
                V2 p = axle + f * x + l * y;
                Corridor.Project(p, out double s, out double d, hint, 5);
                best = Math.Min(best, Corridor.HalfWidthAt(s) - Math.Abs(d));
                foreach (var c in near) best = Math.Min(best, c.Distance(p));
            }
            foreach (var c in near)
            {
                V2 q = c.A - axle; double x = V2.Dot(q, f), y = V2.Dot(q, l);
                if (x > -rear && x < front && Math.Abs(y) < half) return Math.Min(best, 0);
            }
            return best;
        }

        /// <summary>
        /// Cheap clearance for rollouts: rectangle corners against the lane edges (lateral offsets in the frame of the
        /// axle's station, accurate on radii of a few metres) and exact rectangle distance to the near obstacles.
        /// </summary>
        public double QuickClearance(V2 axle, double yaw, int station)
        {
            var c = Corridor; V2 f = V2.FromAngle(yaw), l = f.Perp; double best = double.MaxValue;
            V2 p0 = c.P[station], t = c.T[station], n = c.Nl[station];
            double front = Limits.Front + Limits.Padding, rear = Limits.Rear + Limits.Padding, half = Limits.HalfWidth + Limits.Padding;
            for (int k = 0; k < 4; k++)
            {
                V2 q = axle + f * (k < 2 ? front : -rear) + l * ((k & 1) == 0 ? half : -half), w = q - p0;
                best = Math.Min(best, c.HalfWidthAt(c.S[station] + V2.Dot(w, t)) - Math.Abs(V2.Dot(w, n)));
            }
            double cx = (front - rear) / 2, hx = (front + rear) / 2;
            foreach (var o in Near[station])
            {
                // Exact point-to-rectangle distance in the body frame, sampled every 0.25 m along long (barricade) capsules.
                int m = (int)Math.Ceiling(V2.Distance(o.A, o.B) / .25);
                for (int j = 0; j <= m; j++)
                {
                    V2 q = (m == 0 ? o.A : V2.Lerp(o.A, o.B, (double)j / m)) - axle;
                    double dx = Math.Max(0, Math.Abs(V2.Dot(q, f) - cx) - hx), dy = Math.Max(0, Math.Abs(V2.Dot(q, l)) - half);
                    best = Math.Min(best, Math.Sqrt(dx * dx + dy * dy) - o.R);
                }
            }
            return best;
        }
    }
}
