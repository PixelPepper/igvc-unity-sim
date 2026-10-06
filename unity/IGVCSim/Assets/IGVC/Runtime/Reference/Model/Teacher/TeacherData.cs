using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

// Hindsight teacher (offline labeller). It reads WORLD course geometry, so every label it produces is
// training/evaluation data only: it must never be written anywhere the mission, planner or ROS reads.
namespace IGVC.Reference.Teacher
{
    public sealed class GeoOrigin { public double Latitude, Longitude, Altitude; }

    /// <summary>WGS84 ECEF/ENU, the same maths as ros2/src/igvc_gps/igvc_gps/geodesy.py LocalFrame (odom: x east, y north).</summary>
    public static class Geo
    {
        const double A = 6378137.0, F = 1 / 298.257223563, E2 = F * (2 - F);
        static double Rad(double d) => d * Math.PI / 180;
        static double Deg(double r) => r * 180 / Math.PI;
        public static void Ecef(double lat, double lon, double alt, out double x, out double y, out double z)
        {
            double p = Rad(lat), l = Rad(lon), sp = Math.Sin(p), n = A / Math.Sqrt(1 - E2 * sp * sp);
            x = (n + alt) * Math.Cos(p) * Math.Cos(l); y = (n + alt) * Math.Cos(p) * Math.Sin(l); z = (n * (1 - E2) + alt) * sp;
        }
        static double[] Rows(GeoOrigin o)
        {
            double p = Rad(o.Latitude), l = Rad(o.Longitude);
            return new[] { -Math.Sin(l), Math.Cos(l), 0, -Math.Sin(p) * Math.Cos(l), -Math.Sin(p) * Math.Sin(l), Math.Cos(p), Math.Cos(p) * Math.Cos(l), Math.Cos(p) * Math.Sin(l), Math.Sin(p) };
        }
        public static double[] ToEnu(GeoOrigin o, double lat, double lon, double alt)
        {
            Ecef(o.Latitude, o.Longitude, o.Altitude, out double ox, out double oy, out double oz);
            Ecef(lat, lon, alt, out double x, out double y, out double z);
            double dx = x - ox, dy = y - oy, dz = z - oz; var r = Rows(o);
            return new[] { r[0] * dx + r[1] * dy + r[2] * dz, r[3] * dx + r[4] * dy + r[5] * dz, r[6] * dx + r[7] * dy + r[8] * dz };
        }
        public static V2 ToOdom(GeoOrigin o, double lat, double lon, double alt = 0) { var e = ToEnu(o, lat, lon, alt); return new V2(e[0], e[1]); }
        public static void ToGeodetic(GeoOrigin o, double east, double north, double up, out double lat, out double lon, out double alt)
        {
            Ecef(o.Latitude, o.Longitude, o.Altitude, out double ox, out double oy, out double oz); var r = Rows(o);
            double x = ox + r[0] * east + r[3] * north + r[6] * up, y = oy + r[1] * east + r[4] * north + r[7] * up, z = oz + r[2] * east + r[5] * north + r[8] * up;
            double hxy = Math.Sqrt(x * x + y * y), p = Math.Atan2(z, hxy * (1 - E2));
            for (int i = 0; i < 15; i++)
            {
                double s = Math.Sin(p), n0 = A / Math.Sqrt(1 - E2 * s * s), q = Math.Atan2(z + E2 * n0 * s, hxy);
                if (Math.Abs(q - p) < 1e-14) { p = q; break; }
                p = q;
            }
            double sp = Math.Sin(p), n = A / Math.Sqrt(1 - E2 * sp * sp);
            alt = hxy * Math.Cos(p) + z * sp - n * (1 - E2 * sp * sp); lat = Deg(p); lon = Deg(Math.Atan2(y, x));
        }
    }

    /// <summary>One candidate or the chosen plan (decision log v2 outcome, or the v1 evaluated plan).</summary>
    public sealed class CandidateIn
    {
        public V2 End; public double Yaw = double.NaN, PathLength = double.NaN, Score = double.NaN;
        public List<V2> Path; public string Source = "";
    }

    /// <summary>One saved planning decision: the observed snapshot input plus (optional) outcome join.</summary>
    public sealed class SnapshotIn
    {
        public int Index, DestinationIndex;
        public V2 Robot, Destination; public double Yaw, Lookahead = 7, StampS = double.NaN;
        public CandidateIn Plan;                  // chosen plan (null = none)
        public List<CandidateIn> Candidates;      // v2 only
        public string Action = "";
        public bool HasAfter; public V2 After;    // v2 robot_xy_after
        public double ProgressM = double.NaN, SearchWallS = double.NaN;
        public int Admitted = -1;                 // -1 unknown, 0 rejected, 1 admitted
    }

    public sealed class RunIn
    {
        public string Name = "", Status = "", Reason = "";
        public CourseGeometry Course;
        public GeoOrigin Origin;
        public List<V2> Goals = new List<V2>();   // autonomy.json goals converted to odom (may be empty)
        public List<SnapshotIn> Snapshots = new List<SnapshotIn>();
        public double[] TrajT = new double[0], TrajYaw = new double[0]; public V2[] TrajP = new V2[0];
        public int OutcomeSchema;                 // 0 = no decisions/outcomes.jsonl, 2 = v2 outcomes joined
    }

    public sealed class LabelOptions
    {
        public double[] SpeedCeilings = { 0.6, 2.2 };
        /// <summary>v1 "executed" outcome: robot pose this long after the snapshot (cut at the next destination switch).</summary>
        public double HorizonS = 5;
        public double StallWindowS = 20, StallProgressM = .5, PreviewM = 10;
        public double Cell = .1;
        public int Worst = 10;
        /// <summary>
        /// Corridor label mode, chosen explicitly (CLI --corridor-label). Legacy fields (teacher_cost_m, regret_m, plan
        /// regret, best candidate) are identical in every mode: straight robot-to-entry line plus the entry's cost-to-go.
        /// "straight-v1" (default: the meaning of all earlier labels) writes only those. "path-v3" additionally writes a
        /// separate corridor_target per lane-corridor candidate: the straight leg only when every intersected cell is
        /// free, else the grid shortest path; blocked endpoints, search-limited and disconnected entries get a status and
        /// no cost. (The unaccepted "path-v2" overwrote teacher_cost_m and is no longer produced.)
        /// </summary>
        public string CorridorCost = StraightV1;
        public const string StraightV1 = "straight-v1", PathV3 = "path-v3";
        /// <summary>Fixed bound (m) on the WHOLE robot-to-entry grid leg (both in-cell attachment offsets plus the octile
        /// centre path); entries whose leg would exceed it are "search_limited", never costed.</summary>
        public double CorridorSearchCapM = 60;
    }

    /// <summary>Minimal deterministic JSON writer (invariant culture, fixed decimals, NaN/Inf as null).</summary>
    public sealed class JsonOut
    {
        readonly StringBuilder b = new StringBuilder(); readonly List<bool> first = new List<bool>(); bool afterKey;
        void Sep()
        {
            if (afterKey) { afterKey = false; return; }
            int k = first.Count - 1; if (k < 0) return;
            if (!first[k]) b.Append(','); first[k] = false;
        }
        public JsonOut O() { Sep(); b.Append('{'); first.Add(true); return this; }
        public JsonOut EO() { first.RemoveAt(first.Count - 1); b.Append('}'); return this; }
        public JsonOut A() { Sep(); b.Append('['); first.Add(true); return this; }
        public JsonOut EA() { first.RemoveAt(first.Count - 1); b.Append(']'); return this; }
        public JsonOut K(string k) { Sep(); Quote(k); b.Append(':'); afterKey = true; return this; }
        public JsonOut N(double v, int decimals = 4)
        {
            Sep();
            if (double.IsNaN(v) || double.IsInfinity(v)) b.Append("null");
            else { string s = Math.Round(v, decimals).ToString("0." + new string('#', decimals), CultureInfo.InvariantCulture); b.Append(s == "-0" ? "0" : s); }
            return this;
        }
        public JsonOut I(long v) { Sep(); b.Append(v.ToString(CultureInfo.InvariantCulture)); return this; }
        public JsonOut S(string v) { Sep(); if (v == null) b.Append("null"); else Quote(v); return this; }
        public JsonOut B(bool v) { Sep(); b.Append(v ? "true" : "false"); return this; }
        public JsonOut Null() { Sep(); b.Append("null"); return this; }
        public JsonOut P(V2 p) => A().N(p.X).N(p.Y).EA();
        public JsonOut Pts(IList<V2> ps) { if (ps == null) return Null(); A(); foreach (var p in ps) P(p); return EA(); }
        void Quote(string s)
        {
            b.Append('"');
            foreach (char ch in s)
            {
                if (ch == '"' || ch == '\\') b.Append('\\').Append(ch);
                else if (ch < ' ') b.Append("\\u").Append(((int)ch).ToString("x4"));
                else b.Append(ch);
            }
            b.Append('"');
        }
        public override string ToString() => b.ToString();
    }
}
