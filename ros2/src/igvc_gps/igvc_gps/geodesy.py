"""WGS84 ECEF/ENU conversion. Coordinates are degrees and metres."""
import math

A = 6378137.0
F = 1 / 298.257223563
E2 = F * (2 - F)


def ecef(latitude, longitude, altitude):
    if not all(math.isfinite(v) for v in (latitude, longitude, altitude)):
        raise ValueError('Coordinates must be finite')
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError('Latitude/longitude outside WGS84 range')
    p, l = math.radians(latitude), math.radians(longitude)
    n = A / math.sqrt(1 - E2 * math.sin(p)**2)
    return ((n + altitude) * math.cos(p) * math.cos(l),
            (n + altitude) * math.cos(p) * math.sin(l),
            (n * (1 - E2) + altitude) * math.sin(p))


def geodetic(x, y, z):
    hxy = math.hypot(x, y)
    if hxy < 1e-9:
        return (90. if z >= 0 else -90., 0., abs(z) - A * (1 - F))
    p = math.atan2(z, hxy * (1 - E2))
    for _ in range(15):
        n = A / math.sqrt(1 - E2 * math.sin(p)**2)
        new = math.atan2(z + E2 * n * math.sin(p), hxy)
        if abs(new - p) < 1e-14:
            p = new
            break
        p = new
    n = A / math.sqrt(1 - E2 * math.sin(p)**2)
    altitude = hxy * math.cos(p) + z * math.sin(p) - n * (1 - E2 * math.sin(p)**2)
    return math.degrees(p), math.degrees(math.atan2(y, x)), altitude


class LocalFrame:
    def __init__(self, origin):
        self.origin = dict(origin)
        self.xyz = ecef(origin['latitude'], origin['longitude'], origin['altitude'])
        p, l = math.radians(origin['latitude']), math.radians(origin['longitude'])
        self.rows = ((-math.sin(l), math.cos(l), 0.),
                     (-math.sin(p)*math.cos(l), -math.sin(p)*math.sin(l), math.cos(p)),
                     (math.cos(p)*math.cos(l), math.cos(p)*math.sin(l), math.sin(p)))

    def to_enu(self, latitude, longitude, altitude):
        delta = [a-b for a, b in zip(ecef(latitude, longitude, altitude), self.xyz)]
        return tuple(sum(a*b for a, b in zip(row, delta)) for row in self.rows)

    def to_geodetic(self, east, north, up=0.):
        if not all(math.isfinite(v) for v in (east, north, up)):
            raise ValueError('ENU must be finite')
        xyz = [self.xyz[i] + sum(self.rows[j][i]*v for j, v in enumerate((east, north, up))) for i in range(3)]
        return geodetic(*xyz)
