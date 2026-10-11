"""Observation-only start/finish line crossing contract (docs/FINISH_CROSSING.md).

Pure and dependency-free: no ROS, course, WORLD, centerline or route inputs.
Runtime and audit evaluate the same line from public mission origin plus the
fixed ROS ENU +X normal, using canonical driven-axle base_footprint positions
in the origin-centred odom/ENU frame. The tracker only decides the final
crossing; ordered visits, corridor/body/paint/ramp, identity, continuity,
speed, health and recovery guards stay with their existing owners.
"""
import math

CONTRACT_VERSION = 'finish-crossing/1'
# Generator lane at the origin: y = +-3 m paint around a straight +X lane.
FIXTURE_HALF_SPAN_M = 3.
# Audit trajectory limits: 0.5 s gaps at 2.2 m/s, plus a small allowance.
MAX_INTERVAL_S = .5
MAX_STEP_M = 1.2
ARM_DEPTH_M = 1.
MIN_MOTION_M = 1e-6


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class FinishLine:
    """A finite segment through center, perpendicular to unit normal.

    The forward crossing direction is +normal. Lateral offset is measured
    along normal rotated +90 degrees (ENU left); |lateral| <= half_span_m.
    A point exactly on the line (along == 0) counts as behind it.
    """

    def __init__(self, center_x=0., center_y=0., normal_x=1., normal_y=0.,
                 half_span_m=FIXTURE_HALF_SPAN_M):
        values = (center_x, center_y, normal_x, normal_y, half_span_m)
        if not all(_finite(v) for v in values):
            raise ValueError('finish line values must be finite numbers')
        length = math.hypot(normal_x, normal_y)
        if abs(length - 1.) > 1e-9:
            raise ValueError('finish line normal must be a unit vector')
        if not 0. < half_span_m <= 10.:
            raise ValueError('finish line half span must be in (0, 10] m')
        self.center = (float(center_x), float(center_y))
        self.normal = (float(normal_x), float(normal_y))
        self.half_span_m = float(half_span_m)

    def project(self, x, y):
        """Return (along, lateral) of a point relative to the line center."""
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
    forward, bounded, within-span crossing of the base_footprint point is
    credited, and the first credit latches. Invalid input fails closed: the
    sample is rejected, continuity is broken and the tracker disarms.
    """

    def __init__(self, line=FIXTURE_LINE, *, arm_depth_m=ARM_DEPTH_M,
                 max_step_m=MAX_STEP_M, max_interval_s=MAX_INTERVAL_S):
        if not isinstance(line, FinishLine):
            raise TypeError('line must be a FinishLine')
        if not all(_finite(v) and v > 0. for v in (arm_depth_m, max_step_m, max_interval_s)):
            raise ValueError('tracker limits must be finite and positive')
        self.line = line
        self.arm_depth_m = float(arm_depth_m)
        self.max_step_m = float(max_step_m)
        self.max_interval_s = float(max_interval_s)
        self.previous = None
        self.armed = False
        self.crossing = None
        self.count = 0

    def policy(self):
        return dict(contract_version=CONTRACT_VERSION, line=self.line.describe(),
                    reference='base_footprint (driven-axle center)',
                    arm_depth_m=self.arm_depth_m, max_step_m=self.max_step_m,
                    max_interval_s=self.max_interval_s)

    def observe(self, stamp_s, x, y, *, eligible):
        """Evaluate one sample. eligible: first five destinations visited in order."""
        index = self.count
        self.count += 1
        decision = dict(contract_version=CONTRACT_VERSION, sample_index=index,
                        eligible=eligible is True, crossed=False)
        if self.crossing is not None:
            decision.update(outcome='already_crossed', crossing=dict(self.crossing))
            return decision
        if not all(_finite(v) for v in (stamp_s, x, y)) or type(eligible) is not bool:
            self.previous, self.armed = None, False
            decision.update(outcome='invalid_sample', armed=False)
            return decision
        along, lateral = self.line.project(float(x), float(y))
        current = (float(stamp_s), float(x), float(y), along, lateral, index)
        previous, self.previous = self.previous, current
        decision.update(along_m=along, lateral_m=lateral)
        if previous is None:
            # Arming needs a continuous step, so a restart cannot arm by itself.
            self.armed = False
            decision.update(outcome='first_sample' if index == 0 else 'continuity_restart',
                            armed=False)
            return decision
        dt = current[0] - previous[0]
        step = math.hypot(current[1] - previous[1], current[2] - previous[2])
        decision.update(previous_sample_index=previous[5], interval_s=dt, step_m=step)
        if dt <= 0. or dt > self.max_interval_s:
            self.previous, self.armed = None, False
            decision.update(outcome='discontinuous_interval', armed=False)
            return decision
        if step > self.max_step_m:
            self.previous, self.armed = None, False
            decision.update(outcome='step_too_long', armed=False)
            return decision
        was_armed = self.armed
        before, after = previous[3], along
        if before > 0. >= after:
            # Backing across the line forfeits arming until a new approach.
            self.armed = False
            decision.update(outcome='reverse', armed=False)
            return decision
        if not before <= 0. < after:
            self._arm(current, eligible)
            outcome = 'stationary' if step <= MIN_MOTION_M else 'no_crossing'
            decision.update(outcome=outcome, armed=self.armed)
            return decision
        fraction = -before / (after - before)
        crossing_lateral = previous[4] + fraction*(lateral - previous[4])
        provenance = dict(
            previous_sample_index=previous[5], sample_index=index,
            stamp_s=previous[0] + fraction*dt, fraction=fraction,
            x=previous[1] + fraction*(current[1] - previous[1]),
            y=previous[2] + fraction*(current[2] - previous[2]),
            lateral_m=crossing_lateral, along_before_m=before, along_after_m=after,
            step_m=step, interval_s=dt,
            direction_cosine=(after - before)/step if step > 0. else None)
        decision['candidate'] = provenance
        self.armed = False
        if not eligible:
            outcome = 'ineligible'
        elif not was_armed:
            outcome = 'not_armed'
        elif abs(crossing_lateral) > self.line.half_span_m:
            outcome = 'outside_span'
        else:
            self.crossing = provenance
            decision.update(outcome='crossed', crossed=True, armed=False, crossing=dict(provenance))
            return decision
        decision.update(outcome=outcome, armed=False)
        return decision

    def _arm(self, sample, eligible):
        # Arm only from an eligible observation behind the line within its span.
        _, _, _, along, lateral, _ = sample
        if not eligible:
            self.armed = False
        elif along <= -self.arm_depth_m and abs(lateral) <= self.line.half_span_m:
            self.armed = True
        elif along > 0.:
            self.armed = False

    def report(self):
        """Honest ledger summary: crossing provenance or explicit absence."""
        return dict(self.policy(), crossed=self.crossing is not None,
                    crossing=dict(self.crossing) if self.crossing else None,
                    samples_observed=self.count)
