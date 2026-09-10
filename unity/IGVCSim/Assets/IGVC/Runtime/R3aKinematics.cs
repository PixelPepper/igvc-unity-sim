using System;

namespace IGVC
{
    // Ideal axle kinematics using uncalibrated CAD dimensions, not wheel/contact physics.
    public sealed class R3aKinematics
    {
        public const double WheelRadius = 0.229569608;
        public const double TrackWidth = 0.81051;
        // Canonical physical forward: driven wheels ahead, casters behind the base origin.
        public const double AxleOffsetX = 0.25591;
        public const double BaseOffsetX = -AxleOffsetX;

        public double AxleX { get; private set; }
        public double AxleY { get; private set; }
        public double Yaw { get; private set; }
        public double BaseX => AxleX + BaseOffsetX * Math.Cos(Yaw);
        public double BaseY => AxleY + BaseOffsetX * Math.Sin(Yaw);
        public double Linear { get; private set; }
        public double Angular { get; private set; }
        public double BaseLinearX => Linear;
        public double BaseLinearY => BaseOffsetX * Angular;
        public double LeftWheelPosition { get; private set; }
        public double RightWheelPosition { get; private set; }

        // v is forward speed at the axle; w is ROS positive-Z yaw rate.
        // Exceptions leave the previous state intact.
        public void Step(double v, double w, double dt)
        {
            RequireFinite(v, nameof(v));
            RequireFinite(w, nameof(w));
            RequireFinite(dt, nameof(dt));
            if (dt <= 0) throw new ArgumentOutOfRangeException(nameof(dt), "Time step must be positive.");

            double angle = w * dt;
            double distance = v * dt;
            RequireFinite(angle, nameof(w));
            RequireFinite(distance, nameof(v));
            double half = angle * 0.5;
            // Stable exact constant-twist arc, including the straight-line limit.
            double sinc = Math.Abs(half) < 1e-4
                ? 1 - half * half / 6 + half * half * half * half / 120
                : Math.Sin(half) / half;
            double heading = Yaw + half;
            double nextX = AxleX + distance * sinc * Math.Cos(heading);
            double nextY = AxleY + distance * sinc * Math.Sin(heading);
            double nextYaw = Math.Atan2(Math.Sin(Yaw + angle), Math.Cos(Yaw + angle));
            double nextLeft = LeftWheelPosition + (v - w * TrackWidth * 0.5) / WheelRadius * dt;
            double nextRight = RightWheelPosition - (v + w * TrackWidth * 0.5) / WheelRadius * dt;
            RequireFinite(nextX, nameof(v));
            RequireFinite(nextY, nameof(v));
            RequireFinite(nextYaw, nameof(w));
            RequireFinite(nextLeft, nameof(v));
            RequireFinite(nextRight, nameof(v));

            AxleX = nextX;
            AxleY = nextY;
            Yaw = nextYaw;
            LeftWheelPosition = nextLeft;
            RightWheelPosition = nextRight;
            Linear = v;
            Angular = w;
        }

        public void Reset()
        {
            AxleX = AxleY = Yaw = Linear = Angular = LeftWheelPosition = RightWheelPosition = 0;
        }

        public void RestoreStoppedPose(double x, double y, double yaw)
        {
            RequireFinite(x, nameof(x)); RequireFinite(y, nameof(y)); RequireFinite(yaw, nameof(yaw));
            Reset(); AxleX = x; AxleY = y; Yaw = yaw;
        }

        private static void RequireFinite(double value, string name)
        {
            if (!double.IsFinite(value))
                throw new ArgumentOutOfRangeException(name, "Inputs and resulting state must be finite.");
        }
    }
}
