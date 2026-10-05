"""Opt-in continuity when a replacement path is rejected (checked-path mode).

Default behavior is unchanged: a rejected replacement cancels the active
FollowPath action. With the option enabled, exactly one extra check is made:
the path the *running* action is following is re-admitted from the latest
pose against the latest observed costmap with the same `prepare_controller_plan`
used for every new path (unchanged cross-track, heading, turn-radius, connector
limits, full-footprint connector and suffix sweeps, unknown cells blocking).
Only if that succeeds, for the same action identity and destination, and the
observations are still fresh afterwards, is the running action kept. It is
not resubmitted and not modified. Anything else fails closed to the existing
cancellation. Nothing here talks to ROS.
"""

DISABLED, SEND_NEW, RETAIN, CANCEL = 'disabled', 'send_new', 'retain_active', 'cancel'


class ActivePathRecord:
    """The admitted plan that was actually sent and accepted, with its identity."""

    __slots__ = ('plan', 'goal_id', 'destination', 'sequence', 'target')

    def __init__(self, plan, goal_id, destination, sequence, target):
        self.plan, self.goal_id, self.destination = plan, goal_id, destination
        self.sequence, self.target = sequence, target


def replacement_outcome(new_admitted, *, enabled, active, active_goal_id, destination, action_running,
                        revalidate, still_fresh):
    """Decide what to do with a replacement plan; returns (action, diagnostics).

    `revalidate(plan) -> (admitted, admission_diagnostics)` must be the unchanged
    path admission at the latest pose/grid; `still_fresh() -> bool` re-checks
    observation freshness after that work. Both are called at most once, and only
    when the replacement was rejected and the option is enabled.
    """
    if new_admitted is not None:
        return SEND_NEW, {'mode': 'on' if enabled else 'off', 'evaluated': False, 'reason': 'replacement_admitted'}
    diagnostics = {'mode': 'on' if enabled else 'off', 'evaluated': False}
    if not enabled:
        return CANCEL, {**diagnostics, 'reason': DISABLED}
    if active is None:
        return CANCEL, {**diagnostics, 'reason': 'no_active_admitted_path'}
    if action_running is not True:
        return CANCEL, {**diagnostics, 'reason': 'active_action_not_running'}
    if active_goal_id is None or active.goal_id != active_goal_id:
        return CANCEL, {**diagnostics, 'reason': 'action_identity_mismatch'}
    if active.destination != destination:
        return CANCEL, {**diagnostics, 'reason': 'destination_changed'}
    admitted, admission = revalidate(active.plan)
    diagnostics.update(evaluated=True, active_goal_id=active.goal_id, active_sequence=active.sequence,
                       admission=admission)
    if admitted is None:
        return CANCEL, {**diagnostics, 'reason': 'active_path_not_admissible'}
    if still_fresh() is not True:
        return CANCEL, {**diagnostics, 'reason': 'observations_not_fresh_after_revalidation'}
    return RETAIN, {**diagnostics, 'reason': 'active_path_revalidated'}
