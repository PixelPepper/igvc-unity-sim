using System;
using IGVC;
using UnityEngine;

public static class CasterSuspensionChecks
{
    public static void Run()
    {
        int count = 0;
        void Check(bool condition, string name)
        {
            if (!condition) throw new Exception("Caster suspension check failed: " + name);
            count++;
        }
        bool Same(CasterSuspension a, CasterSuspension b) => a.Height == b.Height
            && a.Velocity == b.Velocity && a.LeftCompression == b.LeftCompression
            && a.RightCompression == b.RightCompression;
        bool Throws(Action action)
        {
            try { action(); return false; }
            catch (ArgumentOutOfRangeException) { return true; }
        }
        var s = new CasterSuspension();
        Check(s.Reset(0, 0) && s.Step(0, 0, .1) && s.Height == 0 && s.Velocity == 0, "flat rest");
        Check(s.Step(.02, .02, .01) && s.Height > 0 && s.Height < .02
            && s.Velocity > 0, "symmetric rise has compliant lag");
        double earlyEnergy = 12000 * Math.Pow(.02 - s.Height, 2) + 15 * s.Velocity * s.Velocity;
        bool settledSteps = true;
        for (int i = 0; i < 100; i++) settledSteps &= s.Step(.02, .02, .01);
        Check(settledSteps, "settling integration accepted");
        double lateEnergy = 12000 * Math.Pow(.02 - s.Height, 2) + 15 * s.Velocity * s.Velocity;
        Check(Math.Abs(s.Height - .02) < 1e-8 && Math.Abs(s.Velocity) < 1e-7
            && lateEnergy < earlyEnergy * 1e-8, "damping dissipates transient and settles");
        Check(s.Reset(.02, 0) && Math.Abs(s.Height - .01) < 1e-12
            && Math.Abs(s.LeftCompression - .01) < 1e-12
            && Math.Abs(s.RightCompression + .01) < 1e-12 && s.Velocity == 0, "one-sided rest and reset without kick");
        s.Step(.03, .03, .01);
        Check(s.Velocity > 0 && s.Step(.04, -.04, .01) && s.Height == 0 && s.Velocity == 0
            && s.LeftCompression == .04 && s.RightCompression == -.04, "both hard stops arrest outward velocity");
        var before = s.Copy();
        Check(!s.Step(.041, -.041, .01) && Same(s, before)
            && !s.Reset(.041, -.041) && Same(s, before), "infeasible twist is transactional");
        Check(s.Step(.01, .01, 0) && Same(s, before), "zero dt freezes all state");
        Check(!s.Step(double.NaN, 0, .01) && !s.Step(0, double.PositiveInfinity, .01)
            && !s.Step(0, 0, double.NaN) && !s.Step(0, 0, -.01)
            && !s.Step(0, 0, .100001) && !s.Reset(0, double.NaN)
            && Same(s, before), "invalid values and dt bounds preserve state");
        Check(Throws(() => new CasterSuspension(mass: 0))
            && Throws(() => new CasterSuspension(springStiffness: -1))
            && Throws(() => new CasterSuspension(damping: -1))
            && Throws(() => new CasterSuspension(travel: 0))
            && Throws(() => new CasterSuspension(mass: double.NaN))
            && Throws(() => new CasterSuspension(springStiffness: double.PositiveInfinity))
            && Throws(() => new CasterSuspension(damping: double.NaN))
            && Throws(() => new CasterSuspension(travel: double.PositiveInfinity)), "constructor constraints");
        var copy = new CasterSuspension(40, 9000, 500, .03);
        copy.Reset(.01, .02);
        copy.Step(.025, .025, .02);
        var clone = copy.Copy();
        Check(Same(copy, clone) && copy.Step(.03, .03, .01)
            && !Same(copy, clone) && clone.Step(.03, .03, .01) && Same(copy, clone), "copy preserves configuration and independent state");
        var fine = new CasterSuspension();
        var coarse = new CasterSuspension();
        for (int i = 0; i < 200; i++) fine.Step(.02, .01, .001);
        for (int i = 0; i < 10; i++) coarse.Step(.02, .01, .02);
        Check(Math.Abs(fine.Height - coarse.Height) < 1e-12
            && Math.Abs(fine.Velocity - coarse.Velocity) < 1e-12, "subdivision robustness");
        Check(s.Reset(0, 0) && s.Height == 0 && s.Velocity == 0
            && s.LeftCompression == 0 && s.RightCompression == 0, "reset restores nominal CAD rest");
        Debug.Log("IGVC_CASTER_SUSPENSION_CHECKS_OK count=" + count);
    }
}
