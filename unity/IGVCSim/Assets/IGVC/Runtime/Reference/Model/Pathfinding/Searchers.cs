using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace IGVC.Reference.Pathfinding
{
    public enum Algo { Dijkstra, AStar, WeightedAStar, BidirAStar, Jps, Hpa, FlowField }

    /// <summary>One query's answer plus the work it took (costs in cells; the study converts to metres).</summary>
    public sealed class SearchResult
    {
        public Algo Algo;
        public bool Found;
        public double Cost = GridMap.Inf;
        public readonly List<int> Path = new List<int>();
        /// <summary>Nodes popped and expanded (grid cells, jump points or abstract nodes).</summary>
        public int Expanded;
        /// <summary>Cells looked at without expansion: JPS jump scans, HPA* insertion/refinement, smoothing.</summary>
        public int Scanned;
        /// <summary>Distinct nodes that got a g-value (per-query memory proxy).</summary>
        public int Touched;
        public double Ms;
        /// <summary>Optional expansion order (cells; abstract node cells for HPA*) for the animated overlay.</summary>
        public List<int> Order;
        /// <summary>JPS: jump points on the path. HPA*: abstract nodes on the abstract path.</summary>
        public readonly List<int> KeyNodes = new List<int>();
        /// <summary>Bidirectional A*: cell where the frontiers met.</summary>
        public int Meet = -1;

        public void Clear(Algo a)
        {
            Algo = a; Found = false; Cost = GridMap.Inf; Path.Clear(); KeyNodes.Clear();
            Expanded = Scanned = Touched = 0; Ms = 0; Meet = -1; Order?.Clear();
        }
    }

    /// <summary>Binary min-heap of (f, g, node) with lazy deletion. Ties on f prefer larger g (deeper node).</summary>
    public sealed class MinHeap
    {
        private double[] f = new double[1024], g = new double[1024];
        private int[] n = new int[1024];
        public int Count, MaxCount;
        public void Clear() { Count = 0; MaxCount = 0; }
        private bool Less(int a, int b) { double d = f[a] - f[b]; if (d < -1e-9) return true; if (d > 1e-9) return false; return g[a] > g[b]; }
        public void Push(int node, double fv, double gv)
        {
            if (Count == n.Length) { Array.Resize(ref f, Count * 2); Array.Resize(ref g, Count * 2); Array.Resize(ref n, Count * 2); }
            int i = Count++; f[i] = fv; g[i] = gv; n[i] = node;
            if (Count > MaxCount) MaxCount = Count;
            while (i > 0) { int p = (i - 1) >> 1; if (!Less(i, p)) break; Swap(i, p); i = p; }
        }
        public double TopF => f[0];
        public int TopNode => n[0];
        public int Pop(out double fv)
        {
            int node = n[0]; fv = f[0]; Count--;
            if (Count > 0)
            {
                f[0] = f[Count]; g[0] = g[Count]; n[0] = n[Count];
                int i = 0;
                while (true)
                {
                    int l = 2 * i + 1, r = l + 1, m = i;
                    if (l < Count && Less(l, m)) m = l;
                    if (r < Count && Less(r, m)) m = r;
                    if (m == i) break;
                    Swap(i, m); i = m;
                }
            }
            return node;
        }
        private void Swap(int a, int b)
        {
            double tf = f[a]; f[a] = f[b]; f[b] = tf; double tg = g[a]; g[a] = g[b]; g[b] = tg;
            int tn = n[a]; n[a] = n[b]; n[b] = tn;
        }
    }

    /// <summary>Per-grid search scratch, "cleared" in O(1) by bumping a generation stamp.</summary>
    public sealed class SearchSpace
    {
        public readonly int N;
        public readonly double[] G;
        public readonly int[] Parent;
        private readonly int[] seen, closed;
        private int gen;
        public readonly MinHeap Heap = new MinHeap();
        public SearchSpace(int n) { N = n; G = new double[n]; Parent = new int[n]; seen = new int[n]; closed = new int[n]; }
        public void Begin()
        {
            gen++;
            if (gen == int.MaxValue) { Array.Clear(seen, 0, N); Array.Clear(closed, 0, N); gen = 1; }
            Heap.Clear();
        }
        public bool Seen(int i) => seen[i] == gen;
        public bool Closed(int i) => closed[i] == gen;
        public void Close(int i) => closed[i] = gen;
        public void Touch(int i, double g, int parent) { seen[i] = gen; G[i] = g; Parent[i] = parent; }
        public double GOf(int i) => seen[i] == gen ? G[i] : GridMap.Inf;
    }

    /// <summary>
    /// Grid searches on one move model, so costs compare exactly: Dijkstra, A*, bidirectional A* and JPS are optimal,
    /// weighted A* is w-suboptimal (HPA* lives in <see cref="Hpa"/>, the flow field in <see cref="FlowField"/>).
    /// </summary>
    public sealed class GridSearch
    {
        public readonly GridMap Map;
        private readonly SearchSpace a, b;
        private readonly Stopwatch sw = new Stopwatch();
        public double Weight = 1.5;
        /// <summary>Optional: every cell a JPS jump scans (overlay). Null = off.</summary>
        public List<int> ScanLog;

        public GridSearch(GridMap map) { Map = map; a = new SearchSpace(map.Count); b = new SearchSpace(map.Count); }
        public SearchSpace Space => a;
        public SearchSpace SpaceB => b;

        public void Run(Algo algo, int s, int t, SearchResult r)
        {
            r.Clear(algo); sw.Restart();
            switch (algo)
            {
                case Algo.Dijkstra: AStar(s, t, 0, r); break;
                case Algo.AStar: AStar(s, t, 1, r); break;
                case Algo.WeightedAStar: AStar(s, t, Weight, r); break;
                case Algo.BidirAStar: Bidirectional(s, t, r); break;
                case Algo.Jps: Jps(s, t, r); break;
                default: throw new ArgumentException("use Hpa / FlowField for " + algo);
            }
            sw.Stop(); r.Ms = sw.Elapsed.TotalMilliseconds;
        }

        /// <summary>
        /// A* with f = g + w·h (octile). w = 0 Dijkstra, w = 1 optimal A*, w &gt; 1 weighted A* without re-opening,
        /// which still guarantees cost ≤ w·optimal (Likhachev et al., ARA*).
        /// </summary>
        private void AStar(int s, int t, double w, SearchResult r)
        {
            var sp = a; var m = Map; sp.Begin();
            if (!m.Free(s) || !m.Free(t)) return;
            int tx = m.X(t), ty = m.Y(t), W = m.W;
            sp.Touch(s, 0, -1); r.Touched++;
            sp.Heap.Push(s, w * m.CellDist(s, t), 0);
            while (sp.Heap.Count > 0)
            {
                int u = sp.Heap.Pop(out _);
                if (sp.Closed(u)) continue;
                sp.Close(u); r.Expanded++; r.Order?.Add(u);
                if (u == t) break;
                int ux = u % W, uy = u / W; double gu = sp.G[u];
                for (int d = 0; d < 8; d++)
                {
                    if (!m.CanMove(ux, uy, d)) continue;
                    int v = u + GridMap.DY[d] * W + GridMap.DX[d];
                    if (sp.Closed(v)) continue;
                    double ng = gu + GridMap.StepCost[d]; bool seen = sp.Seen(v);
                    if (seen && ng >= sp.G[v] - 1e-12) continue;
                    if (!seen) r.Touched++;
                    sp.Touch(v, ng, u);
                    sp.Heap.Push(v, ng + w * GridMap.Octile(ux + GridMap.DX[d] - tx, uy + GridMap.DY[d] - ty), ng);
                }
            }
            if (!sp.Closed(t)) return;
            r.Found = true; r.Cost = sp.G[t]; Trace(sp, t, r.Path);
        }
        private static void Trace(SearchSpace sp, int t, List<int> path)
        {
            path.Clear();
            for (int c = t; c >= 0; c = sp.Parent[c]) path.Add(c);
            path.Reverse();
        }

        /// <summary>
        /// Bidirectional A* (octile h towards the other end), expanding the side with the smaller open list.
        /// μ = best g_f(v) + g_b(v) so far; once either side's smallest f ≥ μ no cheaper path exists, so μ is optimal.
        /// </summary>
        private void Bidirectional(int s, int t, SearchResult r)
        {
            var m = Map; var F = a; var B = b;
            F.Begin(); B.Begin();
            if (!m.Free(s) || !m.Free(t)) return;
            int W = m.W; double mu = GridMap.Inf; int meet = -1;
            F.Touch(s, 0, -1); B.Touch(t, 0, -1); r.Touched += 2;
            F.Heap.Push(s, m.CellDist(s, t), 0); B.Heap.Push(t, m.CellDist(t, s), 0);
            if (s == t) { mu = 0; meet = s; }
            while (true)
            {
                SkipClosed(F); SkipClosed(B);
                if (F.Heap.Count == 0 || B.Heap.Count == 0) break;
                if (F.Heap.TopF >= mu - 1e-9 || B.Heap.TopF >= mu - 1e-9) break;
                bool fwd = F.Heap.Count <= B.Heap.Count;
                var X = fwd ? F : B; var Y = fwd ? B : F;
                int target = fwd ? t : s, tx = m.X(target), ty = m.Y(target);
                int u = X.Heap.Pop(out _);
                X.Close(u); r.Expanded++; r.Order?.Add(u);
                int ux = u % W, uy = u / W; double gu = X.G[u];
                for (int d = 0; d < 8; d++)
                {
                    if (!m.CanMove(ux, uy, d)) continue;
                    int v = u + GridMap.DY[d] * W + GridMap.DX[d];
                    if (X.Closed(v)) continue;
                    double ng = gu + GridMap.StepCost[d]; bool seen = X.Seen(v);
                    if (seen && ng >= X.G[v] - 1e-12) continue;
                    if (!seen) r.Touched++;
                    X.Touch(v, ng, u);
                    X.Heap.Push(v, ng + GridMap.Octile(ux + GridMap.DX[d] - tx, uy + GridMap.DY[d] - ty), ng);
                    if (Y.Seen(v) && ng + Y.G[v] < mu) { mu = ng + Y.G[v]; meet = v; }
                }
            }
            if (meet < 0) return;
            r.Found = true; r.Cost = mu; r.Meet = meet;
            Trace(F, meet, r.Path);
            for (int c = B.Parent[meet]; c >= 0; c = B.Parent[c]) r.Path.Add(c);
        }
        private static void SkipClosed(SearchSpace sp) { while (sp.Heap.Count > 0 && sp.Closed(sp.Heap.TopNode)) sp.Heap.Pop(out _); }

        private int jt, scan;

        /// <summary>
        /// Jump Point Search (Harabor &amp; Grastien 2011), no-corner-cutting variant. A node follows only its parent's
        /// direction plus forced neighbours, scanning ("jumping") until the goal, a forced neighbour, or (diagonals) a
        /// straight sub-jump that finds one. Only jump points enter the open list; paths stay optimal.
        /// </summary>
        private void Jps(int s, int t, SearchResult r)
        {
            var sp = a; var m = Map; sp.Begin(); scan = 0;
            if (!m.Free(s) || !m.Free(t)) return;
            jt = t;
            int W = m.W, tx = m.X(t), ty = m.Y(t);
            sp.Touch(s, 0, -1); r.Touched++;
            sp.Heap.Push(s, m.CellDist(s, t), 0);
            var dirs = new int[8];
            while (sp.Heap.Count > 0)
            {
                int u = sp.Heap.Pop(out _);
                if (sp.Closed(u)) continue;
                sp.Close(u); r.Expanded++; r.Order?.Add(u);
                if (u == t) break;
                int ux = u % W, uy = u / W;
                int nd = PrunedDirections(ux, uy, sp.Parent[u], dirs);
                for (int k = 0; k < nd; k++)
                {
                    int d = dirs[k];
                    int j = Jump(ux + GridMap.DX[d], uy + GridMap.DY[d], GridMap.DX[d], GridMap.DY[d]);
                    if (j < 0 || sp.Closed(j)) continue;
                    int jx = j % W, jy = j / W;
                    double ng = sp.G[u] + GridMap.Octile(jx - ux, jy - uy); bool seen = sp.Seen(j);
                    if (seen && ng >= sp.G[j] - 1e-12) continue;
                    if (!seen) r.Touched++;
                    sp.Touch(j, ng, u);
                    sp.Heap.Push(j, ng + GridMap.Octile(jx - tx, jy - ty), ng);
                }
            }
            r.Scanned = scan;
            if (!sp.Closed(t)) return;
            r.Found = true; r.Cost = sp.G[t];
            var jumps = new List<int>();
            for (int c = t; c >= 0; c = sp.Parent[c]) jumps.Add(c);
            jumps.Reverse();
            r.KeyNodes.AddRange(jumps);
            r.Path.Add(jumps[0]);
            for (int i = 1; i < jumps.Count; i++)
            {
                int ax = m.X(jumps[i - 1]), ay = m.Y(jumps[i - 1]), bx = m.X(jumps[i]), by = m.Y(jumps[i]);
                int sx = Math.Sign(bx - ax), sy = Math.Sign(by - ay);
                while (ax != bx || ay != by) { ax += sx; ay += sy; r.Path.Add(m.Index(ax, ay)); }
            }
        }

        private int PrunedDirections(int x, int y, int parent, int[] o)
        {
            var m = Map; int n = 0;
            if (parent < 0) { for (int d = 0; d < 8; d++) if (m.CanMove(x, y, d)) o[n++] = d; return n; }
            int dx = Math.Sign(x - m.X(parent)), dy = Math.Sign(y - m.Y(parent));
            if (dx != 0 && dy != 0)
            {
                bool fy = m.Free(x, y + dy), fx = m.Free(x + dx, y);
                if (fy) o[n++] = GridMap.DirOf(0, dy);
                if (fx) o[n++] = GridMap.DirOf(dx, 0);
                if (fx && fy && m.Free(x + dx, y + dy)) o[n++] = GridMap.DirOf(dx, dy);
            }
            else if (dx != 0)
            {
                bool next = m.Free(x + dx, y), up = m.Free(x, y + 1), down = m.Free(x, y - 1);
                if (next)
                {
                    o[n++] = GridMap.DirOf(dx, 0);
                    if (up && m.Free(x + dx, y + 1)) o[n++] = GridMap.DirOf(dx, 1);
                    if (down && m.Free(x + dx, y - 1)) o[n++] = GridMap.DirOf(dx, -1);
                }
                if (up) o[n++] = GridMap.DirOf(0, 1);
                if (down) o[n++] = GridMap.DirOf(0, -1);
            }
            else
            {
                bool next = m.Free(x, y + dy), right = m.Free(x + 1, y), left = m.Free(x - 1, y);
                if (next)
                {
                    o[n++] = GridMap.DirOf(0, dy);
                    if (right && m.Free(x + 1, y + dy)) o[n++] = GridMap.DirOf(1, dy);
                    if (left && m.Free(x - 1, y + dy)) o[n++] = GridMap.DirOf(-1, dy);
                }
                if (right) o[n++] = GridMap.DirOf(1, 0);
                if (left) o[n++] = GridMap.DirOf(-1, 0);
            }
            return n;
        }

        /// <summary>Iterative scan from (x,y) in (dx,dy); returns the jump point index or -1.</summary>
        private int Jump(int x, int y, int dx, int dy)
        {
            var m = Map;
            while (true)
            {
                if (!m.Free(x, y)) return -1;
                scan++; int i = y * m.W + x; ScanLog?.Add(i);
                if (i == jt) return i;
                if (dx != 0 && dy != 0)
                {
                    if (JumpStraight(x + dx, y, dx, 0) >= 0 || JumpStraight(x, y + dy, 0, dy) >= 0) return i;
                    if (!(m.Free(x + dx, y) && m.Free(x, y + dy))) return -1;
                }
                else if (IsForcedStraight(x, y, dx, dy)) return i;
                x += dx; y += dy;
            }
        }
        private int JumpStraight(int x, int y, int dx, int dy)
        {
            var m = Map;
            while (true)
            {
                if (!m.Free(x, y)) return -1;
                scan++; int i = y * m.W + x; ScanLog?.Add(i);
                if (i == jt || IsForcedStraight(x, y, dx, dy)) return i;
                x += dx; y += dy;
            }
        }
        /// <summary>A side cell is forced when free but the cell diagonally behind it is blocked (no corner cutting).</summary>
        private bool IsForcedStraight(int x, int y, int dx, int dy)
        {
            var m = Map;
            if (dx != 0) return (m.Free(x, y + 1) && !m.Free(x - dx, y + 1)) || (m.Free(x, y - 1) && !m.Free(x - dx, y - 1));
            return (m.Free(x + 1, y) && !m.Free(x + 1, y - dy)) || (m.Free(x - 1, y) && !m.Free(x - 1, y - dy));
        }
    }

    /// <summary>
    /// Flow field: one Dijkstra from the GOAL stores every cell's exact distance; agents then walk downhill in
    /// O(path length). Expensive for one query, cheap when many share a goal; cached until the goal or map changes.
    /// </summary>
    public sealed class FlowField
    {
        public readonly GridMap Map;
        public readonly double[] Dist;
        private readonly MinHeap heap = new MinHeap();
        private readonly bool[] done;
        private readonly Stopwatch sw = new Stopwatch();
        public int Goal { get; private set; } = -1;
        public int MapVersion { get; private set; } = -1;
        public int Reached { get; private set; }
        public double MaxDist { get; private set; }
        public double BuildMs { get; private set; }
        public int Builds { get; private set; }

        public FlowField(GridMap map) { Map = map; Dist = new double[map.Count]; done = new bool[map.Count]; }
        public bool Valid(int goal) => goal == Goal && MapVersion == Map.Version;
        public void Invalidate() => Goal = -1;

        /// <summary>Full Dijkstra from the goal; optional settle order. Returns cells expanded.</summary>
        public int Build(int goal, List<int> order = null)
        {
            sw.Restart(); var m = Map;
            for (int i = 0; i < Dist.Length; i++) { Dist[i] = GridMap.Inf; done[i] = false; }
            Goal = goal; MapVersion = m.Version; Reached = 0; MaxDist = 0; heap.Clear();
            if (m.Free(goal))
            {
                Dist[goal] = 0; heap.Push(goal, 0, 0); int W = m.W;
                while (heap.Count > 0)
                {
                    int u = heap.Pop(out double du);
                    if (done[u]) continue;
                    done[u] = true; Reached++; order?.Add(u);
                    if (du > MaxDist) MaxDist = du;
                    int ux = u % W, uy = u / W;
                    for (int d = 0; d < 8; d++)
                    {
                        if (!m.CanMove(ux, uy, d)) continue;
                        int v = u + GridMap.DY[d] * W + GridMap.DX[d]; double nd = du + GridMap.StepCost[d];
                        if (nd < Dist[v] - 1e-12) { Dist[v] = nd; heap.Push(v, nd, -nd); }
                    }
                }
            }
            sw.Stop(); BuildMs = sw.Elapsed.TotalMilliseconds; Builds++;
            return Reached;
        }

        public void Query(int s, int t, SearchResult r)
        {
            r.Clear(Algo.FlowField);
            var watch = Stopwatch.StartNew();
            if (!Valid(t)) { r.Expanded = Build(t, r.Order); r.Touched = Reached; }
            Descend(s, r.Path, out r.Scanned);
            watch.Stop(); r.Ms = watch.Elapsed.TotalMilliseconds;
            if (r.Path.Count == 0) return;
            r.Found = true; r.Cost = Dist[s];
        }

        /// <summary>Walk downhill from s; each step takes a neighbour that realises dist[s] exactly.</summary>
        public void Descend(int s, List<int> path, out int steps)
        {
            path.Clear(); steps = 0;
            if (Goal < 0 || !Map.Free(s) || double.IsInfinity(Dist[s])) return;
            var m = Map; int u = s, W = m.W;
            path.Add(u);
            while (u != Goal && steps < m.Count)
            {
                int ux = u % W, uy = u / W, best = -1; double bestD = Dist[u];
                for (int d = 0; d < 8; d++)
                {
                    if (!m.CanMove(ux, uy, d)) continue;
                    int v = u + GridMap.DY[d] * W + GridMap.DX[d];
                    if (Dist[v] + GridMap.StepCost[d] <= Dist[u] + 1e-9 && Dist[v] < bestD) { bestD = Dist[v]; best = v; }
                }
                if (best < 0) { path.Clear(); return; }
                u = best; path.Add(u); steps++;
            }
        }
        public long MemoryBytes => (long)Dist.Length * sizeof(double) + done.Length;
    }
}
