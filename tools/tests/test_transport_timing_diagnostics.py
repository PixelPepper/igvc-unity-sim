"""Offline Unity transport timing summary: validated evidence, never an inferred cause."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import diagnose_transport_timing as diag  # noqa: E402

PREFIX = 'Queue full! Messages are getting dropped!'


class Producer:
    """Records shaped like TransportTimingWindow (schema v2): header, windows, stopped/exhausted."""

    def __init__(self, interval=1.0, cap=1200):
        self.interval, self.cap = interval, cap
        self.records, self.last = [], None
        self.window_start = self.sim_start = self.sim_end = None
        self.window_frames = self.total_frames = self.lines_total = 0
        self.window_max = self.cumulative = 0.
        self.records.append({'schema': diag.SCHEMA, 'kind': 'header', 'seq': 0, 'utc': '2026-10-05T15:00:00.0000000Z',
                             'mono_before_utc_s': 0.0, 'mono_after_utc_s': 0.0, 'mono_source': 'System.Diagnostics.Stopwatch',
                             'mono_frequency_hz': 10000000, 'mono_origin_ticks': 1, 'report_interval_s': interval,
                             'record_cap': cap, 'nominal_exhaustion_after_first_sample_s': (cap-1)*interval,
                             'queue_full_prefix': PREFIX})

    def sample(self, t, sim=None):
        if self.last is not None:
            gap = t - self.last
            self.window_max, self.cumulative = max(self.window_max, gap), max(self.cumulative, gap)
        self.window_start = t if self.window_start is None else self.window_start
        self.sim_start = (t if sim is None else sim) if self.sim_start is None else self.sim_start
        self.sim_end = t if sim is None else sim
        self.last = t
        self.window_frames += 1
        self.total_frames += 1
        return t - self.window_start >= self.interval

    def record(self, kind, utc_mono, lines=0, error=False, note=None):
        self.lines_total += lines
        record = {'schema': diag.SCHEMA, 'kind': kind, 'seq': len(self.records), 'utc': '2026-10-05T15:00:01Z',
                  'mono_before_utc_s': utc_mono, 'mono_after_utc_s': utc_mono + 2e-6, 'mono_s': self.last,
                  'window_start_mono_s': self.window_start, 'frames': self.window_frames, 'total_frames': self.total_frames,
                  'window_max_frame_gap_s': self.window_max, 'cumulative_max_frame_gap_s': self.cumulative,
                  'sim_time_start_s': self.sim_start, 'sim_time_end_s': self.sim_end,
                  'queue_full_lines_since_previous_record': lines, 'queue_full_lines_total': self.lines_total,
                  'cumulative_last_queue_full_observed_mono_s': None, 'connection_error': error}
        if note:
            record['note'] = note
        self.records.append(record)
        self.window_start, self.window_frames, self.window_max, self.sim_start = self.last, 0, 0., self.sim_end
        return record

    def run(self, frames, step=1/60, start=0.):
        t = start
        for _ in range(frames):
            if self.sample(t):
                self.record('exhausted' if len(self.records) == self.cap-1 else 'window', t + 1e-4)
                if len(self.records) >= self.cap:
                    return t
            t += step
        return t

    def stop(self, utc_mono, note='coverage ended: component disabled'):
        return self.record('stopped', utc_mono, note=note)


def log_text(records, noise=True, raw_lines=()):
    lines = ['Initialize engine version: 6000.3.23f1', 'IGVC_COURSE_VARIANT_READY seed=2029'] if noise else []
    for record in records:
        lines += [json.dumps(record, separators=(',', ':')),
                  '(Filename: C:/build/output/unity/unity/Runtime/Export/Debug/Debug.bindings.cs Line: 123)', '']
    return '\n'.join(lines + list(raw_lines)) + '\n'


class TransportTimingDiagnosticsTest(unittest.TestCase):
    def summarize(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'unity.log'
            path.write_bytes(text.encode('utf-8'))  # exact bytes on every platform (no newline translation)
            original = path.read_bytes()
            report = diag.summarize(path)
            self.assertEqual(path.read_bytes(), original)  # the log is never modified
            json.dumps(report, allow_nan=False)
            return report

    def test_steady_cadence_with_stop_is_complete_and_exposes_the_unsampled_tail(self):
        p = Producer()
        t = p.run(200)
        p.stop(t + .25)
        report = self.summarize(log_text(p.records))
        self.assertEqual(report['status'], 'complete', report.get('integrity_issues'))
        self.assertEqual(report['records']['by_kind'], {'window': 3, 'stopped': 1})
        self.assertAlmostEqual(report['frame_samples']['largest_window_frame_gaps'][0]['window_max_frame_gap_s'], 1/60)
        final = report['final']
        self.assertEqual(final['kind'], 'stopped')
        self.assertAlmostEqual(final['last_sampled_frame_mono_s'], p.last)
        self.assertAlmostEqual(final['unsampled_tail_s'], .25 + 1/60, places=6)  # after the last frame, not a gap
        self.assertIn('not measured as a frame gap', final['unsampled_tail_meaning'])
        self.assertEqual(report['header']['nominal_exhaustion_after_first_sample_s'], 1199.0)
        self.assertIn('not a maximum', report['uncertainty']['coverage'])
        self.assertFalse(any('cause' in key or 'verdict' in key for key in report))  # no cause or gate verdict field

    def test_hitch_across_a_reporting_boundary_is_reported_with_its_window_and_bracket(self):
        p = Producer()
        t = p.run(59)              # last frame at 0.9667 s
        p.sample(1.9)              # 0.933 s hitch crosses the 1 s boundary
        p.record('window', 1.9001)
        p.run(70, start=1.9 + 1/60)
        p.stop(4.0)
        report = self.summarize(log_text(p.records))
        worst = report['frame_samples']['largest_window_frame_gaps'][0]
        self.assertEqual(report['status'], 'complete')
        self.assertAlmostEqual(worst['window_max_frame_gap_s'], 1.9 - 58/60)
        self.assertEqual((worst['seq'], worst['mono_before_utc_s']), (1, 1.9001))
        self.assertAlmostEqual(report['frame_samples']['producer_cumulative_max_frame_gap_s'], 1.9 - 58/60)
        self.assertIn('does not distinguish', report['uncertainty']['frames'])

    def test_missing_final_record_is_incomplete_not_healthy(self):
        p = Producer()
        p.run(200)
        report = self.summarize(log_text(p.records))
        self.assertEqual(report['status'], 'incomplete')
        self.assertTrue(any(i.startswith('missing_final_record') for i in report['integrity_issues']))
        self.assertEqual(report['final']['kind'], 'missing')
        self.assertIsNone(report['final']['unsampled_tail_s'])

    def test_default_off_log_has_no_trace_and_is_unavailable(self):
        report = self.summarize(log_text([]))
        self.assertTrue(report['status'].startswith('unavailable'))
        self.assertNotIn('frame_samples', report)
        self.assertEqual(report['input']['trace_records_parsed'], 0)

    def test_malformed_or_non_finite_records_make_the_evidence_incomplete(self):
        p = Producer()
        t = p.run(130)
        p.stop(t + .1)
        good = log_text(p.records)
        for name, extra in {'truncated json': ['{"schema":"igvc_transport_timing_v2","kind":"window","seq":'],
                            'NaN token': ['{"schema":"igvc_transport_timing_v2","kind":"window","mono_s":NaN}'],
                            'marker inside other text': ['at IGVC "schema":"igvc_transport_timing_v2" stack']}.items():
            with self.subTest(name):
                report = self.summarize(good + '\n'.join(extra) + '\n')
                self.assertEqual(report['status'], 'incomplete')
                self.assertTrue(any(i.startswith('malformed_trace_lines') for i in report['integrity_issues']))
        records = [dict(r) for r in p.records]
        records[1]['window_max_frame_gap_s'] = None
        self.assertEqual(self.summarize(log_text(records))['status'], 'incomplete')

    def test_sequence_and_count_contradictions_are_flagged(self):
        p = Producer()
        t = p.run(200)
        p.stop(t + .1)
        cases = {'duplicate record': lambda r: r.insert(2, dict(r[1])),
                 'missing record': lambda r: r.pop(2),
                 'record after final': lambda r: r.append(dict(r[1], seq=len(r))),
                 'frame total jump': lambda r: r[2].__setitem__('total_frames', r[2]['total_frames'] + 5),
                 'warning total jump': lambda r: r[2].__setitem__('queue_full_lines_total', 3),
                 'mono decreases': lambda r: r[3].__setitem__('mono_s', 0.5),
                 'header missing': lambda r: r.pop(0),
                 'mixed schema': lambda r: r[1].__setitem__('schema', 'igvc_transport_timing_v1')}
        for name, corrupt in cases.items():
            with self.subTest(name):
                records = [dict(r) for r in p.records]
                corrupt(records)
                report = self.summarize(log_text(records))
                self.assertEqual(report['status'], 'incomplete', name)
                self.assertGreater(report['integrity_issue_count'], 0)

    def test_zero_warning_lines_are_reported_without_claiming_no_drops(self):
        p = Producer()
        t = p.run(130)
        p.stop(t + .1)
        report = self.summarize(log_text(p.records))
        lines = report['connector_warning_lines']
        self.assertEqual((lines['total_observed'], lines['records_with_new_lines']), (0, 0))
        self.assertIn('never proves that nothing was dropped', report['uncertainty']['warnings'])
        p = Producer()
        p.run(70)
        p.sample(2.0)
        p.record('window', 2.0001, lines=4, error=True)
        p.stop(2.1)
        lines = self.summarize(log_text(p.records))['connector_warning_lines']
        self.assertEqual((lines['total_observed'], lines['first_and_last_seq_with_new_lines'],
                          lines['records_reporting_connection_error']), (4, [2, 2], 1))

    def test_cap_exhaustion_is_complete_with_finite_coverage(self):
        p = Producer(cap=5)
        p.run(400)
        report = self.summarize(log_text(p.records))
        self.assertEqual(report['status'], 'complete', report.get('integrity_issues'))
        self.assertEqual(report['final']['kind'], 'exhausted')
        self.assertEqual(report['records']['count_including_header'], 5)
        self.assertTrue(0 < report['coverage']['covered_mono_span_s'] < 5)
        early = [dict(r) for r in p.records]
        early[2]['kind'] = 'exhausted'
        self.assertEqual(self.summarize(log_text(early[:3]))['status'], 'incomplete')  # exhausted before the cap

    def test_oversize_and_excess_records_are_bounded_and_still_hashed(self):
        p = Producer()
        t = p.run(70)
        p.stop(t + .1)
        text = log_text(p.records) + 'x'*(diag.MAX_LINE_BYTES + 10) + '\n'
        report = self.summarize(text)
        self.assertTrue(any(i.startswith('oversize_lines') for i in report['integrity_issues']))
        self.assertEqual(report['input']['bytes'], len(text.encode()))
        self.assertEqual(report['input']['sha256'], hashlib.sha256(text.encode()).hexdigest())

    def test_wrongly_typed_fields_are_incomplete_evidence_never_exceptions(self):
        p = Producer()
        t = p.run(200)
        p.stop(t + .1)
        huge_text = 'x'*50000  # below the line cap, so the bounded echo itself is exercised
        bad_values = {'list': ['igvc_transport_timing_v2'], 'empty list': [], 'dict': {'a': 1}, 'string': '3',
                      'negative float': -1.5, 'huge int': 10**30, 'oversize int': int('9'*400), 'bool': True, 'null': None,
                      'huge text': huge_text}
        fields = {0: ('schema', 'kind', 'seq', 'record_cap', 'report_interval_s', 'mono_frequency_hz', 'utc',
                      'mono_before_utc_s'),
                  2: ('schema', 'kind', 'seq', 'frames', 'total_frames', 'mono_s', 'window_max_frame_gap_s',
                      'cumulative_max_frame_gap_s', 'queue_full_lines_since_previous_record', 'queue_full_lines_total',
                      'utc', 'mono_before_utc_s', 'mono_after_utc_s'),
                  4: ('kind', 'seq', 'note', 'mono_s', 'mono_before_utc_s', 'cumulative_last_queue_full_observed_mono_s')}
        for index, names in fields.items():
            for field in names:
                for label, value in bad_values.items():
                    if field == 'note' and label not in ('list', 'dict', 'huge text'):
                        continue  # a note is free text; only non-string or oversize notes matter here
                    if field == 'cumulative_last_queue_full_observed_mono_s' and label == 'null':
                        continue  # null is valid: no warning observed yet
                    with self.subTest(record=index, field=field, value=label):
                        records = [dict(r) for r in p.records]
                        records[index][field] = value
                        report = self.summarize(log_text(records))  # must not raise
                        self.assertLess(len(json.dumps(report)), 20000)  # bad values are echoed bounded
                        if field != 'note':
                            self.assertEqual(report['status'], 'incomplete')
        # Root reproducer cases (r0 crashed with unhashable list): list-valued schema and kind.
        for field in ('schema', 'kind'):
            records = [dict(r) for r in p.records]
            records[1][field] = ['igvc_transport_timing_v2'] if field == 'schema' else []
            report = self.summarize(log_text(records))
            self.assertEqual(report['status'], 'incomplete')
        # Values that parse as non-finite floats (1e400) are rejected too.
        text = log_text(p.records).replace('"mono_s":%r' % p.records[2]['mono_s'], '"mono_s":1e400', 1)
        self.assertEqual(self.summarize(text)['status'], 'incomplete')

    def complete_run(self):
        p = Producer()
        t = p.run(200)
        p.stop(t + .1)
        return p

    def test_pathological_or_duplicate_key_json_is_malformed_not_a_crash(self):
        good = log_text(self.complete_run().records)
        nested = '{"schema":"igvc_transport_timing_v2","x":' + '['*30000 + ']'*30000 + '}'
        duplicate = json.dumps(dict(self.complete_run().records[1]), separators=(',', ':'))[:-1] + ',"seq":1}'
        for name, extra in {'deep nesting': nested, 'duplicate key': duplicate}.items():
            with self.subTest(name):
                report = self.summarize(good + extra + '\n')
                self.assertEqual(report['status'], 'incomplete')
                self.assertTrue(any(i.startswith('malformed_trace_lines') for i in report['integrity_issues']))

    def test_producer_consistency_rejects_reproduced_false_completes(self):
        cases = {'first window starts at -1000': lambda r: r[1].__setitem__('window_start_mono_s', -1000.),
                 'window does not start at previous last frame': lambda r: r[2].__setitem__('window_start_mono_s', 0.5),
                 'cumulative max 1000 with small windows': lambda r: [x.__setitem__('cumulative_max_frame_gap_s', 1000.)
                                                                      for x in r[1:]],
                 'gap larger than its window span': lambda r: [r[1].__setitem__('window_max_frame_gap_s', 5.),
                                                               [x.__setitem__('cumulative_max_frame_gap_s', 5.) for x in r[1:]]],
                 'record_cap 2 with 5 records': lambda r: r[0].__setitem__('record_cap', 2),
                 'negative last frame': lambda r: r[1].__setitem__('mono_s', -0.5)}
        for name, corrupt in cases.items():
            with self.subTest(name):
                records = [dict(r) for r in self.complete_run().records]
                corrupt(records)
                report = self.summarize(log_text(records))
                self.assertEqual(report['status'], 'incomplete', name)
                self.assertTrue(report['derived_fields'].startswith('unvalidated'))
                self.assertIsNone(report['final']['unsampled_tail_s'])     # derived spans withheld
                self.assertIsNone(report['coverage']['covered_mono_span_s'])
        p = Producer()  # a stop before any frame has no window start and is valid
        p.stop(.05)
        self.assertEqual(self.summarize(log_text(p.records))['status'], 'complete')

    def test_lower_bounds_ordering_and_interval_reject_remaining_false_completes(self):
        def understate(r):  # a dropped boundary-crossing gap: window max far below span / gaps
            r[2]['window_max_frame_gap_s'] = 1e-3
        cases = {'understated later-window gap': understate,
                 'understated first-window gap (n-1 gaps)': lambda r: [r[1].__setitem__('window_max_frame_gap_s', 1e-3),
                                                                       r[1].__setitem__('cumulative_max_frame_gap_s', 1e-3)],
                 'periodic window shorter than interval': lambda r: r[0].__setitem__('report_interval_s', 5.0),
                 'utc brackets out of order': lambda r: [r[2].__setitem__('mono_before_utc_s', r[1]['mono_after_utc_s'] - .5),
                                                         r[2].__setitem__('mono_after_utc_s', r[1]['mono_after_utc_s'] - .4)],
                 'first frame before header bracket': lambda r: [r[0].__setitem__('mono_before_utc_s', 0.5),
                                                                 r[0].__setitem__('mono_after_utc_s', 0.6)],
                 'final bracket before header (negative span)': lambda r: [r[0].__setitem__('mono_before_utc_s', 10**6),
                                                                           r[0].__setitem__('mono_after_utc_s', 10**6)]}
        for name, corrupt in cases.items():
            with self.subTest(name):
                records = [dict(r) for r in self.complete_run().records]
                corrupt(records)
                report = self.summarize(log_text(records))
                self.assertEqual(report['status'], 'incomplete', name)
                self.assertIsNone(report['coverage']['covered_mono_span_s'])
        # Valid edge cases stay complete: a stop before any frame, and a partial final window shorter than the interval.
        p = Producer()
        p.stop(.05)
        self.assertEqual(self.summarize(log_text(p.records))['status'], 'complete')
        p = Producer()
        t = p.run(75)          # one periodic window, then 14 more frames (0.23 s) before the stop
        p.stop(t + .01)
        report = self.summarize(log_text(p.records))
        self.assertEqual(report['status'], 'complete', report.get('integrity_issues'))
        self.assertGreaterEqual(report['coverage']['covered_mono_span_s'], 0)
        self.assertIn('START of the final record', report['final']['unsampled_tail_meaning'])
        p = Producer()
        p.run(200)
        missing = self.summarize(log_text(p.records))
        self.assertIn('cause not determined', ' '.join(missing['integrity_issues']))

    def test_unwritable_output_path_is_reported_narrowly(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory)/'unity.log'
            log.write_bytes(log_text(self.complete_run().records).encode('utf-8'))
            out = Path(directory)/'missing-dir'/'report.json'
            self.assertEqual(diag.main(['--unity-log', str(log), '--output', str(out)]), 2)
            self.assertFalse(out.exists())

    def test_kind_histogram_is_bounded(self):
        records = [dict(r) for r in self.complete_run().records]
        records += [dict(records[1], kind='k%05d' % i, seq=100 + i) for i in range(900)]
        report = self.summarize(log_text(records))
        self.assertEqual(set(report['records']['by_kind']), {'window', 'stopped', '<invalid>'})
        self.assertLess(len(json.dumps(report)), 20000)

    def test_crlf_log_record_limit_and_multichunk_oversize(self):
        p = self.complete_run()
        crlf = log_text(p.records).replace('\n', '\r\n')
        report = self.summarize(crlf)
        self.assertEqual(report['status'], 'complete', report.get('integrity_issues'))
        self.assertEqual(report['input']['sha256'], hashlib.sha256(crlf.encode()).hexdigest())
        with patch.object(diag, 'MAX_RECORDS', 3):
            report = self.summarize(log_text(p.records))
        self.assertTrue(any(i.startswith('record_limit_exceeded: 2') for i in report['integrity_issues']))
        self.assertEqual(report['status'], 'incomplete')
        text = log_text(p.records) + 'y'*(2*diag.MAX_LINE_BYTES + 77) + '\n' + 'tail line\n'
        report = self.summarize(text)
        self.assertTrue(any(i.startswith('oversize_lines: 1') for i in report['integrity_issues']))
        self.assertEqual((report['input']['bytes'], report['input']['sha256']),
                         (len(text.encode()), hashlib.sha256(text.encode()).hexdigest()))
        self.assertEqual(report['input']['lines'], text.count('\n'))

    def test_cli_reports_unreadable_input_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            missing, out = Path(directory)/'absent.log', Path(directory)/'report.json'
            self.assertEqual(diag.main(['--unity-log', str(missing), '--output', str(out)]), 2)
            self.assertFalse(out.exists())
            self.assertEqual(diag.main(['--unity-log', directory, '--output', str(out)]), 2)

    def test_cli_requires_output_and_never_overwrites(self):
        p = Producer()
        t = p.run(70)
        p.stop(t + .1)
        with tempfile.TemporaryDirectory() as directory:
            log, out = Path(directory)/'unity.log', Path(directory)/'report.json'
            log.write_bytes(log_text(p.records).encode('utf-8'))
            self.assertEqual(diag.main(['--unity-log', str(log), '--output', str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())['status'], 'complete')
            self.assertEqual(diag.main(['--unity-log', str(log), '--output', str(out)]), 1)
            with self.assertRaises(SystemExit):
                diag.main(['--unity-log', str(log)])


if __name__ == '__main__':
    unittest.main()
