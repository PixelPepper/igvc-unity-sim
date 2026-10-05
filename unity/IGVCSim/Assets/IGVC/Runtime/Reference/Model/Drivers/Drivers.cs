using System;
using IGVC.Reference.RacingLine;

namespace IGVC.Reference.Drivers
{
    /// <summary>What a controller gets every control tick.</summary>
    public sealed class DriveContext
    {
        public DriveWorld World;
        public RefPath Path;
        public RobotLimits Limits;
        public double Ceiling, Time;
        /// <summary>The reference line's per-station lateral bounds (its gap through each obstacle group), or null.</summary>
        public double[] Lo, Hi;
    }

    public interface IDriver
    {
        string Name { get; }
        /// <summary>Linear (m/s) and angular (rad/s) velocity command for the state; DiffDrive saturates it.</summary>
        void Act(ref RobotState s, DriveContext ctx, out double v, out double w);
        void Reset();
    }

    internal static class SpeedRules
    {
        /// <summary>Plan speed at s with a short preview so braking starts before the wheel accel lag bites.</summary>
        public static double Speed(DriveContext ctx, double s, double v) => Math.Min(ctx.Path.SpeedAt(s), ctx.Path.SpeedAt(s + .3 + .5 * Math.Abs(v)));
        public static double Cap(DriveContext ctx, double k) => LapSim.Cap(k, ctx.Limits, ctx.Ceiling);
    }

    /// <summary>
    /// Regulated pure pursuit in the spirit of Nav2 RPP: look-ahead distance = speed x LookaheadTime (clamped), target =
    /// first path point at least that far from the axle, curvature k = 2 y / d^2 in the robot frame. Linear speed is
    /// regulated by the path speed plan, by curvature (below MinRadius it scales with r / MinRadius) and by proximity
    /// (whole-body clearance under ProximityDist scales it down). Rotates in place when the target is far off the nose.
    /// </summary>
    public sealed class PurePursuit : IDriver
    {
        public double LookaheadTime = 1.5, MinLookahead = .8, MaxLookahead = 2.5, MinRadius = 1.0, ProximityDist = .08, MinProximityScale = .5;
        public double MinSpeed = .1, RotateThreshold = .9, RotateSpeed = .8;
        public string Name => "Pure pursuit (RPP)";
        public V2 Target { get; private set; }
        public double Lookahead { get; private set; }
        public double Curvature { get; private set; }
        private int hint = -1;
        public void Reset() { hint = -1; }

        public void Act(ref RobotState s, DriveContext ctx, out double v, out double w)
        {
            var path = ctx.Path;
            hint = path.Project(s.Pos, hint, out double sp, out _);
            Lookahead = Math.Max(MinLookahead, Math.Min(MaxLookahead, LookaheadTime * Math.Abs(s.V)));
            double st = sp; V2 target = path.PointAt(st);
            for (int k = 0; k < 200 && V2.Distance(target, s.Pos) < Lookahead; k++) { st += .05; target = path.PointAt(st); }
            Target = target;
            V2 d = target - s.Pos, f = s.Forward; double dx = V2.Dot(d, f), dy = V2.Cross(f, d), d2 = Math.Max(1e-6, dx * dx + dy * dy);
            Curvature = 2 * dy / d2;
            if (Math.Abs(Math.Atan2(dy, dx)) > RotateThreshold) { v = 0; w = Math.Sign(dy) * RotateSpeed; return; }
            v = SpeedRules.Speed(ctx, sp, s.V);
            double radius = 1 / Math.Max(1e-9, Math.Abs(Curvature));
            if (radius < MinRadius) v *= radius / MinRadius;
            int h = s.Hint; double clear = ctx.World.Clearance(s.Pos, s.Heading, ref h);
            if (clear < ProximityDist) v *= Math.Max(MinProximityScale, clear / ProximityDist);
            v = Math.Max(MinSpeed, Math.Min(v, SpeedRules.Cap(ctx, Curvature)));
            w = v * Curvature;
        }
    }

    /// <summary>
    /// Stanley adapted to a unicycle at the axle: omega = v k_path (feed-forward) + KHeading (heading error -
    /// atan(K e / (KSoft + v))), with e the signed cross-track error to the reference line. Speed from the plan with
    /// the same curvature regulation as pure pursuit.
    /// </summary>
    public sealed class Stanley : IDriver
    {
        public double K = 1.2, KSoft = .4, KHeading = 2.0, MinRadius = 1.0, MinSpeed = .1;
        public bool FeedForward = true;
        public string Name => "Stanley";
        public V2 PathPoint { get; private set; }
        public double CrossTrack { get; private set; }
        private int hint = -1;
        public void Reset() { hint = -1; }

        public void Act(ref RobotState s, DriveContext ctx, out double v, out double w)
        {
            var path = ctx.Path;
            hint = path.Project(s.Pos, hint, out double sp, out double e);
            CrossTrack = e; PathPoint = path.PointAt(sp);
            double k = path.KappaAt(sp), he = DiffDrive.Wrap(path.HeadingAt(sp) - s.Heading);
            v = SpeedRules.Speed(ctx, sp, s.V);
            double radius = 1 / Math.Max(1e-9, Math.Abs(k));
            if (radius < MinRadius) v *= radius / MinRadius;
            v = Math.Max(MinSpeed, Math.Min(v, SpeedRules.Cap(ctx, k)));
            w = (FeedForward ? v * k : 0) + KHeading * (he - Math.Atan(K * e / (KSoft + Math.Abs(s.V))));
        }
    }

    /// <summary>
    /// Sampling MPC over (v, omega), in the family of DWA / MPPI. Every Replan seconds it rolls the same DiffDrive model
    /// forward for Horizon seconds under a grid of controls - curvature offset from the line's curvature for the first
    /// Switch seconds and another after (5 x 5), times 3 speed levels of the plan = 75 rollouts - and applies the start of
    /// the cheapest:
    /// <code>
    ///   cost = - WProgress * progress along the corridor / ceiling + sum (WTrack e_line^2 + WHeading heading_error^2) dt
    ///          + WGap * (lateral offset outside the line's gap [lo, hi] + slack)^2 dt   (stay on the line's side of each obstacle)
    ///          + WClear * (Margin - clearance)^2   (whole-body rectangle clearance to edges and obstacles)
    ///          + WHit * (1 + steps left) on contact (rollout stops)
    ///          + WSpeed * max(0, v_end - 1.1 v_plan)^2 + WSmooth * |change of first curvature offset|
    /// </code>
    /// </summary>
    public sealed class SamplingMpc : IDriver
    {
        public double[] CurvatureOffsets = { -1.0, -.35, 0, .35, 1.0 };
        public double[] SpeedLevels = { 1, .6, .25 };
        public double Horizon = 2.0, Dt = .1, Switch = .5, Replan = .2;
        public double Margin = .08, WProgress = 2, WTrack = 3, WHeading = 2, WGap = 50, GapSlack = .15, WClear = 40, WHit = 200, WSpeed = 2, WSmooth = .5;
        public string Name => "Sampling MPC";
        public int Candidates => CurvatureOffsets.Length * CurvatureOffsets.Length * SpeedLevels.Length;
        public int Steps => (int)Math.Round(Horizon / Dt);
        /// <summary>Rollout points (every 2nd step) per candidate, for drawing.</summary>
        public V2[][] Paths { get; private set; }
        public double[] Costs { get; private set; }
        public int Best { get; private set; } = -1;
        public long Rollouts { get; private set; }
        private double nextPlan = -1, bestOffset, bestLevel = 1;
        private int hint = -1;

        public void Reset() { nextPlan = -1; Best = -1; bestOffset = 0; bestLevel = 1; hint = -1; }

        public void Act(ref RobotState s, DriveContext ctx, out double v, out double w)
        {
            if (Paths == null || Paths.Length != Candidates || Paths[0].Length != Steps / 2 + 1)
            {
                Paths = new V2[Candidates][];
                for (int c = 0; c < Candidates; c++) Paths[c] = new V2[Steps / 2 + 1];
                Costs = new double[Candidates];
            }
            hint = ctx.Path.Project(s.Pos, hint, out double sp, out _);
            if (ctx.Time >= nextPlan - 1e-9) { nextPlan = ctx.Time + Replan; Plan(s, ctx); }
            v = bestLevel * SpeedRules.Speed(ctx, sp, s.V);
            w = v * (ctx.Path.KappaAt(sp) + bestOffset);
        }

        private void Plan(RobotState s0, DriveContext ctx)
        {
            var path = ctx.Path; var cor = ctx.World.Corridor; var lim = ctx.Limits;
            int steps = Steps, switchStep = (int)Math.Round(Switch / Dt), c = 0;
            cor.Project(s0.Pos, out double startS, out _, s0.Hint, 4);
            double best = double.MaxValue;
            foreach (double ka in CurvatureOffsets)
                foreach (double kb in CurvatureOffsets)
                    foreach (double level in SpeedLevels)
                    {
                        var s = s0; int ph = hint; double cost = 0, prog = 0, lastS = startS, sp = 0;
                        var pts = Paths[c]; pts[0] = s.Pos; int filled = 0;
                        for (int k = 0; k < steps; k++)
                        {
                            ph = path.Project(s.Pos, ph, out sp, out double e, 4);
                            double vt = level * SpeedRules.Speed(ctx, sp, s.V), kk = path.KappaAt(sp) + (k < switchStep ? ka : kb);
                            DiffDrive.Step(ref s, vt, vt * kk, Dt, lim);
                            s.Hint = cor.Project(s.Pos, out double cs, out double cd, s.Hint, 3);
                            if (ctx.Lo != null) { double out_ = Math.Max(0, Math.Max(ctx.Lo[s.Hint] - GapSlack - cd, cd - ctx.Hi[s.Hint] - GapSlack)); cost += WGap * out_ * out_ * Dt; }
                            double ds = cs - lastS;
                            if (ds < -cor.Length / 2) ds += cor.Length; else if (ds > cor.Length / 2) ds -= cor.Length;
                            prog += ds; lastS = cs;
                            double he = DiffDrive.Wrap(path.HeadingAt(sp) - s.Heading);
                            cost += (WTrack * e * e + WHeading * he * he) * Dt;
                            double clear = ctx.World.QuickClearance(s.Pos, s.Heading, s.Hint);
                            if ((k & 1) == 1) pts[filled = (k + 1) / 2] = s.Pos;
                            if (clear < 0) { cost += WHit * (1 + (steps - k) / (double)steps); break; }
                            if (clear < Margin) cost += WClear * (Margin - clear) * (Margin - clear);
                        }
                        for (int j = filled + 1; j < pts.Length; j++) pts[j] = pts[filled];
                        double over = s.V - 1.1 * path.SpeedAt(sp);
                        if (over > 0) cost += WSpeed * over * over;
                        cost += WSmooth * Math.Abs(ka - bestOffset) - WProgress * prog / Math.Max(.2, ctx.Ceiling);
                        Costs[c] = cost;
                        if (cost < best) { best = cost; Best = c; }
                        c++;
                    }
            int n = SpeedLevels.Length, m = CurvatureOffsets.Length;
            bestOffset = CurvatureOffsets[Best / (m * n)]; bestLevel = SpeedLevels[Best % n];
            Rollouts += Candidates;
        }
    }

    /// <summary>
    /// Feed-forward network: 9 inputs (7 range sensors / range, v / ceiling, omega / max yaw rate) -&gt; 10 tanh -&gt;
    /// 2 tanh (speed, turn). The weights are a flat genome for neuroevolution; no gradient training.
    /// </summary>
    public sealed class NeuralNet
    {
        public const int Inputs = 9, Hidden = 10, Outputs = 2;
        public const int GenomeSize = (Inputs + 1) * Hidden + (Hidden + 1) * Outputs;
        public readonly double[] W;
        public readonly double[] In = new double[Inputs], H = new double[Hidden], Out = new double[Outputs];
        public NeuralNet(double[] genome)
        {
            if (genome.Length != GenomeSize) throw new ArgumentException("genome needs " + GenomeSize + " weights");
            W = genome;
        }
        public static int WIH(int i, int j) => j * (Inputs + 1) + i;
        public static int WHO(int j, int o) => (Inputs + 1) * Hidden + o * (Hidden + 1) + j;
        public void Forward()
        {
            for (int j = 0; j < Hidden; j++)
            {
                double a = W[WIH(Inputs, j)];
                for (int i = 0; i < Inputs; i++) a += W[WIH(i, j)] * In[i];
                H[j] = Math.Tanh(a);
            }
            for (int o = 0; o < Outputs; o++)
            {
                double a = W[WHO(Hidden, o)];
                for (int j = 0; j < Hidden; j++) a += W[WHO(j, o)] * H[j];
                Out[o] = Math.Tanh(a);
            }
        }
    }

    /// <summary>
    /// Drives with a <see cref="NeuralNet"/> fed by range sensors from the axle: sphere-traced rays against the signed
    /// road field and the obstacle capsules. Speed = ceiling * (0.5 + 0.5 out0) (forward only), turn = out1 * max yaw rate.
    /// </summary>
    public sealed class NeuralDriver : IDriver
    {
        public static readonly double[] SensorAngles = { -90, -50, -22, 0, 22, 50, 90 };
        public const double SensorRange = 5;
        public readonly NeuralNet Net;
        public readonly double[] Ranges = new double[SensorAngles.Length];
        public readonly V2[] RayEnds = new V2[SensorAngles.Length];
        public V2 RayOrigin { get; private set; }
        public string Label = "Neuroevolution";
        public string Name => Label;
        public NeuralDriver(double[] genome) { Net = new NeuralNet(genome); }
        public void Reset() { }

        public void Act(ref RobotState s, DriveContext ctx, out double v, out double w)
        {
            var near = ctx.World.Far[s.Hint < 0 ? ctx.World.Station(s.Pos, -1) : s.Hint];
            RayOrigin = s.Pos;
            for (int i = 0; i < Ranges.Length; i++)
            {
                V2 dir = V2.FromAngle(s.Heading + SensorAngles[i] * Math.PI / 180);
                Ranges[i] = ctx.World.Raycast(s.Pos, dir, SensorRange, near);
                RayEnds[i] = s.Pos + dir * Ranges[i];
                Net.In[i] = Ranges[i] / SensorRange;
            }
            Net.In[7] = s.V / Math.Max(.1, ctx.Ceiling);
            Net.In[8] = s.Omega / ctx.Limits.MaxYawRate;
            Net.Forward();
            v = ctx.Ceiling * (.5 + .5 * Net.Out[0]);
            w = Net.Out[1] * ctx.Limits.MaxYawRate;
        }
    }
}
