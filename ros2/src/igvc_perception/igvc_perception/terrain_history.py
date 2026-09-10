"""Bounded causal join between independently timed RGB and depth ground fits."""
from collections import OrderedDict
import math


class GroundHistory:
    def __init__(self):
        self.samples=OrderedDict()

    def clear(self):
        self.samples.clear()

    def update(self, status, now):
        if status.get('valid') is not True:
            self.clear()
            return
        stamp=status.get('stamp_ns');plane=status.get('ground')
        if not isinstance(stamp,int) or stamp<=0 or not isinstance(plane,dict):
            self.clear();raise ValueError('Invalid ground observation')
        fraction=float(plane.get('inlier_fraction',float('nan')))
        rms=float(plane.get('rms_m',float('nan')))
        slope=float(plane.get('slope_deg',float('nan')))
        if not all(map(math.isfinite,(fraction,rms,slope))) or not .6<=fraction<=1 or not 0<=rms<=.035 or not 0<=slope<=20:
            self.clear();raise ValueError('Ground confidence rejected')
        if self.samples and stamp<next(reversed(self.samples)):
            self.clear()
        self.samples[stamp]=(dict(plane),now)
        while len(self.samples)>8:self.samples.popitem(last=False)

    def select(self, rgb_stamp, now, available=None):
        # A later depth observation must not be projected backward into an RGB
        # exposure. The same world plane is assumed locally stationary for .35s.
        ready=[s for s,(_,arrival) in self.samples.items()
               if 0<=rgb_stamp-s<=350_000_000 and 0<=now-arrival<=.5
               and (available is None or s in available)]
        if not ready:raise ValueError('No fresh preceding depth ground estimate')
        stamp=max(ready)
        return stamp,self.samples[stamp][0]
