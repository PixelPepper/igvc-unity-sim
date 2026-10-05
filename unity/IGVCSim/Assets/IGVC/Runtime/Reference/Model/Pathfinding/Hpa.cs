using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace IGVC.Reference.Pathfinding
{
    /// <summary>
    /// HPA* - Hierarchical Path-Finding A* (Botea, Müller &amp; Schaeffer 2004), one abstraction level.
    /// Build: cut the map into C×C clusters; along every border find the entrances (maximal runs where both sides are
    /// free): a run shorter than <see cref="WideEntrance"/> gets one transition in its middle, a longer one two at its
    /// ends, each a pair of adjacent cells joined by an inter-edge of cost 1; inside every cluster a Dijkstra from each
    /// transition cell gives the exact in-cluster distances (intra-edges).
    /// Query: insert start and goal (a Dijkstra inside their clusters), A* over the abstract graph, then refine each
    /// abstract edge with an A* restricted to one cluster. Near-optimal (paths pass through transition cells) and
    /// complete. <see cref="Update"/> rescans only borders touching an edit and rebuilds only affected clusters; the
    /// result is identical to a full rebuild (<see cref="DiffFrom"/>).
    /// </summary>
    public sealed class Hpa
    {
        public const int WideEntrance = 6;
        public readonly GridMap Map;
        public readonly int C, CW, CH;
        /// <summary>Transitions per vertical border (cluster (cx,cy) | (cx+1,cy)), flattened pairs [a0,b0,a1,b1...].</summary>
        public readonly List<int>[] VTrans;
        /// <summary>Transitions per horizontal border ((cx,cy) | (cx,cy+1)).</summary>
        public readonly List<int>[] HTrans;
        public readonly Cluster[] Clusters;
        public double BuildMs { get; private set; }
        public double LastUpdateMs { get; private set; }
        public int LastUpdateClusters { get; private set; }
        public int LastUpdateBorders { get; private set; }
        public int TotalUpdates { get; private set; }
        public bool Built { get; private set; }
        /// <summary>Bumped whenever any cluster is rebuilt (views key on it).</summary>
        public int Revision { get; private set; }

        public sealed class Cluster
        {
            public int X0, Y0, X1, Y1;              // inclusive cell rectangle
            public int[] Nodes = new int[0];         // sorted transition cells
            public double[] Dist = new double[0];    // n×n in-cluster distances (Inf = not connected inside)
            public int[][] Partners = new int[0][];  // per node: cells across its inter-edges
            public int Version;
        }

        private readonly LocalSearch local;
        private readonly SearchSpace abs;
        private readonly PathSmoother smoother;
        private readonly Stopwatch sw = new Stopwatch();

        public Hpa(GridMap map, int clusterSize)
        {
            Map = map; C = Math.Max(2, clusterSize);
            CW = (map.W + C - 1) / C; CH = (map.H + C - 1) / C;
            VTrans = new List<int>[Math.Max(0, CW - 1) * CH];
            HTrans = new List<int>[CW * Math.Max(0, CH - 1)];
            for (int i = 0; i < VTrans.Length; i++) VTrans[i] = new List<int>();
            for (int i = 0; i < HTrans.Length; i++) HTrans[i] = new List<int>();
            Clusters = new Cluster[CW * CH];
            for (int cy = 0; cy < CH; cy++)
                for (int cx = 0; cx < CW; cx++)
                    Clusters[cy * CW + cx] = new Cluster { X0 = cx * C, Y0 = cy * C, X1 = Math.Min(map.W, (cx + 1) * C) - 1, Y1 = Math.Min(map.H, (cy + 1) * C) - 1 };
            local = new LocalSearch(map, C);
            abs = new SearchSpace(map.Count);
            smoother = new PathSmoother(map);
        }

        public int ClusterOf(int cell) => (Map.Y(cell) / C) * CW + Map.X(cell) / C;

        public void BuildAll() { foreach (var _ in BuildSteps(int.MaxValue)) { } }

        /// <summary>Full build yielding every <paramref name="clustersPerStep"/> clusters (index of the last one built).</summary>
        public IEnumerable<int> BuildSteps(int clustersPerStep)
        {
            Built = false; double ms = 0; clustersPerStep = Math.Max(1, clustersPerStep);
            sw.Restart();
            for (int cy = 0; cy < CH; cy++) for (int cx = 0; cx + 1 < CW; cx++) ScanVBorder(cx, cy, VTrans[cy * (CW - 1) + cx]);
            for (int cy = 0; cy + 1 < CH; cy++) for (int cx = 0; cx < CW; cx++) ScanHBorder(cx, cy, HTrans[cy * CW + cx]);
            for (int k = 0; k < Clusters.Length; k++)
            {
                RebuildCluster(k);
                if ((k + 1) % clustersPerStep == 0 && k + 1 < Clusters.Length)
                {
                    sw.Stop(); ms += sw.Elapsed.TotalMilliseconds;
                    yield return k;
                    sw.Restart();
                }
            }
            sw.Stop(); BuildMs = ms + sw.Elapsed.TotalMilliseconds; Built = true;
        }

        private void ScanVBorder(int cx, int cy, List<int> o)
        {
            o.Clear();
            int xa = (cx + 1) * C - 1, xb = xa + 1, y0 = cy * C, y1 = Math.Min(Map.H, (cy + 1) * C) - 1, run = -1;
            for (int y = y0; y <= y1 + 1; y++)
            {
                bool open = y <= y1 && Map.Free(xa, y) && Map.Free(xb, y);
                if (open && run < 0) run = y;
                if (open || run < 0) continue;
                int len = y - run;
                if (len < WideEntrance) { int m = run + len / 2; o.Add(Map.Index(xa, m)); o.Add(Map.Index(xb, m)); }
                else { o.Add(Map.Index(xa, run)); o.Add(Map.Index(xb, run)); o.Add(Map.Index(xa, y - 1)); o.Add(Map.Index(xb, y - 1)); }
                run = -1;
            }
        }
        private void ScanHBorder(int cx, int cy, List<int> o)
        {
            o.Clear();
            int ya = (cy + 1) * C - 1, yb = ya + 1, x0 = cx * C, x1 = Math.Min(Map.W, (cx + 1) * C) - 1, run = -1;
            for (int x = x0; x <= x1 + 1; x++)
            {
                bool open = x <= x1 && Map.Free(x, ya) && Map.Free(x, yb);
                if (open && run < 0) run = x;
                if (open || run < 0) continue;
                int len = x - run;
                if (len < WideEntrance) { int m = run + len / 2; o.Add(Map.Index(m, ya)); o.Add(Map.Index(m, yb)); }
                else { o.Add(Map.Index(run, ya)); o.Add(Map.Index(run, yb)); o.Add(Map.Index(x - 1, ya)); o.Add(Map.Index(x - 1, yb)); }
                run = -1;
            }
        }

        private readonly List<int> tmpNodes = new List<int>(), tmpFrom = new List<int>(), tmpTo = new List<int>();

        /// <summary>Collect the cluster's transition cells from its 4 borders and recompute all intra distances.</summary>
        private void RebuildCluster(int k)
        {
            var cl = Clusters[k]; int cx = k % CW, cy = k / CW;
            tmpNodes.Clear(); tmpFrom.Clear(); tmpTo.Clear();
            // Right/top border: this cluster holds the 'a' side; left/bottom: the 'b' side.
            if (cx + 1 < CW) AddSide(VTrans[cy * (CW - 1) + cx], 0);
            if (cx > 0) AddSide(VTrans[cy * (CW - 1) + cx - 1], 1);
            if (cy + 1 < CH) AddSide(HTrans[cy * CW + cx], 0);
            if (cy > 0) AddSide(HTrans[(cy - 1) * CW + cx], 1);
            tmpNodes.Sort();
            int w = 0;
            for (int i = 0; i < tmpNodes.Count; i++) if (i == 0 || tmpNodes[i] != tmpNodes[i - 1]) tmpNodes[w++] = tmpNodes[i];
            tmpNodes.RemoveRange(w, tmpNodes.Count - w);
            int n = tmpNodes.Count;
            cl.Nodes = tmpNodes.ToArray(); cl.Partners = new int[n][];
            var counts = new int[n];
            for (int i = 0; i < tmpFrom.Count; i++) counts[Array.BinarySearch(cl.Nodes, tmpFrom[i])]++;
            for (int i = 0; i < n; i++) cl.Partners[i] = new int[counts[i]];
            Array.Clear(counts, 0, n);
            for (int i = 0; i < tmpFrom.Count; i++) { int li = Array.BinarySearch(cl.Nodes, tmpFrom[i]); cl.Partners[li][counts[li]++] = tmpTo[i]; }
            for (int i = 0; i < n; i++) Array.Sort(cl.Partners[i]);
            cl.Dist = new double[n * n];
            for (int i = 0; i < n; i++)
            {
                local.Dijkstra(cl, cl.Nodes[i]);
                for (int j = 0; j < n; j++) cl.Dist[i * n + j] = local.DistTo(cl.Nodes[j]);
            }
            cl.Version++; Revision++;
        }
        private void AddSide(List<int> pairs, int side)
        {
            for (int i = 0; i < pairs.Count; i += 2) { int mine = pairs[i + side]; tmpNodes.Add(mine); tmpFrom.Add(mine); tmpTo.Add(pairs[i + 1 - side]); }
        }

        private readonly SortedSet<int> dirtyV = new SortedSet<int>(), dirtyH = new SortedSet<int>(), dirtyC = new SortedSet<int>();
        private readonly List<int> scratch = new List<int>();
        /// <summary>Clusters rebuilt by the last <see cref="Update"/> (the view highlights them).</summary>
        public readonly List<int> LastDirty = new List<int>();

        /// <summary>
        /// Incremental repair after cells in [x0..x1]×[y0..y1] changed: rescan only borders through that rectangle and
        /// rebuild the clusters that contain a changed cell or whose border transitions changed.
        /// </summary>
        public void Update(int x0, int y0, int x1, int y1)
        {
            sw.Restart();
            x0 = Math.Max(0, x0); y0 = Math.Max(0, y0); x1 = Math.Min(Map.W - 1, x1); y1 = Math.Min(Map.H - 1, y1);
            dirtyV.Clear(); dirtyH.Clear(); dirtyC.Clear(); LastDirty.Clear();
            if (x0 > x1 || y0 > y1) { sw.Stop(); return; }
            for (int cy = y0 / C; cy <= y1 / C; cy++) for (int cx = x0 / C; cx <= x1 / C; cx++) dirtyC.Add(cy * CW + cx);
            for (int cx = 0; cx + 1 < CW; cx++)
            {
                int xa = (cx + 1) * C - 1, xb = xa + 1;
                if (x1 < xa || x0 > xb) continue;
                for (int cy = y0 / C; cy <= y1 / C; cy++) dirtyV.Add(cy * (CW - 1) + cx);
            }
            for (int cy = 0; cy + 1 < CH; cy++)
            {
                int ya = (cy + 1) * C - 1, yb = ya + 1;
                if (y1 < ya || y0 > yb) continue;
                for (int cx = x0 / C; cx <= x1 / C; cx++) dirtyH.Add(cy * CW + cx);
            }
            int borders = 0;
            foreach (int v in dirtyV)
            {
                int cx = v % (CW - 1), cy = v / (CW - 1);
                ScanVBorder(cx, cy, scratch); borders++;
                if (SameList(scratch, VTrans[v])) continue;
                VTrans[v].Clear(); VTrans[v].AddRange(scratch);
                dirtyC.Add(cy * CW + cx); dirtyC.Add(cy * CW + cx + 1);
            }
            foreach (int h in dirtyH)
            {
                int cx = h % CW, cy = h / CW;
                ScanHBorder(cx, cy, scratch); borders++;
                if (SameList(scratch, HTrans[h])) continue;
                HTrans[h].Clear(); HTrans[h].AddRange(scratch);
                dirtyC.Add(cy * CW + cx); dirtyC.Add((cy + 1) * CW + cx);
            }
            foreach (int k in dirtyC) { RebuildCluster(k); LastDirty.Add(k); }
            sw.Stop();
            LastUpdateMs = sw.Elapsed.TotalMilliseconds; LastUpdateClusters = dirtyC.Count; LastUpdateBorders = borders; TotalUpdates++;
        }
        private static bool SameList(List<int> a, List<int> b)
        {
            if (a.Count != b.Count) return false;
            for (int i = 0; i < a.Count; i++) if (a[i] != b[i]) return false;
            return true;
        }

        /// <summary>Exact structural comparison (borders, nodes, partners, distances). Null when identical.</summary>
        public string DiffFrom(Hpa o)
        {
            if (o.C != C || o.CW != CW || o.CH != CH) return "different layout";
            for (int i = 0; i < VTrans.Length; i++) if (!SameList(VTrans[i], o.VTrans[i])) return $"V border {i} differs";
            for (int i = 0; i < HTrans.Length; i++) if (!SameList(HTrans[i], o.HTrans[i])) return $"H border {i} differs";
            for (int k = 0; k < Clusters.Length; k++)
            {
                var a = Clusters[k]; var b = o.Clusters[k];
                if (a.Nodes.Length != b.Nodes.Length) return $"cluster {k}: {a.Nodes.Length} vs {b.Nodes.Length} nodes";
                for (int i = 0; i < a.Nodes.Length; i++)
                {
                    if (a.Nodes[i] != b.Nodes[i]) return $"cluster {k}: node {i} differs";
                    if (a.Partners[i].Length != b.Partners[i].Length) return $"cluster {k}: partners of node {i} differ";
                    for (int j = 0; j < a.Partners[i].Length; j++) if (a.Partners[i][j] != b.Partners[i][j]) return $"cluster {k}: partner differs";
                }
                for (int i = 0; i < a.Dist.Length; i++)
                    if (!(a.Dist[i] == b.Dist[i] || (double.IsInfinity(a.Dist[i]) && double.IsInfinity(b.Dist[i])))) return $"cluster {k}: dist[{i}] {a.Dist[i]} vs {b.Dist[i]}";
            }
            return null;
        }

        public int NodeCount { get { int n = 0; foreach (var c in Clusters) n += c.Nodes.Length; return n; } }
        public int EdgeCount
        {
            get
            {
                int e = 0;
                foreach (var c in Clusters)
                {
                    int n = c.Nodes.Length;
                    for (int i = 0; i < n; i++) for (int j = i + 1; j < n; j++) if (!double.IsInfinity(c.Dist[i * n + j])) e++;
                }
                foreach (var l in VTrans) e += l.Count / 2;
                foreach (var l in HTrans) e += l.Count / 2;
                return e;
            }
        }
        public long MemoryBytes
        {
            get
            {
                long b = 0;
                foreach (var c in Clusters) { b += c.Dist.Length * 8L + c.Nodes.Length * 4L; foreach (var p in c.Partners) b += p.Length * 4L + 16; }
                foreach (var l in VTrans) b += l.Count * 4L;
                foreach (var l in HTrans) b += l.Count * 4L;
                return b;
            }
        }

        private int qt, ks, kt;
        private double[] sDist = new double[64], tDist = new double[64];
        private double stDirect;
        /// <summary>Last query's abstract A* expansions (cells of abstract nodes) for the overlay.</summary>
        public readonly List<int> LastAbstractOrder = new List<int>();
        /// <summary>Path cost before smoothing (equals the result cost when smoothing is off).</summary>
        public double LastRawCost { get; private set; }
        /// <summary>Look-ahead of the smoothing pass in cells (a few clusters).</summary>
        public int SmoothWindow => 3 * C;

        public void Query(int s, int t, SearchResult r, bool smooth = false)
        {
            r.Clear(Algo.Hpa);
            if (!Built) BuildAll();
            sw.Restart(); LastAbstractOrder.Clear();
            if (Map.Free(s) && Map.Free(t)) QueryInner(s, t, r);
            LastRawCost = r.Cost;
            if (smooth && r.Found) r.Cost = Smooth(r.Path, ref r.Scanned);
            sw.Stop(); r.Ms = sw.Elapsed.TotalMilliseconds;
            r.Order?.AddRange(LastAbstractOrder);
        }
        public double Smooth(List<int> path, ref int scanned) => smoother.Smooth(path, SmoothWindow, ref scanned);

        private void QueryInner(int s, int t, SearchResult r)
        {
            qt = t; ks = ClusterOf(s); kt = ClusterOf(t);
            var cs = Clusters[ks]; var ct = Clusters[kt];
            Ensure(ref sDist, cs.Nodes.Length); Ensure(ref tDist, ct.Nodes.Length);
            r.Scanned += local.Dijkstra(cs, s);
            for (int j = 0; j < cs.Nodes.Length; j++) sDist[j] = local.DistTo(cs.Nodes[j]);
            stDirect = ks == kt ? local.DistTo(t) : GridMap.Inf;
            r.Scanned += local.Dijkstra(ct, t);
            for (int j = 0; j < ct.Nodes.Length; j++) tDist[j] = local.DistTo(ct.Nodes[j]);

            var sp = abs; sp.Begin();
            sp.Touch(s, 0, -1); r.Touched++;
            sp.Heap.Push(s, Map.CellDist(s, t), 0);
            while (sp.Heap.Count > 0)
            {
                int u = sp.Heap.Pop(out _);
                if (sp.Closed(u)) continue;
                sp.Close(u); r.Expanded++; LastAbstractOrder.Add(u);
                if (u == t) break;
                double gu = sp.G[u]; int ku = ClusterOf(u); var cl = Clusters[ku];
                int li = Array.BinarySearch(cl.Nodes, u);
                if (u == s)
                {
                    for (int j = 0; j < cs.Nodes.Length; j++) Relax(sp, u, cs.Nodes[j], gu + sDist[j], r);
                    if (!double.IsInfinity(stDirect)) Relax(sp, u, t, gu + stDirect, r);
                }
                if (li < 0) continue;
                int n = cl.Nodes.Length;
                for (int j = 0; j < n; j++)
                {
                    if (j == li) continue;
                    double d = cl.Dist[li * n + j];
                    if (!double.IsInfinity(d)) Relax(sp, u, cl.Nodes[j], gu + d, r);
                }
                foreach (int p in cl.Partners[li]) Relax(sp, u, p, gu + 1, r);
                if (ku == kt && !double.IsInfinity(tDist[li])) Relax(sp, u, t, gu + tDist[li], r);
            }
            if (!sp.Closed(t)) return;

            var key = r.KeyNodes;
            for (int c = t; c >= 0; c = sp.Parent[c]) key.Add(c);
            key.Reverse();
            r.Path.Add(key[0]);
            for (int i = 1; i < key.Count; i++)
            {
                int a = key[i - 1], b = key[i], ka = ClusterOf(a);
                if (ka != ClusterOf(b)) { r.Path.Add(b); continue; } // inter-edge: adjacent cells across a border
                r.Scanned += local.AStar(Clusters[ka], a, b, r.Path);
            }
            r.Found = true; r.Cost = sp.G[t];
        }
        private void Relax(SearchSpace sp, int u, int v, double ng, SearchResult r)
        {
            if (sp.Closed(v)) return;
            bool seen = sp.Seen(v);
            if (seen && ng >= sp.G[v] - 1e-12) return;
            if (!seen) r.Touched++;
            sp.Touch(v, ng, u);
            sp.Heap.Push(v, ng + Map.CellDist(v, qt), ng);
        }
        private static void Ensure(ref double[] a, int n) { if (a.Length < n) a = new double[Math.Max(n, a.Length * 2)]; }

        public string Describe() => $"{CW}x{CH} clusters of {C}², {NodeCount} nodes, {EdgeCount} edges";
    }

    /// <summary>Dijkstra / A* restricted to one cluster's rectangle on small local arrays (intra-edges, insertion, refinement).</summary>
    public sealed class LocalSearch
    {
        private readonly GridMap m;
        private readonly double[] g;
        private readonly int[] parent, seen, closed;
        private int gen, w;
        private readonly MinHeap heap = new MinHeap();
        private Hpa.Cluster cl;

        public LocalSearch(GridMap map, int c)
        {
            m = map; int cap = c * c;
            g = new double[cap]; parent = new int[cap]; seen = new int[cap]; closed = new int[cap];
        }
        private int L(int cell) => (m.Y(cell) - cl.Y0) * w + (m.X(cell) - cl.X0);
        private int Cell(int l) => m.Index(cl.X0 + l % w, cl.Y0 + l / w);
        private bool Inside(int x, int y) => x >= cl.X0 && x <= cl.X1 && y >= cl.Y0 && y <= cl.Y1;
        private void Begin(Hpa.Cluster c) { cl = c; w = c.X1 - c.X0 + 1; gen++; heap.Clear(); }
        public double DistTo(int cell) { int l = L(cell); return closed[l] == gen ? g[l] : GridMap.Inf; }

        /// <summary>Full Dijkstra from a cell inside the cluster. Returns cells expanded.</summary>
        public int Dijkstra(Hpa.Cluster c, int from) => Search(c, from, -1, null);
        /// <summary>A* inside the cluster from a to b; appends the cells after a (through b) to path.</summary>
        public int AStar(Hpa.Cluster c, int a, int b, List<int> path) => Search(c, a, b, path);

        private int Search(Hpa.Cluster c, int from, int to, List<int> path)
        {
            Begin(c);
            int ls = L(from), lt = to < 0 ? -1 : L(to), bx = to < 0 ? 0 : m.X(to), by = to < 0 ? 0 : m.Y(to);
            seen[ls] = gen; g[ls] = 0; parent[ls] = -1;
            heap.Push(ls, to < 0 ? 0 : m.CellDist(from, to), 0);
            int expanded = 0;
            while (heap.Count > 0)
            {
                int u = heap.Pop(out _);
                if (closed[u] == gen) continue;
                closed[u] = gen; expanded++;
                if (u == lt) break;
                int ux = cl.X0 + u % w, uy = cl.Y0 + u / w; double gu = g[u];
                for (int d = 0; d < 8; d++)
                {
                    int nx = ux + GridMap.DX[d], ny = uy + GridMap.DY[d];
                    if (!Inside(nx, ny) || !m.CanMove(ux, uy, d)) continue;
                    int v = (ny - cl.Y0) * w + (nx - cl.X0);
                    if (closed[v] == gen) continue;
                    double ng = gu + GridMap.StepCost[d];
                    if (seen[v] == gen && ng >= g[v] - 1e-12) continue;
                    seen[v] = gen; g[v] = ng; parent[v] = u;
                    heap.Push(v, to < 0 ? ng : ng + GridMap.Octile(nx - bx, ny - by), to < 0 ? -ng : ng);
                }
            }
            if (to < 0 || closed[lt] != gen) return expanded;
            int start = path.Count;
            for (int k = lt; k != ls; k = parent[k]) path.Add(Cell(k));
            path.Reverse(start, path.Count - start);
            return expanded;
        }
    }

    /// <summary>
    /// Shortcut smoothing (the HPA* paper's post-processing, adapted to octile costs): from each path cell look up to
    /// <c>window</c> cells ahead (farthest first) for a cell that a canonical octile line (diagonal+straight or
    /// straight+diagonal) reaches more cheaply with every move legal, and splice it in. Never increases cost.
    /// </summary>
    public sealed class PathSmoother
    {
        private readonly GridMap map;
        private readonly List<int> output = new List<int>(), seg = new List<int>();
        private double[] prefix = new double[256];
        public PathSmoother(GridMap m) { map = m; }

        public double Smooth(List<int> path, int window, ref int scanned)
        {
            int n = path.Count;
            if (n < 3) return GridMap.PathCost(map, path);
            if (prefix.Length < n) prefix = new double[Math.Max(n, prefix.Length * 2)];
            prefix[0] = 0;
            for (int i = 1; i < n; i++) prefix[i] = prefix[i - 1] + (map.X(path[i]) != map.X(path[i - 1]) && map.Y(path[i]) != map.Y(path[i - 1]) ? GridMap.Sqrt2 : 1);
            output.Clear(); output.Add(path[0]);
            int at = 0;
            while (at < n - 1)
            {
                int next = at + 1;
                for (int j = Math.Min(n - 1, at + window); j >= at + 2; j--)
                {
                    if (map.CellDist(path[at], path[j]) >= prefix[j] - prefix[at] - 1e-9) continue;
                    if (OctileLine(path[at], path[j], true, ref scanned) || OctileLine(path[at], path[j], false, ref scanned)) { next = j; break; }
                }
                if (next == at + 1) output.Add(path[next]); else output.AddRange(seg);
                at = next;
            }
            path.Clear(); path.AddRange(output);
            return GridMap.PathCost(map, path);
        }

        private bool OctileLine(int a, int b, bool diagonalFirst, ref int scanned)
        {
            seg.Clear();
            int x = map.X(a), y = map.Y(a), bx = map.X(b), by = map.Y(b);
            int sx = Math.Sign(bx - x), sy = Math.Sign(by - y), ddx = Math.Abs(bx - x), ddy = Math.Abs(by - y);
            int diag = Math.Min(ddx, ddy), straight = Math.Max(ddx, ddy) - diag;
            int dDiag = GridMap.DirOf(sx, sy), dStr = ddx > ddy ? GridMap.DirOf(sx, 0) : GridMap.DirOf(0, sy);
            for (int phase = 0; phase < 2; phase++)
            {
                bool doDiag = (phase == 0) == diagonalFirst;
                int count = doDiag ? diag : straight, d = doDiag ? dDiag : dStr;
                for (int k = 0; k < count; k++)
                {
                    scanned++;
                    if (!map.CanMove(x, y, d)) return false;
                    x += GridMap.DX[d]; y += GridMap.DY[d];
                    seg.Add(map.Index(x, y));
                }
            }
            return true;
        }
    }
}
