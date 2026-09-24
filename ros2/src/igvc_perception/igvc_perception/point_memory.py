"""Observation-only point retention with distinct-frame confirmation."""
from collections import OrderedDict


class PointMemory:
    def __init__(self, ttl, capacity, candidate_ttl=3., confirmation_span=.4,
                 confirmation_frames=5):
        self.ttl = ttl
        self.capacity = capacity
        self.candidate_ttl = candidate_ttl
        self.confirmation_span = confirmation_span
        self.confirmation_frames = confirmation_frames
        self.records = OrderedDict()

    def clear(self):
        self.records.clear()

    def __len__(self):
        return len(self.records)

    def values(self):
        return ((record['point'], record['last']) for record in self.records.values())

    def expire(self, now):
        for key, record in list(self.records.items()):
            lifetime = self.ttl if record['confirmed'] else min(self.ttl, self.candidate_ttl)
            if now - record['last'] > lifetime:
                del self.records[key]

    def observe(self, keyed_points, stamp, now):
        """Deduplicate one acquisition before counting temporal evidence.

        Fresh candidates are exposed immediately. Only five distinct acquisition
        stamps spanning confirmation_span seconds earn the longer retention.
        """
        self.expire(now)
        for key, point in dict(keyed_points).items():
            record = self.records.get(key)
            if record is None:
                record = dict(point=point, first=now, last=now, stamp=stamp,
                              count=1, confirmed=False)
                self.records[key] = record
            elif stamp > record['stamp']:
                record.update(point=point, last=now, stamp=stamp, count=record['count']+1)
                record['confirmed'] |= (record['count'] >= self.confirmation_frames
                                        and now-record['first'] >= self.confirmation_span)
            else:
                continue  # Replayed frames do not refresh either evidence or expiry.
            self.records.move_to_end(key)
        while len(self.records) > self.capacity:
            self.records.popitem(last=False)
