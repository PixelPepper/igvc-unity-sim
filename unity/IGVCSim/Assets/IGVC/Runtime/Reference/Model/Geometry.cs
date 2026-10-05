using System;
using System.Collections.Generic;

// Reference Lab shared model. Plain C# (no UnityEngine) so Unity and the dotnet
// harness in tools/reference_lab compile the same source. It reads WORLD course
// geometry and is therefore audit/visualisation-only: nothing here may reach ROS
// or the sensor-led mission (see docs/REFERENCE_LAB.md).
namespace IGVC.Reference
{
    public struct V2
    {
        public double X, Y;
        public V2(double x, double y) { X = x; Y = y; }
        public static V2 operator +(V2 a, V2 b) => new V2(a.X + b.X, a.Y + b.Y);
        public static V2 operator -(V2 a, V2 b) => new V2(a.X - b.X, a.Y - b.Y);
        public static V2 operator -(V2 a) => new V2(-a.X, -a.Y);
        public static V2 operator *(V2 a, double k) => new V2(a.X * k, a.Y * k);
        public static V2 operator *(double k, V2 a) => new V2(a.X * k, a.Y * k);
        public static V2 operator /(V2 a, double k) => new V2(a.X / k, a.Y / k);
        public double Length => Math.Sqrt(X * X + Y * Y);
        public double SqrLength => X * X + Y * Y;
        public V2 Normalized { get { double l = Length; return l > 1e-12 ? new V2(X / l, Y / l) : new V2(0, 0); } }
        /// <summary>Left-hand normal (counter-clockwise quarter turn).</summary>
        public V2 Perp => new V2(-Y, X);
        public static double Dot(V2 a, V2 b) => a.X * b.X + a.Y * b.Y;
        public static double Cross(V2 a, V2 b) => a.X * b.Y - a.Y * b.X;
        public static double Distance(V2 a, V2 b) => (a - b).Length;
        public static V2 Lerp(V2 a, V2 b, double t) => new V2(a.X + (b.X - a.X) * t, a.Y + (b.Y - a.Y) * t);
        public static V2 FromAngle(double a) => new V2(Math.Cos(a), Math.Sin(a));
        public double Angle => Math.Atan2(Y, X);
        public override string ToString() => "(" + X.ToString("0.###") + ", " + Y.ToString("0.###") + ")";
    }

    /// <summary>Segment swept by a disc. Every course obstacle is bounded by one (conservatively).</summary>
    public struct Capsule
    {
        public V2 A, B;
        public double R;
        public Capsule(V2 a, V2 b, double r) { A = a; B = b; R = r; }
        public double Distance(V2 p) => Math.Max(0, SegmentDistance(p, A, B) - R);
        public static double SegmentDistance(V2 p, V2 a, V2 b)
        {
            V2 ab = b - a; double l2 = ab.SqrLength;
            double t = l2 > 1e-18 ? Math.Max(0, Math.Min(1, V2.Dot(p - a, ab) / l2)) : 0;
            return (a + ab * t - p).Length;
        }
        /// <summary>Interval of d where P + N*d (|N| = 1) lies within this capsule grown by <paramref name="grow"/>.</summary>
        public bool LineInterval(V2 p, V2 n, double grow, out double lo, out double hi)
        {
            double r = R + grow; lo = double.PositiveInfinity; hi = double.NegativeInfinity;
            Disc(p, n, A, r, ref lo, ref hi); Disc(p, n, B, r, ref lo, ref hi);
            V2 ab = B - A; double len = ab.Length;
            if (len > 1e-9)
            {
                // Liang-Barsky clip against the capsule's central rectangle.
                V2 e = ab / len, m = e.Perp, w = p - A;
                double t0 = double.NegativeInfinity, t1 = double.PositiveInfinity;
                if (Clip(V2.Dot(w, e), V2.Dot(n, e), 0, len, ref t0, ref t1) && Clip(V2.Dot(w, m), V2.Dot(n, m), -r, r, ref t0, ref t1) && t0 <= t1)
                { lo = Math.Min(lo, t0); hi = Math.Max(hi, t1); }
            }
            return lo <= hi;
        }
        private static void Disc(V2 p, V2 n, V2 c, double r, ref double lo, ref double hi)
        {
            V2 w = p - c; double b = V2.Dot(w, n), disc = b * b - (w.SqrLength - r * r);
            if (disc < 0) return;
            double q = Math.Sqrt(disc); lo = Math.Min(lo, -b - q); hi = Math.Max(hi, -b + q);
        }
        private static bool Clip(double offset, double slope, double min, double max, ref double t0, ref double t1)
        {
            if (Math.Abs(slope) < 1e-12) return offset >= min && offset <= max;
            double a = (min - offset) / slope, b = (max - offset) / slope;
            if (a > b) { double t = a; a = b; b = t; }
            t0 = Math.Max(t0, a); t1 = Math.Min(t1, b); return t0 <= t1;
        }
    }

    public sealed class CourseObstacle
    {
        public string Id, Kind;
        public double X, Y, Yaw, Length, Width;
        public V2 Center => new V2(X, Y);
        /// <summary>
        /// Conservative bound in the course frame. Barrels/potholes: disc of the larger diameter.
        /// Barricades: Unity places length along (cos yaw, sin yaw) (CourseVariant); corner radius w/sqrt(2) covers the box.
        /// </summary>
        public Capsule Shape
        {
            get
            {
                if (Kind != "barricade") return new Capsule(Center, Center, Math.Max(Length, Width) / 2);
                V2 axis = V2.FromAngle(Yaw) * Math.Max(0, Length / 2 - Width / 2);
                return new Capsule(Center - axis, Center + axis, Width / Math.Sqrt(2));
            }
        }
    }

    public sealed class RampInfo { public double X, Y, Yaw, Width, RiseLength, DeckLength, Height; }

    /// <summary>Closed course loop in the odom frame (x forward at spawn, y left), metres.</summary>
    public sealed class CourseGeometry
    {
        public V2[] Center;          // closed loop, duplicate end point removed
        public double[] HalfWidth;   // resolved (manifest 0 = lane_width / 2)
        public bool[] Painted;
        public double LaneWidth;
        public CourseObstacle[] Obstacles = new CourseObstacle[0];
        public RampInfo Ramp;
        public int Seed;
        public string Identity = "";

        public static CourseGeometry Create(IList<V2> center, IList<double> halfWidth, IList<bool> painted, double laneWidth, IList<CourseObstacle> obstacles, RampInfo ramp, int seed, string identity)
        {
            if (center == null || center.Count < 4 || halfWidth.Count != center.Count || painted.Count != center.Count) throw new ArgumentException("Course centerline arrays are invalid");
            int n = center.Count;
            if (V2.Distance(center[0], center[n - 1]) < 1e-6) n--;
            var g = new CourseGeometry { Center = new V2[n], HalfWidth = new double[n], Painted = new bool[n], LaneWidth = laneWidth, Ramp = ramp, Seed = seed, Identity = identity ?? "" };
            for (int i = 0; i < n; i++) { g.Center[i] = center[i]; g.HalfWidth[i] = halfWidth[i] > 0 ? halfWidth[i] : laneWidth / 2; g.Painted[i] = painted[i]; }
            g.Obstacles = obstacles == null ? new CourseObstacle[0] : new List<CourseObstacle>(obstacles).ToArray();
            return g;
        }
        public Capsule[] Shapes() { var s = new Capsule[Obstacles.Length]; for (int i = 0; i < s.Length; i++) s[i] = Obstacles[i].Shape; return s; }
    }

    /// <summary>
    /// R3-a limits for reference studies. Footprint and wheel track are the project's canonical values
    /// (CLAUDE_HANDOFF, R3aKinematics); acceleration and lateral limits are ASSUMPTIONS for comparison, not
    /// calibrated drivetrain data. Speed cap 2.2 m/s is the project ceiling under the 5 mph rule.
    /// </summary>
    public sealed class RobotLimits
    {
        public double Front = 0.6, Rear = 1.1, HalfWidth = 0.5, Padding = 0.02;
        public double TrackWidth = 0.81051;
        public double MaxSpeed = 2.2, MaxReverse = 0.3;
        public double MaxAccel = 0.8, MaxBrake = 1.2, MaxLateral = 1.0, MaxYawRate = 2.0;
        public double InscribedRadius => HalfWidth + Padding;
        public double CircumscribedRadius => Math.Sqrt(Math.Max(Front, Rear) * Math.Max(Front, Rear) + HalfWidth * HalfWidth) + Padding;
        /// <summary>Differential drive: outer wheel speed v(1 + |k| b/2) must stay within the wheel ceiling.</summary>
        public double WheelSpeedCap(double kappa) => MaxSpeed / (1 + Math.Abs(kappa) * TrackWidth / 2);
        public RobotLimits Clone() => (RobotLimits)MemberwiseClone();
    }

    public struct Interval { public double Lo, Hi; public Interval(double lo, double hi) { Lo = lo; Hi = hi; } public double Width => Hi - Lo; }

    /// <summary>The loop resampled into evenly spaced stations with tangents, left normals, curvature and width.</summary>
    public sealed class Corridor
    {
        public readonly int N;
        public readonly double Length, Ds;
        public readonly V2[] P, T, Nl;
        public readonly double[] S, HalfWidth, Kappa;
        public readonly bool[] Painted;
        public readonly CourseGeometry Course;

        public Corridor(CourseGeometry g, double spacing = 0.5)
        {
            Course = g; int m = g.Center.Length;
            var cum = new double[m + 1];
            for (int i = 0; i < m; i++) cum[i + 1] = cum[i] + V2.Distance(g.Center[i], g.Center[(i + 1) % m]);
            Length = cum[m];
            N = Math.Max(40, (int)Math.Round(Length / spacing)); Ds = Length / N;
            P = new V2[N]; T = new V2[N]; Nl = new V2[N]; S = new double[N]; HalfWidth = new double[N]; Kappa = new double[N]; Painted = new bool[N];
            int seg = 0;
            for (int k = 0; k < N; k++)
            {
                double s = k * Ds; while (seg < m - 1 && cum[seg + 1] < s) seg++;
                int b = (seg + 1) % m; double len = cum[seg + 1] - cum[seg], t = len > 1e-12 ? (s - cum[seg]) / len : 0;
                S[k] = s; P[k] = V2.Lerp(g.Center[seg], g.Center[b], t);
                HalfWidth[k] = g.HalfWidth[seg] + (g.HalfWidth[b] - g.HalfWidth[seg]) * t;
                Painted[k] = g.Painted[seg] && g.Painted[b];
            }
            for (int k = 0; k < N; k++)
            {
                V2 a = P[Wrap(k - 1)], c = P[Wrap(k + 1)];
                T[k] = (c - a).Normalized; Nl[k] = T[k].Perp; Kappa[k] = Curvature(a, P[k], c);
            }
        }
        public int Wrap(int i) => ((i % N) + N) % N;
        public double WrapS(double s) { s %= Length; return s < 0 ? s + Length : s; }
        /// <summary>Signed Menger curvature (positive = turning left).</summary>
        public static double Curvature(V2 a, V2 b, V2 c)
        {
            double ab = V2.Distance(a, b), bc = V2.Distance(b, c), ca = V2.Distance(c, a), d = ab * bc * ca;
            return d < 1e-12 ? 0 : 2 * V2.Cross(b - a, c - b) / d;
        }
        public V2 PointAt(double s) { s = WrapS(s); int i = (int)(s / Ds) % N; return V2.Lerp(P[i], P[Wrap(i + 1)], (s - S[i]) / Ds); }
        public double HalfWidthAt(double s) { s = WrapS(s); int i = (int)(s / Ds) % N; double t = (s - S[i]) / Ds; return HalfWidth[i] + (HalfWidth[Wrap(i + 1)] - HalfWidth[i]) * t; }
        public double HeadingAt(double s) { s = WrapS(s); int i = (int)(s / Ds) % N; return (P[Wrap(i + 1)] - P[i]).Angle; }

        /// <summary>
        /// Closest centre segment [i, i+1]. With hint &gt;= 0 only +-window segments are searched (tracking);
        /// otherwise all. s is arc length, d the signed lateral offset (left positive).
        /// </summary>
        public int Project(V2 p, out double s, out double d, int hint = -1, int window = 16)
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
            s = WrapS(S[best] + bestT * Ds); d = Math.Sign(V2.Cross(sb - sa, p - sa)) * Math.Sqrt(bestD2);
            return best;
        }
        /// <summary>Lateral margin to the corridor edge (negative = outside the painted/nominal lane).</summary>
        public double EdgeMargin(V2 p, ref int hint)
        {
            hint = Project(p, out double s, out double d, hint);
            return HalfWidthAt(s) - Math.Abs(d);
        }

        /// <summary>
        /// Free lateral intervals of station i for a disc of radius <paramref name="clearance"/>: the lane minus every
        /// obstacle grown by clearance. Sorted, disjoint. Empty when the station is blocked for that disc.
        /// </summary>
        public void FreeIntervals(int i, IList<Capsule> obstacles, double clearance, List<Interval> output)
        {
            output.Clear();
            double w = HalfWidth[i] - clearance; if (w <= 0) return;
            output.Add(new Interval(-w, w));
            foreach (var c in obstacles)
            {
                double reach = HalfWidth[i] + c.R + clearance + V2.Distance(c.A, c.B);
                if ((c.A - P[i]).SqrLength > reach * reach) continue;
                if (!c.LineInterval(P[i], Nl[i], clearance, out double lo, out double hi)) continue;
                for (int k = output.Count - 1; k >= 0; k--)
                {
                    var iv = output[k]; if (hi <= iv.Lo || lo >= iv.Hi) continue;
                    output.RemoveAt(k);
                    if (hi < iv.Hi) output.Insert(k, new Interval(hi, iv.Hi));
                    if (lo > iv.Lo) output.Insert(k, new Interval(iv.Lo, lo));
                }
            }
        }

        /// <summary>
        /// Per-station lateral bounds [lo, hi] for a line optimiser. Where obstacles split the lane, the interval that
        /// contains <paramref name="route"/> (e.g. a grid planner's path: it fixes which side of each obstacle to pass)
        /// is chosen; without a route, the interval closest to the centre. Returns the number of blocked stations
        /// (no interval at all); those get lo = hi = the route/centre offset and should be reported, not hidden.
        /// </summary>
        public int BoundsFromRoute(IList<V2> route, IList<Capsule> obstacles, double clearance, double[] lo, double[] hi, double[] routeOffset = null)
        {
            var target = new double[N];
            if (route != null && route.Count > 1) RouteOffsets(route, target);
            if (routeOffset != null) Array.Copy(target, routeOffset, N);
            var free = new List<Interval>(); int blocked = 0;
            for (int i = 0; i < N; i++)
            {
                FreeIntervals(i, obstacles, clearance, free);
                if (free.Count == 0) { lo[i] = hi[i] = target[i]; blocked++; continue; }
                int best = 0; double bestGap = double.PositiveInfinity;
                for (int k = 0; k < free.Count; k++)
                {
                    double gap = target[i] < free[k].Lo ? free[k].Lo - target[i] : target[i] > free[k].Hi ? target[i] - free[k].Hi : 0;
                    if (gap < bestGap) { bestGap = gap; best = k; }
                }
                lo[i] = free[best].Lo; hi[i] = free[best].Hi;
            }
            return blocked;
        }
        /// <summary>Lateral offset of a polyline route at every station (route assumed to run once around the loop).</summary>
        public void RouteOffsets(IList<V2> route, double[] offset)
        {
            var s = new List<double>(); var d = new List<double>(); int hint = -1;
            // Dense resampling keeps every station covered by a nearby route sample.
            for (int k = 0; k + 1 < route.Count; k++)
            {
                int steps = Math.Max(1, (int)Math.Ceiling(V2.Distance(route[k], route[k + 1]) / (Ds * .5)));
                for (int j = 0; j < steps; j++)
                {
                    hint = Project(V2.Lerp(route[k], route[k + 1], (double)j / steps), out double ss, out double dd, hint);
                    s.Add(ss); d.Add(dd);
                }
            }
            var sum = new double[N]; var weight = new double[N];
            for (int k = 0; k < s.Count; k++) { int i = (int)Math.Round(s[k] / Ds) % N; sum[i] += d[k]; weight[i] += 1; }
            for (int i = 0; i < N; i++)
            {
                if (weight[i] > 0) { offset[i] = sum[i] / weight[i]; continue; }
                int a = i, b = i; while (weight[Wrap(a)] == 0 && i - a < N) a--; while (weight[Wrap(b)] == 0 && b - i < N) b++;
                if (weight[Wrap(a)] == 0) { offset[i] = 0; continue; }
                double va = sum[Wrap(a)] / weight[Wrap(a)], vb = sum[Wrap(b)] / weight[Wrap(b)];
                offset[i] = va + (vb - va) * (i - a) / (double)(b - a);
            }
        }

        /// <summary>
        /// Whole-body check of the R3-a rectangle (axle frame, x forward) against the nominal lane and the obstacle bounds.
        /// Perimeter samples every 0.1 m; returns null when clear, otherwise a short reason.
        /// </summary>
        public string FootprintContact(V2 axle, double yaw, RobotLimits r, IList<Capsule> obstacles, ref int hint)
        {
            V2 f = V2.FromAngle(yaw), l = f.Perp;
            double front = r.Front + r.Padding, rear = r.Rear + r.Padding, half = r.HalfWidth + r.Padding;
            int along = (int)Math.Ceiling((front + rear) / .1), across = (int)Math.Ceiling(2 * half / .1);
            for (int k = 0; k < 2 * (along + across); k++)
            {
                double x, y;
                if (k < along) { x = -rear + (front + rear) * k / along; y = half; }
                else if (k < 2 * along) { x = -rear + (front + rear) * (k - along) / along; y = -half; }
                else if (k < 2 * along + across) { x = front; y = -half + 2 * half * (k - 2 * along) / across; }
                else { x = -rear; y = -half + 2 * half * (k - 2 * along - across) / across; }
                V2 p = axle + f * x + l * y;
                int h = hint; if (EdgeMargin(p, ref h) < 0) return "lane edge";
                if (k == 0) hint = h;
                foreach (var c in obstacles) if (c.Distance(p) <= 0) return "obstacle";
            }
            // Corner samples miss an obstacle lying wholly under the body; test centres against the rectangle.
            foreach (var c in obstacles)
            {
                V2 q = c.A - axle; double x = V2.Dot(q, f), y = V2.Dot(q, l);
                if (x > -rear && x < front && Math.Abs(y) < half) return "obstacle";
            }
            return null;
        }
    }

    /// <summary>Occupancy raster of the corridor for grid planners. Cell codes: 0 free, 1 outside lane, 2 obstacle, 3 start seam.</summary>
    public sealed class OccupancyGrid
    {
        public const byte Free = 0, Outside = 1, Obstacle = 2, Seam = 3;
        public readonly int W, H;
        public readonly double Cell, X0, Y0, Clearance;
        public readonly byte[] Code;
        public int StartCell = -1, GoalCell = -1;
        public OccupancyGrid(int w, int h, double cell, double x0, double y0, double clearance)
        { W = w; H = h; Cell = cell; X0 = x0; Y0 = y0; Clearance = clearance; Code = new byte[w * h]; }
        public int Index(int x, int y) => y * W + x;
        public bool InBounds(int x, int y) => (uint)x < (uint)W && (uint)y < (uint)H;
        public V2 CellCenter(int i) => new V2(X0 + (i % W + .5) * Cell, Y0 + (i / W + .5) * Cell);
        public int CellOf(V2 p)
        {
            int x = (int)Math.Floor((p.X - X0) / Cell), y = (int)Math.Floor((p.Y - Y0) / Cell);
            return InBounds(x, y) ? Index(x, y) : -1;
        }
        public bool IsFree(int i) => i >= 0 && Code[i] == Free;
        /// <summary>Nearest free cell within <paramref name="radius"/> cells (ring search), or -1.</summary>
        public int NearestFree(int i, int radius = 10)
        {
            if (i < 0) return -1; if (Code[i] == Free) return i;
            int cx = i % W, cy = i / W, best = -1; double bestD = double.PositiveInfinity;
            for (int dy = -radius; dy <= radius; dy++) for (int dx = -radius; dx <= radius; dx++)
            {
                int x = cx + dx, y = cy + dy; if (!InBounds(x, y) || Code[Index(x, y)] != Free) continue;
                double d = dx * dx + dy * dy; if (d < bestD) { bestD = d; best = Index(x, y); }
            }
            return best;
        }
    }

    public static class Rasterizer
    {
        /// <summary>
        /// Configuration-space raster for a disc robot of radius <paramref name="clearance"/> (default: the R3-a
        /// inscribed half-width + padding). That disc is optimistic for the 1.7 m-long body, so grid paths are a
        /// planning reference; whole-body feasibility is checked separately (Corridor.FootprintContact).
        /// With <paramref name="seam"/>, a one-cell wall across the lane at s = 0 turns the closed loop into a
        /// start (just ahead) to goal (just behind) problem, so the shortest path is one full lap.
        /// </summary>
        public static OccupancyGrid Rasterize(Corridor c, IList<Capsule> obstacles, double cell = .1, double clearance = .52, bool seam = true)
        {
            double minX = double.PositiveInfinity, minY = double.PositiveInfinity, maxX = double.NegativeInfinity, maxY = double.NegativeInfinity;
            for (int i = 0; i < c.N; i++)
            {
                double w = c.HalfWidth[i] + 1;
                minX = Math.Min(minX, c.P[i].X - w); maxX = Math.Max(maxX, c.P[i].X + w);
                minY = Math.Min(minY, c.P[i].Y - w); maxY = Math.Max(maxY, c.P[i].Y + w);
            }
            int width = (int)Math.Ceiling((maxX - minX) / cell), height = (int)Math.Ceiling((maxY - minY) / cell);
            if ((long)width * height > 8000000) throw new ArgumentException("Reference grid too large; use a coarser cell");
            var g = new OccupancyGrid(width, height, cell, minX, minY, clearance);
            for (int i = 0; i < g.Code.Length; i++) g.Code[i] = OccupancyGrid.Outside;
            for (int i = 0; i < c.N; i++)
            {
                int j = c.Wrap(i + 1);
                Splat(g, new Capsule(c.P[i], c.P[j], Math.Min(c.HalfWidth[i], c.HalfWidth[j]) - clearance), OccupancyGrid.Outside, OccupancyGrid.Free);
            }
            foreach (var o in obstacles) Splat(g, new Capsule(o.A, o.B, o.R + clearance), OccupancyGrid.Free, OccupancyGrid.Obstacle);
            if (seam)
            {
                V2 p = c.P[0], n = c.Nl[0]; double w = c.HalfWidth[0] + .5;
                Splat(g, new Capsule(p - n * w, p + n * w, cell * .75), OccupancyGrid.Free, OccupancyGrid.Seam);
                g.StartCell = g.NearestFree(g.CellOf(c.PointAt(.6)));
                g.GoalCell = g.NearestFree(g.CellOf(c.PointAt(c.Length - .6)));
            }
            return g;
        }
        private static void Splat(OccupancyGrid g, Capsule c, byte from, byte to)
        {
            if (c.R <= 0) return;
            int x0 = Math.Max(0, (int)Math.Floor((Math.Min(c.A.X, c.B.X) - c.R - g.X0) / g.Cell)), x1 = Math.Min(g.W - 1, (int)Math.Ceiling((Math.Max(c.A.X, c.B.X) + c.R - g.X0) / g.Cell));
            int y0 = Math.Max(0, (int)Math.Floor((Math.Min(c.A.Y, c.B.Y) - c.R - g.Y0) / g.Cell)), y1 = Math.Min(g.H - 1, (int)Math.Ceiling((Math.Max(c.A.Y, c.B.Y) + c.R - g.Y0) / g.Cell));
            for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++)
            {
                int i = g.Index(x, y);
                if (g.Code[i] == from && Capsule.SegmentDistance(g.CellCenter(i), c.A, c.B) <= c.R) g.Code[i] = to;
            }
        }
    }
}
