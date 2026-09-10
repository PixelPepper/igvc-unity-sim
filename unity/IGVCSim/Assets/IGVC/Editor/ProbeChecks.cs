using System;
using System.IO;
using IGVC;
using UnityEngine;

public static class ProbeChecks
{
    public static void Run()
    {
        int count = 0;
        void Check(bool value, string name) { if (!value) throw new Exception("FAIL " + name); count++; Debug.Log("PASS " + name); }
        var m = new ProbeMotion();
        m.Command(1, 0, 100, 100, 0);
        for (int i = 0; i < 50; i++) m.Step(0.01, i * 0.01, true);
        Check(m.X > 0.2 && Math.Abs(m.Y) < 1e-8, "ROS positive X forward");
        m.Step(0.01, 0.51, true);
        Check(m.Linear == 0, "monotonic watchdog");
        double x = m.X;
        m.Command(1, 0, 98, 100, 1); m.Step(0.01, 1, true);
        Check(m.X == x, "stale network command rejected");
        m.Command(1, 0, 102, 100, 1); m.Step(0.01, 1, true);
        Check(m.X == x, "future timestamp rejected");
        m.Command(double.NaN, 0, 100, 100, 1); m.Step(0.01, 1, true);
        Check(m.X == x, "nonfinite command rejected");
        m.SetPaused(true, 100); m.Command(1, 0, 100.1, 100.1, 2); m.Step(0.01, 2, true);
        Check(m.X == x, "pause blocks commands");
        m.SetPaused(false, 101); m.Command(1, 0, 100.9, 101, 2); m.Step(0.01, 2, true);
        Check(m.X == x, "unpause rejects previous command");
        m.Command(0, 1, 101.1, 101.1, 2); m.Step(0.1, 2, true);
        Check(m.Yaw > 0, "positive yaw turns left");
        m.SetStopped(true, 101); m.Step(0.1, 2, true);
        Check(m.Linear == 0 && m.Angular == 0, "latched stop overrides command");
        m.Reset(102);
        Check(m.X == 0 && m.Y == 0 && m.Yaw == 0 && m.Stopped, "reset preserves stop latch");
        m.SetStopped(false, 102); m.Command(1, 0, 102.1, 102.1, 3); m.Step(0.1, 3, true);
        Check(m.Linear > 0, "fresh command after stop clear");
        x = m.X; m.Step(0.1, 3.1, false);
        Check(m.X == x && m.Linear == 0, "disconnect stops active motion");
        var fast = new ProbeMotion();
        for (int i = 0; i < 150; i++)
        {
            double now = i * 0.01;
            fast.Command(100, 0, now, now, now);
            double previous = fast.Linear;
            fast.Step(0.01, now, true);
            if (fast.Linear > 2.2 + 1e-10 || fast.Linear - previous > 0.02 + 1e-10)
                throw new Exception("FAIL forward speed or acceleration exceeded");
        }
        Check(Math.Abs(fast.Linear - 2.2) < 1e-10, "overspeed input saturates at 2.2 m/s with 2 m/s squared ramp");
        Check(fast.Angular == 0, "straight overspeed input remains straight");
        fast.Command(0, 0, 1.5, 1.5, 1.5); fast.Step(0.1, 1.5, true);
        Check(Math.Abs(fast.Linear - 2.0) < 1e-10, "commanded deceleration remains 2 m/s squared");
        fast.Step(0.01, 2.01, true);
        Check(fast.Linear == 0 && fast.Angular == 0, "watchdog immediately stops high speed without ramp delay");
        var reverse = new ProbeMotion();
        reverse.Command(-100, -100, 0, 0, 0); reverse.Step(0.1, 0, true);
        Check(Math.Abs(reverse.Linear + 0.2) < 1e-10 && reverse.X < 0, "reverse recovery ramps backward from rest");
        for (int i = 1; i <= 40; i++)
        {
            double now = i * 0.01;
            reverse.Command(-100, -100, now, now, now); reverse.Step(0.01, now, true);
        }
        Check(Math.Abs(reverse.Linear + 0.3) < 1e-10, "reverse overspeed saturates at 0.3 m/s");
        Check(Math.Abs(reverse.Angular + 0.3) < 1e-10, "reverse saturation preserves requested curvature");
        var curve = new ProbeMotion();
        const double commandedTurn = -0.7222541173;
        curve.Command(2.2, commandedTurn, 0, 0, 0); curve.Step(0.01, 0, true);
        Check(Math.Abs(curve.Linear - 0.02) < 1e-10
            && Math.Abs(curve.Angular - commandedTurn * 0.02 / 2.2) < 1e-10,
            "reported Nav2 launch preserves first-step commanded curvature");
        for (int i = 1; i <= 150; i++)
        {
            double now = i * 0.01;
            curve.Command(2.2, commandedTurn, now, now, now); curve.Step(0.01, now, true);
            if (Math.Abs(curve.Angular / curve.Linear - commandedTurn / 2.2) > 1e-9)
                throw new Exception("FAIL startup curvature tightened during linear ramp");
        }
        Check(Math.Abs(curve.Linear - 2.2) < 1e-10, "startup curvature retained through full speed");
        curve.Command(0, 0, 1.51, 1.51, 1.51); curve.Step(0.1, 1.51, true);
        Check(Math.Abs(curve.Linear - 2.0) < 1e-10
            && Math.Abs(curve.Angular - (commandedTurn + 0.3)) < 1e-10,
            "zero command decelerates both axes with existing rates");
        var pivot = new ProbeMotion();
        pivot.Command(0, 1, 0, 0, 0); pivot.Step(0.1, 0, true);
        Check(pivot.Linear == 0 && Math.Abs(pivot.Angular - 0.3) < 1e-10,
            "zero linear target retains in-place angular ramp");
        var reversal = new ProbeMotion();
        reversal.Command(0.2, 0.1, 0, 0, 0); reversal.Step(0.1, 0, true);
        reversal.Command(-0.2, -0.1, 0.1, 0.1, 0.1); reversal.Step(0.1, 0.1, true);
        Check(Math.Abs(reversal.Linear) < 1e-10 && Math.Abs(reversal.Angular) < 1e-10,
            "controlled direction reversal reaches zero without angular kick");
        reversal.Command(-0.2, -0.1, 0.2, 0.2, 0.2); reversal.Step(0.05, 0.2, true);
        Check(Math.Abs(reversal.Linear + 0.1) < 1e-10 && Math.Abs(reversal.Angular + 0.05) < 1e-10,
            "reverse launch scales angular target with reverse linear ramp");
        var saturatedTurn = new ProbeMotion();
        for (int i = 0; i < 150; i++)
        {
            double now = i * 0.01;
            saturatedTurn.Command(2.2, 2, now, now, now); saturatedTurn.Step(0.01, now, true);
        }
        Check(Math.Abs(saturatedTurn.Linear - 1.1) < 1e-10 && Math.Abs(saturatedTurn.Angular - 1) < 1e-10,
            "angular saturation proportionally reduces linear speed instead of understeering");
        var saturatedForward = new ProbeMotion();
        for (int i = 0; i < 150; i++)
        {
            double now = i * 0.01;
            saturatedForward.Command(4.4, -1, now, now, now); saturatedForward.Step(0.01, now, true);
        }
        Check(Math.Abs(saturatedForward.Linear - 2.2) < 1e-10 && Math.Abs(saturatedForward.Angular + 0.5) < 1e-10,
            "forward saturation proportionally reduces angular speed");
        var saturatedPivot = new ProbeMotion();
        for (int i = 0; i < 50; i++)
        {
            double now = i * 0.01;
            saturatedPivot.Command(0, -100, now, now, now); saturatedPivot.Step(0.01, now, true);
        }
        Check(saturatedPivot.Linear == 0 && Math.Abs(saturatedPivot.Angular + 1) < 1e-10,
            "zero-linear saturation retains bounded in-place rotation");
        string path = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/checks/unity-checks.json"));
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        File.WriteAllText(path, "{\"passed\":" + count + ",\"failed\":0}");
    }
}
