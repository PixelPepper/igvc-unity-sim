"""Behavior tests: reference_lab `label` never overwrites existing generated output of unknown or different mode.

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

    def existing(self, files, mode='path-v3'):
        out = self.tmp / 'out'
        out.mkdir()
        for name, text in files.items():
            (out / name).write_text(text, encoding='utf-8')
        before = {p.name: p.read_bytes() for p in out.iterdir()}
        proc = self.label(out, mode)
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('refusing to write', proc.stdout)
        self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()}, 'existing output bytes changed')
        return proc.stdout

    def test_labels_without_summary_refused(self):
        self.existing({'labels.jsonl': label_line(corridor_label='path-v3')})

    def test_unlabelled_legacy_summary_is_not_assumed_straight(self):
        files = {'labels.jsonl': label_line(), 'summary.json': summary(), 'traps.json': '[]\n'}
        self.assertIn('no corridor_label', self.existing(files, mode='straight-v1'))

    def test_path_v2_corridor_cost_metadata_refused(self):
        files = {'labels.jsonl': label_line(corridor_cost='path-v2'), 'summary.json': summary(corridor_cost='path-v2'),
                 'traps.json': '[]\n'}
        self.assertIn('corridor_cost', self.existing(files))

    def test_different_mode_refused(self):
        files = {'labels.jsonl': label_line(corridor_label='straight-v1'),
                 'summary.json': summary(corridor_label='straight-v1'), 'traps.json': '[]\n'}
        self.assertIn('straight-v1', self.existing(files))

    def test_inconsistent_labels_refused(self):
        files = {'labels.jsonl': label_line(corridor_label='path-v3') + label_line(corridor_label='straight-v1'),
                 'summary.json': summary(corridor_label='path-v3'), 'traps.json': '[]\n'}
        self.existing(files)

    def test_invalid_summary_refused(self):
        files = {'labels.jsonl': label_line(corridor_label='path-v3'), 'summary.json': '{not json',
                 'traps.json': '[]\n'}
        self.assertIn('not valid JSON', self.existing(files))

    def test_fresh_output_passes_guard_and_writes_nothing_on_load_failure(self):
        out = self.tmp / 'fresh'
        proc = self.label(out)
        self.assertNotIn('refusing to write', proc.stdout)
        self.assertIn('FAILED', proc.stdout)  # placeholder run cannot load; guard did not block it
        self.assertFalse(out.exists())

    def test_matching_complete_output_passes_guard(self):
        out = self.tmp / 'out'
        out.mkdir()
        (out / 'labels.jsonl').write_text(label_line(corridor_label='path-v3'), encoding='utf-8')
        (out / 'summary.json').write_text(summary(corridor_label='path-v3'), encoding='utf-8')
        (out / 'traps.json').write_text('[]\n', encoding='utf-8')
        proc = self.label(out)
        self.assertNotIn('refusing to write', proc.stdout)
        self.assertIn('FAILED', proc.stdout)


if __name__ == '__main__':
    unittest.main()
