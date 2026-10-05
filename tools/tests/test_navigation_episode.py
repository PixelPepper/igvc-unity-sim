"""Recorder pairing, bounded retention and disk format without ROS/live sessions."""
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from record_navigation_episode import (BoundedCache, Observation, EpisodeWriter,
    camera_metadata, choose_anchor, decode_image, decode_lane_evidence,
    event_record, observation_metadata, select_observation, write_bundle,
    acquisition_stamp, motion_payload_within_bounds, MAX_SUSPENSION_JOINTS)


def header(ns, frame='camera'):
    return NS(stamp=NS(sec=ns//1_000_000_000, nanosec=ns%1_000_000_000), frame_id=frame)


def image(ns=100, encoding='rgb8'):
    width, height = 2, 2
    depth = encoding == '32FC1'
    channels = 3 if encoding == 'rgb8' else 1
    step = width*(4 if depth else channels)+2
    rows = ([struct.pack('<ff', 1., float('nan')), struct.pack('<ff', 2., 3.)]
            if depth else [bytes(range(width*channels))]*height)
    return NS(header=header(ns), encoding=encoding, width=width, height=height,
              step=step, data=b''.join(row+b'\x00\x00' for row in rows), is_bigendian=False)


def info(ns=100):
    return NS(header=header(ns), width=2, height=2, k=[10.,0.,1.,0.,10.,1.,0.,0.,1.],
              d=[], r=[1.,0.,0.,0.,1.,0.,0.,0.,1.], p=[0.]*12, distortion_model='plumb_bob')


def twist(v=.05, w=.08):
    return NS(linear=NS(x=v, y=0., z=0.), angular=NS(x=0., y=0., z=w))


class NavigationEpisodeTests(unittest.TestCase):
    def test_nav_twist_has_no_invented_acquisition_stamp(self):
        message = twist()
        record = event_record('/cmd_vel/nav', Observation(acquisition_stamp(message), 123.4, message))
        self.assertIsNone(record['acquisition_stamp_ns'])
        self.assertTrue(record['headerless'])
        self.assertEqual(record['linear'], [.05, 0., 0.])
        self.assertEqual(record['angular'], [0., 0., .08])
        self.assertEqual(record['received_monotonic_s'], 123.4)

    def test_transported_twist_retains_original_command_stamp_across_repeats(self):
        message = NS(header=header(987654321012, 'base_footprint'), twist=twist(.1, -.12))
        records = [event_record('/sim/drive_command', Observation(acquisition_stamp(message), wall, message,
                   message.header.frame_id)) for wall in (1., 1.05)]
        self.assertEqual([r['acquisition_stamp_ns'] for r in records], [987654321012]*2)
        self.assertEqual(records[1]['frame_id'], 'base_footprint')
        self.assertEqual(records[1]['linear'], [.1, 0., 0.])
        self.assertEqual(records[1]['angular'], [0., 0., -.12])
        self.assertFalse(records[1]['headerless'])
        self.assertEqual(records[1]['stamp_semantics'], 'adapter_command_acceptance_sim_time')
        self.assertNotEqual(records[0]['received_monotonic_s'], records[1]['received_monotonic_s'])

    def test_suspension_joint_state_preserves_names_stamp_and_missing_effort(self):
        message = NS(header=header(456789012345, 'base_link'),
            name=['rear_body_height', 'left_compression', 'right_compression'],
            position=[.3, .01, .02], velocity=[float('nan'), -.03, .04], effort=[])
        record = event_record('/sim/suspension_state', Observation(acquisition_stamp(message), 1., message, 'base_link'))
        self.assertEqual(record['acquisition_stamp_ns'], 456789012345)
        self.assertEqual(record['name'], message.name)
        self.assertEqual(record['position'], [.3, .01, .02])
        self.assertEqual(record['velocity'], [None, -.03, .04])
        self.assertEqual(record['effort'], [])
        self.assertTrue(record['joint_arrays_aligned'])
        self.assertEqual(record['nonfinite_values'], 'null')
        json.dumps(record, allow_nan=False)
        message.velocity = [.2]
        self.assertFalse(event_record('/sim/suspension_state', Observation(10, 1., message))['joint_arrays_aligned'])

    def test_motion_payload_bounds_reject_oversized_arrays_and_utf8_names(self):
        message = NS(header=header(10, 'base_link'), name=['joint'], position=[0.], velocity=[], effort=[])
        self.assertTrue(motion_payload_within_bounds('/sim/suspension_state', message))
        for key in ('name', 'position', 'velocity', 'effort'):
            original = getattr(message, key)
            setattr(message, key, ['x']*(MAX_SUSPENSION_JOINTS+1) if key == 'name' else [0.]*(MAX_SUSPENSION_JOINTS+1))
            self.assertFalse(motion_payload_within_bounds('/sim/suspension_state', message))
            with self.assertRaises(ValueError):
                event_record('/sim/suspension_state', Observation(10, 1., message))
            setattr(message, key, original)
        message.name = ['é'*65]  # 65 characters, 130 UTF-8 bytes.
        self.assertFalse(motion_payload_within_bounds('/sim/suspension_state', message))
        command = NS(header=header(10, 'é'*257), twist=twist())
        self.assertFalse(motion_payload_within_bounds('/sim/drive_command', command))

    def test_motion_topics_survive_history_writer_with_distinct_timing(self):
        suspension = NS(header=header(200, 'base_link'), name=['rear_body_height'],
                        position=[.3], velocity=[0.], effort=[])
        drive = NS(header=header(100, 'base_footprint'), twist=twist())
        samples = [('/cmd_vel/nav', Observation(None, 1., twist())),
                   ('/sim/drive_command', Observation(100, 1.01, drive, 'base_footprint')),
                   ('/sim/suspension_state', Observation(200, 1.02, suspension, 'base_link'))]
        with tempfile.TemporaryDirectory() as temp:
            writer = EpisodeWriter(Path(temp), capacity=8)
            for sample in samples:
                self.assertTrue(writer.submit('event', sample))
            self.assertTrue(writer.finish())
            self.assertFalse(writer.counters.get('write_errors'))
            rows = [json.loads(line) for line in (Path(temp)/'history.jsonl').read_text().splitlines()]
            self.assertEqual([r['topic'] for r in rows], [t for t, _ in samples])
            self.assertEqual([r['acquisition_stamp_ns'] for r in rows], [None, 100, 200])

    def test_nearby_acquisitions_are_skewed_and_unknown_never_exact(self):
        sample = Observation(110, 1., object())
        selected, evidence = select_observation([sample], 100, 1.1, max_skew_ns=20)
        self.assertIs(selected, sample)
        self.assertEqual(evidence['skew_ns'], 10)
        self.assertEqual(evidence['status'], 'skewed')
        self.assertFalse(evidence['synchronized'])
        selected, evidence = select_observation([Observation(None, 1., object())], 100, 1.1)
        self.assertIsNone(selected)
        self.assertEqual(evidence['status'], 'unavailable')

    def test_projection_source_cannot_be_replaced_by_newer_depth(self):
        source = Observation(900, 1., object())
        newer = Observation(1000, 1.05, object())
        selected, evidence = select_observation([source, newer], 900, 1.1, max_skew_ns=0)
        self.assertIs(selected, source)
        selected, evidence = select_observation([newer], 900, 1.1, max_skew_ns=0)
        self.assertIsNone(selected)
        self.assertFalse(evidence['synchronized'])
        self.assertEqual(evidence['target_stamp_ns'], 900)

    def test_stale_exact_pair_is_not_accepted(self):
        selected, evidence = select_observation([Observation(100, 0., object())], 100, 1.)
        self.assertIsNone(selected)
        selected, _ = select_observation([Observation(100, 2., object())], 100, 1.)
        self.assertIsNone(selected)

    def test_anchor_prefers_actual_processed_rgb_mask_pair(self):
        old_rgb = Observation(100, 1., object())
        latest_rgb = Observation(110, 1.1, object())
        mask = Observation(100, 1.15, object())
        chosen, source = choose_anchor([old_rgb, latest_rgb], [mask], 1.2)
        self.assertIs(chosen, mask)
        self.assertEqual(source, 'lane_mask')
        chosen, _ = choose_anchor([old_rgb, latest_rgb], [mask], 1.2, previous_reception=1.15)
        self.assertIsNone(chosen)

    def test_cache_bounds_and_clock_reset_use_reception_order(self):
        cache = BoundedCache(2)
        samples = [Observation(stamp, wall, object()) for stamp, wall in [(1000,1.), (1001,1.1), (10,1.2)]]
        for sample in samples:
            cache.add(sample)
        self.assertEqual(len(cache.values()), 2)
        self.assertEqual(cache.evicted, 1)
        self.assertEqual(cache.regressions, 1)
        anchor, _ = choose_anchor(cache.values(), [], 1.3)
        self.assertEqual(anchor.stamp_ns, 10)

    def test_camera_info_requires_same_stamp_frame_and_dimensions(self):
        self.assertTrue(camera_metadata(image(), info())['valid'])
        self.assertFalse(camera_metadata(image(), info(101))['valid'])
        wrong = info(); wrong.header.frame_id='wrong'
        self.assertFalse(camera_metadata(image(), wrong)['valid'])
        wrong = info(); wrong.width=3
        self.assertFalse(camera_metadata(image(), wrong)['valid'])

    def test_padded_image_rows_preserve_metric_depth_and_nan(self):
        rgb = decode_image(image())
        self.assertEqual(rgb.shape, (2,2,3))
        self.assertEqual(rgb[1,1].tolist(), [3,4,5])
        depth = decode_image(image(encoding='32FC1'))
        self.assertEqual(depth[1].tolist(), [2.,3.])
        self.assertTrue(np.isnan(depth[0,1]))
        broken = image(); broken.step=1
        with self.assertRaises(ValueError):
            decode_image(broken)

    def test_provenance_uint_timestamps_survive_compressed_storage(self):
        names=('x','y','z','age_wall_s','observations','confirmed','stamp_sec','stamp_nanosec')
        cloud = NS(height=1,width=1,point_step=32,row_step=32,is_bigendian=True,
                   data=struct.pack('>ffffIIII',1.,2.,3.,.5,8,1,123,987654321),
                   fields=[NS(name=name,offset=i*4,datatype=7 if i<4 else 6,count=1) for i,name in enumerate(names)])
        values = decode_lane_evidence(cloud)
        self.assertEqual(int(values['stamp_nanosec'][0]), 987654321)
        self.assertEqual(int(values['confirmed'][0]), 1)
        cloud.point_step=16
        with self.assertRaises(ValueError):
            decode_lane_evidence(cloud)

    def test_headerless_decision_retains_embedded_acquisition_metadata(self):
        sample=Observation(None,1.2,NS(data=json.dumps(dict(phase='evaluated',odom_stamp_ns=900,sequence=2))))
        record=event_record('/mission/decision',sample)
        self.assertIsNone(record['acquisition_stamp_ns'])
        self.assertEqual(record['payload']['odom_stamp_ns'],900)
        self.assertEqual(record['received_monotonic_s'],1.2)

    def test_bundle_and_event_sink_format_with_bounded_event_count(self):
        now=1.2
        selected={key:Observation(ns,1.,message,'camera') for key,ns,message in
                  [('rgb',100,image()),('rgb_info',100,info()),('mask',100,image(encoding='mono8')),
                   ('depth',90,image(90,'32FC1')),('depth_info',90,info(90))]}
        metadata=dict(index=0,anchor_acquisition_stamp_ns=100,
                      observations={k:observation_metadata(s,now,100) for k,s in selected.items()})
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)
            write_bundle(output/'frame',dict(metadata=metadata,samples=selected))
            self.assertTrue((output/'frame/rgb.png').read_bytes().startswith(b'\x89PNG'))
            saved=json.loads((output/'frame/metadata.json').read_text())
            self.assertEqual(saved['observations']['depth']['skew_from_anchor_ns'],-10)
            self.assertTrue(saved['depth_camera']['valid'])
            with np.load(output/'frame/arrays.npz') as arrays:
                self.assertTrue(np.isnan(arrays['depth'][0,1]))
            writer=EpisodeWriter(output,capacity=1,max_events=1)
            event=('/mission/decision',Observation(None,1.,NS(data='{"sequence":1}')))
            self.assertTrue(writer.submit('event',event))
            self.assertFalse(writer.submit('event',event))
            self.assertTrue(writer.finish())
            self.assertEqual(writer.counters['event_limit_drops'],1)
            history=(output/'history.jsonl').read_text().splitlines()
            self.assertEqual(len(history),1)
            self.assertEqual(json.loads(history[0])['payload']['sequence'],1)


if __name__ == '__main__':
    unittest.main()
