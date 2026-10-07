"""Plan from the pose the robot will hold when its plan is admitted (opt-in).

Planning takes ~0.3-0.7 s while the previous action keeps the robot moving and turning.
Controller admission then compares the ACTUAL pose with the path start (0.10 m / 0.15 rad,
unchanged), and turning in slaloms makes it reject otherwise good plans as
`start_pose_departed_checked_path` (36 times in one failed lap on 2026-10-06, including
the passage that would have avoided the trap). This predicts the admission-time pose from
odometry velocity over the measured submit-to-admission latency. Admission and every
collision check still use real observations and the real pose.

Capture provenance: predict_with_provenance() returns, with the unchanged prediction, a
detached record of that same call for the decision snapshot (metadata.latency_compensation):
whether extrapolation actually ran (``applied``), the measured and planning poses, and the
identity of this legacy estimator. It attests pose provenance only, not that the twist was
fresh or time-aligned with the pose, and it is not evidence that prediction is safe.
"""
import copy
import math

# Identity of the latency estimator below; bump the version if any rule it names changes.
LEGACY_ESTIMATOR_ID = 'wallclock_submit_admission_lower_quartile'
LEGACY_ESTIMATOR_VERSION = 1
LATENCY_WINDOW = 20
APPLIED_BRANCHES = ('extrapolated', 'extrapolated_shift_scaled')


class LatencyCompensator:
    def __init__(self, enabled=False, initial_latency_s=.3, alpha=.3, max_latency_s=1.2, max_shift_m=1.):
        self.enabled = bool(enabled)
        self.initial_latency = float(initial_latency_s)
        self.latency = float(initial_latency_s)
        self.alpha, self.max_latency, self.max_shift = float(alpha), float(max_latency_s), float(max_shift_m)
        self.samples = 0
        self.recent = []
        self.predictions = 0
        self.max_applied_shift = 0.
        self._branch = None  # outcome of the latest predict() call, consumed by predict_with_provenance

    def observe_latency(self, seconds):
        """Track measured submit-to-admission time; predict with its 25th percentile (always tracked, used when enabled).

        Biased short on purpose: a robot short of a predicted path start is rejected as cross-track error
        (along-track gap), while one past it simply projects further along the path.
        """
        if seconds is None or not math.isfinite(seconds) or seconds < 0:
            return
        self.recent = (self.recent + [min(seconds, self.max_latency)])[-LATENCY_WINDOW:]
        ordered = sorted(self.recent)
        self.latency = ordered[(len(ordered)-1)//4]
        self.samples += 1

    def predict(self, pose, twist):
        """Pose after `latency` seconds of constant (v, w) unicycle motion; the input pose when disabled or still.

        Same arithmetic, checks and order as before; it now also notes which branch returned (_branch).
        """
        x, y, yaw = pose
        if not self.enabled or twist is None:
            self._branch = 'disabled' if not self.enabled else 'no_twist'
            return pose
        v, w = twist
        if not (math.isfinite(v) and math.isfinite(w)) or (abs(v) < .02 and abs(w) < .02):
            self._branch = 'stationary' if math.isfinite(v) and math.isfinite(w) else 'nonfinite_twist'
            return pose
        t = self.latency
        if abs(w) < 1e-6:
            nx, ny, nyaw = x+v*t*math.cos(yaw), y+v*t*math.sin(yaw), yaw
        else:
            nyaw = yaw+w*t
            nx, ny = x+v/w*(math.sin(nyaw)-math.sin(yaw)), y-v/w*(math.cos(nyaw)-math.cos(yaw))
        shift = math.hypot(nx-x, ny-y)
        self._branch = 'extrapolated'
        if shift > self.max_shift:  # never extrapolate beyond a bounded distance
            scale = self.max_shift/shift
            nx, ny, nyaw = x+(nx-x)*scale, y+(ny-y)*scale, yaw+(nyaw-yaw)*scale
            shift = self.max_shift
            self._branch = 'extrapolated_shift_scaled'
        self.predictions += 1
        self.max_applied_shift = max(self.max_applied_shift, shift)
        return nx, ny, math.atan2(math.sin(nyaw), math.cos(nyaw))

    def predict_with_provenance(self, pose, twist):
        """(planning_pose, metadata) of ONE predict() call; the pose is exactly predict()'s return value.

        ``applied`` records whether extrapolation actually executed, never pose (in)equality: a
        zero-latency extrapolation that returns the input pose is still applied=True, and every early
        return (disabled, missing, non-finite or stationary twist) is applied=False. ``reason`` names
        the branch. The returned metadata is a fresh deep copy that later calls cannot change.
        """
        self._branch = None  # no outcome from an earlier call can leak into this one
        measured = [pose[0], pose[1], pose[2]]
        planning = self.predict(pose, twist)
        branch, self._branch = self._branch, None
        applied = branch in APPLIED_BRANCHES
        metadata = dict(enabled=self.enabled, applied=applied, reason=branch,
                        measured_pose=measured, planning_pose=[planning[0], planning[1], planning[2]],
                        latency_s=self.latency if applied else None,
                        estimator=self.estimator_identity())
        return planning, copy.deepcopy(metadata)

    def estimator_identity(self):
        """JSON-safe identity of this legacy estimator and its constructor settings (fresh dict per call).

        Version 1 rules: a sample is the local monotonic (wall) time from planner submit to the
        admission attempt; each finite non-negative sample is clamped to max_latency_s and kept in a
        window of the last LATENCY_WINDOW; the estimate is the lower order statistic
        sorted(window)[(n-1)//4] (about the 25th percentile), so the first sample replaces
        initial_latency_s. alpha is accepted by the constructor but unused (no averaging). Prediction
        is constant-twist unicycle motion over the estimate using the latest odometry twist (no age
        check); an end pose farther than max_shift_m is scaled toward the start (x, y and yaw
        together). A name for the algorithm, not a quality or safety claim.
        """
        return dict(id=LEGACY_ESTIMATOR_ID, version=LEGACY_ESTIMATOR_VERSION,
                    interval='planner_submit_to_admission_attempt', interval_clock='local_monotonic',
                    window=LATENCY_WINDOW, statistic='sorted_window[(n-1)//4]', above_max_latency='clamp',
                    first_sample='replaces_initial', prediction_model='constant_twist_unicycle',
                    twist_source='latest_odometry_twist_no_age_check',
                    shift_bound='end_pose_scaled_to_max_shift_m',
                    config=dict(initial_latency_s=self.initial_latency, max_latency_s=self.max_latency,
                                max_shift_m=self.max_shift, alpha=self.alpha, alpha_used=False))

    def report(self):
        return dict(enabled=self.enabled, latency_s=round(self.latency, 4), latency_samples=self.samples,
                    predictions=self.predictions, max_applied_shift_m=round(self.max_applied_shift, 3))


def capture_planning_inputs(compensator, measured_pose, twist, origin, resolution, width, height, costs,
                            destination, lane_points, heading_hint, planner_options, frozen_guidance):
    """(planning_pose, inputs, latency_metadata) of one planning request: sensor_course's capture wiring.

    One predict call yields both the planner start pose frozen into ``inputs`` and the provenance
    recorded beside it. ``inputs`` has exactly the shape sensor_course always saved and submitted.
    """
    planning_pose, latency_metadata = compensator.predict_with_provenance(measured_pose, twist)
    inputs = dict(origin=list(origin), resolution=resolution, width=width, height=height,
                  costs=list(costs), robot_xy=list(planning_pose[:2]), robot_yaw=planning_pose[2],
                  destination=list(destination), lane_points=list(lane_points),
                  heading_hint=heading_hint, planner_options=planner_options,
                  frozen_guidance=frozen_guidance)
    return planning_pose, inputs, latency_metadata
