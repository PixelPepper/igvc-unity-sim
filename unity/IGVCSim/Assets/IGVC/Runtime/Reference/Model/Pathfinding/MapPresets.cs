using System;
using System.Collections.Generic;

namespace IGVC.Reference.Pathfinding
{
    public enum MapPreset { City, Cave, Maze, Rooms, Scatter, Traps, Empty }

    /// <summary>
    /// Seeded map generators for large grids. Each produces a map whose free space is ONE connected component
    /// (smaller pockets are filled in), so random start/goal pairs are always solvable and benchmark numbers compare
    /// like with like.
    /// </summary>
    public static class MapPresets
    {
        public static readonly string[] Names = { "City", "Cave", "Maze", "Rooms", "Scatter", "Traps", "Empty" };
        public const int Count = 7;

        public static void Generate(GridMap m, MapPreset p, int seed)
        {
            var rng = new GridRng((ulong)(seed * 7919 + (int)p * 104729 + 17));
            switch (p)
            {
                case MapPreset.City: City(m, rng); break;
                case MapPreset.Cave: Cave(m, rng); break;
                case MapPreset.Maze: Maze(m, rng); break;
                case MapPreset.Rooms: Rooms(m, rng); break;
                case MapPreset.Scatter: Scatter(m, rng); break;
                case MapPreset.Traps: Traps(m, rng); break;
                default: m.Fill(false); break;
            }
            KeepLargestComponent(m);
            m.Version++;
        }

        // ------------------------------------------------------------------------------------------ helpers

        public static void Rect(GridMap m, int x0, int y0, int x1, int y1, bool blocked)
        {
            if (x0 > x1) { int t = x0; x0 = x1; x1 = t; }
            if (y0 > y1) { int t = y0; y0 = y1; y1 = t; }
            x0 = Math.Max(0, x0); y0 = Math.Max(0, y0); x1 = Math.Min(m.W - 1, x1); y1 = Math.Min(m.H - 1, y1);
            byte v = blocked ? (byte)1 : (byte)0;
            for (int y = y0; y <= y1; y++)
            {
                int row = y * m.W;
                for (int x = x0; x <= x1; x++) m.Blocked[row + x] = v;
            }
        }

        public static void Disc(GridMap m, double cx, double cy, double r, bool blocked)
        {
            int x0 = (int)Math.Floor(cx - r), x1 = (int)Math.Ceiling(cx + r), y0 = (int)Math.Floor(cy - r), y1 = (int)Math.Ceiling(cy + r);
            byte v = blocked ? (byte)1 : (byte)0;
            for (int y = Math.Max(0, y0); y <= Math.Min(m.H - 1, y1); y++)
            for (int x = Math.Max(0, x0); x <= Math.Min(m.W - 1, x1); x++)
            {
                double dx = x + 0.5 - cx, dy = y + 0.5 - cy;
                if (dx * dx + dy * dy <= r * r) m.Blocked[y * m.W + x] = v;
            }
        }

        /// <summary>Thick line (capsule) from a to b.</summary>
        public static void Thick(GridMap m, double ax, double ay, double bx, double by, double r, bool blocked)
        {
            int x0 = (int)Math.Floor(Math.Min(ax, bx) - r), x1 = (int)Math.Ceiling(Math.Max(ax, bx) + r);
            int y0 = (int)Math.Floor(Math.Min(ay, by) - r), y1 = (int)Math.Ceiling(Math.Max(ay, by) + r);
            double vx = bx - ax, vy = by - ay, len2 = vx * vx + vy * vy;
            byte v = blocked ? (byte)1 : (byte)0;
            for (int y = Math.Max(0, y0); y <= Math.Min(m.H - 1, y1); y++)
            for (int x = Math.Max(0, x0); x <= Math.Min(m.W - 1, x1); x++)
            {
                double px = x + 0.5 - ax, py = y + 0.5 - ay;
                double t = len2 > 0 ? Math.Max(0, Math.Min(1, (px * vx + py * vy) / len2)) : 0;
                double dx = px - t * vx, dy = py - t * vy;
                if (dx * dx + dy * dy <= r * r) m.Blocked[y * m.W + x] = v;
            }
        }

        public static void KeepLargestComponent(GridMap m)
        {
            var label = new int[m.Count];
            int n = m.Components(label);
            if (n <= 1) return;
            var size = new int[n];
            for (int i = 0; i < label.Length; i++) if (label[i] >= 0) size[label[i]]++;
            int best = 0;
            for (int c = 1; c < n; c++) if (size[c] > size[best]) best = c;
            for (int i = 0; i < label.Length; i++) if (label[i] >= 0 && label[i] != best) m.Blocked[i] = 1;
        }

        /// <summary>Free cell closest to (fx·W, fy·H) - used for default start/goal placement.</summary>
        public static int NearestFree(GridMap m, double fx, double fy)
        {
            int tx = (int)(fx * (m.W - 1)), ty = (int)(fy * (m.H - 1));
            int maxR = Math.Max(m.W, m.H);
            for (int r = 0; r < maxR; r++)
            {
                int best = -1;
                double bd = double.MaxValue;
                for (int y = ty - r; y <= ty + r; y++)
                for (int x = tx - r; x <= tx + r; x++)
                {
                    if (Math.Max(Math.Abs(x - tx), Math.Abs(y - ty)) != r || !m.Free(x, y)) continue;
                    double d = (x - tx) * (x - tx) + (y - ty) * (y - ty);
                    if (d < bd) { bd = d; best = m.Index(x, y); }
                }
                if (best >= 0) return best;
            }
            return -1;
        }

        // ------------------------------------------------------------------------------------------ presets

        /// <summary>Streets between blocks of buildings split into lots, parks, two diagonal avenues and a river with bridges.</summary>
        static void City(GridMap m, GridRng rng)
        {
            m.Fill(false);
            var xs = Streets(m.W, rng);
            var ys = Streets(m.H, rng);
            // blocks between streets
            for (int i = 0; i + 1 < xs.Count; i += 2)
            for (int j = 0; j + 1 < ys.Count; j += 2)
            {
                int bx0 = xs[i], bx1 = xs[i + 1], by0 = ys[j], by1 = ys[j + 1];
                if (bx1 - bx0 < 4 || by1 - by0 < 4) continue;
                if (rng.Chance(0.1))
                {
                    // park: scattered trees
                    int trees = (bx1 - bx0) * (by1 - by0) / 60;
                    for (int k = 0; k < trees; k++) Disc(m, rng.Range(bx0 + 2, bx1 - 1), rng.Range(by0 + 2, by1 - 1), 1.2 + rng.NextDouble() * 1.2, true);
                    continue;
                }
                Lots(m, rng, bx0, by0, bx1 - 1, by1 - 1, 0);
            }
            // diagonal avenues cut through the blocks
            for (int k = 0; k < 2; k++)
            {
                double ax = rng.Range(m.W / 8), ay = k == 0 ? rng.Range(m.H / 4) : m.H - 1 - rng.Range(m.H / 4);
                double bx = m.W - 1 - rng.Range(m.W / 8), by = k == 0 ? m.H - 1 - rng.Range(m.H / 4) : rng.Range(m.H / 4);
                Thick(m, ax, ay, bx, by, 2.6 + m.W / 512.0, false);
            }
            // river: a sinuous band across the map, crossing only at a few bridges
            double phase = rng.NextDouble() * 6.28, amp = m.H * (0.06 + rng.NextDouble() * 0.05), y0 = m.H * (0.38 + rng.NextDouble() * 0.24);
            double halfW = Math.Max(3, m.W / 70.0);
            int bridges = 3 + rng.Range(2);
            var bridgeX = new List<int>();
            for (int b = 0; b < bridges; b++) bridgeX.Add((int)((b + 0.5 + (rng.NextDouble() - 0.5) * 0.6) * m.W / bridges));
            for (int x = 0; x < m.W; x++)
            {
                double c = y0 + amp * Math.Sin(x * 6.28 / m.W * 1.5 + phase);
                bool bridge = false;
                foreach (int bxp in bridgeX) if (Math.Abs(x - bxp) <= Math.Max(3, m.W / 128)) bridge = true;
                for (int y = (int)(c - halfW); y <= (int)(c + halfW); y++)
                    if (m.InBounds(x, y)) m.Blocked[y * m.W + x] = bridge ? (byte)0 : (byte)1;
            }
        }

        /// <summary>Alternating [street start, block start, ...] coordinates: returns pairs (blockStart, blockEnd).</summary>
        static List<int> Streets(int size, GridRng rng)
        {
            var list = new List<int>();
            int scale = Math.Max(1, size / 256);
            int x = rng.Range(2, 6) * scale;
            while (x < size)
            {
                int block = rng.Range(18, 52) * scale;
                int end = Math.Min(size, x + block);
                list.Add(x); list.Add(end);
                x = end + rng.Range(3, 8) * scale;
            }
            return list;
        }

        static void Lots(GridMap m, GridRng rng, int x0, int y0, int x1, int y1, int depth)
        {
            int w = x1 - x0 + 1, h = y1 - y0 + 1;
            if ((w < 14 && h < 14) || depth > 6 || (depth > 1 && rng.Chance(0.15)))
            {
                int inset = rng.Chance(0.4) ? 1 : 0;
                if (w - 2 * inset >= 2 && h - 2 * inset >= 2) Rect(m, x0 + inset, y0 + inset, x1 - inset, y1 - inset, true);
                // courtyards in big buildings
                if (w > 12 && h > 12 && rng.Chance(0.5)) Rect(m, x0 + w / 3, y0 + h / 3, x1 - w / 3, y1 - h / 3, false);
                return;
            }
            int alley = rng.Chance(0.5) ? 1 : (rng.Chance(0.5) ? 2 : 0);
            if (w >= h)
            {
                int s = x0 + w / 3 + rng.Range(Math.Max(1, w / 3));
                Lots(m, rng, x0, y0, s - 1, y1, depth + 1);
                Lots(m, rng, s + alley, y0, x1, y1, depth + 1);
            }
            else
            {
                int s = y0 + h / 3 + rng.Range(Math.Max(1, h / 3));
                Lots(m, rng, x0, y0, x1, s - 1, depth + 1);
                Lots(m, rng, x0, s + alley, x1, y1, depth + 1);
            }
        }

        /// <summary>Cellular-automaton caves (46 % fill, 5 smoothing passes, out of bounds counts as rock).</summary>
        static void Cave(GridMap m, GridRng rng)
        {
            var a = new byte[m.Count];
            var b = new byte[m.Count];
            for (int i = 0; i < a.Length; i++) a[i] = rng.Chance(0.455) ? (byte)1 : (byte)0;
            for (int pass = 0; pass < 5; pass++)
            {
                for (int y = 0; y < m.H; y++)
                for (int x = 0; x < m.W; x++)
                {
                    int n = 0;
                    for (int dy = -1; dy <= 1; dy++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        int nx = x + dx, ny = y + dy;
                        if ((uint)nx >= (uint)m.W || (uint)ny >= (uint)m.H) n++;
                        else n += a[ny * m.W + nx];
                    }
                    b[y * m.W + x] = n >= 5 ? (byte)1 : (byte)0;
                }
                var t = a; a = b; b = t;
            }
            Buffer.BlockCopy(a, 0, m.Blocked, 0, a.Length);
        }

        /// <summary>Recursive-backtracker maze with 3-wide corridors and 1-wide walls, then braided (6 % extra openings).</summary>
        static void Maze(GridMap m, GridRng rng)
        {
            const int pitch = 4, cw = 3;
            int nw = (m.W - 1) / pitch, nh = (m.H - 1) / pitch;
            m.Fill(true);
            var visited = new bool[nw * nh];
            var stack = new int[nw * nh];
            int sp = 0;
            stack[sp++] = 0;
            visited[0] = true;
            Carve(m, 0, 0, pitch, cw);
            var opts = new int[4];
            while (sp > 0)
            {
                int u = stack[sp - 1];
                int ux = u % nw, uy = u / nw, k = 0;
                for (int d = 0; d < 4; d++)
                {
                    int vx = ux + GridMap.DX[d], vy = uy + GridMap.DY[d];
                    if (vx < 0 || vy < 0 || vx >= nw || vy >= nh || visited[vy * nw + vx]) continue;
                    opts[k++] = d;
                }
                if (k == 0) { sp--; continue; }
                int dd = opts[rng.Range(k)];
                int wx = ux + GridMap.DX[dd], wy = uy + GridMap.DY[dd];
                visited[wy * nw + wx] = true;
                Carve(m, wx, wy, pitch, cw);
                Open(m, ux, uy, dd, pitch, cw);
                stack[sp++] = wy * nw + wx;
            }
            // braid: knock out random walls so there are loops (otherwise every algorithm returns the same unique path)
            int extra = nw * nh * 6 / 100;
            for (int i = 0; i < extra; i++)
            {
                int ux = rng.Range(nw - 1), uy = rng.Range(nh - 1);
                Open(m, ux, uy, rng.Range(2), pitch, cw);
            }
        }

        static void Carve(GridMap m, int nx, int ny, int pitch, int cw) =>
            Rect(m, 1 + nx * pitch, 1 + ny * pitch, nx * pitch + cw, ny * pitch + cw, false);

        static void Open(GridMap m, int nx, int ny, int d, int pitch, int cw)
        {
            int x0 = 1 + nx * pitch, y0 = 1 + ny * pitch;
            switch (d)
            {
                case 0: Rect(m, x0 + cw, y0, x0 + cw, y0 + cw - 1, false); break;
                case 1: Rect(m, x0, y0 + cw, x0 + cw - 1, y0 + cw, false); break;
                case 2: Rect(m, x0 - 1, y0, x0 - 1, y0 + cw - 1, false); break;
                case 3: Rect(m, x0, y0 - 1, x0 + cw - 1, y0 - 1, false); break;
            }
        }

        /// <summary>BSP office floor: 2-thick walls split rooms recursively, each split gets 1-2 doors.</summary>
        static void Rooms(GridMap m, GridRng rng)
        {
            m.Fill(false);
            var doors = new List<int[]>();
            Split(m, rng, 0, 0, m.W - 1, m.H - 1, doors, Math.Max(24, m.W / 14));
            foreach (var d in doors) Rect(m, d[0], d[1], d[2], d[3], false);
        }

        static void Split(GridMap m, GridRng rng, int x0, int y0, int x1, int y1, List<int[]> doors, int minRoom)
        {
            int w = x1 - x0 + 1, h = y1 - y0 + 1;
            bool vertical = w > h ? true : h > w ? false : rng.Chance(0.5);
            int len = vertical ? w : h;
            if (len < 2 * minRoom + 2) return;
            int s = (vertical ? x0 : y0) + minRoom + rng.Range(len - 2 * minRoom - 1);
            int span = vertical ? h : w;
            int ndoors = span > 3 * minRoom ? 2 : 1;
            if (vertical)
            {
                Rect(m, s, y0, s + 1, y1, true);
                for (int k = 0; k < ndoors; k++)
                {
                    int dw = rng.Range(3, 7), dy = y0 + 1 + rng.Range(Math.Max(1, h - dw - 2));
                    doors.Add(new[] { s, dy, s + 1, dy + dw - 1 });
                }
                Split(m, rng, x0, y0, s - 1, y1, doors, minRoom);
                Split(m, rng, s + 2, y0, x1, y1, doors, minRoom);
            }
            else
            {
                Rect(m, x0, s, x1, s + 1, true);
                for (int k = 0; k < ndoors; k++)
                {
                    int dw = rng.Range(3, 7), dx = x0 + 1 + rng.Range(Math.Max(1, w - dw - 2));
                    doors.Add(new[] { dx, s, dx + dw - 1, s + 1 });
                }
                Split(m, rng, x0, y0, x1, s - 1, doors, minRoom);
                Split(m, rng, x0, s + 2, x1, y1, doors, minRoom);
            }
            // furniture
            if (w < 3 * minRoom && h < 3 * minRoom && rng.Chance(0.3))
                Rect(m, x0 + w / 3, y0 + h / 3, x0 + w / 3 + rng.Range(2, 5), y0 + h / 3 + rng.Range(2, 5), true);
        }

        /// <summary>Random rectangles and discs until ~27 % of the map is blocked.</summary>
        static void Scatter(GridMap m, GridRng rng)
        {
            m.Fill(false);
            int target = m.Count * 27 / 100, blocked = 0, s = Math.Max(1, m.W / 256);
            for (int guard = 0; guard < 100000 && blocked < target; guard++)
            {
                if (rng.Chance(0.5))
                {
                    int x = rng.Range(m.W), y = rng.Range(m.H), w = rng.Range(2, 22) * s, h = rng.Range(2, 22) * s;
                    Rect(m, x, y, x + w, y + h, true);
                }
                else Disc(m, rng.Range(m.W), rng.Range(m.H), (2 + rng.NextDouble() * 9) * s, true);
                if ((guard & 15) == 0) blocked = m.Count - m.FreeCount();
            }
        }

        /// <summary>
        /// Open field with U-shaped cups and a few long walls: the classic worst case for a greedy heuristic, A* fills
        /// every cup that opens towards the goal before it finds the way around.
        /// </summary>
        static void Traps(GridMap m, GridRng rng)
        {
            m.Fill(false);
            int s = Math.Max(1, m.W / 256);
            int cups = 26 + rng.Range(8);
            for (int k = 0; k < cups; k++)
            {
                int size = (int)(m.W * (0.05 + rng.NextDouble() * 0.11)), cx = rng.Range(m.W), cy = rng.Range(m.H), t = s;
                int dir = rng.Chance(0.6) ? 2 + rng.Range(2) : rng.Range(4); // most cups open towards the start corner (W/S)
                int x0 = cx - size / 2, y0 = cy - size / 2, x1 = cx + size / 2, y1 = cy + size / 2;
                if (dir != 0) Rect(m, x1 - t, y0, x1, y1, true);
                if (dir != 1) Rect(m, x0, y1 - t, x1, y1, true);
                if (dir != 2) Rect(m, x0, y0, x0 + t, y1, true);
                if (dir != 3) Rect(m, x0, y0, x1, y0 + t, true);
            }
            for (int k = 0; k < 4; k++)
            {
                double ax = rng.Range(m.W), ay = rng.Range(m.H), ang = rng.NextDouble() * Math.PI, len = m.W * (0.2 + rng.NextDouble() * 0.25);
                Thick(m, ax, ay, ax + Math.Cos(ang) * len, ay + Math.Sin(ang) * len, 1.0 * s + 0.5, true);
            }
        }
    }
}
