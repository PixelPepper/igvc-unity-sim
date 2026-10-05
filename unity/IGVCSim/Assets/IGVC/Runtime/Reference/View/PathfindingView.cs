using System;
using System.Collections.Generic;
using IGVC.Reference.Pathfinding;
using UnityEngine;

namespace IGVC.Reference
{
    /// <summary>
    /// Draws a <see cref="PathfindingStudy"/> on the reference layer: C-space grid, HPA* clusters / entrances / abstract
    /// graph, the expansion order as a heat ramp (revealed over ~4 s by <see cref="Animate"/>), raw and smoothed paths.
    /// Per-cell data goes into textures (SetGrid), never one quad per cell. Reference only - not autonomy.
    /// </summary>
    public sealed class PathfindingView
    {
        public bool ShowGrid = true, ShowClusters = true, ShowEntrances = true, ShowAbstractGraph = false, ShowExpansions = true, ShowPath = true;
        private const float RevealSeconds = 4f;
        private static readonly Color32 FreeC = new Color32(10, 12, 18, 90), OutsideC = new Color32(0, 0, 0, 0);
        private static readonly Color32 ObstacleC = new Color32(220, 40, 40, 128), SeamC = new Color32(240, 210, 40, 210);
        private static readonly Color32 ScanC = new Color32(40, 160, 170, 110);
        private static readonly Color ClusterC = new Color(.6f, .6f, .62f, .55f), EntranceC = new Color(.2f, .95f, 1f, .95f), GraphC = new Color(.2f, .9f, 1f, .22f);
        private static readonly Color AbstractPathC = new Color(.4f, 1f, 1f, 1f), RawPathC = Color.white, SmoothPathC = new Color(.25f, 1f, .35f, 1f);
        private static readonly Color JumpC = new Color(1f, .2f, 1f, 1f), MeetC = new Color(1f, .55f, .1f, 1f), StartC = new Color(.2f, .9f, .3f, 1f), GoalC = new Color(1f, .25f, .2f, 1f);

        private readonly GameObject root;
        private readonly ReferenceOverlay grid, heat, clusters, graph, nodes, paths, marks;
        private PathfindingStudy study;
        private SearchResult shownResult;
        private Color32[] heatPx;
        private float reveal = 1;
        private int shown = -1;

        public PathfindingView(Transform parent)
        {
            root = new GameObject("Reference pathfinding") { layer = ReferenceLayer.Index };
            root.transform.SetParent(parent, false);
            grid = ReferenceOverlay.Create("pathfinding grid", root.transform);
            heat = ReferenceOverlay.Create("pathfinding expansions", root.transform);
            clusters = ReferenceOverlay.Create("pathfinding clusters", root.transform);
            graph = ReferenceOverlay.Create("pathfinding abstract graph", root.transform);
            nodes = ReferenceOverlay.Create("pathfinding expanded nodes", root.transform);
            paths = ReferenceOverlay.Create("pathfinding paths", root.transform);
            marks = ReferenceOverlay.Create("pathfinding marks", root.transform);
        }

        public bool Visible { get => root != null && root.activeSelf; set { if (root != null) root.SetActive(value); } }
        public void Destroy() { if (root != null) UnityEngine.Object.Destroy(root); }

        /// <summary>Rebuild every overlay from the study. A new result restarts the expansion reveal.</summary>
        public void Draw(PathfindingStudy s)
        {
            study = s;
            if (s == null) { foreach (var o in All()) { o.Clear(); o.Apply(); o.HideGrid(); } return; }
            if (!ReferenceEquals(s.Last, shownResult)) { shownResult = s.Last; reveal = 0; }
            shown = -1;
            DrawGrid(s); DrawClusters(s); DrawPaths(s); DrawMarks(s);
            RevealExpansions(true);
        }

        /// <summary>Call every frame: reveals the expansion order progressively (full reveal in ~4 s).</summary>
        public void Animate(float seconds)
        {
            if (study == null || reveal >= 1) return;
            reveal = Mathf.Clamp01(reveal + seconds / RevealSeconds);
            RevealExpansions(false);
        }

        private IEnumerable<ReferenceOverlay> All() { yield return grid; yield return heat; yield return clusters; yield return graph; yield return nodes; yield return paths; yield return marks; }
        private V2 At(int cell) => study.Grid.CellCenter(cell);

        private void DrawGrid(PathfindingStudy s)
        {
            var g = s.Grid;
            if (!ShowGrid) { grid.HideGrid(); return; }
            var px = new Color32[g.W * g.H];
            for (int i = 0; i < px.Length; i++)
                switch (g.Code[i])
                {
                    case OccupancyGrid.Free: px[i] = FreeC; break;
                    case OccupancyGrid.Obstacle: px[i] = ObstacleC; break;
                    case OccupancyGrid.Seam: px[i] = SeamC; break;
                    default: px[i] = OutsideC; break;
                }
            grid.SetGrid(g.W, g.H, px, g.X0, g.Y0, g.Cell, .015);
        }

        private Hpa ShownHpa(PathfindingStudy s) => s.Hpa != null && s.Hpa.Built ? s.Hpa : null;

        private void DrawClusters(PathfindingStudy s)
        {
            clusters.Clear(); graph.Clear();
            var h = ShownHpa(s); var g = s.Grid;
            if (h != null && ShowClusters)
                foreach (var cl in h.Clusters)
                {
                    if (!AnyFree(s.Map, cl)) continue; // skip clusters wholly outside the lane
                    V2 a = new V2(g.X0 + cl.X0 * g.Cell, g.Y0 + cl.Y0 * g.Cell), b = new V2(g.X0 + (cl.X1 + 1) * g.Cell, g.Y0 + (cl.Y1 + 1) * g.Cell);
                    clusters.Polyline(new[] { a, new V2(b.X, a.Y), b, new V2(a.X, b.Y) }, ClusterC, .015, true, .03);
                }
            if (h != null && ShowAbstractGraph)
                foreach (var cl in h.Clusters)
                {
                    int n = cl.Nodes.Length;
                    for (int i = 0; i < n; i++)
                    {
                        for (int j = i + 1; j < n; j++) if (!double.IsInfinity(cl.Dist[i * n + j])) graph.Line(At(cl.Nodes[i]), At(cl.Nodes[j]), GraphC, .012, .035);
                        foreach (int p in cl.Partners[i]) if (p > cl.Nodes[i]) graph.Line(At(cl.Nodes[i]), At(p), GraphC, .02, .035);
                    }
                }
            if (h != null && ShowEntrances)
                foreach (var cl in h.Clusters) foreach (int c in cl.Nodes) graph.Disc(At(c), .045, EntranceC, .04, 8);
            clusters.Apply(); graph.Apply();
        }
        private static bool AnyFree(GridMap m, Hpa.Cluster cl)
        {
            for (int y = cl.Y0; y <= cl.Y1; y++) for (int x = cl.X0; x <= cl.X1; x++) if (m.Free(x, y)) return true;
            return false;
        }

        private void DrawPaths(PathfindingStudy s)
        {
            paths.Clear();
            var r = s.Last;
            if (ShowPath && r != null && r.Found)
            {
                if (r.Algo == Algo.Hpa && r.KeyNodes.Count > 1) paths.Polyline(s.Centres(r.KeyNodes), AbstractPathC, .035, false, .05);
                paths.Polyline(s.Centres(s.RawPath), RawPathC, .05, false, .055);
                if (s.Smooth && !SamePath(s.RawPath, r.Path)) paths.Polyline(s.Route(), SmoothPathC, .06, false, .06);
            }
            paths.Apply();
        }
        private static bool SamePath(List<int> a, List<int> b)
        {
            if (a.Count != b.Count) return false;
            for (int i = 0; i < a.Count; i++) if (a[i] != b[i]) return false;
            return true;
        }

        private void DrawMarks(PathfindingStudy s)
        {
            marks.Clear();
            var r = s.Last;
            if (r != null && r.Found && ShowPath)
            {
                if (r.Algo == Algo.Jps) foreach (int j in r.KeyNodes) marks.Disc(At(j), .08, JumpC, .065, 10);
                if (r.Algo == Algo.BidirAStar && r.Meet >= 0) marks.Disc(At(r.Meet), .14, MeetC, .065, 14);
            }
            if (s.Start >= 0) marks.Disc(At(s.Start), .25, StartC, .07, 20);
            if (s.Goal >= 0) marks.Disc(At(s.Goal), .25, GoalC, .07, 20);
            marks.Apply();
        }

        /// <summary>Grid searches paint cells into a texture; HPA* (abstract nodes) and JPS (jump points) draw discs.</summary>
        private void RevealExpansions(bool rebuild)
        {
            var s = study; var r = s.Last; var g = s.Grid;
            if (!ShowExpansions || r == null || r.Order == null)
            {
                if (rebuild) { heat.HideGrid(); nodes.Clear(); nodes.Apply(); }
                return;
            }
            int total = r.Order.Count, count = Mathf.Clamp(Mathf.CeilToInt(reveal * total), 0, total);
            if (count == shown && !rebuild) return;
            bool discs = r.Algo == Algo.Hpa || r.Algo == Algo.Jps;
            if (discs)
            {
                nodes.Clear();
                double radius = r.Algo == Algo.Hpa ? .06 : .05;
                for (int k = 0; k < count; k++) nodes.Disc(At(r.Order[k]), radius, Heat(k / (float)Math.Max(1, total - 1)), .045, 8);
                nodes.Apply();
            }
            else if (rebuild) { nodes.Clear(); nodes.Apply(); }

            // Texture layer: grid-search expansions, or the JPS jump scans (revealed together with the jump points).
            bool texture = !discs || (r.Algo == Algo.Jps && s.JumpScans.Count > 0);
            if (!texture) { heat.HideGrid(); shown = count; return; }
            if (heatPx == null || heatPx.Length != g.W * g.H) heatPx = new Color32[g.W * g.H];
            int from = shown;
            if (rebuild || from < 0 || count < from) { Array.Clear(heatPx, 0, heatPx.Length); from = 0; }
            if (!discs)
                for (int k = from; k < count; k++) heatPx[r.Order[k]] = Heat(k / (float)Math.Max(1, total - 1));
            else
            {
                int scans = s.JumpScans.Count, a = (int)((long)scans * from / Math.Max(1, total)), b = (int)((long)scans * count / Math.Max(1, total));
                for (int k = a; k < b; k++) heatPx[s.JumpScans[k]] = ScanC;
            }
            heat.SetGrid(g.W, g.H, heatPx, g.X0, g.Y0, g.Cell, .02);
            shown = count;
        }

        /// <summary>Order heat ramp: early = deep blue, then purple, orange, late = yellow.</summary>
        private static Color32 Heat(float t)
        {
            t = Mathf.Clamp01(t);
            Color a, b; float u;
            if (t < .5f) { a = new Color(.15f, .3f, .95f); b = new Color(.65f, .25f, .85f); u = t * 2; }
            else { a = new Color(.65f, .25f, .85f); b = new Color(1f, .85f, .2f); u = t * 2 - 1; }
            var c = Color.Lerp(a, b, u); c.a = .8f;
            return c;
        }
    }
}
