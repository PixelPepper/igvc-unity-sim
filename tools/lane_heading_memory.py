"""Bounded direction preference from observed paint; never inferred lane bounds."""
import math


class GapHeadingMemory:
    """Remember direction through a gap while observed costs still govern travel.

    ``now`` uses one consistent monotonic clock chosen by the caller. Every
    proposal advances cumulative odometry travel. A fresh accepted corridor
    replaces the previous direction, even when the two disagree.
    """
    def __init__(self, max_travel=20., max_age=60.):
        if (not math.isfinite(max_travel) or not math.isfinite(max_age)
                or max_travel <= 0 or max_age <= 0):
            raise ValueError('Heading memory limits must be finite and positive')
        self.max_travel = max_travel
        self.max_age = max_age
        self.clear()

    def clear(self):
        self.direction = None
        self.observed_at = None
        self.last_time = None
        self.last_pose = None
        self.travel = 0.

    @staticmethod
    def _pose(robot_xy):
        try:
            if len(robot_xy) != 2:
                return None
            pose = tuple(float(v) for v in robot_xy)
            return pose if all(math.isfinite(v) for v in pose) else None
        except (TypeError, ValueError, OverflowError):
            return None

    def observe(self, corridor, robot_xy, now):
        """Replace memory with a freshly accepted actual observed corridor.

        Missing observations leave memory untouched. Passing a memory-generated
        proposal is rejected, preventing remembered direction from refreshing
        its own expiry without new observed paint.
        """
        if corridor is None:
            return False
        pose = self._pose(robot_xy)
        try:
            direction = self._pose(corridor['direction'])
            valid = (pose is not None and direction is not None and math.isfinite(now)
                     and not corridor.get('heading_only', False))
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            self.clear()
            return False
        norm = math.hypot(*direction)
        if norm < 1e-9:
            self.clear()
            return False
        self.direction = tuple(v/norm for v in direction)
        self.observed_at = self.last_time = float(now)
        self.last_pose = pose
        self.travel = 0.
        return True

    def propose(self, robot_xy, robot_yaw, now, lookahead=7.):
        """Return a heading-only target, bounded by remaining supported travel.

        Caller must call this on each odometry update while using the memory so
        curved or reversing motion counts toward the travel bound. No lateral
        boundaries, free cells or collision clearance are inferred here.
        """
        if self.direction is None:
            return None
        pose = self._pose(robot_xy)
        try:
            valid = (pose is not None and all(math.isfinite(v) for v in (robot_yaw, now, lookahead))
                     and lookahead > 0 and now >= self.last_time)
        except (TypeError, ValueError):
            valid = False
        if not valid:
            self.clear()
            return None
        self.travel += math.dist(pose, self.last_pose)
        self.last_pose, self.last_time = pose, now
        age = now-self.observed_at
        alignment = math.cos(robot_yaw)*self.direction[0]+math.sin(robot_yaw)*self.direction[1]
        remaining = self.max_travel-self.travel
        if age > self.max_age or remaining <= .25 or alignment <= 0.:
            self.clear()
            return None
        distance = min(lookahead, remaining)
        return dict(entry=[pose[i]+distance*self.direction[i] for i in range(2)],
                    direction=list(self.direction),
                    yaw=math.atan2(self.direction[1], self.direction[0]),
                    heading_only=True,
                    diagnostics=dict(source='remembered_observed_heading',
                        observed_lane_bounds=False, collision_checked=False,
                        distance_since_support_m=self.travel, age_s=age,
                        remaining_travel_m=remaining, max_travel_m=self.max_travel,
                        max_age_s=self.max_age))
