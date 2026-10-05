#!/usr/bin/env python3
"""Summarize opt-in Unity transport timing records (schema igvc_transport_timing_v2) from a player log.

Read-only and offline. Streams the log once, hashes its exact bytes for binding,
and validates the trace before summarizing it. Missing, malformed or conflicting
records make the evidence incomplete; they never become zero gaps or a healthy
verdict. A log without trace records (tracing off) is reported as unavailable.
The summary never infers a cause: a frame gap does not distinguish focus loss,
GC, OS scheduling, rendering or networking, and zero warning lines never prove
that nothing was dropped. No clock alignment with ROS or other hosts is invented.
Conservatively, any line over the size cap (even an unrelated one) is an
integrity issue, so a tracing-off log containing one reports incomplete rather
than unavailable. Exact-equality checks rely on the producer's C# "R" double
formatting, which round-trips losslessly.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = 'igvc_transport_timing_v2'
MARKER = b'igvc_transport_timing'
MAX_LINE_BYTES = 65536
MAX_RECORDS = 1300          # producer cap is 1200 (header included); more is an integrity problem
MAX_LISTED = 5              # bounded lists in the report
FINAL_KINDS = ('stopped', 'exhausted')
# DateTime.UtcNow.ToString("o") as written by the producer, e.g. 2026-10-05T15:03:14.9744871Z
UTC_FORMAT = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,7})?Z$')
UNCERTAINTY = {
    'clocks': 'mono_s is this host\'s Stopwatch since the trace origin; each utc was read between '
              'mono_before_utc_s and mono_after_utc_s, which bounds its placement, not utc accuracy. UtcNow can be '
              'coarse (milliseconds) and can step. No alignment with ROS, WSL or other hosts is implied. Raw '
              'floats are encodings, not measurement accuracy.',
    'frames': 'A frame gap is wall time between consecutive sampled Updates. It does not distinguish focus loss, '
              'pause, GC, OS suspension, rendering or network causes.',
    'warnings': 'Counts are matching connector log lines observed by the callback, not dropped messages; zero '
                'never proves that nothing was dropped. The per-record count and the cumulative last-observation time '
                'are updated asynchronously: they are not a coherent pair and not exact per-window attribution.',
    'coverage': 'nominal_exhaustion_after_first_sample_s is nominal, not a maximum. mono_s of the final record is '
                'the last sampled frame, not the stop time; the tail after it is unsampled.'}


INT_LIMIT = 2**63
FLOAT_LIMIT = 1e300


def _int(value):
    """A JSON integer within int64 (larger values are malformed, not huge counts)."""
    return isinstance(value, int) and not isinstance(value, bool) and -INT_LIMIT < value < INT_LIMIT


def _finite(value):
    """A finite JSON number of sane magnitude; huge integers never reach float conversion."""
    if _int(value):
        return True
    return isinstance(value, float) and math.isfinite(value) and abs(value) < FLOAT_LIMIT


def _short(value, limit=60):
    """Bounded representation of any JSON-shaped value for messages and the report."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + '...'
    if isinstance(value, (list, dict)):
        return '<%s of %d>' % (type(value).__name__, len(value))
    if isinstance(value, bool) or value is None or _finite(value):
        return value
    if isinstance(value, int):
        return '<int out of range>'
    return '<%s>' % type(value).__name__


def _text(value):
    """A string value, or None for any other JSON type."""
    return value if isinstance(value, str) else None


def _reject_constant(token):
    raise ValueError('non-finite JSON constant ' + token)


def _unique_keys(pairs):
    """JSON object hook: a duplicated key is malformed (never silently last-wins)."""
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError('duplicate JSON key')
        record[key] = value
    return record


def read_trace(path):
    """Stream the log: (sha256, bytes, lines, records, integrity issues). Lines and records are bounded."""
    digest, size, lines, records, issues = hashlib.sha256(), 0, 0, [], []
    oversize = malformed = excess = 0
    with open(path, 'rb') as stream:
        while True:
            line = stream.readline(MAX_LINE_BYTES + 1)
            if not line:
                break
            digest.update(line)
            size += len(line)
            if len(line) > MAX_LINE_BYTES and not line.endswith(b'\n'):
                # Consume the rest of an oversize line (still hashed) and judge it by its start only.
                while line and not line.endswith(b'\n'):
                    line = stream.readline(MAX_LINE_BYTES)
                    digest.update(line)
                    size += len(line)
                lines += 1
                oversize += 1
                continue
            lines += 1
            if MARKER not in line:
                continue
            text = line.decode('utf-8', 'replace').strip()
            if not text.startswith('{"schema":'):
                malformed += 1  # trace marker embedded in another line (e.g. a stack trace)
                continue
            try:
                record = json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_unique_keys)
            except (ValueError, RecursionError):  # malformed, duplicate keys, non-finite or pathologically nested
                malformed += 1
                continue
            if not isinstance(record, dict):
                malformed += 1
                continue
            if len(records) >= MAX_RECORDS:
                excess += 1  # keep reading so the hash still binds every byte
                continue
            records.append(record)
    if excess:
        issues.append('record_limit_exceeded: %d trace records beyond %d were not parsed' % (excess, MAX_RECORDS))
    if oversize:
        issues.append('oversize_lines: %d lines over %d bytes were not parsed' % (oversize, MAX_LINE_BYTES))
    if malformed:
        issues.append('malformed_trace_lines: %d' % malformed)
    return digest.hexdigest(), size, lines, records, issues


def _check_bracket(record, name, issues):
    before, after, utc = record.get('mono_before_utc_s'), record.get('mono_after_utc_s'), record.get('utc')
    # Trace monotonic times start at the origin, so they are never negative; utc is a short ISO string.
    if (not isinstance(utc, str) or len(utc) > 64 or not UTC_FORMAT.match(utc) or not _finite(before) or not _finite(after)
            or before < 0 or before > after):
        issues.append('%s: utc bracket missing, malformed, negative or inverted' % name)
        return None
    return before, after


def validate(records):
    """Return (header, body records, issues). Any issue makes the evidence incomplete."""
    issues = []
    if not records:
        return None, [], issues
    schemas = {_text(r.get('schema')) or '<missing or non-string>' for r in records}
    if schemas != {SCHEMA}:
        issues.append('unsupported_or_mixed_schema: %s' % [_short(s) for s in sorted(schemas)[:MAX_LISTED]])
    header = records[0] if records[0].get('kind') == 'header' else None
    if header is None:
        issues.append('first_record_is_not_header')
    elif not (_int(header.get('seq')) and header['seq'] == 0 and _finite(header.get('report_interval_s')) and header['report_interval_s'] > 0
              and _int(header.get('record_cap')) and header['record_cap'] >= 2
              and _int(header.get('mono_frequency_hz')) and header['mono_frequency_hz'] > 0
              and isinstance(header.get('queue_full_prefix'), str)):
        issues.append('header_fields_missing_or_invalid')
    header_bracket = _check_bracket(header, 'header', issues) if header is not None else None
    interval = header.get('report_interval_s') if header is not None and _finite(header.get('report_interval_s')) else None
    body = records[1:] if header is not None else records
    previous = header
    total_frames = lines_total = 0
    cumulative = 0.
    last_mono = None
    # All Stopwatch reads happen in order on one thread: each UTC bracket starts no earlier than the previous one
    # ended, and the first frame is sampled after the header's bracket.
    last_after = header_bracket[1] if header_bracket else None
    terminal_seen = False
    for record in body:
        seq, kind = record.get('seq'), record.get('kind')
        name = 'seq %s' % _short(seq)
        if terminal_seen:
            issues.append('record_after_final: %s' % name)
            break
        previous_seq = previous.get('seq') if previous is not None else None
        if not _int(seq) or not _int(previous_seq) or seq != previous_seq + 1:
            issues.append('sequence_contradiction at %s (previous %s)' % (_short(seq), _short(previous_seq)))
            break
        if _text(kind) not in ('window',) + FINAL_KINDS:
            issues.append('unknown_kind %r at %s' % (_short(kind), name))
            break
        bracket = _check_bracket(record, name, issues)
        frames, totals = record.get('frames'), record.get('total_frames')
        delta, lines_now = record.get('queue_full_lines_since_previous_record'), record.get('queue_full_lines_total')
        window_gap, cumulative_gap = record.get('window_max_frame_gap_s'), record.get('cumulative_max_frame_gap_s')
        mono = record.get('mono_s')
        if not (_int(frames) and frames >= 0 and _int(totals) and totals == total_frames + frames):
            issues.append('frame_count_contradiction at %s' % name)
        if not (_int(delta) and delta >= 0 and _int(lines_now) and lines_now == lines_total + delta):
            issues.append('warning_count_contradiction at %s' % name)
        # The producer copies exact doubles: cumulative = max(previous cumulative, window gap), and every window
        # after the first starts at the previous record's last frame. Those are checked for exact equality.
        if not (_finite(window_gap) and _finite(cumulative_gap) and window_gap >= 0
                and cumulative_gap == max(cumulative, window_gap)):
            issues.append('frame_gap_contradiction at %s' % name)
        start = record.get('window_start_mono_s')
        if frames == 0 and _finite(window_gap) and window_gap != 0:
            issues.append('gap_without_frames at %s' % name)
        if start is None:
            if not (mono is None and frames == 0 and last_mono is None):
                issues.append('window_start_missing at %s' % name)  # only a stop before any frame has no start
        elif not _finite(start) or start < 0:
            issues.append('window_start_invalid at %s' % name)
        elif last_mono is not None and start != last_mono:
            issues.append('window_start_not_previous_last_frame at %s' % name)
        elif _finite(mono) and (start > mono or (_finite(window_gap) and window_gap > mono - start + 1e-9)):
            issues.append('window_gap_exceeds_window_span at %s' % name)
        if _finite(mono) and mono < 0:
            issues.append('mono_s_negative at %s' % name)
        if bracket and last_after is not None and bracket[0] < last_after:
            issues.append('utc_bracket_not_ordered at %s' % name)
        if last_mono is None and _finite(start) and header_bracket and start < header_bracket[1]:
            issues.append('first_frame_before_header_bracket at %s' % name)
        if _finite(start) and _finite(mono) and _int(frames) and _finite(window_gap) and mono >= start:
            span = mono - start
            tolerance = 1e-9 * max(1., span)  # floating summation rounding only
            # n new frames give n gaps after the previous record's last frame; the first window has n-1.
            gaps = frames if last_mono is not None else frames - 1
            if gaps <= 0 and span > tolerance:
                issues.append('window_span_without_frame_gaps at %s' % name)
            elif gaps > 0 and window_gap * gaps < span - tolerance:
                issues.append('window_gap_below_necessary_lower_bound at %s' % name)
            # Periodic records are emitted only when the span reaches the interval (the producer's own comparison).
            if _text(kind) in ('window', 'exhausted') and interval is not None and span < interval:
                issues.append('periodic_window_shorter_than_report_interval at %s' % name)
        if header is not None and _int(header.get('record_cap')) and seq >= header['record_cap']:
            issues.append('seq_beyond_record_cap at %s' % name)
        if mono is not None and not _finite(mono) or (frames and mono is None):
            issues.append('mono_s_missing_or_non_finite at %s' % name)
        elif mono is not None and last_mono is not None and mono < last_mono:
            issues.append('mono_s_decreased at %s' % name)
        if bracket and mono is not None and _finite(mono) and bracket[0] < mono:
            issues.append('utc_read_before_last_frame at %s' % name)
        last_warning = record.get('cumulative_last_queue_full_observed_mono_s')
        if not (last_warning is None or (_finite(last_warning) and last_warning >= 0)):
            issues.append('warning_time_invalid at %s' % name)
        if kind == 'exhausted' and header is not None and _int(header.get('record_cap')) and seq != header['record_cap'] - 1:
            issues.append('exhausted_before_cap at %s' % name)
        total_frames = totals if _int(totals) else total_frames
        lines_total = lines_now if _int(lines_now) else lines_total
        cumulative = cumulative_gap if _finite(cumulative_gap) else cumulative
        last_mono = mono if _finite(mono) else last_mono
        last_after = bracket[1] if bracket else last_after
        terminal_seen = _text(kind) in FINAL_KINDS
        previous = record
    if body and not terminal_seen and not any(i.startswith(('record_after_final', 'sequence_contradiction',
                                                            'unknown_kind')) for i in issues):
        issues.append('missing_final_record: no stopped/exhausted record; cause not determined')
    if header is not None and not body:
        issues.append('header_only: no window or final record')
    return header, body, issues


def summarize(path):
    sha, size, lines, records, read_issues = read_trace(path)
    report = {'input': {'unity_log': str(path), 'sha256': sha, 'bytes': size, 'lines': lines,
                        'trace_records_parsed': len(records)},
              'uncertainty': UNCERTAINTY}
    if not records and not read_issues:
        report['status'] = 'unavailable: no %s records (tracing off or not reached)' % SCHEMA
        return report
    header, body, issues = validate(records)
    issues = read_issues + issues
    report['status'] = 'complete' if not issues else 'incomplete'
    validated = not issues
    report['derived_fields'] = ('validated' if validated else
                                'unvalidated: evidence incomplete; raw values below are echoed, derived spans withheld')
    report['integrity_issues'] = issues[:2*MAX_LISTED]
    report['integrity_issue_count'] = len(issues)
    if header is not None:
        report['header'] = {key: _short(header.get(key), 200) for key in (
            'utc', 'mono_before_utc_s', 'mono_after_utc_s', 'mono_source', 'mono_frequency_hz', 'report_interval_s',
            'record_cap', 'nominal_exhaustion_after_first_sample_s', 'queue_full_prefix')}
    kinds = {}
    for record in body:
        kind = _text(record.get('kind'))
        kind = kind if kind in ('window',) + FINAL_KINDS else '<invalid>'
        kinds[kind] = kinds.get(kind, 0) + 1
    report['records'] = {'count_including_header': len(records), 'by_kind': kinds}
    valid = [r for r in body if _finite(r.get('window_max_frame_gap_s'))]
    worst = sorted(valid, key=lambda r: r['window_max_frame_gap_s'], reverse=True)[:MAX_LISTED]
    first = next((r for r in body if _finite(r.get('window_start_mono_s'))), None)
    last = body[-1] if body else None
    report['frame_samples'] = {
        'first_sampled_frame_mono_s': first.get('window_start_mono_s') if first else None,
        'last_sampled_frame_mono_s': _short(last.get('mono_s')) if last else None,
        'total_frames': _short(last.get('total_frames')) if last else None,
        'largest_window_frame_gaps': [{'seq': _short(r.get('seq')), 'window_max_frame_gap_s': r['window_max_frame_gap_s'],
                                       'window_start_mono_s': _short(r.get('window_start_mono_s')),
                                       'last_frame_mono_s': _short(r.get('mono_s')), 'utc': _short(r.get('utc')),
                                       'mono_before_utc_s': _short(r.get('mono_before_utc_s')),
                                       'mono_after_utc_s': _short(r.get('mono_after_utc_s'))} for r in worst],
        'producer_cumulative_max_frame_gap_s': _short(last.get('cumulative_max_frame_gap_s')) if last else None}
    nonzero = [r for r in body if _int(r.get('queue_full_lines_since_previous_record'))
               and r['queue_full_lines_since_previous_record'] > 0]
    report['connector_warning_lines'] = {
        'total_observed': _short(last.get('queue_full_lines_total')) if last else None,
        'records_with_new_lines': len(nonzero),
        'first_and_last_seq_with_new_lines': [_short(nonzero[0].get('seq')), _short(nonzero[-1].get('seq'))] if nonzero else None,
        'cumulative_last_observed_mono_s': _short(last.get('cumulative_last_queue_full_observed_mono_s')) if last else None,
        'records_reporting_connection_error': sum(1 for r in body if r.get('connection_error') is True)}
    final = last if last is not None and _text(last.get('kind')) in FINAL_KINDS else None
    tail = None
    if validated and final and _finite(final.get('mono_before_utc_s')) and _finite(final.get('mono_s')):
        tail = final['mono_before_utc_s'] - final['mono_s']
    report['final'] = {
        'kind': final.get('kind') if final else 'missing',
        'note': _short(final.get('note'), 200) if final else None,
        'last_sampled_frame_mono_s': _short(final.get('mono_s')) if final else None,
        'final_utc': _short(final.get('utc')) if final else None,
        'final_mono_before_utc_s': _short(final.get('mono_before_utc_s')) if final else None,
        'final_mono_after_utc_s': _short(final.get('mono_after_utc_s')) if final else None,
        'unsampled_tail_s': tail,
        'unsampled_tail_meaning': 'from the last sampled frame to the START of the final record\'s UTC bracket '
                                  '(mono_before_utc_s), a lower endpoint rather than the exact read time; not measured '
                                  'as a frame gap and not attributable to any cause'}
    report['coverage'] = {
        'header_mono_before_utc_s': _short(header.get('mono_before_utc_s')) if header else None,
        'final_mono_after_utc_s': _short(final.get('mono_after_utc_s')) if final else None,
        'covered_mono_span_s': (final['mono_after_utc_s'] - header['mono_before_utc_s'])
        if validated and final and header and _finite(final.get('mono_after_utc_s'))
        and _finite(header.get('mono_before_utc_s')) else None}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unity-log', required=True, type=Path, help='Unity player log (read-only)')
    parser.add_argument('--output', required=True, type=Path, help='write JSON report here (must not exist)')
    args = parser.parse_args(argv)
    try:
        report = summarize(args.unity_log)
    except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:  # input problems only
        print(f'cannot read Unity log {args.unity_log}: {type(exc).__name__}', file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    try:
        # Exclusive create (never overwrite). The report is fully serialized before the file is created,
        # so only an I/O failure during the single write could leave a partial file.
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(text + '\n')
    except FileExistsError:
        print(f'refusing to overwrite {args.output}', file=sys.stderr)
        return 1
    except (FileNotFoundError, PermissionError, IsADirectoryError) as exc:  # output path problems only
        print(f'cannot create report {args.output}: {type(exc).__name__}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
