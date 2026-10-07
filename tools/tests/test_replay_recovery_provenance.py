"""Recovery-event replays are labelled counterfactual reconstructions admitted by grid stamp.

Run directories, snapshots, events and trajectories are synthetic and written to a
temporary directory; no recorded run, course, WORLD geometry or teacher label is
read. Recovery planners are mocked so the tests observe exactly which events reach
them and with what arguments; the forward planner itself must never be called.
"""
from pathlib import Path
from unittest import mock
import contextlib
import copy
import gzip
import io
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import replay_recovery

STAMP = 1_700_000_000_123_456_789
ABSENT = object()
# Driven straight along +x at 0.5 m/s; the recovery event is stamped at t=6 s.
TRAJECTORY = [[float(t), .5*t, 2., 0.] for t in range(9)]
SELECTION = {'guidance': 'observed_gate', 'target': [8., 6.], 'yaw': .5}


def snapshot(stamp=STAMP):
    payload = {'schema_version': 1,
               'input': {'origin': [-5., -5.], 'resolution': .5, 'width': 4, 'height': 4,
                         'costs': [0]*15+[100], 'robot_xy': [9., 9.], 'robot_yaw': 1.,
                         'destination': [8., 9.],
                         'planner_options': {'goal_footprint': [-1.1, .6, -.5, .5], 'body_clearance_weight': .2,
                                             'entrance_tracking': True}},
               'metadata': {'source_sha256': 'synthetic'}}
    if stamp is not ABSENT:
        payload['metadata']['grid_stamp_ns'] = stamp
    return payload


def event(sequence, stamp=STAMP):
    payload = {'schema_version': 1, 'phase': 'recovery_guidance_selected', 'sequence': sequence,
               'odom_stamp_ns': 6_000_000_000, 'destination_index': 3,
               'selection': copy.deepcopy(SELECTION), 'selection_pose': [3., 2., 0.]}
    if stamp is not ABSENT:
        payload['grid_stamp_ns'] = stamp
    return payload


def plan(goal, path):
    return {'local_goal': goal, 'path': path, 'diagnostics': {}}


LEGACY = {'distance_m': .6, 'forward_plan': plan([3.123, 4.567, 0.], [[2., 2., 0.], [3., 4., 0.]]),
          'diagnostics': {'original_trap_progress_m': .5512}}
ESCAPE = {'escape_type': 'retrace', 'distance_m': 1.2, 'forward_plan': plan([6.004, 1.996, 0.], [[4.4, 2.1, 0.]]),
          'diagnostics': {'original_trap_progress_m': .7349, 'max_corridor_deviation_m': .1234}}


class ReplayHarness(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root/'synthetic-run'
        (self.run/'decisions').mkdir(parents=True)
        self.loaded, self.backup, self.escape = [], [], []
        self.backup_effect = self.escape_effect = None

    def write(self, sequence, payload=None, raw=None):
        path = self.run/'decisions'/f'{sequence:05d}.json.gz'
        if raw is not None:
            path.write_bytes(raw)
        else:
            with gzip.open(path, 'wt') as stream:
                json.dump(payload, stream)

    @contextlib.contextmanager
    def mocked(self):
        real_load = replay_recovery.load_snapshot

        def load(run, sequence):
            self.loaded.append(sequence)
            return real_load(run, sequence)

        def backup(*args, **kwargs):
            self.backup.append((args, kwargs))
            if self.backup_effect is not None:
                raise self.backup_effect
            return copy.deepcopy(LEGACY)

        def escape(*args, **kwargs):
            self.escape.append((args, kwargs))
            if self.escape_effect is not None:
                raise self.escape_effect
            return copy.deepcopy(ESCAPE)

        with mock.patch.object(replay_recovery, 'load_snapshot', side_effect=load), \
                mock.patch.object(replay_recovery, 'select_backup_recovery', side_effect=backup), \
                mock.patch.object(replay_recovery, 'select_trap_escape', side_effect=escape), \
                mock.patch.object(replay_recovery, 'plan_observed_navigation',
                                  side_effect=AssertionError('planner must stay mocked')) as forward:
            self.forward = forward
            yield

    def replay(self, payload, allow=False, budget_scale=1., index=7):
        self.data = {'decisions': [payload], 'trajectory': copy.deepcopy(TRAJECTORY)}
        with self.mocked():
            return replay_recovery.replay_event(self.run, self.data, payload, [], budget_scale,
                                                event_index=index, allow_grid_mismatch=allow)

    def assert_no_planner(self):
        self.assertEqual((self.backup, self.escape), ([], []))

    def assert_skipped(self, row, reason):
        self.assertEqual((row['status'], row['skipped'], row['reason']), ('skipped', True, reason))
        self.assertIsNone(row['replay_kind'])
        self.assertEqual(row['input_binding'], 'not_evaluated')
        for key in ('legacy', 'retrace', 'trap_region', 'stall_pose'):
            self.assertNotIn(key, row)


class AdmissionTest(ReplayHarness):
    def test_equal_stamps_execute_as_labelled_counterfactual(self):
        self.write(4, snapshot())
        row = self.replay(event(4))
        self.assertEqual((row['status'], row['skipped'], row['reason']), ('executed', False, 'grid_stamp_match'))
        self.assertEqual(row['replay_kind'], 'counterfactual_reconstructed')
        self.assertEqual(row['input_binding'], 'not_evaluated')
        self.assertEqual((row['event_index'], row['sequence'], row['budget_scale']), (7, 4, 1.))
        self.assertEqual(row['grid_stamp']['status'], 'match')
        self.assertEqual(row['grid_stamp']['event'], {'value': STAMP, 'type': 'int', 'problem': None})
        self.assertEqual(row['grid_stamp']['snapshot'], {'value': STAMP, 'type': 'int', 'problem': None})
        self.assertEqual((len(self.backup), len(self.escape)), (1, 1))

    def test_differing_stamps_skip_with_raw_values_and_no_planner(self):
        self.write(4, snapshot(STAMP+1))
        row = self.replay(event(4))
        self.assert_skipped(row, 'grid_stamp_mismatch')
        self.assertEqual(row['grid_stamp']['status'], 'mismatch')
        self.assertEqual((row['grid_stamp']['event']['value'], row['grid_stamp']['snapshot']['value']),
                         (STAMP, STAMP+1))
        self.assert_no_planner()

    def test_missing_or_malformed_stamps_are_unknown_and_never_coerced(self):
        bad = [(ABSENT, None), (True, True), (False, False), (float(STAMP), float(STAMP)), (0, 0),
               (-STAMP, -STAMP), (str(STAMP), str(STAMP)), (None, None), ([STAMP], None),
               (float('nan'), None)]
        for side in ('event', 'snapshot'):
            for value, recorded in bad:
                with self.subTest(side=side, value=value):
                    self.write(4, snapshot(value if side == 'snapshot' else STAMP))
                    row = self.replay(event(4, value if side == 'event' else STAMP))
                    self.assert_skipped(row, 'grid_stamp_unknown')
                    stamp = row['grid_stamp'][side]
                    self.assertEqual(row['grid_stamp']['status'], 'unknown')
                    self.assertIsNotNone(stamp['problem'])
                    self.assertIs(type(stamp['value']), type(recorded))
                    if recorded is not None:
                        self.assertEqual(stamp['value'], recorded)
        self.assert_no_planner()

    def test_numerically_equal_non_int_stamps_do_not_match(self):
        for event_stamp, snapshot_stamp in ((1, True), (True, 1), (float(10**9), 10**9), (10**9, float(10**9))):
            with self.subTest(event=event_stamp, snapshot=snapshot_stamp):
                self.write(4, snapshot(snapshot_stamp))
                self.assert_skipped(self.replay(event(4, event_stamp)), 'grid_stamp_unknown')
        self.assert_no_planner()

    def test_snapshot_without_metadata_is_unknown(self):
        payload = snapshot()
        del payload['metadata']
        self.write(4, payload)
        row = self.replay(event(4))
        self.assert_skipped(row, 'grid_stamp_unknown')
        self.assertEqual(row['grid_stamp']['snapshot']['problem'], 'metadata_absent')
        payload['metadata'] = [STAMP]
        self.write(4, payload)
        self.assert_skipped(self.replay(event(4)), 'grid_stamp_unknown')
        self.assert_no_planner()

    def test_opt_in_executes_mismatch_and_unknown_with_their_labels(self):
        cases = ((STAMP, STAMP+1, 'grid_stamp_mismatch', 'mismatch'),
                 (float(STAMP), STAMP, 'grid_stamp_unknown', 'unknown'),
                 (STAMP, ABSENT, 'grid_stamp_unknown', 'unknown'),
                 (STAMP, STAMP, 'grid_stamp_match', 'match'))
        for count, (event_stamp, snapshot_stamp, reason, status) in enumerate(cases, 1):
            with self.subTest(reason=reason, status=status):
                self.write(4, snapshot(snapshot_stamp))
                row = self.replay(event(4, event_stamp), allow=True)
                self.assertEqual((row['status'], row['reason'], row['allow_grid_mismatch']),
                                 ('executed', reason, True))
                self.assertEqual(row['replay_kind'], 'counterfactual_reconstructed')
                self.assertEqual(row['input_binding'], 'not_evaluated')
                self.assertEqual(row['grid_stamp']['status'], status)
                self.assertEqual(row['grid_stamp']['event']['value'], event_stamp)
                self.assertIs(type(row['grid_stamp']['event']['value']), type(event_stamp))
                self.assertIn('legacy', row)
                self.assertEqual(len(self.backup), count)

    def test_unavailable_snapshots_stay_skipped_even_with_opt_in(self):
        valid = gzip.compress(json.dumps(snapshot()).encode())
        shapes = {'input_list': dict(snapshot(), input=[]), 'top_level_list': [snapshot()]}
        broken = [('costs', 'costs', [0]*15), ('width', 'width', 0), ('height', 'height', True),
                  ('resolution', 'resolution', -.5), ('origin', 'origin', [1.]),
                  ('destination', 'destination', None)]
        for name, key, value in broken:
            payload = snapshot()
            payload['input'][key] = value
            shapes[name] = payload
        payload = snapshot()
        del payload['input']['planner_options']
        shapes['no_options'] = payload
        footprints = {'footprint_short': [.4], 'footprint_pair': [.4, .3],
                      'footprint_unordered_x': [.6, -1.1, -.5, .5], 'footprint_unordered_y': [-1.1, .6, .5, -.5],
                      'footprint_degenerate': [-1.1, -1.1, -.5, .5], 'footprint_nan': [-1.1, float('nan'), -.5, .5],
                      'footprint_inf': [-1.1, .6, -.5, float('inf')], 'footprint_bool': [-1.1, .6, False, True]}
        for name, value in footprints.items():
            payload = snapshot()
            payload['input']['planner_options']['goal_footprint'] = value
            shapes[name] = payload
        cases = [('absent', None, 'snapshot_missing'),
                 ('bad_gzip', b'not gzip at all', 'snapshot_unreadable'),
                 ('truncated', valid[:len(valid)//2], 'snapshot_unreadable'),
                 ('bad_json', gzip.compress(b'{"input": '), 'snapshot_invalid_json')]
        cases += [(name, gzip.compress(json.dumps(shape).encode()), 'snapshot_malformed')
                  for name, shape in shapes.items()]
        for allow in (False, True):
            for name, raw, reason in cases:
                with self.subTest(allow=allow, case=name):
                    path = self.run/'decisions'/'00004.json.gz'
                    path.unlink(missing_ok=True)
                    if raw is not None:
                        self.write(4, raw=raw)
                    row = self.replay(event(4), allow=allow)
                    self.assert_skipped(row, reason)
                    self.assertEqual(row['grid_stamp']['status'], 'not_evaluated')
                    self.assertEqual(row['grid_stamp']['event']['value'], STAMP)
                    self.assertIsNone(row['grid_stamp']['snapshot'])
                    self.assertIsInstance(row['detail'], str)
        self.assert_no_planner()

    def test_malformed_events_are_skipped_rows(self):
        self.write(4, snapshot())
        edits = {'selection_pose': [3., 2.], 'selection': {'guidance': 'x'}, 'odom_stamp_ns': None,
                 'sequence': True}
        for key, value in edits.items():
            for allow in (False, True):
                with self.subTest(key=key, allow=allow):
                    payload = event(4)
                    payload[key] = value
                    self.assert_skipped(self.replay(payload, allow=allow), 'event_malformed')
        payload = event(4)
        del payload['destination_index']
        self.assert_skipped(self.replay(payload, allow=True), 'event_malformed')
        self.assert_no_planner()

    def test_planner_errors_stay_visible(self):
        self.write(4, snapshot())
        for error in (RuntimeError('planner bug'), OSError('planner io'), KeyError('costs'), ValueError('bad')):
            with self.subTest(error=type(error).__name__):
                self.backup_effect = error
                with self.assertRaises(type(error)):
                    self.replay(event(4))

    def test_escape_planner_errors_stay_visible(self):
        self.write(4, snapshot())
        for error in (RuntimeError('escape bug'), OSError('escape io'), KeyError('costs'), ValueError('bad')):
            with self.subTest(error=type(error).__name__):
                self.escape_effect = error
                with self.assertRaises(type(error)):
                    self.replay(event(4))


class ReconstructionTest(ReplayHarness):
    def test_admitted_output_and_forwarded_values_are_unchanged(self):
        self.write(4, snapshot())
        payload = event(4)
        before = copy.deepcopy(payload)
        row = self.replay(payload, budget_scale=.5)
        self.assertEqual(payload, before)
        self.assertEqual(self.data, {'decisions': [before], 'trajectory': TRAJECTORY})
        self.assertEqual({key: row[key] for key in ('stamp_s', 'stall_pose', 'guidance', 'guidance_exclusion',
                                                    'driven_path_m', 'teacher_trap')},
                         {'stamp_s': 6., 'stall_pose': [3., 2., 0.], 'guidance': 'observed_gate',
                          'guidance_exclusion': None, 'driven_path_m': 3., 'teacher_trap': None})
        self.assertEqual(row['trap_region'], {'center': [4.4, 2.], 'radius': .8, 'entry_yaw': 0.})
        self.assertEqual(row['legacy'], {'type': 'straight_backup', 'distance_m': .6,
                                         'continuation_goal': [3.12, 4.57], 'trap_progress_m': .55,
                                         'corridor_deviation_m': None, 'path_enters_trap_region': False,
                                         'teacher': None})
        self.assertEqual(row['retrace'], {'type': 'retrace', 'distance_m': 1.2, 'continuation_goal': [6., 2.],
                                          'trap_progress_m': .73, 'corridor_deviation_m': .12,
                                          'path_enters_trap_region': True, 'teacher': None})
        grid = snapshot()['input']
        positional = ((-5., -5.), .5, 4, 4, grid['costs'], (3., 2.), 0., [8., 9.])
        options = dict(replay_recovery.FORWARD_OPTIONS, body_clearance_weight=.2)
        (backup_args, backup_kwargs), = self.backup
        (escape_args, escape_kwargs), = self.escape
        self.assertEqual(backup_args, positional)
        self.assertEqual(escape_args, positional)
        self.assertEqual({key: backup_kwargs[key] for key in ('goal_footprint', 'max_search_seconds',
                                                               'forward_options')},
                         {'goal_footprint': (-1.1, .6, -.5, .5), 'max_search_seconds': 2.5, 'forward_options': options})
        self.assertEqual({key: escape_kwargs[key] for key in ('goal_footprint', 'driven_path', 'straight_seconds',
                                                               'retrace_seconds', 'forward_options')},
                         {'goal_footprint': (-1.1, .6, -.5, .5), 'driven_path': [(.5*t, 2.) for t in range(7)],
                          'straight_seconds': 2.5, 'retrace_seconds': 4., 'forward_options': options})
        (region,) = escape_kwargs['trap_regions']
        self.assertAlmostEqual(region['center'][0], 4.4)
        self.assertEqual((region['center'][1], region['radius']), (2., .8))
        for kwargs in (backup_kwargs, escape_kwargs):
            forward = kwargs['forward_planner']
            self.assertIs(forward.func, self.forward)
            self.assertEqual(forward.keywords, {'lane_points': [], 'frozen_guidance': SELECTION,
                                                'entrance_tracking': True})
        self.forward.assert_not_called()


class CommandLineTest(ReplayHarness):
    def main(self, decisions, *flags):
        (self.run/'run.json').write_text(json.dumps({'reason': 'synthetic', 'decisions': decisions,
                                                     'trajectory': TRAJECTORY}))
        output = self.root/'report.json'
        with self.mocked(), contextlib.redirect_stdout(io.StringIO()):
            status = replay_recovery.main([str(self.run), '--labels-root', str(self.root/'no-labels'),
                                           '--output', str(output), *flags])
        self.assertEqual(status, 0)
        (entry,) = json.loads(output.read_text())
        return entry

    def decisions(self):
        self.write(2, snapshot())
        self.write(4, snapshot())
        self.write(5, snapshot())  # Present but never selected: no replacement draws from it.
        return [{'phase': 'requested', 'sequence': 1}, event(2), {'phase': 'action_result', 'sequence': 2},
                event(2, STAMP+5), event(3), event(4)]

    def test_selection_is_fixed_with_unique_event_indices_and_counts(self):
        entry = self.main(self.decisions())
        stalls = entry['stalls']
        self.assertEqual([row['event_index'] for row in stalls], [1, 3, 4, 5])
        self.assertEqual([row['sequence'] for row in stalls], [2, 2, 3, 4])
        self.assertEqual([row['reason'] for row in stalls],
                         ['grid_stamp_match', 'grid_stamp_mismatch', 'snapshot_missing', 'grid_stamp_match'])
        self.assertEqual([row['replay_kind'] for row in stalls],
                         ['counterfactual_reconstructed', None, None, 'counterfactual_reconstructed'])
        self.assertTrue(all(row['input_binding'] == 'not_evaluated' for row in stalls))
        self.assertNotIn(5, self.loaded)
        self.assertEqual(len(self.backup), 2)
        skipped = dict.fromkeys(replay_recovery.SKIP_REASONS, 0)
        skipped.update(grid_stamp_mismatch=1, snapshot_missing=1)
        self.assertEqual(entry['stall_counts'], {
            'selected': 4, 'executed': 2, 'skipped': 2, 'skipped_by_reason': skipped,
            'by_status': {'executed': {'grid_stamp_match': 2, 'grid_stamp_mismatch': 0, 'grid_stamp_unknown': 0},
                          'skipped': skipped}})
        self.assertEqual((entry['controls'], entry['control_counts']['selected']), ([], 0))

    def test_opt_in_flag_executes_mismatch_but_not_missing_snapshot(self):
        entry = self.main(self.decisions(), '--allow-grid-mismatch')
        self.assertEqual([row['status'] for row in entry['stalls']], ['executed', 'executed', 'skipped', 'executed'])
        self.assertTrue(all(row['allow_grid_mismatch'] for row in entry['stalls']))
        counts = entry['stall_counts']
        self.assertEqual((counts['selected'], counts['executed'], counts['skipped']), (4, 3, 1))
        self.assertEqual(counts['by_status']['executed']['grid_stamp_mismatch'], 1)
        self.assertEqual(counts['skipped_by_reason']['snapshot_missing'], 1)

    def test_planner_error_is_not_reported_as_a_skip(self):
        self.backup_effect = RuntimeError('planner bug')
        with self.assertRaises(RuntimeError):
            self.main(self.decisions())

    def test_help_documents_labels_flag_and_counts(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), self.assertRaises(SystemExit):
            replay_recovery.main(['--help'])
        text = stream.getvalue()
        for field in ('--allow-grid-mismatch', 'counterfactual_reconstructed', 'input_binding=not_evaluated',
                      'event_index', 'grid_stamp_match', 'grid_stamp_mismatch', 'grid_stamp_unknown',
                      'snapshot_missing', 'stall_counts', 'skipped_by_reason', 'by_status'):
            self.assertIn(field, text)


if __name__ == '__main__':
    unittest.main()
