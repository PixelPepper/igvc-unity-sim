"""OKF v0.2 knowledge tooling: conformance vs warnings, trust, freshness, source pins, search, export."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agents'))
import knowledge  # noqa: E402

NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)


def concept(type_='Reference', extra=''):
    return f'---\ntype: {type_}\ntitle: T\ndescription: D\ntags: [a]\n{extra}---\n\nBody.\n'


class KnowledgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'kb'
        self.bundle.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text, newline='\n', prefix=b''):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prefix + text.replace('\n', newline).encode('utf-8'))
        return path

    def load(self):
        return knowledge.Bundle(self.root, 'kb', now=NOW).load()

    def cli(self, *args):
        return knowledge.main(['--root', str(self.root), '--bundle', 'kb', *map(str, args)])

    def codes(self, items):
        return sorted(item['code'] for item in items)

    def test_format_errors_are_only_bad_frontmatter_and_type(self):
        self.write('kb/no-fm.md', 'just text\n')
        self.write('kb/unterminated.md', '---\ntype: X\n')
        self.write('kb/bad-yaml.md', '---\ntype: [unclosed\n---\n')
        self.write('kb/no-type.md', '---\ntitle: x\n---\n')
        self.write('kb/empty-type.md', '---\ntype: "  "\n---\n')
        self.write('kb/list.md', '---\n- a\n---\n')
        self.write('kb/unknown.md', concept('Totally Custom Type', 'weird_extension: {nested: true}\n'))
        self.write('kb/bom.md', concept(), newline='\r\n', prefix=b'\xef\xbb\xbf')
        bundle = self.load()
        self.assertEqual(self.codes(bundle.errors), ['frontmatter_missing', 'frontmatter_not_mapping',
            'frontmatter_unparseable', 'frontmatter_unterminated', 'type_missing_or_empty', 'type_missing_or_empty'])
        self.assertEqual(sorted(n['id'] for n in bundle.nodes), ['bom', 'unknown'])

    def test_reserved_files_follow_their_structure(self):
        cases = {'index-extra-key': ('kb/index.md', '---\nokf_version: "0.2"\nextra: 1\n---\n# S\n',
                                     'index_frontmatter_only_okf_version'),
                 'index-nested': ('kb/sub/index.md', '---\nokf_version: "0.2"\n---\n# S\n',
                                  'index_frontmatter_outside_root'),
                 'index-unterminated': ('kb/index.md', '---\nokf_version: "0.2"\n# S\n', 'index_frontmatter_unterminated'),
                 'log-order': ('kb/log.md', '# Log\n\n## 2026-09-01\n* a\n\n## 2026-10-01\n* b\n', 'log_not_newest_first'),
                 'log-non-date': ('kb/log.md', '# Log\n\n## Recent changes\n* a\n', 'log_heading_not_iso_date'),
                 'log-frontmatter': ('kb/log.md', '---\nx: 1\n---\n# Log\n', 'log_frontmatter_not_allowed')}
        for name, (rel, text, code) in cases.items():
            with self.subTest(name):
                for stale in self.bundle.rglob('*.md'):
                    stale.unlink()
                self.write(rel, text)
                self.assertEqual(self.codes(self.load().errors), [code])

    def test_links_are_soft_and_produce_edges(self):
        self.write('kb/a.md', concept() + '[b](b.md) [root](/sub/c.md) [gone](missing.md) '
                   '[ext](../outside.txt) [url](https://example.com/x) [anchor](#top)\n')
        self.write('kb/b.md', concept())
        self.write('kb/sub/c.md', concept())
        bundle = self.load()
        self.assertEqual(bundle.errors, [])
        edges = {(e['source'], e['target']) for e in bundle.edges if e['kind'] == 'link'}
        self.assertEqual(edges, {('a', 'b'), ('a', 'sub/c')})
        self.assertIn('broken_link', self.codes(bundle.warnings))
        self.assertIn('missing_external_target', self.codes(bundle.warnings))

    def test_trust_counts_only_well_formed_events(self):
        at = 'at: 2026-10-01T00:00:00Z'
        cases = {'none': ('', 'unverified'),
                 'bare': (f'verified: {{ by: "human:alice", {at} }}\n', 'human-reviewed'),
                 'list': (f'verified:\n  - {{ by: "process:nightly", {at} }}\n', 'machine-confirmed'),
                 'mixed': (f'verified:\n  - {{ by: "process:nightly", {at} }}\n  - {{ by: "human:bob" }}\n',
                           'machine-confirmed'),
                 'naive': ('verified: { by: "human:alice", at: "2026-10-01T00:00:00" }\n', 'unverified'),
                 'empty-actor': (f'verified: {{ by: "", {at} }}\n', 'unverified'),
                 'empty-list': ('verified: []\n', 'unverified'),
                 'scalar': ('verified: yes\n', 'unverified')}
        for name, (extra, _) in cases.items():
            self.write(f'kb/{name}.md', concept(extra=extra))
        bundle = self.load()
        self.assertEqual({n['id']: n['trust'] for n in bundle.nodes}, {k: v for k, (_, v) in cases.items()})
        flagged = {w['path'].split('/')[-1][:-3] for w in bundle.warnings if w['code'] == 'malformed_verified_event'}
        self.assertEqual(flagged, {'mixed', 'naive', 'empty-actor', 'empty-list', 'scalar'})
        self.assertEqual(bundle.errors, [])

    def test_stale_after_is_a_timezone_aware_comparison(self):
        self.write('kb/past.md', concept(extra='stale_after: 2026-10-01T00:00:00Z\n'))
        self.write('kb/future.md', concept(extra='stale_after: 2027-01-01T00:00:00+00:00\n'))
        self.write('kb/naive.md', concept(extra='stale_after: "2026-10-01T00:00:00"\n'))
        bundle = self.load()
        self.assertEqual({n['id']: n['freshness'] for n in bundle.nodes},
                         {'past': 'stale', 'future': 'current', 'naive': 'unknown'})
        self.assertEqual(bundle.errors, [])

    def test_source_pins_report_drift_and_block_unsafe_paths(self):
        source = self.write('src/doc.md', 'line one\nline two\n')
        digest = knowledge.normalized_sha256(source.read_bytes())
        self.write('src/crlf.md', 'line one\nline two\n', newline='\r\n', prefix=b'\xef\xbb\xbf')
        self.assertEqual(knowledge.normalized_sha256((self.root / 'src/crlf.md').read_bytes()), digest)
        pins = (f'igvc_sources:\n  - {{path: src/doc.md, sha256: {digest}}}\n'
                f'  - {{path: src/crlf.md, sha256: {digest}}}\n'
                '  - {path: src/gone.md, sha256: x}\n  - {path: ../escape.md, sha256: x}\n'
                '  - {path: /etc/passwd, sha256: x}\n')
        self.write('kb/pins.md', concept(extra=pins))
        status = {s['path']: s['status'] for s in self.load().nodes[0]['sources_status']}
        self.assertEqual(status, {'src/doc.md': 'match', 'src/crlf.md': 'match', 'src/gone.md': 'missing',
                                  '../escape.md': 'blocked', '/etc/passwd': 'blocked'})
        source.write_text('line one\nchanged\n', encoding='utf-8')
        bundle = self.load()
        self.assertEqual(bundle.nodes[0]['sources_status'][0]['status'], 'changed')
        self.assertIn('source_changed', self.codes(bundle.warnings))
        self.assertEqual(bundle.errors, [])
        self.assertIn(digest, (self.bundle / 'pins.md').read_text())  # the pin was not rewritten

    def test_pin_policy_refuses_sensitive_or_generated_paths_before_reading(self):
        # Synthetic files only; contents are never read when policy refuses the path.
        refused = {'artifacts/run.json': 'excluded_location', '.git/config.txt': 'excluded_location',
                   'ros2/build/x.txt': 'excluded_location', 'unity/IGVCSim/Library/a.txt': 'excluded_location',
                   'tools/agents/node_modules/p.js': 'excluded_location', '.env': 'credential_like_name',
                   'keys/server.pem': 'credential_like_name', 'docs/api_token.txt': 'credential_like_name',
                   'docs/picture.png': 'not_allowed_text_type', 'docs/../x.md': 'escapes_repository'}
        for rel, reason in refused.items():
            with self.subTest(rel):
                self.write(rel.replace('docs/../', ''), 'synthetic\n')
                self.assertEqual(knowledge.resolve_inside(self.root, rel), (None, reason))
        self.write('kb/s.md', concept(extra='igvc_sources:\n  - {path: artifacts/run.json, sha256: x}\n'))
        self.assertEqual(self.load().nodes[0]['sources_status'][0], {'path': 'artifacts/run.json',
                         'status': 'blocked', 'reason': 'excluded_location'})
        self.write('docs/latin1.md', 'x')
        (self.root / 'docs/latin1.md').write_bytes(b'\xff\xfe bad')
        self.write('docs/ok.md', 'fine\n')
        self.assertEqual(self.cli('pin', 'docs/ok.md'), 0)
        for bad in ('docs/latin1.md', 'artifacts/run.json', 'missing.md'):
            self.assertEqual(self.cli('pin', bad), 1)

    @unittest.skipIf(os.name == 'nt', 'symlink creation needs privileges on Windows')
    def test_symlinked_source_is_refused(self):
        outside = Path(tempfile.mkdtemp())
        (outside / 'notes.md').write_text('x', encoding='utf-8')
        os.symlink(outside, self.root / 'link')
        self.write('kb/s.md', concept(extra='igvc_sources:\n  - {path: link/notes.md, sha256: x}\n'))
        self.assertEqual(self.load().nodes[0]['sources_status'][0]['reason'], 'symlink_refused')

    def test_unusual_yaml_values_become_safe_json_with_warnings(self):
        extra = ('ratio: .nan\nlimit: .inf\nseen: !!set {b: null, a: null}\nblob: !!binary aGk=\n'
                 'loop: &loop [1, *loop]\n')
        self.write('kb/odd.md', '---\ntype: Reference\ntitle: [not, a, string]\ndescription: 7\n'
                   f'tags: {{x: 1}}\n{extra}---\n\nlidar body\n')
        bundle = self.load()
        self.assertEqual(bundle.errors, [])
        codes = set(self.codes(bundle.warnings))
        self.assertTrue({'nonfinite_number_replaced', 'set_converted_to_sorted_list', 'binary_value_replaced',
                         'recursive_value_replaced', 'title_not_string', 'description_not_string'} <= codes, codes)
        self.assertEqual(bundle.search('lidar')[0]['id'], 'odd')
        out = self.root / 'odd.json'
        self.assertEqual(self.cli('--now', '2026-10-05T12:00:00Z', 'export', '--output', out), 0)
        metadata = json.loads(out.read_text())['nodes'][0]['metadata']
        self.assertEqual((metadata['ratio'], metadata['seen'], metadata['blob']), (None, ['a', 'b'], None))

    def test_search_is_bounded_and_ranked(self):
        for i in range(60):
            self.write(f'kb/c{i:02d}.md', concept() + ('lidar ' * (1 + i % 3)))
        bundle = self.load()
        self.assertEqual(len(bundle.search('lidar', limit=500)), knowledge.MAX_LIMIT)
        self.assertEqual(bundle.search('lidar', limit=1)[0]['id'], 'c02')

    def test_strict_project_is_explicit_curation_not_conformance(self):
        self.write('kb/a.md', '---\ntype: Reference\n---\nBody\n')  # conformant, missing project fields
        self.assertEqual(self.cli('check'), 0)
        self.assertEqual(self.cli('check', '--strict-project'), 1)

    def test_bundle_outside_root_is_a_graceful_error(self):
        self.assertEqual(knowledge.main(['--root', str(self.root), '--bundle', '../elsewhere', 'check']), 2)

    def test_export_is_deterministic_and_failure_keeps_last_good_file(self):
        self.write('kb/a.md', concept())
        first, second = self.root / 'o1.json', self.root / 'o2.json'
        for out in (first, second):
            self.assertEqual(self.cli('--now', '2026-10-05T12:00:00Z', 'export', '--output', out), 0)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        document = json.loads(first.read_text())
        self.assertEqual((document['schema_version'], document['okf_version'], document['project_id'],
                          document['bundle_path'], document['generated_at']),
                         (1, '0.2', 'igvc-unity-sim', 'kb', '2026-10-05T12:00:00+00:00'))
        self.assertNotIn(str(self.root), first.read_text())
        good = first.read_bytes()
        self.write('kb/broken.md', 'no frontmatter\n')
        self.assertEqual(self.cli('--now', '2026-10-06T00:00:00Z', 'export', '--output', first), 1)
        self.assertEqual(first.read_bytes(), good)  # last good export retained, old generated_at included
        fresh = self.root / 'never.json'
        self.assertEqual(self.cli('export', '--output', fresh), 1)
        self.assertFalse(fresh.exists())

    def test_project_bundle_is_format_valid(self):
        # Drift is advisory and covered by synthetic fixtures above; this asserts OKF conformance only.
        bundle = knowledge.Bundle(knowledge.DEFAULT_ROOT, 'docs/knowledge').load()
        self.assertEqual(bundle.errors, [])
        self.assertGreaterEqual(len(bundle.nodes), 7)


if __name__ == '__main__':
    unittest.main()
