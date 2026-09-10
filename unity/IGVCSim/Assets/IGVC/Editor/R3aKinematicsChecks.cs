using System;
using System.IO;
using IGVC;
using UnityEngine;

public static class R3aKinematicsChecks
{
    public static void Run()
    {
        int count = 0;
        bool Near(double a, double b) => Math.Abs(a - b) < 1e-10;
        void Check(bool value, string name)
        {
            if (!value) throw new Exception("FAIL " + name);
            count++;
            Debug.Log("PASS " + name);
        }

        var m = new R3aKinematics();
        m.Step(0.5, 0, 2);
        Check(Near(m.AxleX, 1) && Near(m.AxleY, 0) && Near(m.BaseX, 0.74409), "R3a straight distance and base behind driven axle");
        Check(m.LeftWheelPosition > 0 && m.RightWheelPosition < 0
            && Near(m.LeftWheelPosition, -m.RightWheelPosition)
            && Near(m.LeftWheelPosition * R3aKinematics.WheelRadius, 1), "R3a canonical opposing wheel axes");

        m.Reset();
        m.Step(0, 1, Math.PI / 2);
        Check(Near(m.AxleX, 0) && Near(m.AxleY, 0) && Near(m.BaseX, 0) && Near(m.BaseY, -0.25591), "R3a pure yaw fixes axle and moves base behind heading");
        Check(Near(m.BaseLinearX, 0) && Near(m.BaseLinearY, -0.25591)
            && m.LeftWheelPosition < 0 && m.RightWheelPosition < 0, "R3a offset twist and turn wheel signs");

        m.Reset();
        m.Step(0.8, 0.4, Math.PI / 0.8);
        Check(Near(m.AxleX, 2) && Near(m.AxleY, 2) && Near(m.Yaw, Math.PI / 2), "R3a quarter circle closed form");
        m.Reset();
        m.Step(0.8, -0.4, Math.PI / 0.8);
        Check(Near(m.AxleX, 2) && Near(m.AxleY, -2) && Near(m.Yaw, -Math.PI / 2), "R3a clockwise arc");

        var whole = new R3aKinematics();
        var split = new R3aKinematics();
        whole.Step(-0.7, 0.9, 9);
        for (int i = 0; i < 900; i++) split.Step(-0.7, 0.9, 0.01);
        Check(Near(whole.AxleX, split.AxleX) && Near(whole.AxleY, split.AxleY)
            && Near(whole.Yaw, split.Yaw) && Near(whole.LeftWheelPosition, split.LeftWheelPosition)
            && Near(whole.RightWheelPosition, split.RightWheelPosition), "R3a subdivision consistency across yaw wrap");
        m.Reset();
        m.Step(1, 1e-12, 1);
        Check(Near(m.AxleX, 1) && Math.Abs(m.AxleY - 5e-13) < 1e-20, "R3a near zero yaw arc stability");

        double x = m.AxleX, y = m.AxleY, yaw = m.Yaw, left = m.LeftWheelPosition, right = m.RightWheelPosition;
        double[][] invalid = {
            new[] { double.NaN, 0.0, 1.0 }, new[] { 0.0, double.PositiveInfinity, 1.0 },
            new[] { 0.0, 0.0, double.NaN }, new[] { 0.0, 0.0, double.PositiveInfinity },
            new[] { 0.0, 0.0, 0.0 }, new[] { 0.0, 0.0, -1.0 },
            new[] { double.NegativeInfinity, 0.0, 1.0 }, new[] { 0.0, double.NaN, 1.0 },
            new[] { double.MaxValue, 0.0, 2.0 }
        };
        foreach (double[] values in invalid)
        {
            bool rejected = false;
            try { m.Step(values[0], values[1], values[2]); }
            catch (ArgumentOutOfRangeException) { rejected = true; }
            Check(rejected && m.AxleX == x && m.AxleY == y && m.Yaw == yaw
                && m.LeftWheelPosition == left && m.RightWheelPosition == right && m.Linear == 1 && m.Angular == 1e-12,
                "R3a invalid input leaves state intact " + count);
        }
        m.Reset();
        Check(m.AxleX == 0 && m.AxleY == 0 && m.Yaw == 0 && m.LeftWheelPosition == 0
            && m.RightWheelPosition == 0 && m.Linear == 0 && m.Angular == 0
            && Near(m.BaseX, -0.25591) && m.BaseY == 0, "R3a reset axle origin and wheel state");

        string path = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/checks/r3a-kinematics-checks.json"));
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        File.WriteAllText(path, "{\"passed\":" + count + ",\"failed\":0}");
    }
}
