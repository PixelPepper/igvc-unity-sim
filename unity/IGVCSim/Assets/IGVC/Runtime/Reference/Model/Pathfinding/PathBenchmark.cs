using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace IGVC.Reference.Pathfinding
{
    /// <summary>One benchmark contender: an algorithm (+ cluster size / smoothing for HPA*).</summary>
    public sealed class BenchEntry
    {
        public string Name; public Algo Algo; public int Cluster; public bool Smooth;
        public BenchEntry(string name, Algo algo, int cluster = 0, bool smooth = false) { Name = name; Algo = algo; Cluster = cluster; Smooth = smooth; }
    }

    /// <summary>Aggregated measurements of one contender over all queries (costs in cells, gaps in percent).</summary>
    public sealed class BenchRow
    {
        public BenchEntry Entry;
        public int Queries, Found, Wrong, Optimal;
        public double SumExpanded, SumScanned, SumTouched, SumMs, SumCost, SumGap, MaxGap;
        public long MemoryBytes;
        public double PrepMs;
        public double AvgExpanded => Queries > 0 ? SumExpanded / Queries : 0;
        public double AvgScanned => Queries > 0 ? SumScanned / Queries : 0;
        public double AvgTouched => Queries > 0 ? SumTouched / Queries : 0;
        public double AvgMs => Queries > 0 ? SumMs / Queries : 0;
        public double AvgCost => Found > 0 ? SumCost / Found : 0;
        public double AvgGap => Found > 0 ? SumGap / Found : 0;
        /// <summary>Everything except timings, for determinism checks.</summary>
        public string Signature() => $"{Entry.Name}|{Queries}|{Found}|{Wrong}|{Optimal}|{SumExpanded}|{SumScanned}|{SumTouched}|{SumCost:R}|{SumGap:R}|{MaxGap:R}|{MemoryBytes}";
    }

    /// <summary>
    /// Many-query benchmark: seeded random start/goal pairs from the largest connected component (or a shared goal,
    /// the crowd case where a flow field pays off). A* gives each pair's optimum; every contender reports expansions,
    /// scanned cells, touched nodes, time, cost and optimality gap. <see cref="Steps"/> yields after every search.
    /// </summary>
    public sealed class PathBenchmark
    {
        public static List<BenchEntry> DefaultEntries(double weight = 1.5) => new List<BenchEntry>
        {
            new BenchEntry("Dijkstra", Algo.Dijkstra),
            new BenchEntry("A*", Algo.AStar),
            new BenchEntry("Weighted A* " + weight.ToString("0.##"), Algo.WeightedAStar),
            new BenchEntry("Bidir A*", Algo.BidirAStar),
            new BenchEntry("JPS", Algo.Jps),
            new BenchEntry("HPA* C8", Algo.Hpa, 8),
            new BenchEntry("HPA* C16", Algo.Hpa, 16),
            new BenchEntry("HPA* C32", Algo.Hpa, 32),
            new BenchEntry("HPA* C16+smooth", Algo.Hpa, 16, true),
            new BenchEntry("Flow field", Algo.FlowField),
        };

        public readonly GridMap Map;
        public readonly GridSearch Search;
        public readonly FlowField Field;
        public readonly Func<int, Hpa> HpaFor;
        public readonly List<BenchRow> Rows = new List<BenchRow>();
        public readonly int Pairs, Seed;
        public readonly bool SharedGoal;
        public int Done { get; private set; }
        public bool Finished { get; private set; }
        public double TotalMs { get; private set; }
        public readonly List<int> Starts = new List<int>(), Goals = new List<int>();
        private readonly SearchResult reference = new SearchResult(), result = new SearchResult();

        public PathBenchmark(GridMap map, GridSearch search, FlowField field, Func<int, Hpa> hpaFor, List<BenchEntry> entries, int pairs, int seed, bool sharedGoal)
        {
            Map = map; Search = search; Field = field; HpaFor = hpaFor; Pairs = pairs; Seed = seed; SharedGoal = sharedGoal;
            foreach (var e in entries) Rows.Add(new BenchRow { Entry = e });
            MakePairs();
        }

        private void MakePairs()
        {
            var rng = new GridRng((ulong)Seed);
            var label = new int[Map.Count];
            int comps = Map.Components(label);
            if (comps == 0) return;
            var size = new int[comps]; int best = 0;
            for (int i = 0; i < label.Length; i++) if (label[i] >= 0 && ++size[label[i]] > size[best]) best = label[i];
            var cells = new List<int>(size[best]);
            for (int i = 0; i < label.Length; i++) if (label[i] == best) cells.Add(i);
            // Minimum separation: a fifth of the map, capped by what the component can offer (thin course rings).
            double minD = Math.Min(Math.Max(Map.W, Map.H) / 5.0, Math.Sqrt(cells.Count));
            int shared = SharedGoal ? cells[rng.Range(cells.Count)] : -1;
            for (int k = 0; k < Pairs; k++)
            {
                int s = cells[rng.Range(cells.Count)], t = shared;
                for (int tries = 0; tries < 60; tries++)
                {
                    if (!SharedGoal) t = cells[rng.Range(cells.Count)];
                    if (Map.CellDist(s, t) >= minD) break;
                    if (SharedGoal) s = cells[rng.Range(cells.Count)];
                }
                Starts.Add(s); Goals.Add(t);
            }
        }

        public void RunAll() { foreach (var _ in Steps()) { } }

        public IEnumerable<int> Steps()
        {
            var total = Stopwatch.StartNew();
            // HPA* pre-processing is measured once, outside the per-query numbers.
            foreach (var row in Rows)
            {
                if (row.Entry.Algo != Algo.Hpa) continue;
                var h = HpaFor(row.Entry.Cluster);
                if (!h.Built) foreach (var _ in h.BuildSteps(64)) yield return 0;
                row.PrepMs = h.BuildMs; row.MemoryBytes = h.MemoryBytes;
                yield return 0;
            }
            for (int q = 0; q < Starts.Count; q++)
            {
                int s = Starts[q], t = Goals[q];
                Search.Run(Algo.AStar, s, t, reference);
                yield return q;
                foreach (var row in Rows)
                {
                    RunEntry(row.Entry, s, t, result);
                    row.Queries++; row.SumExpanded += result.Expanded; row.SumScanned += result.Scanned; row.SumTouched += result.Touched; row.SumMs += result.Ms;
                    if (row.Entry.Algo == Algo.FlowField) row.MemoryBytes = Field.MemoryBytes;
                    else if (row.Entry.Algo != Algo.Hpa) row.MemoryBytes = Math.Max(row.MemoryBytes, (long)result.Touched * 20);
                    if (result.Found != reference.Found) row.Wrong++;
                    if (result.Found && reference.Found)
                    {
                        row.Found++; row.SumCost += result.Cost;
                        double gap = reference.Cost > 0 ? (result.Cost - reference.Cost) / reference.Cost * 100.0 : 0;
                        if (gap < 1e-7) { gap = 0; row.Optimal++; }
                        row.SumGap += gap;
                        if (gap > row.MaxGap) row.MaxGap = gap;
                    }
                    yield return q;
                }
                Done = q + 1;
            }
            total.Stop(); TotalMs = total.Elapsed.TotalMilliseconds; Finished = true;
        }

        public void RunEntry(BenchEntry e, int s, int t, SearchResult r)
        {
            switch (e.Algo)
            {
                case Algo.Hpa: HpaFor(e.Cluster).Query(s, t, r, e.Smooth); break;
                case Algo.FlowField: Field.Query(s, t, r); break;
                default: Search.Run(e.Algo, s, t, r); break;
            }
        }
    }
}
