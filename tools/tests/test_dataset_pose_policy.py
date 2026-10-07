"""Dataset pose-provenance admission: kinds, flags, whole-group exclusion and counts (synthetic fixtures)."""

import gzip
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'learning'))
from build_dataset import build_corridor_rows, build_rows, main  # noqa: E402
from dataset_policy import (DATASET_ROW_UNLABELLED, PosePolicy, admit_group, filter_rows,  # noqa: E402
                            load_snapshot_provenance, row_provenance)

POSE = [.5, .2, .5]
AHEAD = [.7, .3, .55]
KINDS = ('measured', 'predicted', 'unknown_legacy', 'malformed', 'unavailable')
POLICIES = [PosePolicy(allow_predicted=p, allow_unknown_legacy=u) for p, u in itertools.product((False, True), repeat=2)]


def compensation(enabled, applied, measured, planning):
    return dict(latency_compensation=dict(enabled=enabled, applied=applied, measured_pose=measured,
                                          planning_pose=planning))


def snapshot_for(kind, costmap=False):
    """A schema-1 snapshot payload of the requested provenance kind (None for unavailable)."""
    planning = AHEAD if kind == 'predicted' else POSE
    inputs = dict(robot_xy=planning[:2], robot_yaw=planning[2], destination=[1.8, .2])
    if costmap:
        inputs.update(origin=[0., -1.], resolution=.1, width=20, height=20, costs=[0]*400)
    metadata = {'measured': compensation(False, False, POSE, POSE),
                'predicted': compensation(True, True, POSE, AHEAD),
                'unknown_legacy': {},
                'malformed': compensation(False, True, POSE, POSE)}.get(kind)
    return None if kind == 'unavailable' else dict(schema_version=1, input=inputs, metadata=metadata)


def write_gz(path, payload):
    with gzip.open(path, 'wt', encoding='utf-8') as stream:
        json.dump(payload, stream)


def write_jsonl(path, records):
    Path(path).write_text(''.join(json.dumps(r)+'\n' for r in records))


def route_fixture(directory, kinds, single=()):
    """One labelled route decision per kind (index = position+1); `single` indices have only the grid candidate."""
    outcomes, labels = [], []
    for index, kind in enumerate(kinds, 1):
        candidates = [dict(source='grid', endpoint=[5., 0.], features=dict(score=1., min_lethal_clearance_m=.4))]
        labelled = [dict(source='grid', endpoint=[5., 0.], teacher_cost_m=12.25)]
        if index not in single:
            candidates.append(dict(source='route_alt', endpoint=[5., 2.], distinct_by='hazard_side',
                                   features=dict(score=1.5, min_lethal_clearance_m=1.2)))
            labelled.append(dict(source='route_alt', endpoint=[5., 2.], teacher_cost_m=11.125))
        outcomes.append(dict(schema_version=2, index=index, destination_index=0, candidates=candidates))
        labels.append(dict(index=index, candidates=labelled))
        payload = snapshot_for(kind)
        if payload is not None:
            write_gz(Path(directory)/f'{index:05d}.json.gz', payload)
    write_jsonl(Path(directory)/'outcomes.jsonl', outcomes)
    write_jsonl(Path(directory)/'labels.jsonl', labels)
    return Path(directory)/'outcomes.jsonl', Path(directory)/'labels.jsonl'


def corridor_fixture(directory, kinds):
    outcomes, labels = [], []
    for index, kind in enumerate(kinds, 1):
        candidates = [dict(source='corridor', endpoint=[1.5, -.2, 0.], score=.2, features=dict(confidence=.8, distance_m=1.)),
                      dict(source='corridor', endpoint=[1.5, .4, 0.], score=.5, features=dict(confidence=.6, distance_m=1.2))]
        outcomes.append(dict(schema_version=2, index=index, destination_index=0, candidates=candidates,
                             plan=dict(source='observed_lane_corridor')))
        labels.append(dict(index=index, stamp_s=1., candidates=[
            dict(source='corridor', endpoint=c['endpoint'][:2], endpoint_cell='free', teacher_cost_m=10.+k)
            for k, c in enumerate(candidates)]))
        payload = snapshot_for(kind, costmap=True)
        if payload is not None:
            write_gz(Path(directory)/f'{index:05d}.json.gz', payload)
    write_jsonl(Path(directory)/'outcomes.jsonl', outcomes)
    write_jsonl(Path(directory)/'labels.jsonl', labels)
    return Path(directory)/'outcomes.jsonl', Path(directory)/'labels.jsonl'


def allowed(kind, policy):
    return kind == 'measured' or (kind == 'predicted' and policy.allow_predicted) \
        or (kind == 'unknown_legacy' and policy.allow_unknown_legacy)


class SnapshotProvenanceTests(unittest.TestCase):
    def classify(self, payload=None, raw=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'00001.json.gz'
            if raw is not None:
                path.write_bytes(raw)
            elif payload is not None:
                write_gz(path, payload)
            return load_snapshot_provenance(path)

    def test_every_kind_and_reason(self):
        cases = [
            (snapshot_for('measured'), ('measured', 'latency_compensation_not_applied')),
            (snapshot_for('predicted'), ('predicted', 'latency_compensation_applied')),
            # applied=true at zero motion: identical poses are still predicted, never measured.
            (dict(snapshot_for('measured'), metadata=compensation(True, True, POSE, POSE)),
             ('predicted', 'latency_compensation_applied')),
            (dict(schema_version=1, input=snapshot_for('measured')['input']), ('unknown_legacy', 'metadata_absent')),
            (snapshot_for('unknown_legacy'), ('unknown_legacy', 'latency_compensation_absent')),
            (snapshot_for('malformed'), ('malformed', 'applied_while_disabled')),
            (dict(snapshot_for('measured'), metadata=compensation(False, False, POSE, AHEAD)),
             ('malformed', 'planning_pose_input_mismatch')),
            (dict(snapshot_for('measured'), schema_version=2), ('unavailable', 'snapshot_invalid')),
            ([1, 2], ('unavailable', 'snapshot_invalid')),
            (dict(schema_version=1, input=[1, 2]), ('unavailable', 'snapshot_invalid')),
        ]
        for payload, expected in cases:
            with self.subTest(expected=expected):
                snapshot, provenance = self.classify(payload)
                self.assertEqual((provenance['kind'], provenance['reason']), expected)
                self.assertEqual(snapshot is None, expected[0] == 'unavailable')
        self.assertEqual(self.classify()[1], dict(kind='unavailable', reason='snapshot_missing'))
        self.assertEqual(self.classify(raw=b'not gzip')[1], dict(kind='unavailable', reason='snapshot_unreadable'))
        self.assertEqual(self.classify(raw=gzip.compress(b'{"schema_version": 1,'))[1],
                         dict(kind='unavailable', reason='snapshot_unreadable'))

    def test_flag_matrix(self):
        for policy, kind in itertools.product(POLICIES, KINDS):
            with self.subTest(policy=policy, kind=kind):
                admitted, reason = admit_group([dict(kind=kind, reason='r')], policy)
                self.assertEqual(admitted, allowed(kind, policy))
                self.assertEqual(reason, None if admitted else f'kind_not_allowed:{kind}')
        self.assertEqual(PosePolicy().to_dict(),
                         dict(allowed=['measured'], allow_predicted=False, allow_unknown_legacy=False))


class RouteBuilderTests(unittest.TestCase):
    def test_route_join_admits_only_allowed_kinds_with_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = route_fixture(directory, KINDS)
            for policy in POLICIES:
                with self.subTest(policy=policy):
                    rows, stats = build_rows(*paths, 'run', pose_policy=policy)
                    expected = [k for k in KINDS if allowed(k, policy)]
                    self.assertEqual(sorted({r['pose_source'] for r in rows}), sorted(expected))
                    self.assertEqual(stats['groups'], len(expected))
                    pose = stats['pose']
                    self.assertEqual(pose['members_by_kind'], {k: 1 for k in KINDS})
                    self.assertEqual(pose['admitted_groups'], len(expected))
                    self.assertEqual(pose['excluded_groups'],
                                     {f'kind_not_allowed:{k}': 1 for k in KINDS if k not in expected})
                    self.assertEqual(pose['excluded_rows'],
                                     {f'kind_not_allowed:{k}': 2 for k in KINDS if k not in expected})
                    self.assertEqual(pose['members_by_reason']['unavailable/snapshot_missing'], 1)

    def test_default_is_measured_only_and_values_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = route_fixture(directory, ('measured', 'predicted'))
            default, _ = build_rows(*paths, 'run')
            wide, _ = build_rows(*paths, 'run', pose_policy=PosePolicy(True, True))
        self.assertEqual([r['index'] for r in default], [1, 1])
        self.assertEqual(default, [r for r in wide if r['index'] == 1])
        grid, alt = default
        self.assertEqual(grid, dict(run='run', index=1, group='run:1', destination_index=0, source='grid',
            heuristic_choice=True, features=dict(score=1., min_lethal_clearance_m=.4), distinct_by=None,
            endpoint=[5., 0.], teacher_cost_m=12.25, regret_m=1.125, teacher_best=False, replayed=False,
            pose_source='measured', pose_reason='latency_compensation_not_applied'))
        self.assertEqual((alt['teacher_cost_m'], alt['regret_m'], alt['teacher_best']), (11.125, 0., True))
        predicted = [r for r in wide if r['index'] == 2]
        self.assertEqual([(r['pose_source'], r['pose_reason']) for r in predicted],
                         [('predicted', 'latency_compensation_applied')]*2)

    def test_admission_precedes_cardinality_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = route_fixture(directory, ('predicted', 'measured'), single=(1, 2))
            rows, stats = build_rows(*paths, 'run')
            self.assertEqual((rows, stats['groups']), ([], 0))
            self.assertEqual(stats['pose']['excluded_groups'], {'kind_not_allowed:predicted': 1})
            self.assertEqual(stats['pose']['excluded_rows'], {'kind_not_allowed:predicted': 1})
            self.assertEqual(stats['pose']['admitted_groups'], 1)  # then dropped as a single option


class CorridorBuilderTests(unittest.TestCase):
    def test_corridor_join_uses_admitted_snapshot_and_never_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = corridor_fixture(directory, ('measured', 'unknown_legacy', 'unavailable', 'malformed'))
            default, stats = build_corridor_rows(*paths, 'run')
            wide, wide_stats = build_corridor_rows(*paths, 'run', pose_policy=PosePolicy(True, True))
        self.assertEqual([r['index'] for r in default], [1, 1])
        self.assertEqual({r['pose_source'] for r in default}, {'measured'})
        self.assertEqual([r['index'] for r in wide], [1, 1, 2, 2])
        self.assertEqual([r['pose_reason'] for r in wide if r['index'] == 2], ['latency_compensation_absent']*2)
        self.assertEqual(default, [r for r in wide if r['index'] == 1])
        self.assertEqual(stats['pose']['excluded_groups'], {'kind_not_allowed:unavailable': 1,
            'kind_not_allowed:malformed': 1, 'kind_not_allowed:unknown_legacy': 1})
        self.assertEqual(wide_stats['pose']['excluded_groups'],
                         {'kind_not_allowed:unavailable': 1, 'kind_not_allowed:malformed': 1})
        self.assertEqual((stats['missing_snapshot'], wide_stats['missing_snapshot']), (0, 0))
        self.assertEqual([r['regret_m'] for r in default], [0., 1.])


class RowReaderTests(unittest.TestCase):
    def rows(self, group, *kinds):
        out = []
        for k, kind in enumerate(kinds):
            row = dict(group=group, regret_m=float(k))
            if kind is not None:
                row.update(pose_source=kind, pose_reason='r')
            out.append(row)
        return out

    def test_unlabelled_rows_are_unknown_legacy_and_need_the_opt_in(self):
        old = self.rows('a:1', None, None)
        self.assertEqual(row_provenance(old[0]), dict(kind='unknown_legacy', reason=DATASET_ROW_UNLABELLED))
        kept, counts = filter_rows(old, PosePolicy())
        self.assertEqual((kept, counts['excluded_groups']), ([], {'kind_not_allowed:unknown_legacy': 1}))
        kept, counts = filter_rows(old, PosePolicy(allow_unknown_legacy=True))
        self.assertEqual(kept, old)
        self.assertEqual(counts['members_by_reason'], {f'unknown_legacy/{DATASET_ROW_UNLABELLED}': 2})

    def test_whole_group_exclusion_mixed_kinds_and_no_replenishment(self):
        wide = PosePolicy(True, True)
        rows = (self.rows('g:1', 'measured', 'measured') + self.rows('g:2', 'measured', 'predicted')
                + self.rows('g:3', 'measured', 'malformed') + self.rows('g:4', 'measured', None)
                + self.rows('g:5', 'unknown_legacy', None) + self.rows('g:6', 'bogus', 'measured')
                + [dict(regret_m=0., pose_source='measured', pose_reason='r')])
        kept, counts = filter_rows(rows, wide)
        self.assertEqual(sorted({r['group'] for r in kept}), ['g:1', 'g:5'])
        self.assertEqual(len(kept), 4)
        self.assertEqual(counts['excluded_groups'], {'mixed_provenance': 2, 'kind_not_allowed:malformed': 2,
                                                     'group_absent': 1})
        kept, counts = filter_rows(rows, PosePolicy())
        self.assertEqual([r['group'] for r in kept], ['g:1', 'g:1'])
        self.assertEqual(counts['admitted_rows'], 2)


class SummaryTests(unittest.TestCase):
    def test_cli_summary_records_policy_and_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decisions = root/'runs'/'runA'/'decisions'
            decisions.mkdir(parents=True)
            outcomes, labels = route_fixture(decisions, KINDS)
            (root/'labels'/'runA').mkdir(parents=True)
            labels.replace(root/'labels'/'runA'/'labels.jsonl')
            out = root/'route.jsonl'
            self.assertEqual(main(['build', '--runs', 'runA', '--runs-root', str(root/'runs'), '--labels-root',
                                   str(root/'labels'), '--out', str(out), '--allow-predicted']), 0)
            summary = json.loads(out.with_suffix('.summary.json').read_text())
            rows = [json.loads(line) for line in out.read_text().splitlines()]
        self.assertEqual(summary['pose_policy'], PosePolicy(allow_predicted=True).to_dict())
        self.assertEqual(summary['pose']['admitted_groups'], 2)
        self.assertEqual(summary['pose']['excluded_groups'], {'kind_not_allowed:malformed': 1,
            'kind_not_allowed:unavailable': 1, 'kind_not_allowed:unknown_legacy': 1})
        self.assertEqual(summary['runs']['runA']['pose'], summary['pose'])
        self.assertEqual({r['pose_source'] for r in rows}, {'measured', 'predicted'})


if __name__ == '__main__':
    unittest.main()
