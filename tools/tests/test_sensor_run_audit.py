"""Behavioral offline judge fixtures; no Unity or ROS process is needed."""
import copy
import contextlib
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_sensor_run import audit, main, ramp_traversal
from course_judge import paint_evidence, ramp_body_evidence, topology_evidence
from export_autonomy_mission import export_mission
from sensor_telemetry import SensorTelemetry
from mission_health import MissionHealthLedger


def course_fixture():
    # Subdivided square, with wide safe bends, easy to reason about directly.
    corners = [(0., 0.), (20., 0.), (20., 20.), (0., 20.), (0., 0.)]
    points = []
    for a, b in zip(corners, corners[1:]):
        for i in range(20):
            points.append(dict(x=a[0]+(b[0]-a[0])*i/20,
                               y=a[1]+(b[1]-a[1])*i/20, painted=True, half_width=3.))
    points.append(dict(points[0]))
    return dict(frame='odom', units='m', lane_width_m=6., centerline=points,
                obstacles=[dict(id='far', kind='barrel', x=100., y=100., width=.5)],
                ramps=[dict(id='ramp', x=5., y=0., yaw=0., width=3.,
                            rise_length=3., deck_length=2.)])


def walk(points, step=.2):
    samples = [[0., points[0][0], points[0][1], 0.]]
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        count = max(1, math.ceil(length/step))
        yaw = math.atan2(b[1]-a[1], b[0]-a[0])
        for i in range(1, count+1):
            samples.append([samples[-1][0]+.1, a[0]+(b[0]-a[0])*i/count,
                            a[1]+(b[1]-a[1])*i/count, yaw])
    return samples


def health_fixture(samples, *, lane_visible=True, healthy=True):
    """Use the real emitter contract, including its bounded recent history."""
    wall = [0.]
    telemetry = SensorTelemetry(clock=lambda: wall[0])
    for sample in samples:
        wall[0] = sample[0]-samples[0][0]
        stamp = round(sample[0]*1e9)
        telemetry.observe_clock(stamp)
        telemetry.status('lanes', {'valid':lane_visible, 'stamp_ns':stamp})
        telemetry.status('depth_processing', {'valid':True, 'stamp_ns':stamp})
        telemetry.status('lane_health', True)
        telemetry.status('depth_health', healthy)
    return telemetry.report()


class SensorRunAuditTests(unittest.TestCase):
    def setUp(self):
        self.course = course_fixture()
        self.samples = walk([(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)])
        self.hash = hashlib.sha256(json.dumps(self.course).encode()).hexdigest()
        self.mission = export_mission({'origin': dict(latitude=42., longitude=-83., altitude=0.)}, self.course)
        self.mission_hash = hashlib.sha256(json.dumps(self.mission).encode()).hexdigest()
        self.run = dict(status='completed', mode='sensor-led', completed_destinations=6,
                        total_destinations=6, trajectory=self.samples,
                        sim_status=f'course_hash={self.hash} line_guard=scoring line_blocks=0',
                        mission_sha256=self.mission_hash,
                        elapsed_wall_s=self.samples[-1][0]-self.samples[0][0],
                        sensor_health=health_fixture(self.samples))

    def with_interval(self, *, fail_at=None, event_limit=32):
        run = copy.deepcopy(self.run)
        clock = [0.]
        telemetry = SensorTelemetry(clock=lambda: clock[0])
        ledger = MissionHealthLedger(event_limit=event_limit)
        ledger.begin(0., round(self.samples[0][0]*1e9))
        for index, row in enumerate(self.samples):
            clock[0] = row[0]
            stamp = round(row[0]*1e9)
            telemetry.observe_clock(stamp)
            telemetry.status('lanes', {'valid':False,'stamp_ns':stamp})
            telemetry.status('depth_processing', {'valid':True,'stamp_ns':stamp})
            telemetry.status('lane_health', True)
            telemetry.status('depth_health', index != fail_at)
            ledger.observe(telemetry.health_summary(),clock[0],stamp)
        run.update(mission_health_interval=ledger.end(clock[0],stamp),
                   health_trajectory_start_index=0,
                   health_trajectory_end_index=len(self.samples)-1,
                   sensor_health=telemetry.report())
        return run

    def judge(self, run):
        return audit(run,self.course,self.mission,course_sha256=self.hash,
                     mission_sha256=self.mission_hash)

    def test_full_loop_with_bound_sampled_health_can_pass(self):
        result = self.judge(self.with_interval())
        self.assertTrue(result['passed'], result['sensor_health_evidence'])
        self.assertTrue(result['full_loop_certified'])

    def test_middle_failure_survives_latest_pass_and_bounded_history(self):
        result = self.judge(self.with_interval(fail_at=3))
        self.assertTrue(result['checks']['sensor_health_latest_processing_passes'])
        self.assertFalse(result['checks']['sensor_health_interval_verified'])
        self.assertFalse(result['passed'])

    def test_forged_pass_or_wrong_interval_cannot_certify(self):
        for mutation in ('gap','time','counter','index','history','limits','unmonitored_motion',
                         'nan_elapsed','nan_sim_elapsed','event_stamp','event_reset','missing_first'):
            run = self.with_interval(event_limit=10000 if mutation == 'missing_first' else 32)
            value = run['mission_health_interval']
            if mutation == 'gap': value['max_interior_gap_s'] = .4
            elif mutation == 'time': value['start']['monotonic_s'] -= 5
            elif mutation == 'counter': value['totals']['unknown'] = 1
            elif mutation == 'index': run['health_trajectory_start_index'] = 8
            elif mutation == 'history': value['recent_events'][-1]['status'] = 'unknown'
            elif mutation == 'limits': value['health_limits']['max_age_wall_s'] = 5.
            elif mutation == 'nan_elapsed': value['elapsed_wall_s'] = float('nan')
            elif mutation == 'nan_sim_elapsed': value['elapsed_sim_s'] = float('nan')
            elif mutation == 'event_stamp': value['recent_events'][-1]['odom_stamp_ns'] -= 1
            elif mutation == 'event_reset': value['recent_events'][4]['odom_stamp_ns'] = 0
            elif mutation == 'missing_first':
                value['recent_events'][0]['monotonic_s'] += .05
            else:
                run['trajectory'].insert(0,[-.1,-.1,0.,0.])
                run['health_trajectory_start_index'] += 1
                run['health_trajectory_end_index'] += 1
            with self.subTest(mutation=mutation):
                self.assertFalse(self.judge(run)['checks']['sensor_health_interval_verified'])

    def test_full_loop_body_ramp_and_paint_pass(self):
        result = audit(self.run, self.course, self.mission, course_sha256=self.hash,
                       mission_sha256=self.mission_hash)
        self.assertTrue(result['geometric_full_loop_certified'], result)
        self.assertTrue(result['checks']['mission_identity_matches'])
        self.assertTrue(result['checks']['sensor_health_latest_processing_passes'])
        self.assertFalse(result['passed'])
        self.assertFalse(result['full_loop_certified'])
        self.assertEqual(result['sensor_health_evidence']['interval_status'], 'unverified')
        self.assertEqual(result['sensor_health_evidence']['interval_reason'],
                         'schema_v1_has_no_full_interval_health_proof')
        self.assertEqual(result['certification_status'], 'uncertified')
        self.assertTrue(result['ramp_traversals'][0]['passed'])
        self.assertTrue(result['ramp_body_containment'][0]['passed'])
        self.assertFalse(result['wheel_support_certified'])

    def test_missing_mismatched_and_conflicting_identity_fail_closed(self):
        for expected, runtime, extra in [(None, self.hash, None),
                                         (self.hash, 'b'*64, None),
                                         (self.hash, self.hash, 'b'*64),
                                         (self.hash, None, None)]:
            run = copy.deepcopy(self.run)
            run['sim_status'] = 'line_guard=scoring line_blocks=0'+(f' course_hash={runtime}' if runtime else '')
            if extra:
                run['course_sha256'] = extra
            result = audit(run, self.course, self.mission, course_sha256=expected)
            self.assertFalse(result['checks']['course_identity_matches'])
            self.assertFalse(result['full_loop_certified'])
            self.assertFalse(result['paint_crossing_certified'])
            self.assertEqual(result['certification_status'], 'uncertified')

    def test_missing_failed_and_incomplete_health_never_certify_valid_geometry(self):
        failed = health_fixture(self.samples, healthy=False)
        incomplete = {'schema_version':1, 'processing_health_summary':{
            'status':'pass', 'fresh_successful_processing':True}}
        for evidence in (None, failed, incomplete):
            with self.subTest(evidence='missing' if evidence is None else evidence.get('streams') is None):
                run = copy.deepcopy(self.run)
                if evidence is None:
                    run.pop('sensor_health')
                else:
                    run['sensor_health'] = evidence
                result = audit(run,self.course,self.mission,course_sha256=self.hash,
                               mission_sha256=self.mission_hash)
                self.assertFalse(result['checks']['sensor_health_latest_processing_passes'])
                self.assertFalse(result['passed'])
                self.assertFalse(result['full_loop_certified'])
                self.assertTrue(result['geometric_full_loop_certified'])
                self.assertTrue(result['paint_crossing']['passed'])
                self.assertTrue(result['world_topology']['passed'])
        self.assertEqual(audit({**self.run,'sensor_health':failed},self.course,self.mission,
            course_sha256=self.hash,mission_sha256=self.mission_hash)
            ['sensor_health_evidence']['latest_processing_status'], 'fail')

    def test_mission_identity_is_required_independently_of_course_and_geometry(self):
        for observed, expected in ((None,self.mission_hash),(self.mission_hash,None),
                                   ('b'*64,self.mission_hash),('invalid',self.mission_hash)):
            run = copy.deepcopy(self.run)
            if observed is None:
                run.pop('mission_sha256')
            else:
                run['mission_sha256'] = observed
            result = audit(run,self.course,self.mission,course_sha256=self.hash,
                           mission_sha256=expected)
            self.assertFalse(result['checks']['mission_identity_matches'])
            self.assertFalse(result['passed'])
            self.assertFalse(result['full_loop_certified'])
            self.assertTrue(result['geometric_full_loop_certified'])
            self.assertEqual(result['certification_status'], 'uncertified')

    def test_legitimate_lane_gap_is_processing_pass_but_interval_still_unverified(self):
        run = {**self.run, 'sensor_health':health_fixture(self.samples,lane_visible=False)}
        result = audit(run,self.course,self.mission,course_sha256=self.hash,
                       mission_sha256=self.mission_hash)
        health = result['sensor_health_evidence']
        self.assertTrue(health['latest_processing_passed'])
        self.assertEqual(health['latest_processing']['lane_detection_visibility']['status'], 'insufficient')
        self.assertFalse(result['full_loop_certified'])

    def test_telemetry_from_wrong_interval_cannot_certify(self):
        run = copy.deepcopy(self.run)
        run['sensor_health']['streams']['clock']['last_stamp_ns'] += 20_000_000_000
        result = audit(run,self.course,self.mission,course_sha256=self.hash,
                       mission_sha256=self.mission_hash)
        self.assertEqual(result['sensor_health_evidence']['interval_reason'],
                         'telemetry_clock_does_not_match_trajectory_end')
        self.assertFalse(result['passed'])
        run = copy.deepcopy(self.run)
        run['sensor_health']['duration_wall_s'] = 1.
        result = audit(run,self.course,self.mission,course_sha256=self.hash,
                       mission_sha256=self.mission_hash)
        self.assertEqual(result['sensor_health_evidence']['interval_reason'],
                         'missing_or_inconsistent_wall_interval')
        self.assertFalse(result['passed'])

    def test_cli_hashes_exact_mission_bytes_and_keeps_geometric_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            course_path, mission_path = root/'course.json', root/'autonomy.json'
            run_path, output_path = root/'run.json', root/'audit.json'
            course_path.write_text(json.dumps(self.course),encoding='utf-8')
            mission_path.write_text(json.dumps(self.mission),encoding='utf-8')
            run_path.write_text(json.dumps(self.run),encoding='utf-8')
            args = ['audit_sensor_run.py','--run',str(run_path),'--course',str(course_path),
                    '--output',str(output_path)]
            for suffix, expected_match in ((b'',True),(b'\n',False)):
                mission_path.write_bytes(json.dumps(self.mission).encode()+suffix)
                with patch.object(sys,'argv',args), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(),1)  # Schema-1 interval proof stays open.
                report = json.loads(output_path.read_text())
                self.assertEqual(report['checks']['mission_identity_matches'],expected_match)
                self.assertEqual(report['mission_identity']['expected_mission_sha256'],
                                 hashlib.sha256(mission_path.read_bytes()).hexdigest())
                self.assertTrue(report['geometric_full_loop_certified'])

    def test_whole_body_crosses_paint_while_axle_remains_inside(self):
        evidence = paint_evidence(walk([(4, 2.6), (6, 2.6)]), self.course)
        self.assertFalse(evidence['passed'])
        self.assertGreater(evidence['contact_pose_count'], 0)

    def test_swept_paint_intersection_with_clear_endpoints(self):
        translation = [[0, 10, 1, 0], [.4, 10, 5, 0]]
        rotation = [[0, 10, 2, 0], [.4, 10, 2, -math.pi]]
        for samples in (translation, rotation):
            self.assertFalse(paint_evidence(samples, self.course)['passed'])
            self.assertGreater(paint_evidence(samples, self.course)['contact_pose_count'], 0)

    def test_real_gap_allows_boundary_crossing_and_valid_loop(self):
        course = copy.deepcopy(self.course)
        for point in course['centerline']:
            if point['y'] == 0 and 8 <= point['x'] <= 14:
                point['painted'] = False
        samples = walk([(0, 0), (10, 0), (10, 4), (12, 4), (12, 0),
                        (20, 0), (20, 20), (0, 20), (0, 0)])
        self.assertTrue(paint_evidence(samples, course)['passed'])
        self.assertTrue(topology_evidence(samples, course)['passed'])
        self.assertFalse(paint_evidence(samples, self.course)['passed'])

    def test_stationary_region_claim_does_not_complete_loop(self):
        run = copy.deepcopy(self.run)
        run['trajectory'] = [[i*.1, 0, 0, 0] for i in range(100)]
        mission = copy.deepcopy(self.mission)
        mission['goals'] = [dict(latitude=42., longitude=-83., altitude=0., radius_m=.4)]*6
        report = audit(run, self.course, mission, course_sha256=self.hash)
        self.assertTrue(report['checks']['six_destinations_independently_visited_in_order'])
        self.assertFalse(report['checks']['ordered_world_full_loop'])
        self.assertEqual(report['world_topology']['progress_m'], 0.)

    def test_diagonal_shortcut_and_reverse_loop_rejected(self):
        shortcut = walk([(0, 0), (20, 20), (0, 0)])
        reverse = walk([(0, 0), (0, 20), (20, 20), (20, 0), (0, 0)])
        for samples in (shortcut, reverse):
            self.assertFalse(topology_evidence(samples, self.course)['passed'])

    def test_unmarked_shortcut_still_rejected_by_topology(self):
        course = copy.deepcopy(self.course)
        for point in course['centerline']:
            point['painted'] = False
        shortcut = walk([(0, 0), (20, 20), (0, 0)])
        self.assertFalse(topology_evidence(shortcut, course)['passed'])

    def test_axle_pass_does_not_prove_body_containment_or_departure(self):
        ramp = self.course['ramps'][0]
        for path in ([(3, 1.1), (15, 1.1)], [(3, 0), (13.1, 0)]):
            samples = walk(path)
            self.assertTrue(ramp_traversal(samples, ramp)['passed'])
            self.assertFalse(ramp_body_evidence(samples, ramp)['passed'])

    def test_gaps_and_wrong_world_metadata_prevent_certification(self):
        run = copy.deepcopy(self.run)
        run['trajectory'][10][0] += 1.
        result = audit(run, self.course, self.mission, course_sha256=self.hash)
        self.assertFalse(result['paint_crossing_certified'])
        self.assertFalse(result['topology_certified'])
        course = copy.deepcopy(self.course)
        course['frame'] = 'map'
        self.assertFalse(topology_evidence(self.samples, course)['passed'])
        self.assertFalse(paint_evidence(self.samples, course)['passed'])

    def test_unbounded_sweep_produces_failed_report(self):
        run = copy.deepcopy(self.run)
        run['trajectory'] = [[0, 0, 0, 0], [.1, 1000000, 0, 0]]
        result = audit(run, self.course, self.mission, course_sha256=self.hash)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['whole_footprint_paint_sweep_clear'])
        self.assertFalse(result['checks']['all_ramps_body_contained_entry_to_departure'])


if __name__ == '__main__':
    unittest.main()
