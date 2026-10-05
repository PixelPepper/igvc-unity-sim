"""Bounded memory of the robot's own stall regions; never reads course data.

A region is recorded only from proprioception at a detected stall: the axle
pose, the heading on which the robot entered (its own recent trajectory), and
a disc ahead of the front bumper where the observed pocket lies (default:
centre 1.4 m ahead of the axle, radius 0.8 m, i.e. 0.6-2.2 m ahead, +-0.8 m
lateral). The stall pose itself stays outside the disc so that a continuation
may pass the stall pose while turning away, but cannot drive into the pocket. Consumers
receive a COPY of the observed grid with those cells lethal, so continuation
searches cannot re-enter the pocket. The live costmap is never modified.
Regions expire by age, by net distance travelled away, or on a new destination.
"""
import copy
import math


def _finite(*values):
    try:
        return all(not isinstance(v, bool) and math.isfinite(v) for v in values)
    except TypeError:
        return False


def recent_path(trajectory, max_age_s=60., max_length_m=6., min_spacing_m=.05):
    """Return the newest <= max_length_m of driven axle positions, oldest first.

    ``trajectory`` rows are [stamp_s, x, y, yaw] from odometry (proprioceptive
    history only). Rows older than max_age_s before the newest row are ignored.
    Positions are thinned to min_spacing_m; the newest row is always included.
    """
    if not trajectory:
        return []
    newest = trajectory[-1]
    if len(newest) < 3 or not _finite(*newest[:3]):
        return []
    points = [(float(newest[1]), float(newest[2]))]
    length = 0.
    for row in reversed(trajectory[:-1]):
        if len(row) < 3 or not _finite(*row[:3]) or newest[0]-row[0] > max_age_s:
            break
        step = math.dist(points[-1], row[1:3])
        if step < min_spacing_m:
            continue
        if length+step > max_length_m:
            break
        length += step
        points.append((float(row[1]), float(row[2])))
    return points[::-1]


def path_length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def entry_heading(points, span_m=1.5):
    """Heading of the robot's own displacement over the last span_m of path."""
    if len(points) < 2:
        return None
    end = points[-1]
    for point in reversed(points[:-1]):
        if math.dist(point, end) >= span_m:
            break
    if math.dist(point, end) < .2:
        return None
    return math.atan2(end[1]-point[1], end[0]-point[0])


def point_in_regions(xy, regions, margin=0.):
    return any(math.dist(xy, r['center']) <= r['radius']+margin for r in regions)


def mask_costs(costs, width, height, resolution, origin, regions, keep_clear=None):
    """Return (copy of costs with region cells lethal, number of cells changed).

    ``keep_clear`` = (x, y, yaw, footprint) leaves cells whose centres lie
    under the current body unmasked, so a robot whose body still touches a
    region after an imperfect backup can be planned for; any forward motion
    into the region remains blocked because the surrounding cells are lethal.
    """
    masked = list(costs)
    changed = 0
    if keep_clear is not None:
        kx, ky, kyaw, (bx0, bx1, by0, by1) = keep_clear
        kc, ks = math.cos(kyaw), math.sin(kyaw)
    for region in regions:
        cx, cy = region['center']
        radius = region['radius']
        left = max(0, math.floor((cx-radius-origin[0])/resolution))
        right = min(width-1, math.floor((cx+radius-origin[0])/resolution))
        bottom = max(0, math.floor((cy-radius-origin[1])/resolution))
        top = min(height-1, math.floor((cy+radius-origin[1])/resolution))
        for iy in range(bottom, top+1):
            wy = origin[1]+(iy+.5)*resolution
            for ix in range(left, right+1):
                wx = origin[0]+(ix+.5)*resolution
                if (wx-cx)**2+(wy-cy)**2 > radius*radius:
                    continue
                if keep_clear is not None:
                    dx, dy = wx-kx, wy-ky
                    lx, ly = dx*kc+dy*ks, -dx*ks+dy*kc
                    if bx0 <= lx <= bx1 and by0 <= ly <= by1:
                        continue
                index = iy*width+ix
                if masked[index] != 100:
                    masked[index] = 100
                    changed += 1
    return masked, changed


class TrapMemory:
    """At most ``max_regions`` stall discs, each bounded in age and distance."""

    def __init__(self, radius_m=.8, front_offset_m=1.4, max_age_s=120.,
                 release_distance_m=8., max_regions=3, history_limit=20):
        if not (_finite(radius_m, front_offset_m, max_age_s, release_distance_m)
                and 0 < radius_m <= 2. and 0 <= front_offset_m <= 2.
                and 0 < max_age_s <= 300. and 0 < release_distance_m <= 20.
                and isinstance(max_regions, int) and 1 <= max_regions <= 5):
            raise ValueError('Invalid trap memory bounds')
        self.radius = float(radius_m)
        self.front_offset = float(front_offset_m)
        self.max_age = float(max_age_s)
        self.release_distance = float(release_distance_m)
        self.max_regions = max_regions
        self.history_limit = history_limit
        self._regions = []
        self._expired = []
        self._recorded = 0

    @property
    def active(self):
        return bool(self._regions)

    def regions(self):
        """Picklable geometry only: what planners need, nothing else."""
        return [{'center': list(r['center']), 'radius': r['radius']} for r in self._regions]

    def record(self, stall_pose, now, destination_index, entry_yaw=None, protect_xy=None, protect_radius_m=0.):
        """Remember a stall region; returns None (nothing recorded) when it would cover protect_xy.

        A stall within reach of the current destination is an approach problem, not a closed
        pocket: remembering it would forbid the goal itself (seen live on 2026-10-02).
        """
        x, y, yaw = stall_pose
        if not _finite(x, y, yaw, now) or (entry_yaw is not None and not _finite(entry_yaw)):
            raise ValueError('Finite trap memory inputs required')
        center = [x+self.front_offset*math.cos(yaw), y+self.front_offset*math.sin(yaw)]
        if protect_xy is not None and math.dist(center, protect_xy) <= self.radius+protect_radius_m:
            return None
        self._recorded += 1
        region = {'id': self._recorded,
                  'center': center,
                  'radius': self.radius, 'stall_pose': [x, y, yaw],
                  'entry_yaw': entry_yaw, 'recorded_at': float(now),
                  'destination_index': destination_index}
        self._regions.append(region)
        while len(self._regions) > self.max_regions:
            self._retire(self._regions[0], 'capacity', now)
        return copy.deepcopy(region)

    def _retire(self, region, reason, now):
        self._regions.remove(region)
        self._expired.append({**region, 'expired_reason': reason, 'age_s': float(now)-region['recorded_at']})
        del self._expired[:-self.history_limit]

    def observe(self, pose, now, destination_index):
        """Expire regions; return the expired records (for logging)."""
        before = len(self._expired)
        for region in list(self._regions):
            if destination_index != region['destination_index']:
                reason = 'destination_changed'
            elif not _finite(now) or now < region['recorded_at']:
                reason = 'clock_reset'
            elif now-region['recorded_at'] >= self.max_age:
                reason = 'expired'
            elif math.dist(pose[:2], region['center']) >= self.release_distance:
                reason = 'released_by_distance'
            else:
                continue
            self._retire(region, reason, now)
        return copy.deepcopy(self._expired[before:])

    def clear(self, reason, now):
        for region in list(self._regions):
            self._retire(region, reason, now)

    def report(self):
        return {'radius_m': self.radius, 'front_offset_m': self.front_offset,
                'max_age_s': self.max_age, 'release_distance_m': self.release_distance,
                'max_regions': self.max_regions, 'recorded': self._recorded,
                'active': copy.deepcopy(self._regions), 'expired': copy.deepcopy(self._expired)}


def exclude_trapped_guidance(selected, destination_xy, regions, stall_xy=None,
                             consumed_distance_m=1.):
    """Reject a recovery guidance target inside a remembered trap.

    A target within consumed_distance_m of the stall axle is also rejected:
    the backup acceptance rule needs >=0.5 m of progress beyond the trap
    toward the target, which such an already-reached target cannot provide.
    Returns (selection or None, diagnostics). A rejected observed target is
    replaced by the broad GPS destination (null yaw), which is sensor-legal
    mission input, unless that destination is itself trapped. The
    replacement is always reported, never silent.
    """
    trapped = bool(regions) and point_in_regions(selected['target'], regions)
    consumed = stall_xy is not None and math.dist(selected['target'], stall_xy) < consumed_distance_m
    if not trapped and not consumed:
        return selected, {'excluded': False}
    diagnostics = {'excluded': True, 'trapped_selection': copy.deepcopy(selected),
                   'target_inside_trap': trapped, 'target_consumed': consumed}
    if point_in_regions(destination_xy, regions or []) or (
            stall_xy is not None and math.dist(destination_xy, stall_xy) < consumed_distance_m):
        diagnostics['reason'] = 'destination_inside_trap'
        return None, diagnostics
    diagnostics['reason'] = 'broad_gps_fallback'
    return {'guidance': 'broad_gps', 'target': [float(destination_xy[0]), float(destination_xy[1])],
            'yaw': None}, diagnostics


def evaluate_with_trap_memory(regions, origin, resolution, width, height, costs,
                              robot_xy, robot_yaw, *args, **kwargs):
    """Worker entry: plan on a masked COPY of the observed grid.

    Same signature as observed_navigation.evaluate_observed_navigation with the
    trap regions prepended. The current body is kept clear (see mask_costs).
    """
    from observed_navigation import evaluate_observed_navigation
    footprint = kwargs.get('goal_footprint')
    keep = (robot_xy[0], robot_xy[1], robot_yaw, footprint) if footprint is not None else None
    masked, changed = mask_costs(costs, width, height, resolution, origin, regions, keep_clear=keep)
    result = evaluate_observed_navigation(origin, resolution, width, height, masked,
                                          robot_xy, robot_yaw, *args, **kwargs)
    result['diagnostics']['trap_memory'] = {'regions': copy.deepcopy(regions),
                                            'masked_cells': changed}
    return result
