import gzip
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from navigation_decisions import (DecisionRecorder, DecisionOutcomes, compact_event_metadata,
                                  decimate_path, read_outcomes, OUTCOME_FILE)
import replay_navigation_decision as replay_tool
from sensor_course import send_goal_with_startup_retry

REAL_SNAPSHOT = (Path(__file__).resolve().parents[2] / 'artifacts/sandbox/runs/'
                 '20261002T061204-d4510a99/decisions/00001.json.gz')
OUTCOME_KEYS = {'schema_version', 'index', 'destination_index', 'plan', 'candidates', 'search_wall_s',
                'admitted', 'action', 'robot_xy_after', 'progress_m'}
WORLD_WORDS = ('course', 'world', 'route', 'centerline', 'obstacle')


def evaluated_fixture():
    plan = dict(local_goal=(3., .1), yaw=.05, path=[(i*.01, 0.) for i in range(485)],
                diagnostics=dict(endpoint=(5., .2), path_length=5.1, weighted_cost=6.2,
                                 endpoint_progress=4.9, local_path_length=3.,
                                 destination_yaw_error_rad=None, guidance='observed_lane_corridor'))
    diagnostics = dict(guidance='observed_lane_corridor', lane_detection=dict(accepted_candidates=[
        dict(pair=[0, 1], entry=[3.3, -.04], direction=[.9997, .0248], distance_m=3.32, score=2.49,
             confidence=.55, gps_alignment=.99, overlap_m=4.15, width_samples_m=[6.05]),
        dict(pair=[0, 2], entry=[4.0, 1.0], direction=[1., 0.], distance_m=4.1, score=1.2,
             confidence=.9, gps_alignment=.8)]))
    return plan, diagnostics


class DecisionOutcomeTests(unittest.TestCase):
    def test_outcomes_round_trip_with_schema_and_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = DecisionRecorder(Path(directory) / 'decisions')
            outcomes = DecisionOutcomes(recorder.submit_outcome)
            plan, diagnostics = evaluated_fixture()
            outcomes.begin(1, 0, (0., 0.), (10., 0.))
            outcomes.evaluated(1, plan, diagnostics, .42)
            outcomes.update(1, admitted=True)
            outcomes.update(1, action='accepted')
            outcomes.begin(2, 0, (2., 0.), (10., 0.))
            outcomes.evaluated(2, None, dict(guidance='broad_gps'), .1)
            outcomes.result(1, 5)  # preempted goal result arrives after decision 2
            outcomes.close((2.5, 0.))
            result = recorder.close()
            self.assertEqual(result['outcomes']['saved'], 2)
            self.assertEqual(result['outcomes']['dropped'], 0)
            records = read_outcomes(Path(directory) / 'decisions')
            self.assertEqual(set(records), {1, 2})
            first, second = records[1], records[2]
            self.assertEqual(set(first), OUTCOME_KEYS)
            self.assertEqual(first['schema_version'], 2)
            self.assertEqual(first['action'], 'canceled')
            self.assertTrue(first['admitted'])
            self.assertEqual(first['robot_xy_after'], [2., 0.])
            self.assertAlmostEqual(first['progress_m'], 2.)
            self.assertEqual(first['plan']['endpoint'], [3., .1, .05])
            self.assertEqual(first['plan']['source'], 'observed_lane_corridor')
            self.assertLessEqual(len(first['plan']['path']), 60)
            self.assertEqual(first['plan']['path'][-1], [4.84, 0.])
            sources = [c['source'] for c in first['candidates']]
            self.assertEqual(sources, ['corridor', 'corridor', 'grid'])
            self.assertEqual(first['candidates'][0]['score'], 1.2)  # sorted by heuristic score
            self.assertEqual(len(first['candidates'][0]['endpoint']), 3)
            self.assertEqual(first['candidates'][2]['path_length_m'], 5.1)
            self.assertIn('gps_alignment', first['candidates'][1]['features'])
            self.assertEqual(second['action'], 'not_sent')
            self.assertIsNone(second['plan']['endpoint'])
            self.assertEqual(second['plan']['source'], 'broad_gps')
            self.assertIsNone(second['admitted'])
            self.assertAlmostEqual(second['progress_m'], .5)
            text = (Path(directory) / 'decisions' / OUTCOME_FILE).read_text()
            self.assertFalse(any(word in text for word in WORLD_WORDS))
            self.assertNotIn('10.0', text)  # destination held only to compute progress
            print(f'\noutcome record bytes: {[len(line) for line in text.splitlines()]}')

    def test_outcome_drops_are_counted_and_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = DecisionRecorder(Path(directory) / 'decisions', outcome_capacity=1)
            started, release = threading.Event(), threading.Event()

            class Stall(dict):  # json's encoder calls items() on dict subclasses
                def items(self):
                    started.set(); release.wait(5.)
                    return super().items()
            self.assertTrue(recorder.submit_outcome(Stall(schema_version=2, index=0)))
            self.assertTrue(started.wait(5.))
            accepted = [recorder.submit_outcome(dict(schema_version=2, index=i)) for i in range(1, 6)]
            self.assertEqual(accepted, [True, False, False, False, False])
            release.set()
            result = recorder.close()
            self.assertEqual(result['outcomes']['dropped'], 4)
            self.assertEqual(result['outcomes']['saved'], 2)
            self.assertTrue(result['outcomes']['drained'])
            self.assertEqual(set(read_outcomes(Path(directory) / 'decisions')), {0, 1})

    def test_outcomes_wait_for_action_result_and_stay_bounded(self):
        written = []
        outcomes = DecisionOutcomes(written.append, max_open=3)
        outcomes.begin(1, 0, (0., 0.), (5., 0.))
        outcomes.update(1, action='accepted')
        outcomes.begin(2, 0, (1., 0.), (5., 0.))
        self.assertEqual(written, [])  # accepted goal still running
        outcomes.result(1, 4)
        self.assertEqual([r['index'] for r in written], [1])
        self.assertEqual(written[0]['action'], 'succeeded')
        for index in range(3, 10):
            outcomes.update(index-1, action='accepted')
            outcomes.begin(index, 0, (0., 0.), (5., 0.))
        self.assertLessEqual(len(outcomes.open), 3)
        with self.assertRaises(ValueError):
            outcomes.update(9, action='teleported')

    def test_decimation_keeps_endpoints(self):
        self.assertIsNone(decimate_path([]))
        points = decimate_path([(float(i), 0.) for i in range(1000)])
        self.assertEqual(len(points), 60)
        self.assertEqual(points[0], [0., 0.])
        self.assertEqual(points[-1], [999., 0.])


@unittest.skipUnless(REAL_SNAPSHOT.exists(), 'real capture not present')
class ReplayCompatibilityTests(unittest.TestCase):
    def test_real_snapshot_still_validates_and_replays(self):
        snapshot, digest = replay_tool.load_snapshot(REAL_SNAPSHOT)
        self.assertEqual(snapshot['schema_version'], 1)
        self.assertEqual(len(digest), 64)
        report = replay_tool.replay(snapshot, diagnostics_only=True)
        self.assertEqual(report['status'], 'diagnostics_only')

    def test_replay_refuses_world_keys_and_outcome_log(self):
        snapshot, _ = replay_tool.load_snapshot(REAL_SNAPSHOT)
        for key in ('course', 'world', 'route', 'centerline'):
            bad = json.loads(json.dumps(snapshot))
            bad['input'][key] = [[0., 0.]]
            with self.assertRaises(ValueError):
                replay_tool.validate_snapshot(bad)
        bad = json.loads(json.dumps(snapshot))
        bad['outcome'] = {}
        with self.assertRaises(ValueError):
            replay_tool.validate_snapshot(bad)
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / OUTCOME_FILE
            log.write_text(json.dumps(dict(schema_version=2, index=1))+'\n')
            with self.assertRaises(ValueError):
                replay_tool.load_snapshot(log)
            self.assertEqual(replay_tool.main(['--snapshot', str(log)]), 1)


class FakeHandle:
    def __init__(self, accepted):
        self.accepted = accepted


class StartupGoalRetryTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.
        self.retries = []
        self.waits = []

    def run_case(self, replies, *, startup, still=lambda: True, server=True):
        replies = list(replies)
        sends = []
        def send():
            sends.append(self.now)
            return FakeHandle(replies.pop(0))
        def wait_for_server(timeout_sec):
            self.waits.append(timeout_sec)
            return server
        def pause(seconds):
            self.now += seconds
        handle = send_goal_with_startup_retry(send, wait_for_server, pause, self.retries,
            startup=startup, still_startup=still, clock=lambda: self.now)
        return handle, sends

    def test_retries_rejections_before_first_acceptance(self):
        handle, sends = self.run_case([False, False, True], startup=True)
        self.assertTrue(handle.accepted)
        self.assertEqual(len(sends), 3)
        self.assertEqual([r['attempt'] for r in self.retries], [1, 2])
        self.assertEqual(self.waits, [5.])

    def test_startup_retries_are_bounded(self):
        handle, sends = self.run_case([False]*10, startup=True)
        self.assertFalse(handle.accepted)
        self.assertLessEqual(len(sends), 5)
        self.assertLessEqual(self.now, 5.)

    def test_no_retry_after_first_acceptance(self):
        handle, sends = self.run_case([False, True], startup=False)
        self.assertFalse(handle.accepted)  # caller raises exactly as before
        self.assertEqual(len(sends), 1)
        self.assertEqual(self.retries, [])
        self.assertEqual(self.waits, [])

    def test_no_retry_once_robot_moved(self):
        handle, sends = self.run_case([False, True], startup=True, still=lambda: False)
        self.assertFalse(handle.accepted)
        self.assertEqual(len(sends), 1)

    def test_unavailable_server_at_startup_raises(self):
        with self.assertRaises(RuntimeError):
            self.run_case([True], startup=True, server=False)


class DecisionRecorderTests(unittest.TestCase):
    def test_full_evidence_does_not_overflow_bounded_ros_decision_events(self):
        metadata = dict(odom_stamp_ns=123000000000, source_sha256={'source':'a'*64},
            memory_refresh_input=dict(evidence_rows=[[1.1234567,2.1234567,0.,1.1234567,6,1,123,456789123]]*8000,
                                      receipt_age_wall_s=.1))
        self.assertGreater(len(json.dumps(metadata)),262144)
        event = compact_event_metadata(metadata)
        self.assertLess(len(json.dumps(event)),4096)
        self.assertEqual(event['odom_stamp_ns'],123000000000)
        self.assertEqual(event['memory_refresh_input_summary']['rows'],8000)
        self.assertEqual(len(metadata['memory_refresh_input']['evidence_rows']),8000)

    def test_retains_replay_input_and_exact_acquisition_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = DecisionRecorder(Path(directory) / 'decisions')
            inputs = dict(costs=[-1, 0, 99, 100], robot_xy=[2., 3.], heading_hint=None)
            metadata = dict(odom_stamp_ns=123456789123, lane_stamp_ns=123456700000)
            name = recorder.submit(1, inputs, metadata)
            result = recorder.close()
            self.assertEqual(result['saved'], 1)
            self.assertFalse(result['errors'])
            with gzip.open(Path(directory) / 'decisions' / name, 'rt') as stream:
                saved = json.load(stream)
            self.assertEqual(saved['input'], inputs)
            self.assertEqual(saved['metadata'], metadata)

    def test_existing_capture_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                DecisionRecorder(directory)

    def test_write_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = DecisionRecorder(Path(directory) / 'decisions')
            recorder.submit(1, dict(invalid=float('nan')), {})
            result = recorder.close()
            self.assertEqual(result['saved'], 0)
            self.assertEqual(len(result['errors']), 1)
