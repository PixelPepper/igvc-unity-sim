using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace IGVC.Reference.Pathfinding
{
    /// <summary>
    /// Facade the Reference Lab UI drives: one occupancy raster of the WORLD course, the selected planner, its last
    /// result (with expansion order for the overlay), the benchmark, and incremental course edits. Reference only
    /// (full course knowledge) - never autonomy. Costs reported in metres = cells × grid cell size.
    /// </summary>
    public sealed class PathfindingStudy
    {
        public OccupancyGrid Grid;
        public GridMap Map;
        public int Start, Goal;
        public Algo Algorithm = Algo.Hpa;
        public int ClusterSize = 16;
        public bool Smooth = true;
        public double Weight = 1.5;
        public SearchResult Last;
        public Hpa Hpa;
        public GridSearch Search { get; private set; }
        public FlowField Field { get; private set; }
        /// <summary>Last path before smoothing (equals Last.Path when smoothing is off or changed nothing).</summary>
        public readonly List<int> RawPath = new List<int>();
        public double RawCost = GridMap.Inf;
        /// <summary>Cells scanned by the last JPS jumps (overlay).</summary>
        public readonly List<int> JumpScans = new List<int>();
        /// <summary>Optimal start→goal cost in cells (A*), Inf when unknown or unreachable.</summary>
        public double OptimalCost = GridMap.Inf;
        public double SmoothMs;
        /// <summary>Bumped by every Run/Replace/Benchmark so views can cache.</summary>
        public int Revision;
        public int LastEditClusters = -1;
        public double LastEditMs;
        private readonly Dictionary<int, Hpa> hpas = new Dictionary<int, Hpa>();
        private PathSmoother smoother;
        private PathBenchmark bench;

        public PathfindingStudy(OccupancyGrid grid) { Init(grid); }

        private void Init(OccupancyGrid grid)
        {
            Grid = grid; Map = GridMap.FromOccupancy(grid); Start = grid.StartCell; Goal = grid.GoalCell;
            Search = new GridSearch(Map); Field = new FlowField(Map); smoother = new PathSmoother(Map);
            hpas.Clear(); Hpa = null; bench = null; Reset();
        }
        private void Reset() { Last = null; RawPath.Clear(); RawCost = GridMap.Inf; JumpScans.Clear(); OptimalCost = GridMap.Inf; SmoothMs = 0; Revision++; }

        /// <summary>HPA* abstraction for a cluster size, created lazily (built on first use).</summary>
        public Hpa HpaFor(int cluster)
        {
            if (!hpas.TryGetValue(cluster, out var h)) { h = new Hpa(Map, cluster); hpas[cluster] = h; }
            return h;
        }

        public double Metres(double cells) => cells * Grid.Cell;
        public static string Label(Algo a)
        {
            switch (a)
            {
                case Algo.AStar: return "A*";
                case Algo.WeightedAStar: return "Weighted A*";
                case Algo.BidirAStar: return "Bidirectional A*";
                case Algo.Jps: return "JPS";
                case Algo.Hpa: return "HPA*";
                case Algo.FlowField: return "Flow field";
                default: return "Dijkstra";
            }
        }

        /// <summary>
        /// Optimal reference (A*), then the HPA* build if needed (time-sliced, <paramref name="workPerStep"/> clusters per
        /// step), then the selected query with its expansion order recorded. Yields a short status line per step.
        /// </summary>
        public IEnumerable<string> Run(int workPerStep = 64)
        {
            Reset();
            if (!Map.Free(Start) || !Map.Free(Goal)) { Last = new SearchResult { Order = new List<int>() }; Last.Clear(Algorithm); yield return "start or goal cell is blocked"; yield break; }
            var reference = new SearchResult();
            Search.Run(Algo.AStar, Start, Goal, reference);
            OptimalCost = reference.Found ? reference.Cost : GridMap.Inf;
            yield return reference.Found ? $"optimum {Metres(reference.Cost):0.00} m (A*)" : "no path exists";
            if (Algorithm == Algo.Hpa)
            {
                Hpa = HpaFor(ClusterSize);
                if (!Hpa.Built) foreach (int k in Hpa.BuildSteps(workPerStep)) yield return $"building HPA* C{Hpa.C}: {k + 1}/{Hpa.Clusters.Length} clusters";
            }
            var r = new SearchResult { Order = new List<int>() };
            Search.Weight = Weight;
            switch (Algorithm)
            {
                case Algo.Hpa: Hpa.Query(Start, Goal, r); break;
                case Algo.FlowField: Field.Invalidate(); Field.Query(Start, Goal, r); break;
                case Algo.Jps: Search.ScanLog = JumpScans; Search.Run(Algo.Jps, Start, Goal, r); Search.ScanLog = null; break;
                default: Search.Run(Algorithm, Start, Goal, r); break;
            }
            RawPath.AddRange(r.Path); RawCost = r.Cost;
            if (Smooth && r.Found)
            {
                var sw = Stopwatch.StartNew();
                r.Cost = smoother.Smooth(r.Path, 3 * ClusterSize, ref r.Scanned);
                sw.Stop(); SmoothMs = sw.Elapsed.TotalMilliseconds; r.Ms += SmoothMs;
            }
            Last = r; Revision++;
            yield return r.Found ? $"{Label(r.Algo)}: {Metres(r.Cost):0.00} m, {r.Expanded} expanded" : $"{Label(r.Algo)}: no path";
        }

        /// <summary>PathBenchmark over the default entries (seeded pairs); yields progress every few searches.</summary>
        public IEnumerable<string> Benchmark(int pairs, int seed)
        {
            Search.Weight = Weight;
            bench = new PathBenchmark(Map, Search, Field, HpaFor, PathBenchmark.DefaultEntries(Weight), pairs, seed, false);
            int n = 0;
            foreach (int _ in bench.Steps()) if (++n % 4 == 0) yield return $"benchmark {bench.Done}/{bench.Pairs} queries";
            Field.Invalidate(); Revision++;
            yield return $"benchmark done in {bench.TotalMs / 1000:0.0} s";
        }
        public IReadOnlyList<BenchRow> Rows => bench == null ? (IReadOnlyList<BenchRow>)new BenchRow[0] : bench.Rows;
        public PathBenchmark Bench => bench;

        /// <summary>Last path as world cell centres, start→goal (smoothed when <see cref="Smooth"/>).</summary>
        public List<V2> Route() => Centres(Last == null ? null : Last.Path);
        public List<V2> Centres(IList<int> cells)
        {
            var o = new List<V2>();
            if (cells != null) foreach (int c in cells) o.Add(Grid.CellCenter(c));
            return o;
        }

        /// <summary>
        /// Course edit: diff the blocked cells, repair every built HPA* incrementally over the changed bounding box (equal
        /// to a full rebuild), invalidate the flow field and results. A different raster layout rebuilds everything.
        /// </summary>
        public void Replace(OccupancyGrid next)
        {
            if (next.W != Grid.W || next.H != Grid.H || next.Cell != Grid.Cell || next.X0 != Grid.X0 || next.Y0 != Grid.Y0) { Init(next); return; }
            var changed = new List<int>();
            for (int i = 0; i < next.Code.Length; i++)
            {
                byte b = next.Code[i] == OccupancyGrid.Free ? (byte)0 : (byte)1;
                if (b != Map.Blocked[i]) { Map.Blocked[i] = b; changed.Add(i); }
            }
            Grid = next; Start = next.StartCell; Goal = next.GoalCell; bench = null;
            LastEditClusters = 0; LastEditMs = 0;
            if (changed.Count > 0)
            {
                Map.Version++; Field.Invalidate();
                foreach (var h in hpas.Values)
                {
                    if (!h.Built) continue; // a partial build restarts from scratch on next use
                    // One bounding box per touched cluster tile, so two distant edits don't repair everything between them.
                    var boxes = new SortedDictionary<int, int[]>();
                    foreach (int i in changed)
                    {
                        int x = Map.X(i), y = Map.Y(i), k = h.ClusterOf(i);
                        if (!boxes.TryGetValue(k, out var bb)) boxes[k] = new[] { x, y, x, y };
                        else { bb[0] = Math.Min(bb[0], x); bb[1] = Math.Min(bb[1], y); bb[2] = Math.Max(bb[2], x); bb[3] = Math.Max(bb[3], y); }
                    }
                    int clusters = 0; double ms = 0;
                    foreach (var bb in boxes.Values) { h.Update(bb[0], bb[1], bb[2], bb[3]); clusters += h.LastUpdateClusters; ms += h.LastUpdateMs; }
                    if (h == Hpa) { LastEditClusters = clusters; LastEditMs = ms; }
                }
            }
            Reset();
        }

        public string[] Summary()
        {
            var s = new List<string>();
            if (Last == null) { s.Add("no result yet"); return s.ToArray(); }
            string name = Label(Last.Algo) + (Last.Algo == Algo.Hpa && Hpa != null ? " C" + Hpa.C : Last.Algo == Algo.WeightedAStar ? " w" + Weight.ToString("0.##") : "") + (Smooth ? " + smoothing" : "");
            s.Add(Last.Found ? $"{name}: {Metres(Last.Cost):0.00} m" : $"{name}: no path");
            s.Add($"expanded {Last.Expanded}, scanned {Last.Scanned}, touched {Last.Touched}");
            s.Add($"query {Last.Ms:0.00} ms" + (Smooth && Last.Found ? $" (smoothing {SmoothMs:0.00} ms, raw {Metres(RawCost):0.00} m)" : ""));
            if (Last.Algo == Algo.Hpa && Hpa != null) s.Add($"HPA* {Hpa.CW}x{Hpa.CH} clusters, {Hpa.NodeCount} nodes, {Hpa.EdgeCount} edges, build {Hpa.BuildMs:0} ms");
            if (Last.Algo == Algo.Jps) s.Add($"{Last.KeyNodes.Count} jump points on the path, {JumpScans.Count} cells scanned");
            if (Last.Found && !double.IsInfinity(OptimalCost)) s.Add($"gap vs A* optimum ({Metres(OptimalCost):0.00} m): {(OptimalCost > 0 ? (Last.Cost - OptimalCost) / OptimalCost * 100 : 0):0.00} %");
            if (LastEditClusters >= 0) s.Add($"last edit: {LastEditClusters} clusters rebuilt in {LastEditMs:0.0} ms");
            return s.ToArray();
        }
    }
}
