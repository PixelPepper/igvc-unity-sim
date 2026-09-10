using System;

namespace IGVC
{
    // Provisional motion-aligned yaw response, not a no-slip/contact or caster trail model.
    public sealed class CasterSwivel
    {
        public const double MaximumTimeStep = .1;
        readonly double alignmentDistance, maxRate, stationarySpeed;
        public double Angle { get; private set; }
        public double Velocity { get; private set; }

        public CasterSwivel(double alignmentDistance = .12, double maxRate = 4,
            double stationarySpeed = .005)
        {
            if (!Finite(alignmentDistance) || alignmentDistance <= 0)
                throw new ArgumentOutOfRangeException(nameof(alignmentDistance));
            if (!Finite(maxRate) || maxRate <= 0) throw new ArgumentOutOfRangeException(nameof(maxRate));
            if (!Finite(stationarySpeed) || stationarySpeed < 0)
                throw new ArgumentOutOfRangeException(nameof(stationarySpeed));
            this.alignmentDistance = alignmentDistance;
            this.maxRate = maxRate;
            this.stationarySpeed = stationarySpeed;
        }

        public bool Step(double vForward, double vLeft, double dt)
        {
            if (!Finite(vForward) || !Finite(vLeft) || !Finite(dt) || dt < 0 || dt > MaximumTimeStep)
                return false;
            if (dt == 0) return true;
            double scale = Math.Max(Math.Abs(vForward), Math.Abs(vLeft));
            double speed = scale == 0 ? 0 : scale * Math.Sqrt(
                (vForward / scale) * (vForward / scale) + (vLeft / scale) * (vLeft / scale));
            if (!Finite(speed)) return false;
            if (speed <= stationarySpeed) { Velocity = 0; return true; }
            double target = Math.Atan2(vLeft, vForward);
            // Remainder avoids subtracting a potentially large number of full turns.
            double error = (target - Angle % (2 * Math.PI)) % (2 * Math.PI);
            if (error <= -Math.PI) error += 2 * Math.PI; // Exact antipodal tie always turns positive.
            if (error > Math.PI) error -= 2 * Math.PI;
            double increment = error * (1 - Math.Exp(-speed / alignmentDistance * dt));
            double limit = maxRate * dt;
            increment = Math.Max(-limit, Math.Min(limit, increment));
            double next = Angle + increment;
            double velocity = (next - Angle) / dt;
            if (!Finite(next) || !Finite(velocity)) return false;
            Angle = next;
            Velocity = velocity;
            return true;
        }

        public void Reset() { Angle = 0; Velocity = 0; }
        static bool Finite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
    }
}
