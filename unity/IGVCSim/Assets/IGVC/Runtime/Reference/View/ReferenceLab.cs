using System;
using System.Collections.Generic;
using System.Diagnostics;
using IGVC.Reference.Drivers;
using IGVC.Reference.Pathfinding;
using IGVC.Reference.RacingLine;
using UnityEngine;

namespace IGVC.Reference
{
    /// <summary>
    /// Audit-side orchestrator for the sandbox "Reference lab" tab. It reads the WORLD course Unity renders,
    /// so it never publishes to ROS or writes mission inputs. Studies run as frame-budgeted jobs on the main
    /// thread and only when the panel allows (session stopped), so they cannot load a running trial.
    /// </summary>
    public sealed class ReferenceLab : MonoBehaviour
    {
        private const double FrameBudgetMs = 6;
        private TransportProbe probe;
        private CourseVariant.Manifest source;
        private Transform root;
        private PathfindingView pathView;
        private RacingLineView lineView;
        private DriversView driverView;
        private ReferenceOverlay trailOverlay;
        private IEnumerator<string> job;
        private string jobName;
        private Action jobDone;
        private readonly List<V2> trail = new List<V2>();
        private double nextTrailSample;
        private int trailHint = -1;

        public CourseGeometry Course { get; private set; }
        public Corridor Corridor { get; private set; }
        public Capsule[] Shapes { get; private set; }
        public OccupancyGrid Grid { get; private set; }
        public readonly RobotLimits Limits = new RobotLimits();
        public PathfindingStudy Paths { get; private set; }
        public RacingLineStudy Line { get; private set; }
        public DriversStudy Drivers { get; private set; }
        public string Status { get; private set; } = "Idle";
        public bool Busy => job != null;
        public bool GhostsRunning { get; private set; }
        public double GhostSpeed = 1;
        public bool RecordTrail;
        public double TrailMaxDeviation { get; private set; }
        public double TrailMeanDeviation { get; private set; }
        public int TrailContacts { get; private set; }
        public bool UseRoute = true;
        public PathfindingView PathView => pathView;
        public RacingLineView LineView => lineView;
        public DriversView DriverView => driverView;

        public void Initialize(TransportProbe owner)
        {
            probe = owner;
            root = new GameObject("Reference lab (audit only)") { layer = ReferenceLayer.Index }.transform;
            ReferenceOverlay.Height = GroundHeight;
            pathView = new PathfindingView(root); lineView = new RacingLineView(root); driverView = new DriversView(root);
            trailOverlay = ReferenceOverlay.Create("robot trail", root);
            Sync();
        }
        private double GroundHeight(double x, double y)
        {
            double h = 0;
            if (source?.ramps != null) foreach (var ramp in source.ramps) h = Math.Max(h, CourseRamp.HeightAt(ramp, x, y));
            return h;
        }

        public static CourseGeometry FromManifest(CourseVariant.Manifest m)
        {
            var center = new List<V2>(); var hw = new List<double>(); var painted = new List<bool>();
            foreach (var p in m.centerline) { center.Add(new V2(p.x, p.y)); hw.Add(p.half_width); painted.Add(p.painted); }
            var obstacles = new List<CourseObstacle>();
            foreach (var o in m.obstacles) obstacles.Add(new CourseObstacle { Id = o.id, Kind = o.kind, X = o.x, Y = o.y, Yaw = o.yaw, Length = o.length, Width = o.width });
            RampInfo ramp = null;
            if (m.ramps != null && m.ramps.Length > 0)
            {
                var r = m.ramps[0];
                ramp = new RampInfo { X = r.x, Y = r.y, Yaw = r.yaw, Width = r.width, RiseLength = r.rise_length, DeckLength = r.deck_length, Height = r.height };
            }
            string hash = string.IsNullOrEmpty(m.runtime_hash) ? "" : " sha256:" + m.runtime_hash.Substring(0, Math.Min(12, m.runtime_hash.Length));
            return CourseGeometry.Create(center, hw, painted, m.lane_width_m, obstacles, ramp, m.seed, "seed " + m.seed + hash);
        }

        /// <summary>Rebuild geometry after a sandbox course edit. The planner study updates incrementally.</summary>
        public void Sync()
        {
            if (probe.ActiveVariant == null || probe.ActiveVariant == source) return;
            Cancel(); StopGhosts();
            source = probe.ActiveVariant;
            Course = FromManifest(source); Corridor = new Corridor(Course); Shapes = Course.Shapes();
            Grid = Rasterizer.Rasterize(Corridor, Shapes, .1, Limits.InscribedRadius);
            if (Paths == null) Paths = new PathfindingStudy(Grid); else Paths.Replace(Grid);
            Line = new RacingLineStudy(Corridor, Shapes, Limits);
            Drivers = null;
            pathView.Draw(Paths); lineView.Visible = false; driverView.Visible = false;
            trail.Clear(); trailHint = -1; DrawTrail();
            Status = "Course " + Course.Identity + ": " + Corridor.Length.ToString("0.0") + " m loop, " + Course.Obstacles.Length + " obstacles, grid " + Grid.W + "x" + Grid.H + ".";
        }

        private void Launch(string name, IEnumerable<string> steps, Action done)
        {
            if (Busy) throw new InvalidOperationException("Wait for '" + jobName + "' to finish.");
            jobName = name; job = steps.GetEnumerator(); jobDone = done; Status = name + "...";
        }
        public void Cancel() { if (job != null) { job.Dispose(); job = null; Status = jobName + " cancelled."; } }

        public void PlanRoute() => Launch("Planning", Paths.Run(), () => { pathView.Draw(Paths); Status = "Route planned."; });
        public void Benchmark(int pairs) => Launch("Benchmark", Paths.Benchmark(pairs, 2027), () => Status = "Benchmark complete: " + pairs + " start/goal pairs.");
        public void OptimiseLine()
        {
            PrepareLine();
            Launch("Optimising line", Line.Run(), () => { lineView.Visible = true; lineView.Draw(Line); Drivers = null; Status = "Line ready."; });
        }
        public void CompareLines()
        {
            PrepareLine();
            Launch("Comparing line methods", Line.CompareAll(), () => { lineView.Visible = true; lineView.Draw(Line); Drivers = null; Status = "Comparison complete."; });
        }
        private void PrepareLine()
        {
            // The grid route fixes which side of each obstacle the continuous line passes.
            Line.SetRoute(UseRoute && Paths.Last != null && Paths.Last.Found ? Paths.Route() : null);
        }
        public void StartGhosts()
        {
            if (Line.Line == null) throw new InvalidOperationException("Optimise a racing line first.");
            if (Drivers == null) Drivers = new DriversStudy(Corridor, Shapes, Limits, Line);
            Drivers.Restart(); GhostsRunning = true; driverView.Visible = true; Status = "Ghosts driving the reference line.";
        }
        public void StopGhosts() { GhostsRunning = false; }
        public void TrainNeural(int generations)
        {
            if (Line.Line == null) throw new InvalidOperationException("Optimise a racing line first.");
            if (Drivers == null) Drivers = new DriversStudy(Corridor, Shapes, Limits, Line);
            StopGhosts(); Launch("Training neural driver", Drivers.TrainNeural(generations, 2027), () => Status = "Training complete; Start ghosts to watch it.");
        }
        public void ClearTrail() { trail.Clear(); trailHint = -1; TrailMaxDeviation = TrailMeanDeviation = 0; TrailContacts = 0; DrawTrail(); }
        public void SetVisible(bool value) { root.gameObject.SetActive(value); }
        public bool DrawingsVisible => root.gameObject.activeSelf;

        private void Update()
        {
            if (probe == null) return;
            if (probe.ActiveVariant != source) Sync();
            if (job != null)
            {
                var watch = Stopwatch.StartNew();
                try
                {
                    while (watch.Elapsed.TotalMilliseconds < FrameBudgetMs)
                    {
                        if (!job.MoveNext()) { job.Dispose(); job = null; var done = jobDone; jobDone = null; done?.Invoke(); break; }
                        if (!string.IsNullOrEmpty(job.Current)) Status = jobName + ": " + job.Current;
                    }
                }
                catch (Exception e) { job = null; Status = jobName + " failed: " + e.Message; UnityEngine.Debug.LogWarning("Reference lab: " + e); }
            }
            pathView.Animate(Time.deltaTime);
            if (GhostsRunning && Drivers != null)
            {
                Drivers.Step(Math.Min(.1, Time.deltaTime) * GhostSpeed);
                driverView.Draw(Drivers);
                if (Drivers.Finished) { GhostsRunning = false; Status = "Ghost lap finished."; }
            }
            if (RecordTrail && Time.timeAsDouble >= nextTrailSample) SampleTrail();
        }

        // The real robot's path is compared with the reference line for review only.
        private void SampleTrail()
        {
            nextTrailSample = Time.timeAsDouble + .1;
            var p = new V2(probe.AxleX, probe.AxleY);
            if (trail.Count > 0 && V2.Distance(trail[trail.Count - 1], p) < .05) return;
            trail.Add(p);
            if (Corridor.FootprintContact(p, probe.AxleYaw, Limits, Shapes, ref trailHint) != null) TrailContacts++;
            if (Line?.Line != null && Line.Line.Length > 1)
            {
                double best = double.PositiveInfinity;
                for (int i = 0; i < Line.Line.Length; i++)
                    best = Math.Min(best, Capsule.SegmentDistance(p, Line.Line[i], Line.Line[(i + 1) % Line.Line.Length]));
                TrailMaxDeviation = Math.Max(TrailMaxDeviation, best);
                TrailMeanDeviation += (best - TrailMeanDeviation) / trail.Count;
            }
            if (trail.Count % 5 == 0) DrawTrail();
        }
        private void DrawTrail()
        {
            trailOverlay.Clear();
            trailOverlay.Polyline(trail, new Color(1f, .85f, .1f, .95f), .07, false, .08);
            trailOverlay.Apply();
        }
        private void OnDestroy()
        {
            Cancel();
            pathView?.Destroy(); lineView?.Destroy(); driverView?.Destroy();
            if (root != null) Destroy(root.gameObject);
        }
    }
}
