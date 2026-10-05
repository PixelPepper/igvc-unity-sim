#!/usr/bin/env python3
"""Open Knowledge Format (OKF v0.2) tooling for the project knowledge bundle.

Usage (WSL or CI, where PyYAML is installed; do not pip-install on Windows):
  python3 tools/agents/knowledge.py check [--strict-project]
  python3 tools/agents/knowledge.py search QUERY [--limit 5]
  python3 tools/agents/knowledge.py export --output artifacts/agents/observatory/knowledge.json
  python3 tools/agents/knowledge.py pin PATH [PATH ...]      # print normalized source hashes
Options before the command: --root REPO (default: this repository), --bundle DIR (default: docs/knowledge),
--now ISO8601 (evaluation instant, for reproducible output).

`check` exits 1 only for OKF v0.2 format errors (unparseable/unterminated or type-less frontmatter,
malformed index.md/log.md). Broken links, unknown types/keys, missing optional fields, staleness,
malformed trust events, non-JSON YAML values and source drift are warnings. `--strict-project` also
fails on warnings; that is a project curation switch, not OKF conformance. Nothing here executes,
fetches or follows bundle content. Source hashes are never rewritten automatically.

Spec: GoogleCloudPlatform/open-knowledge-format SPEC.md at commit
ad30107c31c06aec8a7d5636e0d1058118604e6f (OKF v0.2).
"""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import math
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
# Export refuses beyond these (leaving any previous file untouched); body_display_bytes is a display hint.
EXPORT_LIMITS = {'max_bytes': 2*1024*1024, 'max_nodes': 1000, 'max_edges': 4000, 'body_display_bytes': 8192}
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
LOG_HEADING = re.compile(r'^##\s+(.*?)\s*$')
ISO_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
ACTOR = re.compile(r'^(human|process):[^\s:]+$|^[^\s:/]+/[^\s]+$')
DEFAULT_ROOT = Path(__file__).resolve().parents[2]

# Source pin policy, applied to the path text before anything is read.
TEXT_SUFFIXES = {'.md', '.txt', '.rst', '.py', '.json', '.yaml', '.yml', '.toml', '.cfg', '.ini', '.csv',
                 '.xml', '.xacro', '.urdf', '.sdf', '.launch', '.rviz', '.cs', '.cpp', '.hpp', '.h', '.c',
                 '.sh', '.ps1', '.mjs', '.js', '.ts', '.uxml', '.uss', '.tss', '.msg', '.srv', '.action'}
DENIED_PREFIXES = ('artifacts/', '.git/', 'ros2/build/', 'ros2/install/', 'ros2/log/',
                   'unity/IGVCSim/Library/', 'unity/IGVCSim/Temp/', 'unity/IGVCSim/Obj/',
                   'unity/IGVCSim/Logs/', 'unity/IGVCSim/UserSettings/', 'unity/IGVCSim/Build/',
                   'unity/IGVCSim/Builds/', 'unity/IGVCSim/Assets/IGVC/GeneratedRobot/')
DENIED_PARTS = {'.git', 'node_modules', '__pycache__', '.venv', '.cursor', '.codex-remote-attachments'}
CREDENTIAL_NAME = re.compile(r'(^\.env|\.dpapi$|\.pem$|\.key$|\.p12$|\.pfx$|^id_(rsa|ed25519|ecdsa)|'
                             r'credential|secret|token|password|auth\.json$)', re.IGNORECASE)


def _yaml():
    try:
        import yaml
    except ImportError:
        sys.exit('PyYAML is required: run in WSL/CI (python3-yaml), do not install into Windows Python')
    return yaml


def decode_text(data):
    """UTF-8 (optional BOM) with CRLF/CR normalized to LF, or None if not UTF-8."""
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return None
    return text.replace('\r\n', '\n').replace('\r', '\n')


def split_frontmatter(text):
    """(yaml_text, body, state): state is 'present', 'absent' or 'unterminated'."""
    lines = text.split('\n')
    if not lines or lines[0].rstrip() != '---':
        return None, text, 'absent'
    for number, line in enumerate(lines[1:], start=1):
        if line.rstrip() == '---':
            return '\n'.join(lines[1:number]), '\n'.join(lines[number+1:]), 'present'
    return None, text, 'unterminated'


def normalized_sha256(data):
    """SHA-256 of UTF-8 text (BOM dropped) with CRLF/CR normalized to LF (checkout-independent)."""
    text = decode_text(data)
    if text is None:
        raise ValueError('not UTF-8 text')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalize_pin(relative):
    """Canonical POSIX spelling of a pin path (backslashes and './' removed), or None if unusable."""
    if not isinstance(relative, str) or not relative:
        return None
    return PurePosixPath(relative.replace('\\', '/')).as_posix()


def pin_policy(relative):
    """Reason the path may never be pinned or read, or None. Text-only check, nothing is opened.
    Location exclusions are case-folded so 'Artifacts/' or '.GIT/' cannot bypass them."""
    if not isinstance(relative, str) or not relative or relative.startswith(('/', '\\')) or ':' in relative:
        return 'not_repository_relative'
    pure = PurePosixPath(relative.replace('\\', '/'))
    if '..' in pure.parts:
        return 'escapes_repository'
    folded = pure.as_posix().casefold()
    if (any(folded.startswith(prefix.casefold()) for prefix in DENIED_PREFIXES)
            or {part.casefold() for part in DENIED_PARTS} & {part.casefold() for part in pure.parts}):
        return 'excluded_location'
    if CREDENTIAL_NAME.search(pure.name):
        return 'credential_like_name'
    if pure.suffix.lower() not in TEXT_SUFFIXES:
        return 'not_allowed_text_type'
    return None


def resolve_inside(root, relative):
    """A pinnable regular text file inside root, or (None, reason). Policy is checked before any read."""
    reason = pin_policy(relative)
    if reason:
        return None, reason
    current = root
    for part in PurePosixPath(normalize_pin(relative)).parts:
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


def to_json(value, notes, _active=None):
    """JSON-safe copy of a YAML value; unusual values are normalized and noted, never crash."""
    active = set() if _active is None else _active
    if isinstance(value, (dict, list, tuple, set, frozenset)):
        if id(value) in active:
            notes.add('recursive_value_replaced')
            return None
        active.add(id(value))
        try:
            if isinstance(value, dict):
                return {str(k): to_json(v, notes, active) for k, v in value.items()}
            if isinstance(value, (set, frozenset)):
                notes.add('set_converted_to_sorted_list')
                return sorted((to_json(v, notes, active) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
            return [to_json(v, notes, active) for v in value]
        finally:
            active.discard(id(value))
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        notes.add('nonfinite_number_replaced')
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        notes.add('binary_value_replaced')
        return None
    notes.add('unsupported_value_stringified')
    return str(value)


def _text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ' '.join(_text(v) for v in value)
    return '' if value is None else str(value)


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
    """Only well-formed events (actor convention + timezone-aware `at`) contribute; never invent review."""
    if 'verified' not in frontmatter:
        return 'unverified'
    verified = frontmatter['verified']
    events = [verified] if isinstance(verified, dict) else verified if isinstance(verified, list) else []
    valid = []
    for event in events:
        actor = event.get('by') if isinstance(event, dict) else None
        at = _instant(event.get('at')) if isinstance(event, dict) else None
        if isinstance(actor, str) and ACTOR.match(actor.strip() or ' ') and at is not None and at.tzinfo is not None:
            valid.append(actor.strip())
        else:
            warn('malformed_verified_event')
    if not events:
        warn('malformed_verified_event')
    if not valid:
        return 'unverified'
    return 'human-reviewed' if any(a.startswith('human:') for a in valid) else 'machine-confirmed'


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
        self.bundle_rel = self.bundle.relative_to(self.root).as_posix()  # ValueError if outside root
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
            text = decode_text(path.read_bytes())
            if text is None:
                self.error(rel, 'not_utf8')
                continue
            if path.name == 'index.md':
                self._check_index(path, rel, text, yaml)
            elif path.name == 'log.md':
                self._check_log(rel, text)
            else:
                self._concept(path, rel, text, yaml)
        return self

    def _safe_load(self, rel, block, yaml, code):
        try:
            return True, yaml.safe_load(block)
        except yaml.YAMLError as exc:
            self.error(rel, code, str(exc).splitlines()[0] if str(exc) else None)
            return False, None

    def _check_index(self, path, rel, text, yaml):
        block, body, state = split_frontmatter(text)
        if state == 'unterminated':
            self.error(rel, 'index_frontmatter_unterminated')
            return
        if state == 'present':
            ok, data = self._safe_load(rel, block, yaml, 'index_frontmatter_unparseable')
            if not ok:
                return
            if path.parent != self.bundle:
                self.error(rel, 'index_frontmatter_outside_root')
            elif not isinstance(data, dict) or set(data) != {'okf_version'}:
                self.error(rel, 'index_frontmatter_only_okf_version')
            elif str(data['okf_version']) != OKF_VERSION:
                self.warn(rel, 'okf_version_differs', str(data['okf_version']))
        self._links(path, rel, body)

    def _check_log(self, rel, text):
        if split_frontmatter(text)[2] != 'absent':
            self.error(rel, 'log_frontmatter_not_allowed')
            return
        dates = []
        for line in text.split('\n'):
            match = LOG_HEADING.match(line)
            if not match:
                continue
            try:
                # Exact YYYY-MM-DD only: newer fromisoformat also accepts compact forms like 20261005.
                if not ISO_DATE.fullmatch(match.group(1)):
                    raise ValueError(match.group(1))
                dates.append(date.fromisoformat(match.group(1)))
            except ValueError:
                self.error(rel, 'log_heading_not_iso_date', match.group(1)[:40])
                return
        if dates != sorted(dates, reverse=True):
            self.error(rel, 'log_not_newest_first')

    def _concept(self, path, rel, text, yaml):
        block, body, state = split_frontmatter(text)
        if state != 'present':
            self.error(rel, 'frontmatter_unterminated' if state == 'unterminated' else 'frontmatter_missing')
            return
        ok, data = self._safe_load(rel, block, yaml, 'frontmatter_unparseable')
        if not ok:
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
        for field in ('title', 'description'):
            if field in data and not isinstance(data[field], str):
                self.warn(rel, f'{field}_not_string')
        warn = lambda code: self.warn(rel, code)
        notes = set()
        metadata = to_json(data, notes)
        for note in sorted(notes):
            self.warn(rel, note)
        node = {'id': node_id, 'path': rel, 'type': data['type'],
                'title': data['title'] if isinstance(data.get('title'), str) else path.stem,
                'description': data['description'] if isinstance(data.get('description'), str) else None,
                'metadata': metadata, 'body': body.strip('\n'),
                'trust': trust_tier(data, warn), 'freshness': freshness(data, self.now, warn),
                'lifecycle': data['status'] if isinstance(data.get('status'), str) else 'stable',
                'sources_status': self._pins(rel, node_id, data)}
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
            # Accepted pins are reported in canonical POSIX form; refused ones keep their raw text for diagnosis.
            label = (normalize_pin(path) if not reason else path) if isinstance(path, str) else None
            if not reason:
                try:
                    actual = normalized_sha256(target.read_bytes())
                except ValueError:
                    reason = 'not_utf8_text'
            if reason:
                state = 'missing' if reason == 'missing' else 'blocked'
                self.warn(rel, f'source_{state}', f'{label}: {reason}')
                status.append({'path': label, 'status': state, 'reason': reason})
                continue
            state = 'match' if actual == expected else 'changed'
            if state == 'changed':
                self.warn(rel, 'source_changed', label)
            status.append({'path': label, 'status': state, 'expected_sha256': expected if isinstance(expected, str) else None,
                           'actual_sha256': actual})
            self.edges.append({'source': node_id, 'target': label, 'kind': 'source_pin'})
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
        terms = [t for t in re.findall(r'\w+', str(query).lower()) if t]
        limit = max(1, min(MAX_LIMIT, int(limit)))
        scored = []
        for node in self.nodes:
            meta = node['metadata'] if isinstance(node['metadata'], dict) else {}
            fields = ((_text(node['title']), 3), (_text(meta.get('tags')), 2),
                      (_text(node['description']), 2), (_text(node['body']), 1))
            score = sum(weight*text.lower().count(term) for text, weight in fields for term in terms)
            if score:
                scored.append((-score, node['id'], node))
        return [{'id': n['id'], 'path': n['path'], 'title': n['title'], 'description': n['description'],
                 'score': -s} for s, _, n in sorted(scored, key=lambda item: item[:2])[:limit]]

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
        failed = 0
        for path in args.paths:
            target, reason = resolve_inside(root, path)
            if not reason:
                try:
                    print(f'- path: {normalize_pin(path)}\n  sha256: {normalized_sha256(target.read_bytes())}')
                    continue
                except ValueError:
                    reason = 'not_utf8_text'
            print(f'error {path}: {reason}', file=sys.stderr)
            failed += 1
        return 1 if failed else 0
    now = _instant(args.now) if args.now else None
    if args.now and (now is None or now.tzinfo is None):
        print('error: --now must be an ISO 8601 instant with a UTC offset', file=sys.stderr)
        return 2
    try:
        bundle = Bundle(root, args.bundle, now=now).load()
    except ValueError:
        print(f'error: bundle {args.bundle!r} is not inside root', file=sys.stderr)
        return 2
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
    # Failure writes nothing: an existing output file (the last good export) is left untouched, so a
    # consumer must use this exit status, not an unchanged snapshot, to detect a failed refresh.
    if bundle.errors:
        print(f'refusing export: {len(bundle.errors)} OKF format errors (run check); output left unchanged',
              file=sys.stderr)
        return 1
    document = bundle.export()
    text = json.dumps(document, indent=1, sort_keys=True, allow_nan=False) + '\n'
    if (len(text.encode('utf-8')) > EXPORT_LIMITS['max_bytes'] or len(document['nodes']) > EXPORT_LIMITS['max_nodes']
            or len(document['edges']) > EXPORT_LIMITS['max_edges']):
        print('refusing export: exceeds documented consumer limits; output left unchanged', file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(args.output)
    print(f'wrote {args.output} ({len(bundle.nodes)} nodes, {len(bundle.warnings)} warnings)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
