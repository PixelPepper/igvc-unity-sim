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

        /// <summary>True when every C-space cell sampled along a-b (half-cell steps) is free, ignoring the first
        /// <paramref name="skipA"/> and last <paramref name="skipB"/> metres (a pose snapped out of an inflated cell).</summary>
        public bool LineFree(V2 a, V2 b, double skipA = 0, double skipB = 0)
        {
            double len = V2.Distance(a, b); int n = Math.Max(1, (int)Math.Ceiling(len / (Grid.Cell * .5)));
            for (int i = 0; i <= n; i++)
            {
                double s = len * i / n; if (s < skipA || len - s < skipB) continue;
                if (!Map.Free(Grid.CellOf(V2.Lerp(a, b, (double)i / n)))) return false;
            }
            return true;
        }

        private SearchSpace reach;
        /// <summary>
        /// Shortest C-space grid path length (m, 8-connected, same move model as <see cref="Field"/>) from
        /// <paramref name="from"/> to each target, or NaN when unreachable within <paramref name="maxM"/>. A pose in a
        /// blocked cell snaps to the free cells within 1 m plus the straight offset (as <see cref="CostToGo(double[], V2, out int, out bool)"/>).
        /// One bounded Dijkstra that stops once every target is settled.
        /// </summary>
        public double[] PathFrom(V2 from, IList<V2> targets, double maxM, out int expanded)
        {
            expanded = 0; var res = new double[targets.Count]; for (int t = 0; t < res.Length; t++) res[t] = double.NaN;
            if (targets.Count == 0) return res;
            if (reach == null) reach = new SearchSpace(Map.Count);
            var S = reach; S.Begin(); var heap = S.Heap; double cell = Grid.Cell; int W = Map.W;
            foreach (var (c, off) in Anchors(from)) if (off / cell < S.GOf(c)) { S.Touch(c, off / cell, -1); heap.Push(c, off / cell, -off / cell); }
            if (heap.Count == 0) return res;
            var anchors = new Dictionary<int, List<(int t, double off)>>(); var left = new int[targets.Count]; var best = new double[targets.Count];
            var done = new bool[targets.Count]; int open = 0;
            for (int t = 0; t < targets.Count; t++)
            {
                best[t] = double.PositiveInfinity;
                foreach (var (c, off) in Anchors(targets[t]))
                {
                    if (!anchors.TryGetValue(c, out var l)) anchors[c] = l = new List<(int, double)>();
                    l.Add((t, off)); left[t]++;
                }
                if (left[t] == 0) done[t] = true; else open++;
            }
            double maxCells = maxM / cell;
            while (heap.Count > 0 && open > 0)
            {
                int u = heap.Pop(out double du);
                if (S.Closed(u) || du > S.G[u] + 1e-9) continue;
                if (du > maxCells) break;
                for (int t = 0; t < done.Length; t++) if (!done[t] && du * cell >= best[t]) { done[t] = true; open--; }
                if (open == 0) break;
                S.Close(u); expanded++;
                if (anchors.TryGetValue(u, out var hits))
                    foreach (var (t, off) in hits)
                    {
                        if (done[t]) continue;
                        best[t] = Math.Min(best[t], du * cell + off);
                        if (--left[t] == 0) { done[t] = true; open--; }
                    }
                int ux = u % W, uy = u / W;
                for (int d = 0; d < 8; d++)
                {
                    if (!Map.CanMove(ux, uy, d)) continue;
                    int v = u + GridMap.DY[d] * W + GridMap.DX[d]; double nd = du + GridMap.StepCost[d];
                    if (!S.Closed(v) && nd < S.GOf(v) - 1e-12) { S.Touch(v, nd, u); heap.Push(v, nd, -nd); }
                }
            }
            for (int t = 0; t < res.Length; t++) if (!double.IsInfinity(best[t])) res[t] = best[t];
            return res;
        }
        /// <summary>The point's own free cell (offset 0), else every free cell within 1 m with its straight offset.</summary>
        private List<(int cell, double off)> Anchors(V2 p)
        {
            var o = new List<(int, double)>(); int c = Grid.CellOf(p); if (c < 0) return o;
            if (Map.Free(c)) { o.Add((c, 0)); return o; }
            int cx = c % Grid.W, cy = c / Grid.W, r = 10;
            for (int dy = -r; dy <= r; dy++) for (int dx = -r; dx <= r; dx++)
            {
                int x = cx + dx, y = cy + dy; if (!Grid.InBounds(x, y) || dx * dx + dy * dy > r * r) continue;
                int i = Grid.Index(x, y); if (Map.Free(i)) o.Add((i, V2.Distance(p, Grid.CellCenter(i))));
            }
            return o;
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
