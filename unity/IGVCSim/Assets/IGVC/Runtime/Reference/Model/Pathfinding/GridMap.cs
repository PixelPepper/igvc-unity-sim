using System;
using System.Collections.Generic;

// Reference Lab pathfinding (ported from the Mechanics Sandbox HierarchicalPathfinding mechanic).
// Audit/visualisation only: plans on WORLD course geometry, never feeds ROS or the mission.
namespace IGVC.Reference.Pathfinding
{
    /// <summary>
    /// 8-connected occupancy grid shared by every algorithm so costs are comparable: straight step 1, diagonal sqrt(2),
    /// and a diagonal is legal only when BOTH orthogonal neighbours are free (no corner cutting). Undirected.
    /// </summary>
    public sealed class GridMap
    {
        public const double Sqrt2 = 1.4142135623730951;
        public const double Inf = double.PositiveInfinity;
        /// <summary>Directions: 0..3 straight (E, N, W, S), 4..7 diagonal (NE, NW, SW, SE).</summary>
        public static readonly int[] DX = { 1, 0, -1, 0, 1, -1, -1, 1 };
        public static readonly int[] DY = { 0, 1, 0, -1, 1, 1, -1, -1 };
        public static readonly double[] StepCost = { 1, 1, 1, 1, Sqrt2, Sqrt2, Sqrt2, Sqrt2 };

        public readonly int W, H;
        public readonly byte[] Blocked;
        /// <summary>Bumped on every change; caches (flow field, views) key on it.</summary>
        public int Version;

        public GridMap(int w, int h) { W = w; H = h; Blocked = new byte[w * h]; }
        /// <summary>Blocked wherever the occupancy code is not Free (outside lane, C-space obstacle, start seam).</summary>
        public static GridMap FromOccupancy(OccupancyGrid g)
        {
            var m = new GridMap(g.W, g.H);
            for (int i = 0; i < g.Code.Length; i++) m.Blocked[i] = g.Code[i] == OccupancyGrid.Free ? (byte)0 : (byte)1;
            return m;
        }

        public int Count => W * H;
        public int Index(int x, int y) => y * W + x;
        public int X(int i) => i % W;
        public int Y(int i) => i / W;
        public bool InBounds(int x, int y) => (uint)x < (uint)W && (uint)y < (uint)H;
        public bool Free(int x, int y) => (uint)x < (uint)W && (uint)y < (uint)H && Blocked[y * W + x] == 0;
        public bool Free(int i) => i >= 0 && i < Blocked.Length && Blocked[i] == 0;

        public bool Set(int x, int y, bool blocked)
        {
            if (!InBounds(x, y)) return false;
            int i = y * W + x; byte v = blocked ? (byte)1 : (byte)0;
            if (Blocked[i] == v) return false;
            Blocked[i] = v; Version++; return true;
        }
        public void Fill(bool blocked) { byte v = blocked ? (byte)1 : (byte)0; for (int i = 0; i < Blocked.Length; i++) Blocked[i] = v; Version++; }
        public GridMap Clone() { var m = new GridMap(W, H); Buffer.BlockCopy(Blocked, 0, m.Blocked, 0, Blocked.Length); return m; }

        public bool CanMove(int x, int y, int d)
        {
            int nx = x + DX[d], ny = y + DY[d];
            if (!Free(nx, ny)) return false;
            return d < 4 || (Free(nx, y) && Free(x, ny));
        }

        /// <summary>Octile distance: exact cost on an empty 8-connected grid (admissible and consistent).</summary>
        public static double Octile(int dx, int dy)
        {
            if (dx < 0) dx = -dx; if (dy < 0) dy = -dy;
            return dx > dy ? dx + (Sqrt2 - 1) * dy : dy + (Sqrt2 - 1) * dx;
        }
        public double CellDist(int a, int b) => Octile(X(a) - X(b), Y(a) - Y(b));
        public int FreeCount() { int n = 0; for (int i = 0; i < Blocked.Length; i++) if (Blocked[i] == 0) n++; return n; }

        /// <summary>Connected-component labels under the move rule; blocked cells get -1. Returns the count.</summary>
        public int Components(int[] label)
        {
            for (int i = 0; i < label.Length; i++) label[i] = -1;
            var stack = new int[Count]; int comp = 0;
            for (int s = 0; s < Count; s++)
            {
                if (Blocked[s] != 0 || label[s] >= 0) continue;
                int sp = 0; stack[sp++] = s; label[s] = comp;
                while (sp > 0)
                {
                    int u = stack[--sp], ux = u % W, uy = u / W;
                    for (int d = 0; d < 8; d++)
                    {
                        if (!CanMove(ux, uy, d)) continue;
                        int v = u + DY[d] * W + DX[d];
                        if (label[v] >= 0) continue;
                        label[v] = comp; stack[sp++] = v;
                    }
                }
                comp++;
            }
            return comp;
        }

        /// <summary>Null when the path runs s..t through free cells with legal moves only; otherwise the reason.</summary>
        public string ValidatePath(List<int> path, int s, int t, out double cost)
        {
            cost = 0;
            if (path == null || path.Count == 0) return "empty path";
            if (path[0] != s) return $"path starts at {path[0]} not {s}";
            if (path[path.Count - 1] != t) return $"path ends at {path[path.Count - 1]} not {t}";
            for (int i = 0; i < path.Count; i++)
            {
                if (!Free(path[i])) return $"cell {X(path[i])},{Y(path[i])} is blocked";
                if (i == 0) continue;
                int ax = X(path[i - 1]), ay = Y(path[i - 1]), dx = X(path[i]) - ax, dy = Y(path[i]) - ay;
                int d = DirOf(dx, dy);
                if (d < 0) return $"step {i} jumps ({dx},{dy})";
                if (!CanMove(ax, ay, d)) return $"step {i} at {ax},{ay} dir {d} cuts a corner / hits a wall";
                cost += StepCost[d];
            }
            return null;
        }
        public static int DirOf(int dx, int dy) { for (int d = 0; d < 8; d++) if (DX[d] == dx && DY[d] == dy) return d; return -1; }
        public static double PathCost(GridMap m, List<int> path)
        {
            double c = 0;
            for (int i = 1; i < path.Count; i++) c += m.X(path[i]) != m.X(path[i - 1]) && m.Y(path[i]) != m.Y(path[i - 1]) ? Sqrt2 : 1;
            return c;
        }
    }

    /// <summary>SplitMix64: seeded and platform-independent, so maps and benchmarks reproduce exactly.</summary>
    public sealed class GridRng
    {
        private ulong s;
        public GridRng(ulong seed) { s = seed * 0x9E3779B97F4A7C15UL + 0x1234567UL; }
        public ulong NextU64()
        {
            ulong z = s += 0x9E3779B97F4A7C15UL;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL; z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
            return z ^ (z >> 31);
        }
        public int Range(int n) => n <= 0 ? 0 : (int)(NextU64() % (ulong)n);
        public int Range(int lo, int hi) => lo + Range(hi - lo);
        public double NextDouble() => (NextU64() >> 11) * (1.0 / (1UL << 53));
        public bool Chance(double p) => NextDouble() < p;
    }
}
