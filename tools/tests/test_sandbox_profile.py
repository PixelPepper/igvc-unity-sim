"""Offline sandbox boundary, routing and shutdown tests."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox_profile import DEFAULTS, LIMITS, build_profile, mission_argv, validate_settings
from sandbox_session import Supervisor, atomic_json, parse_command, stop_child, main


class SandboxTests(unittest.TestCase):
    def test_atomic_write_retries_transient_sharing_denial(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'status.json'
            atomic_json(path, {'state': 'idle'})
            import os
            original_replace = os.replace
            attempts = []
            def locked_then_replace(source, target):
                attempts.append(target)
                # Readers continue seeing complete previous JSON until replace.
                self.assertEqual(json.loads(path.read_text()), {'state': 'idle'})
                if len(attempts) <= 2:
                    raise PermissionError(13, 'sharing violation')
                return original_replace(source, target)
            with patch('sandbox_session.os.replace', side_effect=locked_then_replace), \
                 patch('sandbox_session.time.sleep') as pause:
                atomic_json(path, {'state': 'running'})
            self.assertEqual(len(attempts), 3)
            self.assertEqual(pause.call_count, 2)
            self.assertEqual(json.loads(path.read_text()), {'state': 'running'})

    def test_atomic_write_fails_after_bounded_persistent_sharing_denial(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'status.json'
            atomic_json(path, {'state': 'idle'})
            with patch('sandbox_session.os.replace', side_effect=PermissionError(13, 'locked')) as replace, \
                 patch('sandbox_session.time.sleep') as pause:
                with self.assertRaises(PermissionError):
                    atomic_json(path, {'state': 'running'})
            self.assertEqual(replace.call_count, 41)
            self.assertEqual(pause.call_count, 40)
            self.assertTrue(all(call.args == (.025,) for call in pause.call_args_list))
            self.assertEqual(json.loads(path.read_text()), {'state': 'idle'})

    def test_profile_effects_and_independent_execution(self):
        for controller in ('rpp', 'mppi'):
            profile, baseline = build_profile(dict(controller=controller, execution='nav2-goal', speed_mps=.8, inflation_m=.7, lookahead_m=.9))
            follow = profile['controller_server']['ros__parameters']['FollowPath']
            self.assertEqual(follow['desired_linear_vel' if controller == 'rpp' else 'vx_max'], .8)
            if controller == 'rpp':
                self.assertEqual(follow['lookahead_dist'], .9)
            for name in ('local_costmap', 'global_costmap'):
                self.assertEqual(profile[name][name]['ros__parameters']['inflation_layer']['inflation_radius'], .7)
            self.assertEqual(profile['planner_server']['ros__parameters']['GridBased']['max_planning_time'], 2.)

    def test_limits_and_unknown_fields(self):
        for key, (low, high) in LIMITS.items():
            for value in (low-.01, high+.01, float('nan'), float('inf'), True, '1'):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_settings({key: value})
            validate_settings({key: low}); validate_settings({key: high})
        with self.assertRaises(ValueError):
            validate_settings({'route': 'forbidden'})
        for value in ({}, {'id': 'x', 'action': 'shell'}, {'id': 'x', 'action': 'start', 'extra': 2}):
            with self.assertRaises(ValueError):
                parse_command(value)

    def test_routing_argv_has_only_sanitized_mission(self):
        argv = mission_argv('python', Path('autonomy.json'), Path('run'), dict(execution='nav2-goal', planning_budget_s=1.2, clearance_weight=4))
        self.assertEqual(argv[argv.index('--mission')+1], 'autonomy.json')
        self.assertEqual(argv[argv.index('--path-execution')+1], 'nav2-goal')
        self.assertEqual(argv[argv.index('--planning-budget')+1], '1.2')
        self.assertNotIn('--course', argv)
        self.assertNotIn('--route', argv)

    def test_stale_and_repeated_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            atomic_json(folder / 'command.json', {'id': 'stale', 'action': 'start'})
            supervisor = Supervisor(folder, folder / 'autonomy.json', Mock())
            supervisor.start = Mock()
            with patch('sandbox_session.ROOT', folder):
                supervisor.startup(); supervisor.tick()
            supervisor.start.assert_not_called()
            atomic_json(folder / 'command.json', {'id': 'fresh', 'action': 'start'})
            supervisor.tick(); supervisor.tick()
            supervisor.start.assert_called_once()
            self.assertIn('heartbeat_utc', json.loads((folder / 'status.json').read_text()))

    def test_cleanup_failure_cannot_advertise_idle(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            ros = Mock(); ros.disable.side_effect = RuntimeError('no gate response')
            supervisor = Supervisor(folder, folder / 'autonomy.json', ros)
            supervisor.nav_owned = True; supervisor.nav = Mock()
            atomic_json(folder / 'command.json', {'id': 'stop', 'action': 'stop'})
            supervisor.tick()
            state = json.loads((folder / 'status.json').read_text())
            self.assertEqual(state['state'], 'error')
            self.assertFalse(state['editable'])
            self.assertTrue(supervisor.nav_owned)
            supervisor.nav.assert_called_with('stop')

    def test_child_exit_confirmation(self):
        child = Mock(pid=123)
        child.poll.return_value = None
        child.wait.side_effect = __import__('subprocess').TimeoutExpired('mission', 1)
        with patch('sandbox_session.os.killpg'), patch('sandbox_session.group_running', return_value=False):
            with self.assertRaises(RuntimeError):
                stop_child(child)
        child.poll.return_value = 0
        with patch('sandbox_session.group_running', return_value=False):
            stop_child(child)

    def test_stop_ignores_invalid_settings(self):
        command_id, action, settings = parse_command({'id': 'stop-now', 'action': 'stop',
                                                      'settings': {'speed_mps': float('nan')}})
        self.assertEqual(action, 'stop')
        self.assertEqual(settings, DEFAULTS)

    def test_missing_start_dependency_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            supervisor = Supervisor(folder, folder / 'autonomy.json', Mock())
            supervisor.start = Mock(side_effect=FileNotFoundError('missing mission'))
            atomic_json(folder / 'command.json', {'id': 'start', 'action': 'start'})
            supervisor.tick()
            state = json.loads((folder / 'status.json').read_text())
            self.assertEqual(state['state'], 'error')
            self.assertFalse(state['editable'])
            self.assertIn('missing mission', state['message'])

    def test_polite_stop_signals_coordinator_before_workers(self):
        child = Mock(pid=123)
        child.poll.side_effect = [None, None, 0]
        with patch('sandbox_session.os.killpg') as group_signal, \
             patch('sandbox_session.group_running', return_value=False):
            stop_child(child)
        child.send_signal.assert_called_once_with(__import__('signal').SIGINT)
        group_signal.assert_not_called()

    def test_missing_command_preserves_idle(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            supervisor = Supervisor(folder, folder / 'autonomy.json', Mock())
            with patch('sandbox_session.ROOT', folder):
                supervisor.startup(); supervisor.tick()
            state = json.loads((folder / 'status.json').read_text())
            self.assertEqual(state['state'], 'idle')
            self.assertTrue(state['editable'])
            (folder / 'command.json').write_text('{broken')
            supervisor.tick()
            self.assertEqual(json.loads((folder / 'status.json').read_text())['state'], 'error')

    def test_independent_heartbeat_during_blocking_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            supervisor = Supervisor(folder, folder / 'autonomy.json', Mock())
            supervisor.status('starting', 'Blocked service')
            before = json.loads((folder / 'status.json').read_text())['heartbeat_utc']
            supervisor.start_heartbeat()
            try:
                # Main thread performs no tick while a ROS call would block.
                time.sleep(.7)
                state = json.loads((folder / 'status.json').read_text())
                self.assertNotEqual(before, state['heartbeat_utc'])
                self.assertEqual(state['state'], 'starting')
                self.assertFalse(state['editable'])
            finally:
                supervisor.stop_heartbeat()
            self.assertFalse(supervisor.heartbeat_thread.is_alive())

    @unittest.skipIf(sys.platform == 'win32', 'Supervisor uses Linux session locks')
    def test_shutdown_file_runs_cleanup_without_processing_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'shutdown.request').touch()
            session = Mock()
            with patch('sandbox_session.ROOT', folder), patch('sandbox_session.RosControl') as control, \
                 patch('sandbox_session.Supervisor', return_value=session), \
                 patch('sandbox_session.signal.signal'), \
                 patch.object(sys, 'argv', ['sandbox_session.py', '--directory', str(folder),
                                          '--mission', str(folder / 'autonomy.json')]):
                main()
            session.tick.assert_not_called()
            session.cleanup.assert_called_once()
            session.stop_heartbeat.assert_called_once()
            control.return_value.close.assert_called_once()


class EscapeSettingTests(unittest.TestCase):
    def test_legacy_keeps_baseline_mission_arguments(self):
        argv = mission_argv('python3', Path('m.json'), Path('run'), {})
        self.assertNotIn('--escape', argv)
        self.assertEqual(validate_settings({})['escape'], 'legacy')

    def test_retrace_is_forwarded_and_unknown_rejected(self):
        argv = mission_argv('python3', Path('m.json'), Path('run'), dict(escape='retrace'))
        self.assertEqual(argv[argv.index('--escape')+1], 'retrace')
        with self.assertRaises(ValueError):
            validate_settings(dict(escape='teleport'))


class LearnedScorerSettingTests(unittest.TestCase):
    def test_zero_weights_keep_baseline_arguments(self):
        argv = mission_argv('python3', Path('m.json'), Path('run'), {})
        self.assertFalse(any(a.endswith('-scorer') or a.endswith('-weight') and 'clearance' not in a for a in argv))

    def test_positive_weight_passes_current_model(self):
        argv = mission_argv('python3', Path('m.json'), Path('run'), dict(route_weight=1.))
        model = argv[argv.index('--route-scorer')+1]
        self.assertTrue(model.endswith('artifacts/learning/models/current/route_scorer.json'))
        self.assertEqual(argv[argv.index('--route-weight')+1], '1.0')
        self.assertNotIn('--corridor-scorer', argv)
        with self.assertRaises(ValueError):
            validate_settings(dict(corridor_weight=11.))


if __name__ == '__main__':
    unittest.main()
