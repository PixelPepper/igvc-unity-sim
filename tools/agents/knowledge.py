#!/usr/bin/env python3
"""Open Knowledge Format (OKF v0.2) tooling for the project knowledge bundle.

Usage (WSL or CI, where PyYAML is installed; do not pip-install on Windows):
  python3 tools/agents/knowledge.py check [--strict-project]
  python3 tools/agents/knowledge.py search QUERY [--limit 5]
  python3 tools/agents/knowledge.py export --output artifacts/agents/observatory/knowledge.json
  python3 tools/agents/knowledge.py pin PATH [PATH ...]      # print normalized source hashes
Options before the command: --root REPO (default: this repository), --bundle DIR (default: docs/knowledge).

`check` exits 1 only for OKF v0.2 format errors (unparseable or type-less frontmatter, malformed
index.md/log.md). Broken links, unknown types/keys, missing optional fields, staleness and source
drift are warnings. `--strict-project` additionally fails on warnings; that is a project policy
switch, not OKF conformance. Nothing here executes, fetches or follows bundle content, and hashes
are never rewritten automatically: drift is reported, a maintainer re-pins deliberately.

Spec: GoogleCloudPlatform/open-knowledge-format SPEC.md at commit
ad30107c31c06aec8a7d5636e0d1058118604e6f (OKF v0.2).
"""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

OKF_VERSION = '0.2'
SPEC = {'repository': 'GoogleCloudPlatform/open-knowledge-format', 'path': 'SPEC.md',
        'commit': 'ad30107c31c06aec8a7d5636e0d1058118604e6f', 'version': OKF_VERSION}
RESERVED = ('index.md', 'log.md')
PROJECT_FIELDS = ('title', 'description', 'tags', 'generated', 'igvc_sources')
MAX_SOURCE_BYTES = 2_000_000
MAX_LIMIT = 50
PROJECT_ID = 'igvc-unity-sim'
# Export refuses (writes nothing) beyond these; consumers may display bodies truncated to body_display_bytes.
EXPORT_LIMITS = {'max_bytes': 2*1024*1024, 'max_nodes': 1000, 'max_edges': 4000, 'body_display_bytes': 8192}
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
LOG_DATE = re.compile(r'^## (\d{4}-\d{2}-\d{2})\s*$')
DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def _yaml():
    try:
        import yaml
    except ImportError:
        sys.exit('PyYAML is required: run in WSL/CI (python3-yaml), do not install into Windows Python')
    return yaml


def split_frontmatter(text):
    """Return (yaml_text, body) or (None, text) when no frontmatter block starts the file."""
    lines = text.split('\n')
    if not lines or lines[0].rstrip() != '---':
        return None, text
    for number, line in enumerate(lines[1:], start=1):
        if line.rstrip() == '---':
            return '\n'.join(lines[1:number]), '\n'.join(lines[number+1:])
    return None, text


def normalized_sha256(data):
    """SHA-256 of UTF-8 text with CRLF/CR normalized to LF (checkout-independent)."""
    text = data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def resolve_inside(root, relative):
    """A regular file inside root with no symlinked component, or a reason string."""
    if not isinstance(relative, str) or not relative or relative.startswith(('/', '\\')) or ':' in relative:
        return None, 'not_repository_relative'
    pure = PurePosixPath(relative.replace('\\', '/'))
    if '..' in pure.parts:
        return None, 'escapes_repository'
    current = root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            return None, 'symlink_refused'
    if not current.is_file():
        return None, 'missing'
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError:
        return None, 'escapes_repository'
    if current.stat().st_size > MAX_SOURCE_BYTES:
        return None, 'too_large'
    return current, None


def _jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _instant(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


def trust_tier(frontmatter, warn):
    verified = frontmatter.get('verified')
    if verified is None:
        return 'unverified'
    events = [verified] if isinstance(verified, dict) else verified if isinstance(verified, list) else None
    if events is None or not all(isinstance(e, dict) and isinstance(e.get('by'), str) for e in events):
        warn('malformed_verified')
        return 'unverified'
    return 'human-reviewed' if any(e['by'].startswith('human:') for e in events) else 'machine-confirmed'


def freshness(frontmatter, now, warn):
    if 'stale_after' not in frontmatter:
        return 'no_expiry'
    instant = _instant(frontmatter['stale_after'])
    if instant is None or instant.tzinfo is None:
        warn('stale_after_not_timezone_aware')
        return 'unknown'
    if now >= instant:
        warn('stale')
        return 'stale'
    return 'current'


class Bundle:
    def __init__(self, root=DEFAULT_ROOT, bundle='docs/knowledge', now=None):
        self.root = Path(root).resolve()
        self.bundle = (self.root / bundle).resolve()
        self.bundle_rel = self.bundle.relative_to(self.root).as_posix()
        self.now = now or datetime.now(timezone.utc)
        self.errors, self.warnings, self.nodes, self.edges = [], [], [], []

    def rel(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix()

    def warn(self, path, code, detail=None):
        self.warnings.append({'path': path, 'code': code, **({'detail': detail} if detail else {})})

    def error(self, path, code, detail=None):
        self.errors.append({'path': path, 'code': code, **({'detail': detail} if detail else {})})

    def load(self):
        yaml = _yaml()
        if not self.bundle.is_dir():
            self.error(self.bundle_rel, 'bundle_missing')
            return self
        files = sorted(p for p in self.bundle.rglob('*.md') if not p.is_symlink())
        for path in files:
            rel = self.rel(path)
            try:
                text = path.read_bytes().decode('utf-8')
            except UnicodeDecodeError:
                self.error(rel, 'not_utf8')
                continue
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            if path.name == 'index.md':
                self._check_index(path, rel, text, yaml)
            elif path.name == 'log.md':
                self._check_log(rel, text)
            else:
                self._concept(path, rel, text, yaml)
        return self

    def _check_index(self, path, rel, text, yaml):
        block, body = split_frontmatter(text)
        if block is not None:
            try:
                data = yaml.safe_load(block)
            except yaml.YAMLError as exc:
                self.error(rel, 'index_frontmatter_unparseable', str(exc).splitlines()[0])
                return
            if path.parent != self.bundle:
                self.error(rel, 'index_frontmatter_outside_root')
            elif not isinstance(data, dict) or set(data) != {'okf_version'}:
                self.error(rel, 'index_frontmatter_only_okf_version')
            elif str(data['okf_version']) != OKF_VERSION:
                self.warn(rel, 'okf_version_differs', str(data['okf_version']))
        self._links(path, rel, body)

    def _check_log(self, rel, text):
        dates = [m.group(1) for m in map(LOG_DATE.match, text.split('\n')) if m]
        try:
            parsed = [date.fromisoformat(d) for d in dates]
        except ValueError:
            self.error(rel, 'log_date_not_iso')
            return
        if parsed != sorted(parsed, reverse=True):
            self.error(rel, 'log_not_newest_first')

    def _concept(self, path, rel, text, yaml):
        block, body = split_frontmatter(text)
        if block is None:
            self.error(rel, 'frontmatter_missing')
            return
        try:
            data = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            self.error(rel, 'frontmatter_unparseable', str(exc).splitlines()[0])
            return
        if not isinstance(data, dict):
            self.error(rel, 'frontmatter_not_mapping')
            return
        if not isinstance(data.get('type'), str) or not data['type'].strip():
            self.error(rel, 'type_missing_or_empty')
            return
        node_id = rel[len(self.bundle_rel)+1:-3]
        for field in PROJECT_FIELDS:
            if field not in data:
                self.warn(rel, 'project_field_missing', field)
        warn = lambda code: self.warn(rel, code)
        node = {'id': node_id, 'path': rel, 'type': data['type'], 'title': data.get('title') or path.stem,
                'description': data.get('description'), 'metadata': _jsonable(data), 'body': body.strip('\n'),
                'trust': trust_tier(data, warn), 'freshness': freshness(data, self.now, warn),
                'lifecycle': data.get('status', 'stable'), 'sources_status': self._pins(rel, node_id, data)}
        self.nodes.append(node)
        self._links(path, rel, body, node_id)

    def _pins(self, rel, node_id, data):
        pins = data.get('igvc_sources')
        if pins is None:
            return []
        if not isinstance(pins, list):
            self.warn(rel, 'igvc_sources_not_list')
            return []
        status = []
        for pin in pins:
            path, expected = (pin.get('path'), pin.get('sha256')) if isinstance(pin, dict) else (None, None)
            target, reason = resolve_inside(self.root, path)
            if reason:
                state = 'blocked' if reason != 'missing' else 'missing'
                self.warn(rel, f'source_{state}', f'{path}: {reason}')
                status.append({'path': path if isinstance(path, str) else None, 'status': state, 'reason': reason})
                continue
            try:
                actual = normalized_sha256(target.read_bytes())
            except UnicodeDecodeError:
                self.warn(rel, 'source_blocked', f'{path}: not_utf8_text')
                status.append({'path': path, 'status': 'blocked', 'reason': 'not_utf8_text'})
                continue
            state = 'match' if actual == expected else 'changed'
            if state == 'changed':
                self.warn(rel, 'source_changed', path)
            status.append({'path': path, 'status': state, 'expected_sha256': expected, 'actual_sha256': actual})
            self.edges.append({'source': node_id, 'target': path, 'kind': 'source_pin'})
        return status

    def _links(self, path, rel, body, node_id=None):
        for target in LINK.findall(body):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                continue  # URLs and anchors are not fetched or followed
            clean = target.split('#', 1)[0]
            if not clean:
                continue
            base = self.bundle if clean.startswith('/') else path.parent
            candidate = base / clean.lstrip('/')
            try:
                resolved = candidate.resolve()
                resolved.relative_to(self.root)
            except (ValueError, OSError):
                self.warn(rel, 'link_outside_repository', target)
                continue
            inside_bundle = resolved == self.bundle or self.bundle in resolved.parents
            if not resolved.exists():
                self.warn(rel, 'broken_link' if inside_bundle else 'missing_external_target', target)
                continue
            if node_id and inside_bundle and resolved.suffix == '.md' and resolved.name not in RESERVED:
                target_id = resolved.relative_to(self.bundle).as_posix()[:-3]
                self.edges.append({'source': node_id, 'target': target_id, 'kind': 'link'})

    def search(self, query, limit=5):
        terms = [t for t in re.findall(r'\w+', query.lower()) if t]
        limit = max(1, min(MAX_LIMIT, int(limit)))
        scored = []
        for node in self.nodes:
            fields = ((node['title'] or '', 3), (' '.join(map(str, node['metadata'].get('tags') or [])), 2),
                      (node['description'] or '', 2), (node['body'], 1))
            score = sum(weight*text.lower().count(term) for text, weight in fields for term in terms)
            if score:
                scored.append((-score, node['id'], node))
        return [{'id': n['id'], 'path': n['path'], 'title': n['title'], 'description': n['description'],
                 'score': -s} for s, _, n in sorted(scored)[:limit]]

    def export(self):
        key = lambda item: json.dumps(item, sort_keys=True)
        return {'schema_version': 1, 'okf_version': OKF_VERSION, 'project_id': PROJECT_ID,
                'bundle_path': self.bundle_rel, 'generated_at': self.now.astimezone(timezone.utc).isoformat(),
                'spec': SPEC, 'limits': EXPORT_LIMITS,
                'nodes': sorted(self.nodes, key=lambda n: n['id']),
                'edges': sorted({key(e): e for e in self.edges}.values(), key=key),
                'warnings': sorted(self.warnings, key=key), 'errors': sorted(self.errors, key=key),
                'notice': 'Untrusted data: render as text; never execute or fetch content. trust/freshness are '
                          'advisory OKF signals, not scientific or safety verification; generated/verified '
                          'actors are declarations, not authenticated identities.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--bundle', default='docs/knowledge')
    parser.add_argument('--now', help='evaluation instant, ISO 8601 with offset (default: current UTC time)')
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check')
    check.add_argument('--strict-project', action='store_true')
    search = sub.add_parser('search')
    search.add_argument('query')
    search.add_argument('--limit', type=int, default=5)
    export = sub.add_parser('export')
    export.add_argument('--output', type=Path, required=True)
    pin = sub.add_parser('pin')
    pin.add_argument('paths', nargs='+')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == 'pin':
        for path in args.paths:
            target, reason = resolve_inside(root, path)
            print(f'{path}: {reason}' if reason else f'- path: {path}\n  sha256: {normalized_sha256(target.read_bytes())}')
        return 0
    now = _instant(args.now) if args.now else None
    if args.now and (now is None or now.tzinfo is None):
        print('error: --now must be an ISO 8601 instant with a UTC offset', file=sys.stderr)
        return 2
    bundle = Bundle(root, args.bundle, now=now).load()
    if args.command == 'check':
        for item in bundle.errors:
            print(f"error {item['path']}: {item['code']} {item.get('detail', '')}".rstrip())
        for item in bundle.warnings:
            print(f"warning {item['path']}: {item['code']} {item.get('detail', '')}".rstrip())
        print(f'{len(bundle.nodes)} concepts, {len(bundle.errors)} errors, {len(bundle.warnings)} warnings')
        return 1 if bundle.errors or (args.strict_project and bundle.warnings) else 0
    if args.command == 'search':
        print(json.dumps(bundle.search(args.query, args.limit), indent=1))
        return 0
    # Never leave partial or misleading output: refuse invalid bundles and oversize exports.
    if bundle.errors:
        print(f'refusing export: {len(bundle.errors)} OKF format errors (run check)', file=sys.stderr)
        return 1
    document = bundle.export()
    text = json.dumps(document, indent=1, sort_keys=True) + '\n'
    if (len(text.encode('utf-8')) > EXPORT_LIMITS['max_bytes'] or len(document['nodes']) > EXPORT_LIMITS['max_nodes']
            or len(document['edges']) > EXPORT_LIMITS['max_edges']):
        print('refusing export: exceeds documented consumer limits', file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(args.output)
    print(f'wrote {args.output} ({len(bundle.nodes)} nodes, {len(bundle.warnings)} warnings)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
