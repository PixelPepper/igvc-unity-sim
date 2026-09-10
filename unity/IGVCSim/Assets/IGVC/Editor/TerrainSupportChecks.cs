using System;
using System.Collections.Generic;
using IGVC;
using UnityEngine;

public static class TerrainSupportChecks
{
    public static void Run()
    {
        int count = 0;
        var owned = new List<GameObject>();
        void Check(bool condition, string name)
        {
            if (!condition) throw new Exception("Terrain support check failed: " + name);
            count++;
        }
        Collider Ground(float height, float slope)
        {
            var go = new GameObject("Disposable terrain support fixture");
            owned.Add(go);
            go.hideFlags = HideFlags.HideAndDontSave;
            go.transform.rotation = Quaternion.Euler(-slope, 0, 0);
            go.transform.position = new Vector3(0, height, 0) - go.transform.up * .1f;
            var collider = go.AddComponent<BoxCollider>();
            collider.size = new Vector3(6, .2f, 6);
            Physics.SyncTransforms();
            return collider;
        }
        try
        {
            var flat = Ground(0, 0);
            Check(TerrainSupport.TryPose(Vector3.zero, 0, new[] { flat }, out var p, out var q), "flat accepted");
            Check(Vector3.Distance(p, new Vector3(0, .30385548f, -.25591f)) < 1e-5f, "flat canonical body offset");
            Check(Quaternion.Angle(q, Quaternion.identity) < .001f, "flat level heading");
            var raised = Ground(.195f, 0);
            Check(TerrainSupport.TryPose(Vector3.zero, 90, new[] { flat, raised }, out p, out q), "closest supplied raised surface selected");
            Check(Vector3.Distance(p, new Vector3(-.25591f, .49885548f, 0)) < 1e-5f, "raised height and rotated rearward offset");
            Check(Vector3.Distance(q * Vector3.forward, Vector3.right) < 1e-5f, "yaw retained on flat support");
            var slope = Ground(.195f, 10);
            Check(TerrainSupport.TryPose(Vector3.zero, 0, new[] { slope }, out p, out q), "ten degree slope accepted");
            float angle = 10 * Mathf.Deg2Rad;
            var expectedUp = new Vector3(0, Mathf.Cos(angle), -Mathf.Sin(angle));
            var expectedForward = new Vector3(0, Mathf.Sin(angle), Mathf.Cos(angle));
            Check(Vector3.Distance(q * Vector3.up, expectedUp) < 1e-5f
                && Vector3.Distance(q * Vector3.forward, expectedForward) < 1e-5f, "analytical slope normal and projected heading");
            var expectedPosition = new Vector3(0,
                .195f + .30385548f * Mathf.Cos(angle) - .25591f * Mathf.Sin(angle),
                -.30385548f * Mathf.Sin(angle) - .25591f * Mathf.Cos(angle));
            Check(Vector3.Distance(p, expectedPosition) < 1e-5f, "plane interpolation at axle and inclined body offset");
            var steep = Ground(0, 20);
            Check(!TerrainSupport.TryPose(Vector3.zero, 0, new[] { steep }, out _, out _), "slope above fifteen degrees rejected");
            Check(!TerrainSupport.TryPose(Vector3.zero, 0, Array.Empty<Collider>(), out _, out _), "unsupplied scene surfaces cannot support pose");
            var shortGround = Ground(0, 0);
            ((BoxCollider)shortGround).size = new Vector3(2, .2f, .4f);
            Physics.SyncTransforms();
            Check(!TerrainSupport.TryPose(Vector3.zero, 0, new[] { shortGround }, out _, out _), "missing rear contact rejected");
            Check(!TerrainSupport.TryPose(new Vector3(float.NaN, 0, 0), 0, new[] { flat }, out _, out _)
                && !TerrainSupport.TryPose(Vector3.zero, float.PositiveInfinity, new[] { flat }, out _, out _), "nonfinite inputs rejected");
            Debug.Log("IGVC_TERRAIN_SUPPORT_CHECKS_OK count=" + count);
        }
        finally
        {
            foreach (var go in owned) UnityEngine.Object.DestroyImmediate(go);
            Physics.SyncTransforms();
        }
    }
}
