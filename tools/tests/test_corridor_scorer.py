"""Learned lane-corridor re-rank: exact weight-0 identity, gates, fallback, data parity."""

import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'learning'))
import observed_navigation  # noqa: E402
from lane_corridor_policy import CORRIDOR_FEATURES, corridor_feature_rows, propose_lane_corridor  # noqa: E402
from navigation_decisions import outcome_candidates  # noqa: E402
from build_dataset import build_corridor_rows  # noqa: E402
from learned_scorer import LearnedScorer, SCHEMA  # noqa: E402


def stripe(y, start=2., end=12., step=.2):
    x = np.arange(start, end+step/2, step)
    return np.column_stack((x, np.full_like(x, y)))


# Three parallel lines: two accepted corridors (below and above the middle line).
POINTS = np.vstack((stripe(-3), stripe(0), stripe(3)))
ROBOT, YAW, GOAL = [0., -1.2], 0., [20., -1.]
# Explicit measured pose provenance: dataset builders admit only measured snapshots by default.
MEASURED = dict(latency_compensation=dict(enabled=False, applied=False, measured_pose=[*ROBOT, YAW],
                                          planning_pose=[*ROBOT, YAW]))
ORIGIN, RES, W, H = [-5., -10.], .1, 300, 200


def costmap(barrier_y=None):
    costs = [0]*(W*H)
    if barrier_y is not None:  # an observed obstacle row inside one corridor
        iy = int((barrier_y-ORIGIN[1])/RES)
        for ix in range(int((4.-ORIGIN[0])/RES), int((9.-ORIGIN[0])/RES)):
            costs[iy*W+ix] = 100
    return (ORIGIN, RES, W, H, costs)


class PreferOther:
    """Stub corridor scorer: predicts high regret for the heuristic's pick."""
    decision = 'corridor'

    def score(self, rows):
        return [10. if row['score_rank'] == 0 else 0. for row in rows]


class Broken:
    decision = 'corridor'

    def score(self, rows):
        raise RuntimeError('boom')


def propose(**kwargs):
    diagnostics = {}
    result = propose_lane_corridor(POINTS, ROBOT, YAW, GOAL, min_width=1.2, lookahead=7.,
                                   diagnostics=diagnostics, **kwargs)
    return result, diagnostics


class CorridorRerankTests(unittest.TestCase):
    def test_scene_has_two_accepted_corridors(self):
        _, diagnostics = propose()
        self.assertEqual(len(diagnostics['accepted_candidates']), 2)

    def test_weight_zero_or_no_scorer_is_exactly_the_heuristic(self):
        baseline = propose()
        for kwargs in (dict(corridor_scorer=PreferOther(), corridor_weight=0.),
                       dict(corridor_scorer=None, corridor_weight=16.)):
            self.assertEqual(json.dumps(propose(**kwargs), sort_keys=True),
                             json.dumps(baseline, sort_keys=True))

    def test_rerank_only_switches_between_accepted_proposals(self):
        (base, base_diag), (hook, diag) = propose(), propose(corridor_scorer=PreferOther(), corridor_weight=1.,
                                                            costmap=costmap())
        accepted = [c['pair'] for c in base_diag['accepted_candidates']]
        self.assertNotEqual(hook['entry'], base['entry'])
        self.assertIn(diag['selected_pair'], accepted)
        self.assertNotEqual(diag['selected_pair'], base_diag['selected_pair'])
        self.assertEqual(diag['corridor_rerank']['status'], 'applied')
        self.assertTrue(diag['corridor_rerank']['changed'])
        self.assertEqual(diag['top_candidate_basis'], 'learned_rerank')
        self.assertTrue(hook['diagnostics']['learned_rerank']['changed'])
        # The same gates rejected the same pairs.
        self.assertEqual(diag['pair_rejection_counts'], base_diag['pair_rejection_counts'])
        # Logged per candidate so outcomes.jsonl can show the re-rank.
        logged = [c['features'] for c in outcome_candidates(dict(lane_detection=diag), None)]
        self.assertTrue(all('learned_regret_m' in f and 'rerank_score' in f for f in logged))

    def test_scorer_failure_or_wrong_model_falls_back_with_flag(self):
        base, _ = propose()
        route_model = LearnedScorer(dict(schema=SCHEMA, features=['score'], fill_value=-1., base=0.,
                                         learning_rate=.1, trees=[]))
        self.assertEqual(route_model.decision, 'route')
        for scorer in (Broken(), route_model):
            result, diagnostics = propose(corridor_scorer=scorer, corridor_weight=1.)
            self.assertEqual(result['entry'], base['entry'])
            self.assertEqual(diagnostics['corridor_rerank']['status'], 'error')
            self.assertFalse(result['diagnostics']['learned_rerank']['changed'])

    def test_costmap_features_see_an_observed_obstacle_in_one_corridor(self):
        _, diagnostics = propose()
        rows = corridor_feature_rows(diagnostics['accepted_candidates'], ROBOT, YAW, GOAL, costmap(-1.5))
        lower = min(range(2), key=lambda k: diagnostics['accepted_candidates'][k]['entry'][1])
        self.assertLess(rows[lower]['ahead_lethal_distance_m'], 8.)
        self.assertEqual(rows[1-lower]['ahead_lethal_distance_m'], 8.)
        self.assertTrue(set(rows[0]) <= set(CORRIDOR_FEATURES))

    def test_planner_never_receives_corridor_options(self):
        received = {}

        def fake_select_local_goal(*args, **kwargs):
            received.update(kwargs, target=list(args[7]))
            return None

        original = observed_navigation.select_local_goal
        observed_navigation.select_local_goal = fake_select_local_goal
        try:
            args = costmap() + (ROBOT, YAW, GOAL, POINTS)
            options = dict(lookahead=7., goal_footprint=None)
            observed_navigation.plan_observed_navigation(*args, **options)
            base_target = received['target']
            received.clear()
            diagnostics = {}
            observed_navigation.plan_observed_navigation(*args, guidance_diagnostics=diagnostics,
                corridor_scorer=PreferOther(), corridor_weight=1., **options)
        finally:
            observed_navigation.select_local_goal = original
        self.assertNotIn('corridor_scorer', received)
        self.assertNotIn('corridor_weight', received)
        self.assertNotEqual(received['target'], base_target)
        self.assertTrue(diagnostics['lane_detection']['corridor_rerank']['changed'])

    def test_dataset_rows_match_runtime_features(self):
        cmap = costmap(-1.5)
        diagnostics = {}
        observed_navigation.select_observed_guidance(POINTS, ROBOT, YAW, GOAL, lookahead=7.,
                                                     guidance_diagnostics=diagnostics)
        candidates = outcome_candidates(diagnostics, None)
        runtime = corridor_feature_rows(diagnostics['lane_detection']['accepted_candidates'],
                                        ROBOT, YAW, GOAL, cmap)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            outcome = dict(schema_version=2, index=3, destination_index=0, candidates=candidates,
                           plan=dict(source='observed_lane_corridor'))
            label = dict(index=3, stamp_s=1., candidates=[dict(source=c['source'], endpoint=c['endpoint'][:2],
                         endpoint_cell='free', teacher_cost_m=10.+k) for k, c in enumerate(candidates)])
            (tmp/'outcomes.jsonl').write_text(json.dumps(outcome)+'\n')
            (tmp/'labels.jsonl').write_text(json.dumps(label)+'\n')
            snapshot = dict(schema_version=1, input=dict(origin=cmap[0], resolution=RES, width=W, height=H,
                            costs=cmap[4], robot_xy=ROBOT, robot_yaw=YAW, destination=GOAL), metadata=MEASURED)
            with gzip.open(tmp/'00003.json.gz', 'wt') as stream:
                json.dump(snapshot, stream)
            rows, stats = build_corridor_rows(tmp/'outcomes.jsonl', tmp/'labels.jsonl', 'run')
        self.assertEqual((stats['groups'], len(rows)), (1, 2))
        self.assertEqual([r['heuristic_choice'] for r in rows], [True, False])
        self.assertEqual([r['regret_m'] for r in rows], [0., 1.])
        for row in rows:
            k = min(range(2), key=lambda j: np.hypot(*np.subtract(
                diagnostics['lane_detection']['accepted_candidates'][j]['entry'], row['endpoint'])))
            self.assertEqual(set(row['features']), set(runtime[k]))
            for name, value in row['features'].items():
                self.assertAlmostEqual(value, runtime[k][name], delta=1e-3, msg=name)


def _target(status, cost):
    return dict(status=status, entry_straight_m=3., entry_path_m=cost, cost_m=cost)


class CorridorLabelModeTests(unittest.TestCase):
    """build_corridor_rows: one explicit label mode, no guessed targets, counted omissions."""

    def write(self, tmp, labels_by_index, plan_source='observed_lane_corridor'):
        cmap = costmap()
        diagnostics = {}
        observed_navigation.select_observed_guidance(POINTS, ROBOT, YAW, GOAL, lookahead=7.,
                                                     guidance_diagnostics=diagnostics)
        candidates = outcome_candidates(diagnostics, None)
        snapshot = dict(schema_version=1, input=dict(origin=cmap[0], resolution=RES, width=W, height=H,
                        costs=cmap[4], robot_xy=ROBOT, robot_yaw=YAW, destination=GOAL), metadata=MEASURED)
        outcomes, labels = [], []
        for index, (mode, per_candidate) in labels_by_index.items():
            outcomes.append(dict(schema_version=2, index=index, destination_index=0, candidates=candidates,
                                 plan=dict(source=plan_source)))
            rows = []
            for k, c in enumerate(candidates):
                row = dict(source=c['source'], endpoint=c['endpoint'][:2], endpoint_cell='free',
                           teacher_cost_m=10.+k, regret_m=float(k))
                if per_candidate is not None:
                    row['corridor_target'] = per_candidate[k]
                rows.append(row)
            label = dict(index=index, stamp_s=1., candidates=rows)
            if mode is not None:
                label['corridor_label'] = mode
            labels.append(label)
            with gzip.open(tmp/f'{index:05d}.json.gz', 'wt') as stream:
                json.dump(snapshot, stream)
        (tmp/'outcomes.jsonl').write_text(''.join(json.dumps(o)+'\n' for o in outcomes))
        (tmp/'labels.jsonl').write_text(''.join(json.dumps(l)+'\n' for l in labels))
        self.assertEqual(len(candidates), 2)
        return tmp/'outcomes.jsonl', tmp/'labels.jsonl'

    def test_path_v3_uses_separate_target_and_omits_whole_groups_with_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Decision 3: the legacy straight line prefers candidate 0, the grid detour reverses it.
            # Decision 4: candidate 1 is search-limited -> the whole group goes, with a reason.
            # Decision 5: candidate 0 is proven disconnected -> the whole group goes, never a penalty.
            paths = self.write(Path(tmp), {
                3: ('path-v3', [_target('grid_path', 19.), _target('line_of_sight', 11.)]),
                4: ('path-v3', [_target('line_of_sight', 10.), _target('search_limited', None)]),
                5: ('path-v3', [_target('disconnected', None), _target('line_of_sight', 11.)])})
            rows, stats = build_corridor_rows(*paths, 'run', corridor_label='path-v3')
        self.assertEqual([r['index'] for r in rows], [3, 3])
        self.assertEqual([r['teacher_cost_m'] for r in rows], [19., 11.])
        self.assertEqual([r['regret_m'] for r in rows], [8., 0.])
        self.assertEqual([r['teacher_best'] for r in rows], [False, True])
        self.assertEqual({r['corridor_status'] for r in rows}, {'grid_path', 'line_of_sight'})
        self.assertEqual(stats['groups'], 1)
        self.assertEqual(stats['omitted_target_groups'], 2)
        self.assertEqual(stats['omitted_target'], {'search_limited': 1, 'disconnected': 1})
        self.assertTrue(all(r['corridor_label'] == 'path-v3' for r in rows))

    def test_legacy_mode_keeps_previous_rows_and_ignores_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write(Path(tmp), {3: (None, None)})
            rows, stats = build_corridor_rows(*paths, 'run', corridor_label='straight-v1')
        self.assertEqual([r['teacher_cost_m'] for r in rows], [10., 11.])
        self.assertEqual([r['regret_m'] for r in rows], [0., 1.])
        self.assertNotIn('corridor_label', rows[0])
        self.assertEqual(stats['omitted_target_groups'], 0)

    def test_mode_mismatch_mixed_and_incompatible_records_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            v3 = [_target('line_of_sight', 10.), _target('line_of_sight', 11.)]
            cases = [
                ('straight-v1', {3: ('path-v3', v3)}),                 # selected mode differs from labels
                ('path-v3', {3: (None, None)}),                         # legacy labels used as path-v3
                ('straight-v1', {3: ('path-v2', None)}),                # unaccepted overwritten-cost labels
                ('path-v3', {3: ('path-v3', v3), 4: (None, None)}),     # mixed modes in one file
                ('path-v3', {3: ('path-v3', None)}),                    # path-v3 record without corridor_target
                ('path-v3', {3: ('path-v3', [_target('grid_path', None), _target('line_of_sight', 11.)])}),
                ('path-v2', {3: ('path-v2', None)}),                    # unsupported selection
            ]
            for k, (selected, labels) in enumerate(cases):
                case = tmp/str(k)
                case.mkdir()
                paths = self.write(case, labels)
                with self.subTest(case=k), self.assertRaises(ValueError):
                    build_corridor_rows(*paths, 'run', corridor_label=selected)

    def rewrite_labels(self, labels_path, *edits):
        """Replace labels.jsonl with one raw record per edit (a dict update of the original record)."""
        base = json.loads(labels_path.read_text().splitlines()[0])
        records = []
        for edit in edits:
            record = dict(base)
            for key, value in edit.items():
                if value is None:
                    record.pop(key, None)
                else:
                    record[key] = value
            records.append(record)
        labels_path.write_text(''.join(json.dumps(r)+'\n' for r in records))

    def test_raw_duplicates_and_contradictory_aliases_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            v3 = [_target('line_of_sight', 10.), _target('line_of_sight', 11.)]
            cases = [
                # Mixed modes sharing index 3: deduplication must not hide the legacy record.
                ('path-v3', dict(corridor_label='path-v3'), dict(corridor_label=None)),
                ('straight-v1', dict(corridor_label=None), dict(corridor_label='path-v3')),
                # Same mode, same index: rejected instead of silently choosing a row.
                ('path-v3', dict(corridor_label='path-v3'), dict(corridor_label='path-v3')),
                ('straight-v1', dict(corridor_label=None), dict(corridor_label=None)),
                # Contradictory aliases on one record, in either selected mode.
                ('path-v3', dict(corridor_label='path-v3', corridor_cost='straight-v1')),
                ('straight-v1', dict(corridor_label='straight-v1', corridor_cost='path-v3')),
                ('path-v3', dict(corridor_label='path-v3', corridor_cost='path-v2')),
                # Unknown and path-v2 modes, including via the legacy alias alone.
                ('straight-v1', dict(corridor_label=None, corridor_cost='path-v2')),
                ('path-v3', dict(corridor_label='bogus')),
            ]
            for k, (selected, *edits) in enumerate(cases):
                case = tmp/str(k)
                case.mkdir()
                outcomes, labels = self.write(case, {3: ('path-v3', v3)})
                self.rewrite_labels(labels, *edits)
                with self.subTest(case=k), self.assertRaises(ValueError):
                    build_corridor_rows(outcomes, labels, 'run', corridor_label=selected)

    def test_valid_unique_records_and_agreeing_aliases_are_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            v3 = [_target('grid_path', 19.), _target('line_of_sight', 11.)]
            cases = [
                ('path-v3', {}, [19., 11.]),
                ('path-v3', dict(corridor_cost='path-v3'), [19., 11.]),
                ('straight-v1', dict(corridor_label=None), [10., 11.]),
                ('straight-v1', dict(corridor_label=None, corridor_cost='straight-v1'), [10., 11.]),
                ('straight-v1', dict(corridor_label='straight-v1', corridor_cost='straight-v1'), [10., 11.]),
            ]
            for k, (selected, edit, costs) in enumerate(cases):
                case = tmp/str(k)
                case.mkdir()
                outcomes, labels = self.write(case, {3: ('path-v3', v3)})
                self.rewrite_labels(labels, edit)
                with self.subTest(case=k):
                    rows, stats = build_corridor_rows(outcomes, labels, 'run', corridor_label=selected)
                    self.assertEqual([r['teacher_cost_m'] for r in rows], costs)
                    self.assertEqual(stats['groups'], 1)

    def test_malformed_raw_label_lines_are_rejected_with_line_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            v3 = [_target('grid_path', 19.), _target('line_of_sight', 11.)]
            bad = ['{"index": 4, "corridor_label": "straight-v1"', '[4]', '"text"',
                   '{"corridor_label": "path-v3"}', '{"index": true}', '{"index": 4.0}',
                   '{"index": "4"}', '{"index": null}']
            for k, line in enumerate(bad):
                case = tmp/str(k)
                case.mkdir()
                outcomes, labels = self.write(case, {3: ('path-v3', v3)})
                labels.write_text(labels.read_text()+'\n'+line+'\n')
                with self.subTest(line=line), self.assertRaisesRegex(ValueError, r'labels\.jsonl:3: '):
                    build_corridor_rows(outcomes, labels, 'run', corridor_label='path-v3')
            # Blank and whitespace-only lines remain tolerated around a valid record.
            case = tmp/'blank'
            case.mkdir()
            outcomes, labels = self.write(case, {3: ('path-v3', v3)})
            labels.write_text('\n  \n'+labels.read_text()+'\n\t\n')
            rows, stats = build_corridor_rows(outcomes, labels, 'run', corridor_label='path-v3')
            self.assertEqual(([r['teacher_cost_m'] for r in rows], stats['groups']), ([19., 11.], 1))

    def test_omissions_before_target_check_are_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            v3 = [_target('line_of_sight', 10.), _target('line_of_sight', 11.)]
            paths = self.write(Path(tmp), {3: ('path-v3', v3)}, plan_source='grid')
            rows, stats = build_corridor_rows(*paths, 'run', corridor_label='path-v3')
        self.assertEqual((rows, stats['not_corridor_guidance'], stats['groups']), ([], 1, 0))

    def test_cli_requires_an_explicit_corridor_label(self):
        from build_dataset import main
        with self.assertRaises(SystemExit):
            main(['build', '--runs', 'x', '--kind', 'corridor'])
        with self.assertRaises(SystemExit):
            main(['build', '--runs', 'x', '--corridor-label', 'path-v3'])


if __name__ == '__main__':
    unittest.main()
