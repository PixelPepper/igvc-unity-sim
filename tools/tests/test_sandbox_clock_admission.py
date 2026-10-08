"""Perception use_sim_time admission before sandbox mission spawn, without installed ROS."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sandbox_session
from sandbox_session import CLOCK_NODES, Supervisor, atomic_json, check_sim_time, classify_sim_time

try:
    # Use the real message shape when ROS is installed; otherwise mirror its fields.
    from rcl_interfaces.msg import ParameterValue
    from rcl_interfaces.srv import GetParameters

    def parameter(kind, flag=False, **fields):
        return ParameterValue(type=kind, bool_value=flag, **fields)

    def response(*values):
        return GetParameters.Response(values=list(values))
except ImportError:
    def parameter(kind, flag=False, **fields):
        return SimpleNamespace(**dict(dict(type=kind, bool_value=flag, integer_value=0,
                                           double_value=0.0, string_value=''), **fields))

    def response(*values):
        return SimpleNamespace(values=list(values))

TRUE = lambda: response(parameter(1, True))


class FakeFuture:
    def __init__(self, result=None, exception=None, done=True):
        self._result, self._exception, self._done = result, exception, done
        self.cancelled = False

    def done(self):
        return self._done

    def result(self):
        return self._result

    def exception(self):
        return self._exception

    def cancel(self):
        self.cancelled = True


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class FakeParameters:
    """Per-node AsyncParameterClient stand-in with configurable behavior."""
    def __init__(self, clock, behaviors):
        self.clock, self.behaviors = clock, behaviors
        self.created, self.waits, self.spins, self.futures = [], [], [], []

    def make_client(self, name):
        behavior = self.behaviors[name]
        if isinstance(behavior, Exception):
            raise behavior
        self.created.append(name)
        fake = self

        class Client:
            def wait_for_services(self, timeout_sec=None):
                fake.waits.append((name, timeout_sec))
                if behavior == 'unavailable':
                    fake.clock.now += timeout_sec
                    return False
                return True

            def get_parameters(self, names):
                assert names == ['use_sim_time']
                if behavior == 'silent':
                    future = FakeFuture(done=False)
                elif isinstance(behavior, FakeFuture):
                    future = behavior
                else:
                    future = FakeFuture(behavior)
                fake.futures.append(future)
                return future
        return Client()

    def spin(self, future, timeout_sec):
        self.spins.append(timeout_sec)
        if not future.done():
            self.clock.now += timeout_sec

    def check(self):
        return check_sim_time(self.make_client, self.spin, monotonic=self.clock)


class ClassificationTests(unittest.TestCase):
    def test_only_single_strict_boolean_true_admits(self):
        self.assertEqual(classify_sim_time(TRUE())['status'], 'true')
        self.assertIs(classify_sim_time(TRUE())['value'], True)
        cases = [(response(parameter(1, False)), 'false'),
                 (response(parameter(0)), 'absent'),
                 (response(parameter(2, True, integer_value=1)), 'wrong_type'),
                 (response(parameter(4, True, string_value='true')), 'wrong_type'),
                 (response(), 'malformed'),
                 (response(parameter(1, True), parameter(1, True)), 'malformed'),
                 (SimpleNamespace(), 'malformed'),
                 (None, 'malformed'),
                 (SimpleNamespace(values=[SimpleNamespace(type=1, bool_value=1)]), 'malformed'),
                 (SimpleNamespace(values=[SimpleNamespace(type=True, bool_value=True)]), 'malformed'),
                 (SimpleNamespace(values=[SimpleNamespace(type='1', bool_value=True)]), 'malformed')]
        for value, status in cases:
            with self.subTest(status=status, value=value):
                observed = classify_sim_time(value)
                self.assertEqual(observed['status'], status)
                self.assertIsNot(observed['value'], True)
                self.assertTrue(observed['error'])


class CheckTests(unittest.TestCase):
    def run_check(self, lane, depth):
        fake = FakeParameters(FakeClock(), {CLOCK_NODES[0]: lane, CLOCK_NODES[1]: depth})
        return fake, fake.check()

    def test_both_true_admits_with_observed_values(self):
        fake, evidence = self.run_check(TRUE(), TRUE())
        self.assertTrue(evidence['admitted'])
        self.assertEqual(evidence['requested_nodes'], list(CLOCK_NODES))
        self.assertEqual([item['node'] for item in evidence['nodes']], list(CLOCK_NODES))
        for item in evidence['nodes']:
            self.assertEqual((item['status'], item['value'], item['type']), ('true', True, 1))
        json.dumps(evidence, allow_nan=False)

    def test_each_failure_category_denies_admission(self):
        cases = {'false': response(parameter(1, False)), 'absent': response(parameter(0)),
                 'wrong_type': response(parameter(4, True, string_value='true')),
                 'malformed': response(), 'service_unavailable': 'unavailable', 'timeout': 'silent',
                 'exception': RuntimeError('graph failure')}
        for status, behavior in cases.items():
            with self.subTest(status=status):
                _, evidence = self.run_check(TRUE(), behavior)
                self.assertFalse(evidence['admitted'])
                self.assertEqual(evidence['nodes'][0]['status'], 'true')
                self.assertEqual(evidence['nodes'][1]['status'], status)
                self.assertIsNone(evidence['nodes'][1]['value'] if status != 'false' else None)
                self.assertTrue(evidence['nodes'][1]['error'])

    def test_response_exception_is_not_success(self):
        _, evidence = self.run_check(FakeFuture(exception=ValueError('bad reply')), TRUE())
        self.assertFalse(evidence['admitted'])
        self.assertEqual(evidence['nodes'][0]['status'], 'exception')
        self.assertIn('bad reply', evidence['nodes'][0]['error'])

    def test_unavailable_discovery_shares_one_bounded_deadline(self):
        fake, evidence = self.run_check('unavailable', 'unavailable')
        self.assertFalse(evidence['admitted'])
        self.assertEqual(fake.waits, [(CLOCK_NODES[0], sandbox_session.CLOCK_ADMISSION_TIMEOUT)])
        self.assertEqual([item['status'] for item in evidence['nodes']], ['service_unavailable', 'timeout'])
        self.assertLessEqual(evidence['elapsed_seconds'], 16)
        self.assertLessEqual(sandbox_session.CLOCK_ADMISSION_TIMEOUT, 16)

    def test_silent_response_is_bounded_and_cancelled(self):
        fake, evidence = self.run_check('silent', TRUE())
        self.assertEqual(evidence['nodes'][0]['status'], 'timeout')
        self.assertTrue(fake.futures[0].cancelled)
        self.assertLessEqual(sum(fake.spins), 16)
        self.assertEqual(evidence['nodes'][1]['status'], 'timeout')
        self.assertLessEqual(evidence['elapsed_seconds'], 16)

    def test_requested_timeout_cannot_exceed_admission_bound(self):
        fake = FakeParameters(FakeClock(), {CLOCK_NODES[0]: 'unavailable', CLOCK_NODES[1]: TRUE()})
        check_sim_time(fake.make_client, fake.spin, timeout=60, monotonic=fake.clock)
        self.assertLessEqual(fake.waits[0][1], sandbox_session.CLOCK_ADMISSION_TIMEOUT)


class SupervisorAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.sessions = self.folder / 'session'; self.sessions.mkdir()
        (self.folder / 'autonomy.json').write_text('{}')
        self.calls = []
        self.ros = Mock()
        self.ros.disable.side_effect = lambda: self.calls.append('disable')
        self.supervisor = Supervisor(self.folder, self.folder / 'autonomy.json', self.ros)
        self.supervisor.nav = Mock(side_effect=self.nav)
        self.nav_stop_error = None
        self.popen = Mock(side_effect=self.spawn)
        self.spawn_provenance = None
        for target, value in [('sandbox_session.session_dir', lambda root: self.sessions),
                              ('sandbox_session.build_profile', lambda settings: ({}, 'baseline.yaml')),
                              ('sandbox_session.mission_argv', lambda *args: ['mission']),
                              ('sandbox_session.subprocess.Popen', self.popen)]:
            patcher = patch(target, value); patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.dict(sys.modules, {'sensor_course': SimpleNamespace(destinations=lambda mission: [0]*6)})
        patcher.start(); self.addCleanup(patcher.stop)

    def nav(self, action, profile=None):
        self.calls.append('nav '+action)
        if action == 'start':
            (self.sessions / 'nav.json').write_text('{"pid": 7}')
        elif self.nav_stop_error:
            raise RuntimeError(self.nav_stop_error)
        else:
            (self.sessions / 'nav.json').unlink()

    def spawn(self, argv, **kwargs):
        self.calls.append('spawn')
        self.spawn_provenance = json.loads((self.supervisor.folder / 'provenance.json').read_text())
        return Mock(pid=4242, poll=Mock(return_value=None))

    def command(self):
        atomic_json(self.folder / 'command.json', {'id': 'go', 'action': 'start', 'settings': {}})
        self.supervisor.process_command(json.loads((self.folder / 'command.json').read_text()))
        return json.loads((self.folder / 'status.json').read_text())

    def checked(self, lane, depth):
        fake = FakeParameters(FakeClock(), {CLOCK_NODES[0]: lane, CLOCK_NODES[1]: depth})
        def verify():
            self.calls.append('verify')
            return fake.check()
        self.ros.verify_sim_time.side_effect = verify

    def assert_denied(self, state):
        self.popen.assert_not_called()
        self.assertIsNone(self.supervisor.child)
        self.assertEqual(state['state'], 'error')
        self.assertFalse(state['editable'])
        self.assertIn('nav stop', self.calls)
        self.assertLess(self.calls.index('verify'), self.calls.index('nav stop'))
        self.ros.gate.assert_not_called()
        evidence = json.loads((self.supervisor.folder / 'clock-admission.json').read_text())
        self.assertFalse(evidence['admitted'])
        self.assertEqual([item['node'] for item in evidence['nodes']], list(CLOCK_NODES))
        provenance = json.loads((self.supervisor.folder / 'provenance.json').read_text())
        self.assertEqual(provenance['clock_configuration'], evidence)
        self.assertNotIn('mission_pid', provenance)
        return evidence

    def test_success_persists_evidence_before_mission_spawn(self):
        self.checked(TRUE(), TRUE())
        state = self.command()
        self.assertEqual(state['state'], 'running')
        self.assertEqual(self.calls[-3:], ['nav start', 'verify', 'spawn'])
        evidence = self.spawn_provenance['clock_configuration']
        self.assertTrue(evidence['admitted'])
        self.assertEqual([(item['node'], item['status'], item['value'], item['type']) for item in evidence['nodes']],
                         [(name, 'true', True, 1) for name in CLOCK_NODES])
        self.assertEqual(json.loads((self.supervisor.folder / 'clock-admission.json').read_text()), evidence)
        final = json.loads((self.supervisor.folder / 'provenance.json').read_text())
        self.assertEqual(final['clock_configuration'], evidence)
        self.assertEqual(final['mission_pid'], 4242)

    def test_each_failure_category_prevents_spawn_and_cleans_navigation(self):
        cases = {'false': response(parameter(1, False)), 'absent': response(parameter(0)),
                 'wrong_type': response(parameter(2, True, integer_value=1)),
                 'malformed': response(parameter(1, True), parameter(1, True)),
                 'service_unavailable': 'unavailable', 'timeout': 'silent',
                 'exception': RuntimeError('graph failure')}
        for status, behavior in cases.items():
            with self.subTest(status=status):
                self.setUp()
                self.checked(behavior, TRUE())
                state = self.command()
                evidence = self.assert_denied(state)
                self.assertEqual(evidence['nodes'][0]['status'], status)
                self.assertIn(status, state['message'])
                self.assertIn('Perception clock admission failed', state['message'])
                self.assertFalse(self.supervisor.nav_owned)
                self.assertFalse((self.sessions / 'nav.json').exists())

    def test_verification_exception_records_failure_without_fabricated_values(self):
        def verify():
            self.calls.append('verify')
            raise ImportError('rclpy.parameter_client unavailable')
        self.ros.verify_sim_time.side_effect = verify
        state = self.command()
        evidence = self.assert_denied(state)
        self.assertIn('rclpy.parameter_client unavailable', evidence['error'])
        self.assertEqual({item['status'] for item in evidence['nodes']}, {'not_observed'})
        self.assertTrue(all(item['value'] is None for item in evidence['nodes']))
        self.assertIn('rclpy.parameter_client unavailable', state['message'])

    def test_inconsistent_admitted_flag_is_not_trusted(self):
        self.checked(TRUE(), response(parameter(1, False)))
        verify = self.ros.verify_sim_time.side_effect
        self.ros.verify_sim_time.side_effect = lambda: dict(verify(), admitted=True)
        self.assert_denied(self.command())

    def test_cleanup_failure_preserves_original_reason(self):
        self.checked(TRUE(), 'unavailable')
        self.nav_stop_error = 'navigation stop refused'
        state = self.command()
        self.popen.assert_not_called()
        self.assertEqual(state['state'], 'error')
        self.assertFalse(state['editable'])
        self.assertIn('Perception clock admission failed', state['message'])
        self.assertIn('service_unavailable', state['message'])
        self.assertIn('cleanup failed', state['message'])
        self.assertIn('navigation stop refused', state['message'])
        self.assertTrue(self.supervisor.failed_cleanup)
        self.assertTrue(self.supervisor.nav_owned)

    def test_evidence_persistence_failure_blocks_admitted_spawn(self):
        self.checked(TRUE(), TRUE())
        original = sandbox_session.atomic_json
        def failing(path, data):
            if path.name == 'clock-admission.json':
                raise PermissionError(13, 'evidence locked')
            return original(path, data)
        with patch('sandbox_session.atomic_json', failing):
            state = self.command()
        self.popen.assert_not_called()
        self.assertEqual(state['state'], 'error')
        self.assertIn('clock evidence not persisted', state['message'])
        self.assertIn('nav stop', self.calls)

    def test_os_error_after_navigation_start_uses_cleanup_path(self):
        self.checked(TRUE(), TRUE())
        self.popen.side_effect = OSError('exec failed')
        state = self.command()
        self.assertEqual(state['state'], 'error')
        self.assertIn('exec failed', state['message'])
        self.assertNotIn('Invalid or missing command', state['message'])
        self.assertIn('nav stop', self.calls)
        self.assertFalse(self.supervisor.nav_owned)


if __name__ == '__main__':
    unittest.main()
