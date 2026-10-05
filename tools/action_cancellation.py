"""Confirm action termination before handing motion ownership to recovery.

No ROS dependency: the caller supplies a goal handle and an executor-aware
``wait(future, timeout=...)`` callback. A cancellation response is not a terminal
result: even a rejected/unknown/already-terminated cancellation can race result
delivery. Only SUCCEEDED, CANCELED or ABORTED results permit this helper to return.
"""
import math


TERMINAL_STATUSES = frozenset((4, 5, 6))


def cancel_action_and_wait(active, wait, *, timeout=5., on_diagnostic=None):
    """Cancel if needed, then return the confirmed terminal result envelope.

    Each wait receives the caller's timeout unchanged. At most two waits occur
    (cancel response, terminal result), so the total wait bound is twice timeout.
    Wait/transport/future/diagnostic exceptions propagate without a retry. This
    confirms action termination, not zero measured robot velocity.
    """
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('Positive finite action cancellation timeout required')

    terminal = active.get_result_async()
    details = {'cancel_return_code': None, 'already_terminal': terminal.done(),
               'terminal_status': None, 'terminal_confirmed': False,
               'wait_timeout_s': timeout}

    def emit(phase):
        if on_diagnostic is not None:
            on_diagnostic({**details, 'phase': phase})

    if not details['already_terminal']:
        cancellation = active.cancel_goal_async()
        emit('cancel_requested')
        response = wait(cancellation, timeout=timeout)
        if not cancellation.done():
            raise RuntimeError('Cancellation response is not complete; recovery withheld')
        code = getattr(response, 'return_code', None)
        if isinstance(code, bool) or not isinstance(code, int):
            raise RuntimeError('Invalid cancellation response; recovery withheld')
        details.update(cancel_return_code=code,
                       terminal_pending_at_cancel_response=not terminal.done())
        emit('cancel_response')

    # A nonzero response is not sufficient evidence of an active goal. Await the
    # authoritative result, within the same caller-specified bounded timeout.
    if not terminal.done():
        wait(terminal, timeout=timeout)
    if not terminal.done():
        raise RuntimeError('Action terminal result is not complete; recovery withheld')
    outcome = terminal.result()
    status = getattr(outcome, 'status', None)
    details['terminal_status'] = status
    if (isinstance(status, bool) or not isinstance(status, int)
            or status not in TERMINAL_STATUSES):
        emit('invalid_terminal_result')
        raise RuntimeError('Action result is not terminal; recovery withheld')
    details['terminal_confirmed'] = True
    emit('terminal_confirmed')
    return outcome
