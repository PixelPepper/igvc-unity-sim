"""Observation-only start/finish line crossing contract (docs/FINISH_CROSSING.md).

Pure and dependency-free: no ROS, course, WORLD, centerline or route inputs.
Runtime and audit evaluate the same line from public mission origin plus the
fixed ROS ENU +X normal, using canonical driven-axle base_footprint positions
in the origin-centred odom/ENU frame. The tracker only decides the final
crossing; ordered visits, corridor/body/paint/ramp, identity, health and
recovery guards stay with their existing owners.
"""
import math

CONTRACT_VERSION = 'finish-crossing/1'
LEGACY_CONTRACT = 'legacy'
# Generator lane at the origin: y = +-3 m paint around a straight +X lane.
FIXTURE_HALF_SPAN_M = 3.
# Audit trajectory limits: 0.5 s gaps at 2.2 m/s. Every continuous interval
# must satisfy step <= (2.2 + 1e-6) m/s * dt and the absolute 1.2 m bound.
MAX_INTERVAL_S = .5
MAX_SPEED_MPS = 2.2
SPEED_ALLOWANCE_MPS = 1e-6
MAX_STEP_M = 1.2
ARM_DEPTH_M = 1.
# Forward candidates whose step is at or below this are tiny_jitter.
MIN_MOTION_M = 1e-6
# Audit compatibility tolerance for unit direction, center and half width.
AUDIT_TOLERANCE = 1e-6


def _finite_float(value):
    """Return a finite float, or None for bools, non-numbers, overflowing ints, inf and nan."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        value = float(value)
    except OverflowError:
        return None
    return value if math.isfinite(value) else None


def _all_finite(*values):
    return all(isinstance(v, float) and math.isfinite(v) for v in values)


def _distance(dx, dy):
    # hypot raises on overflow from finite inputs; report it as inf instead.
    try:
        return math.hypot(dx, dy)
    except OverflowError:
        return math.inf


def select_contract(run):
    """Select the finish contract for an audit report's run block.

    No finish_crossing key selects the legacy radius rules. A present block
    must carry exactly CONTRACT_VERSION; anything else fails closed.
    """
    if not isinstance(run, dict):
        raise ValueError('run must be a mapping')
    if 'finish_crossing' not in run:
        return LEGACY_CONTRACT
    block = run['finish_crossing']
    version = block.get('contract_version') if isinstance(block, dict) else None
    if not isinstance(version, str) or version != CONTRACT_VERSION:
        raise ValueError(f'unsupported finish contract version: {version!r}')
    return CONTRACT_VERSION


class FinishLine:
    """A finite segment through center, perpendicular to unit normal.

    The forward crossing direction is +normal. Lateral offset is measured
    along normal rotated +90 degrees (ENU left); |lateral| <= half_span_m.
    A point exactly on the line (along == 0) counts as behind it.
    """

    def __init__(self, center_x=0., center_y=0., normal_x=1., normal_y=0.,
                 half_span_m=FIXTURE_HALF_SPAN_M):
        values = [_finite_float(v) for v in (center_x, center_y, normal_x, normal_y, half_span_m)]
        if None in values:
            raise ValueError('finish line values must be finite numbers')
        center_x, center_y, normal_x, normal_y, half_span_m = values
        if abs(_distance(normal_x, normal_y) - 1.) > 1e-9:
            raise ValueError('finish line normal must be a unit vector')
        if not 0. < half_span_m <= 10.:
            raise ValueError('finish line half span must be in (0, 10] m')
        self.center = (center_x, center_y)
        self.normal = (normal_x, normal_y)
        self.half_span_m = half_span_m

    def project(self, x, y):
        """Return (along, lateral) relative to the center; may overflow for extreme inputs."""
        dx, dy = x - self.center[0], y - self.center[1]
        nx, ny = self.normal
        return dx*nx + dy*ny, -dx*ny + dy*nx

    def describe(self):
        return dict(center_xy=list(self.center), normal_xy=list(self.normal),
                    half_span_m=self.half_span_m)


# Public mission origin is odom/ENU (0, 0); the fixture lane leaves and
# rejoins it along ROS +X (east). No armed heading or WORLD tangent is used.
FIXTURE_LINE = FinishLine()


class FinishCrossingTracker:
    """Deterministic sequential crossing decisions over (stamp_s, x, y) samples.

    observe() returns one decision per sample. Only an eligible, armed,
    forward, moving, speed-bounded, within-span crossing of the base_footprint
    point is credited, and the first credit latches. Invalid input, including
    values whose arithmetic overflows, fails closed: the sample is rejected,
    continuity is broken and the tracker disarms. Decisions never carry inf
    or nan.
    """

    def __init__(self, line=FIXTURE_LINE, *, arm_depth_m=ARM_DEPTH_M, max_step_m=MAX_STEP_M,
                 max_interval_s=MAX_INTERVAL_S, max_speed_mps=MAX_SPEED_MPS):
        if not isinstance(line, FinishLine):
            raise ValueError('line must be a FinishLine')
        limits = [_finite_float(v) for v in (arm_depth_m, max_step_m, max_interval_s, max_speed_mps)]
        if not all(v is not None and v > 0. for v in limits):
            raise ValueError('tracker limits must be finite and positive')
        self.line = line
        self.arm_depth_m, self.max_step_m, self.max_interval_s, self.max_speed_mps = limits
        self.previous = None
        self.armed = False
        self.crossing = None
        self.count = 0
        # Bounded provenance: only the latest decision and forward candidate.
        self.last_outcome = None
        self.last_candidate = None

    def policy(self):
        return dict(contract_version=CONTRACT_VERSION, line=self.line.describe(),
                    reference='base_footprint (driven-axle center)',
                    arm_depth_m=self.arm_depth_m, max_step_m=self.max_step_m,
                    max_interval_s=self.max_interval_s, max_speed_mps=self.max_speed_mps,
                    speed_allowance_mps=SPEED_ALLOWANCE_MPS, min_motion_m=MIN_MOTION_M,
                    audit_tolerance=AUDIT_TOLERANCE)

    def observe(self, stamp_s, x, y, *, eligible):
        """Evaluate one sample. eligible: first five destinations visited in order."""
        index = self.count
        self.count += 1
        decision = dict(contract_version=CONTRACT_VERSION, sample_index=index,
                        eligible=eligible is True, crossed=False)
        stamp, x, y = (_finite_float(v) for v in (stamp_s, x, y))
        along = lateral = None
        if None not in (stamp, x, y):
            along, lateral = self.line.project(x, y)
        if type(eligible) is not bool or not _all_finite(along, lateral):
            return self._reject(decision, 'invalid_sample')
        if self.crossing is not None:
            decision['crossing'] = dict(self.crossing)
            return self._record(decision, 'already_crossed')
        current = (stamp, x, y, along, lateral, index)
        previous, self.previous = self.previous, current
        decision.update(along_m=along, lateral_m=lateral)
        if previous is None:
            # Arming needs a continuous step, so a restart cannot arm by itself.
            self.armed = False
            return self._record(decision, 'first_sample' if index == 0 else 'continuity_restart')
        dt = stamp - previous[0]
        step = _distance(x - previous[1], y - previous[2])
        if not _all_finite(dt, step):
            # Extreme finite stamps or positions overflow the interval arithmetic.
            return self._reject(decision, 'invalid_sample')
        decision.update(previous_sample_index=previous[5], interval_s=dt, step_m=step)
        if dt <= 0. or dt > self.max_interval_s:
            return self._reject(decision, 'discontinuous_interval')
        if step > self.max_step_m:
            return self._reject(decision, 'step_too_long')
        # Compare without dividing so a tiny interval cannot produce inf.
        if step > (self.max_speed_mps + SPEED_ALLOWANCE_MPS)*dt:
            return self._reject(decision, 'speed_too_high')
        decision['speed_mps'] = step/dt
        was_armed = self.armed
        before = previous[3]
        if before > 0. >= along:
            # Backing across the line forfeits arming until a new approach.
            self.armed = False
            return self._record(decision, 'reverse')
        if not before <= 0. < along:
            self._arm(current, eligible)
            return self._record(decision, 'stationary' if step <= MIN_MOTION_M else 'no_crossing')
        fraction = -before / (along - before)
        crossing_lateral = previous[4] + fraction*(lateral - previous[4])
        provenance = dict(
            previous_sample_index=previous[5], sample_index=index,
            stamp_s=previous[0] + fraction*dt, fraction=fraction,
            x=previous[1] + fraction*(x - previous[1]),
            y=previous[2] + fraction*(y - previous[2]),
            lateral_m=crossing_lateral, along_before_m=before, along_after_m=along,
            step_m=step, interval_s=dt, speed_mps=step/dt,
            direction_cosine=(along - before)/step if step > 0. else None)
        decision['candidate'] = provenance
        self.armed = False
        if step <= MIN_MOTION_M:
            outcome = 'tiny_jitter'
        elif not eligible:
            outcome = 'ineligible'
        elif not was_armed:
            outcome = 'not_armed'
        elif abs(crossing_lateral) > self.line.half_span_m:
            outcome = 'outside_span'
        else:
            self.crossing = provenance
            decision.update(crossed=True, crossing=dict(provenance))
            outcome = 'crossed'
        return self._record(decision, outcome)

    def _arm(self, sample, eligible):
        # Arm only from an eligible observation behind the line within its span.
        _, _, _, along, lateral, _ = sample
        if not eligible:
            self.armed = False
        elif along <= -self.arm_depth_m and abs(lateral) <= self.line.half_span_m:
            self.armed = True
        elif along > 0.:
            self.armed = False

    def _reject(self, decision, outcome):
        self.previous, self.armed = None, False
        return self._record(decision, outcome)

    def _record(self, decision, outcome):
        decision.update(outcome=outcome, armed=self.armed)
        self.last_outcome = {k: v for k, v in decision.items() if not isinstance(v, dict)}
        if 'candidate' in decision:
            self.last_candidate = dict(decision['candidate'], outcome=outcome)
        return decision

    def report(self):
        """Honest ledger summary: crossing provenance or explicit absence, plus last outcome."""
        return dict(self.policy(), crossed=self.crossing is not None,
                    crossing=dict(self.crossing) if self.crossing else None,
                    samples_observed=self.count,
                    last_outcome=dict(self.last_outcome) if self.last_outcome else None,
                    last_candidate=dict(self.last_candidate) if self.last_candidate else None)
