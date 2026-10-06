using System;
using System.Collections.Generic;
using IGVC.Reference.Pathfinding;
using IGVC.Reference.RacingLine;

namespace IGVC.Reference.Teacher
{
    /// <summary>Racing-line speed profile (lower-bound lap sim) used for teacher speed labels.</summary>
    public sealed class SpeedProfile
    {
        public double Ceiling, LapTime; public int BlockedStations;
        public V2[] Pts; public double[] V;
        public double At(V2 p, out int station)
        {
            station = 0; double best = double.PositiveInfinity;
            for (int i = 0; i < Pts.Length; i++) { double d = (Pts[i] - p).SqrLength; if (d < best) { best = d; station = i; } }
            return Pts.Length == 0 ? double.NaN : V[station];
        }
    }

    /// <summary>
    /// Full-knowledge teacher: the whole course as a C-space grid (Rasterizer, no seam, inscribed clearance as in the
    /// Reference Lab), one exact cost-to-go field (metres) per destination cell, route descent and racing-line speeds.
    /// WORLD data: offline labels only, never a mission input.
    /// </summary>
    public sealed class HindsightTeacher
    {
        public readonly CourseGeometry Course; public readonly Corridor Corridor; public readonly Capsule[] Shapes;
        public readonly RobotLimits Limits; public readonly OccupancyGrid Grid; public readonly GridMap Map;
        public readonly int FreeCells;
        private readonly FlowField flow;
        private readonly Dictionary<int, double[]> fields = new Dictionary<int, double[]>();
        private readonly Dictionary<double, SpeedProfile> speeds = new Dictionary<double, SpeedProfile>();
        private RacingLineStudy line;

        public HindsightTeacher(CourseGeometry course, RobotLimits limits = null, double cell = .1)
        {
            Course = course; Limits = limits ?? new RobotLimits(); Corridor = new Corridor(course); Shapes = course.Shapes();
            Grid = Rasterizer.Rasterize(Corridor, Shapes, cell, Limits.InscribedRadius, false);
            Map = GridMap.FromOccupancy(Grid); flow = new FlowField(Map); FreeCells = Map.FreeCount();
        }
        public double Cell => Grid.Cell;
        public byte CodeAt(V2 p) { int c = Grid.CellOf(p); return c < 0 ? OccupancyGrid.Outside : Grid.Code[c]; }
        /// <summary>Destination cell: the point's own cell or the nearest free one within 2.5 m (-1 if none).</summary>
        public int GoalCell(V2 p, out double snap)
        {
            int c = Grid.NearestFree(Grid.CellOf(p), 25);
            snap = c < 0 ? double.NaN : V2.Distance(p, Grid.CellCenter(c)); return c;
        }
        /// <summary>Dijkstra from the goal cell over free cells; metres; Inf where unreachable. Cached per goal.</summary>
        public double[] Field(int goal)
        {
            if (goal < 0) return null;
            if (fields.TryGetValue(goal, out var f)) return f;
            flow.Build(goal); f = new double[flow.Dist.Length];
            for (int i = 0; i < f.Length; i++) f[i] = flow.Dist[i] * Grid.Cell;
            fields[goal] = f; return f;
        }
        public double[] FieldFor(V2 destination) => Field(GoalCell(destination, out _));
        public static int Reached(double[] f) { if (f == null) return 0; int n = 0; foreach (var v in f) if (!double.IsInfinity(v)) n++; return n; }

        /// <summary>Cost-to-go (m) at p: its own cell, else the best reached cell within 1 m plus the straight offset; NaN if none.</summary>
        public double CostToGo(double[] f, V2 p, out int cell, out bool snapped)
        {
            cell = -1; snapped = false; if (f == null) return double.NaN;
            int c = Grid.CellOf(p); if (c < 0) return double.NaN;
            if (!double.IsInfinity(f[c])) { cell = c; return f[c]; }
            int cx = c % Grid.W, cy = c / Grid.W, r = 10; double best = double.PositiveInfinity;
            for (int dy = -r; dy <= r; dy++) for (int dx = -r; dx <= r; dx++)
            {
                int x = cx + dx, y = cy + dy; if (!Grid.InBounds(x, y) || dx * dx + dy * dy > r * r) continue;
                int i = Grid.Index(x, y); if (double.IsInfinity(f[i])) continue;
                double v = f[i] + V2.Distance(p, Grid.CellCenter(i)); if (v < best) { best = v; cell = i; }
            }
            snapped = cell >= 0; return snapped ? best : double.NaN;
        }
        public double CostToGo(double[] f, V2 p) => CostToGo(f, p, out _, out _);

        /// <summary>
        /// True when every grid cell the segment a-b intersects is free C-space (supercover traversal; an exact corner
        /// crossing also tests both side cells, matching <see cref="GridMap.CanMove"/>'s no-corner-cutting rule). Both
        /// endpoint cells must be free: nothing is skipped or snapped, so a blocked pose never gains a connection.
        /// </summary>
        public bool SegmentFree(V2 a, V2 b)
        {
            double cs = Grid.Cell, ax = (a.X - Grid.X0) / cs, ay = (a.Y - Grid.Y0) / cs, bx = (b.X - Grid.X0) / cs, by = (b.Y - Grid.Y0) / cs;
            int x = (int)Math.Floor(ax), y = (int)Math.Floor(ay), x1 = (int)Math.Floor(bx), y1 = (int)Math.Floor(by);
            if (!Map.Free(x, y) || !Map.Free(x1, y1)) return false;
            double dx = bx - ax, dy = by - ay; int sx = Math.Sign(dx), sy = Math.Sign(dy);
            double tdx = sx != 0 ? 1 / Math.Abs(dx) : double.PositiveInfinity, tdy = sy != 0 ? 1 / Math.Abs(dy) : double.PositiveInfinity;
            double tx = sx > 0 ? (x + 1 - ax) * tdx : sx < 0 ? (ax - x) * tdx : double.PositiveInfinity;
            double ty = sy > 0 ? (y + 1 - ay) * tdy : sy < 0 ? (ay - y) * tdy : double.PositiveInfinity;
            int guard = Math.Abs(x1 - x) + Math.Abs(y1 - y) + 2;
            while ((x != x1 || y != y1) && guard-- > 0)
            {
                if (Math.Abs(tx - ty) < 1e-12) { if (!Map.Free(x + sx, y) || !Map.Free(x, y + sy)) return false; x += sx; y += sy; tx += tdx; ty += tdy; }
                else if (tx < ty) { x += sx; tx += tdx; }
                else { y += sy; ty += tdy; }
                if (!Map.Free(x, y)) return false;
            }
            return x == x1 && y == y1; // float drift past the end cell: conservatively not free
        }

        /// <summary>Outcome of <see cref="PathFrom"/> for one target.</summary>
        public enum Reach { Reached, Disconnected, SearchLimited, BlockedStart, BlockedTarget }

        private SearchSpace reach;
        /// <summary>
        /// Shortest C-space grid path length (m, 8-connected, same move model as <see cref="Field"/>) from
        /// <paramref name="from"/> to each target, NaN unless <see cref="Reach.Reached"/>. Endpoints attach only to their
        /// own free cell (straight in-cell offset to its centre; a cell is convex). A blocked or off-grid endpoint is
        /// reported, never snapped. One Dijkstra on the reused search space, stopping once every target is settled:
        /// targets unsettled when the next node exceeds <paramref name="maxM"/> are SearchLimited (unknown); targets
        /// unsettled after the start's whole free component is exhausted are Disconnected (proven on this grid).
        /// </summary>
        public double[] PathFrom(V2 from, IList<V2> targets, double maxM, out Reach[] status, out int expanded)
        {
            expanded = 0; int n = targets.Count; var res = new double[n]; status = new Reach[n];
            for (int t = 0; t < n; t++) res[t] = double.NaN;
            var at = new Dictionary<int, List<int>>(); int open = 0;
            for (int t = 0; t < n; t++)
            {
                int c = Grid.CellOf(targets[t]);
                if (!Map.Free(c)) { status[t] = Reach.BlockedTarget; continue; }
                if (!at.TryGetValue(c, out var l)) at[c] = l = new List<int>();
                l.Add(t); open++; status[t] = Reach.SearchLimited;
            }
            int start = Grid.CellOf(from);
            if (!Map.Free(start)) { for (int t = 0; t < n; t++) if (status[t] == Reach.SearchLimited) status[t] = Reach.BlockedStart; return res; }
            if (open == 0) return res;
            if (reach == null) reach = new SearchSpace(Map.Count);
            var S = reach; S.Begin(); var heap = S.Heap; double cell = Grid.Cell; int W = Map.W;
            double startOff = V2.Distance(from, Grid.CellCenter(start)), maxCells = maxM / cell; bool capped = false;
            S.Touch(start, 0, -1); heap.Push(start, 0, 0);
            while (heap.Count > 0 && open > 0)
            {
                int u = heap.Pop(out double du);
                if (S.Closed(u) || du > S.G[u] + 1e-9) continue;
                if (du > maxCells) { capped = true; break; }
                S.Close(u); expanded++;
                if (at.TryGetValue(u, out var hits))
                    foreach (int t in hits) { res[t] = startOff + du * cell + V2.Distance(Grid.CellCenter(u), targets[t]); status[t] = Reach.Reached; open--; }
                int ux = u % W, uy = u / W;
                for (int d = 0; d < 8; d++)
                {
                    if (!Map.CanMove(ux, uy, d)) continue;
                    int v = u + GridMap.DY[d] * W + GridMap.DX[d]; double nd = du + GridMap.StepCost[d];
                    if (!S.Closed(v) && nd < S.GOf(v) - 1e-12) { S.Touch(v, nd, u); heap.Push(v, nd, -nd); }
                }
            }
            if (!capped) for (int t = 0; t < n; t++) if (status[t] == Reach.SearchLimited) status[t] = Reach.Disconnected;
            return res;
        }

        /// <summary>Steepest-descent route from p (first point = p itself) until the goal or <paramref name="maxLength"/>.</summary>
        public List<V2> Route(double[] f, V2 p, double maxLength = double.PositiveInfinity, List<int> cells = null)
        {
            var route = new List<V2>(); cells?.Clear();
            CostToGo(f, p, out int u, out _); if (u < 0) return route;
            route.Add(p); V2 c0 = Grid.CellCenter(u); double len = V2.Distance(p, c0);
            if (len > 1e-9) route.Add(c0);
            cells?.Add(u); int W = Map.W;
            while (f[u] > 0 && len < maxLength)
            {
                int ux = u % W, uy = u / W, best = -1; double bestD = f[u];
                for (int d = 0; d < 8; d++)
                {
                    if (!Map.CanMove(ux, uy, d)) continue;
                    int v = u + GridMap.DY[d] * W + GridMap.DX[d];
                    if (f[v] + GridMap.StepCost[d] * Grid.Cell <= f[u] + 1e-9 && f[v] < bestD) { bestD = f[v]; best = v; }
                }
                if (best < 0) break;
                len += (f[u] - f[best]); u = best; route.Add(Grid.CellCenter(u)); cells?.Add(u);
            }
            return route;
        }

        public SpeedProfile Speed(double ceiling)
        {
            if (speeds.TryGetValue(ceiling, out var s)) return s;
            if (line == null) line = new RacingLineStudy(Corridor, Shapes, Limits);
            line.SpeedCeiling = ceiling; foreach (var _ in line.Run()) { }
            s = new SpeedProfile { Ceiling = ceiling, LapTime = line.Lap.LapTime, BlockedStations = line.BlockedStations, Pts = (V2[])line.Line.Clone(), V = (double[])line.Lap.V.Clone() };
            speeds[ceiling] = s; return s;
        }

        // ---- polyline helpers ----
        public static double Length(IList<V2> pts) { double l = 0; if (pts != null) for (int i = 1; i < pts.Count; i++) l += V2.Distance(pts[i - 1], pts[i]); return l; }
        /// <summary>Point at arc length s (clamped to the ends).</summary>
        public static V2 Along(IList<V2> pts, double s)
        {
            if (pts == null || pts.Count == 0) return new V2(double.NaN, double.NaN);
            double acc = 0;
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                double seg = V2.Distance(pts[i], pts[i + 1]);
                if (acc + seg >= s && seg > 1e-12) return V2.Lerp(pts[i], pts[i + 1], Math.Max(0, (s - acc) / seg));
                acc += seg;
            }
            return pts[pts.Count - 1];
        }
        /// <summary>Route direction around arc length s, from the points 1 m either side (grid steps are 45 degree quantised).</summary>
        public static double YawAlong(IList<V2> pts, double s)
        {
            V2 d = Along(pts, s + 1) - Along(pts, Math.Max(0, s - 1));
            return d.SqrLength > 1e-12 ? d.Angle : double.NaN;
        }
        public static List<V2> Resample(IList<V2> pts, double step, double maxLength)
        {
            var o = new List<V2>(); if (pts == null || pts.Count == 0) return o;
            double total = Math.Min(Length(pts), maxLength);
            for (double s = 0; s < total - 1e-9; s += step) o.Add(Along(pts, s));
            o.Add(Along(pts, total)); return o;
        }
        public static double WrapAngle(double a) { while (a > Math.PI) a -= 2 * Math.PI; while (a <= -Math.PI) a += 2 * Math.PI; return a; }
    }
}
