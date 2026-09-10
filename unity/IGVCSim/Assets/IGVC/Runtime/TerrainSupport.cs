using System;
using System.Collections.Generic;
using UnityEngine;

namespace IGVC
{
    // Provisional three-point kinematic support, not tire/contact physics.
    public static class TerrainSupport
    {
        public static bool TryPose(Vector3 axleGroundUnity, float unityYawDegrees,
            IReadOnlyList<Collider> surfaces, out Vector3 bodyPosition, out Quaternion bodyRotation)
        {
            bodyPosition = default;
            bodyRotation = Quaternion.identity;
            if (!Finite(axleGroundUnity) || !float.IsFinite(unityYawDegrees) || surfaces == null)
                return false;
            var heading = Quaternion.Euler(0, unityYawDegrees, 0);
            if (!Sample(axleGroundUnity + heading * new Vector3(-.35f, 0, 0), surfaces, out var left)
                || !Sample(axleGroundUnity + heading * new Vector3(.35f, 0, 0), surfaces, out var right)
                || !Sample(axleGroundUnity + heading * new Vector3(0, 0, -.85f), surfaces, out var rear))
                return false;
            var normal = Vector3.Cross(right - left, rear - left);
            if (!Finite(normal) || normal.sqrMagnitude < 1e-10f) return false;
            normal.Normalize();
            if (normal.y < 0) normal = -normal;
            if (normal.y < Mathf.Cos(15 * Mathf.Deg2Rad)) return false;
            float height = left.y - (normal.x * (axleGroundUnity.x - left.x)
                + normal.z * (axleGroundUnity.z - left.z)) / normal.y;
            var forward = Vector3.ProjectOnPlane(heading * Vector3.forward, normal);
            if (!float.IsFinite(height) || !Finite(forward) || forward.sqrMagnitude < 1e-10f) return false;
            var rotation = Quaternion.LookRotation(forward.normalized, normal);
            var position = new Vector3(axleGroundUnity.x, height, axleGroundUnity.z)
                + rotation * new Vector3(0, .30385548f, -.25591f);
            if (!Finite(position) || !float.IsFinite(rotation.x) || !float.IsFinite(rotation.y)
                || !float.IsFinite(rotation.z) || !float.IsFinite(rotation.w)) return false;
            bodyPosition = position;
            bodyRotation = rotation;
            return true;
        }

        private static bool Sample(Vector3 point, IReadOnlyList<Collider> surfaces, out Vector3 hitPoint)
        {
            hitPoint = default;
            var ray = new Ray(new Vector3(point.x, 3, point.z), Vector3.down);
            float closest = float.PositiveInfinity;
            bool found = false;
            for (int i = 0; i < surfaces.Count; i++)
            {
                var surface = surfaces[i];
                if (surface == null || !surface.enabled || !surface.gameObject.activeInHierarchy) continue;
                if (surface.Raycast(ray, out var hit, 6) && float.IsFinite(hit.distance)
                    && Finite(hit.point) && hit.distance < closest)
                {
                    closest = hit.distance;
                    hitPoint = hit.point;
                    found = true;
                }
            }
            return found;
        }

        private static bool Finite(Vector3 value) => float.IsFinite(value.x)
            && float.IsFinite(value.y) && float.IsFinite(value.z);
    }
}
