"""Agent message listener: durable cursor delivery, legacy mode, validation and locking."""

import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'agents'))
import wait_message  # noqa: E402

SCRIPT = TOOLS / 'agents' / 'wait_message.py'
HEADER = '---\nid: T-0001\n---\n\n## Log\n'


def entry(stamp, recipient, kind='DISPATCH', body='body'):
    return f'\n### {stamp} · gpt-6-astra → {recipient} · {kind}\n\n{body}\n'


class Stop(Exception):
    """Raised by the fake sleep to end a watch loop."""


class FakeClock:
    def __init__(self, hooks=()):
        self.now = 0.0
        self.sleeps = []
        self.hooks = list(hooks)

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds
        if self.hooks:
            self.hooks.pop(0)()
        else:
            raise Stop


class ListenerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.tasks = root / 'tasks'
        self.tasks.mkdir()
        self.cursor = root / 'state' / 'opus.json'
        self.cursor.parent.mkdir()
        self.log = self.tasks / 'T-0001-example.md'
        self.log.write_text(HEADER, encoding='utf-8')

    def post(self, *entries, log=None):
        log = log or self.log
        with open(log, 'a', encoding='utf-8') as handle:
            handle.write(''.join(entries))

    def run_main(self, *extra, to='claude-opus-5-5', clock=None, out=None):
        clock = clock or FakeClock()
        out = out if out is not None else io.StringIO()
        argv = ['--to', to, '--tasks', str(self.tasks), '--poll', '1', '--timeout', '3', *extra]
        code = wait_message.main(argv, out=out, clock=clock, sleep=clock.sleep)
        return code, out.getvalue() if isinstance(out, io.StringIO) else None, clock

    def headings(self, text):
        return [line for line in text.splitlines() if line.startswith('[')]

    def state(self):
        return json.loads(self.cursor.read_text(encoding='utf-8'))


class DurableDeliveryTest(ListenerTest):
    def test_missing_cursor_replays_existing_addressed_messages_immediately(self):
        self.post(entry('t1', 'claude-opus-5-5'), entry('t2', 'gpt-6.1-sol'), entry('t3', 'all'))
        code, text, clock = self.run_main('--cursor', str(self.cursor))
        self.assertEqual(code, 0)
        self.assertEqual(clock.sleeps, [])
        self.assertEqual(len(self.headings(text)), 2)
        self.assertIn('t1', text)
        self.assertIn('t3', text)
        self.assertNotIn('t2', text)
        state = self.state()
        self.assertEqual(state['version'], 1)
        self.assertEqual(state['recipient'], 'claude-opus-5-5')
        self.assertEqual(state['tasks'], str(self.tasks.resolve()))
        self.assertEqual(len(state['delivered']), 2)

    def test_message_posted_while_offline_survives_restart(self):
        self.post(entry('t1', 'claude-opus-5-5'))
        self.assertEqual(self.run_main('--cursor', str(self.cursor))[0], 0)
        self.post(entry('t2', 'claude-opus-5-5', body='offline dispatch'))
        code, text, clock = self.run_main('--cursor', str(self.cursor))
        self.assertEqual(code, 0)
        self.assertEqual(clock.sleeps, [])
        self.assertIn('offline dispatch', text)
        self.assertNotIn('t1', text)

    def test_existing_cursor_without_new_messages_times_out(self):
        self.post(entry('t1', 'claude-opus-5-5'))
        self.run_main('--cursor', str(self.cursor))
        code, text, clock = self.run_main('--cursor', str(self.cursor),
                                          clock=FakeClock([lambda: None] * 5))
        self.assertEqual(code, 2)
        self.assertEqual(text, '')
        self.assertEqual(sum(clock.sleeps), 3)

    def test_first_run_with_no_messages_does_not_lose_later_dispatch(self):
        code, _, _ = self.run_main('--cursor', str(self.cursor),
                                   clock=FakeClock([lambda: None] * 5))
        self.assertEqual(code, 2)
        self.assertEqual(self.state()['delivered'], [])
        self.post(entry('t1', 'claude-opus-5-5'))
        code, text, _ = self.run_main('--cursor', str(self.cursor))
        self.assertEqual(code, 0)
        self.assertIn('t1', text)

    def test_watch_prints_each_new_message_once_and_persists(self):
        self.post(entry('t1', 'claude-opus-5-5'))
        clock = FakeClock([lambda: self.post(entry('t2', 'all')),
                           lambda: None,
                           lambda: self.post(entry('t3', 'claude-opus-5-5'),
                                             entry('t4', 'user'))])
        with self.assertRaises(Stop):
            self.run_main('--cursor', str(self.cursor), '--watch', clock=clock)
        delivered = {tuple(item) for item in self.state()['delivered']}
        self.assertEqual({h.split(' · ')[0][4:] for _, h in delivered}, {'t1', 't2', 't3'})
        out = io.StringIO()
        clock = FakeClock([lambda: None])
        with self.assertRaises(Stop):
            self.run_main('--cursor', str(self.cursor), '--watch', clock=clock, out=out)
        self.assertEqual(out.getvalue(), '')

    def test_watch_output_lists_messages_in_order(self):
        clock = FakeClock([lambda: self.post(entry('t1', 'claude-opus-5-5'))])
        out = io.StringIO()
        with self.assertRaises(Stop):
            self.run_main('--cursor', str(self.cursor), '--watch', clock=clock, out=out)
        self.assertEqual(len(self.headings(out.getvalue())), 1)

    def test_recipient_filter_uses_separate_cursors(self):
        self.post(entry('t1', 'claude-opus-5-5'), entry('t2', 'gpt-6.1-sol'))
        sol_cursor = self.cursor.with_name('sol.json')
        _, opus, _ = self.run_main('--cursor', str(self.cursor))
        _, sol, _ = self.run_main('--cursor', str(sol_cursor), to='gpt-6.1-sol')
        self.assertIn('t1', opus)
        self.assertNotIn('t2', opus)
        self.assertIn('t2', sol)
        self.assertNotIn('t1', sol)


class CursorValidationTest(ListenerTest):
    def assert_error_keeps_cursor(self, content, *, to='claude-opus-5-5'):
        self.post(entry('t1', 'claude-opus-5-5'))
        self.cursor.write_text(content, encoding='utf-8')
        err = io.StringIO()
        with mock.patch('sys.stderr', err):
            code, text, _ = self.run_main('--cursor', str(self.cursor), to=to)
        self.assertEqual(code, 1)
        self.assertEqual(text, '')
        self.assertIn('error:', err.getvalue())
        self.assertEqual(self.cursor.read_text(encoding='utf-8'), content)

    def good_state(self, **changes):
        state = {'version': 1, 'recipient': 'claude-opus-5-5',
                 'tasks': str(self.tasks.resolve()), 'delivered': []}
        state.update(changes)
        return json.dumps(state)

    def test_corrupt_json_fails_without_reset(self):
        self.assert_error_keeps_cursor('{not json')

    def test_wrong_version_extra_key_and_bad_ids_fail(self):
        for content in (self.good_state(version=2), self.good_state(version=True),
                        self.good_state(extra=1), self.good_state(delivered=[['a']]),
                        self.good_state(delivered=[['a', 3]]), json.dumps([])):
            with self.subTest(content=content):
                self.assert_error_keeps_cursor(content)

    def test_wrong_recipient_fails(self):
        self.assert_error_keeps_cursor(self.good_state(recipient='gpt-6.1-sol'))

    def test_wrong_task_directory_fails(self):
        self.assert_error_keeps_cursor(self.good_state(tasks=str(Path(self.temp.name))))

    def test_nonfinite_or_nonpositive_timing_rejected(self):
        for flag, value in (('--poll', '0'), ('--poll', '-1'), ('--poll', 'nan'),
                            ('--timeout', 'inf'), ('--timeout', '0')):
            with self.subTest(flag=flag, value=value), mock.patch('sys.stderr', io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    wait_message.main(['--to', 'x', flag, value])
                self.assertEqual(raised.exception.code, 2)


class FailureRecoveryTest(ListenerTest):
    def test_output_failure_does_not_mark_messages_consumed(self):
        self.post(entry('t1', 'claude-opus-5-5'))

        class Broken(io.StringIO):
            def write(self, text):
                raise BrokenPipeError('closed pipe')

        with mock.patch('sys.stderr', io.StringIO()):
            code, _, _ = self.run_main('--cursor', str(self.cursor), out=Broken())
        self.assertEqual(code, 1)
        self.assertEqual(self.state()['delivered'], [])
        code, text, _ = self.run_main('--cursor', str(self.cursor))
        self.assertEqual(code, 0)
        self.assertIn('t1', text)

    def test_interrupted_save_keeps_previous_cursor_and_redelivers(self):
        self.post(entry('t1', 'claude-opus-5-5'))
        self.run_main('--cursor', str(self.cursor))
        before = self.cursor.read_text(encoding='utf-8')
        self.post(entry('t2', 'claude-opus-5-5'))
        with mock.patch.object(wait_message.os, 'replace', side_effect=OSError('disk full')), \
                mock.patch('sys.stderr', io.StringIO()) as err:
            code, text, _ = self.run_main('--cursor', str(self.cursor))
        self.assertEqual(code, 1)
        self.assertIn('t2', text)  # printed, then save failed: at-least-once
        self.assertIn('delivered again', err.getvalue())
        self.assertEqual(self.cursor.read_text(encoding='utf-8'), before)
        self.assertEqual(sorted(p.name for p in self.cursor.parent.iterdir()),
                         ['opus.json', 'opus.json.lock'])
        code, text, _ = self.run_main('--cursor', str(self.cursor))
        self.assertEqual(code, 0)
        self.assertIn('t2', text)


class LockTest(ListenerTest):
    def test_lock_contention_fails_and_release_allows_next_consumer(self):
        self.post(entry('t1', 'claude-opus-5-5'))
        lock = wait_message.CursorLock(self.cursor)
        with lock:
            with mock.patch('sys.stderr', io.StringIO()) as err:
                code, text, _ = self.run_main('--cursor', str(self.cursor))
            self.assertEqual(code, 1)
            self.assertEqual(text, '')
            self.assertIn('locked', err.getvalue())
            self.assertFalse(self.cursor.exists())
        code, text, _ = self.run_main('--cursor', str(self.cursor))
        self.assertEqual(code, 0)
        self.assertIn('t1', text)
        self.assertTrue(Path(str(self.cursor) + '.lock').exists())

    def test_lock_contention_across_processes(self):
        holder = subprocess.Popen(
            [sys.executable, '-c',
             'import sys; sys.path.insert(0, sys.argv[1]); import wait_message\n'
             'with wait_message.CursorLock(sys.argv[2]):\n'
             '    print("held", flush=True); sys.stdin.readline()',
             str(TOOLS / 'agents'), str(self.cursor)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), 'held')
            busy = self.subprocess_run()
            self.assertEqual(busy.returncode, 1)
            self.assertIn('locked', busy.stderr)
        finally:
            holder.communicate('\n', timeout=30)
        self.post(entry('t1', 'claude-opus-5-5'))
        done = self.subprocess_run()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('t1', done.stdout)

    def subprocess_run(self):
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        return subprocess.run(
            [sys.executable, str(SCRIPT), '--to', 'claude-opus-5-5', '--tasks', str(self.tasks),
             '--cursor', str(self.cursor), '--timeout', '1', '--poll', '0.1'],
            capture_output=True, text=True, encoding='utf-8', env=env, timeout=60)


class LegacyModeTest(ListenerTest):
    def test_no_cursor_ignores_startup_messages_and_prints_new_ones(self):
        self.post(entry('t1', 'claude-opus-5-5'))
        clock = FakeClock([lambda: self.post(entry('t2', 'all'))])
        code, text, _ = self.run_main(clock=clock)
        self.assertEqual(code, 0)
        self.assertNotIn('t1', text)
        self.assertIn('t2', text)
        self.assertEqual(sorted(p.name for p in self.cursor.parent.iterdir()), [])

    def test_no_cursor_times_out_with_exit_two(self):
        self.post(entry('t1', 'claude-opus-5-5'))
        with mock.patch('sys.stderr', io.StringIO()) as err:
            code, text, _ = self.run_main(clock=FakeClock([lambda: None] * 5))
        self.assertEqual(code, 2)
        self.assertEqual(text, '')
        self.assertIn('timeout', err.getvalue())


if __name__ == '__main__':
    unittest.main()
