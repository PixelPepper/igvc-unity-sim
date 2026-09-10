"""Docker report lifecycle regressions, using isolated synthetic artifacts."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import generate_course_variant as generator


class DockerReportingTests(unittest.TestCase):
    def test_new_course_archives_and_invalidates_previous_docker_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Path('ros2/src/igvc_gps/config/full_loop.json')
            (root / config).parent.mkdir(parents=True)
            shutil.copyfile(TOOLS.parent / config, root / config)
            output = root / 'artifacts/courses/seed-2027'
            output.mkdir(parents=True)
            previous = {
                'course.json': '{"previous_course": true}',
                'mission.json': '{"previous_mission": true}',
                'docker-run.json': '{"status": "completed"}',
                'validation.json': '{"passed": true}',
                'docker-unity.log': 'previous Unity session',
            }
            for name, value in previous.items():
                (output / name).write_text(value)
            with patch.object(generator, 'ROOT', root), patch.object(generator, 'render'), \
                    patch.object(sys, 'argv', ['generate_course_variant.py', '--seed', '2027']), \
                    contextlib.redirect_stdout(io.StringIO()):
                generator.main()
            archives = list(output.glob('previous-*'))
            self.assertEqual(len(archives), 1, 'Previous Docker evidence must be retained')
            for name, value in previous.items():
                self.assertEqual((archives[0] / name).read_text(), value)
            self.assertFalse((output / 'docker-run.json').exists(), 'A fresh session must not reuse a completed run')
            self.assertFalse((output / 'validation.json').exists(), 'A fresh session must not expose a stale pass')
            self.assertEqual(json.loads((output / 'course.json').read_text())['seed'], 2027)
            mission = json.loads((output / 'mission.json').read_text())
            self.assertEqual(mission['course_sha256'], hashlib.sha256((output / 'course.json').read_bytes()).hexdigest())

    def test_auditor_exit_code_tracks_report_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            course = {'schema_version': 1, 'frame': 'odom', 'seed': 2027,
                      'obstacles': [{'id': 'distant-barrel', 'kind': 'barrel', 'x': 10.,
                                     'y': 10., 'yaw': 0., 'length': 1., 'width': 1.,
                                     'height': 1., 'depth': 0.}]}
            course_path = root / 'course.json'
            course_path.write_text(json.dumps(course))
            course_hash = hashlib.sha256(course_path.read_bytes()).hexdigest()
            run = {'status': 'completed', 'total_waypoints': 1, 'completed_waypoints': 1,
                   'run_id': 5, 'trajectory': [[1., 0., 0., 0.], [1.2, 0., 0., 0.]],
                   'audit': {'ordered_waypoints_visited': 1, 'ordered_waypoints_required': 1,
                             'complete': True, 'valid': True, 'errors': [], 'run_id': 5},
                   'sim_status': f'run=5 line_blocks=0 course_hash={course_hash}'}
            for status, expected_exit in [('completed', 0), ('failed', 1)]:
                with self.subTest(status=status):
                    run['status'] = status
                    run_path = root / 'docker-run.json'
                    run_path.write_text(json.dumps(run))
                    result = subprocess.run([sys.executable, str(TOOLS / 'audit_course_variant.py'),
                                             '--course', str(course_path), '--run', str(run_path)],
                                            capture_output=True, text=True, timeout=30)
                    report = json.loads((root / 'validation.json').read_text())
                    self.assertEqual(report['passed'], status == 'completed')
                    self.assertTrue(report['checks']['runtime_course_hash_matches'])
                    if status == 'failed':
                        self.assertEqual([name for name, passed in report['checks'].items() if not passed],
                                         ['run_completed'])
                    self.assertEqual(result.returncode, expected_exit, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
