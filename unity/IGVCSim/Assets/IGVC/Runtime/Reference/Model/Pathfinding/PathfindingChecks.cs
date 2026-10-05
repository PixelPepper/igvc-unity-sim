using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace IGVC.Reference.Pathfinding
{
    /// <summary>Behavioural checks: optimality vs Dijkstra, HPA* completeness/bound/incremental update, real-course lap.</summary>
    public static class PathfindingChecks
    {
        private static readonly MapPreset[] Presets = { MapPreset.City, MapPreset.Cave, MapPreset.Maze, MapPreset.Rooms, MapPreset.Scatter, MapPreset.Traps, MapPreset.Empty };

        public static void Run(CheckContext c)
        {
            var watch = Stopwatch.StartNew();
            Presets_(c);
            Optimal(c);
            Corner(c);
            HpaBound(c);
            Incremental(c);
            Benchmarks(c);
            Course(c, new Corridor(SyntheticCourses.Stadium(obstacles: new[] { SyntheticCourses.Barrel("b1", 5, 0), SyntheticCourses.Barrel("b2", -4, 16.8) })), "stadium");
            StudyReplace(c);
            if (c.Course != null) Course(c, new Corridor(c.Course), "real course");
            else c.Note("no frozen course; real-course pathfinding checks skipped");
            c.Note($"pathfinding checks took {watch.Elapsed.TotalSeconds:0.0} s");
        }

        private static GridMap Make(MapPreset p, int size, int seed) { var m = new GridMap(size, size); MapPresets.Generate(m, p, seed); return m; }

        private static List<(int s, int t)> Pairs(GridMap m, int n, int seed, bool connectedOnly = true, double minDist = 0)
        {
            var rng = new GridRng((ulong)seed); var label = new int[m.Count]; m.Components(label);
            var free = new List<int>();
            for (int i = 0; i < m.Count; i++) if (m.Free(i)) free.Add(i);
            var list = new List<(int, int)>();
            for (int guard = 0; list.Count < n && guard < n * 50 && free.Count > 0; guard++)
            {
                int s = free[rng.Range(free.Count)], t = free[rng.Range(free.Count)];
                if ((connectedOnly && label[s] != label[t]) || m.CellDist(s, t) < minDist) continue;
                list.Add((s, t));
            }
            return list;
        }

        private static void Presets_(CheckContext c)
        {
            bool ok = true; string why = "";
            foreach (var p in Presets)
            {
                var a = Make(p, 128, 5); var b = Make(p, 128, 5); var d = Make(p, 128, 6);
                double free = a.FreeCount() / (double)a.Count;
                if (!Same(a.Blocked, b.Blocked)) { ok = false; why = p + " not deterministic"; }
                if (a.Components(new int[a.Count]) != 1) { ok = false; why = p + " not one component"; }
                if (p != MapPreset.Empty && (free < .25 || free > .95 || Same(a.Blocked, d.Blocked))) { ok = false; why = p + " trivial or seed-independent"; }
            }
            c.Check(ok, "synthetic map presets deterministic, connected, seed-dependent " + why);
        }
        private static bool Same(byte[] a, byte[] b) { for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false; return true; }

        private static void Optimal(CheckContext c)
        {
            int pairs = 0; string fail = null; double worstW = 1;
            foreach (var p in Presets)
                for (int seed = 1; seed <= 2 && fail == null; seed++)
                {
                    var m = Make(p, 128, seed); var gs = new GridSearch(m) { Weight = 1.5 }; var ff = new FlowField(m);
                    var dj = new SearchResult(); var r = new SearchResult();
                    foreach (var (s, t) in Pairs(m, 25, seed * 31 + (int)p))
                    {
                        gs.Run(Algo.Dijkstra, s, t, dj);
                        if (!dj.Found || m.ValidatePath(dj.Path, s, t, out double dc) != null || Math.Abs(dc - dj.Cost) > 1e-6) { fail = $"{p}/{seed}: Dijkstra path invalid"; break; }
                        foreach (var a in new[] { Algo.AStar, Algo.BidirAStar, Algo.Jps, Algo.FlowField, Algo.WeightedAStar })
                        {
                            if (a == Algo.FlowField) ff.Query(s, t, r); else gs.Run(a, s, t, r);
                            double walked = 0;
                            string v = r.Found ? m.ValidatePath(r.Path, s, t, out walked) : "not found";
                            if (v == null && Math.Abs(walked - r.Cost) > 1e-6) v = "reported cost != walked cost";
                            if (v == null && a != Algo.WeightedAStar && Math.Abs(r.Cost - dj.Cost) > 1e-6) v = $"cost {r.Cost} vs optimum {dj.Cost}";
                            if (v == null && a == Algo.WeightedAStar && (r.Cost > 1.5 * dj.Cost + 1e-6 || r.Cost < dj.Cost - 1e-6)) v = "outside [1, w] bound";
                            if (v != null) { fail = $"{a} on {p}/{seed} {m.X(s)},{m.Y(s)}->{m.X(t)},{m.Y(t)}: {v}"; break; }
                            if (a == Algo.WeightedAStar && dj.Cost > 0) worstW = Math.Max(worstW, r.Cost / dj.Cost);
                        }
                        if (fail != null) break;
                        pairs++;
                    }
                }
            c.Check(fail == null, $"A*, bidirectional A*, JPS, flow field equal Dijkstra and WA*(1.5) within bound on {pairs} pairs over 7 presets x 2 seeds " + fail);
            c.Note($"weighted A* 1.5 worst ratio {worstW:0.000}");

            var empty = new GridMap(200, 200); var g2 = new GridSearch(empty); var j = new SearchResult(); var astar = new SearchResult();
            g2.Run(Algo.Jps, empty.Index(0, 0), empty.Index(199, 150), j); g2.Run(Algo.AStar, empty.Index(0, 0), empty.Index(199, 150), astar);
            c.Check(Math.Abs(j.Cost - GridMap.Octile(199, 150)) < 1e-6 && j.Expanded <= 4 && astar.Expanded > 150, $"JPS on an empty grid expands {j.Expanded} jump points (A* {astar.Expanded})");
        }

        private static void Corner(CheckContext c)
        {
            var m = new GridMap(16, 16);
            MapPresets.Rect(m, 0, 0, 7, 7, true); MapPresets.Rect(m, 8, 8, 15, 15, true);
            var gs = new GridSearch(m); var r = new SearchResult(); bool none = true;
            foreach (var a in new[] { Algo.Dijkstra, Algo.AStar, Algo.BidirAStar, Algo.Jps }) { gs.Run(a, m.Index(2, 12), m.Index(12, 2), r); none &= !r.Found; }
            var h = new Hpa(m, 4); h.Query(m.Index(2, 12), m.Index(12, 2), r); none &= !r.Found;
            c.Check(none && !m.CanMove(7, 8, 7), "no algorithm squeezes through a diagonal corner gap");

            var box = new GridMap(64, 64);
            MapPresets.Rect(box, 40, 40, 50, 40, true); MapPresets.Rect(box, 40, 50, 50, 50, true); MapPresets.Rect(box, 40, 40, 40, 50, true); MapPresets.Rect(box, 50, 40, 50, 50, true);
            int s = box.Index(3, 3), t = box.Index(45, 45); var g2 = new GridSearch(box); bool invented = false;
            foreach (var a in new[] { Algo.Dijkstra, Algo.AStar, Algo.WeightedAStar, Algo.BidirAStar, Algo.Jps }) { g2.Run(a, s, t, r); invented |= r.Found || r.Path.Count > 0; }
            var hb = new Hpa(box, 16); hb.Query(s, t, r); invented |= r.Found;
            new FlowField(box).Query(s, t, r); invented |= r.Found;
            c.Check(!invented, "unreachable goal: no algorithm (incl. HPA*, flow field) invents a path");
        }

        /// <summary>Stated sandbox bound: pairs ≥ 48 cells apart, mean gap ≤ 10 %, worst ≤ 25 % (C32: 35 %); smoothed mean ≤ 2 %, worst ≤ 20 %.</summary>
        private static void HpaBound(CheckContext c)
        {
            foreach (int cluster in new[] { 8, 16, 32 })
            {
                double worst = 0, sum = 0, worstS = 0, sumS = 0; int n = 0; string fail = null;
                foreach (var p in Presets)
                {
                    var m = Make(p, 256, 2); var gs = new GridSearch(m); var h = new Hpa(m, cluster); h.BuildAll();
                    var dj = new SearchResult(); var r = new SearchResult();
                    foreach (var (s, t) in Pairs(m, 20, 11 + cluster + (int)p, minDist: 48))
                    {
                        gs.Run(Algo.Dijkstra, s, t, dj); h.Query(s, t, r);
                        if (dj.Found != r.Found) { fail = $"{p}: complete"; break; }
                        string v = m.ValidatePath(r.Path, s, t, out double walked);
                        if (v != null || Math.Abs(walked - r.Cost) > 1e-6 || r.Cost < dj.Cost - 1e-6) { fail = $"{p}: refined path {v ?? "cost mismatch"}"; break; }
                        double gap = dj.Cost > 0 ? (r.Cost - dj.Cost) / dj.Cost : 0;
                        h.Query(s, t, r, smooth: true);
                        v = m.ValidatePath(r.Path, s, t, out double ws);
                        if (v != null || Math.Abs(ws - r.Cost) > 1e-6 || r.Cost > h.LastRawCost + 1e-9) { fail = $"{p}: smoothing {v ?? "lengthened or cost mismatch"}"; break; }
                        double gapS = dj.Cost > 0 ? (r.Cost - dj.Cost) / dj.Cost : 0;
                        worst = Math.Max(worst, gap); sum += gap; worstS = Math.Max(worstS, gapS); sumS += gapS; n++;
                    }
                    if (fail != null) break;
                }
                double worstBound = cluster >= 32 ? .35 : .25;
                c.Check(fail == null && n > 100 && sum / n <= .10 && worst <= worstBound && sumS / n <= .02 && worstS <= .20,
                    $"HPA* C{cluster} complete, valid, mean gap {sum / Math.Max(1, n):P2} (<=10%), worst {worst:P1} (<={worstBound:P0}); smoothed mean {sumS / Math.Max(1, n):P2} (<=2%), worst {worstS:P1} (<=20%), {n} queries " + fail);
            }
        }

        private static void Incremental(CheckContext c)
        {
            var rng = new GridRng(4242);
            foreach (int cluster in new[] { 8, 16 })
            {
                var m = Make(MapPreset.City, 128, 9); var inc = new Hpa(m, cluster); inc.BuildAll();
                string diff = null; int maxRebuilt = 0;
                for (int edit = 1; edit <= 120 && diff == null; edit++)
                {
                    int x = rng.Range(m.W), y = rng.Range(m.H), r = rng.Range(0, 4);
                    if (edit % 4 == 0) { x = rng.Range(1, m.W / cluster) * cluster - rng.Range(2); y = rng.Range(1, m.H / cluster) * cluster - rng.Range(2); }
                    bool block = rng.Chance(.55);
                    for (int yy = y - r; yy <= y + r; yy++) for (int xx = x - r; xx <= x + r; xx++) m.Set(xx, yy, block);
                    inc.Update(x - r, y - r, x + r, y + r);
                    maxRebuilt = Math.Max(maxRebuilt, inc.LastUpdateClusters);
                    if (edit % 10 == 0 || edit == 1) { var full = new Hpa(m, cluster); full.BuildAll(); diff = inc.DiffFrom(full); if (diff != null) diff = $"edit {edit}: {diff}"; }
                }
                var gs = new GridSearch(m); var a = new SearchResult(); var q = new SearchResult(); bool complete = true;
                foreach (var (s, t) in Pairs(m, 30, 5, connectedOnly: false))
                {
                    gs.Run(Algo.Dijkstra, s, t, a); inc.Query(s, t, q);
                    complete &= a.Found == q.Found && (!q.Found || m.ValidatePath(q.Path, s, t, out _) == null);
                }
                c.Check(diff == null && complete && maxRebuilt < inc.Clusters.Length / 4,
                    $"HPA* C{cluster}: 120 random edits, incremental Update == full rebuild, still complete (max {maxRebuilt}/{inc.Clusters.Length} clusters per edit) " + diff);
            }
        }

        private static void Benchmarks(CheckContext c)
        {
            string[] Run(int seed)
            {
                var m = Make(MapPreset.City, 128, 1); var gs = new GridSearch(m); var ff = new FlowField(m); var hs = new Dictionary<int, Hpa>();
                Hpa For(int k) { if (!hs.TryGetValue(k, out var h)) hs[k] = h = new Hpa(m, k); return h; }
                var b = new PathBenchmark(m, gs, ff, For, PathBenchmark.DefaultEntries(), 24, seed, false); b.RunAll();
                var sig = new List<string>();
                foreach (var row in b.Rows) sig.Add(row.Signature());
                bool ok = b.Finished;
                foreach (var row in b.Rows)
                {
                    ok &= row.Wrong == 0 && row.Queries == 24;
                    if (row.Entry.Algo != Algo.Hpa && row.Entry.Algo != Algo.WeightedAStar) ok &= row.Found == 24 && row.MaxGap < 1e-6;
                    if (row.Entry.Algo == Algo.Hpa) ok &= row.AvgGap < 10;
                }
                BenchRow R(string n) => b.Rows.Find(x => x.Entry.Name == n);
                ok &= R("JPS").AvgExpanded < R("A*").AvgExpanded && R("A*").AvgExpanded < R("Dijkstra").AvgExpanded && R("HPA* C16").AvgExpanded < R("A*").AvgExpanded;
                sig.Add(ok ? "ok" : "BAD");
                return sig.ToArray();
            }
            var x1 = Run(77); var x2 = Run(77); var x3 = Run(78);
            c.Check(x1[x1.Length - 1] == "ok", "benchmark: optimal solvers zero gap, reachability agrees, JPS < A* < Dijkstra and HPA* < A* expansions");
            c.Check(string.Join(";", x1) == string.Join(";", x2) && string.Join(";", x1) != string.Join(";", x3), "benchmark rows identical for the same seed (timings excluded), different for another");
        }

        private static IEnumerable<string> Drain(IEnumerable<string> steps) { var l = new List<string>(); foreach (var s in steps) l.Add(s); return l; }

        /// <summary>Start→goal on a rasterised course is one lap: every algorithm agrees on the optimum, HPA* is near it.</summary>
        private static void Course(CheckContext c, Corridor corridor, string name)
        {
            var grid = Rasterizer.Rasterize(corridor, corridor.Course.Shapes());
            var study = new PathfindingStudy(grid);
            var lines = new List<string>(); double optimum = GridMap.Inf; string fail = null; double hpaGap = 0, smoothM = 0;
            foreach (var a in new[] { Algo.Dijkstra, Algo.AStar, Algo.WeightedAStar, Algo.BidirAStar, Algo.Jps, Algo.FlowField, Algo.Hpa })
            {
                study.Algorithm = a; study.Smooth = false; Drain(study.Run());
                var r = study.Last;
                string v = r.Found ? study.Map.ValidatePath(r.Path, study.Start, study.Goal, out _) : "no path";
                if (v == null) foreach (int cell in r.Path) if (grid.Code[cell] != OccupancyGrid.Free) { v = "enters a non-free cell"; break; }
                if (a == Algo.Dijkstra) optimum = r.Cost;
                else if (v == null && a != Algo.Hpa && a != Algo.WeightedAStar && Math.Abs(r.Cost - optimum) > 1e-6) v = $"cost {r.Cost} vs Dijkstra {optimum}";
                if (a == Algo.Hpa) hpaGap = (r.Cost - optimum) / optimum;
                if (v != null) { fail = PathfindingStudy.Label(a) + ": " + v; break; }
                lines.Add($"{PathfindingStudy.Label(a)} exp {r.Expanded} scan {r.Scanned} {r.Ms:0.0} ms");
            }
            study.Algorithm = Algo.Hpa; study.Smooth = true; Drain(study.Run());
            smoothM = study.Metres(study.Last.Cost);
            bool smoothOk = study.Last.Found && study.Map.ValidatePath(study.Last.Path, study.Start, study.Goal, out _) == null && study.Last.Cost <= study.RawCost + 1e-9;
            double lap = study.Metres(optimum);
            c.Check(fail == null && lap > .8 * corridor.Length && lap < 1.3 * corridor.Length,
                $"{name}: start->goal is one lap ({lap:0.0} m vs corridor {corridor.Length:0.0} m), all optimal algorithms agree, paths stay in free cells " + fail);
            c.Check(hpaGap >= -1e-9 && hpaGap <= .25 && smoothOk, $"{name}: HPA* C16 gap {hpaGap:P2} (<=25%), smoothed {smoothM:0.00} m valid and not longer");
            var route = study.Route();
            c.Check(route.Count == study.Last.Path.Count && V2.Distance(route[0], grid.CellCenter(grid.StartCell)) < 1e-9, $"{name}: Route() returns world cell centres from the start");
            if (name == "real course") c.Note($"real course {corridor.Course.Identity}, grid {grid.W}x{grid.H}, lap {lap:0.00} m (corridor {corridor.Length:0.0} m), HPA* {study.Hpa.Describe()}, build {study.Hpa.BuildMs:0} ms: " + string.Join("; ", lines));
            if (name == "real course")
            {
                var bw = Stopwatch.StartNew(); Drain(study.Benchmark(6, 3));
                bool ok = true;
                foreach (var row in study.Rows) { ok &= row.Wrong == 0; if (row.Entry.Algo != Algo.Hpa && row.Entry.Algo != Algo.WeightedAStar) ok &= row.MaxGap < 1e-6; }
                c.Check(ok && study.Rows.Count == 10, $"real course: benchmark of 6 random pairs consistent ({bw.Elapsed.TotalSeconds:0.0} s)");
            }
        }

        /// <summary>A course edit (extra barrel) through Replace equals a fresh study built on the edited raster.</summary>
        private static void StudyReplace(CheckContext c)
        {
            var b1 = SyntheticCourses.Barrel("b1", 5, 0); var b2 = SyntheticCourses.Barrel("b2", -4, 16.8); var b3 = SyntheticCourses.Barrel("b3", 16.9, 4);
            var before = new Corridor(SyntheticCourses.Stadium(obstacles: new[] { b1, b2 }));
            var after = new Corridor(SyntheticCourses.Stadium(obstacles: new[] { b1, b3 }));
            var editedGrid = Rasterizer.Rasterize(after, after.Course.Shapes());
            var study = new PathfindingStudy(Rasterizer.Rasterize(before, before.Course.Shapes()));
            var algos = new[] { Algo.Hpa, Algo.AStar, Algo.Jps };
            foreach (var a in algos) { study.Algorithm = a; Drain(study.Run()); }
            study.ClusterSize = 8; study.Algorithm = Algo.Hpa; Drain(study.Run()); study.ClusterSize = 16;
            study.Replace(editedGrid);
            var fresh = new PathfindingStudy(editedGrid);
            bool same = study.LastEditClusters > 0 && study.LastEditClusters < study.Hpa.Clusters.Length / 2;
            string why = "";
            foreach (var a in algos)
            {
                study.Algorithm = fresh.Algorithm = a; Drain(study.Run()); Drain(fresh.Run());
                bool eq = study.Last.Found && fresh.Last.Found && study.Last.Cost == fresh.Last.Cost && study.Last.Path.Count == fresh.Last.Path.Count;
                for (int i = 0; eq && i < study.Last.Path.Count; i++) eq = study.Last.Path[i] == fresh.Last.Path[i];
                if (!eq) { same = false; why += PathfindingStudy.Label(a) + " differs; "; }
            }
            foreach (int k in new[] { 16, 8 }) { var d = study.HpaFor(k).DiffFrom(fresh.HpaFor(k).Built ? fresh.HpaFor(k) : Built(fresh.HpaFor(k))); if (d != null) { same = false; why += $"C{k}: {d}; "; } }
            c.Check(same, $"study Replace (moved barrel, {study.LastEditClusters} clusters repaired) equals a fresh study: same paths and HPA* abstraction " + why);
        }
        private static Hpa Built(Hpa h) { h.BuildAll(); return h; }
    }
}
