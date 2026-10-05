import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sensor_telemetry import SensorTelemetry
from record_sensor_health import main, record


class TelemetryTests(unittest.TestCase):
    def test_live_rgb_and_failed_lane_pipeline_are_distinct(self):
        now = [0.]
        telemetry = SensorTelemetry(clock=lambda: now[0])
        for i in range(10):
            now[0] = i*.1
            telemetry.observe_clock(i*100_000_000)
            telemetry.observe('rgb', i*100_000_000)
            telemetry.status('lanes', {'valid': False, 'reason': 'waiting_for_depth_ground_or_rgb_tf'})
        report = telemetry.report()
        self.assertAlmostEqual(report['streams']['rgb']['max_gap_s'], .1)
        self.assertEqual(report['status_reason_counts']['lanes']['waiting_for_depth_ground_or_rgb_tf'], 10)
        self.assertEqual(report['streams']['rgb']['count'], 10)
        json.dumps(report, allow_nan=False)

    def test_trailing_dropout_is_included_and_history_is_bounded(self):
        now = [0.]
        telemetry = SensorTelemetry(clock=lambda: now[0], window=3, event_limit=2)
        for i in range(8):
            now[0] = i*.1
            telemetry.observe('rgb', i)
            telemetry.status('health', True)
        now[0] += .9
        report = telemetry.report()
        self.assertAlmostEqual(report['streams']['rgb']['max_gap_including_tail_s'], .9)
        self.assertEqual(len(telemetry.streams['rgb']['gaps']), 3)
        self.assertEqual(len(report['recent_events']), 2)
        self.assertEqual(report['total_status_events'], 8)

    def test_stamp_resets_and_callback_ordering_are_not_hidden(self):
        telemetry = SensorTelemetry(clock=lambda: 0.)
        telemetry.observe_clock(10)
        telemetry.observe('rgb', 20)
        telemetry.observe('rgb', 20)
        telemetry.observe_clock(0)
        telemetry.observe('rgb', 0)
        report = telemetry.report()
        self.assertEqual(report['clock_resets'], 1)
        self.assertEqual(report['streams']['rgb']['negative_lag_samples'], 2)
        self.assertEqual(report['streams']['rgb']['duplicates'], 1)
        self.assertEqual(report['streams']['rgb']['stamp_regressions'], 1)

    def test_large_json_and_unicode_statuses_are_byte_bounded(self):
        telemetry = SensorTelemetry(clock=lambda: 0., event_limit=2, status_byte_limit=512)
        payloads = [{'valid': True, 'reason': 'many_points', 'points': ['x'*1000]},
                    json.dumps({'reason': 'oversize', 'points': ['x'*1000]}),
                    {'reason': '\x00'*1000, 'points': ['x'*1000]}, '😀'*200]
        for payload in payloads:
            telemetry.status('lanes', payload)
        report = telemetry.report()
        self.assertEqual(report['total_status_events'], 4)
        self.assertEqual(report['streams']['lanes']['count'], 4)
        self.assertEqual(report['status_rejection_counts']['lanes']['status_payload_too_large'], 4)
        self.assertEqual(report['status_reason_counts']['lanes']['many_points'], 1)
        for event in report['recent_events']:
            self.assertLessEqual(len(json.dumps(event['value'], ensure_ascii=False).encode('utf-8')), 512)
            self.assertIs(event['value']['valid'], False)
        json.dumps(report, allow_nan=False)

    def test_nonfinite_status_is_rejected_without_losing_reasons_or_counts(self):
        telemetry = SensorTelemetry(clock=lambda: 0.)
        for payload in ('{"valid":true,"reason":"bad_plane","ground":[NaN]}',
                        '{"valid":true,"reason":"bad_plane","lag":1e999}',
                        {'valid': True, 'reason': 'bad_plane', 'ground': {'offset': float('inf')}}):
            telemetry.status('lanes', payload)
        report = telemetry.report()
        self.assertEqual(report['streams']['lanes']['count'], 3)
        self.assertEqual(report['status_reason_counts']['lanes']['bad_plane'], 3)
        self.assertEqual(report['status_rejection_counts']['lanes']['nonfinite_or_unserializable_status'], 3)
        self.assertEqual(report['processing_health_summary']['checks']['lanes']['status'], 'fail')
        json.dumps(report, allow_nan=False)

    def test_successful_processing_needs_fresh_receipt_clock_and_acquisition(self):
        now = [0.]
        telemetry = SensorTelemetry(clock=lambda: now[0])
        telemetry.observe_clock(10_000_000_000)
        for name in ('lanes', 'depth_processing'):
            telemetry.status(name, {'valid': True, 'stamp_ns': 9_900_000_000})
        telemetry.status('lane_health', True)
        telemetry.status('depth_health', True)
        self.assertTrue(telemetry.health_summary()['fresh_successful_processing'])
        now[0] = 2.
        self.assertEqual(telemetry.health_summary()['status'], 'unknown')
        telemetry.observe_clock(12_000_000_000)
        for name in ('lanes', 'depth_processing'):
            telemetry.status(name, {'valid': True, 'stamp_ns': 9_900_000_000})
        telemetry.status('lane_health', True)
        telemetry.status('depth_health', True)
        self.assertFalse(telemetry.health_summary()['fresh_successful_processing'])
        telemetry.status('lanes', {'valid': True, 'stamp_ns': 12_000_000_001})
        self.assertEqual(telemetry.health_summary()['checks']['lanes']['status'], 'unknown')
        telemetry.status('lanes', {'valid': True, 'stamp_ns': 10**400})
        self.assertEqual(telemetry.health_summary()['checks']['lanes']['status'], 'unknown')

    def test_missing_clock_or_success_stamp_is_unknown(self):
        telemetry = SensorTelemetry(clock=lambda: 0.)
        for name in ('lanes', 'depth_processing'):
            telemetry.status(name, {'valid': True})
        self.assertEqual(telemetry.health_summary()['status'], 'unknown')
        telemetry.observe_clock(1)
        self.assertEqual(telemetry.health_summary()['status'], 'unknown')

    def test_live_images_do_not_override_failed_processing(self):
        telemetry = SensorTelemetry(clock=lambda: 0.)
        telemetry.observe('rgb', 1)
        telemetry.observe('depth', 1)
        telemetry.status('lanes', {'valid': False, 'reason': 'missing_transform'})
        telemetry.status('depth_processing', {'valid': False, 'reason': 'no_new_pair'})
        summary = telemetry.health_summary()
        self.assertEqual(summary['status'], 'fail')
        self.assertFalse(summary['fresh_successful_processing'])

    def test_legitimate_lane_gap_is_processed_with_insufficient_visibility(self):
        telemetry = SensorTelemetry(clock=lambda: 0.)
        telemetry.observe_clock(10_000_000_000)
        telemetry.status('lane_health', True)
        telemetry.status('depth_health', True)
        telemetry.status('lanes', {'valid': False, 'stamp_ns': 9_900_000_000,
                                    'current_points': 11, 'components': 1})
        telemetry.status('depth_processing', {'valid': True, 'stamp_ns': 9_900_000_000})
        summary = telemetry.health_summary()
        self.assertEqual(summary['status'], 'pass')
        self.assertTrue(summary['fresh_successful_processing'])
        self.assertEqual(summary['lane_detection_visibility']['status'], 'insufficient')
        self.assertEqual(summary['lane_detection_visibility']['current_points'], 11)
        telemetry.status('lanes', {'valid': False, 'reason': 'acquisition_tf_not_ready'})
        self.assertEqual(telemetry.health_summary()['checks']['lanes']['status'], 'fail')

    def test_missing_or_stale_health_cannot_establish_processing_success(self):
        now = [0.]
        telemetry = SensorTelemetry(clock=lambda: now[0])
        telemetry.observe_clock(10_000_000_000)
        for name in ('lanes', 'depth_processing'):
            telemetry.status(name, {'valid': True, 'stamp_ns': 10_000_000_000})
        self.assertEqual(telemetry.health_summary()['status'], 'unknown')
        telemetry.status('lane_health', True)
        telemetry.status('depth_health', True)
        self.assertEqual(telemetry.health_summary()['status'], 'pass')
        now[0] = 2.
        telemetry.observe_clock(12_000_000_000)
        for name in ('lanes', 'depth_processing'):
            telemetry.status(name, {'valid': True, 'stamp_ns': 12_000_000_000})
        self.assertEqual(telemetry.health_summary()['status'], 'unknown')
        telemetry.status('lane_health', False)
        self.assertEqual(telemetry.health_summary()['checks']['lanes']['status'], 'fail')

    def test_rejected_lane_status_fails_despite_fresh_positive_health(self):
        telemetry = SensorTelemetry(clock=lambda: 0.)
        telemetry.observe_clock(1)
        telemetry.status('lane_health', True)
        telemetry.status('lanes', {'valid': False, 'stamp_ns': 1, 'ground': float('nan')})
        self.assertEqual(telemetry.health_summary()['checks']['lanes']['status'], 'fail')

    def test_reason_cardinality_and_saved_report_do_not_change_later(self):
        telemetry = SensorTelemetry(clock=lambda: 0.)
        for i in range(70):
            telemetry.status('lanes', {'valid': False, 'reason': str(i)})
        first = telemetry.report()
        self.assertEqual(len(first['status_reason_counts']['lanes']), 64)
        first_counts = dict(first['status_reason_counts']['lanes'])
        telemetry.status('lanes', {'valid': True, 'stamp_ns': 0})
        self.assertEqual(first['status_reason_counts']['lanes'], first_counts)
        self.assertFalse(first['latest_status']['lanes']['valid'])


class RecorderTests(unittest.TestCase):
    def ros(self):
        ros = Mock()
        ros.ok.return_value = False
        return ros

    def test_recording_succeeds_with_no_health_evidence(self):
        ros = self.ros()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'report.json'
            report = record(.1, output, ros, attach=lambda node: SensorTelemetry(clock=lambda: 0.), clock=lambda: 0.)
            self.assertEqual(report['recording_status'], 'recorded')
            self.assertEqual(report['processing_health_summary']['status'], 'unknown')
            self.assertEqual(json.loads(output.read_text())['streams'], {})
        ros.create_node.return_value.destroy_node.assert_called_once()
        ros.try_shutdown.assert_called_once()
        with patch.dict(sys.modules, {'rclpy': ros}), patch('record_sensor_health.record', return_value=report), patch('builtins.print'):
            self.assertEqual(main(['--duration', '.1', '--output', 'unused.json']), 0)

    def test_attachment_failure_releases_node_and_context(self):
        ros = self.ros()
        with self.assertRaisesRegex(RuntimeError, 'subscription failed'):
            record(.1, Path('unused.json'), ros, attach=Mock(side_effect=RuntimeError('subscription failed')))
        ros.create_node.return_value.destroy_node.assert_called_once()
        ros.try_shutdown.assert_called_once()

    def test_node_creation_failure_releases_initialized_context(self):
        ros = self.ros()
        ros.create_node.side_effect = RuntimeError('create failed')
        with self.assertRaisesRegex(RuntimeError, 'create failed'):
            record(.1, Path('unused.json'), ros)
        ros.try_shutdown.assert_called_once()

    def test_report_write_failure_still_releases_resources(self):
        ros = self.ros()
        output = Mock()
        output.write_text.side_effect = OSError('disk full')
        with self.assertRaisesRegex(OSError, 'disk full'):
            record(.1, output, ros, attach=lambda node: SensorTelemetry(clock=lambda: 0.), clock=lambda: 0.)
        ros.create_node.return_value.destroy_node.assert_called_once()
        ros.try_shutdown.assert_called_once()

    def test_context_shutdown_runs_even_when_node_cleanup_fails(self):
        ros = self.ros()
        ros.create_node.return_value.destroy_node.side_effect = RuntimeError('destroy failed')
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(RuntimeError, 'destroy failed'):
            record(.1, Path(directory)/'report.json', ros, attach=lambda node: SensorTelemetry(clock=lambda: 0.), clock=lambda: 0.)
        ros.try_shutdown.assert_called_once()


if __name__ == '__main__':
    unittest.main()
