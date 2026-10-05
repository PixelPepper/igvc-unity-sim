#!/usr/bin/env python3
"""Append one row per saved live run to docs/evidence/benchmark_runs.csv.

Usage:
  benchmark_ledger.py append <run_dir> [--audit PATH] [--run-id ID] [--notes TEXT] [--ledger CSV]
  benchmark_ledger.py backfill <run_dir> [<run_dir> ...] [--ledger CSV]

Supported layouts (detected from files, never guessed):
  iteration  run.json, live.json, audit.json, profile.yaml   (tools/agents/iteration-live.ps1)
  sandbox    run.json, provenance.json, an audit JSON, profile.yaml   (tools/sandbox_session.py)
A sandbox run often has several audit files; pass --audit when more than one exists.
Batch runs are not yet a supported layout.

Semantics: values are copied from the saved artifacts, never recomputed or
taken from the current checkout. A field the artifacts do not record stays
empty (for example, a sandbox run records no git commit or player hash). The
audit verdict is copied: only a JSON boolean is a verdict, anything else is
`unknown`. An audit without run_sha256 is recorded as unbound with no audit
values; one whose run_sha256 differs from run.json is an error. Recorded hashes are cross-checked against file bytes (run.json vs
the audit's run_sha256; profile.yaml vs the recorded profile hash), and a
mismatch is an error. Re-ingesting an identical row is a no-op; a different
row for an existing run_id is an error. Rows with different course, mission or
profile hashes are not controlled comparisons. Any error leaves the ledger
byte-for-byte unchanged. Standard library only.
"""

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile

LEDGER = Path(__file__).resolve().parents[1] / 'docs' / 'evidence' / 'benchmark_runs.csv'
COLUMNS = (
    'run_id', 'utc', 'git_sha', 'profile_sha', 'player_sha', 'seed', 'controller',
    'requested_speed_mps', 'elapsed_s', 'destinations', 'backups', 'min_clearance_m',
    'return_distance_m', 'health_failed_samples', 'audit_passed', 'source', 'notes',
    # Added identity/semantics columns (see module docstring).
    'certification_status', 'geometric_full_loop', 'course_sha256', 'mission_sha256',
    'run_sha256', 'audit_file', 'audit_sha256', 'audit_binding')
AUDIT_NAMES = ('audit.json', 'handoff-audit.json', 'claude-audit.json')
CONTROLLERS = {'nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController': 'rpp',
               'nav2_mppi_controller::MPPIController': 'mppi'}


class LedgerError(Exception):
    pass


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise LedgerError(f'cannot read {path}: {error}') from error


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


def find_audit(run_dir, audit):
    if audit:
        return Path(audit)
    present = [run_dir/name for name in AUDIT_NAMES if (run_dir/name).exists()]
    if len(present) != 1:
        raise LedgerError(f'{run_dir}: expected exactly one audit file among {AUDIT_NAMES}, found '
                          f'{[p.name for p in present]}; pass --audit')
    return present[0]


def controller_from_profile(profile_path):
    plugins = re.findall(r'^\s*plugin:\s*"?([\w:]+)"?\s*$', profile_path.read_text(encoding='utf-8'), re.M)
    found = {CONTROLLERS[p] for p in plugins if p in CONTROLLERS}
    return found.pop() if len(found) == 1 else ''


def build_row(run_dir, audit=None, run_id=None, notes=''):
    run_dir = Path(run_dir)
    run_path, profile_path = run_dir/'run.json', run_dir/'profile.yaml'
    if (run_dir/'live.json').exists():
        source, meta = 'iteration', load_json(run_dir/'live.json')
        utc, git_sha = meta.get('started_utc'), meta.get('commit')
        profile_sha, player_sha = meta.get('profile_sha256'), meta.get('player_assembly_sha256')
        default_id = f'{run_dir.parent.name}/{run_dir.name}'
    elif (run_dir/'provenance.json').exists():
        source, meta = 'sandbox', load_json(run_dir/'provenance.json')
        utc, git_sha, player_sha = meta.get('created_utc'), None, None
        profile_sha = meta.get('profile_sha256')
        default_id = run_dir.name
    else:
        raise LedgerError(f'{run_dir}: neither live.json (iteration) nor provenance.json (sandbox) present')
    if not run_path.exists():
        raise LedgerError(f'{run_dir}: run.json missing')
    run = load_json(run_path)
    audit_path = find_audit(run_dir, audit)
    report = load_json(audit_path)

    run_sha = sha256(run_path)
    binding = 'run_sha256_matched'
    if 'run_sha256' not in report:
        # Unbound audit: its numbers may describe another run, so none are copied.
        binding, report = 'unbound_no_run_sha256', {}
    elif report['run_sha256'] != run_sha:
        raise LedgerError(f'{audit_path}: run_sha256 {report.get("run_sha256")} does not match run.json {run_sha}')
    if profile_path.exists() and profile_sha and sha256(profile_path) != profile_sha:
        raise LedgerError(f'{profile_path}: bytes do not match recorded profile hash {profile_sha}')

    controller = get(meta, 'settings', 'controller') or (
        controller_from_profile(profile_path) if profile_path.exists() else '')
    seed = re.search(r'\bseed=(\d+)\b', run.get('sim_status') or '')
    done, total = run.get('completed_destinations'), run.get('total_destinations')
    recoveries = run.get('recoveries')
    verdict = report.get('passed')
    row = {
        'run_id': run_id or default_id, 'utc': text(utc), 'git_sha': text(git_sha),
        'profile_sha': text(profile_sha), 'player_sha': text(player_sha),
        'seed': seed.group(1) if seed else '', 'controller': text(controller),
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
        'audit_binding': binding}
    for key in ('run_id', 'notes'):
        if any(c in row[key] for c in '\r\n'):
            raise LedgerError(f'{key} must be a single line')
    return row


def read_ledger(ledger):
    if not ledger.exists():
        return []
    with ledger.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise LedgerError(f'{ledger}: header does not match the expected columns')
        return list(reader)


def add(rows, ledger):
    """Validate every row against the ledger, then write once atomically."""
    existing = read_ledger(ledger)
    by_id = {row['run_id']: row for row in existing}
    new, results = [], []
    for row in rows:
        current = by_id.get(row['run_id'])
        if current is None:
            by_id[row['run_id']] = row
            new.append(row)
            results.append(f'appended {row["run_id"]}')
        elif current == row:
            results.append(f'unchanged {row["run_id"]} (identical row present)')
        else:
            differing = sorted(k for k in COLUMNS if current.get(k) != row[k])
            raise LedgerError(f'{row["run_id"]}: existing row conflicts on {differing}; ledger unchanged')
    if new:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(existing + new)
        ledger.parent.mkdir(parents=True, exist_ok=True)
        handle, temp = tempfile.mkstemp(dir=ledger.parent, prefix='.benchmark_runs.')
        try:
            with os.fdopen(handle, 'w', encoding='utf-8', newline='') as out:
                out.write(buffer.getvalue())
            os.replace(temp, ledger)
        except BaseException:
            os.unlink(temp)
            raise
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ledger', type=Path, default=LEDGER)
    sub = parser.add_subparsers(dest='command', required=True)
    append = sub.add_parser('append', help='add one run; --audit/--run-id resolve ambiguity')
    append.add_argument('run_dir', type=Path)
    append.add_argument('--audit')
    append.add_argument('--run-id')
    append.add_argument('--notes', default='')
    backfill = sub.add_parser('backfill', help='add several runs, each with exactly one audit file')
    backfill.add_argument('run_dirs', type=Path, nargs='+')
    args = parser.parse_args(argv)
    try:
        rows = ([build_row(args.run_dir, args.audit, args.run_id, args.notes)] if args.command == 'append'
                else [build_row(run_dir) for run_dir in args.run_dirs])
        for line in add(rows, args.ledger):
            print(line)
    except LedgerError as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
