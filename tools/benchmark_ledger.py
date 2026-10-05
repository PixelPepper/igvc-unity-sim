#!/usr/bin/env python3
"""Append one row per saved live run to docs/evidence/benchmark_runs.csv.

Usage:
  benchmark_ledger.py append <run_dir> [--audit PATH] [--run-id ID] [--notes TEXT] [--ledger CSV] [--lock-timeout S]
  benchmark_ledger.py backfill <run_dir> [<run_dir> ...] [--ledger CSV] [--lock-timeout S]

Supported layouts (detected from files, never guessed):
  iteration  run.json, live.json, audit.json, profile.yaml   (tools/agents/iteration-live.ps1)
  sandbox    run.json, provenance.json, an audit JSON, profile.yaml   (tools/sandbox_session.py)
A sandbox run often has several audit files; pass --audit when more than one exists.
Batch runs are not a supported layout. backfill is all-or-nothing: if any run
directory is invalid, no row is written.

Column semantics (copied from the run's own artifacts, never recomputed or
taken from the current checkout; an unrecorded value stays empty):
  run_id               --run-id, else the sandbox directory name or
                       "<date dir>/<role dir>" for an iteration run. Validated.
  utc                  iteration live.json started_utc (trial start); sandbox
                       provenance.json created_utc (session record creation).
                       These are different events.
  git_sha, player_sha  iteration live.json commit / player_assembly_sha256.
                       A sandbox run records neither, so they stay empty.
  seed                 run.json `seed` if it is an integer. The course label in
                       sim_status (course=seed-2027) is not treated as a seed.
  controller           sandbox settings.controller, else the single known
                       controller plugin in profile.yaml (rpp | mppi).
  elapsed_s            run.json elapsed_wall_s: the mission's own wall-clock
                       duration, not simulation time and not the audit span.
  destinations         completed/total from run.json.
  backups              number of entries in run.json `recoveries` (recorded
                       recovery executions), not backup distance.
  min_clearance_m      audit conservative_swept_clearance_lower_bound_m: a
                       conservative lower bound on swept-body obstacle clearance.
  return_distance_m    audit final_distance_to_origin_m.
  health_failed_samples audit sensor_health_evidence.interval_totals.fail.
  audit_passed         the audit's `passed` only if it is a JSON boolean and the
                       audit is bound to these run bytes; otherwise `unknown`.
  audit_binding        run_sha256_matched | unbound_no_run_sha256 (no audit
                       values are copied). A differing run_sha256 is an error.
  profile_binding      matched | unverified_profile_missing | no_recorded_hash.
                       Recorded profile hash vs profile.yaml bytes; a mismatch
                       is an error.
Rows with different course, mission or profile hashes are not controlled comparisons.

Ledger safety: the whole read/validate/append transaction holds an exclusive
lock file (<ledger>.lock, created atomically). Contention waits up to
--lock-timeout seconds and then fails; a foreign lock is never removed. A stale
lock left by a crashed process must be inspected and removed by a person.
Existing rows are validated (columns, run_id, unique run_id and run_sha256) and
their bytes are preserved; new rows are appended using the file's existing line
ending. A run_id already present with identical values is a no-op; different
values, or the same run_sha256 under another run_id, are errors. Any error
leaves the ledger byte-for-byte unchanged. Standard library only.
"""

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
import time

LEDGER = Path(__file__).resolve().parents[1] / 'docs' / 'evidence' / 'benchmark_runs.csv'
COLUMNS = (
    'run_id', 'utc', 'git_sha', 'profile_sha', 'player_sha', 'seed', 'controller',
    'requested_speed_mps', 'elapsed_s', 'destinations', 'backups', 'min_clearance_m',
    'return_distance_m', 'health_failed_samples', 'audit_passed', 'source', 'notes',
    'certification_status', 'geometric_full_loop', 'course_sha256', 'mission_sha256',
    'run_sha256', 'audit_file', 'audit_sha256', 'audit_binding', 'profile_binding')
AUDIT_NAMES = ('audit.json', 'handoff-audit.json', 'claude-audit.json')
CONTROLLERS = {'nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController': 'rpp',
               'nav2_mppi_controller::MPPIController': 'mppi'}
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*(/[A-Za-z0-9][A-Za-z0-9_.-]*)?')
SHA256 = re.compile(r'[0-9a-f]{64}')


class LedgerError(Exception):
    pass


def sha256(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as error:
        raise LedgerError(f'cannot read {path}: {error}') from error


def load_object(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise LedgerError(f'cannot read {path}: {error}') from error
    if not isinstance(value, dict):
        raise LedgerError(f'{path}: expected a JSON object, found {type(value).__name__}')
    return value


def text(value):
    """Render a recorded scalar; absent or structured values stay empty."""
    if value is None or isinstance(value, (dict, list)):
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return repr(value) if isinstance(value, float) else str(value)


def get(value, *path):
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def check_run_id(run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id) or \
            any(part in ('.', '..') for part in run_id.split('/')):
        raise LedgerError(f'invalid run_id {run_id!r}: use letters, digits, ._- and at most one /')
    return run_id


def find_audit(run_dir, audit):
    if audit:
        return Path(audit)
    present = [run_dir/name for name in AUDIT_NAMES if (run_dir/name).exists()]
    if len(present) != 1:
        raise LedgerError(f'{run_dir}: expected exactly one audit file among {AUDIT_NAMES}, found '
                          f'{[p.name for p in present]}; pass --audit')
    return present[0]


def controller_from_profile(profile_text):
    plugins = re.findall(r'^\s*plugin:\s*"?([\w:]+)"?\s*$', profile_text, re.M)
    found = {CONTROLLERS[p] for p in plugins if p in CONTROLLERS}
    return found.pop() if len(found) == 1 else ''


def build_row(run_dir, audit=None, run_id=None, notes=''):
    run_dir = Path(run_dir).resolve()  # normalizes dot paths before deriving an id
    run_path, profile_path = run_dir/'run.json', run_dir/'profile.yaml'
    if (run_dir/'live.json').exists():
        source, meta = 'iteration', load_object(run_dir/'live.json')
        utc, git_sha = meta.get('started_utc'), meta.get('commit')
        profile_sha, player_sha = meta.get('profile_sha256'), meta.get('player_assembly_sha256')
        default_id = f'{run_dir.parent.name}/{run_dir.name}'
    elif (run_dir/'provenance.json').exists():
        source, meta = 'sandbox', load_object(run_dir/'provenance.json')
        utc, git_sha, player_sha = meta.get('created_utc'), None, None
        profile_sha = meta.get('profile_sha256')
        default_id = run_dir.name
    else:
        raise LedgerError(f'{run_dir}: neither live.json (iteration) nor provenance.json (sandbox) present')
    if not run_path.exists():
        raise LedgerError(f'{run_dir}: run.json missing')
    run = load_object(run_path)
    audit_path = find_audit(run_dir, audit)
    report = load_object(audit_path)

    run_sha = sha256(run_path)
    audit_binding = 'run_sha256_matched'
    if 'run_sha256' not in report:
        audit_binding, report = 'unbound_no_run_sha256', {}  # may describe another run: copy nothing
    elif report['run_sha256'] != run_sha:
        raise LedgerError(f'{audit_path}: run_sha256 {report["run_sha256"]} does not match run.json {run_sha}')

    profile_text = None
    if profile_path.exists():
        try:
            profile_text = profile_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as error:
            raise LedgerError(f'cannot read {profile_path}: {error}') from error
    if not profile_sha:
        profile_binding = 'no_recorded_hash'
    elif profile_text is None:
        profile_binding = 'unverified_profile_missing'
    elif sha256(profile_path) != profile_sha:
        raise LedgerError(f'{profile_path}: bytes do not match recorded profile hash {profile_sha}')
    else:
        profile_binding = 'matched'

    controller = get(meta, 'settings', 'controller') or (
        controller_from_profile(profile_text) if profile_text is not None else '')
    seed = run.get('seed')
    done, total = run.get('completed_destinations'), run.get('total_destinations')
    recoveries = run.get('recoveries')
    verdict = report.get('passed')
    row = {
        'run_id': check_run_id(run_id if run_id is not None else default_id),
        'utc': text(utc), 'git_sha': text(git_sha), 'profile_sha': text(profile_sha),
        'player_sha': text(player_sha),
        'seed': str(seed) if isinstance(seed, int) and not isinstance(seed, bool) else '',
        'controller': text(controller),
        'requested_speed_mps': text(run.get('requested_speed_mps')),
        'elapsed_s': text(run.get('elapsed_wall_s')),
        'destinations': f'{done}/{total}' if isinstance(done, int) and isinstance(total, int) else '',
        'backups': str(len(recoveries)) if isinstance(recoveries, list) else '',
        'min_clearance_m': text(report.get('conservative_swept_clearance_lower_bound_m')),
        'return_distance_m': text(report.get('final_distance_to_origin_m')),
        'health_failed_samples': text(get(report, 'sensor_health_evidence', 'interval_totals', 'fail')),
        'audit_passed': text(verdict) if isinstance(verdict, bool) else 'unknown',
        'source': source, 'notes': notes,
        'certification_status': text(report.get('certification_status')),
        'geometric_full_loop': text(report.get('geometric_full_loop_certified')),
        'course_sha256': text(get(report, 'course_identity', 'expected_course_sha256')),
        'mission_sha256': text(get(report, 'mission_identity', 'expected_mission_sha256')),
        'run_sha256': run_sha, 'audit_file': audit_path.name, 'audit_sha256': sha256(audit_path),
        'audit_binding': audit_binding, 'profile_binding': profile_binding}
    if any(c in notes for c in '\r\n'):
        raise LedgerError('notes must be a single line')
    return row


def read_ledger(ledger):
    """Return (raw bytes, rows). Rejects any shape the writer would not produce."""
    if not ledger.exists():
        return b'', []
    raw = ledger.read_bytes()
    try:
        content = raw.decode('utf-8')
    except UnicodeDecodeError as error:
        raise LedgerError(f'{ledger}: not UTF-8: {error}') from error
    if content and not content.endswith('\n'):
        raise LedgerError(f'{ledger}: last line is not terminated; refusing to append')
    reader = csv.DictReader(io.StringIO(content, newline=''))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise LedgerError(f'{ledger}: header does not match the expected columns')
    rows, ids, shas = [], set(), set()
    for number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise LedgerError(f'{ledger}: row {number} has the wrong number of fields')
        try:
            check_run_id(row['run_id'])
        except LedgerError as error:
            raise LedgerError(f'{ledger}: row {number}: {error}') from error
        if not SHA256.fullmatch(row['run_sha256']):
            raise LedgerError(f'{ledger}: row {number}: invalid run_sha256')
        if row['run_id'] in ids or row['run_sha256'] in shas:
            raise LedgerError(f'{ledger}: row {number}: duplicate run_id or run_sha256')
        ids.add(row['run_id'])
        shas.add(row['run_sha256'])
        rows.append(row)
    return raw, rows


class LedgerLock:
    """Exclusive cross-process lock: an atomically created <ledger>.lock file."""

    def __init__(self, ledger, timeout_s):
        self.path = ledger.with_name(ledger.name + '.lock')
        self.timeout_s = timeout_s
        self.held = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_s
        while True:
            try:
                handle = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise LedgerError(f'{self.path} is held by another process (waited {self.timeout_s} s); '
                                      'it is never removed automatically') from None
                time.sleep(0.05)
                continue
            with os.fdopen(handle, 'w') as out:
                out.write(f'pid={os.getpid()} host={socket.gethostname()}\n')
            self.held = True
            return self

    def __exit__(self, *exc):
        if self.held:
            os.unlink(self.path)
            self.held = False


def add(rows, ledger, lock_timeout_s=10.0):
    """Validate every row against the ledger, then append once, under the lock."""
    with LedgerLock(ledger, lock_timeout_s):
        raw, existing = read_ledger(ledger)
        by_id = {row['run_id']: row for row in existing}
        by_sha = {row['run_sha256']: row['run_id'] for row in existing}
        new, results = [], []
        for row in rows:
            current = by_id.get(row['run_id'])
            if current is None:
                if row['run_sha256'] in by_sha:
                    raise LedgerError(f'run_sha256 {row["run_sha256"]} already recorded as '
                                      f'{by_sha[row["run_sha256"]]}; not adding it as {row["run_id"]}')
                by_id[row['run_id']], by_sha[row['run_sha256']] = row, row['run_id']
                new.append(row)
                results.append(f'appended {row["run_id"]}')
            elif current == row:
                results.append(f'unchanged {row["run_id"]} (identical row present)')
            else:
                differing = sorted(k for k in COLUMNS if current.get(k) != row[k])
                raise LedgerError(f'{row["run_id"]}: existing row conflicts on {differing}; ledger unchanged')
        if new:
            ending = '\r\n' if raw.split(b'\n', 1)[0].endswith(b'\r') else '\n'
            buffer = io.StringIO(newline='')
            writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator=ending)
            if not raw:
                writer.writeheader()
            writer.writerows(new)
            handle, temp = tempfile.mkstemp(dir=ledger.parent, prefix='.benchmark_runs.')
            try:
                with os.fdopen(handle, 'wb') as out:
                    out.write(raw + buffer.getvalue().encode('utf-8'))  # existing bytes untouched
                os.replace(temp, ledger)
            except BaseException:
                if os.path.exists(temp):
                    os.unlink(temp)
                raise
        return results


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--ledger', type=Path, default=LEDGER, help='CSV path (default: %(default)s)')
    common.add_argument('--lock-timeout', type=float, default=10.0, help='seconds to wait for the ledger lock')
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    append = sub.add_parser('append', parents=[common], help='add one run; --audit/--run-id resolve ambiguity')
    append.add_argument('run_dir', type=Path)
    append.add_argument('--audit')
    append.add_argument('--run-id')
    append.add_argument('--notes', default='')
    backfill = sub.add_parser('backfill', parents=[common], help='add several runs, all or nothing')
    backfill.add_argument('run_dirs', type=Path, nargs='+')
    args = parser.parse_args(argv)
    try:
        rows = ([build_row(args.run_dir, args.audit, args.run_id, args.notes)] if args.command == 'append'
                else [build_row(run_dir) for run_dir in args.run_dirs])
        for line in add(rows, args.ledger, args.lock_timeout):
            print(line)
    except LedgerError as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
