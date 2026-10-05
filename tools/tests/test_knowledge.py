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

    def write(self, rel, text, newline='\n'):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace('\n', newline).encode('utf-8'))
        return path

    def load(self):
        return knowledge.Bundle(self.root, 'kb', now=NOW).load()

    def codes(self, items):
        return sorted(item['code'] for item in items)

    def test_format_errors_are_only_missing_or_bad_frontmatter_and_type(self):
        self.write('kb/no-fm.md', 'just text\n')
        self.write('kb/bad-yaml.md', '---\ntype: [unclosed\n---\n')
        self.write('kb/no-type.md', '---\ntitle: x\n---\n')
        self.write('kb/empty-type.md', '---\ntype: "  "\n---\n')
        self.write('kb/list.md', '---\n- a\n---\n')
        self.write('kb/unknown.md', concept('Totally Custom Type', 'weird_extension: {nested: true}\n'))
        bundle = self.load()
        self.assertEqual(self.codes(bundle.errors), ['frontmatter_missing', 'frontmatter_not_mapping',
            'frontmatter_unparseable', 'type_missing_or_empty', 'type_missing_or_empty'])
        self.assertEqual([n['id'] for n in bundle.nodes], ['unknown'])

    def test_links_are_soft_and_produce_edges(self):
        self.write('kb/a.md', concept(extra='') + '[b](b.md) [root](/sub/c.md) [gone](missing.md) '
                   '[ext](../outside.txt) [url](https://example.com/x) [anchor](#top)\n')
        self.write('kb/b.md', concept())
        self.write('kb/sub/c.md', concept())
        bundle = self.load()
        self.assertEqual(bundle.errors, [])
        edges = {(e['source'], e['target']) for e in bundle.edges if e['kind'] == 'link'}
        self.assertEqual(edges, {('a', 'b'), ('a', 'sub/c')})
        self.assertIn('broken_link', self.codes(bundle.warnings))
        self.assertIn('missing_external_target', self.codes(bundle.warnings))

    def test_trust_tiers_from_verified_only(self):
        cases = {'none': ('', 'unverified'),
                 'bare': ('verified: { by: "human:alice", at: 2026-10-01T00:00:00Z }\n', 'human-reviewed'),
                 'list': ('verified:\n  - { by: "process:nightly", at: 2026-10-01T00:00:00Z }\n', 'machine-confirmed'),
                 'bad': ('verified: yes\n', 'unverified')}
        for name, (extra, _) in cases.items():
            self.write(f'kb/{name}.md', concept(extra=extra + 'status: stable\n'))
        bundle = self.load()
        tiers = {n['id']: n['trust'] for n in bundle.nodes}
        self.assertEqual(tiers, {name: tier for name, (_, tier) in cases.items()})
        self.assertIn('malformed_verified', self.codes(bundle.warnings))
        self.assertEqual({n['lifecycle'] for n in bundle.nodes}, {'stable'})

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
        self.write('src/crlf.md', 'line one\nline two\n', newline='\r\n')
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
        self.assertEqual(knowledge.normalized_sha256(source.read_bytes()) != digest, True)  # pin was not rewritten

    @unittest.skipIf(os.name == 'nt', 'symlink creation needs privileges on Windows')
    def test_symlinked_source_is_refused(self):
        outside = Path(tempfile.mkdtemp())
        (outside / 'secret.md').write_text('x', encoding='utf-8')
        os.symlink(outside, self.root / 'link')
        self.write('kb/s.md', concept(extra='igvc_sources:\n  - {path: link/secret.md, sha256: x}\n'))
        self.assertEqual(self.load().nodes[0]['sources_status'][0]['reason'], 'symlink_refused')

    def test_reserved_files_follow_their_structure(self):
        self.write('kb/index.md', '---\nokf_version: "0.2"\nextra: 1\n---\n# S\n')
        self.write('kb/sub/index.md', '---\nokf_version: "0.2"\n---\n# S\n')
        self.write('kb/log.md', '# Log\n\n## 2026-09-01\n* a\n\n## 2026-10-01\n* b\n')
        self.assertEqual(self.codes(self.load().errors), ['index_frontmatter_only_okf_version',
            'index_frontmatter_outside_root', 'log_not_newest_first'])

    def test_search_is_bounded_and_ranked(self):
        for i in range(60):
            self.write(f'kb/c{i:02d}.md', concept() + ('lidar ' * (1 + i % 3)))
        bundle = self.load()
        self.assertEqual(len(bundle.search('lidar', limit=500)), knowledge.MAX_LIMIT)
        top = bundle.search('lidar', limit=1)
        self.assertEqual(top[0]['id'], 'c02')

    def test_export_is_deterministic_portable_and_refuses_invalid_bundles(self):
        self.write('kb/a.md', concept())
        out1, out2 = self.root / 'o1.json', self.root / 'o2.json'
        for out in (out1, out2):
            self.assertEqual(knowledge.main(['--root', str(self.root), '--bundle', 'kb',
                                             '--now', '2026-10-05T12:00:00Z', 'export', '--output', str(out)]), 0)
        self.assertEqual(out1.read_bytes(), out2.read_bytes())
        document = json.loads(out1.read_text())
        self.assertEqual((document['schema_version'], document['okf_version'], document['project_id'],
                          document['bundle_path']), (1, '0.2', 'igvc-unity-sim', 'kb'))
        self.assertNotIn(str(self.root), out1.read_text())
        self.write('kb/broken.md', 'no frontmatter\n')
        bad = self.root / 'bad.json'
        self.assertEqual(knowledge.main(['--root', str(self.root), '--bundle', 'kb', 'export', '--output', str(bad)]), 1)
        self.assertFalse(bad.exists())

    def test_project_bundle_conforms_with_current_pins(self):
        bundle = knowledge.Bundle(knowledge.DEFAULT_ROOT, 'docs/knowledge').load()
        self.assertEqual(bundle.errors, [])
        self.assertEqual([w for w in bundle.warnings if w['code'].startswith('source_')], [])
        self.assertGreaterEqual(len(bundle.nodes), 7)
        self.assertTrue(all(s['status'] == 'match' for n in bundle.nodes for s in n['sources_status']))


if __name__ == '__main__':
    unittest.main()
