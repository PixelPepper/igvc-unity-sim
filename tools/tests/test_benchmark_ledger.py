"""Benchmark ledger: both run layouts, verbatim verdicts, provenance binding, locking and ledger safety."""

import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import benchmark_ledger as ledger  # noqa: E402

PROFILE = 'controller_server:\n  ros__parameters:\n    FollowPath:\n      plugin: nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController\n'
# Real sim_status shape: the seed appears only inside a course label.
UNIQUE = itertools.count()  # distinct run bytes per fixture
SIM_STATUS = 'r3a_kinematic_oracle run=0 course=seed-2027 course_hash=1126a943 terrain_support=True'


def write(path, value):
    path.write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_run(root, layout, passed=True, audit_names=('audit.json',), elapsed=None):
    run_dir = Path(root) / '2026-10-01' / f'{layout}-run'
    run_dir.mkdir(parents=True)
    run_sha = write(run_dir/'run.json', {
        'completed_destinations': 6, 'total_destinations': 6,
        'elapsed_wall_s': 363.37 + next(UNIQUE) if elapsed is None else elapsed,
        'requested_speed_mps': 0.6, 'recoveries': [{'actual_distance_m': .6}], 'sim_status': SIM_STATUS})
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

    def run_cli(self, command, *args):
        return ledger.main([command, *map(str, args), '--ledger', str(self.csv), '--lock-timeout', '0.3'])

    def rows(self):
        return ledger.read_ledger(self.csv)[1]

    def test_iteration_layout_copies_recorded_provenance_and_keeps_course_label_out_of_seed(self):
        self.assertEqual(self.run_cli('append', make_run(self.root, 'iteration')), 0)
        row, = self.rows()
        self.assertEqual((row['run_id'], row['source'], row['git_sha'], row['player_sha'], row['seed']),
                         ('2026-10-01/iteration-run', 'iteration', 'ac765e9', 'abc', ''))
        self.assertEqual((row['controller'], row['destinations'], row['backups'], row['audit_passed']),
                         ('rpp', '6/6', '1', 'true'))
        self.assertEqual((row['audit_binding'], row['profile_binding']), ('run_sha256_matched', 'matched'))

    def test_sandbox_layout_leaves_unrecorded_provenance_empty(self):
        self.assertEqual(self.run_cli('append', make_run(self.root, 'sandbox', passed=False)), 0)
        row, = self.rows()
        self.assertEqual((row['git_sha'], row['player_sha'], row['controller'], row['audit_passed']),
                         ('', '', 'mppi', 'false'))

    def test_ambiguous_audits_require_an_explicit_choice(self):
        run_dir = make_run(self.root, 'sandbox', audit_names=('handoff-audit.json', 'claude-audit.json'))
        self.assertEqual(self.run_cli('append', run_dir), 1)
        self.assertFalse(self.csv.exists())
        self.assertEqual(self.run_cli('append', run_dir, '--audit', run_dir/'handoff-audit.json'), 0)

    def test_unknown_verdicts_and_unverifiable_profile_are_explicit(self):
        run_dir = make_run(self.root, 'iteration', passed='yes')
        (run_dir/'profile.yaml').unlink()
        self.assertEqual(self.run_cli('append', run_dir), 0)
        row, = self.rows()
        self.assertEqual((row['audit_passed'], row['profile_binding']), ('unknown', 'unverified_profile_missing'))
        unbound = make_run(self.root/'b', 'sandbox')
        audit = json.loads((unbound/'audit.json').read_text())
        del audit['run_sha256']
        write(unbound/'audit.json', audit)
        self.assertEqual(self.run_cli('append', unbound), 0)
        self.assertEqual((self.rows()[1]['audit_passed'], self.rows()[1]['audit_binding'],
                          self.rows()[1]['return_distance_m']), ('unknown', 'unbound_no_run_sha256', ''))

    def test_bad_evidence_fails_without_touching_the_ledger(self):
        self.assertEqual(self.run_cli('append', make_run(self.root/'a', 'iteration')), 0)
        before = self.csv.read_bytes()
        foreign = make_run(self.root/'b', 'sandbox')
        write(foreign/'run.json', {'completed_destinations': 3})       # audit describes other bytes
        edited = make_run(self.root/'c', 'iteration')
        write(edited/'profile.yaml', PROFILE + '# edited\n')           # profile hash mismatch
        listy = make_run(self.root/'d', 'sandbox')
        (listy/'provenance.json').write_text('[]', encoding='utf-8')   # JSON but not an object
        for run_dir in (foreign, edited, listy):
            self.assertEqual(self.run_cli('append', run_dir), 1, run_dir)
        self.assertEqual(self.run_cli('append', make_run(self.root/'e', 'iteration'), '--run-id', '../x'), 1)
        self.assertEqual(self.csv.read_bytes(), before)

    def test_backfill_is_all_or_nothing(self):
        good, bad = make_run(self.root/'a', 'iteration'), make_run(self.root/'b', 'sandbox')
        (bad/'run.json').write_text('{not json', encoding='utf-8')
        self.assertEqual(self.run_cli('backfill', good, bad), 1)
        self.assertFalse(self.csv.exists())

    def test_idempotent_reingest_conflicts_and_same_bytes_under_new_id(self):
        run_dir = make_run(self.root, 'iteration')
        self.assertEqual(self.run_cli('append', run_dir), 0)
        before = self.csv.read_bytes()
        self.assertEqual(self.run_cli('backfill', run_dir / '.' / '..' / run_dir.name), 0)  # dot path, same id
        self.assertEqual(self.run_cli('append', run_dir, '--notes', 'different'), 1)
        self.assertEqual(self.run_cli('append', run_dir, '--run-id', 'renamed'), 1)
        self.assertEqual(self.csv.read_bytes(), before)

    def test_existing_bytes_and_line_endings_are_preserved_and_corruption_rejected(self):
        self.assertEqual(self.run_cli('append', make_run(self.root/'a', 'iteration')), 0)
        crlf = self.csv.read_bytes().replace(b'\n', b'\r\n')
        self.csv.write_bytes(crlf)
        self.assertEqual(self.run_cli('append', make_run(self.root/'b', 'sandbox')), 0)
        after = self.csv.read_bytes()
        self.assertTrue(after.startswith(crlf))
        self.assertNotIn(b'\n', after.replace(b'\r\n', b''))
        self.csv.write_bytes(after + b'only,three,fields\r\n')
        corrupted = self.csv.read_bytes()
        self.assertEqual(self.run_cli('append', make_run(self.root/'c', 'iteration')), 1)
        self.assertEqual(self.csv.read_bytes(), corrupted)

    def test_foreign_lock_is_waited_on_then_reported_never_broken(self):
        lock = self.csv.with_name(self.csv.name + '.lock')
        lock.write_text('pid=other\n', encoding='utf-8')
        self.assertEqual(self.run_cli('append', make_run(self.root, 'iteration')), 1)
        self.assertEqual(lock.read_text(encoding='utf-8'), 'pid=other\n')
        self.assertFalse(self.csv.exists())

    def test_concurrent_processes_never_lose_rows(self):
        runs = [make_run(self.root/str(i), 'sandbox', elapsed=300.0+i) for i in range(6)]
        procs = [subprocess.Popen([sys.executable, str(TOOLS/'benchmark_ledger.py'), 'append', str(run),
                                   '--run-id', f'run-{i}', '--ledger', str(self.csv), '--lock-timeout', '20'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) for i, run in enumerate(runs)]
        codes = [proc.wait(timeout=60) for proc in procs]
        self.assertEqual(codes, [0]*6, [proc.stderr.read() for proc in procs])
        self.assertEqual(sorted(row['run_id'] for row in self.rows()), [f'run-{i}' for i in range(6)])
        self.assertFalse(self.csv.with_name(self.csv.name + '.lock').exists())


if __name__ == '__main__':
    unittest.main()
