"""Benchmark ledger: both run layouts, verbatim verdicts, provenance binding, idempotency, safety."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import benchmark_ledger as ledger  # noqa: E402

PROFILE = 'controller_server:\n  ros__parameters:\n    FollowPath:\n      plugin: nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController\n'


def write(path, value):
    path.write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_run(root, layout, passed=True, sim_status='oracle seed=2027 run=1', audit_names=('audit.json',)):
    run_dir = Path(root) / 'runs' / f'{layout}-run'
    run_dir.mkdir(parents=True)
    run_sha = write(run_dir/'run.json', {
        'completed_destinations': 6, 'total_destinations': 6, 'elapsed_wall_s': 363.37,
        'requested_speed_mps': 0.6, 'recoveries': [{'actual_distance_m': .6}], 'sim_status': sim_status})
    profile_sha = write(run_dir/'profile.yaml', PROFILE)
    if layout == 'iteration':
        write(run_dir/'live.json', {'started_utc': '2026-10-02T02:44:27Z', 'commit': 'ac765e9',
                                    'profile_sha256': profile_sha, 'player_assembly_sha256': 'abc'})
    else:
        write(run_dir/'provenance.json', {'created_utc': '2026-10-02T03:57:16Z', 'profile_sha256': profile_sha,
                                          'settings': {'controller': 'mppi'}})
    for name in audit_names:
        write(run_dir/name, {
            'passed': passed, 'run_sha256': run_sha, 'certification_status': 'passed',
            'geometric_full_loop_certified': True, 'conservative_swept_clearance_lower_bound_m': .0793,
            'final_distance_to_origin_m': .3952, 'sensor_health_evidence': {'interval_totals': {'fail': 0}},
            'course_identity': {'expected_course_sha256': 'c'}, 'mission_identity': {'expected_mission_sha256': 'm'}})
    return run_dir


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.csv = self.root / 'benchmark_runs.csv'

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return ledger.main(['--ledger', str(self.csv), *map(str, args)])

    def rows(self):
        return ledger.read_ledger(self.csv)

    def test_iteration_layout_copies_recorded_provenance_and_verdict(self):
        run_dir = make_run(self.root, 'iteration')
        self.assertEqual(self.run_cli('append', run_dir), 0)
        row, = self.rows()
        self.assertEqual((row['run_id'], row['source'], row['git_sha'], row['player_sha']),
                         ('runs/iteration-run', 'iteration', 'ac765e9', 'abc'))
        self.assertEqual((row['seed'], row['controller'], row['destinations'], row['backups']),
                         ('2027', 'rpp', '6/6', '1'))
        self.assertEqual((row['audit_passed'], row['elapsed_s'], row['audit_binding']),
                         ('true', '363.37', 'run_sha256_matched'))

    def test_sandbox_layout_leaves_unrecorded_provenance_empty(self):
        run_dir = make_run(self.root, 'sandbox', passed=False, sim_status='oracle course=sandbox')
        self.assertEqual(self.run_cli('append', run_dir), 0)
        row, = self.rows()
        self.assertEqual((row['git_sha'], row['player_sha'], row['seed']), ('', '', ''))
        self.assertEqual((row['controller'], row['audit_passed']), ('mppi', 'false'))

    def test_ambiguous_audits_require_an_explicit_choice(self):
        run_dir = make_run(self.root, 'sandbox', audit_names=('handoff-audit.json', 'claude-audit.json'))
        self.assertEqual(self.run_cli('append', run_dir), 1)
        self.assertFalse(self.csv.exists())
        self.assertEqual(self.run_cli('append', run_dir, '--audit', run_dir/'handoff-audit.json'), 0)
        self.assertEqual(self.rows()[0]['audit_file'], 'handoff-audit.json')

    def test_non_boolean_or_unbound_verdict_is_unknown_never_pass(self):
        run_dir = make_run(self.root, 'iteration', passed='yes')
        self.assertEqual(self.run_cli('append', run_dir), 0)
        self.assertEqual(self.rows()[0]['audit_passed'], 'unknown')
        unbound = make_run(self.root/'b', 'iteration')
        audit = json.loads((unbound/'audit.json').read_text())
        del audit['run_sha256']
        write(unbound/'audit.json', audit)
        self.assertEqual(self.run_cli('append', unbound, '--run-id', 'unbound'), 0)
        row = self.rows()[1]
        self.assertEqual((row['audit_passed'], row['audit_binding'], row['return_distance_m']),
                         ('unknown', 'unbound_no_run_sha256', ''))

    def test_audit_for_other_run_bytes_fails_and_ledger_is_unchanged(self):
        self.assertEqual(self.run_cli('append', make_run(self.root/'a', 'iteration')), 0)
        before = self.csv.read_bytes()
        other = make_run(self.root/'b', 'sandbox')
        write(other/'run.json', {'completed_destinations': 3})  # audit now describes different bytes
        self.assertEqual(self.run_cli('append', other), 1)
        self.assertEqual(self.csv.read_bytes(), before)

    def test_profile_bytes_must_match_recorded_hash(self):
        run_dir = make_run(self.root, 'iteration')
        write(run_dir/'profile.yaml', PROFILE + '# edited\n')
        self.assertEqual(self.run_cli('append', run_dir), 1)
        self.assertFalse(self.csv.exists())

    def test_reingest_is_idempotent_and_conflict_fails_without_change(self):
        run_dir = make_run(self.root, 'iteration')
        self.assertEqual(self.run_cli('append', run_dir), 0)
        before = self.csv.read_bytes()
        self.assertEqual(self.run_cli('backfill', run_dir), 0)
        self.assertEqual(self.csv.read_bytes(), before)
        self.assertEqual(self.run_cli('append', run_dir, '--notes', 'different'), 1)
        self.assertEqual(self.csv.read_bytes(), before)

    def test_malformed_input_and_foreign_header_preserve_existing_bytes(self):
        self.assertEqual(self.run_cli('append', make_run(self.root, 'iteration')), 0)
        before = self.csv.read_bytes()
        broken = make_run(self.root/'b', 'sandbox')
        (broken/'provenance.json').write_text('{not json', encoding='utf-8')
        self.assertEqual(self.run_cli('append', broken), 1)
        self.assertEqual(self.csv.read_bytes(), before)
        foreign = self.root/'foreign.csv'
        foreign.write_text('run_id,other\nx,y\n', encoding='utf-8')
        valid = make_run(self.root/'c', 'iteration')
        self.assertEqual(ledger.main(['--ledger', str(foreign), 'append', str(valid)]), 1)
        self.assertEqual(foreign.read_text(encoding='utf-8'), 'run_id,other\nx,y\n')


if __name__ == '__main__':
    unittest.main()
