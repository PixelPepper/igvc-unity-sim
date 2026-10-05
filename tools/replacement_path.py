"""Opt-in continuity when a replacement path is rejected (checked-path mode).

Default behavior is unchanged: a rejected replacement cancels the active
FollowPath action. With the option enabled, exactly one extra check is made:
the admitted plan the *running* action was given is re-admitted from the same
pose and observed costmap snapshot that rejected the replacement, with the same
`prepare_controller_plan` used for every new path (unchanged cross-track,
heading, turn-radius, connector limits, full-footprint connector and suffix
sweeps, unknown cells blocking). That call returns a new connector joined to an
unchanged suffix of the running path. Only that returned geometry, exactly as
checked, may be sent as a new FollowPath goal: the old action is never kept
running on geometry that was not swept from the current pose. Anything else
fails closed to the existing cancellation. Nothing here talks to ROS.
"""

DISABLED, SEND_NEW, SEND_REVALIDATED, CANCEL = 'disabled', 'send_new', 'send_revalidated_active', 'cancel'


class ActivePathRecord:
    """The admitted plan that was actually sent and accepted, with its identity."""

    __slots__ = ('plan', 'goal_id', 'destination', 'sequence', 'target')

    def __init__(self, plan, goal_id, destination, sequence, target):
        self.plan, self.goal_id, self.destination = plan, goal_id, destination
        self.sequence, self.target = sequence, target


def running_action(handle, result):
    """(goal_id hex or None, running) from a live action handle and its result future.

    Running is True only for an existing handle with an unfinished result.
    """
    goal_id = bytes(handle.goal_id.uuid).hex() if handle is not None else None
    return goal_id, handle is not None and result is not None and not result.done()


def snapshot_revalidator(prepare, pose, grid, footprint):
    """Admission of a plan against one pose/grid snapshot (the one that rejected the replacement)."""
    def revalidate(plan):
        if pose is None or grid is None:
            return None, {'accepted': False, 'reason': 'observed_snapshot_unavailable'}
        info = grid.info
        return prepare(plan, pose, (info.origin.position.x, info.origin.position.y), info.resolution,
                       info.width, info.height, grid.data, footprint)
    return revalidate


def _suffix_matches(active_path, admitted_path, join_index, connector_samples):
    """True if the admitted plan's tail is exactly active_path[join_index:]."""
    suffix = admitted_path[connector_samples:]
    return (isinstance(join_index, int) and 0 < join_index < len(active_path)
            and list(suffix) == list(active_path[join_index:]))


def replacement_outcome(new_admitted, *, enabled, active, active_goal_id, destination, action_running,
                        revalidate, still_fresh):
    """Decide what to do with a replacement plan; returns (action, plan or None, diagnostics).

    `revalidate(plan) -> (admitted, admission_diagnostics)` must be the unchanged
    path admission on the snapshot that rejected the replacement; `still_fresh()
    -> bool` re-checks observation freshness after that work. Both are called at
    most once, and only when the replacement was rejected and the option is
    enabled. SEND_REVALIDATED returns the admitted connector+suffix itself, to be
    sent unchanged.
    """
    diagnostics = {'mode': 'on' if enabled else 'off', 'evaluated': False}
    if new_admitted is not None:
        return SEND_NEW, new_admitted, {**diagnostics, 'reason': 'replacement_admitted'}
    if not enabled:
        return CANCEL, None, {**diagnostics, 'reason': DISABLED}
    if active is None:
        return CANCEL, None, {**diagnostics, 'reason': 'no_active_admitted_path'}
    if action_running is not True:
        return CANCEL, None, {**diagnostics, 'reason': 'active_action_not_running'}
    if active_goal_id is None or active.goal_id != active_goal_id:
        return CANCEL, None, {**diagnostics, 'reason': 'action_identity_mismatch'}
    if active.destination != destination:
        return CANCEL, None, {**diagnostics, 'reason': 'destination_changed'}
    admitted, admission = revalidate(active.plan)
    diagnostics.update(evaluated=True, active_goal_id=active.goal_id, active_sequence=active.sequence,
                       admission=admission)
    if admitted is None:
        return CANCEL, None, {**diagnostics, 'reason': 'active_path_not_admissible'}
    join, connector = admission.get('join_index'), admission.get('connector_samples')
    if not isinstance(connector, int) or not _suffix_matches(active.plan['path'], admitted['path'], join, connector):
        return CANCEL, None, {**diagnostics, 'reason': 'revalidated_suffix_mismatch'}
    if still_fresh() is not True:
        return CANCEL, None, {**diagnostics, 'reason': 'observations_not_fresh_after_revalidation'}
    diagnostics.update(selected_plan='revalidated_active_connector_and_suffix', join_index=join,
                       connector_samples=connector, sent_path_points=len(admitted['path']),
                       connector_distance_m=admission.get('connector_distance_m'))
    return SEND_REVALIDATED, admitted, {**diagnostics, 'reason': 'active_path_revalidated'}
