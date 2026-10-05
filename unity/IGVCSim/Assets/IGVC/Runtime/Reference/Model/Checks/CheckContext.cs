using System;
using System.Collections.Generic;

namespace IGVC.Reference
{
    /// <summary>Shared check runner for Unity (Editor/ReferenceLabChecks) and tools/reference_lab (dotnet).</summary>
    public sealed class CheckContext
    {
        /// <summary>Frozen real course if available (may be null); checks must also cover synthetic cases.</summary>
        public CourseGeometry Course;
        public Action<string> Log = _ => { };
        public int Passed { get; private set; }
        public readonly List<string> Failures = new List<string>();
        public bool StopOnFailure = true;
        public void Check(bool value, string name)
        {
            if (value) { Passed++; Log("PASS " + name); return; }
            Failures.Add(name); Log("FAIL " + name);
            if (StopOnFailure) throw new Exception("FAIL " + name);
        }
        public void Note(string text) => Log("NOTE " + text);
    }

    public static class ReferenceChecks
    {
        public static void RunAll(CheckContext c)
        {
            GeometryChecks.Run(c);
#if !REFLAB_ONLY_VEHICLES
            Pathfinding.PathfindingChecks.Run(c);
#endif
#if !REFLAB_ONLY_PATHFINDING
            RacingLine.RacingLineChecks.Run(c);
            Drivers.DriversChecks.Run(c);
#endif
#if !REFLAB_ONLY_PATHFINDING && !REFLAB_ONLY_VEHICLES
            Teacher.TeacherChecks.Run(c);
#endif
        }
    }

    /// <summary>Synthetic courses with known answers, shared by every area's checks.</summary>
    public static class SyntheticCourses
    {
        /// <summary>Stadium loop: two straights joined by semicircles, counter-clockwise, start at the origin heading +x.</summary>
        public static CourseGeometry Stadium(double straight = 20, double radius = 8, double halfWidth = 3, double step = .25, params CourseObstacle[] obstacles)
        {
            var pts = new List<V2>();
            void Line(V2 a, V2 b) { int n = (int)Math.Ceiling(V2.Distance(a, b) / step); for (int i = 0; i < n; i++) pts.Add(V2.Lerp(a, b, (double)i / n)); }
            void Arc(V2 c, double from, double to) { int n = (int)Math.Ceiling(Math.Abs(to - from) * radius / step); for (int i = 0; i < n; i++) pts.Add(c + V2.FromAngle(from + (to - from) * i / n) * radius); }
            Line(new V2(0, 0), new V2(straight / 2, 0));
            Arc(new V2(straight / 2, radius), -Math.PI / 2, Math.PI / 2);
            Line(new V2(straight / 2, 2 * radius), new V2(-straight / 2, 2 * radius));
            Arc(new V2(-straight / 2, radius), Math.PI / 2, 3 * Math.PI / 2);
            Line(new V2(-straight / 2, 0), new V2(0, 0));
            var hw = new double[pts.Count]; var painted = new bool[pts.Count];
            for (int i = 0; i < pts.Count; i++) { hw[i] = halfWidth; painted[i] = true; }
            return CourseGeometry.Create(pts, hw, painted, 2 * halfWidth, obstacles, null, 1, "synthetic-stadium");
        }
        public static CourseObstacle Barrel(string id, double x, double y) => new CourseObstacle { Id = id, Kind = "barrel", X = x, Y = y, Length = .6, Width = .6 };
    }
}
