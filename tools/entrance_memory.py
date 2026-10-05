"""Remember a fixed, observed paint-pair entrance; never extrapolate lane bounds."""
import math


class ObservedEntranceMemory:
    """Optional approach target memory, independent of collision checking.

    Call ``propose`` on each odometry update so cumulative travel is bounded.
    ``now`` must use one consistent clock. The caller must ``clear`` when the
    destination changes. ``lookahead`` is accepted for API compatibility, but
    never translates or extends the observed entry.

    ``diagnostics`` remains available after a None result: observed_approach is
    freshly supported, in_gap retains a target after missing/rejected paint,
    reacquiring means its entrance was reached/passed, and unobserved means no
    usable target remains. None of these states establishes collision clearance.
    """

    def __init__(self, max_travel=20., max_age=60., reached_distance=.7):
        if not all(self._number(v) is not None and self._number(v) > 0
                   for v in (max_travel, max_age, reached_distance)):
            raise ValueError('Entrance memory limits must be finite and positive')
        self.max_travel = float(max_travel)
        self.max_age = float(max_age)
        self.reached_distance = float(reached_distance)
        self.clear()

    @staticmethod
    def _number(value):
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
            return number if math.isfinite(number) else None
        except (TypeError, ValueError, OverflowError):
            return None

    @classmethod
    def _pose(cls, value):
        try:
            if len(value) != 2:
                return None
            result = tuple(cls._number(v) for v in value)
            return result if None not in result else None
        except TypeError:
            return None

    def _report(self, state, reason, age=None):
        self.diagnostics = dict(state=state, reason=reason, age_s=age,
            distance_since_support_m=self.travel, max_age_s=self.max_age,
            max_travel_m=self.max_travel, collision_checked=False,
            observed_lane_bounds=False)

    def clear(self):
        """Forget the entrance, including on an incompatible new destination."""
        self.entry = self.direction = self.segments = self.confidence = None
        self.observed_at = self.observed_pose = None
        self.last_time = self.last_pose = None
        self._last_geometry = None
        self._last_support_stamp_ns = None
        self.travel = 0.
        self._report('unobserved', 'cleared')

    def _invalidate(self, reason, age=None, state='unobserved'):
        # Preserve the expiry evidence after discarding the usable target.
        travel = self.travel
        geometry = self._last_geometry
        proof = self._last_support_stamp_ns
        self.clear()
        self.travel = travel
        self._last_geometry = geometry
        self._last_support_stamp_ns = proof
        self._report(state, reason, age)

    def _advance(self, pose, now):
        if self.entry is None:
            return False
        if now < self.last_time:
            self._invalidate('clock_reset', now-self.observed_at)
            return False
        self.travel += math.dist(pose, self.last_pose)
        self.last_time, self.last_pose = now, pose
        age = now-self.observed_at
        if age > self.max_age:
            self._invalidate('age_limit', age)
        elif self.travel > self.max_travel:
            self._invalidate('travel_limit', age)
        elif math.dist(pose, self.entry) <= self.reached_distance:
            self._invalidate('entrance_reached', age, 'reacquiring')
        elif sum((pose[i]-self.entry[i])*self.direction[i] for i in (0, 1)) >= 0.:
            self._invalidate('entrance_passed', age, 'reacquiring')
        else:
            return True
        return False

    def observe(self, corridor, robot_xy, now, *, support_stamp_ns=None):
        """Store an actual supported corridor; proposals cannot refresh it.

        An actual corridor must contain finite entry/direction/confidence and
        two nondegenerate observed segments in diagnostics, as emitted by
        propose_lane_corridor. Missing or rejected observations do not reset
        support time/travel. Invalid clock or odometry clears the usable target.
        An optional positive integer support_stamp_ns is acquisition evidence
        supplied by the caller's bilateral freshness gate, not a cloud header.
        A newer proof may renew an active identical entrance; consumed geometry
        cannot revive until an explicit clear or a different observed entrance.
        """
        pose, timestamp = self._pose(robot_xy), self._number(now)
        if pose is None or timestamp is None:
            self._invalidate('invalid_input')
            return False
        if self.last_time is not None and timestamp < self.last_time:
            self._invalidate('clock_reset', timestamp-self.observed_at)
            return False
        if self.entry is not None:
            self._advance(pose, timestamp)
        if corridor is None:
            if self.entry is not None:
                self._report('in_gap', 'missing_corridor', timestamp-self.observed_at)
            return False
        if support_stamp_ns is not None and (type(support_stamp_ns) is not int or support_stamp_ns <= 0):
            self._report('in_gap' if self.entry is not None else 'unobserved',
                         'invalid_support_stamp', timestamp-self.observed_at if self.entry is not None else None)
            return False
        try:
            entry = self._pose(corridor['entry'])
            direction = self._pose(corridor['direction'])
            confidence = self._number(corridor['confidence'])
            raw_segments = corridor['diagnostics']['segments']
            segments = [[self._pose(point) for point in segment] for segment in raw_segments]
            valid = (not corridor.get('heading_only', False)
                and not corridor.get('observed_entrance', False)
                and entry is not None and direction is not None
                and confidence is not None and 0. < confidence <= 1.
                and len(segments) == 2
                and all(len(s) == 2 and None not in s and math.dist(*s) > 1e-9 for s in segments))
        except (KeyError, TypeError, ValueError, OverflowError):
            valid = False
        if valid:
            norm = math.hypot(*direction)
            valid = math.isfinite(norm) and norm > 1e-9
        if not valid:
            self._report('in_gap' if self.entry is not None else 'unobserved',
                         'rejected_observation', timestamp-self.observed_at if self.entry is not None else None)
            return False
        direction = tuple(v/norm for v in direction)
        geometry = (entry, direction, tuple(tuple(s) for s in segments))
        # Cloud headers and confidence changes alone are not acquisition proof.
        # A consumed entrance remains suppressed even with newer acquisitions.
        if geometry == self._last_geometry:
            newer_proof = (support_stamp_ns is not None and
                (self._last_support_stamp_ns is None or support_stamp_ns > self._last_support_stamp_ns))
            if self.entry is None or not newer_proof:
                self._report('in_gap' if self.entry is not None else self.diagnostics['state'],
                             'repeated_geometry', timestamp-self.observed_at if self.entry is not None else self.diagnostics['age_s'])
                return False
        if (math.dist(pose, entry) <= self.reached_distance or
                sum((pose[i]-entry[i])*direction[i] for i in (0, 1)) >= 0.):
            self._invalidate('observed_entrance_already_reached_or_passed', state='reacquiring')
            return False
        self.entry, self.direction, self.confidence = entry, direction, confidence
        self.segments = tuple(tuple(s) for s in segments)
        self._last_geometry = geometry
        self._last_support_stamp_ns = support_stamp_ns
        self.observed_at = self.last_time = timestamp
        self.observed_pose = self.last_pose = pose
        self.travel = 0.
        self._report('observed_approach', 'actual_corridor_observed', 0.)
        return True

    def propose(self, robot_xy, robot_yaw, now, lookahead=7.):
        """Return the fixed entrance, or None with an explicit retained reason."""
        if self.entry is None:
            return None
        pose, timestamp = self._pose(robot_xy), self._number(now)
        lookahead_value = self._number(lookahead)
        if (pose is None or timestamp is None or self._number(robot_yaw) is None
                or lookahead_value is None or lookahead_value <= 0):
            self._invalidate('invalid_input')
            return None
        if not self._advance(pose, timestamp):
            return None
        self._report(self.diagnostics['state'], self.diagnostics['reason'], timestamp-self.observed_at)
        diagnostics = dict(self.diagnostics, source='remembered_observed_entrance',
            observed_at=self.observed_at, observed_pose=list(self.observed_pose),
            support_stamp_ns=self._last_support_stamp_ns,
            segments=[[list(point) for point in segment] for segment in self.segments])
        return dict(entry=list(self.entry), direction=list(self.direction),
            yaw=math.atan2(self.direction[1], self.direction[0]), confidence=self.confidence,
            observed_entrance=True, heading_only=False, collision_checked=False,
            diagnostics=diagnostics)
