using System;

namespace IGVC
{
    // Experimental rear pitch support, not rigidbody/contact/traction physics.
    // Two provisional parallel springs; gravity/static sag is compensated about CAD rest.
    public sealed class CasterSuspension
    {
        public const double MaximumTimeStep = 0.1;
        const double IntegrationStep = 0.001;
        readonly double mass, springStiffness, damping, travel;
        public double Height { get; private set; }
        public double Velocity { get; private set; }
        public double LeftCompression { get; private set; }
        public double RightCompression { get; private set; }

        public CasterSuspension(double mass = 30, double springStiffness = 12000,
            double damping = 700, double travel = 0.04)
        {
            if (!Finite(mass) || mass <= 0) throw new ArgumentOutOfRangeException(nameof(mass));
            if (!Finite(springStiffness) || springStiffness <= 0) throw new ArgumentOutOfRangeException(nameof(springStiffness));
            if (!Finite(damping) || damping < 0) throw new ArgumentOutOfRangeException(nameof(damping));
            if (!Finite(travel) || travel <= 0) throw new ArgumentOutOfRangeException(nameof(travel));
            this.mass = mass;
            this.springStiffness = springStiffness;
            this.damping = damping;
            this.travel = travel;
        }

        public CasterSuspension Copy() => (CasterSuspension)MemberwiseClone();

        public bool Reset(double left, double right)
        {
            if (!Bounds(left, right, out _, out _)) return false;
            double height = left * 0.5 + right * 0.5;
            return Commit(left, right, height, 0);
        }

        // Heights are relative to the rigid front axle roll plane, in metres.
        // Positive compression means terrain support is above the rear body support.
        public bool Step(double left, double right, double dt)
        {
            if (!Finite(dt) || dt < 0 || dt > MaximumTimeStep
                || !Bounds(left, right, out double low, out double high)) return false;
            if (dt == 0) return true; // Pause preserves even the previous compression observations.
            double height = Height, velocity = Velocity;
            Stop(ref height, ref velocity, low, high);
            int steps = (int)Math.Ceiling(dt / IntegrationStep);
            double h = dt / steps;
            for (int i = 0; i < steps; i++)
            {
                double acceleration = (springStiffness * ((left - height) + (right - height))
                    - 2 * damping * velocity) / mass;
                velocity += acceleration * h;
                height += velocity * h;
                if (!Finite(height) || !Finite(velocity)) return false;
                Stop(ref height, ref velocity, low, high);
            }
            return Commit(left, right, height, velocity);
        }

        bool Bounds(double left, double right, out double low, out double high)
        {
            low = Math.Max(left, right) - travel;
            high = Math.Min(left, right) + travel;
            return Finite(left) && Finite(right) && Finite(low) && Finite(high) && low <= high;
        }

        static void Stop(ref double height, ref double velocity, double low, double high)
        {
            height = Math.Max(low, Math.Min(high, height));
            if ((height <= low && velocity < 0) || (height >= high && velocity > 0)) velocity = 0;
        }

        bool Commit(double left, double right, double height, double velocity)
        {
            double lc = left - height, rc = right - height;
            if (!Finite(height) || !Finite(velocity) || !Finite(lc) || !Finite(rc)
                || Math.Abs(lc) > travel + 1e-12 || Math.Abs(rc) > travel + 1e-12) return false;
            Height = height;
            Velocity = velocity;
            // Remove only roundoff at a hard stop.
            LeftCompression = Math.Max(-travel, Math.Min(travel, lc));
            RightCompression = Math.Max(-travel, Math.Min(travel, rc));
            return true;
        }

        static bool Finite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
    }
}
