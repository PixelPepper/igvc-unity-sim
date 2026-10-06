"""Behavior tests: reference_lab `label` output is immutable; any existing generated name refuses the target.

The guard runs before the run folder is loaded, so a placeholder run folder suffices. Fresh output is shown to pass
the guard (it then fails loading the placeholder run, before writing anything); a real labelled run is not exercised.
"""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'tools' / 'reference_lab' / 'ReferenceLab.csproj'
DOTNET = shutil.which('dotnet')


def summary(**fields):
    return json.dumps({'labelled': 1, **fields}) + '\n'


def label_line(**fields):
    return json.dumps({'schema_version': 1, 'index': 0, **fields}) + '\n'


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None) for p in sorted(root.rglob('*'))}


@unittest.skipIf(DOTNET is None, 'dotnet not available')
class LabelOutputIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([DOTNET, 'build', str(PROJECT), '-nologo', '-v', 'q'], check=True, capture_output=True, text=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='label_out_'))
        self.run_dir = self.tmp / 'run_placeholder'
        self.run_dir.mkdir()
        (self.run_dir / 'run.json').write_text('{}', encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def label(self, out, mode='path-v3'):
        cmd = [DOTNET, 'run', '--no-build', '--project', str(PROJECT), '--', 'label', '--run', str(self.run_dir),
               '--out', str(out), '--corridor-label', mode]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    def existing(self, files, mode='path-v3', dirs=()):
        out = self.tmp / 'out'
        out.mkdir()
        for name in dirs:
            (out / name).mkdir()
            (out / name / 'inner.txt').write_text('keep\n', encoding='utf-8')
        for name, text in files.items():
            (out / name).write_text(text, encoding='utf-8')
        before = snapshot(out)
        proc = self.label(out, mode)
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('refusing to write', proc.stdout)
        self.assertIn('fresh --out', proc.stdout)
        self.assertEqual(before, snapshot(out), 'existing output bytes changed')
        return proc.stdout

    def complete(self, mode):
        return {'labels.jsonl': label_line(corridor_label=mode), 'summary.json': summary(corridor_label=mode),
                'traps.json': '[]\n'}

    def test_same_mode_complete_path_v3_refused(self):
        self.assertIn('already exists', self.existing(self.complete('path-v3')))

    def test_same_mode_complete_straight_v1_refused(self):
        self.existing(self.complete('straight-v1'), mode='straight-v1')

    def test_labels_without_summary_refused(self):
        self.existing({'labels.jsonl': label_line(corridor_label='path-v3')})

    def test_traps_only_refused(self):
        self.assertIn('traps.json', self.existing({'traps.json': '[]\n'}))

    def test_truncated_summary_refused(self):
        files = self.complete('path-v3')
        files['summary.json'] = '{"labelled": 1, "corridor_la'
        self.existing(files)

    def test_corrupt_labels_and_empty_traps_refused(self):
        self.existing({'labels.jsonl': '{not json\n', 'summary.json': summary(corridor_label='path-v3'), 'traps.json': ''})

    def test_named_directory_collisions_refused(self):
        for name in ('summary.json', 'labels.jsonl', 'traps.json'):
            with self.subTest(name=name):
                self.assertIn(name, self.existing({}, dirs=(name,)))
                shutil.rmtree(self.tmp / 'out')

    def test_unlabelled_legacy_output_refused(self):
        files = {'labels.jsonl': label_line(), 'summary.json': summary(), 'traps.json': '[]\n'}
        self.existing(files, mode='straight-v1')

    def test_path_v2_corridor_cost_metadata_refused(self):
        files = {'labels.jsonl': label_line(corridor_cost='path-v2'), 'summary.json': summary(corridor_cost='path-v2'),
                 'traps.json': '[]\n'}
        self.existing(files)

    def test_different_mode_refused(self):
        self.existing(self.complete('straight-v1'))

    def test_target_file_refused(self):
        out = self.tmp / 'out'
        out.write_bytes(b'not a directory\n')
        proc = self.label(out)
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('target is a file', proc.stdout)
        self.assertEqual(out.read_bytes(), b'not a directory\n')

    def test_fresh_output_passes_guard_and_writes_nothing_on_load_failure(self):
        out = self.tmp / 'fresh'
        proc = self.label(out)
        self.assertNotIn('refusing to write', proc.stdout)
        self.assertIn('FAILED', proc.stdout)  # placeholder run cannot load; guard did not block it
        self.assertFalse(out.exists())

    def test_empty_or_unrelated_directory_passes_guard(self):
        out = self.tmp / 'out'
        out.mkdir()
        proc = self.label(out)
        self.assertNotIn('refusing to write', proc.stdout)
        self.assertIn('FAILED', proc.stdout)
        (out / 'notes.txt').write_bytes(b'unrelated\n')
        proc = self.label(out)
        self.assertNotIn('refusing to write', proc.stdout)
        self.assertIn('FAILED', proc.stdout)
        self.assertEqual(snapshot(out), {'notes.txt': b'unrelated\n'})


if __name__ == '__main__':
    unittest.main()
