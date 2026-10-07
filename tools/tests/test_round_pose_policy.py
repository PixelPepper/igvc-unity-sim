"""run_round carries one explicit pose policy through build, train and gate, and into the cache identity.

Synthetic only: a recording command runner stands in for build_dataset/train_scorer/the teacher, and
round_gate.gate is mocked except where its real empty-dataset path is the point of the test.
"""

import argparse
import contextlib
import gzip
import io
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'learning'))
from dataset_policy import PosePolicy  # noqa: E402
import round_gate  # noqa: E402
import run_round  # noqa: E402

RUNS = ('run-1', 'run-2')
POLICIES = [PosePolicy(allow_predicted=p, allow_unknown_legacy=u) for p, u in itertools.product((False, True), repeat=2)]
MEASURED = dict(pose_source='measured', pose_reason='latency_compensation_not_applied')


def args(**overrides):
    base = dict(round=1, models_dir=None, from_existing=None, no_promote=False, force=[], dry_run=False,
                fraction=.5, jobs=2, instances=2, allow_predicted=False, allow_unknown_legacy=False)
    return argparse.Namespace(**dict(base, **overrides))


def flags(policy):
    return (['--allow-predicted'] if policy.allow_predicted else []) \
        + (['--allow-unknown-legacy'] if policy.allow_unknown_legacy else [])


def ranking_rows(run, pose=MEASURED):
    rows = []
    for index in range(3):
        for k in range(3):
            rows.append(dict(run=run, index=index, group=f'{run}:{index}', source='grid' if k == 0 else 'route_alt',
                             heuristic_choice=k == 0, features=dict(score=.1*k), teacher_cost_m=10.+k,
                             regret_m=float(k), teacher_best=k == 0, **pose))
    return rows


class Runner:
    """Records argv; writes deterministic dataset/model/report bytes like the real tools would."""

    def __init__(self, root, dataset_rows=None):
        self.root, self.calls, self.dataset_rows = Path(root), [], dataset_rows

    def __call__(self, argv, log=None):
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        joined = ' '.join(argv)
        if 'build_dataset.py' in joined and 'build' in argv:
            out = Path(argv[argv.index('--out') + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            rows = self.dataset_rows if self.dataset_rows is not None else [r for n in RUNS for r in ranking_rows(n)]
            out.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
            out.with_suffix('.summary.json').write_text(json.dumps(dict(rows=len(rows), groups=len(rows)//3)))
        elif 'train_scorer.py' in joined:
            model = Path(argv[argv.index('--model-out') + 1])
            model.parent.mkdir(parents=True, exist_ok=True)
            model.write_text(json.dumps(dict(features=['score'])), encoding='utf-8')
            Path(argv[argv.index('--report-out') + 1]).write_text('{}', encoding='utf-8')
        elif argv[0].startswith('powershell'):
            pass  # the teacher is never run here
        else:
            raise AssertionError(joined)

    def tool_calls(self, script):
        return [c for c in self.calls if any(script in a for a in c)]


def gate_report(promote=False):
    decision = dict(promote=promote, weight=1. if promote else None, reasons=['mock'], recommended_weight=1.)
    return dict(decision=decision, mode='first', notes=[], overall=dict(new={}, heuristic={}), hook={},
                new_vs_heuristic={}, new_recipe=dict(features=['score']), new_sha256='x', current_sha256=None)


def write_run(root, name, label_record=None, snapshot=b'snapshot-a'):
    decisions = Path(root) / f'artifacts/learning/replayed/{name}/decisions'
    decisions.mkdir(parents=True, exist_ok=True)
    (decisions / 'outcomes.jsonl').write_text('{"schema_version": 2, "index": 1}\n', encoding='utf-8')
    (decisions / '00001.json.gz').write_bytes(gzip.compress(snapshot, mtime=0))
    labels = Path(root) / f'artifacts/learning/labels-replayed/{name}'
    labels.mkdir(parents=True, exist_ok=True)
    (labels / 'labels.jsonl').write_text(json.dumps(label_record or dict(index=1)) + '\n', encoding='utf-8')


class RoundPolicyBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in RUNS:
            write_run(self.root, name)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, runner, **overrides):
        round_ = run_round.Round(args(**overrides), root=self.root, runner=runner,
                                 kind_support=dict(build=True, train=True))
        round_.log = lambda text: None
        round_.state['data_runs'] = list(RUNS)
        return round_

    def run_steps(self, runner, promote=False, **overrides):
        """build -> train -> gate with a mocked gate; returns (round, records, gate mock)."""
        round_ = self.make(runner, **overrides)
        with mock.patch.object(round_gate, 'gate', return_value=gate_report(promote)) as gate:
            built = round_.build()
            trained = round_.train(built)
            gated = round_.gate(trained)
        return round_, dict(built=built, trained=trained, gated=gated), gate


class PropagationTests(RoundPolicyBase):
    def test_exact_flags_reach_build_train_and_direct_gate_for_both_kinds(self):
        for policy in POLICIES:
            with self.subTest(policy=policy):
                self.tearDown()
                self.setUp()
                runner = Runner(self.root)
                _, records, gate = self.run_steps(runner, allow_predicted=policy.allow_predicted,
                                                  allow_unknown_legacy=policy.allow_unknown_legacy)
                builds, trains = runner.tool_calls('build_dataset.py'), runner.tool_calls('train_scorer.py')
                self.assertEqual(len(builds), 2)
                self.assertEqual(len(trains), 2)
                for argv in builds + trains:
                    self.assertEqual([a for a in argv if a.startswith('--allow-')], flags(policy))
                route, corridor = builds
                self.assertNotIn('--corridor-label', route)
                self.assertEqual(corridor[corridor.index('--corridor-label') + 1], 'straight-v1')
                self.assertEqual([c.kwargs['pose_policy'] for c in gate.call_args_list], [policy, policy])
                for step in ('built', 'trained', 'gated'):
                    for kind in ('route', 'corridor'):
                        self.assertEqual(records[step][kind]['pose_policy'], policy.to_dict())
                        self.assertEqual(records[step][kind]['policy_cache'], run_round.POLICY_CACHE)

    def test_default_never_widens(self):
        runner = Runner(self.root)
        _, _, gate = self.run_steps(runner)
        self.assertFalse(any(a.startswith('--allow-') for c in runner.calls for a in c))
        self.assertEqual(gate.call_args.kwargs['pose_policy'], PosePolicy())
        parsed = run_round.parse_args(['--round', '1', '--allow-predicted'])
        self.assertEqual(run_round.Round(parsed, root=self.root).pose_policy, PosePolicy(allow_predicted=True))
        self.assertEqual(run_round.Round(run_round.parse_args(['--round', '1']), root=self.root).pose_policy,
                         PosePolicy())

    def test_label_command_names_the_legacy_mode_explicitly(self):
        script = self.make(Runner(self.root)).label_command(['run-1', 'run-2'])[-1]
        self.assertEqual(script.count('--corridor-label straight-v1'), 2)
        self.assertNotIn('path-v3', script)


class CacheIdentityTests(RoundPolicyBase):
    def test_same_policy_resumes_without_work(self):
        self.run_steps(Runner(self.root))
        runner = Runner(self.root)
        _, _, gate = self.run_steps(runner)
        self.assertEqual(runner.calls, [])
        gate.assert_not_called()

    def test_changed_policy_reevaluates_even_with_identical_bytes(self):
        self.run_steps(Runner(self.root))
        runner = Runner(self.root)
        _, _, gate = self.run_steps(runner, allow_predicted=True)
        self.assertEqual((len(runner.tool_calls('build_dataset.py')), len(runner.tool_calls('train_scorer.py'))),
                         (2, 2))
        self.assertEqual(gate.call_count, 2)

    def test_changed_policy_bypasses_imported_and_already_promoted_shortcuts(self):
        round_, _, _ = self.run_steps(Runner(self.root), promote=True)
        manifest = json.loads((round_.models_dir / 'manifest.json').read_text())
        self.assertEqual(set(manifest['models']), {'route', 'corridor'})
        # Same policy: the promoted model's gate is skipped.
        runner = Runner(self.root)
        _, _, gate = self.run_steps(runner, promote=True)
        gate.assert_not_called()
        # An 'imported' record never stands in for build/train/gate identity.
        state_path = round_.dir / 'state.json'
        state = json.loads(state_path.read_text())
        for name in ('build_route', 'train_route', 'gate_route'):
            state['steps'][name].update(status='imported', input_hash='legacy')
        state_path.write_text(json.dumps(state))
        runner = Runner(self.root)
        _, _, gate = self.run_steps(runner, promote=True)
        self.assertEqual(len(runner.tool_calls('build_dataset.py')), 1)  # route only; corridor still valid
        # Changed policy: re-gated although the new model is already the promoted one.
        runner = Runner(self.root)
        _, _, gate = self.run_steps(runner, promote=True, allow_unknown_legacy=True)
        self.assertEqual(gate.call_count, 2)
        self.assertEqual(len(runner.tool_calls('build_dataset.py')), 2)

    def test_snapshot_bytes_changed_with_same_size_and_mtime_invalidate_build(self):
        self.run_steps(Runner(self.root))
        snapshot = self.root / 'artifacts/learning/replayed/run-1/decisions/00001.json.gz'
        stat = snapshot.stat()
        snapshot.write_bytes(gzip.compress(b'snapshot-b', mtime=0))  # same length, different content
        os.utime(snapshot, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(snapshot.stat().st_size, stat.st_size)
        runner = Runner(self.root)
        self.run_steps(runner)
        self.assertEqual(len(runner.tool_calls('build_dataset.py')), 2)

    def test_snapshot_added_or_removed_invalidates_build(self):
        self.run_steps(Runner(self.root))
        extra = self.root / 'artifacts/learning/replayed/run-2/decisions/00002.json.gz'
        extra.write_bytes(gzip.compress(b'snapshot-c', mtime=0))
        runner = Runner(self.root)
        self.run_steps(runner)
        self.assertEqual(len(runner.tool_calls('build_dataset.py')), 2)
        extra.unlink()
        runner = Runner(self.root)
        self.run_steps(runner)
        self.assertEqual(len(runner.tool_calls('build_dataset.py')), 2)

    def test_mutated_outputs_are_not_reused(self):
        round_, _, _ = self.run_steps(Runner(self.root))
        dataset = round_.dir / 'dataset/route_candidates.jsonl'
        dataset.write_text(dataset.read_text() + '\n', encoding='utf-8')
        runner = Runner(self.root)
        self.run_steps(runner)
        self.assertEqual([c[c.index('--out') + 1].endswith('route_candidates.jsonl')
                          for c in runner.tool_calls('build_dataset.py')], [True])
        model = round_.dir / 'models/corridor_scorer.json'
        model.write_text('{"features": ["other"]}', encoding='utf-8')
        runner = Runner(self.root)
        _, _, gate = self.run_steps(runner)
        self.assertEqual(len(runner.tool_calls('train_scorer.py')), 1)
        gate.assert_not_called()  # retraining restored the exact bytes that were gated
        report = round_.dir / 'gate/route.json'
        report.write_text('{}', encoding='utf-8')
        runner = Runner(self.root)
        _, _, gate = self.run_steps(runner)
        self.assertEqual(runner.calls, [])
        self.assertEqual(gate.call_count, 1)  # a changed gate report is re-evaluated, not reused


class LabelModeTests(RoundPolicyBase):
    def assert_rejected_unchanged(self, record=None, raw=None):
        path = self.root / 'artifacts/learning/labels-replayed/run-2/labels.jsonl'
        if raw is not None:
            path.write_text(raw, encoding='utf-8')
        else:
            path.write_text(json.dumps(record) + '\n', encoding='utf-8')
        before = path.read_bytes()
        runner = Runner(self.root)
        with self.assertRaisesRegex(SystemExit, 'not overwritten'):
            self.run_steps(runner)
        self.assertEqual(runner.calls, [])
        self.assertEqual(path.read_bytes(), before)
        # The label step fails closed the same way and never launches the teacher over it.
        round_ = self.make(runner)
        round_.state['steps']['replay'] = dict(status='done', replayed_runs=list(RUNS))
        with self.assertRaisesRegex(SystemExit, 'not overwritten'):
            round_.label()
        self.assertEqual(runner.calls, [])
        self.assertEqual(path.read_bytes(), before)

    def test_path_v2_labels_fail_closed(self):
        self.assert_rejected_unchanged(dict(index=1, corridor_label='path-v2'))

    def test_path_v3_labels_are_mismatched(self):
        self.assert_rejected_unchanged(dict(index=1, corridor_label='path-v3'))

    def test_malformed_labels_fail_closed(self):
        self.assert_rejected_unchanged(raw='{"index": 1,\n')

    def test_explicit_straight_v1_labels_are_valid(self):
        write_run(self.root, 'run-2', dict(index=1, corridor_label='straight-v1'))
        runner = Runner(self.root)
        self.run_steps(runner)
        self.assertEqual(len(runner.tool_calls('build_dataset.py')), 2)


class OutcomeTests(RoundPolicyBase):
    def test_empty_after_pose_admission_is_recorded_and_never_promoted(self):
        predicted = dict(pose_source='predicted', pose_reason='latency_compensation_applied')
        runner = Runner(self.root, dataset_rows=[r for n in RUNS for r in ranking_rows(n, predicted)])
        round_ = self.make(runner)
        built = round_.build()
        trained = round_.train(built)
        gated = round_.gate(trained)  # the real gate: measured-only leaves no usable rows
        for kind in ('route', 'corridor'):
            self.assertFalse(gated[kind]['promoted'])
            self.assertFalse(gated[kind]['decision']['promote'])
            self.assertEqual(gated[kind]['pose_policy'], PosePolicy().to_dict())
            self.assertEqual(gated[kind]['dataset_admission']['usable'], dict(rows=0, groups=0))
            report = json.loads((round_.dir / f'gate/{kind}.json').read_text())
            self.assertEqual(report['pose_policy'], PosePolicy().to_dict())
        self.assertFalse((round_.models_dir / 'manifest.json').exists())

    def test_failed_training_is_recorded_with_policy_and_not_reused(self):
        def failing(argv, log=None):
            if any('train_scorer.py' in str(a) for a in argv):
                raise SystemExit('Command failed (1)')
            Runner(self.root)(argv, log)
        round_ = self.make(failing, allow_predicted=True)
        built = round_.build()
        with self.assertRaises(SystemExit):
            round_.train(built)
        record = json.loads((round_.dir / 'state.json').read_text())['steps']['train_route']
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['pose_policy'], PosePolicy(allow_predicted=True).to_dict())
        self.assertTrue(record['report'].endswith('models/route_scorer.report.json'))
        runner = Runner(self.root)
        self.run_steps(runner, allow_predicted=True)
        self.assertEqual(len(runner.tool_calls('train_scorer.py')), 2)

    def test_dry_run_writes_nothing(self):
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*'))
        runner = Runner(self.root)
        round_ = self.make(runner, dry_run=True, allow_predicted=True)
        lines = []
        round_.log = lines.append
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(round_gate, 'gate') as gate:
            built = round_.build()
            round_.gate(round_.train(built))
        gate.assert_not_called()
        self.assertEqual(runner.calls, [])
        self.assertEqual(sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*')), before)
        self.assertTrue(any('--allow-predicted' in line and 'build_dataset.py' in line for line in lines))


if __name__ == '__main__':
    unittest.main()
