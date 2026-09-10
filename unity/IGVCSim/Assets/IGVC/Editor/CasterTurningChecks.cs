using System;
using System.Collections.Generic;
using IGVC;
using UnityEngine;

public static class CasterTurningChecks
{
    public static void Run()
    {
        int count = 0;
        var owned = new List<GameObject>();
        void Check(bool value, string name)
        {
            if (!value) throw new Exception("Caster turning check failed: " + name);
            count++;
        }
        var settings = new CasterSettings { effective_rear_mass_kg = 30,
            spring_n_per_m_each = 12000, damper_ns_per_m_each = 700,
            vertical_travel_m = .04, joint_limit_m = .045,
            front_half_track_m = .405255f, rear_half_track_m = .24612f, rear_distance_m = .85f };
        BoxCollider Box(Vector3 position, Vector3 size, Quaternion rotation)
        {
            var go = new GameObject("Disposable caster turning fixture");
            owned.Add(go);
            go.hideFlags = HideFlags.HideAndDontSave;
            go.transform.SetPositionAndRotation(position, rotation);
            var box = go.AddComponent<BoxCollider>();
            box.size = size;
            return box;
        }
        float slope = Mathf.Tan(10 * Mathf.Deg2Rad);
        Vector3 OnPlane(Vector3 point) => new Vector3(point.x, .195f + slope * point.z, point.z);
        Vector3 FrontDirection(float yaw)
        {
            var heading = Quaternion.Euler(0, yaw, 0);
            return (OnPlane(heading * new Vector3(settings.front_half_track_m, 0, 0))
                - OnPlane(heading * new Vector3(-settings.front_half_track_m, 0, 0))).normalized;
        }
        bool Safe(CasterTerrainSupport.Candidate c)
        {
            var up = c.Rotation * Vector3.up;
            return float.IsFinite(c.Position.x) && float.IsFinite(c.Position.y) && float.IsFinite(c.Position.z)
                && float.IsFinite(up.x) && float.IsFinite(up.y) && float.IsFinite(up.z)
                && double.IsFinite(c.Height) && double.IsFinite(c.Velocity)
                && up.y >= Mathf.Cos(15 * Mathf.Deg2Rad)
                && Math.Abs(c.Left) <= .04 && Math.Abs(c.Right) <= .04
                && Math.Abs(c.LeftJoint) <= .045 && Math.Abs(c.RightJoint) <= .045;
        }
        try
        {
            var inclineRotation = Quaternion.Euler(-10, 0, 0);
            var plane = Box(new Vector3(0, .195f, 0) - inclineRotation * Vector3.up * .1f,
                new Vector3(8, .2f, 8), inclineRotation);
            Physics.SyncTransforms();
            var support = new CasterTerrainSupport(settings, new[] { plane });
            var expectedNormal = new Vector3(0, 1, -slope).normalized;
            foreach (float yaw in new[] { 0f, 45f, 90f, 135f, 180f, 225f, 270f, 315f })
            {
                Check(support.TryPreview(Vector3.zero, yaw, 0, true, out var pose), "equilibrium reset yaw=" + yaw);
                Check(Vector3.Distance(pose.Rotation * Vector3.right, FrontDirection(yaw)) < 2e-5f,
                    "rigid front axle direction yaw=" + yaw);
                Check(Vector3.Distance(pose.Rotation * Vector3.up, expectedNormal) < 2e-5f,
                    "equilibrium plane normal yaw=" + yaw);
                double expectedRear = -settings.rear_distance_m * slope * Math.Cos(yaw * Math.PI / 180);
                Check(Math.Abs(pose.Height - expectedRear) < 2e-6 && Math.Abs(pose.Left) < 2e-6
                    && Math.Abs(pose.Right) < 2e-6, "analytic rear requirement and sign yaw=" + yaw);
                Check(Safe(pose), "equilibrium travel and slope yaw=" + yaw);
                support.Commit(pose);
            }
            Check(support.TryPreview(Vector3.zero, 0, 0, true, out var initial), "turn initial reset");
            support.Commit(initial);
            bool turns = true, axles = true, projection = true, previewUnchanged = true;
            double peakCompression = 0;
            for (int degree = 1; degree <= 360; degree++)
            {
                var previous = support.Current;
                if (!support.TryPreview(Vector3.zero, degree, .01, false, out var next)) { turns = false; break; }
                previewUnchanged &= ReferenceEquals(previous, support.Current);
                turns &= Safe(next);
                axles &= Vector3.Distance(next.Rotation * Vector3.right, FrontDirection(degree)) < 2e-5f;
                double vertical = (next.Rotation * Vector3.up).y;
                projection &= Math.Abs(next.LeftJoint * vertical - next.Left) < 1e-10
                    && Math.Abs(next.RightJoint * vertical - next.Right) < 1e-10;
                peakCompression = Math.Max(peakCompression, Math.Max(Math.Abs(next.Left), Math.Abs(next.Right)));
                support.Commit(next);
            }
            Check(turns, "full committed turn remains finite within slope and travel limits");
            Check(axles, "rigid front axle throughout transient turning");
            Check(projection && peakCompression > 1e-4, "nonzero transient slider vertical projection");
            Check(previewUnchanged, "preview never replaces committed state");

            // A small raised patch affects only the left rear sample at yaw zero.
            var patch = Box(new Vector3(-settings.rear_half_track_m,
                OnPlane(new Vector3(0, 0, -settings.rear_distance_m)).y + .025f - .01f,
                -settings.rear_distance_m), new Vector3(.12f, .02f, .12f), Quaternion.identity);
            var mixed = new CasterTerrainSupport(settings, new Collider[] { plane, patch });
            Physics.SyncTransforms();
            Check(mixed.TryPreview(Vector3.zero, 0, 0, true, out var unequal)
                && Math.Abs(unequal.Left - .0125) < 2e-6 && Math.Abs(unequal.Right + .0125) < 2e-6,
                "left rear bump has positive left and negative right compression");
            mixed.Commit(unequal);
            var saved = mixed.Current;
            patch.transform.position += Vector3.up * .075f;
            Physics.SyncTransforms();
            Check(!mixed.TryPreview(Vector3.zero, 0, .01, false, out _)
                && ReferenceEquals(saved, mixed.Current) && saved.Left == unequal.Left,
                "cross axle twist beyond total travel rejects transactionally");
            plane.enabled = false;
            Physics.SyncTransforms();
            Check(!mixed.TryPreview(Vector3.zero, 0, .01, false, out _)
                && ReferenceEquals(saved, mixed.Current), "missing front support rejects transactionally");
            Debug.Log("IGVC_CASTER_TURNING_CHECKS_OK count=" + count);
        }
        finally
        {
            foreach (var go in owned) UnityEngine.Object.DestroyImmediate(go);
            Physics.SyncTransforms();
        }
    }
}
