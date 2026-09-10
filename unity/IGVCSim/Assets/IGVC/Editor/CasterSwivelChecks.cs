using System;
using IGVC;
using UnityEngine;

public static class CasterSwivelChecks
{
    public static void Run()
    {
        int count = 0;
        void Check(bool value, string name)
        {
            if (!value) throw new Exception("Caster swivel check failed: " + name);
            count++;
        }
        bool Throws(Action action)
        {
            try { action(); return false; }
            catch (ArgumentOutOfRangeException) { return true; }
        }
        var s = new CasterSwivel();
        Check(s.Step(1, 0, .1) && s.Angle == 0 && s.Velocity == 0, "forward rest");
        Check(s.Step(-1, 0, .01) && Math.Abs(s.Angle - .04) < 1e-12
            && Math.Abs(s.Velocity - 4) < 1e-12, "exact reverse chooses positive antipodal turn with rate cap");
        for (int i = 0; i < 300; i++) s.Step(-1, 0, .01);
        Check(Math.Abs(s.Angle - Math.PI) < 1e-7, "reverse converges to pi");
        var left = new CasterSwivel();
        var right = new CasterSwivel();
        left.Step(1, 1, .01); right.Step(1, -1, .01);
        Check(left.Angle > 0 && right.Angle < 0 && Math.Abs(left.Angle + right.Angle) < 1e-12,
            "left and right directions are symmetric");
        double before = s.Angle;
        Check(s.Step(-1, -.02, .01) && s.Angle > before && s.Angle > Math.PI
            && s.Angle - before < .04, "crossing pi takes continuous short positive path");
        bool bounded = true, feedback = true;
        for (int i = 0; i < 300; i++)
        {
            before = s.Angle;
            bounded &= s.Step(Math.Cos(i * .17), Math.Sin(i * .17), .01)
                && Math.Abs(s.Angle - before) <= .040000000001;
            feedback &= Math.Abs(s.Velocity - (s.Angle - before) / .01) < 1e-12;
        }
        Check(bounded && feedback, "rate bound and actual increment velocity through repeated turns");
        before = s.Angle;
        Check(s.Step(.003, .004, .01) && s.Angle == before && s.Velocity == 0,
            "stationary threshold holds previous angle");
        s.Step(0, 1, .01);
        before = s.Angle;
        double previousVelocity = s.Velocity;
        Check(s.Step(-1, -1, 0) && s.Angle == before && s.Velocity == previousVelocity,
            "pause freezes angle and velocity");
        Check(!s.Step(double.NaN, 0, .01) && !s.Step(0, double.PositiveInfinity, .01)
            && !s.Step(1, 0, -.01) && !s.Step(1, 0, .100001) && !s.Step(1, 0, double.NaN)
            && !s.Step(double.MaxValue, double.MaxValue, .01)
            && s.Angle == before && s.Velocity == previousVelocity, "invalid input rejects transactionally");
        Check(Throws(() => new CasterSwivel(alignmentDistance: 0))
            && Throws(() => new CasterSwivel(alignmentDistance: double.NaN))
            && Throws(() => new CasterSwivel(maxRate: -1))
            && Throws(() => new CasterSwivel(maxRate: double.PositiveInfinity))
            && Throws(() => new CasterSwivel(stationarySpeed: -.001))
            && Throws(() => new CasterSwivel(stationarySpeed: double.NaN)), "configuration validation");
        var slow = new CasterSwivel(maxRate: 100);
        var fast = new CasterSwivel(maxRate: 100);
        for (int i = 0; i < 100; i++) slow.Step(0, .1, .01);
        for (int i = 0; i < 50; i++) fast.Step(0, .2, .01);
        double expected = Math.PI / 2 * (1 - Math.Exp(-.1 / .12));
        Check(Math.Abs(slow.Angle - expected) < 1e-12 && Math.Abs(fast.Angle - expected) < 1e-12,
            "equal traveled distance produces analytical exponential response at different speeds");
        s.Reset();
        Check(s.Angle == 0 && s.Velocity == 0, "reset clears all state");
        Debug.Log("IGVC_CASTER_SWIVEL_CHECKS_OK count=" + count);
    }
}
