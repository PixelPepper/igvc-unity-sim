"""Behavioral mission coverage tests using the actual telemetry summary emitter."""
import copy
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mission_health import MissionHealthLedger
from sensor_telemetry import SensorTelemetry


def summary(*, now=0., healthy=True, missing=False, lane_visible=True):
    wall = [0.]
    telemetry = SensorTelemetry(clock=lambda: wall[0])
    if not missing:
        telemetry.observe_clock(10_000_000_000)
        telemetry.status('lanes', {'valid':lane_visible,'stamp_ns':10_000_000_000})
        telemetry.status('depth_processing', {'valid':True,'stamp_ns':10_000_000_000})
        telemetry.status('lane_health', True)
        telemetry.status('depth_health', healthy)
    wall[0] = now
    return telemetry.health_summary(now=now)


class MissionHealthTests(unittest.TestCase):
    def ledger(self, **options):
        ledger = MissionHealthLedger(**options)
        ledger.begin(100.,10_000_000_000)
        return ledger

    def observe(self, ledger, time, health=None):
        return ledger.observe(summary() if health is None else health,
            100.+time,10_000_000_000+round(time*1e9))

    def end(self, ledger, time):
        return ledger.end(100.+time,10_000_000_000+round(time*1e9))

    def test_healthy_interval_has_complete_boundary_inclusive_coverage(self):
        ledger = self.ledger()
        for time in (.1,.2,.3,.4):
            self.assertEqual(self.observe(ledger,time), 'pass')
        result = self.end(ledger,.5)
        self.assertTrue(result['passed'])
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(result['totals'], {'pass':4,'fail':0,'unknown':0})
        self.assertAlmostEqual(result['max_gap_including_bounds_s'], .1)
        self.assertEqual(result['start']['odom_stamp_ns'],10_000_000_000)
        self.assertEqual(result['end']['odom_stamp_ns'],10_500_000_000)
        self.assertFalse(ledger.active)

    def test_mid_interval_failure_then_latest_pass_remains_failed(self):
        ledger = self.ledger()
        self.observe(ledger,.1)
        self.observe(ledger,.2,summary(healthy=False))
        self.observe(ledger,.3)
        result = self.end(ledger,.4)
        self.assertTrue(result['coverage_complete'])
        self.assertFalse(result['passed'])
        self.assertTrue(result['latched_fail'])
        self.assertEqual(result['totals']['fail'],1)
        self.assertIn('depth_processing:processing_health_false',result['reason_counts'])

    def test_missing_stale_and_unknown_samples_latch_without_rejecting_real_lane_gap(self):
        for health in (summary(missing=True),summary(now=2.),None):
            ledger = self.ledger()
            ledger.observe(health,100.1,10_100_000_000)
            self.observe(ledger,.2)
            result = self.end(ledger,.3)
            self.assertFalse(result['passed'])
            self.assertTrue(result['latched_unknown'])
        ledger = self.ledger()
        for time in (.1,.2):
            self.observe(ledger,time,summary(lane_visible=False))
        self.assertTrue(self.end(ledger,.3)['passed'])

    def test_zero_or_one_latest_healthy_sample_cannot_cover_interval(self):
        for count in (0,1):
            ledger = self.ledger()
            if count:
                self.observe(ledger,.1)
            result = self.end(ledger,.2)
            self.assertFalse(result['passed'])
            self.assertIn('fewer_than_two_distinct_samples',result['failure_reasons'])

    def test_first_tail_and_interior_gaps_are_all_coverage_failures(self):
        for times, end in (((.3,.4),.5), ((.1,.2),.5), ((.1,.4),.5)):
            ledger = self.ledger()
            for time in times:
                self.observe(ledger,time)
            result = self.end(ledger,end)
            self.assertFalse(result['coverage_complete'])
            self.assertFalse(result['passed'])
            self.assertAlmostEqual(result['max_gap_including_bounds_s'], .3)

    def test_exact_gap_bound_can_pass(self):
        ledger = self.ledger()
        for time in (.25,.5):
            self.observe(ledger,time)
        self.assertTrue(self.end(ledger,.75)['passed'])

    def test_wall_or_sim_clock_reset_and_duplicate_ticks_fail_closed(self):
        for wall, stamp, reason in ((100.05,10_200_000_000,'wall_clock_regression'),
                                   (100.2,9_000_000_000,'odom_clock_regression'),
                                   (100.1,10_100_000_000,'duplicate_wall_sample')):
            ledger = self.ledger()
            self.observe(ledger,.1)
            ledger.observe(summary(),wall,stamp)
            self.observe(ledger,.3)
            result = self.end(ledger,.4)
            self.assertFalse(result['passed'])
            self.assertIn(reason,result['integrity_errors'])

    def test_nonfinite_and_malformed_summary_cannot_create_evidence(self):
        malformed = copy.deepcopy(summary())
        malformed['checks']['lanes']['age_wall_s'] = math.nan
        forged = {'status':'pass','fresh_successful_processing':True}
        inconsistent = copy.deepcopy(summary())
        inconsistent['checks']['lanes']['reported_healthy'] = False
        for health in (malformed,forged,inconsistent):
            ledger = self.ledger()
            self.observe(ledger,.1,health)
            self.observe(ledger,.2)
            result = self.end(ledger,.3)
            self.assertFalse(result['passed'])
            json.dumps(result,allow_nan=False)
        for now,stamp in ((math.nan,10_100_000_000),(100.1,-1),(100.1,True)):
            ledger = self.ledger()
            ledger.observe(summary(),now,stamp)
            self.observe(ledger,.2)
            result = self.end(ledger,.3)
            self.assertFalse(result['passed'])
            self.assertIn('invalid_sample_boundary',result['integrity_errors'])
            json.dumps(result,allow_nan=False)

    def test_invalid_begin_or_end_and_nonpositive_elapsed_fail_closed(self):
        with self.assertRaises(ValueError):
            MissionHealthLedger().begin(math.inf,0)
        with self.assertRaises(ValueError):
            MissionHealthLedger(max_gap_s=math.nan)
        for now,stamp in ((math.nan,10_300_000_000),(100.05,10_300_000_000),
                          (100.3,9_000_000_000)):
            ledger = self.ledger()
            self.observe(ledger,.1)
            self.observe(ledger,.2)
            result = ledger.end(now,stamp)
            self.assertFalse(result['passed'])
            json.dumps(result,allow_nan=False)
        ledger = self.ledger()
        ledger.observe(summary(),100.,10_000_000_000)
        self.assertFalse(ledger.end(100.,10_000_000_000)['passed'])

    def test_bounded_history_cannot_erase_earlier_failure_or_mutate_snapshot(self):
        ledger = self.ledger(event_limit=2)
        self.observe(ledger,.1,summary(healthy=False))
        for time in (.2,.3,.4,.5):
            self.observe(ledger,time)
        result = self.end(ledger,.6)
        self.assertEqual(len(result['recent_events']),2)
        self.assertEqual(result['sample_count'],5)
        self.assertEqual(result['totals']['fail'],1)
        self.assertIsNotNone(result['first_fail'])
        self.assertFalse(result['passed'])
        result['totals']['fail'] = 0
        self.assertEqual(self.end(ledger,.8)['totals']['fail'],1)
        self.assertIsNone(ledger.observe(summary(),101.,11_000_000_000))

    def test_finite_endpoints_with_overflowed_elapsed_are_serializable_failures(self):
        ledger = MissionHealthLedger()
        ledger.begin(-1e308,0)
        ledger.observe(summary(),-1e308,0)
        ledger.observe(summary(),1e308,1)
        result = ledger.end(1e308,2)
        self.assertFalse(result['passed'])
        self.assertIn('invalid_sample_elapsed',result['integrity_errors'])
        self.assertIn('invalid_elapsed_interval',result['integrity_errors'])
        json.dumps(result,allow_nan=False)

    def test_reason_cardinality_and_status_values_remain_bounded(self):
        ledger = self.ledger(event_limit=3)
        for i in range(100):
            health = summary(missing=True)
            health['checks']['lanes']['reason'] = str(i)+'x'*1000
            self.observe(ledger,(i+1)*.1,health)
        result = self.end(ledger,10.1)
        self.assertLessEqual(len(result['reason_counts']),64)
        self.assertTrue(all(len(key.encode())<=160 for key in result['reason_counts']))
        self.assertEqual(result['totals']['unknown'],100)
        self.assertEqual(len(result['recent_events']),3)


if __name__ == '__main__':
    unittest.main()
