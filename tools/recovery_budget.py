"""Bound recovery by local trapping episodes and total mission attempts."""
import math


class RecoveryBudget:
    def __init__(self, *, total_limit, attempts_per_trap=2, release_distance=3.0):
        if (type(total_limit) is not int or total_limit < 1
                or type(attempts_per_trap) is not int or attempts_per_trap < 1
                or not math.isfinite(release_distance) or release_distance <= 0):
            raise ValueError('Positive recovery limits required')
        self.total_limit = total_limit
        self.attempts_per_trap = attempts_per_trap
        self.release_distance = release_distance
        self.total = self.local = 0
        self.anchor = self.previous = None
        self.forward_distance = 0.0
        self.episodes_cleared = 0

    def observe(self, pose):
        if len(pose) != 3 or not all(math.isfinite(v) for v in pose):
            raise ValueError('Finite odometry pose required')
        pose = tuple(pose)
        if self.previous is not None and self.anchor is not None:
            dx, dy = pose[0]-self.previous[0], pose[1]-self.previous[1]
            yaw = self.previous[2] + math.atan2(math.sin(pose[2]-self.previous[2]),
                                               math.cos(pose[2]-self.previous[2])) / 2
            # Reversing never earns progress. A back-and-forth shuffle also
            # cannot leave the original trap's release radius.
            self.forward_distance += max(0.0, dx*math.cos(yaw)+dy*math.sin(yaw))
        self.previous = pose
        released = (self.anchor is not None and self.forward_distance >= self.release_distance
                    and math.dist(pose[:2], self.anchor) >= self.release_distance)
        if released:
            self.local = 0
            self.anchor = None
            self.forward_distance = 0.0
            self.episodes_cleared += 1
        return released

    @property
    def available(self):
        return self.total < self.total_limit and self.local < self.attempts_per_trap

    def consume(self, pose):
        self.observe(pose)
        if not self.available:
            raise RuntimeError('Recovery budget exhausted')
        if self.anchor is None:
            self.anchor = tuple(pose[:2])
            self.forward_distance = 0.0
        self.total += 1
        self.local += 1

    def report(self):
        return dict(total_attempts=self.total, total_limit=self.total_limit,
                    local_attempts=self.local, attempts_per_trap=self.attempts_per_trap,
                    release_distance_m=self.release_distance, anchor=self.anchor,
                    forward_distance_m=self.forward_distance, episodes_cleared=self.episodes_cleared)
