using System;
using UnityEngine;

namespace IGVC
{
    // Simulator truth constraint only. Never publishes geometry to autonomy or perception.
    public sealed class LaneBoundaryGuard : MonoBehaviour
    {
        [Serializable] public struct Segment { public Vector2 a, b; }
        [SerializeField] private Segment[] segments;
        public int BlockedSteps { get; private set; }
        public void Configure(Segment[] value) { segments = value ?? throw new ArgumentNullException(nameof(value)); }
        public void Clear() { BlockedSteps = 0; }
        public bool CanOccupy(double x, double y, double yaw)
        {
            if (segments == null || segments.Length == 0) return false;
            double c = Math.Cos(yaw), s = Math.Sin(yaw);
            foreach (var line in segments)
            {
                // Broad phase around the complete conservative axle-relative footprint.
                if (Math.Max(line.a.x, line.b.x) < x - 1.5 || Math.Min(line.a.x, line.b.x) > x + 1.5
                    || Math.Max(line.a.y, line.b.y) < y - 1.5 || Math.Min(line.a.y, line.b.y) > y + 1.5) continue;
                double ax = c * (line.a.x-x) + s * (line.a.y-y), ay = -s * (line.a.x-x) + c * (line.a.y-y);
                double bx = c * (line.b.x-x) + s * (line.b.y-y), by = -s * (line.b.x-x) + c * (line.b.y-y);
                // Liang-Barsky line/AABB intersection, including endpoint containment.
                double low = 0, high = 1, dx = bx-ax, dy = by-ay;
                if (Clip(-dx, ax+1.13, ref low, ref high) && Clip(dx, .63-ax, ref low, ref high)
                    && Clip(-dy, ay+.53, ref low, ref high) && Clip(dy, .53-ay, ref low, ref high)) return false;
            }
            return true;
        }
        public bool AllowsMotion(double x, double y, double yaw, double v, double w, double dt)
        {
            // Samples sweep at <=5 mm corner motion. 30 mm skin covers the sample gaps.
            int steps = Math.Max(1, (int)Math.Ceiling((Math.Abs(v)+1.3*Math.Abs(w))*dt/.005));
            for (int i=1; i<=steps; i++)
            {
                double t=dt*i/steps, angle=w*t, half=angle*.5;
                double sinc=Math.Abs(half)<1e-8 ? 1 : Math.Sin(half)/half;
                if (!CanOccupy(x+v*t*sinc*Math.Cos(yaw+half), y+v*t*sinc*Math.Sin(yaw+half), yaw+angle))
                { BlockedSteps++; return false; }
            }
            return true;
        }
        private static bool Clip(double p, double q, ref double low, ref double high)
        {
            if (Math.Abs(p)<1e-12) return q>=0;
            double t=q/p;
            if (p<0) { if(t>high)return false; low=Math.Max(low,t); }
            else { if(t<low)return false; high=Math.Min(high,t); }
            return true;
        }
    }
}
