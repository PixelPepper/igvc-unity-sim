using System;

namespace IGVC
{
    // Ideal planar integration for the transport probe, not a tire/contact model.
    public sealed class ProbeMotion
    {
        // Margin below the 5 mph (2.2352 m/s) competition maximum.
        public const double MaximumForwardSpeed = 2.2;
        // The ROS command boundary owns authorization for manual reverse recovery.
        public const double MaximumReverseSpeed = 0.3;
        public double X { get; private set; }
        public double Y { get; private set; }
        public double Yaw { get; private set; }
        public double Linear { get; private set; }
        public double Angular { get; private set; }
        public bool Paused { get; private set; }
        public bool Stopped { get; private set; }
        private double lastReceived = double.NegativeInfinity;
        private double minimumStamp;
        private double targetLinear;
        private double targetAngular;

        public void Command(double linear, double angular, double stamp, double simulationTime, double monotonic)
        {
            if (Paused || Stopped || !double.IsFinite(linear) || !double.IsFinite(angular)
                || !double.IsFinite(stamp) || stamp < minimumStamp || simulationTime - stamp > 0.5 || stamp - simulationTime > 0.1)
                return;
            double linearLimit = linear >= 0 ? MaximumForwardSpeed : MaximumReverseSpeed;
            double scale = 1.0;
            if (Math.Abs(linear) > linearLimit) scale = linearLimit / Math.Abs(linear);
            if (Math.Abs(angular) > 1.0) scale = Math.Min(scale, 1.0 / Math.Abs(angular));
            targetLinear = linear * scale;
            targetAngular = angular * scale;
            lastReceived = monotonic;
        }

        public void Step(double dt, double monotonic, bool connected)
        {
            if (Paused || Stopped || !connected || monotonic - lastReceived > 0.5)
            {
                Linear = Angular = 0;
                targetLinear = targetAngular = 0;
                return;
            }
            Linear = Approach(Linear, targetLinear, dt * 2);
            // Couple launch ramps so a low initial speed does not tighten the commanded turn.
            // Zero-linear commands still permit in-place rotation and ordinary stopping.
            double angularScale = Math.Abs(targetLinear) > 1e-9
                ? Math.Min(1.0, Math.Abs(Linear / targetLinear)) : 1.0;
            Angular = Approach(Angular, targetAngular * angularScale, dt * 3);
            double midYaw = Yaw + Angular * dt * 0.5;
            X += Linear * Math.Cos(midYaw) * dt;
            Y += Linear * Math.Sin(midYaw) * dt;
            Yaw = Math.Atan2(Math.Sin(Yaw + Angular * dt), Math.Cos(Yaw + Angular * dt));
        }

        public void SetPaused(bool value, double simulationTime) { Paused = value; Invalidate(simulationTime); }
        public void SetStopped(bool value, double simulationTime) { Stopped = value; Invalidate(simulationTime); }
        public void Reset(double simulationTime) { X = Y = Yaw = 0; Invalidate(simulationTime); }
        public void RejectMotion(double simulationTime) { Invalidate(simulationTime); }
        private void Invalidate(double simulationTime)
        {
            minimumStamp = simulationTime + 0.000001;
            lastReceived = double.NegativeInfinity;
            Linear = Angular = targetLinear = targetAngular = 0;
        }
        private static double Approach(double value, double target, double step) =>
            value + Math.Clamp(target - value, -step, step);
    }
}
