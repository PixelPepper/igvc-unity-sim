"""Linux launcher behavior without invoking Docker, Unity or signalling real processes."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import linux_session as launcher


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        with patch.object(launcher.os, 'getuid', return_value=1000, create=True), \
             patch.object(launcher.os, 'getgid', return_value=1000, create=True):
            self.session = launcher.Session(self.temp.name)
        self.session.directory.mkdir(parents=True)

    def state(self):
        return dict(pid=4321, executable=str(self.session.player), root=str(self.session.root),
                    boot_id='boot', start_ticks='22', seed=2027, difficulty='normal')

    def container(self, root=None):
        root = self.session.root if root is None else Path(root)
        return {'Config': {'Labels': {'com.docker.compose.project.working_dir': str(root)}},
                'Mounts': [{'Source': str(root / 'artifacts'), 'Destination': '/opt/igvc/artifacts'}]}

    def test_cli_preserves_command_arguments(self):
        args = launcher.parser().parse_args(['run', 'python3', '-c', 'print("a b")'])
        self.assertEqual(args.command, ['python3', '-c', 'print("a b")'])
        args = launcher.parser().parse_args(['start', '--seed', '4', '--difficulty', 'hard'])
        self.assertEqual((args.seed, args.difficulty), (4, 'hard'))

    def test_other_checkout_rejected_before_any_compose_action(self):
        self.session.containers = Mock(return_value=[self.container(self.session.root / 'other')])
        self.session.compose = Mock()
        with self.assertRaisesRegex(launcher.SessionError, 'another checkout'):
            self.session.exec_ros('echo', 'hello')
        self.session.compose.assert_not_called()

    def test_mount_mismatch_rejected_even_with_matching_label(self):
        container = self.container()
        container['Mounts'][0]['Source'] = '/other/artifacts'
        self.session.containers = Mock(return_value=[container])
        with self.assertRaises(launcher.SessionError):
            self.session.owned_containers()

    def test_own_container_accepted(self):
        self.session.containers = Mock(return_value=[self.container()])
        self.assertEqual(len(self.session.owned_containers()), 1)

    def test_reused_pid_is_never_signalled(self):
        state = self.state()
        self.session.state_path.write_text(json.dumps(state))
        identity = {k: state[k] for k in ('pid', 'executable', 'boot_id', 'start_ticks')}
        identity['start_ticks'] = '99'
        with patch.object(launcher, 'process_identity', return_value=identity), \
             patch.object(launcher.os, 'pidfd_open', create=True) as pidfd:
            self.session.stop_player()
        pidfd.assert_not_called()
        self.assertFalse(self.session.state_path.exists())

    def test_different_executable_is_never_owned(self):
        state = self.state()
        identity = {k: state[k] for k in ('pid', 'executable', 'boot_id', 'start_ticks')}
        identity['executable'] = '/usr/bin/unrelated'
        with patch.object(launcher, 'process_identity', return_value=identity):
            self.assertFalse(self.session.owns_player(state))

    def test_ownership_rechecked_after_pidfd_open(self):
        self.session.state_path.write_text(json.dumps(self.state()))
        with patch.object(self.session, 'owns_player', side_effect=[True, False]), \
             patch.object(launcher.os, 'pidfd_open', return_value=999, create=True), \
             patch.object(launcher.os, 'close') as close, \
             patch.object(launcher.signal, 'pidfd_send_signal', create=True) as send:
            self.session.stop_player()
        send.assert_not_called()
        close.assert_called_once_with(999)

    def test_failed_start_removes_only_own_container(self):
        self.session.player.parent.mkdir(parents=True)
        self.session.player.touch()
        self.session.graphical = Mock()
        self.session.owned_containers = Mock(return_value=[])
        self.session.compose = Mock(side_effect=[None, launcher.SessionError('generation failed'), None])
        args = argparse.Namespace(seed=2027, difficulty='normal')
        with patch.object(launcher.os, 'access', return_value=True), \
             patch.object(launcher.socket, 'socket'):
            with self.assertRaisesRegex(launcher.SessionError, 'generation failed'):
                self.session.start(args)
        self.assertEqual(self.session.compose.call_args.args, ('down',))
        self.assertFalse(self.session.state_path.exists())

    def test_failed_start_does_not_remove_foreign_container(self):
        self.session.player.parent.mkdir(parents=True)
        self.session.player.touch()
        self.session.graphical = Mock()
        self.session.owned_containers = Mock(side_effect=[[], launcher.SessionError('another checkout')])
        self.session.compose = Mock(side_effect=launcher.SessionError('up failed'))
        with patch.object(launcher.os, 'access', return_value=True), \
             patch.object(launcher.socket, 'socket'), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(launcher.SessionError, 'up failed'):
                self.session.start(argparse.Namespace(seed=2027, difficulty='normal'))
        self.assertEqual(self.session.compose.call_count, 1)

    def test_difficulty_mismatch_does_not_run_motion(self):
        folder = self.session.root / 'artifacts/courses/seed-2027'
        folder.mkdir(parents=True)
        (folder / 'course.json').write_text('{"seed":2027,"difficulty":"easy"}')
        with self.assertRaisesRegex(launcher.SessionError, 'does not match'):
            self.session.validate_course(argparse.Namespace(action='course', seed=2027, difficulty='hard'))

    def test_stopped_status_does_not_exec_ros(self):
        self.session.prerequisites = Mock()
        self.session.owned_containers = Mock(return_value=[])
        self.session.compose = Mock()
        self.session.exec_ros = Mock()
        # fcntl exists on Linux; a mock allows this read-only contract test on Windows too.
        with patch.object(launcher.sys, 'platform', 'linux'), \
             patch.object(launcher.os, 'getuid', return_value=1000, create=True), \
             patch.object(launcher, 'Session', return_value=self.session), \
             patch.dict(sys.modules, {'fcntl': Mock()}), contextlib.redirect_stdout(io.StringIO()) as out:
            launcher.main(['status'])
        self.assertIn('Unity: stopped', out.getvalue())
        self.session.exec_ros.assert_not_called()

    def test_graphical_requires_local_display(self):
        with patch.dict(launcher.os.environ, {'DISPLAY': 'remote.example:0'}):
            with self.assertRaisesRegex(launcher.SessionError, 'local X11'):
                self.session.graphical()

    def test_graphical_scopes_and_wildcards_cookie(self):
        self.session.run = Mock(return_value=Mock(stdout='0100aabbcc\n'))
        with patch.dict(launcher.os.environ, {'DISPLAY': ':2'}), \
             patch.object(Path, 'is_socket', return_value=True), \
             patch.object(launcher.shutil, 'which', return_value='/usr/bin/xauth'):
            self.session.graphical()
        self.assertEqual(self.session.run.call_args_list[0].args[0], ['xauth', 'nlist', ':2'])
        self.assertEqual(self.session.run.call_args.kwargs['input'], 'ffffaabbcc\n')

    def test_native_display_without_cookie_rejected(self):
        with patch.dict(launcher.os.environ, {'DISPLAY': ':0'}), \
             patch.object(Path, 'is_socket', return_value=True), \
             patch.object(Path, 'is_dir', return_value=False), \
             patch.object(launcher.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(launcher.SessionError, 'Install xauth'):
                self.session.graphical()

    def test_wslg_display_without_xauth_supported(self):
        with patch.dict(launcher.os.environ, {'DISPLAY': ':0'}), \
             patch.object(Path, 'is_socket', return_value=True), \
             patch.object(Path, 'is_dir', return_value=True), \
             patch.object(launcher.shutil, 'which', return_value=None):
            self.session.graphical()
        self.assertEqual(Path(self.session.env['IGVC_XAUTHORITY']).read_bytes(), b'')


if __name__ == '__main__':
    unittest.main()
