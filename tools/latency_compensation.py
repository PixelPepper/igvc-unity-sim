"""Plan from the pose the robot will hold when its plan is admitted (opt-in).

Planning takes ~0.3-0.7 s while the previous action keeps the robot moving and turning.
Controller admission then compares the ACTUAL pose with the path start (0.10 m / 0.15 rad,
unchanged), and turning in slaloms makes it reject otherwise good plans as
`start_pose_departed_checked_path` (36 times in one failed lap on 2026-10-06, including
the passage that would have avoided the trap). This predicts the admission-time pose from
odometry velocity over the measured submit-to-admission latency. Admission and every
collision check still use real observations and the real pose.
"""
import math


class LatencyCompensator:
    def __init__(self, enabled=False, initial_latency_s=.3, alpha=.3, max_latency_s=1.2, max_shift_m=1.):
        self.enabled = bool(enabled)
        self.latency = float(initial_latency_s)
        self.alpha, self.max_latency, self.max_shift = float(alpha), float(max_latency_s), float(max_shift_m)
        self.samples = 0
        self.recent = []
        self.predictions = 0
        self.max_applied_shift = 0.

    def observe_latency(self, seconds):
        """Track measured submit-to-admission time; predict with its 25th percentile (always tracked, used when enabled).

        Biased short on purpose: a robot short of a predicted path start is rejected as cross-track error
        (along-track gap), while one past it simply projects further along the path.
        """
        if seconds is None or not math.isfinite(seconds) or seconds < 0:
            return
        self.recent = (self.recent + [min(seconds, self.max_latency)])[-20:]
        ordered = sorted(self.recent)
        self.latency = ordered[(len(ordered)-1)//4]
        self.samples += 1

    def predict(self, pose, twist):
        """Pose after `latency` seconds of constant (v, w) unicycle motion; the input pose when disabled or still."""
        x, y, yaw = pose
        if not self.enabled or twist is None:
            return pose
        v, w = twist
        if not (math.isfinite(v) and math.isfinite(w)) or (abs(v) < .02 and abs(w) < .02):
            return pose
        t = self.latency
        if abs(w) < 1e-6:
            nx, ny, nyaw = x+v*t*math.cos(yaw), y+v*t*math.sin(yaw), yaw
        else:
            nyaw = yaw+w*t
            nx, ny = x+v/w*(math.sin(nyaw)-math.sin(yaw)), y-v/w*(math.cos(nyaw)-math.cos(yaw))
        shift = math.hypot(nx-x, ny-y)
        if shift > self.max_shift:  # never extrapolate beyond a bounded distance
            scale = self.max_shift/shift
            nx, ny, nyaw = x+(nx-x)*scale, y+(ny-y)*scale, yaw+(nyaw-yaw)*scale
            shift = self.max_shift
        self.predictions += 1
        self.max_applied_shift = max(self.max_applied_shift, shift)
        return nx, ny, math.atan2(math.sin(nyaw), math.cos(nyaw))

    def report(self):
        return dict(enabled=self.enabled, latency_s=round(self.latency, 4), latency_samples=self.samples,
                    predictions=self.predictions, max_applied_shift_m=round(self.max_applied_shift, 3))
