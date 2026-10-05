using System;
using System.Collections.Generic;
using System.Diagnostics;
using IGVC.Reference.RacingLine;

namespace IGVC.Reference.Drivers
{
    /// <summary>One ghost robot: its driver, state, metrics and debug drawing data. Ghosts never interact.</summary>
    public sealed class Ghost
    {
        public string Name;
        public (double R, double G, double B) Color;
        public IDriver Driver;
        public RobotState State;
        public (V2 Axle, double Yaw) Pose => (State.Pos, State.Heading);
        public double V => State.V;

        public double Time, Progress, LapTime = -1, FirstContactS = -1, MinClearance = double.MaxValue, MaxSpeed, MaxCte;
        public int Contacts, ContactSteps;
        public bool Completed, Done, InContact;
        public string Status = "";
        public readonly List<V2> Trail = new List<V2>();
        internal double CteIntegral, LastS, StallTimer, StallRef, NextTrail;
        internal long Ticks, Calls;
        internal int PathHint = -1;

        public double MeanCte => Time > 0 ? CteIntegral / Time : 0;
        public double MicrosPerCall => Calls > 0 ? Ticks * 1e6 / Stopwatch.Frequency / Calls : 0;

        // Debug for the view (null when the driver has none).
        public V2? LookaheadTarget => Driver is PurePursuit pp ? pp.Target : (V2?)null;
        public V2[][] Rollouts => (Driver as SamplingMpc)?.Paths;
        public double[] RolloutCosts => (Driver as SamplingMpc)?.Costs;
        public int BestRollout => Driver is SamplingMpc m ? m.Best : -1;
        public V2[] RayEnds => (Driver as NeuralDriver)?.RayEnds;
        public V2 RayOrigin => Driver is NeuralDriver n ? n.RayOrigin : State.Pos;
    }

    /// <summary>
    /// Ghost robots driving the reference line on the WORLD corridor (reference only, not autonomy): regulated pure
    /// pursuit, Stanley, sampling MPC and (once trained) a range-sensor neural driver, each on its own (no ghost-ghost
    /// collisions), with the R3-a diff-drive limits. Contacts use the whole-body footprint. Fixed 20 Hz steps.
    /// </summary>
    public sealed class DriversStudy
    {
        public const double Dt = .05, StallTime = 15, StallDistance = .3;
        public readonly Corridor Corridor;
        public readonly Capsule[] Shapes;
        public readonly RobotLimits Limits;
        public readonly RacingLineStudy LineStudy;
        public readonly DriveWorld World;
        /// <summary>Ghost speed ceiling; NaN = the line study's SpeedCeiling.</summary>
        public double SpeedCeiling = double.NaN;
        /// <summary>Speed plan derating for the trackers (lateral / yaw / braking share used by the plan).</summary>
        public double PlanLateralShare = .85, PlanBrakeShare = .75;
        public bool IncludeNeural = true;
        public RefPath Path { get; private set; }
        /// <summary>Standing-start lap of the reference line under the same limits and ceiling (lap-time lower bound).</summary>
        public double LowerBound { get; private set; }
        public double Time { get; private set; }
        public double MaxTime { get; private set; }
        public double Ceiling { get; private set; }
        public double[] NeuralGenome;
        public NeuroTrainer Trainer { get; private set; }
        public IReadOnlyList<Ghost> Ghosts => ghosts;
        public bool Finished { get { foreach (var g in ghosts) if (!g.Done) return false; return ghosts.Count > 0; } }

        private readonly List<Ghost> ghosts = new List<Ghost>();
        private DriveContext ctx;
        private double accumulator;

        public DriversStudy(Corridor corridor, Capsule[] shapes, RobotLimits limits, RacingLineStudy line)
        {
            Corridor = corridor; Shapes = shapes ?? new Capsule[0]; Limits = limits ?? new RobotLimits(); LineStudy = line;
            World = new DriveWorld(corridor, Shapes, Limits);
        }

        public static RobotState StartState(Corridor c) => new RobotState { Pos = c.P[0], Heading = c.HeadingAt(0), Hint = 0 };

        private void Prepare()
        {
            if (LineStudy.Line == null) foreach (var _ in LineStudy.Run()) { }
            Ceiling = double.IsNaN(SpeedCeiling) ? LineStudy.SpeedCeiling : SpeedCeiling;
            var plan = Limits.Clone();
            plan.MaxLateral *= PlanLateralShare; plan.MaxYawRate *= PlanLateralShare; plan.MaxBrake *= PlanBrakeShare;
            var line = LineStudy.Line;
            var lap = LapSim.Simulate(line, plan, Ceiling);
            Path = new RefPath(line, lap.Kappa, lap.V);
            LowerBound = LapSim.Simulate(line, Limits, Ceiling, null, false, true).LapTime;
            MaxTime = Math.Max(60, 3 * LowerBound + 30);
            ctx = new DriveContext { World = World, Path = Path, Limits = Limits, Ceiling = Ceiling, Lo = LineStudy.Lo, Hi = LineStudy.Hi };
        }

        public void Restart()
        {
            Prepare();
            ghosts.Clear(); Time = 0; accumulator = 0;
            Add(new PurePursuit(), "Pure pursuit (RPP)", (.25, .9, .35));
            Add(new Stanley(), "Stanley", (.3, .6, 1));
            Add(new SamplingMpc(), "Sampling MPC", (1, .6, .15));
            if (IncludeNeural && NeuralGenome != null) Add(new NeuralDriver((double[])NeuralGenome.Clone()), "Neural (NeuroGA)", (.9, .35, .95));
        }
        private void Add(IDriver d, string name, (double, double, double) color)
        {
            d.Reset();
            var g = new Ghost { Name = name, Color = color, Driver = d, State = StartState(Corridor) };
            g.Trail.Add(g.State.Pos);
            ghosts.Add(g);
        }

        /// <summary>Advances by dt seconds in fixed sub-steps (bounded per call so a slow frame cannot stall Unity).</summary>
        public void Step(double dt)
        {
            if (ghosts.Count == 0) Restart();
            accumulator += dt;
            for (int k = 0; accumulator >= Dt && k < 2000; k++) { SubStep(); accumulator -= Dt; }
            if (accumulator > Dt) accumulator = 0;
        }
        public void RunToEnd() { if (ghosts.Count == 0) Restart(); while (!Finished) SubStep(); }

        private void SubStep()
        {
            if (Finished) return;
            ctx.Time = Time;
            foreach (var g in ghosts)
            {
                if (g.Done) continue;
                long t0 = Stopwatch.GetTimestamp();
                g.Driver.Act(ref g.State, ctx, out double v, out double w);
                g.Ticks += Stopwatch.GetTimestamp() - t0; g.Calls++;
                DiffDrive.Step(ref g.State, v, w, Dt, Limits);
                g.Time += Dt;
                Measure(g);
            }
            Time += Dt;
        }

        private void Measure(Ghost g)
        {
            int hint = g.State.Hint;
            bool hit = World.Contact(g.State.Pos, g.State.Heading, ref hint, out double clearance) != null;
            g.State.Hint = hint;
            Corridor.Project(g.State.Pos, out double s, out _, hint, 4);
            double ds = s - g.LastS;
            if (ds < -Corridor.Length / 2) ds += Corridor.Length; else if (ds > Corridor.Length / 2) ds -= Corridor.Length;
            g.Progress += ds; g.LastS = s;
            if (hit) { if (!g.InContact) { g.Contacts++; if (g.FirstContactS < 0) g.FirstContactS = s; } g.ContactSteps++; }
            g.InContact = hit;

            g.MinClearance = Math.Min(g.MinClearance, clearance);
            g.PathHint = Path.Project(g.State.Pos, g.PathHint, out _, out double e);
            g.CteIntegral += Math.Abs(e) * Dt; g.MaxCte = Math.Max(g.MaxCte, Math.Abs(e));
            g.MaxSpeed = Math.Max(g.MaxSpeed, g.State.V);
            if (g.Time >= g.NextTrail) { g.NextTrail = g.Time + .25; g.Trail.Add(g.State.Pos); if (g.Trail.Count > 240) g.Trail.RemoveAt(0); }
            if (g.Progress >= Corridor.Length)
            {
                double over = g.Progress - Corridor.Length;
                g.LapTime = g.Time - (ds > 1e-6 ? over / ds * Dt : 0); g.Completed = true; g.Done = true; g.Status = "lap"; return;
            }
            g.StallTimer += Dt;
            if (g.StallTimer >= StallTime) { if (g.Progress - g.StallRef < StallDistance) { g.Done = true; g.Status = "stalled"; return; } g.StallTimer = 0; g.StallRef = g.Progress; }
            if (g.Time >= MaxTime) { g.Done = true; g.Status = "timeout"; }
        }

        /// <summary>Neuroevolution on this corridor; frame-steppable (each item is a bounded chunk of simulation).</summary>
        public IEnumerable<string> TrainNeural(int generations, ulong seed)
        {
            Prepare();
            Trainer = new NeuroTrainer(new DriveContext { World = World, Path = Path, Limits = Limits, Ceiling = Ceiling }, seed, 24, NeuralGenome);
            foreach (var line in Trainer.Train(generations)) yield return line;
            NeuralGenome = (double[])Trainer.GA.Best.Clone();
            ghosts.Clear();
            yield return "trained: best fitness " + Trainer.GA.BestFitness.ToString("0.0") + " (gen 0 " + Trainer.GA.BestHistory[0].ToString("0.0") + ")";
        }

        public string[] Summary()
        {
            var s = new List<string>();
            foreach (var g in ghosts)
                s.Add(g.Name + ": " + (g.Completed ? "lap " + g.LapTime.ToString("0.00") + " s" : g.Status.Length > 0 ? g.Status + " at " + g.Progress.ToString("0.0") + " m" : "driving " + g.Progress.ToString("0.0") + " m")
                    + ", contacts " + g.Contacts + (g.FirstContactS >= 0 ? " (first at s=" + g.FirstContactS.ToString("0.0") + ")" : "")
                    + ", min clearance " + (g.MinClearance == double.MaxValue ? "-" : g.MinClearance.ToString("0.00")) + " m, CTE mean " + g.MeanCte.ToString("0.00") + " / max " + g.MaxCte.ToString("0.00")
                    + " m, vmax " + g.MaxSpeed.ToString("0.00") + " m/s, " + g.MicrosPerCall.ToString("0") + " us/call");
            if (Path != null) s.Add("Ceiling " + Ceiling.ToString("0.0#") + " m/s; lap-time lower bound (standing, this line) " + LowerBound.ToString("0.00") + " s. Reference only - not autonomy.");
            return s.ToArray();
        }
    }
}
