using System.Collections.Generic;
using IGVC.Reference.RacingLine;
using UnityEngine;

namespace IGVC.Reference
{
    /// <summary>
    /// Draws a <see cref="RacingLineStudy"/> on the reference layer: per-station bounds as two edge lines (blocked stations
    /// marked), the selected line coloured by lap-sim speed (slow red, fast green) with braking segments underlaid, stations
    /// where the whole body would touch, and the faint corridor centre. Reference only - never seen by the sensors.
    /// </summary>
    public sealed class RacingLineView
    {
        public bool ShowBounds = true, ShowLine = true, ShowCentre = true;
        private readonly ReferenceOverlay overlay;
        private readonly List<V2> points = new List<V2>(), lo = new List<V2>(), hi = new List<V2>();
        private readonly List<Color> colors = new List<Color>();
        private static readonly Color Bound = new Color(.3f, .8f, 1f, .75f), Centre = new Color(1f, 1f, 1f, .25f), Brake = new Color(.75f, .05f, .55f, .8f);
        private static readonly Color Slow = new Color(1f, .2f, .15f), Mid = new Color(1f, .9f, .25f), Fast = new Color(.25f, .95f, .35f);
        private static readonly Color Blocked = new Color(1f, 0f, 0f, .9f), Touch = new Color(1f, .35f, 0f, .9f);

        public RacingLineView(Transform parent) { overlay = ReferenceOverlay.Create("racing line", parent); }

        public bool Visible { get => overlay != null && overlay.Visible; set { if (overlay != null) overlay.Visible = value; } }

        public void Draw(RacingLineStudy s)
        {
            if (overlay == null) return;
            overlay.Clear();
            var tr = s?.Track;
            if (tr == null) { overlay.Apply(); return; }
            int n = tr.N;
            if (ShowCentre) overlay.Polyline(tr.P, Centre, .03, true, .02);
            if (ShowBounds)
            {
                lo.Clear(); hi.Clear();
                for (int i = 0; i < n; i++) { lo.Add(tr.P[i] + tr.Nl[i] * tr.Lo[i]); hi.Add(tr.P[i] + tr.Nl[i] * tr.Hi[i]); }
                overlay.Polyline(lo, Bound, .04, true, .025); overlay.Polyline(hi, Bound, .04, true, .025);
                foreach (int i in tr.Blocked) overlay.Disc(tr.P[i] + tr.Nl[i] * tr.Lo[i], .18, Blocked, .04);
            }
            if (ShowLine && s.Line != null && s.Lap != null && s.Lap.N == s.Line.Length)
            {
                var lap = s.Lap; double vMin = lap.MinSpeed, vMax = lap.MaxSpeed, span = vMax - vMin;
                points.Clear(); colors.Clear();
                for (int i = 0; i < lap.N; i++)
                {
                    points.Add(s.Line[i]);
                    float t = span > 1e-6 ? (float)((lap.V[i] - vMin) / span) : 1f;
                    colors.Add(t < .5f ? Color.Lerp(Slow, Mid, t * 2) : Color.Lerp(Mid, Fast, t * 2 - 1));
                }
                for (int i = 0; i < lap.N; i++)
                    if (lap.Braking[i]) overlay.Line(s.Line[i], s.Line[(i + 1) % lap.N], Brake, .18, .035);
                overlay.Polyline(points, colors, .08, true, .045);
                foreach (int i in s.LineContactStations) overlay.Ring(s.Line[i], .25, Touch, .04, .05);
            }
            overlay.Apply();
        }

        public void Destroy() { if (overlay != null) Object.Destroy(overlay.gameObject); }
    }
}
