"""Bounded target intent after backup; contains no route or collision authority."""
import copy
import math

from observed_navigation import valid_guidance


def _number(value):
    try:
        return not isinstance(value, bool) and math.isfinite(value)
    except (TypeError, ValueError, OverflowError):
        return False


def _coordinates(value, size):
    try:
        if len(value) != size or not all(_number(v) for v in value):
            raise ValueError
        return tuple(float(v) for v in value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError('Finite coordinates required') from None


class RecoveryIntent:
    """Preserve one selected target for at most 30 seconds after backup.

    Call propose with measured axle pose (x, y, yaw), using one monotonic clock.
    Progress uses positive body-X displacement with midpoint heading, not path
    length or commanded motion. The caller owns fresh sensing and all clearance.
    """

    def __init__(self):
        self._guidance = None
        self.diagnostics = {'state': 'inactive', 'reason': 'uninstalled',
                            'max_age_s': 30., 'collision_checked': False}

    @property
    def active(self):
        return self._guidance is not None

    def clear(self, reason):
        self._guidance = None
        self.diagnostics = {**self.diagnostics, 'state': 'inactive', 'reason': reason}

    def install(self, guidance, trap_pose, backup_pose, now, destination_index):
        """Install after measured successful backup; invalid input clears and raises."""
        try:
            # Optional yaw is normalized to the shared selection record. Broad
            # GPS deliberately has null yaw; observed directions can be numeric.
            guidance = {**guidance, 'yaw': guidance.get('yaw')} if isinstance(guidance, dict) else guidance
            if (not valid_guidance(guidance)
                    or not _number(now)
                    or type(destination_index) is not int or destination_index < 0):
                raise ValueError('Finite recovery intent inputs required')
            target = _coordinates(guidance['target'], 2)
            trap = _coordinates(trap_pose, 3)
            backup = _coordinates(backup_pose, 3)
        except ValueError:
            self.clear('invalid_input')
            raise
        self._guidance = copy.deepcopy(guidance)
        self._target, self._trap, self._backup = target, trap, backup
        self._previous = backup
        self._installed_at = self._last_time = float(now)
        self._destination_index = destination_index
        self._forward = 0.
        self._trap_target_distance = math.dist(trap[:2], target)
        self.diagnostics = {'state': 'active', 'reason': 'installed',
            'destination_index': destination_index, 'guidance': guidance['guidance'],
            'target': list(target), 'age_s': 0., 'max_age_s': 30.,
            'positive_forward_m': 0., 'net_distance_from_backup_m': 0.,
            'improvement_beyond_trap_m': self._trap_target_distance-math.dist(backup[:2], target),
            'target_distance_m': math.dist(backup[:2], target), 'collision_checked': False}

    def propose(self, pose, now, destination_index):
        if not self.active:
            return None
        try:
            pose = _coordinates(pose, 3)
            if not _number(now) or type(destination_index) is not int or destination_index < 0:
                raise ValueError('Finite recovery intent inputs required')
        except ValueError:
            self.clear('invalid_input')
            return None
        if destination_index != self._destination_index:
            self.clear('destination_changed')
            return None
        if now < self._last_time:
            self.clear('clock_reset')
            return None
        age = float(now)-self._installed_at
        self.diagnostics['age_s'] = age
        if age >= 30.:
            self.clear('expired')
            return None
        dx, dy = pose[0]-self._previous[0], pose[1]-self._previous[1]
        yaw = self._previous[2]+math.atan2(math.sin(pose[2]-self._previous[2]),
                                          math.cos(pose[2]-self._previous[2]))/2
        self._forward += max(0., dx*math.cos(yaw)+dy*math.sin(yaw))
        self._previous, self._last_time = pose, float(now)
        net = math.dist(pose[:2], self._backup[:2])
        distance = math.dist(pose[:2], self._target)
        improvement = self._trap_target_distance-distance
        target_yaw = self._guidance['yaw']
        heading_error = (None if target_yaw is None else
            math.atan2(math.sin(target_yaw-pose[2]), math.cos(target_yaw-pose[2])))
        self.diagnostics.update(reason='retained', positive_forward_m=self._forward,
            net_distance_from_backup_m=net, improvement_beyond_trap_m=improvement,
            target_distance_m=distance, heading_error_rad=heading_error)
        if distance <= .25 and (heading_error is None or abs(heading_error) <= .35):
            self.clear('target_reached')
            return None
        if self._forward >= 1. and net >= 1. and improvement >= .5:
            self.clear('trap_cleared')
            return None
        return copy.deepcopy(self._guidance)
