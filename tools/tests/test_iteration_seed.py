"""Recording-mode trial seed: default 2027, explicit held-out seeds, invalid values rejected."""
import importlib.util
from pathlib import Path
import sys
import unittest

AGENTS = Path(__file__).resolve().parents[1]/'agents'
spec = importlib.util.spec_from_file_location('iteration_mission', AGENTS/'iteration-mission.py')
iteration_mission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iteration_mission)

WORKSPACE, JOB = Path('/w'), Path('/j')  # built with Path, so expectations also hold on native Windows


def mission_path(seed):
    return str(WORKSPACE/f'artifacts/courses/seed-{seed}/autonomy.json')


LEGACY_2027 = [sys.executable, str(WORKSPACE/'tools/sensor_course.py'), '--mission', mission_path(2027),
               '--report', str(JOB/'run.json'), '--capture-dir', str(JOB/'decisions'), '--timeout', '600',
               '--speed', '0.6', '--planning-budget', '0.5', '--path-execution', 'checked-path']


class IterationMissionSeedTest(unittest.TestCase):
    def parse(self, *extra):
        args = iteration_mission.build_parser().parse_args(['/w', '/j', *extra])
        return iteration_mission.commands(args.workspace, args.job, args.seed)

    def test_default_reproduces_the_previous_2027_commands(self):
        record, mission = self.parse()
        self.assertEqual(mission, LEGACY_2027)
        self.assertEqual(record, [sys.executable, str(WORKSPACE/'tools/record_navigation_episode.py'), '--output',
                                  str(JOB/'episode'), '--duration', '660', '--image-hz', '2'])

    def test_explicit_seed_selects_only_the_course_folder(self):
        default_record, _ = self.parse()
        for seed in (2028, 2029, 0, 2147483647):
            with self.subTest(seed=seed):
                record, mission = self.parse('--seed', str(seed))
                self.assertEqual(record, default_record)  # recorder options unchanged
                expected = list(LEGACY_2027)
                expected[3] = mission_path(seed)
                self.assertEqual(mission, expected)
                self.assertEqual([a for a in mission if 'seed-' in a], [expected[3]])

    def test_invalid_seeds_are_rejected_by_the_parser(self):
        for text in ('-1', '1.5', '2028.0', 'x', '', 'true', '2147483648', '+5', ' 2028', '２０２８'):
            with self.subTest(text=text), self.assertRaises(SystemExit):
                iteration_mission.build_parser().parse_args(['/w', '/j', '--seed', text])


if __name__ == '__main__':
    unittest.main()
