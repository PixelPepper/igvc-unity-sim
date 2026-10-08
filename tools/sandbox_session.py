#!/usr/bin/env python3
"""Own a stopped/editable sandbox and one sensor-led mission at a time."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid
import yaml
from sandbox_profile import ROOT, build_profile, mission_argv, validate_settings
from session_paths import session_dir


def atomic_json(path, data):
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
    # Windows readers without delete sharing briefly deny WSL replacement.
    # Preserve atomic visibility and bound this filesystem-only retry to 1 s (parallel
    # instances lengthened the lock beyond .25 s); Unity treats status as stale only after 3 s.
    for attempt in range(41):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 40:
                raise
            time.sleep(.025)


def parse_command(value):
    if not isinstance(value, dict) or set(value) - {'id', 'action', 'settings'}:
        raise ValueError('Invalid command schema')
    if not isinstance(value.get('id'), str) or not 1 <= len(value['id']) <= 128:
        raise ValueError('Command requires an id of 1..128 characters')
    if value.get('action') not in ('start', 'stop'):
        raise ValueError('Invalid command action')
    settings = validate_settings({} if value['action'] == 'stop' else value.get('settings', {}))
    return value['id'], value['action'], settings


def group_running(pgid):
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().split(') ', 1)[1].split()
            if fields[0] != 'Z' and int(fields[2]) == pgid:
                return True
        except (OSError, ValueError, IndexError):
            pass
    return False


def stop_child(child):
    if child is None:
        return
    for sig, timeout in ((signal.SIGINT, 15), (signal.SIGTERM, 5)):
        if child.poll() is not None and not group_running(child.pid):
            return
        try:
            # Give the coordinator time to save evidence and close its planner.
            # Interrupting the entire group also kills multiprocessing workers.
            if sig == signal.SIGINT and child.poll() is None:
                child.send_signal(sig)
            else:
                os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        deadline = time.monotonic()+timeout
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        while group_running(child.pid) and time.monotonic() < deadline:
            time.sleep(.1)
        if child.poll() is not None and not group_running(child.pid):
            return
    raise RuntimeError('Subprocess did not confirm exit; ownership retained')


# Perception nodes whose use_sim_time must be true before a mission may spawn.
CLOCK_NODES = ('/igvc_lane_detector', '/igvc_depth_processor')
# One monotonic deadline bounds discovery and responses for every node together.
CLOCK_ADMISSION_TIMEOUT = 15.0
# rcl_interfaces/msg/ParameterType constants (kept local so unit tests need no ROS).
PARAMETER_NOT_SET, PARAMETER_BOOL = 0, 1
CLOCK_SCOPE = ('Configuration admission only: use_sim_time=true does not prove /clock delivery, '
               'sensor freshness or processing health, or a safe or audited mission')


class ClockAdmissionError(RuntimeError):
    """Perception clock configuration was not positively confirmed."""


def classify_sim_time(response):
    """Strictly classify a GetParameters response for the single use_sim_time request."""
    observed = dict(status='malformed', value=None, type=None, error=None)
    values = getattr(response, 'values', None)
    try:
        values = list(values)
    except TypeError:
        return observed | dict(error='Response has no parameter value sequence')
    if len(values) != 1:
        return observed | dict(error='Expected exactly one parameter value, received %d' % len(values))
    kind = getattr(values[0], 'type', None)
    if type(kind) is not int:
        return observed | dict(error='Parameter type is not an integer: %r' % (kind,))
    observed['type'] = kind
    if kind == PARAMETER_NOT_SET:
        return observed | dict(status='absent', error='use_sim_time is not set')
    if kind != PARAMETER_BOOL:
        return observed | dict(status='wrong_type', error='use_sim_time has non-Boolean parameter type %d' % kind)
    flag = getattr(values[0], 'bool_value', None)
    if type(flag) is not bool:
        return observed | dict(error='Boolean parameter carries non-Boolean value %r' % (flag,))
    observed['value'] = flag
    if flag is not True:
        return observed | dict(status='false', error='use_sim_time is false')
    return observed | dict(status='true')


def check_sim_time(make_client, spin, nodes=CLOCK_NODES, timeout=CLOCK_ADMISSION_TIMEOUT,
                   monotonic=time.monotonic):
    """Query use_sim_time on each node through its parameter services; never raises."""
    started = monotonic()
    deadline = started+min(timeout, CLOCK_ADMISSION_TIMEOUT)
    observations = []
    for name in nodes:
        observed = dict(node=name, status='timeout', value=None, type=None, error=None)
        try:
            remaining = deadline-monotonic()
            if remaining <= 0:
                raise TimeoutError('Admission deadline exhausted before querying this node')
            client = make_client(name)
            if not client.wait_for_services(timeout_sec=remaining):
                observed.update(status='service_unavailable',
                                error='Parameter services not discovered within %.1f s' % remaining)
                observations.append(observed); continue
            remaining = deadline-monotonic()
            if remaining <= 0:
                raise TimeoutError('Admission deadline exhausted after service discovery')
            future = client.get_parameters(['use_sim_time'])
            spin(future, remaining)
            if not future.done():
                future.cancel()
                raise TimeoutError('No parameter response within %.1f s' % remaining)
            failure = future.exception()
            if failure is not None:
                raise failure
            observed.update(classify_sim_time(future.result()))
        except TimeoutError as exc:
            observed.update(status='timeout', error=str(exc))
        except Exception as exc:
            observed.update(status='exception', value=None, type=None, error=type(exc).__name__+': '+str(exc))
        observations.append(observed)
    return dict(parameter='use_sim_time', requirement='exactly one Boolean true per node',
                requested_nodes=list(nodes), timeout_seconds=min(timeout, CLOCK_ADMISSION_TIMEOUT),
                elapsed_seconds=round(monotonic()-started, 3),
                checked_utc=datetime.now(timezone.utc).isoformat(),
                admitted=len(observations) == len(nodes) > 0 and all(item['status'] == 'true' for item in observations),
                nodes=observations, scope=CLOCK_SCOPE)


class RosControl:
    def __init__(self):
        import rclpy
        from std_srvs.srv import SetBool, Trigger
        self.rclpy = rclpy
        rclpy.init()
        self.node = rclpy.create_node('sandbox_supervisor')
        self.gate = self.node.create_client(SetBool, '/sim/set_autonomy')
        self.reset = self.node.create_client(Trigger, '/sim/reset')
        self.estop = self.node.create_client(SetBool, '/sim/estop')
        self.SetBool, self.Trigger = SetBool, Trigger

    def call(self, client, request):
        if not client.wait_for_service(timeout_sec=8):
            raise RuntimeError('Simulator service unavailable')
        future = client.call_async(request)
        self.rclpy.spin_until_future_complete(self.node, future, timeout_sec=8)
        if not future.done() or future.result() is None or not future.result().success:
            raise RuntimeError('Simulator service did not confirm success')

    def disable(self):
        request = self.SetBool.Request(); request.data = False
        self.call(self.gate, request)

    def reset_pose(self):
        request = self.SetBool.Request(); request.data = False
        self.call(self.estop, request)
        self.call(self.reset, self.Trigger.Request())

    def verify_sim_time(self, nodes=CLOCK_NODES, timeout=CLOCK_ADMISSION_TIMEOUT):
        clients = []
        def make_client(name):
            from rclpy.parameter_client import AsyncParameterClient
            clients.append(AsyncParameterClient(self.node, name))
            return clients[-1]
        def spin(future, timeout_sec):
            self.rclpy.spin_until_future_complete(self.node, future, timeout_sec=timeout_sec)
        try:
            return check_sim_time(make_client, spin, nodes, timeout)
        finally:
            for client in clients:
                try:
                    client.destroy()
                except Exception:
                    pass

    def close(self):
        self.node.destroy_node(); self.rclpy.shutdown()


class Supervisor:
    def __init__(self, directory, mission, ros):
        self.directory, self.mission, self.ros = directory, mission, ros
        self.child = None
        self.nav_owned = False
        self.failed_cleanup = False
        self.seen = set()
        self.command_id = ''
        self.folder = None
        self.state = 'idle'
        self.message = ''
        self.completed = 0
        self.last_invalid = None
        self.status_lock = threading.RLock()
        self.heartbeat_stop = threading.Event()
        self.heartbeat_thread = None

    def status(self, state, message):
        with self.status_lock:
            self.state = state
            self.message = message
            self.write_status()

    def write_status(self):
        with self.status_lock:
            atomic_json(self.directory / 'status.json', dict(id=self.command_id, state=self.state,
                        message=self.message, completed_destinations=self.completed, total_destinations=6,
                        editable=self.state in ('idle', 'completed') and not self.failed_cleanup,
                        heartbeat_utc=datetime.now(timezone.utc).isoformat()))

    def start_heartbeat(self):
        def heartbeat():
            while not self.heartbeat_stop.wait(.5):
                try:
                    self.write_status()
                except OSError:
                    # Preserve supervision through transient shared-file failures.
                    pass
        self.heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        self.heartbeat_thread.start()

    def stop_heartbeat(self):
        self.heartbeat_stop.set()
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)

    def nav(self, action, profile=None):
        argv = [sys.executable, str(ROOT / 'tools/ros_session.py'), action, 'nav']
        if profile:
            argv += ['--params-file', str(profile)]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=35)
        if self.folder:
            with (self.folder / 'nav-management.log').open('a') as log:
                log.write(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError('Managed navigation '+action+' failed: '+result.stderr[-500:])

    def cleanup(self):
        errors = []
        # Disable first, even when mission cancellation cannot be confirmed.
        for label, operation in [('autonomy gate', self.ros.disable),
                                 ('mission', lambda: stop_child(self.child)),
                                 ('navigation', lambda: self.nav('stop') if self.nav_owned else None),
                                 ('final autonomy gate', self.ros.disable)]:
            try:
                operation()
            except Exception as exc:
                errors.append(label+': '+str(exc))
        self.failed_cleanup = bool(errors)
        if errors:
            raise RuntimeError('; '.join(errors))
        self.child = None
        self.nav_owned = False

    def startup(self):
        # Any existing command is acknowledged but never replayed on restart.
        try:
            value = json.loads((self.directory / 'command.json').read_text())
            if isinstance(value, dict) and isinstance(value.get('id'), str):
                self.command_id = value['id']; self.seen.add(self.command_id)
        except (OSError, ValueError):
            pass
        self.ros.disable()
        if (session_dir(ROOT) / 'nav.json').exists():
            raise RuntimeError('Managed navigation already exists; refusing to advertise editable idle')
        self.status('idle', 'Ready; command present at startup ignored')

    def start(self, settings):
        if self.child is not None or self.nav_owned or self.failed_cleanup:
            raise RuntimeError('Stop and confirm cleanup before starting another mission')
        # Never claim an existing managed navigation launch as ours.
        if (session_dir(ROOT) / 'nav.json').exists():
            raise RuntimeError('An existing managed navigation session must be stopped first')
        self.completed = 0
        self.status('starting', 'Disabling autonomy and resetting pose')
        self.ros.disable(); self.ros.reset_pose()
        self.folder = self.directory / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
        self.folder.mkdir(parents=True)
        profile, baseline = build_profile(settings)
        profile_path = self.folder / 'profile.yaml'
        profile_path.write_text(yaml.safe_dump(profile, sort_keys=False))
        # Freeze the already sanitized six-destination mission for this run.
        mission_path = self.folder / 'autonomy.json'
        mission_path.write_bytes(self.mission.read_bytes())
        course_path = self.directory / 'course.json'
        if course_path.is_file():
            (self.folder / 'course.json').write_bytes(course_path.read_bytes())
        from sensor_course import destinations
        if len(destinations(json.loads(mission_path.read_text()))) != 6:
            raise ValueError('Sandbox requires exactly six sanitized GPS destinations')
        argv = mission_argv(sys.executable, mission_path, self.folder, settings)
        atomic_json(self.folder / 'provenance.json', dict(command_id=self.command_id,
                    settings=settings, baseline=str(baseline), mission=str(self.mission),
                    mission_sha256=hashlib.sha256(mission_path.read_bytes()).hexdigest(),
                    profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest(),
                    mission_argv=argv, created_utc=datetime.now(timezone.utc).isoformat()))
        self.nav_owned = True
        try:
            self.nav('start', profile_path)
            # Simulator autonomy stays disabled; no mission spawns without admission.
            self.status('starting', 'Verifying perception use_sim_time configuration')
            self.admit_clock()
            with (self.folder / 'mission.log').open('w') as log:
                self.child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                              stdin=subprocess.DEVNULL, start_new_session=True)
            provenance = json.loads((self.folder / 'provenance.json').read_text())
            provenance['mission_pid'] = self.child.pid
            provenance['supervisor_pid'] = os.getpid()
            provenance['navigation_session'] = json.loads((session_dir(ROOT) / 'nav.json').read_text())
            frozen_course = self.folder / 'course.json'
            provenance['course_sha256'] = hashlib.sha256(frozen_course.read_bytes()).hexdigest() if frozen_course.exists() else None
            atomic_json(self.folder / 'provenance.json', provenance)
        except (OSError, ValueError) as exc:
            # process_command treats these as invalid commands without cleanup;
            # navigation (and possibly a mission) is owned now, so force cleanup.
            raise RuntimeError('Mission start failed after navigation start: '+str(exc)) from exc
        self.status('running', 'Sensor-led mission running')

    def admit_clock(self):
        """Persist perception clock configuration evidence; raise unless positively admitted."""
        try:
            evidence = self.ros.verify_sim_time()
            if not isinstance(evidence, dict) or not isinstance(evidence.get('nodes'), list):
                raise TypeError('Clock admission returned malformed evidence')
        except Exception as exc:
            # Record the failure itself; never fabricate observations.
            evidence = dict(parameter='use_sim_time', requirement='exactly one Boolean true per node',
                            requested_nodes=list(CLOCK_NODES), admitted=False,
                            checked_utc=datetime.now(timezone.utc).isoformat(),
                            error=type(exc).__name__+': '+str(exc), scope=CLOCK_SCOPE,
                            nodes=[dict(node=name, status='not_observed', value=None, type=None, error=None)
                                   for name in CLOCK_NODES])
        observed = {item.get('node'): item for item in evidence['nodes'] if isinstance(item, dict)}
        admitted = (evidence.get('admitted') is True and
                    all(observed.get(name, {}).get('status') == 'true' and
                        observed[name].get('value') is True for name in CLOCK_NODES))
        evidence['admitted'] = admitted
        persist_error = None
        try:
            atomic_json(self.folder / 'clock-admission.json', evidence)
            provenance = json.loads((self.folder / 'provenance.json').read_text())
            provenance['clock_configuration'] = evidence
            atomic_json(self.folder / 'provenance.json', provenance)
        except Exception as exc:
            persist_error = 'clock evidence not persisted: '+str(exc)
        if not admitted:
            reasons = evidence.get('error') or '; '.join(
                '%s=%s (%s)' % (name, observed.get(name, {}).get('status', 'missing'),
                                observed.get(name, {}).get('error') or 'no detail') for name in CLOCK_NODES)
            raise ClockAdmissionError('Perception clock admission failed (use_sim_time): '+reasons+
                                      ('; '+persist_error if persist_error else ''))
        if persist_error:
            raise ClockAdmissionError('Perception clock admitted but '+persist_error)

    def tick(self):
        try:
            try:
                raw = (self.directory / 'command.json').read_text()
            except FileNotFoundError:
                raw = None
            if raw is not None:
                self.process_command(json.loads(raw))
        except Exception as exc:
            try:
                self.cleanup()
            except Exception as cleanup:
                exc = RuntimeError(str(exc)+'; cleanup failed: '+str(cleanup))
            self.status('error', str(exc))
        self.monitor_child()

    def process_command(self, value):
        try:
            command_id, action, settings = parse_command(value)
            self.last_invalid = None
            if command_id not in self.seen:
                self.seen.add(command_id); self.command_id = command_id
                atomic_json(self.directory / 'last-command.json', value)
                if action == 'stop':
                    self.status('stopping', 'Confirming mission and navigation shutdown')
                    self.cleanup()
                    self.status('idle', 'Stopped; course editing available')
                else:
                    self.start(settings)
        except (OSError, ValueError) as exc:
            marker = str(exc)
            if marker != self.last_invalid:
                self.last_invalid = marker
                self.status('error', 'Invalid or missing command: '+marker)
        except Exception as exc:
            try:
                self.cleanup()
            except Exception as cleanup:
                exc = RuntimeError(str(exc)+'; cleanup failed: '+str(cleanup))
            self.status('error', str(exc))
    def monitor_child(self):
        if self.child is not None:
            progress = self.folder / 'run.progress.json'
            try:
                value = json.loads(progress.read_text())
                self.completed = max(0, min(6, int(value.get('completed_destinations', 0))))
            except (OSError, ValueError, TypeError):
                pass
            # sensor_course writes its JSON progress at finalization; use its
            # flushed destination events to display progress while it runs.
            try:
                import re
                with (self.folder / 'mission.log').open('rb') as log:
                    log.seek(0, 2); log.seek(max(0, log.tell()-65536))
                    events = re.findall(rb'Destination ([1-6])/6', log.read())
                if events:
                    self.completed = max(self.completed, int(events[-1]))
            except OSError:
                pass
            code = self.child.poll()
            if code is not None:
                try:
                    report = json.loads((self.folder / 'run.json').read_text())
                    success = code == 0 and report.get('status') == 'completed' and report.get('completed_destinations') == 6
                    self.completed = int(report.get('completed_destinations', 0))
                    self.cleanup()
                    self.status('completed' if success else 'error', 'All destinations completed' if success else 'Mission failed; inspect run evidence')
                except Exception as exc:
                    try:
                        self.cleanup()
                    except Exception as cleanup:
                        exc = RuntimeError(str(exc)+'; cleanup failed: '+str(cleanup))
                    self.status('error', str(exc))
            elif self.state == 'running':
                self.status('running', 'Sensor-led mission running')
        self.status(self.state, self.message)


def main():
    import fcntl
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--mission', type=Path, required=True)
    parser.add_argument('--rviz', action='store_true')
    args = parser.parse_args()
    args.directory = args.directory.resolve(); args.mission = args.mission.resolve()
    args.directory.mkdir(parents=True, exist_ok=True)
    lock_path = session_dir(ROOT) / 'sandbox.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path.open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ros = RosControl(); supervisor = Supervisor(args.directory, args.mission, ros)
    rviz = None
    ending = False
    started = False
    def request_stop(*_):
        nonlocal ending
        ending = True
    signal.signal(signal.SIGINT, request_stop); signal.signal(signal.SIGTERM, request_stop)
    try:
        supervisor.startup()
        started = True
        supervisor.start_heartbeat()
        if args.rviz:
            with (args.directory / 'rviz.log').open('w') as log:
                rviz = subprocess.Popen(['rviz2', '-d', str(ROOT / 'ros2/src/igvc_sim_bridge/rviz/nav.rviz'),
                    '--ros-args', '-p', 'use_sim_time:=true'], stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=True)
        while not ending and not (args.directory / 'shutdown.request').exists():
            supervisor.tick(); time.sleep(.25)
    finally:
        supervisor.status('stopping', 'Supervisor shutdown; confirming cleanup')
        errors = []
        if not started:
            errors.append('Supervisor initialization failed; idle safety not confirmed')
        for operation in (supervisor.cleanup, lambda: stop_child(rviz)):
            try:
                operation()
            except Exception as exc:
                errors.append(str(exc))
        if (session_dir(ROOT) / 'nav.json').exists():
            errors.append('Managed navigation ownership remains; idle safety not confirmed')
        supervisor.status('error' if errors else 'idle', '; '.join(errors) if errors else 'Supervisor stopped')
        supervisor.stop_heartbeat()
        ros.close()
        lock.close()
        if errors:
            raise RuntimeError('; '.join(errors))


if __name__ == '__main__':
    main()
