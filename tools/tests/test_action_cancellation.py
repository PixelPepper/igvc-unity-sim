"""Action/result delivery ordering controls for recovery motion handoff."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from action_cancellation import cancel_action_and_wait


class Future:
    def __init__(self, value=None, *, done=False, error=None):
        self.value, self.complete, self.error = value, done, error

    def done(self):
        return self.complete

    def result(self):
        if not self.complete:
            raise AssertionError('Result read before delivery')
        if self.error is not None:
            raise self.error
        return self.value


class Goal:
    def __init__(self, terminal, code=0):
        self.terminal = terminal
        self.cancellation = Future(SimpleNamespace(return_code=code))
        self.cancel_requests = 0

    def get_result_async(self):
        return self.terminal

    def cancel_goal_async(self):
        self.cancel_requests += 1
        return self.cancellation


class CancellationTests(unittest.TestCase):
    def test_already_terminal_reads_and_validates_result_without_cancel_or_wait(self):
        for status in (4, 5, 6):
            with self.subTest(status=status):
                outcome = SimpleNamespace(status=status)
                goal = Goal(Future(outcome, done=True))
                events = []
                def wait(*args, **kwargs):
                    self.fail('Already terminal action must not wait')
                self.assertIs(cancel_action_and_wait(goal, wait, on_diagnostic=events.append), outcome)
                self.assertEqual(goal.cancel_requests, 0)
                self.assertTrue(events[-1]['terminal_confirmed'])

    def test_accepted_cancel_waits_for_delayed_terminal_before_return(self):
        self.check_delayed_result(0, 5)

    def test_nonzero_cancel_response_waits_for_delayed_terminal(self):
        for code in (1, 2, 3):
            for status in (4, 5, 6):
                with self.subTest(code=code, status=status):
                    self.check_delayed_result(code, status)

    def check_delayed_result(self, code, status):
        outcome = SimpleNamespace(status=status)
        goal = Goal(Future(outcome), code)
        calls, events = [], []
        def wait(future, *, timeout):
            calls.append((future, timeout))
            if future is goal.cancellation:
                self.assertFalse(goal.terminal.done())
            else:
                self.assertIs(future, goal.terminal)
                self.assertFalse(events[-1]['terminal_confirmed'])
            future.complete = True
            return future.result()
        self.assertIs(cancel_action_and_wait(goal, wait, timeout=.7, on_diagnostic=events.append), outcome)
        self.assertEqual(calls, [(goal.cancellation, .7), (goal.terminal, .7)])
        response = next(event for event in events if event['phase'] == 'cancel_response')
        self.assertEqual(response['cancel_return_code'], code)
        self.assertTrue(response['terminal_pending_at_cancel_response'])
        self.assertFalse(response['terminal_confirmed'])
        self.assertTrue(events[-1]['terminal_confirmed'])

    def test_result_delivered_during_cancel_response_needs_no_second_wait(self):
        outcome = SimpleNamespace(status=4)
        goal = Goal(Future(outcome), 3)
        calls = []
        def wait(future, *, timeout):
            calls.append(future)
            goal.terminal.complete = future.complete = True
            return future.result()
        self.assertIs(cancel_action_and_wait(goal, wait), outcome)
        self.assertEqual(calls, [goal.cancellation])

    def test_still_active_goal_cannot_authorize_recovery_after_cancel_response(self):
        for code in (0, 1, 2, 3):
            with self.subTest(code=code):
                goal = Goal(Future(SimpleNamespace(status=5)), code)
                failure = RuntimeError('caller terminal timeout')
                events = []
                def wait(future, *, timeout):
                    self.assertEqual(timeout, 1.25)
                    if future is goal.cancellation:
                        future.complete = True
                        return future.result()
                    raise failure
                with self.assertRaises(RuntimeError) as raised:
                    cancel_action_and_wait(goal, wait, timeout=1.25, on_diagnostic=events.append)
                self.assertIs(raised.exception, failure)
                self.assertFalse(goal.terminal.done())
                self.assertFalse(any(event['terminal_confirmed'] for event in events))
                self.assertEqual(events[-1]['cancel_return_code'], code)

    def test_cancel_wait_exception_propagates_without_retry(self):
        goal = Goal(Future(SimpleNamespace(status=5)))
        failure = RuntimeError('caller cancel timeout')
        calls = []
        def wait(future, *, timeout):
            calls.append(future)
            raise failure
        with self.assertRaises(RuntimeError) as raised:
            cancel_action_and_wait(goal, wait)
        self.assertIs(raised.exception, failure)
        self.assertEqual(calls, [goal.cancellation])
        self.assertEqual(goal.cancel_requests, 1)

    def test_completed_future_exception_and_invalid_terminal_fail_closed(self):
        failure = ValueError('result transport failure')
        goal = Goal(Future(done=True, error=failure))
        with self.assertRaises(ValueError) as raised:
            cancel_action_and_wait(goal, lambda *args, **kwargs: self.fail('Unexpected wait'))
        self.assertIs(raised.exception, failure)
        for outcome in (None, SimpleNamespace(), SimpleNamespace(status=True),
                        SimpleNamespace(status='5'), SimpleNamespace(status=0),
                        SimpleNamespace(status=1), SimpleNamespace(status=2),
                        SimpleNamespace(status=3), SimpleNamespace(status=7)):
            with self.subTest(outcome=outcome):
                goal = Goal(Future(outcome, done=True))
                with self.assertRaisesRegex(RuntimeError, 'not terminal'):
                    cancel_action_and_wait(goal, lambda *args, **kwargs: self.fail('Unexpected wait'))

    def test_wait_return_cannot_substitute_for_actual_future_completion(self):
        goal = Goal(Future(SimpleNamespace(status=5)))
        def wait(future, *, timeout):
            if future is goal.cancellation:
                future.complete = True
            return future.value
        with self.assertRaisesRegex(RuntimeError, 'not complete'):
            cancel_action_and_wait(goal, wait)

    def test_invalid_cancel_response_and_timeout_fail_closed(self):
        for code in (None, True, '0'):
            with self.subTest(code=code):
                goal = Goal(Future(SimpleNamespace(status=5)), code)
                def wait(future, *, timeout):
                    future.complete = True
                    return future.result()
                with self.assertRaisesRegex(RuntimeError, 'Invalid cancellation response'):
                    cancel_action_and_wait(goal, wait)
                self.assertFalse(goal.terminal.done())
        for timeout in (0, -1, float('nan'), float('inf'), True, None):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                cancel_action_and_wait(Goal(Future()), lambda *args, **kwargs: None, timeout=timeout)


if __name__ == '__main__':
    unittest.main()
