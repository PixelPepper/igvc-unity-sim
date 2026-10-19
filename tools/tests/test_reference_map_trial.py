"""Reference-map trial driver: fixed bounds, admission and smoke gates, and the unchanged mission command."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference_map_trial import (DEFAULT_TIMEOUT, MAX_SPEED, MAX_TIMEOUT, build_parser, SMOKE_TOPICS, bounded_settings, evaluate_admission,
                                 evaluate_smoke, mission_command)

NODES = ('/igvc_lane_detector', '/igvc_depth_processor')


class ReferenceMapTrialTests(unittest.TestCase):
    def test_bounds_are_refused_not_clamped(self):
        self.assertEqual(bounded_settings(.6, 360), ({'speed_mps': .6}, 360.))
        for speed, timeout in ((.61, 60), (0, 60), (-.1, 60), (.5, 361), (.5, 0), (math.nan, 60), (.5, math.inf), (True, 60)):
            with self.subTest(speed=speed, timeout=timeout), self.assertRaises(ValueError):
                bounded_settings(speed, timeout)
        self.assertEqual((MAX_SPEED, MAX_TIMEOUT), (.6, 360.))

    def test_cli_default_is_180_and_360_needs_explicit_opt_in(self):
        base = ['--run-dir', '/tmp/run', '--mission', '/tmp/autonomy.json']
        self.assertEqual(build_parser().parse_args(base).timeout, 180.)
        self.assertEqual(DEFAULT_TIMEOUT, 180.)
        self.assertEqual(build_parser().parse_args(base+['--timeout', '360']).timeout, 360.)
        self.assertEqual(bounded_settings(.6, build_parser().parse_args(base).timeout)[1], 180.)

    def test_revalidate_active_path_is_explicit_opt_in(self):
        settings, timeout = bounded_settings(.6, 180)
        base = mission_command('python3', Path('/tmp/autonomy.json'), Path('/tmp/run'), settings, timeout)
        self.assertNotIn('--revalidate-active-path', base)
        opted = mission_command('python3', Path('/tmp/autonomy.json'), Path('/tmp/run'), settings, timeout,
                                revalidate_active_path=True)
        self.assertEqual(opted, base+['--revalidate-active-path'])
        parse = lambda extra: build_parser().parse_args(['--run-dir', '/tmp/r', '--mission', '/tmp/m']+extra)
        self.assertFalse(parse([]).revalidate_active_path)
        self.assertTrue(parse(['--revalidate-active-path']).revalidate_active_path)

    def test_latency_compensation_is_explicit_opt_in(self):
        settings, timeout = bounded_settings(.6, 180)
        base = mission_command('python3', Path('/tmp/autonomy.json'), Path('/tmp/run'), settings, timeout)
        self.assertNotIn('--latency-compensation', base)
        opted = mission_command('python3', Path('/tmp/autonomy.json'), Path('/tmp/run'), settings, timeout,
                                latency_compensation=True)
        self.assertEqual(opted, base+['--latency-compensation'])
        self.assertEqual(settings, {'speed_mps': .6})          # caller's settings are not mutated
        parse = lambda extra: build_parser().parse_args(['--run-dir', '/tmp/r', '--mission', '/tmp/m']+extra)
        self.assertFalse(parse([]).latency_compensation)
        self.assertTrue(parse(['--latency-compensation']).latency_compensation)

    def test_smoke_requires_every_stream_and_positive_clock(self):
        full = {topic: 3 for topic in SMOKE_TOPICS}
        self.assertTrue(evaluate_smoke(full, 1_000)['ok'])
        self.assertFalse(evaluate_smoke(full, 0)['ok'])
        self.assertFalse(evaluate_smoke(full, None)['ok'])
        for topic in SMOKE_TOPICS:
            with self.subTest(missing=topic):
                partial = dict(full, **{topic: 0})
                result = evaluate_smoke(partial, 1_000)
                self.assertFalse(result['ok']); self.assertEqual(result['missing'], [topic])

    def test_admission_requires_true_boolean_on_every_node(self):
        good = dict(admitted=True, nodes=[dict(node=n, status='true', value=True) for n in NODES])
        self.assertTrue(evaluate_admission(good, NODES))
        self.assertFalse(evaluate_admission(dict(good, admitted=False), NODES))
        self.assertFalse(evaluate_admission(dict(good, nodes=good['nodes'][:1]), NODES))
        self.assertFalse(evaluate_admission(dict(good, nodes=[dict(node=n, status='true', value='true') for n in NODES]), NODES))
        self.assertFalse(evaluate_admission(None, NODES))

    def test_mission_command_is_the_unchanged_sensor_course_with_trial_timeout(self):
        settings, timeout = bounded_settings(.6, 150)
        argv = mission_command('python3', Path('/tmp/autonomy.json'), Path('/tmp/run'), settings, timeout)
        self.assertTrue(argv[1].endswith('tools/sensor_course.py'))
        self.assertEqual(argv[argv.index('--timeout')+1], '150')
        self.assertEqual(argv[argv.index('--speed')+1], '0.6')
        self.assertNotIn('--course', argv)


if __name__ == '__main__':
    unittest.main()
