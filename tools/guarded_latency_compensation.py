"""Guarded planning-pose prediction over an explicitly selected latency estimator (pure; no runtime callers yet).

A new variant, not the legacy latency_compensation experiment and not proof of safety. The planner
start pose may be predicted from ONE whole odometry message (pose, twist, header stamp, local
receipt time) over a bounded horizon; every check that matters stays on actual observations:

  * planning_context: disabled -> the identical measured pose. Enabled -> predicts only from a
    well-formed sample whose pose is exactly the measured pose and whose local receipt age is in
    [0, max_sample_age_s]; anything else returns the measured pose with a counted no-action reason.
    Nothing is retimed. ``applied`` records that the extrapolation branch executed, never pose
    (in)equality: a zero horizon with a moving twist is applied=True with equal poses.
  * Prediction: constant (v, w) unicycle motion over min(estimate, max_shift_m/|v|,
    max_yaw_shift_rad/|w|); |v| < 0.02 and |w| < 0.02 is stationary; no end-pose scaling.
  * Latency samples go through latency_estimators (make_estimator / AdmissionSample) with BOTH
    clocks supplied by the caller; this module never converts one clock into the other and never
    substitutes a receipt time or stamp interval for the wall submit time.
  * admit_from_measured_pose runs the caller's unchanged admission exactly once on the ACTUAL entry
    pose, latest grid and footprint, returns its result untouched, then samples the latency.

Course, WORLD and grid geometry never enter prediction. Defaults (1 m, 0.6 rad, 0.25 s) are the
provisional simulation bounds of reviewed candidate f41aeeb, not measured limits.
"""
import copy
from dataclasses import dataclass
import math
from typing import Optional

from latency_estimators import AdmissionSample, make_estimator

PREDICTION_POLICY = 'guarded_constant_twist_unicycle'
PREDICTION_POLICY_VERSION = 1
STATIONARY_SPEED = .02  # m/s and rad/s: below both, the twist predicts nothing (candidate threshold)
STRAIGHT_TURN = 1e-9    # |w*t| below this uses the straight-line formula (stable small turns)
# No-action reasons of planning_context ('disabled' is reported but not counted as a skip).
SKIP_REASONS = ('no_odometry_sample', 'malformed_odometry_sample', 'pose_not_from_sample', 'invalid_now',
                'future_odometry_sample', 'stale_odometry_sample', 'stationary_twist')
# Why an admission attempt produced no estimator sample (estimator rejections are counted by the estimator).
NOT_SAMPLED_REASONS = ('missing_odometry_sample', 'malformed_odometry_sample', 'entry_pose_not_from_sample')


def _real(value):
    """A finite int or float representable as a float, never a bool; never raises OverflowError."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _pose(value, size=3):
    """The values as a tuple when ``value`` is a list/tuple of ``size`` finite reals, else None."""
    if not isinstance(value, (list, tuple)) or len(value) != size or not all(_real(v) for v in value):
        return None
    return tuple(value)


@dataclass(frozen=True)
class OdometrySample:
    """One whole odometry message. pose (x, y, yaw) m/rad, twist (v, w) m/s and rad/s, stamp_ns the header
    stamp in integer nanoseconds, received_s its local monotonic receipt time in seconds (never refreshed)."""
    pose: tuple
    twist: tuple
    stamp_ns: int
    received_s: float


def _well_formed(sample):
    return (isinstance(sample, OdometrySample) and _pose(sample.pose) is not None
            and _pose(sample.twist, 2) is not None and type(sample.stamp_ns) is int and _real(sample.received_s))


@dataclass(frozen=True)
class GuardedConfig:
    """Prediction bounds, frozen for the compensator's lifetime."""
    enabled: bool
    estimator_kind: str
    max_shift_m: float
    max_yaw_shift_rad: float
    max_sample_age_s: float


def execution_mode_error(enabled, path_execution):
    """Startup check: compensation is gated by checked-path admission and learns only there.

    nav2-goal sends the destination without path_entry admission, so a predicted start would run
    ungated and the latency would never be sampled. Returns an error message, or None when allowed.
    """
    if enabled and path_execution != 'checked-path':
        return '--latency-compensation requires --path-execution checked-path (admission-gated)'
    return None


class GuardedLatencyCompensator:
    def __init__(self, estimator_kind, *, enabled, max_shift_m=1., max_yaw_shift_rad=.6, max_sample_age_s=.25,
                 estimator_config=None):
        """``estimator_kind`` and ``enabled`` are required (no default, no fallback). ``estimator_config`` holds
        the estimator's own settings (its per-kind defaults otherwise); the receipt-age bound is shared and
        set only here, so prediction and estimator freshness can never diverge."""
        if type(enabled) is not bool:
            raise ValueError(f'enabled must be a bool, got {enabled!r}')
        for name, value, upper in (('max_shift_m', max_shift_m, 2.), ('max_yaw_shift_rad', max_yaw_shift_rad, math.pi/2),
                                   ('max_sample_age_s', max_sample_age_s, 1.)):
            if not _real(value) or not 0 < value <= upper:
                raise ValueError(f'{name} must be a number in (0, {upper:g}] (not bool), got {value!r}')
        config = dict(estimator_config or {})
        if 'max_sample_age_s' in config:
            raise ValueError('max_sample_age_s is shared with prediction; set it on the compensator only')
        self._estimator = make_estimator(estimator_kind, max_sample_age_s=float(max_sample_age_s), **config)
        self._config = GuardedConfig(enabled, estimator_kind, float(max_shift_m), float(max_yaw_shift_rad),
                                     float(max_sample_age_s))
        self.predictions = 0
        self.skipped = {}       # planning_context no-action reason -> count
        self.not_sampled = {}   # admission attempts without an estimator sample, by reason
        self.max_applied_shift = 0.
        self.max_applied_yaw_shift = 0.

    @property
    def config(self):
        """Frozen GuardedConfig (read-only)."""
        return self._config

    @property
    def estimator(self):
        """The latency estimator (read-only reference; its config is frozen too)."""
        return self._estimator

    @property
    def enabled(self):
        return self._config.enabled

    @property
    def latency(self):
        return self._estimator.latency

    def horizon(self, twist):
        """Prediction time: the estimate, shortened so the arc stays within both bounds."""
        v, w = twist
        t = self._estimator.latency
        if abs(v) > 0:
            t = min(t, self._config.max_shift_m/abs(v))  # arc length bounds the chord, so the shift does too
        if abs(w) > 0:
            t = min(t, self._config.max_yaw_shift_rad/abs(w))
        return t

    def _predict(self, pose, twist):
        """Constant-twist unicycle pose after horizon(twist); records shift statistics."""
        x, y, yaw = pose
        v, w = twist
        t = self.horizon(twist)
        if abs(w*t) < STRAIGHT_TURN:
            nx, ny, nyaw = x+v*t*math.cos(yaw), y+v*t*math.sin(yaw), yaw
        else:
            nyaw = yaw+w*t
            nx, ny = x+v/w*(math.sin(nyaw)-math.sin(yaw)), y-v/w*(math.cos(nyaw)-math.cos(yaw))
        self.predictions += 1
        self.max_applied_shift = max(self.max_applied_shift, math.hypot(nx-x, ny-y))
        self.max_applied_yaw_shift = max(self.max_applied_yaw_shift, abs(nyaw-yaw))
        return (nx, ny, math.atan2(math.sin(nyaw), math.cos(nyaw))), t

    def planning_context(self, sample, measured_pose, now):
        """(planning_pose, detached context) for one planning request.

        ``measured_pose`` must be three finite reals (ValueError otherwise; nothing is fabricated).
        ``now`` is the local monotonic time in seconds. When nothing is applied the returned pose IS
        ``measured_pose``. The context's enabled/applied/measured_pose/planning_pose fields are the
        snapshot_pose_provenance contract.
        """
        if _pose(measured_pose) is None:
            raise ValueError(f'measured_pose must be three finite numbers, got {measured_pose!r}')
        context = dict(enabled=self.enabled, applied=False, reason=None,
                       measured_pose=list(measured_pose), planning_pose=list(measured_pose),
                       latency_s=self.latency, horizon_s=0., odom_stamp_ns=None, odom_receipt_age_s=None,
                       twist=None, identity=self.identity())
        planning_pose, reason = measured_pose, None
        if not self.enabled:
            reason = 'disabled'
        elif sample is None:
            reason = 'no_odometry_sample'
        elif not _well_formed(sample):
            reason = 'malformed_odometry_sample'
        else:
            context.update(odom_stamp_ns=sample.stamp_ns, twist=list(sample.twist))
            age = now-sample.received_s if _real(now) else None
            if not _real(age):
                reason = 'invalid_now'
            else:
                context['odom_receipt_age_s'] = age
                if tuple(sample.pose) != tuple(measured_pose):
                    reason = 'pose_not_from_sample'
                elif age < 0:
                    reason = 'future_odometry_sample'
                elif age > self._config.max_sample_age_s:
                    reason = 'stale_odometry_sample'
                elif abs(sample.twist[0]) < STATIONARY_SPEED and abs(sample.twist[1]) < STATIONARY_SPEED:
                    reason = 'stationary_twist'
                else:
                    planning_pose, horizon = self._predict(tuple(measured_pose), tuple(sample.twist))
                    context.update(applied=True, reason='predicted', planning_pose=list(planning_pose),
                                   horizon_s=horizon)
        if reason is not None:
            context['reason'] = reason
            if reason != 'disabled':
                self.skipped[reason] = self.skipped.get(reason, 0)+1
        return planning_pose, copy.deepcopy(context)

    def _not_sampled(self, reason):
        self.not_sampled[reason] = self.not_sampled.get(reason, 0)+1
        return dict(sampled=False, reason=reason, accepted=False, interval_s=None, clamped=False)

    def observe_admission(self, planning_sample, entry_sample, entry_pose, now, submitted_at):
        """Sample the estimator for one admission attempt (accepted or rejected); returns a fresh outcome.

        Clocks are forwarded as given: planning/entry header stamps, the entry receipt time, ``now``
        (admission) and ``submitted_at`` (planner submit), both local monotonic seconds. A missing
        ``submitted_at`` is passed on as None: the wall estimator rejects it, the EMA ignores it. No
        sample is taken when either odometry sample is missing or malformed, or when ``entry_pose`` is
        not exactly the entry sample's pose (its stamp would not time this admission).
        """
        if planning_sample is None or entry_sample is None:
            return self._not_sampled('missing_odometry_sample')
        if not isinstance(planning_sample, OdometrySample) or not isinstance(entry_sample, OdometrySample):
            return self._not_sampled('malformed_odometry_sample')
        if not isinstance(entry_pose, (list, tuple)) or tuple(entry_sample.pose) != tuple(entry_pose):
            return self._not_sampled('entry_pose_not_from_sample')
        observation = self._estimator.observe_admission(AdmissionSample(
            planning_stamp_ns=planning_sample.stamp_ns, admission_stamp_ns=entry_sample.stamp_ns,
            submit_wall_s=submitted_at, admission_wall_s=now, admission_receipt_wall_s=entry_sample.received_s))
        return dict(sampled=True, reason=observation.reason, accepted=observation.accepted,
                    interval_s=observation.interval_s, clamped=observation.clamped)

    def identity(self):
        """Fresh JSON-safe identity of the guarded prediction policy and its estimator."""
        return dict(prediction=dict(id=PREDICTION_POLICY, version=PREDICTION_POLICY_VERSION,
                                    model='constant_twist_unicycle',
                                    horizon='min(latency_s, max_shift_m/|v|, max_yaw_shift_rad/|w|)',
                                    stationary=f'|v| < {STATIONARY_SPEED} and |w| < {STATIONARY_SPEED}',
                                    end_pose_scaling=False, applied='extrapolation_branch_executed',
                                    sample='whole_odometry_message; receipt age in [0, max_sample_age_s]; '
                                           'pose must equal the measured pose',
                                    legacy_equivalent=False,
                                    config=dict(enabled=self.enabled, max_shift_m=self._config.max_shift_m,
                                                max_yaw_shift_rad=self._config.max_yaw_shift_rad,
                                                max_sample_age_s=self._config.max_sample_age_s)),
                    estimator=self._estimator.identity())

    def report(self):
        """Fresh JSON-safe counters and identity, including every no-action and estimator rejection."""
        return dict(enabled=self.enabled, latency_s=self.latency, predictions=self.predictions,
                    skipped=dict(self.skipped), not_sampled=dict(self.not_sampled),
                    max_applied_shift_m=self.max_applied_shift,
                    max_applied_yaw_shift_rad=self.max_applied_yaw_shift,
                    estimator=self._estimator.report(), identity=self.identity())


def frozen_planner_inputs(origin, resolution, width, height, costs, planning_pose, destination, lane_points,
                          heading_hint, planner_options, frozen_guidance):
    """The exact observations sent to the planning worker and saved for replay.

    Only robot_xy/robot_yaw come from the planning pose; every observed array is copied as received.
    """
    return dict(origin=list(origin), resolution=resolution, width=width, height=height,
                costs=list(costs), robot_xy=[planning_pose[0], planning_pose[1]], robot_yaw=planning_pose[2],
                destination=list(destination), lane_points=list(lane_points),
                heading_hint=heading_hint, planner_options=planner_options,
                frozen_guidance=frozen_guidance)


def rebase_heading_hint(hint, measured_pose, planning_pose):
    """Move a pose-relative heading-only hint with the planning start pose.

    GapHeadingMemory anchors its heading-only entry at the robot position, so the planner would
    otherwise see a target offset from its own start. World-anchored hints (observed entrances,
    heading_only False) and missing hints are returned unchanged. A new dict is returned; the hint
    and the memory that produced it are never modified.
    """
    if not hint or not hint.get('heading_only') or tuple(planning_pose) == tuple(measured_pose):
        return hint
    dx, dy = planning_pose[0]-measured_pose[0], planning_pose[1]-measured_pose[1]
    return dict(hint, entry=[hint['entry'][0]+dx, hint['entry'][1]+dy], rebased_from=list(hint['entry']))


def admit_from_measured_pose(compensator, admit, plan, entry_pose, entry_grid, footprint,
                             planning_sample, entry_sample, planning_context, now, submitted_at):
    """Run the caller's unchanged admission once on the ACTUAL pose/grid, then sample the latency.

    ``entry_grid`` is (origin, resolution, width, height, costs) of the latest observed grid. ``admit``
    receives exactly (plan, entry_pose, *entry_grid, footprint); its two results are returned as the
    same objects. The planning pose appears in the provenance only. Sampling happens for every attempt,
    accepted or rejected; the provenance copies the actual arguments.
    """
    admitted, admission = admit(plan, entry_pose, *entry_grid, footprint)
    sample = compensator.observe_admission(planning_sample, entry_sample, entry_pose, now, submitted_at)
    provenance = dict(enabled=planning_context['enabled'], applied=planning_context['applied'],
                      measured_pose=list(planning_context['measured_pose']),
                      planning_pose=list(planning_context['planning_pose']),
                      admission_pose=list(entry_pose),
                      planning_odom_stamp_ns=getattr(planning_sample, 'stamp_ns', None),
                      admission_odom_stamp_ns=getattr(entry_sample, 'stamp_ns', None),
                      admission_receipt_s=getattr(entry_sample, 'received_s', None),
                      admission_now_s=now, submitted_at_s=submitted_at,
                      latency_sample=sample, latency_estimate_s=compensator.latency,
                      identity=compensator.identity())
    return admitted, admission, copy.deepcopy(provenance)
