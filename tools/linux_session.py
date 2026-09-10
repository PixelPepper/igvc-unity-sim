"""Native Linux Docker/Unity lifecycle. No privileged Docker or GUI fallback."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'igvc-sim'


class SessionError(RuntimeError):
    pass


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    actions = result.add_subparsers(dest='action', required=True)
    for name in ('build', 'prepare-unity', 'unity-build', 'start', 'status',
                 'rviz', 'shell', 'run', 'course', 'audit', 'stop'):
        action = actions.add_parser(name)
        if name in ('start', 'course', 'audit'):
            action.add_argument('--seed', type=int, default=2027)
            action.add_argument('--difficulty', choices=('easy', 'normal', 'hard'), default='normal')
        if name == 'unity-build':
            action.add_argument('--unity', default=os.environ.get('UNITY_EDITOR'))
        if name == 'run':
            action.add_argument('command', nargs=argparse.REMAINDER)
    return result


def process_identity(pid):
    """An executable, boot and start tick tuple prevents PID reuse from owning a process."""
    try:
        proc = Path('/proc') / str(pid)
        stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        if stat[0] == 'Z':
            return None
        return dict(pid=pid, start_ticks=stat[19],
                    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    executable=str((proc / 'exe').resolve(strict=True)))
    except (OSError, ValueError, IndexError):
        return None


class Session:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.directory = self.root / 'artifacts/session'
        self.state_path = self.directory / 'linux-player.json'
        self.player = self.root / 'artifacts/build-course-linux/IGVCCourse.x86_64'
        self.env = os.environ.copy()
        self.env.update(IGVC_UID=str(os.getuid()), IGVC_GID=str(os.getgid()))
        self.env.setdefault('DISPLAY', ':0')
        self.env['IGVC_XAUTHORITY'] = str(self.directory / 'linux.xauth')

    def run(self, args, capture=False, timeout=None, **kwargs):
        try:
            return subprocess.run(args, cwd=self.root, env=self.env, check=True,
                                  text=True, capture_output=capture, timeout=timeout, **kwargs)
        except FileNotFoundError as exc:
            raise SessionError(f'Missing command {args[0]}; install it and retry.') from exc
        except subprocess.TimeoutExpired as exc:
            raise SessionError(f'Command timed out: {args[0]}') from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or '').strip() if capture else ''
            raise SessionError(f'Command failed ({exc.returncode}): {args[0]} {detail}') from exc

    def compose(self, *args, **kwargs):
        return self.run(['docker', 'compose', '--project-name', PROJECT,
                         '-f', str(self.root / 'compose.yaml'),
                         '-f', str(self.root / 'compose.linux.yaml'), *args], **kwargs)

    def prerequisites(self):
        if not shutil.which('docker'):
            raise SessionError('Install Docker Engine and the Docker Compose v2 plugin.')
        try:
            self.run(['docker', 'info'], capture=True, timeout=20)
            self.run(['docker', 'compose', 'version'], capture=True, timeout=20)
        except SessionError as exc:
            raise SessionError('Docker must be running and accessible as your current user. '
                               'Configure Docker Engine group access for your user, then retry. '
                               f'No automatic sudo is used. {exc}') from exc
        self.directory.mkdir(parents=True, exist_ok=True)
        authority = Path(self.env['IGVC_XAUTHORITY'])
        if not authority.exists():
            authority.touch(mode=0o600)

    def graphical(self):
        display = os.environ.get('DISPLAY', '')
        match = re.fullmatch(r'(?:unix)?:(\d+)(?:\.\d+)?', display)
        if not match:
            raise SessionError('Set DISPLAY from a local X11 or XWayland desktop (for example :0).')
        endpoint = Path('/tmp/.X11-unix') / ('X' + match.group(1))
        if not endpoint.is_socket():
            raise SessionError(f'X11 socket {endpoint} is missing; log into X11 or enable XWayland.')
        self.env['DISPLAY'] = display
        authority = Path(self.env['IGVC_XAUTHORITY'])
        cookie = ''
        if shutil.which('xauth'):
            # Read only this display's cookie, never dump the user's complete authority.
            cookie = self.run(['xauth', 'nlist', display], capture=True, timeout=10).stdout.strip()
        if cookie:
            narrow = '\n'.join('ffff' + line[4:] for line in cookie.splitlines()) + '\n'
            authority.write_text('')
            authority.chmod(0o600)
            self.run(['xauth', '-f', str(authority), 'nmerge', '-'],
                     input=narrow, capture=True, timeout=10)
        elif Path('/mnt/wslg').is_dir():
            # WSLg commonly provides a local socket without MIT-MAGIC-COOKIE authentication.
            authority.write_text('')
            authority.chmod(0o600)
        else:
            raise SessionError('No X11 authentication cookie found. Install xauth and set '
                               'XAUTHORITY to your desktop authority file; do not use xhost +.')

    def containers(self):
        ids = self.run(['docker', 'ps', '-aq', '--filter',
                        f'label=com.docker.compose.project={PROJECT}'], capture=True, timeout=20).stdout.split()
        if not ids:
            return []
        return json.loads(self.run(['docker', 'inspect', *ids], capture=True, timeout=20).stdout)

    def owned_containers(self):
        containers = self.containers()
        expected = str(self.root / 'artifacts')
        for container in containers:
            labels = container.get('Config', {}).get('Labels', {}) or {}
            directory = labels.get('com.docker.compose.project.working_dir', '')
            mounts = [m.get('Source') for m in container.get('Mounts', [])
                      if m.get('Destination') == '/opt/igvc/artifacts']
            if directory != str(self.root) or mounts != [expected]:
                raise SessionError('The igvc-sim Compose project belongs to another checkout '
                                   'or has unverifiable ownership. Stop it from its own checkout first.')
        return containers

    def saved(self):
        if not self.state_path.exists():
            return None
        try:
            state = json.loads(self.state_path.read_text())
            if not isinstance(state, dict) or not isinstance(state.get('pid'), int) or state['pid'] <= 0:
                raise ValueError('invalid PID')
            return state
        except (OSError, ValueError) as exc:
            raise SessionError(f'Invalid player state {self.state_path}; inspect it before removing it.') from exc

    def owns_player(self, state):
        if not state or state.get('root') != str(self.root) or state.get('executable') != str(self.player):
            return False
        identity = process_identity(state['pid'])
        return identity is not None and all(state.get(k) == v for k, v in identity.items())

    def stop_player(self):
        state = self.saved()
        if self.owns_player(state):
            # pidfd pins the kernel process even if it exits and its numerical PID is reused.
            try:
                fd = os.pidfd_open(state['pid'])
            except ProcessLookupError:
                fd = None
            if fd is not None:
                try:
                    if self.owns_player(state):
                        signal.pidfd_send_signal(fd, signal.SIGTERM)
                        deadline = time.monotonic() + 10
                        while self.owns_player(state) and time.monotonic() < deadline:
                            time.sleep(.1)
                        if self.owns_player(state):
                            signal.pidfd_send_signal(fd, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                finally:
                    os.close(fd)
        self.state_path.unlink(missing_ok=True)

    def exec_ros(self, *args, interactive=False):
        self.owned_containers()
        return self.compose('exec', *([] if interactive else ['-T']), 'ros',
                            '/opt/igvc/docker/entrypoint.sh', *args)

    def start(self, args):
        if not self.player.is_file() or not os.access(self.player, os.X_OK):
            raise SessionError('Run prepare-unity then unity-build to create the executable Linux player.')
        if self.owned_containers() or self.owns_player(self.saved()):
            raise SessionError('A session already exists. Run stop from its owning checkout first.')
        self.graphical()
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', 10000))
            except OSError as exc:
                raise SessionError('TCP port 10000 is already in use. Stop the existing simulator first.') from exc
        attempted = False
        child = None
        try:
            attempted = True
            self.compose('up', '-d', timeout=90)
            self.compose('run', '--rm', '--no-deps', 'ros', 'python3',
                         'tools/generate_course_variant.py', '--seed', str(args.seed),
                         '--difficulty', args.difficulty, timeout=120)
            folder = self.root / f'artifacts/courses/seed-{args.seed}'
            with (folder / 'linux-player-stdout.log').open('w') as log:
                child = subprocess.Popen([str(self.player), '--ros-ip', '127.0.0.1',
                    '--ros-port', '10000', '--course-manifest', str(folder / 'course.json'),
                    '-logFile', str(folder / 'docker-unity.log')], cwd=self.root,
                    env=self.env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            identity = process_identity(child.pid)
            if identity is None or identity['executable'] != str(self.player):
                raise SessionError('Unity exited before process ownership could be recorded; inspect its log.')
            identity.update(root=str(self.root), seed=args.seed, difficulty=args.difficulty)
            self.state_path.write_text(json.dumps(identity, indent=2) + '\n')
            deadline = time.monotonic() + 60
            started = time.monotonic()
            while True:
                if child.poll() is not None:
                    raise SessionError('Unity exited during startup; inspect docker-unity.log.')
                if time.monotonic() >= deadline:
                    raise SessionError('ROS TCP endpoint did not become available within 60 seconds.')
                try:
                    with socket.create_connection(('127.0.0.1', 10000), timeout=1):
                        if time.monotonic() - started >= 2:
                            break
                except OSError:
                    pass
                time.sleep(.25)
        except BaseException:
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)
            self.state_path.unlink(missing_ok=True)
            if attempted:
                try:
                    self.owned_containers()
                    self.compose('down', timeout=60)
                except SessionError as cleanup:
                    print(f'Startup cleanup: {cleanup}', file=sys.stderr)
            raise
        print('Unity is running and the ROS TCP endpoint accepts connections. '
              'Sensor, navigation and graphical readiness still require live verification.')

    def validate_course(self, args):
        path = self.root / f'artifacts/courses/seed-{args.seed}/course.json'
        try:
            course = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise SessionError(f'Generate this course with start first: {path}') from exc
        if course.get('seed') != args.seed or course.get('difficulty') != args.difficulty:
            raise SessionError('Requested seed/difficulty does not match the generated course.')
        if args.action == 'course':
            state = self.saved()
            if not self.owns_player(state) or state.get('seed') != args.seed or state.get('difficulty') != args.difficulty:
                raise SessionError('The running owned player does not match this seed/difficulty.')


def main(argv=None):
    args = parser().parse_args(argv)
    if not sys.platform.startswith('linux'):
        raise SessionError('Use this launcher on Linux. Windows users should use tools/docker.ps1.')
    if os.getuid() == 0:
        raise SessionError('Run as your desktop user, without sudo; configure Docker access for that user.')
    session = Session()
    if args.action == 'prepare-unity':
        session.run(['bash', str(ROOT / 'docker/prepare-unity.sh')])
        return
    if args.action == 'unity-build':
        editor = shutil.which(args.unity) if args.unity else None
        if not editor:
            raise SessionError('Install licensed Unity 6000.3.23f1 with Linux build support and pass '
                               '--unity /path/to/Editor/Unity or set UNITY_EDITOR.')
        log = ROOT / 'artifacts/logs/docker-unity-build-linux.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        session.run([editor, '-batchmode', '-quit', '-projectPath', str(ROOT / 'unity/IGVCSim'),
                     '-buildTarget', 'Linux64', '-executeMethod', 'GroundRenderChecks.BuildCourse',
                     '-logFile', str(log)])
        if not session.player.is_file():
            raise SessionError(f'Unity did not create the Linux player; inspect {log}')
        return
    if args.action == 'run' and not args.command:
        raise SessionError('Provide a container command after run.')
    session.prerequisites()
    import fcntl
    with (session.directory / 'linux-session.lock').open('a') as lock:
        # Interactive commands must not prevent emergency stop in another terminal.
        if args.action in ('start', 'stop'):
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise SessionError('Another start/stop operation is in progress in this checkout.') from exc
        session.owned_containers()
        if args.action == 'build':
            session.compose('build')
        elif args.action == 'start':
            session.start(args)
        elif args.action == 'stop':
            session.stop_player()
            session.compose('down', timeout=60)
        elif args.action == 'status':
            session.compose('ps', '-a')
            state = session.saved()
            print('Unity: ' + ('running (owned)' if session.owns_player(state) else
                              'stopped (stale state ignored)' if state else 'stopped'))
        elif args.action == 'shell':
            session.exec_ros('bash', interactive=True)
        elif args.action == 'run':
            command = args.command[1:] if args.command[0] == '--' else args.command
            if not command:
                raise SessionError('Provide a container command after run.')
            session.exec_ros(*command)
        elif args.action == 'rviz':
            session.graphical()
            session.exec_ros('ros2', 'run', 'rviz2', 'rviz2', '-d',
                '/opt/igvc/install/igvc_sim_bridge/share/igvc_sim_bridge/rviz/nav.rviz',
                '--ros-args', '-p', 'use_sim_time:=true', interactive=True)
        elif args.action in ('course', 'audit'):
            session.validate_course(args)
            folder = f'/opt/igvc/artifacts/courses/seed-{args.seed}'
            if args.action == 'course':
                session.exec_ros('python3', 'tools/full_course.py', '--mission',
                                 f'{folder}/mission.json', '--report', f'{folder}/docker-run.json')
            else:
                session.exec_ros('python3', 'tools/audit_course_variant.py', '--course',
                                 f'{folder}/course.json', '--run', f'{folder}/docker-run.json')


if __name__ == '__main__':
    try:
        main()
    except (SessionError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
