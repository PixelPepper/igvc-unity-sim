import unittest
from igvc_perception.terrain_history import GroundHistory


class GroundHistoryTests(unittest.TestCase):
    def test_delayed_surface_uses_only_fresh_jointly_available_pair(self):
        h=GroundHistory()
        for stamp in (1_000_000_000,1_200_000_000):h.update(self.value(stamp),10)
        self.assertEqual(h.select(1_300_000_000,10.1,{1_000_000_000})[0],1_000_000_000)
        with self.assertRaises(ValueError):h.select(1_400_000_000,10.1,{1_000_000_000})
        with self.assertRaises(ValueError):h.select(1_300_000_000,10.1,set())

    def value(self,stamp):
        return dict(valid=True,stamp_ns=stamp,ground=dict(normal=[0,0,1],offset=0,
                    inlier_fraction=.9,rms_m=.01,slope_deg=0))

    def test_causal_join_ignores_future_and_chooses_newest_prior(self):
        h=GroundHistory()
        for stamp in (1_000_000_000,1_200_000_000,1_400_000_000):h.update(self.value(stamp),10)
        self.assertEqual(h.select(1_300_000_000,10.1)[0],1_200_000_000)
        with self.assertRaises(ValueError):h.select(900_000_000,10.1)

    def test_both_wall_freshness_and_acquisition_age_required(self):
        h=GroundHistory();h.update(self.value(1_000_000_000),10)
        with self.assertRaises(ValueError):h.select(1_100_000_000,10.51)
        with self.assertRaises(ValueError):h.select(1_350_000_001,10.1)
        self.assertEqual(h.select(1_350_000_000,10.5)[0],1_000_000_000)

    def test_invalid_fit_reset_and_time_reversal_clear_history(self):
        h=GroundHistory();h.update(self.value(1_000_000_000),10)
        h.update(dict(valid=False),10.1)
        with self.assertRaises(ValueError):h.select(1_100_000_000,10.2)
        h.update(self.value(1_000_000_000),11);h.update(self.value(100_000_000),11.1)
        self.assertNotIn(1_000_000_000,h.samples)
        h.clear();self.assertFalse(h.samples)

    def test_bad_confidence_and_bounded_cache(self):
        h=GroundHistory()
        for i in range(20):h.update(self.value(i+1),10)
        self.assertEqual(len(h.samples),8)
        v=self.value(100);v['ground']['rms_m']=float('nan')
        with self.assertRaises(ValueError):h.update(v,10)
        self.assertFalse(h.samples)


if __name__=='__main__':unittest.main()
