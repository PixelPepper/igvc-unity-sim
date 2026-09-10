"""Dependency-free, fail-closed ordered route audit; coordinates/metres, time/seconds.

Call update(x, y, stamp, run_id=...) for every odometry sample. Errors latch;
there is deliberately no reset method. This audits traversal, not lane clearance.
"""
import bisect
import hashlib
import json
import math


class ProgressError(ValueError):
    """A sample invalidated the traversal (also recorded in snapshot.errors)."""


class CourseProgress:
    def __init__(self, points, *, waypoint_arcs=None, waypoint_xy=None, max_lateral=1.8,
                 local_window=3.0, reverse_allowance=2.0, max_speed=2.5,
                 max_sample_gap=0.5, start_tolerance=0.3,
                 waypoint_tolerance=0.3):
        self.points = [tuple(map(float, p[:2])) for p in points]
        if len(self.points) < 2 or any(len(p) != 2 or not all(map(math.isfinite, p))
                                       for p in self.points):
            raise ValueError('At least two finite XY route points required')
        self.arcs = [0.0]
        for a, b in zip(self.points, self.points[1:]):
            length = math.dist(a, b)
            if length <= 1e-9:
                raise ValueError('Consecutive duplicate route points')
            self.arcs.append(self.arcs[-1] + length)
        self.total = self.arcs[-1]
        self.waypoints = ([float(s) for s in waypoint_arcs] if waypoint_arcs is not None
                          else self.arcs[1:].copy())
        if (any(not math.isfinite(s) or s < 0 or s > self.total for s in self.waypoints)
                or any(a >= b for a, b in zip(self.waypoints, self.waypoints[1:]))):
            raise ValueError('Waypoint arcs must be finite, increasing and on route')
        self.waypoint_xy = ([tuple(map(float, p[:2])) for p in waypoint_xy]
                            if waypoint_xy is not None else [self.point_at(s) for s in self.waypoints])
        if (len(self.waypoint_xy) != len(self.waypoints)
                or any(len(p) != 2 or not all(map(math.isfinite, p)) for p in self.waypoint_xy)):
            raise ValueError('Finite XY checkpoint per waypoint arc required')
        for name, value in [('max_lateral', max_lateral), ('local_window', local_window),
                            ('reverse_allowance', reverse_allowance), ('max_speed', max_speed),
                            ('max_sample_gap', max_sample_gap), ('start_tolerance', start_tolerance),
                            ('waypoint_tolerance', waypoint_tolerance)]:
            if not math.isfinite(value) or value <= 0:
                raise ValueError(name + ' must be finite and positive')
            setattr(self, name, float(value))
        self.progress = self.maximum = self.traveled = self.lateral = 0.0
        self.next_waypoint = 0
        self.last = None
        self.run_id = None
        self.errors = []

    @classmethod
    def from_mission(cls, mission, **options):
        route = mission['route']
        if route['frame'] != 'odom':
            raise ValueError('Auditor requires odom route coordinates')
        return cls(route['dense_xy'],
                   waypoint_arcs=[w['route_s_m'] for w in mission['waypoints']],
                   waypoint_xy=[w['odom_xy'] for w in mission['waypoints']], **options)

    def _identity(self):
        payload = [self.points, self.waypoints, self.waypoint_xy]
        return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()

    def export_state(self):
        """Persist this for from_state; snapshot alone can restore an existing auditor."""
        return dict(points=self.points, waypoint_arcs=self.waypoints, waypoint_xy=self.waypoint_xy,
                    options={k: getattr(self, k) for k in (
                        'max_lateral', 'local_window', 'reverse_allowance', 'max_speed',
                        'max_sample_gap', 'start_tolerance', 'waypoint_tolerance')},
                    snapshot=self.snapshot())

    @classmethod
    def from_state(cls, state):
        result = cls(state['points'], waypoint_arcs=state['waypoint_arcs'],
                     waypoint_xy=state['waypoint_xy'], **state['options'])
        result._load_snapshot(state['snapshot'])
        return result

    def _load_snapshot(self, snapshot):
        if snapshot['route_sha256'] != self._identity():
            raise ValueError('Saved audit belongs to a different ordered route')
        fields = dict(progress='progress_m', maximum='maximum_progress_m',
                      traveled='traveled_m', lateral='lateral_m')
        for attr, key in fields.items():
            value = float(snapshot[key])
            if not math.isfinite(value) or value < 0:
                raise ValueError('Invalid saved audit ' + key)
            setattr(self, attr, value)
        self.next_waypoint = int(snapshot['ordered_waypoints_visited'])
        if not (0 <= self.progress <= self.maximum <= self.total
                and 0 <= self.next_waypoint <= len(self.waypoints)):
            raise ValueError('Saved progress outside route')
        self.last = tuple(snapshot['previous_sample']) if snapshot['previous_sample'] is not None else None
        self.run_id = snapshot['run_id']
        self.errors = list(snapshot['errors'])

    def restore(self, snapshot, current_pose, current_stamp, run_id=None):
        """Explicit stationary-pause resume, never an audit failure/reset recovery.

        Caller must ensure the robot stayed stopped during the observation gap;
        endpoint agreement alone cannot prove there was no intervening movement.
        """
        self._load_snapshot(snapshot)
        if self.errors:
            raise ProgressError('Cannot resume invalid audit: ' + self.errors[-1])
        if self.last is None:
            self._fail('Cannot resume before first observation')
        pose = tuple(map(float, current_pose[:2]))
        stamp = float(current_stamp)
        if (len(pose) != 2 or not all(map(math.isfinite, (*pose, stamp)))
                or run_id != self.run_id or stamp < self.last[2]
                or math.dist(pose, self.last[:2]) > .1):
            self._fail('Resume requires same run, nondecreasing time and pose within 0.1 m')
        # Preserve prior XY so the next sample still accounts for any small drift.
        self.last = (*self.last[:2], stamp)
        return self.snapshot()

    def _fail(self, message):
        self.errors.append(message)
        raise ProgressError(message)

    def point_at(self, arc):
        i = min(len(self.points) - 2, max(0, bisect.bisect_right(self.arcs, arc) - 1))
        f = (arc - self.arcs[i]) / (self.arcs[i + 1] - self.arcs[i])
        a, b = self.points[i:i + 2]
        return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))

    def _project(self, p, max_step=None):
        # Search only the previous arc neighbourhood: closed endpoints and nearby
        # parallel branches cannot win a global nearest-segment search.
        window = self.local_window if max_step is None else min(self.local_window, max_step)
        lo, hi = max(0., self.progress - window), min(self.total, self.progress + window)
        first = min(len(self.points) - 2, max(0, bisect.bisect_right(self.arcs, lo) - 1))
        last = min(len(self.points) - 2, bisect.bisect_left(self.arcs, hi))
        candidates = []
        for i in range(first, last + 1):
            a, b = self.points[i:i + 2]
            length = self.arcs[i + 1] - self.arcs[i]
            lower = max(0., (lo - self.arcs[i]) / length)
            upper = min(1., (hi - self.arcs[i]) / length)
            # bisect_left(hi) can include a segment starting beyond hi. An empty
            # intersection must not become t=0 and escape the reachable window.
            if lower > upper:
                continue
            t = ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / length**2
            t = max(lower, min(upper, t))
            arc = self.arcs[i] + t * length
            q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            candidates.append((math.dist(p, q), abs(arc - self.progress), arc))
        distance, _, arc = min(candidates)
        return arc, distance

    def update(self, x, y, stamp, *, run_id=None):
        if self.errors:
            raise ProgressError('Audit already invalid: ' + self.errors[-1])
        x, y, stamp = float(x), float(y), float(stamp)
        if not all(map(math.isfinite, (x, y, stamp))):
            self._fail('Non-finite odometry')
        p = (x, y)
        if self.last is None:
            if math.dist(p, self.points[0]) > self.start_tolerance:
                self._fail('Traversal did not start at ordered route origin')
            self.last = (x, y, stamp)
            self.run_id = run_id
            return self.snapshot()
        if run_id != self.run_id:
            self._fail('Simulation run changed; reset forbidden')
        dt = stamp - self.last[2]
        delta = math.dist(p, self.last[:2])
        if dt == 0 and delta <= 1e-9:
            return self.snapshot()
        if dt <= 0:
            self._fail('Odometry time reversed or moving sample has duplicate stamp')
        if dt > self.max_sample_gap:
            self._fail('Odometry gap too large to audit continuous traversal')
        if delta > self.max_speed * dt + 1e-8:
            self._fail('Teleport/speed bound exceeded (default 0.25 m per 0.1 s)')
        # Offset corners can switch their nearest segment abruptly even when
        # odometry moves smoothly. Project within the reachable arc interval,
        # rather than choose a discontinuous nearest segment and then reject it.
        # No additive per-sample credit: stationary samples cannot gain progress.
        arc, lateral = self._project(p, max_step=1.5 * delta)
        if lateral > self.max_lateral:
            self._fail('Outside ordered route lateral corridor')
        # Two adjacent orthogonal segments need up to sqrt(2)*chord. This bound
        # allows normal corners, but rejects discontinuous branch projections.
        if abs(arc - self.progress) > 1.5 * delta + 0.02:
            self._fail('Projected arc jump exceeds odometry displacement bound')
        if arc < self.maximum - self.reverse_allowance - 1e-8:
            self._fail('Reverse allowance exceeded')
        self.progress, self.lateral = arc, lateral
        self.maximum = max(self.maximum, arc)
        self.traveled += delta
        self.last = (x, y, stamp)
        while self.next_waypoint < len(self.waypoints):
            target = self.waypoints[self.next_waypoint]
            if arc + self.waypoint_tolerance < target:
                break
            # Crossing an arc without physically visiting its waypoint is not
            # enough; dense routes should use sparse explicit mission checkpoints.
            if math.dist(p, self.waypoint_xy[self.next_waypoint]) > self.waypoint_tolerance + delta:
                break
            self.next_waypoint += 1
        return self.snapshot()

    def snapshot(self):
        return dict(valid=not self.errors, errors=self.errors.copy(),
                    route_sha256=self._identity(), previous_sample=self.last, run_id=self.run_id,
                    progress_m=self.progress, maximum_progress_m=self.maximum,
                    total_arc_m=self.total, fraction=self.progress / self.total,
                    traveled_m=self.traveled, lateral_m=self.lateral,
                    reverse_from_max_m=self.maximum - self.progress,
                    ordered_waypoints_visited=self.next_waypoint,
                    ordered_waypoints_required=len(self.waypoints),
                    complete=(not self.errors and self.progress >= .98 * self.total
                              and self.next_waypoint == len(self.waypoints)))


ProgressAuditor = CourseProgress
