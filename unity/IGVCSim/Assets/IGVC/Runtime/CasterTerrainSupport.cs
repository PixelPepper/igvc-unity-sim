using System;
using System.Collections.Generic;
using UnityEngine;

namespace IGVC
{
    [Serializable]
    public sealed class CasterSettings
    {
        public double effective_rear_mass_kg, spring_n_per_m_each, damper_ns_per_m_each;
        public double vertical_travel_m, joint_limit_m;
        public float front_half_track_m, rear_half_track_m, rear_distance_m;

        public void Validate()
        {
            if (!float.IsFinite(front_half_track_m) || front_half_track_m <= 0 || front_half_track_m > 1
                || !float.IsFinite(rear_half_track_m) || rear_half_track_m <= 0 || rear_half_track_m > front_half_track_m
                || !float.IsFinite(rear_distance_m) || rear_distance_m <= .1 || rear_distance_m > 2
                || !double.IsFinite(joint_limit_m) || joint_limit_m > .1
                || joint_limit_m < vertical_travel_m / Math.Cos(15 * Math.PI / 180))
                throw new ArgumentException("Invalid caster support dimensions or slider limits");
            CreateSpring(); // Validate the spring/damper configuration at the boundary.
        }

        public CasterSuspension CreateSpring() => new CasterSuspension(effective_rear_mass_kg,
            spring_n_per_m_each, damper_ns_per_m_each, vertical_travel_m);
    }

    // Rigid front axle plus one sprung rear pitch degree of freedom. Ground samples use
    // a yaw-only support footprint; caster sliders compensate vertical displacement.
    // This small-angle model deliberately does not solve full wheel/contact dynamics.
    public sealed class CasterTerrainSupport
    {
        public sealed class Candidate
        {
            internal CasterSuspension spring;
            public Vector3 Position;
            public Quaternion Rotation;
            public float AxleHeight;
            public double LeftRate, RightRate;
            public double Height => spring.Height;
            public double Velocity => spring.Velocity;
            public double Left => spring.LeftCompression;
            public double Right => spring.RightCompression;
            public double LeftJoint => Left / (Rotation * Vector3.up).y;
            public double RightJoint => Right / (Rotation * Vector3.up).y;
        }

        private readonly CasterSettings settings;
        private readonly IReadOnlyList<Collider> surfaces;
        public Candidate Current { get; private set; }
        private static readonly Vector3 BodyOffset = new Vector3(0, .30385548f, -.25591f);

        public CasterTerrainSupport(CasterSettings configuration, IReadOnlyList<Collider> ground)
        { configuration.Validate(); settings = configuration; surfaces = ground; }

        public bool TryPreview(Vector3 axle, float yaw, double dt, bool reset, out Candidate candidate)
        {
            candidate = null;
            if (!Finite(axle) || !float.IsFinite(yaw) || !double.IsFinite(dt) || dt < 0 || dt > .1) return false;
            Quaternion heading = Quaternion.Euler(0, yaw, 0);
            if (!Sample(axle + heading * new Vector3(-settings.front_half_track_m, 0, 0), out var frontLeft)
                || !Sample(axle + heading * new Vector3(settings.front_half_track_m, 0, 0), out var frontRight)
                || !Sample(axle + heading * new Vector3(-settings.rear_half_track_m, 0, -settings.rear_distance_m), out var rearLeft)
                || !Sample(axle + heading * new Vector3(settings.rear_half_track_m, 0, -settings.rear_distance_m), out var rearRight)) return false;
            float height = (frontLeft.y + frontRight.y) * .5f;
            float crossSlope = (frontRight.y - frontLeft.y) / (2 * settings.front_half_track_m);
            double requiredLeft = rearLeft.y - height + crossSlope * settings.rear_half_track_m;
            double requiredRight = rearRight.y - height - crossSlope * settings.rear_half_track_m;
            var spring = reset || Current == null ? settings.CreateSpring() : Current.spring.Copy();
            if (!(reset || Current == null ? spring.Reset(requiredLeft, requiredRight) : spring.Step(requiredLeft, requiredRight, dt))) return false;
            var rear = axle + heading * new Vector3(0, 0, -settings.rear_distance_m);
            rear.y = height + (float)spring.Height;
            var normal = Vector3.Cross(frontRight - frontLeft, rear - frontLeft).normalized;
            if (normal.y < 0) normal = -normal;
            if (!Finite(normal) || normal.y < Mathf.Cos(15 * Mathf.Deg2Rad)) return false;
            var forward = Vector3.ProjectOnPlane(heading * Vector3.forward, normal);
            if (forward.sqrMagnitude < 1e-10f) return false;
            var rotation = Quaternion.LookRotation(forward.normalized, normal);
            if (Math.Abs(spring.LeftCompression / normal.y) > settings.joint_limit_m
                || Math.Abs(spring.RightCompression / normal.y) > settings.joint_limit_m) return false;
            candidate = new Candidate { spring = spring, Rotation = rotation, AxleHeight = height,
                Position = new Vector3(axle.x, height, axle.z) + rotation * BodyOffset,
                LeftRate = !reset && Current != null && dt > 0 ? (spring.LeftCompression - Current.Left) / dt : 0,
                RightRate = !reset && Current != null && dt > 0 ? (spring.RightCompression - Current.Right) / dt : 0 };
            return true;
        }

        public void Commit(Candidate candidate) => Current = candidate ?? throw new ArgumentNullException(nameof(candidate));

        private bool Sample(Vector3 at, out Vector3 point)
        {
            point = default; float closest = float.PositiveInfinity;
            var ray = new Ray(new Vector3(at.x, 3, at.z), Vector3.down);
            foreach (var surface in surfaces)
                if (surface != null && surface.enabled && surface.gameObject.activeInHierarchy
                    && surface.Raycast(ray, out var hit, 6) && Finite(hit.point) && hit.distance < closest)
                { closest = hit.distance; point = hit.point; }
            return float.IsFinite(closest);
        }

        private static bool Finite(Vector3 value) => float.IsFinite(value.x) && float.IsFinite(value.y) && float.IsFinite(value.z);
    }
}
