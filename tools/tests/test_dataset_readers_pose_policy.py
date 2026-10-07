"""Training and promotion readers share one pose policy (synthetic rows only; fitting is mocked)."""

import contextlib
import io
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'learning'))
import dataset_policy  # noqa: E402
from dataset_policy import PosePolicy, read_dataset_rows  # noqa: E402
import round_gate  # noqa: E402
import train_scorer  # noqa: E402

REASON = dict(measured='latency_compensation_not_applied', predicted='latency_compensation_applied',
              unknown_legacy='latency_compensation_absent', malformed='applied_while_disabled',
              unavailable='snapshot_missing')
KINDS = ('measured', 'predicted', 'unknown_legacy', 'malformed', 'unavailable', None)  # None: unlabelled legacy row
POLICIES = [PosePolicy(allow_predicted=p, allow_unknown_legacy=u) for p, u in itertools.product((False, True), repeat=2)]


def row(group, kind, heuristic, regret, run='run-a', score=.5):
    record = dict(run=run, index=int(group.split(':')[1]) if ':' in str(group) else 0, group=group,
                  source='grid' if heuristic else 'route_alt', heuristic_choice=heuristic,
                  features=dict(score=score, min_lethal_clearance_m=1.25+regret), endpoint=[1., 2.],
                  teacher_cost_m=10.+regret, regret_m=regret, teacher_best=regret == 0.)
    if kind is not None:
        record.update(pose_source=kind, pose_reason=REASON[kind])
    return record


def ranking_group(group, kind, run='run-a'):
    """A valid ranking group: one heuristic choice, two alternatives, all of one provenance."""
    return [row(group, kind, True, .75, run), row(group, kind, False, 0., run), row(group, kind, False, 1.5, run)]


def write_jsonl(path, rows):
    Path(path).write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')


def allowed(kind, policy):
    return kind == 'measured' or (kind == 'predicted' and policy.allow_predicted) \
        or (kind in ('unknown_legacy', None) and policy.allow_unknown_legacy)


class SharedReaderTests(unittest.TestCase):
    def test_both_public_readers_admit_the_same_groups_under_every_policy(self):
        rows = [r for k, kind in enumerate(KINDS) for r in ranking_group(f'run-a:{k}', kind)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'d.jsonl'
            write_jsonl(path, rows)
            for policy in POLICIES:
                with self.subTest(policy=policy):
                    expected = [r for k, kind in enumerate(KINDS) if allowed(kind, policy)
                                for r in rows if r['group'] == f'run-a:{k}']
                    train_rows = train_scorer.load_rows(path, policy)
                    gate_rows = round_gate.load_rows(path, policy)
                    self.assertEqual(train_rows, expected)
                    self.assertEqual(gate_rows, expected)
                    _, stats = read_dataset_rows(path, policy)
                    self.assertEqual(stats['pose_policy'], policy.to_dict())
                    self.assertEqual(stats['pre_pose'], dict(rows=18, groups=6))
                    self.assertEqual(stats['usable'], dict(rows=len(expected), groups=len(expected)//3))
            self.assertEqual(train_scorer.load_rows(path), round_gate.load_rows(path))  # default: measured only
            self.assertEqual({r['group'] for r in train_scorer.load_rows(path)}, {'run-a:0'})

    def test_legacy_unlabelled_rows_need_the_unknown_opt_in(self):
        rows = ranking_group('run-a:1', None)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'d.jsonl'
            write_jsonl(path, rows)
            default, stats = read_dataset_rows(path)
            opted, opted_stats = read_dataset_rows(path, PosePolicy(allow_unknown_legacy=True))
            predicted_only, _ = read_dataset_rows(path, PosePolicy(allow_predicted=True))
        self.assertEqual((default, predicted_only), ([], []))
        self.assertEqual(stats['pose']['excluded_groups'], {'kind_not_allowed:unknown_legacy': 1})
        self.assertEqual(opted, rows)
        self.assertEqual(opted_stats['pose']['provenance_by_reason'],
                         {f'unknown_legacy/{dataset_policy.DATASET_ROW_UNLABELLED}': 3})

    def test_one_forbidden_or_mixed_member_drops_an_otherwise_valid_group(self):
        forbidden = ranking_group('run-a:1', 'measured') + [row('run-a:1', 'predicted', False, 2.)]
        mixed = ranking_group('run-a:2', 'measured') + [row('run-a:2', None, False, 2.)]
        valid = ranking_group('run-a:3', 'measured')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'d.jsonl'
            write_jsonl(path, forbidden+mixed+valid)
            default, stats = read_dataset_rows(path)
            wide, wide_stats = read_dataset_rows(path, PosePolicy(True, True))
        # The three measured members of groups 1 and 2 would form valid ranking groups; nothing is replenished.
        self.assertEqual(default, valid)
        self.assertEqual(wide, valid)
        self.assertEqual(stats['pose']['excluded_groups'], {'kind_not_allowed:predicted': 1,
                                                            'kind_not_allowed:unknown_legacy': 1})
        self.assertEqual(wide_stats['pose']['excluded_groups'], {'mixed_provenance': 2})
        self.assertEqual(wide_stats['pose_admitted'], dict(rows=3, groups=1))

    def test_malformed_group_fields_are_excluded_and_neighbours_kept(self):
        bad = [dict(row('x', 'measured', True, 0.), group=value) for value in ([1, 2], {'a': 1}, None, 7)]
        bad.append({k: v for k, v in row('x', 'measured', True, 0.).items() if k != 'group'})
        first, last = ranking_group('run-a:1', 'measured'), ranking_group('run-a:2', 'measured')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'d.jsonl'
            write_jsonl(path, first+bad+last)
            rows, stats = read_dataset_rows(path, PosePolicy(True, True))
            self.assertEqual(train_scorer.load_rows(path), first+last)
        self.assertEqual(rows, first+last)
        self.assertEqual(stats['pose']['excluded_groups'], {'group_invalid': 5})
        self.assertEqual(stats['pre_pose'], dict(rows=11, groups=2))

    def test_values_are_unchanged_and_order_is_group_major(self):
        a, b = ranking_group('run-a:1', 'measured'), ranking_group('run-b:2', 'measured', run='run-b')
        interleaved = [a[0], b[0], a[1], b[1], a[2], b[2]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'d.jsonl'
            write_jsonl(path, interleaved)
            rows, _ = read_dataset_rows(path)
        self.assertEqual(rows, a+b)  # previous readers' order: groups by first appearance, rows in file order
        for got, want in zip(rows, a+b):
            self.assertEqual(json.dumps(got, sort_keys=True), json.dumps(want, sort_keys=True))

    def test_ranking_rule_runs_after_pose_admission_and_is_counted(self):
        single = [row('run-a:1', 'measured', True, 0.)]
        two_heuristics = [row('run-a:2', 'measured', True, 0.), row('run-a:2', 'measured', True, 1.)]
        no_heuristic = [row('run-a:3', 'measured', False, 0.), row('run-a:3', 'measured', False, 1.)]
        valid = ranking_group('run-a:4', 'measured')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'d.jsonl'
            write_jsonl(path, single+two_heuristics+no_heuristic+valid)
            rows, stats = read_dataset_rows(path)
        self.assertEqual(rows, valid)
        self.assertEqual(stats['pose_admitted'], dict(rows=8, groups=4))
        self.assertEqual(stats['ranking_excluded'], dict(rows=5, groups=3))
        self.assertEqual(stats['usable'], dict(rows=3, groups=1))

    def test_malformed_json_is_rejected_with_its_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'d.jsonl'
            for k, bad in enumerate(('{"group": "run-a:1",', '[1, 2]', '"text"')):
                text = ''.join(json.dumps(r)+'\n' for r in ranking_group('run-a:1', 'measured'))
                path.write_text(text+'\n'+bad+'\n', encoding='utf-8')
                for reader in (read_dataset_rows, train_scorer.load_rows, round_gate.load_rows):
                    with self.subTest(case=k, reader=reader.__module__), \
                            self.assertRaisesRegex(ValueError, r'd\.jsonl:5: '):
                        reader(path)


class TrainCliTests(unittest.TestCase):
    def run_main(self, argv):
        with contextlib.redirect_stdout(io.StringIO()):
            return train_scorer.main(argv)

    def test_flags_propagate_and_empty_report_is_written_without_fitting(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_jsonl(tmp/'d.jsonl', ranking_group('run-a:1', 'predicted') + ranking_group('run-a:2', 'malformed'))
            for flags, policy in (([], PosePolicy()), (['--allow-unknown-legacy'], PosePolicy(False, True))):
                with self.subTest(flags=flags), \
                        mock.patch.object(train_scorer, 'read_dataset_rows', wraps=read_dataset_rows) as reader, \
                        mock.patch.object(train_scorer, 'make_model') as fit, \
                        mock.patch.object(train_scorer, 'cross_validate') as cv:
                    status = self.run_main(['--dataset', str(tmp/'d.jsonl'), '--model-out', str(tmp/'m.json'),
                                            '--report-out', str(tmp/'r.json')] + flags)
                    self.assertEqual(status, 1)
                    self.assertEqual(reader.call_args.args[1], policy)
                    fit.assert_not_called()
                    cv.assert_not_called()
                    report = json.loads((tmp/'r.json').read_text())
                    self.assertEqual(report['pose_policy'], policy.to_dict())
                    self.assertEqual((report['rows'], report['dataset_admission']['usable']['rows']), (0, 0))
                    self.assertEqual(report['dataset_admission']['pre_pose'], dict(rows=6, groups=2))
                    self.assertIn('error', report)
                    self.assertFalse((tmp/'m.json').exists())

    def test_predicted_flag_admits_rows_to_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_jsonl(tmp/'d.jsonl', ranking_group('run-a:1', 'predicted'))
            with mock.patch.object(train_scorer, 'cross_validate', side_effect=ValueError('cv mocked')), \
                    mock.patch.object(train_scorer, 'make_model', side_effect=RuntimeError('fit reached')):
                with self.assertRaisesRegex(RuntimeError, 'fit reached'):
                    self.run_main(['--dataset', str(tmp/'d.jsonl'), '--model-out', str(tmp/'m.json'),
                                   '--allow-predicted'])

    def test_malformed_dataset_report_is_written_and_nothing_fitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp/'d.jsonl').write_text('{"group": \n', encoding='utf-8')
            with mock.patch.object(train_scorer, 'make_model') as fit:
                status = self.run_main(['--dataset', str(tmp/'d.jsonl'), '--model-out', str(tmp/'m.json'),
                                        '--report-out', str(tmp/'r.json')])
            fit.assert_not_called()
            report = json.loads((tmp/'r.json').read_text())
        self.assertEqual(status, 2)
        self.assertIn('d.jsonl:1: malformed dataset JSON', report['error'])
        self.assertEqual(report['pose_policy'], PosePolicy().to_dict())


def fake_cv(rows, new_recipe, spec, repo=None, model_factory=None):
    return dict(new=np.zeros(len(rows)), current=None, fold=np.zeros(len(rows), dtype=int), folds=1, courses=2,
                course={r['run']: r['run'] for r in rows})


class GateTests(unittest.TestCase):
    def write(self, tmp, rows):
        write_jsonl(tmp/'d.jsonl', rows)
        (tmp/'new.json').write_text(json.dumps(dict(features=['score', 'min_lethal_clearance_m'])))
        return tmp/'d.jsonl', tmp/'new.json'

    def test_direct_gate_applies_the_given_policy_and_reports_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset, new = self.write(Path(tmp), ranking_group('run-a:1', 'predicted')
                                      + ranking_group('run-b:2', 'measured', run='run-b'))
            with mock.patch.object(round_gate, 'cross_validate', side_effect=fake_cv) as cv:
                default = round_gate.gate(dataset, new, repo=Path(tmp))
                wide = round_gate.gate(dataset, new, repo=Path(tmp), pose_policy=PosePolicy(allow_predicted=True))
            self.assertEqual([len(call.args[0]) for call in cv.call_args_list], [3, 6])
        self.assertEqual(default['pose_policy'], PosePolicy().to_dict())
        self.assertEqual(wide['pose_policy'], PosePolicy(allow_predicted=True).to_dict())
        self.assertEqual((default['rows'], wide['rows']), (3, 6))
        self.assertEqual(default['dataset_admission']['pose']['excluded_groups'], {'kind_not_allowed:predicted': 1})
        self.assertEqual(wide['dataset_admission']['usable'], dict(rows=6, groups=2))

    def test_empty_after_admission_is_never_promotable(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset, new = self.write(Path(tmp), ranking_group('run-a:1', 'unavailable')
                                      + ranking_group('run-a:2', 'malformed'))
            with mock.patch.object(round_gate, 'cross_validate') as cv:
                report = round_gate.gate(dataset, new, repo=Path(tmp), pose_policy=PosePolicy(True, True))
            cv.assert_not_called()
        self.assertFalse(report['decision']['promote'])
        self.assertEqual(report['rows'], 0)
        self.assertEqual(report['pose_policy'], PosePolicy(True, True).to_dict())
        self.assertEqual(report['dataset_admission']['pre_pose'], dict(rows=6, groups=2))
        self.assertEqual(report['dataset_admission']['pose_admitted'], dict(rows=0, groups=0))

    def test_cli_flags_reach_the_gate_and_out_is_written_for_empty_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            dataset, new = self.write(tmp, [row('run-a:1', None, True, 0.)])  # admitted, then a single member
            argv = ['--dataset', str(dataset), '--new', str(new), '--out', str(tmp/'g.json')]
            with contextlib.redirect_stdout(io.StringIO()), \
                    mock.patch.object(round_gate, 'gate', wraps=round_gate.gate) as gate:
                status = round_gate.main(argv + ['--allow-unknown-legacy', '--allow-predicted'])
            self.assertEqual(gate.call_args.kwargs['pose_policy'], PosePolicy(True, True))
            report = json.loads((tmp/'g.json').read_text())
            self.assertEqual(status, 0)
            self.assertFalse(report['decision']['promote'])
            self.assertEqual(report['dataset_admission']['pose_admitted'], dict(rows=1, groups=1))
            self.assertEqual(report['dataset_admission']['ranking_excluded'], dict(rows=1, groups=1))
            dataset.write_text('not json\n', encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                status = round_gate.main(argv)
            report = json.loads((tmp/'g.json').read_text())
        self.assertEqual(status, 2)
        self.assertFalse(report['decision']['promote'])
        self.assertIn('d.jsonl:1: malformed dataset JSON', report['error'])
        self.assertEqual(report['pose_policy'], PosePolicy().to_dict())


if __name__ == '__main__':
    unittest.main()
