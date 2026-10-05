using System;
using System.Collections.Generic;
using IGVC.Reference.RacingLine;

namespace IGVC.Reference.Drivers
{
    /// <summary>
    /// One deterministic training run of one genome: the robot starts at rest on the start line and drives until a
    /// whole-body contact (crash), a stall (under StallDistance of progress in StallTime), one lap, or the time limit.
    /// fitness = progress along the corridor (m) + 2 * (time left when the lap is complete).
    /// </summary>
    public sealed class Episode
    {
        public const double Dt = DriversStudy.Dt, StallTime = 4, StallDistance = .3;
        public readonly double TimeLimit;
        public readonly NeuralDriver Driver;
        public RobotState State;
        public double Time { get; private set; }
        public double Progress { get; private set; }
        public bool Done { get; private set; }
        public bool Crashed { get; private set; }
        public bool Finished { get; private set; }
        public double Fitness { get; private set; }
        private readonly DriveContext ctx;
        private double lastS, stallTimer, stallRef;

        public Episode(double[] genome, DriveContext ctx)
        {
            Driver = new NeuralDriver(genome); this.ctx = ctx;
            State = DriversStudy.StartState(ctx.World.Corridor);
            TimeLimit = 10 + ctx.World.Corridor.Length / (.5 * Math.Max(.2, ctx.Ceiling));
        }

        public void Step()
        {
            if (Done) return;
            ctx.Time = Time;
            Driver.Act(ref State, ctx, out double v, out double w);
            DiffDrive.Step(ref State, v, w, Dt, ctx.Limits);
            Time += Dt;
            var cor = ctx.World.Corridor;
            int hint = State.Hint;
            bool hit = ctx.World.Contact(State.Pos, State.Heading, ref hint) != null;
            State.Hint = hint;
            cor.Project(State.Pos, out double s, out _, hint, 4);
            double ds = s - lastS;
            if (ds < -cor.Length / 2) ds += cor.Length; else if (ds > cor.Length / 2) ds -= cor.Length;
            Progress += ds; lastS = s;
            if (hit) { Crashed = true; Finish(); return; }
            stallTimer += Dt;
            if (stallTimer >= StallTime) { if (Progress - stallRef < StallDistance) { Finish(); return; } stallTimer = 0; stallRef = Progress; }
            if (Progress >= cor.Length) { Finished = true; Finish(); return; }
            if (Time >= TimeLimit) Finish();
        }
        private void Finish() { Done = true; Fitness = Progress + (Finished ? 2 * (TimeLimit - Time) : 0); }
        public double Run() { while (!Done) Step(); return Fitness; }
    }

    /// <summary>
    /// Generational GA over network weights (neuroevolution): elitism (elites keep their deterministic fitness, so the
    /// best never decreases), tournament selection, per-neuron crossover (each neuron's incoming weights from one
    /// parent), Gaussian mutation with occasional resets.
    /// </summary>
    public sealed class NeuroGA
    {
        public int Population, Elite = 3, Tournament = 3;
        public double CrossoverRate = .75, MutationRate = .09, MutationSigma = .35, ResetRate = .01;
        public double[][] Genomes { get; private set; }
        public double[] Fitness { get; private set; }
        public bool[] Evaluated { get; private set; }
        public int Generation { get; private set; }
        public double[] Best { get; private set; }
        public double BestFitness { get; private set; } = double.MinValue;
        public readonly List<double> BestHistory = new List<double>(), MeanHistory = new List<double>();
        public readonly List<int> FinishersHistory = new List<int>();
        private readonly SplitMix rng;

        public NeuroGA(ulong seed, double[] seedGenome = null, int population = 24)
        {
            rng = new SplitMix(seed); Population = population;
            Genomes = new double[Population][]; Fitness = new double[Population]; Evaluated = new bool[Population];
            for (int p = 0; p < Population; p++)
            {
                var g = new double[NeuralNet.GenomeSize];
                if (seedGenome != null && p < Population / 2) { Array.Copy(seedGenome, g, g.Length); if (p > 0) Mutate(g, 2); }
                else RandomGenome(g);
                Genomes[p] = g;
            }
        }
        public void RandomGenome(double[] g)
        {
            for (int j = 0; j < NeuralNet.Hidden; j++)
                for (int i = 0; i <= NeuralNet.Inputs; i++) g[NeuralNet.WIH(i, j)] = rng.Gauss() * (1.6 / Math.Sqrt(NeuralNet.Inputs + 1));
            for (int o = 0; o < NeuralNet.Outputs; o++)
                for (int j = 0; j <= NeuralNet.Hidden; j++) g[NeuralNet.WHO(j, o)] = rng.Gauss() * (1.6 / Math.Sqrt(NeuralNet.Hidden + 1));
        }
        private void Mutate(double[] g, double scale)
        {
            for (int k = 0; k < g.Length; k++)
            {
                double r = rng.NextDouble();
                if (r < ResetRate) g[k] = rng.Gauss();
                else if (r < ResetRate + MutationRate * scale) g[k] += rng.Gauss() * MutationSigma;
            }
        }
        public void SetFitness(int p, double f) { Fitness[p] = f; Evaluated[p] = true; }
        public int NextUnevaluated() { for (int p = 0; p < Population; p++) if (!Evaluated[p]) return p; return -1; }

        /// <summary>Records the statistics of the fully evaluated generation.</summary>
        public void Record(int finishers)
        {
            int bi = 0; double mean = 0;
            for (int p = 0; p < Population; p++) { mean += Fitness[p]; if (Fitness[p] > Fitness[bi]) bi = p; }
            if (Fitness[bi] > BestFitness || Best == null) { BestFitness = Fitness[bi]; Best = (double[])Genomes[bi].Clone(); }
            BestHistory.Add(Fitness[bi]); MeanHistory.Add(mean / Population); FinishersHistory.Add(finishers);
        }

        /// <summary>Breeds the next generation from the evaluated one (elites carry their fitness over).</summary>
        public void Breed()
        {
            var order = new int[Population];
            for (int i = 0; i < Population; i++) order[i] = i;
            Array.Sort(order, (a, b) => Fitness[a] != Fitness[b] ? Fitness[b].CompareTo(Fitness[a]) : a.CompareTo(b));
            var next = new double[Population][]; var nextFit = new double[Population]; var nextEval = new bool[Population];
            for (int e = 0; e < Elite; e++) { next[e] = (double[])Genomes[order[e]].Clone(); nextFit[e] = Fitness[order[e]]; nextEval[e] = true; }
            for (int p = Elite; p < Population; p++)
            {
                var child = (double[])Genomes[Select()].Clone();
                if (rng.NextDouble() < CrossoverRate)
                {
                    var b = Genomes[Select()];
                    for (int j = 0; j < NeuralNet.Hidden; j++)
                        if (rng.NextDouble() < .5) for (int i = 0; i <= NeuralNet.Inputs; i++) child[NeuralNet.WIH(i, j)] = b[NeuralNet.WIH(i, j)];
                    for (int o = 0; o < NeuralNet.Outputs; o++)
                        if (rng.NextDouble() < .5) for (int j = 0; j <= NeuralNet.Hidden; j++) child[NeuralNet.WHO(j, o)] = b[NeuralNet.WHO(j, o)];
                }
                Mutate(child, 1);
                next[p] = child;
            }
            Genomes = next; Fitness = nextFit; Evaluated = nextEval; Generation++;
        }
        private int Select()
        {
            int best = rng.Range(Population);
            for (int t = 1; t < Tournament; t++) { int c = rng.Range(Population); if (Fitness[c] > Fitness[best]) best = c; }
            return best;
        }
    }

    /// <summary>
    /// Seeded, budgeted, frame-steppable neuroevolution: each Advance() runs at most StepBudget simulation steps of the
    /// current episode, so a caller can spread training over frames. Same seed and inputs give the same genomes.
    /// </summary>
    public sealed class NeuroTrainer
    {
        public readonly NeuroGA GA;
        public int StepBudget = 200;
        private readonly DriveContext ctx;
        private Episode current;
        private int currentGenome = -1, finishers;

        public NeuroTrainer(DriveContext ctx, ulong seed, int population = 24, double[] seedGenome = null)
        {
            this.ctx = ctx; GA = new NeuroGA(seed, seedGenome, population);
        }
        public bool GenerationEvaluated => current == null && GA.NextUnevaluated() < 0;

        /// <summary>Advances the current evaluation; returns a status line.</summary>
        public string Advance()
        {
            if (current == null)
            {
                currentGenome = GA.NextUnevaluated();
                if (currentGenome < 0) return "generation " + GA.Generation + " evaluated";
                current = new Episode(GA.Genomes[currentGenome], ctx);
            }
            for (int k = 0; k < StepBudget && !current.Done; k++) current.Step();
            if (!current.Done) return "gen " + GA.Generation + " genome " + currentGenome + " t " + current.Time.ToString("0.0") + " s";
            GA.SetFitness(currentGenome, current.Fitness);
            if (current.Finished) finishers++;
            string line = "gen " + GA.Generation + " genome " + currentGenome + "/" + GA.Population + " fitness " + current.Fitness.ToString("0.0") + (current.Crashed ? " (contact)" : current.Finished ? " (lap)" : "");
            current = null;
            return line;
        }

        /// <summary>Evaluates the current generation, records it, and breeds until <paramref name="generations"/> more have been recorded.</summary>
        public IEnumerable<string> Train(int generations)
        {
            for (int g = 0; g <= generations; g++)
            {
                if (GA.BestHistory.Count > GA.Generation) GA.Breed(); // a generation already recorded by an earlier call
                finishers = 0;
                while (!GenerationEvaluated) yield return Advance();
                GA.Record(finishers);
                yield return "generation " + GA.Generation + ": best " + GA.BestHistory[GA.BestHistory.Count - 1].ToString("0.0") + ", mean " + GA.MeanHistory[GA.MeanHistory.Count - 1].ToString("0.0") + ", laps " + finishers;
            }
        }
    }
}
