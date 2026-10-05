"""Behavioral checks for bounded rule compatibility, without ROS or Unity."""
import contextlib
import copy
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_competition_profile import DEFAULT_PROFILE, main, validate


class CompetitionProfileTests(unittest.TestCase):
    def setUp(self):
        self.course = {'units': 'm', 'ramps': [{'height': .45, 'rise_length': 3.}],
                       'obstacles': [{'kind': 'pothole', 'width': .6096, 'length': .6096,
                                      'depth': 0., 'color': 'white', 'representation': 'solid_white_circle'}],
                       'passage_widths_m': [1.524, 1.6]}
        self.autonomy = {'schema_version': 1, 'origin': {}, 'goals': [{} for _ in range(4)],
                         'max_speed_mps': 2.2352}
        self.settings = {'timeout_wall_s': 360., 'requested_speed_mps': 2.2352,
                         'waypoint_pairs': [[0, 1], [2, 3]], 'guidance': 'organizer_waypoints'}

    def report(self, **kwargs):
        return validate(self.course, self.autonomy, settings=self.settings, **kwargs)

    def check(self, name, report=None):
        return next(c for c in (report or self.report())['checks'] if c['id'] == name)

    def test_exact_imperial_conversions_and_hardware_unknown(self):
        report = self.report()
        self.assertEqual(report['configuration_status'], 'pass')
        self.assertEqual(report['status'], 'unknown')
        self.assertFalse(report['certification'])
        self.assertEqual(self.check('configured_speed_cap')['expected'], 2.2352)
        self.assertEqual(self.check('pothole_diameter_0')['expected'], .6096)
        self.assertEqual(self.check('minimum_passage')['expected'], 1.524)

    def test_fifteen_degrees_exceeds_fifteen_percent(self):
        self.course['ramps'][0]['height'] = 3 * math.tan(math.radians(15))
        self.assertEqual(self.check('ramp_grade_0')['status'], 'fail')
        self.course['ramps'][0]['height'] = .45
        self.assertEqual(self.check('ramp_grade_0')['status'], 'pass')

    def test_white_circle_does_not_make_a_depression_compliant(self):
        hole = self.course['obstacles'][0]
        self.assertEqual(self.check('pothole_representation_0')['status'], 'pass')
        hole['depth'] = .15
        self.assertEqual(self.check('pothole_representation_0')['status'], 'fail')
        hole['depth'] = 0
        hole['color'] = '#48494a'
        self.assertEqual(self.check('pothole_representation_0')['status'], 'fail')
        hole.pop('representation'); hole.pop('color')
        self.assertEqual(self.check('pothole_representation_0')['status'], 'unknown')

    def test_training_time_speed_and_guidance_mismatches(self):
        self.settings.update(timeout_wall_s=600., requested_speed_mps=3., guidance='generated_regions')
        self.autonomy['goals'] += [{}, {}]
        self.autonomy['max_speed_mps'] = 3.
        for name in ('configured_run_timeout', 'requested_speed_cap', 'configured_speed_cap',
                     'organizer_waypoint_count', 'organizer_waypoint_guidance'):
            self.assertEqual(self.check(name)['status'], 'fail', name)

    def test_pairing_cannot_repeat_a_destination(self):
        self.settings['waypoint_pairs'] = [[0, 1], [1, 3]]
        self.assertEqual(self.check('organizer_waypoint_pairing')['status'], 'fail')

    def test_no_metadata_added_to_runtime_autonomy(self):
        self.autonomy['competition'] = {'run_timeout_s': 360}
        self.assertEqual(self.check('sanitized_autonomy_keys')['status'], 'fail')

    def test_lane_width_does_not_establish_passage_clearance(self):
        self.course.pop('passage_widths_m'); self.course['lane_width_m'] = 6.
        self.assertEqual(self.check('minimum_passage')['status'], 'unknown')
        self.course['passage_widths_m'] = [1.523]
        self.assertEqual(self.check('minimum_passage')['status'], 'fail')

    def test_sampled_speed_can_disprove_but_not_certify(self):
        run = {'trajectory': [[0, 0, 0, 0], [1, 3, 0, 0]],
               'timeout_wall_s': 600, 'requested_speed_mps': 2.2, 'elapsed_wall_s': 400}
        report = self.report(run=run)
        self.assertEqual(self.check('sampled_run_speed', report)['status'], 'fail')
        self.assertEqual(self.check('run_setting_timeout_wall_s', report)['status'], 'fail')
        self.assertEqual(self.check('run_elapsed', report)['status'], 'fail')
        run['trajectory'][1][1] = .5
        self.assertEqual(self.check('sampled_run_speed', self.report(run=run))['status'], 'unknown')
        run['trajectory'][1][0] = 0
        self.assertEqual(self.check('sampled_run_speed', self.report(run=run))['status'], 'unknown')

    def test_speed_window_conflict_preserved(self):
        conflict = self.check('opening_speed_window')
        self.assertEqual(conflict['status'], 'unknown')
        self.assertEqual(conflict['observed']['narrative']['distance_ft'], 44)
        self.assertEqual(conflict['observed']['table']['distance_ft'], 88)

    def test_read_only_cli_json_and_digest_binding(self):
        originals = copy.deepcopy((self.course, self.autonomy, self.settings))
        with tempfile.TemporaryDirectory() as directory:
            paths = {}
            for name, value in zip(('course', 'autonomy', 'settings'), originals):
                paths[name] = Path(directory) / (name + '.json')
                paths[name].write_text(json.dumps(value), encoding='utf-8')
            run = Path(directory) / 'run.json'
            run.write_text(json.dumps({'course_sha256': 'wrong'}), encoding='utf-8')
            before = {p: p.read_bytes() for p in [*paths.values(), run]}
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main([arg for name, p in paths.items() for arg in ('--' + name, str(p))] + ['--run', str(run)])
            report = json.loads(output.getvalue())
            self.assertEqual(code, 1)
            self.assertEqual(self.check('run_course_binding', report)['status'], 'fail')
            self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(originals, (self.course, self.autonomy, self.settings))

    def test_nonfinite_json_is_a_structured_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / 'invalid.json'
            invalid.write_text('{"max_speed_mps":NaN}', encoding='utf-8')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['--course', str(invalid), '--autonomy', str(invalid)])
            self.assertEqual(code, 1)
            self.assertIn('Non-finite', json.loads(output.getvalue())['error'])


if __name__ == '__main__':
    unittest.main()
