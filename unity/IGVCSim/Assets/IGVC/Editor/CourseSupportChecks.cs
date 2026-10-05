using System;
using System.IO;
using System.Linq;
using IGVC;
using UnityEditor.SceneManagement;
using UnityEngine;

// Ground support is private simulator geometry; this check publishes no map to ROS.
public static class CourseSupportChecks
{
    private static CasterSettings Settings() => new CasterSettings {
        effective_rear_mass_kg = 30, spring_n_per_m_each = 12000, damper_ns_per_m_each = 700,
        vertical_travel_m = .04, joint_limit_m = .045, front_half_track_m = .405255f,
        rear_half_track_m = .24612f, rear_distance_m = .85f };

    public static void Run()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        new GameObject("Course frame (source spawn to odom origin)");
        var guard = new GameObject("Support check guard").AddComponent<LaneBoundaryGuard>();
        // A small portable fixture: paint is far from the motion samples; no ramp
        // is needed to enable flat-ground and pothole-rim support.
        var points = Enumerable.Range(0, 25).Select(i => new CourseVariant.Point {
            x = 20 * Math.Cos(i * Math.PI / 12), y = 20 * Math.Sin(i * Math.PI / 12),
            half_width = 3, painted = true }).ToArray();
        var hole = new CourseVariant.Obstacle { id = "recorded-pothole", kind = "pothole",
            x = -2.28313195363848, y = 42.3049323884978,
            width = .895829300235607, length = .895829300235607, depth = .133584008116146 };
        // Include the recorded coordinates within the generated ground's bounds.
        foreach (var p in points) p.y += 20;
        var manifest = new CourseVariant.Manifest { schema_version = 1, seed = 0,
            frame = "odom", units = "m", lane_width_m = 6, camera_pitch_rad = .174532925,
            centerline = points, obstacles = new[] { hole }, ramps = Array.Empty<CourseRamp.Definition>() };
        string temporary = Path.GetTempFileName();
        int count = 0;
        void Check(bool value, string label)
        { if (!value) throw new Exception("Course support check failed: " + label); count++; }
        try
        {
            var neighbor = new CourseVariant.Obstacle { id = "overlapping-rim", kind = "pothole",
                x = hole.x + 1.2, y = hole.y, width = .9, length = .9, depth = .15 };
            manifest.obstacles = new[] { hole, neighbor };
            File.WriteAllText(temporary, JsonUtility.ToJson(manifest));
            bool overlapRejected = false;
            try { CourseVariant.Load(temporary, guard); }
            catch (InvalidDataException error) { overlapRejected = error.Message.Contains("rim overlaps"); }
            Check(overlapRejected, "a neighboring flat rim cannot bridge an actual depression");
            manifest.obstacles = new[] { hole };
            File.WriteAllText(temporary, JsonUtility.ToJson(manifest));
            var course = CourseVariant.Load(temporary, guard);
            Check(course.support_surfaces != null && course.support_surfaces.Length > 0,
                "terrain support exists without a ramp");
            bool Hit(float rosX, float rosY, out float height)
            {
                height = float.NegativeInfinity;
                var ray = new Ray(new Vector3(-rosY, 3, rosX), Vector3.down);
                foreach (var collider in course.support_surfaces)
                    if (collider.Raycast(ray, out var hit, 6)) height = Math.Max(height, hit.point.y);
                return float.IsFinite(height);
            }
            // All visible annular ground remains drivable across coarse-cell seams.
            bool ring = true;
            for (int degree = 0; degree < 360; degree += 5)
                foreach (double radius in new[] { .48, .6, .8, 1.0, 1.2 })
                    ring &= Hit((float)(hole.x + radius * Math.Cos(degree * Math.PI / 180)),
                        (float)(hole.y + radius * Math.Sin(degree * Math.PI / 180)), out float h)
                        && Math.Abs(h) < 1e-5;
            Check(ring, "continuous flat rim around the actual hole");
            Check(!Hit((float)hole.x, (float)hole.y, out _), "actual hole remains unsupported");
            var support = new CasterTerrainSupport(Settings(), course.support_surfaces);
            double x = -1.278669002056347, y = 41.64475523333686, yaw = -2.563953;
            float heading = (float)(-yaw * Mathf.Rad2Deg);
            Check(support.TryPreview(new Vector3((float)-y, 0, (float)x), heading, 0, true, out var initial),
                "recorded stop pose has support");
            support.Commit(initial);
            // Exercise slow forward travel, not just a ray hit or object-name check.
            bool moves = true;
            for (int tick = 1; tick <= 200; tick++)
            {
                double travel = tick * .05 * .01;
                var next = new Vector3((float)-(y + travel * Math.Sin(yaw)), 0,
                    (float)(x + travel * Math.Cos(yaw)));
                if (!support.TryPreview(next, heading, .01, false, out var candidate)) { moves = false; break; }
                moves &= Math.Abs(candidate.AxleHeight) < 1e-5;
                support.Commit(candidate);
            }
            Check(moves, "low-speed forward motion clears the former invisible support gap");
            Debug.Log("IGVC_COURSE_SUPPORT_CHECKS_OK count=" + count);
        }
        finally { File.Delete(temporary); }
    }

    public static void Reproduce()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        new GameObject("Course frame (source spawn to odom origin)");
        var guard = new GameObject("Support check guard").AddComponent<LaneBoundaryGuard>();
        string path = Path.GetFullPath(Path.Combine(Application.dataPath,
            "../../../artifacts/courses/seed-2027/course.json"));
        var course = CourseVariant.Load(path, guard);
        var support = new CasterTerrainSupport(Settings(), course.support_surfaces);
        // Frozen end pose from entrance-verified-run, not a runtime navigation hint.
        double x = -1.278669002056347, y = 41.64475523333686, yaw = -2.563953;
        var at = new Vector3((float)-y, 0, (float)x);
        float heading = (float)(-yaw * Mathf.Rad2Deg);
        bool initial = support.TryPreview(at, heading, 0, true, out var first);
        if (initial) support.Commit(first);
        foreach (double speed in new[] { .02, .05, .1, .5 })
        {
            var next = new Vector3((float)-(y + speed * .01 * Math.Sin(yaw)), 0,
                (float)(x + speed * .01 * Math.Cos(yaw)));
            bool accepted = support.TryPreview(next, heading, .01, false, out _);
            // Compare the same support model against the rendered rim, without altering the course.
            var visible = new CasterTerrainSupport(Settings(), course.support_surfaces.Concat(
                UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsSortMode.None)
                    .Where(c => c.name == "Pothole rim")).ToArray());
            bool withRim = visible.TryPreview(at, heading, 0, true, out var start);
            if (withRim) visible.Commit(start);
            withRim &= visible.TryPreview(next, heading, .01, false, out _);
            Debug.Log($"IGVC_SUPPORT_REPRO speed={speed:R} initial={initial} accepted={accepted} with_rim={withRim}");
        }
    }
}
