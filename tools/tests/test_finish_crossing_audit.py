"""Offline audit adoption of finish-crossing/1; no Unity or ROS process is needed."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_sensor_run import audit
from course_judge import topology_evidence
from export_autonomy_mission import export_mission
from mission_health import MissionHealthLedger
from sensor_telemetry import SensorTelemetry

VERSION = 'finish-crossing/1'
ORIGIN = dict(latitude=42., longitude=-83., altitude=0., world_frame='odom',
              axes='x_east_y_north_z_up')
# Leaves and rejoins the origin along +X, as the generator's loop does.
CORNERS = [(0., 0.), (20., 0.), (20., 20.), (-10., 20.), (-10., 0.), (0., 0.)]
# Ends on y=1 and stops 3.5 m past the line: offset crossing, endpoint far from origin.
# Turn at the WORLD corner, then drift: turning at (-10, 1) pins reachable
# progress at arc 89 (nearest point) until the corridor is exited.
LAP = [(0, 0), (20, 0), (20, 20), (-10, 20), (-10, 0), (-8, 1), (3.5, 1)]


def course_fixture(corners=CORNERS, origin_half_width=3.):
    points = []
    for a, b in zip(corners, corners[1:]):
        count = round(math.dist(a, b))
        for i in range(count):
            points.append(dict(x=a[0]+(b[0]-a[0])*i/count, y=a[1]+(b[1]-a[1])*i/count,
                               painted=True, half_width=3.))
    points.append(dict(points[0]))
    points[0]['half_width'] = points[-1]['half_width'] = origin_half_width
    return dict(frame='odom', units='m', lane_width_m=6., centerline=points,
                obstacles=[dict(id='far', kind='barrel', x=100., y=100., width=.5)],
                ramps=[dict(id='ramp', x=5., y=0., yaw=0., width=3.,
                            rise_length=3., deck_length=2.)])


def walk(points, step=.2):
    samples = [[0., float(points[0][0]), float(points[0][1]), 0.]]
    for a, b in zip(points, points[1:]):
        count = max(1, math.ceil(math.dist(a, b)/step))
        yaw = math.atan2(b[1]-a[1], b[0]-a[0])
        for i in range(1, count+1):
            samples.append([samples[-1][0]+.1, a[0]+(b[0]-a[0])*i/count,
                            a[1]+(b[1]-a[1])*i/count, yaw])
    return samples


class FinishCrossingAuditTests(unittest.TestCase):
    def setUp(self):
        self.course = course_fixture()
        self.mission = export_mission({'origin': dict(ORIGIN)}, self.course)

    def run_for(self, samples, course=None, mission=None, finish=None):
        """Complete run evidence, with a sampled health ledger bound to every row."""
        course, mission = course or self.course, mission or self.mission
        course_hash = hashlib.sha256(json.dumps(course).encode()).hexdigest()
        mission_hash = hashlib.sha256(json.dumps(mission).encode()).hexdigest()
        clock = [0.]
        telemetry = SensorTelemetry(clock=lambda: clock[0])
        ledger = MissionHealthLedger(event_limit=32)
        ledger.begin(0., round(samples[0][0]*1e9))
        for row in samples:
            clock[0] = row[0]-samples[0][0]
            stamp = round(row[0]*1e9)
            # Lanes are visible and every health Boolean passes at every sample.
            telemetry.observe_clock(stamp)
            telemetry.status('lanes', {'valid': True, 'stamp_ns': stamp})
            telemetry.status('depth_processing', {'valid': True, 'stamp_ns': stamp})
            telemetry.status('lane_health', True)
            telemetry.status('depth_health', True)
            ledger.observe(telemetry.health_summary(), clock[0], stamp)
        run = dict(status='completed', mode='sensor-led', completed_destinations=6,
                   total_destinations=6, trajectory=samples,
                   sim_status=f'course_hash={course_hash} line_guard=scoring line_blocks=0',
                   mission_sha256=mission_hash, elapsed_wall_s=samples[-1][0]-samples[0][0],
                   mission_health_interval=ledger.end(clock[0], stamp),
                   health_trajectory_start_index=0, health_trajectory_end_index=len(samples)-1,
                   sensor_health=telemetry.report(),
                   finish_crossing=dict(contract_version=VERSION) if finish is None else finish)
        return run, course_hash, mission_hash

    def judge(self, samples, *, course=None, mission=None, finish=None, legacy=False):
        run, course_hash, mission_hash = self.run_for(samples, course, mission, finish)
        if legacy:
            del run['finish_crossing']
        return audit(run, course or self.course, mission or self.mission,
                     course_sha256=course_hash, mission_sha256=mission_hash)

    def test_offset_crossing_with_full_evidence_passes_without_final_point(self):
        result = self.judge(walk(LAP))
        self.assertTrue(result['passed'], {k: v for k, v in result['checks'].items() if not v})
        self.assertEqual(result['finish_contract'], VERSION)
        checks = result['checks']
        for name in ('sensor_health_interval_verified', 'sensor_health_latest_processing_passes',
                     'finish_contract_supported', 'five_destinations_independently_visited_in_order',
                     'finish_line_crossed_after_ordered_visits', 'ordered_world_full_loop',
                     'whole_footprint_paint_sweep_clear', 'all_ramps_body_contained_entry_to_departure'):
            self.assertTrue(checks[name], name)
        self.assertNotIn('returned_within_0_4_m', checks)
        self.assertNotIn('six_destinations_independently_visited_in_order', checks)
        crossing = result['finish_crossing']['audit']['crossing']
        self.assertAlmostEqual(crossing['lateral_m'], 1.)
        self.assertGreater(math.hypot(crossing['x'], crossing['y']), .4)
        self.assertGreater(result['final_distance_to_origin_m'], .4)
        topology = result['world_topology']
        self.assertGreaterEqual(topology['crossing_previous_sample_index'],
                                topology['gates_completed_sample_index'])
        self.assertGreater(topology['progress_m'], topology['total_arc_m'])

    def test_same_trajectory_fails_legacy_point_semantics(self):
        result = self.judge(walk(LAP), legacy=True)
        self.assertEqual(result['finish_contract'], 'legacy')
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['returned_within_0_4_m'])
        self.assertFalse(result['checks']['ordered_world_full_loop'])
        self.assertNotIn('finish_line_crossed_after_ordered_visits', result['checks'])

    def test_runtime_claims_are_not_proof_of_crossing(self):
        claimed = dict(contract_version=VERSION, crossed=True, samples_observed=999,
                       crossing=dict(previous_sample_index=1, sample_index=2))
        result = self.judge(walk(LAP[:-1]+[(-1, 1)]), finish=claimed)
        self.assertFalse(result['checks']['finish_line_crossed_after_ordered_visits'])
        self.assertFalse(result['checks']['ordered_world_full_loop'])
        self.assertFalse(result['passed'])

    def test_early_ineligible_crossing_does_not_latch_or_count(self):
        start = [[0., 0., 0., 0.]]
        for x in [-.2*i for i in range(1, 8)] + [-1.4+.2*i for i in range(1, 8)]:
            start.append([start[-1][0]+.1, x, 0., 0.])
        samples = start + [[start[-1][0]+row[0], *row[1:]] for row in walk([(0, 0)]+LAP[1:])[1:]]
        result = self.judge(samples)
        self.assertTrue(result['passed'], {k: v for k, v in result['checks'].items() if not v})
        self.assertGreater(result['finish_crossing']['audit']['crossing']['previous_sample_index'],
                           result['finish_crossing']['fifth_visit_sample_index'])
        stopped = samples[:next(i for i, r in enumerate(samples) if i > 20 and r[1] > -1 and r[2] == 1)]
        result = self.judge(stopped)
        self.assertFalse(result['checks']['finish_line_crossed_after_ordered_visits'])
        self.assertFalse(result['passed'])

    def test_crossing_before_final_gate_cannot_complete_topology(self):
        samples = walk(LAP)
        result = topology_evidence(samples, self.course, finish_crossing=True,
                                   crossing=dict(previous_sample_index=3, sample_index=4))
        self.assertFalse(result['passed'])
        self.assertEqual(result['gates_visited'], result['gates_required'])
        result = topology_evidence(samples, self.course, finish_crossing=True, crossing=None)
        self.assertFalse(result['passed'])

    def test_no_crossing_and_reverse_crossing_fail(self):
        for name, lap in (('none', LAP[:-1]+[(-1, 1)]),
                          ('reverse', LAP[:4]+[(-10, 4.5), (1.5, 4.5), (1.5, 1), (-2, 1)])):
            with self.subTest(name):
                result = self.judge(walk(lap))
                self.assertIsNone(result['finish_crossing']['audit']['crossing'])
                self.assertFalse(result['checks']['finish_line_crossed_after_ordered_visits'])
                self.assertFalse(result['passed'])

    def test_crossing_outside_span_fails(self):
        result = self.judge(walk(LAP[:4]+[(-10, 2), (-1.2, 2), (-.2, 3.8), (1.5, 3.8)]))
        self.assertEqual(result['finish_crossing']['audit']['last_candidate']['outcome'], 'outside_span')
        self.assertFalse(result['checks']['finish_line_crossed_after_ordered_visits'])
        self.assertFalse(result['passed'])

    def test_unsupported_or_malformed_version_fails_closed_without_legacy(self):
        for finish in (dict(contract_version='finish-crossing/2'), dict(), VERSION,
                       dict(contract_version=None)):
            with self.subTest(finish=finish):
                result = self.judge(walk(LAP), finish=finish)
                self.assertEqual(result['finish_contract'], 'unsupported')
                self.assertFalse(result['checks']['finish_contract_supported'])
                self.assertFalse(result['checks']['finish_line_crossed_after_ordered_visits'])
                self.assertNotIn('returned_within_0_4_m', result['checks'])
                self.assertFalse(result['passed'])

    def test_claimed_line_or_limits_mismatch_rejected_not_adopted(self):
        line = dict(center_xy=[0., 0.], normal_xy=[1., 0.], half_span_m=5.)
        for key, value in (('line', line), ('max_speed_mps', 3.), ('max_interval_s', 1.),
                           ('max_step_m', True)):
            with self.subTest(key=key):
                result = self.judge(walk(LAP), finish={'contract_version': VERSION, key: value})
                self.assertIn(f'claimed_{key}_mismatch',
                              result['finish_crossing']['compatibility']['reasons'])
                self.assertFalse(result['passed'])

    def test_rotated_narrow_or_origin_incompatible_fixture_fails(self):
        square = course_fixture([(0., 0.), (20., 0.), (20., 20.), (0., 20.), (0., 0.)])
        frameless = export_mission({'origin': dict(latitude=42., longitude=-83., altitude=0.)}, self.course)
        for name, course, mission, reason in (
                ('rotated', square, export_mission({'origin': dict(ORIGIN)}, square),
                 'world_last_segment_not_plus_x'),
                ('narrow', course_fixture(origin_half_width=2.5), None, 'world_half_width_below_line_span'),
                ('origin', None, frameless, 'mission_frame_not_odom_x_east_y_north_z_up')):
            with self.subTest(name):
                result = self.judge(walk(LAP), course=course, mission=mission)
                self.assertIn(reason, result['finish_crossing']['compatibility']['reasons'])
                self.assertFalse(result['checks']['finish_contract_supported'])
                self.assertFalse(result['passed'])

    def test_skipped_ordered_gates_fail(self):
        result = self.judge(walk([(0, 0), (15, 0), (20, 10)]+LAP[2:]))
        topology = result['world_topology']
        self.assertLess(topology['gates_visited'], topology['gates_required'])
        self.assertFalse(result['checks']['ordered_world_full_loop'])
        self.assertFalse(result['passed'])

    def test_first_five_destination_miss_fails(self):
        result = self.judge(walk([(0, 0), (20, 0), (20, 22.5), (-10, 22.5), (-10, 1), (3.5, 1)]))
        self.assertFalse(result['checks']['five_destinations_independently_visited_in_order'])
        self.assertFalse(result['checks']['finish_line_crossed_after_ordered_visits'])
        self.assertFalse(result['passed'])

    def test_terminal_excursion_past_origin_still_corridor_checked(self):
        result = self.judge(walk(LAP+[(3.5, 4.5)]))
        self.assertTrue(result['checks']['finish_line_crossed_after_ordered_visits'])
        self.assertIn('Outside ordered WORLD corridor', result['world_topology'].get('reason', ''))
        self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
