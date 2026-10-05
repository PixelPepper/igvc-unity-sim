using IGVC.Reference.Drivers;
using UnityEngine;

namespace IGVC.Reference
{
    /// <summary>
    /// Per-frame drawing of the ghost drivers: translucent footprint box per ghost in its colour (red outline while in
    /// contact), a short trail, the pure-pursuit look-ahead target, the MPC's best rollout over faint samples, and the
    /// neural driver's range rays. Reference only - never seen by the sensors.
    /// </summary>
    public sealed class DriversView
    {
        private readonly ReferenceOverlay overlay;
        private static readonly Color ContactColor = new Color(1f, 0f, 0f, 1f);

        public DriversView(Transform parent) { overlay = ReferenceOverlay.Create("ghost drivers", parent); }

        public bool Visible { get => overlay != null && overlay.Visible; set { if (overlay != null) overlay.Visible = value; } }

        private static Color Tint(Ghost g, float alpha) => new Color((float)g.Color.R, (float)g.Color.G, (float)g.Color.B, alpha);

        public void Draw(DriversStudy s)
        {
            if (overlay == null) return;
            overlay.Clear();
            if (s == null) { overlay.Apply(); return; }
            var r = s.Limits;
            double front = r.Front + r.Padding, rear = r.Rear + r.Padding, half = r.HalfWidth + r.Padding;
            foreach (var g in s.Ghosts)
            {
                V2 axle = g.Pose.Axle; double yaw = g.Pose.Yaw;
                if (g.Trail.Count > 1) overlay.Polyline(g.Trail, Tint(g, .55f), .04, false, .04);
                if (g.Trail.Count > 0) overlay.Line(g.Trail[g.Trail.Count - 1], axle, Tint(g, .55f), .04, .04);

                var rollouts = g.Rollouts;
                if (rollouts != null)
                {
                    int best = g.BestRollout;
                    for (int c = 0; c < rollouts.Length; c++) if (c != best) overlay.Polyline(rollouts[c], Tint(g, .12f), .015, false, .05);
                    if (best >= 0 && best < rollouts.Length) overlay.Polyline(rollouts[best], Tint(g, .95f), .05, false, .055);
                }
                var rays = g.RayEnds;
                if (rays != null)
                {
                    V2 origin = g.RayOrigin;
                    foreach (var end in rays) { overlay.Line(origin, end, Tint(g, .5f), .02, .05); overlay.Disc(end, .05, Tint(g, .9f), .055, 10); }
                }
                var target = g.LookaheadTarget;
                if (target.HasValue)
                {
                    overlay.Line(axle, target.Value, Tint(g, .5f), .02, .06);
                    overlay.Ring(target.Value, .15, Tint(g, 1f), .04, .06, 16);
                }

                overlay.Box(axle, yaw, front, rear, half, Tint(g, .35f), .07);
                overlay.BoxOutline(axle, yaw, front, rear, half, g.InContact ? ContactColor : Tint(g, 1f), .04, .08);
                overlay.Disc(axle, .06, Tint(g, 1f), .085, 12);
            }
            overlay.Apply();
        }

        public void Destroy() { if (overlay != null) Object.Destroy(overlay.gameObject); }
    }
}
