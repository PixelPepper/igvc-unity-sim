#!/usr/bin/env python3
"""T-0091 PROPOSED rule-dimensioned AutoNav reference course, revision r2 (geometry only, not Unity).

r1 (commit 6761c726) used deep arc meanders to reach 500 ft. Those were rejected as unlike the reference
image. r2 builds the course centreline from the traced reference image itself, so the curves stay SHALLOW and
reference-like:
- the midline of the traced outer and inner tapes;
- closed by a straight No Man's Land (NML) segment;
- smoothed with a fixed periodic Gaussian.
The midline is then fitted into a field box. Two clearly labelled variants are built and MEASURED:
  field-120x100 : the shape fitted into 120 ft east-west x 100 ft north-south (anisotropic fit, reported);
  rules-485     : the same silhouette scaled uniformly so the north->south mission run is ~485 ft and the closed
                  loop stays <= 520 ft; the larger footprint is a user-authorized, disclosed deviation.
  length-500ft  : (r2) the same silhouette scaled uniformly until the nominal lap is 500 ft; the required footprint
                  is reported. This is a deviation from the 120 x 100 ft field, never a silent exception.
Frame: metres, x east, y north, origin at the field's south-west corner. The loop is counter-clockwise from the
north start, heading north. Lane widths, drum sizes, tape and ramp are physical and are never scaled.

Measured, not assumed:
- the paired tape-edge lane width (nearest distance to each own edge, not the construction offset);
- the nominal centreline radius, and separately the inner tape-edge radius and folds;
- field bounds, lane-to-lane clearance and drum overlap;
- per-drum cross-section gaps (conservative, all drums jointly);
- a 5 ft-disc raster corridor and its ordered route witness. The witness length is a GRID ESTIMATE only, not a
  bound and not a gate, and the witness is not curvature-limited.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

FT = .3048
FIELD_W, FIELD_H = 120*FT, 100*FT
MARGIN = .25
TAPE = .1016
DRUM_D, DRUM_H = .597, 1.008
R_DRUM = DRUM_D/2
PASS = 5*FT
LANE_MIN, LANE_MAX = 10*FT, 20*FT
W_RIGHT, W_CORRIDOR, W_NML = LANE_MIN+.01, 4.4, 6.0   # right +1 cm so measured width clears 10 ft with no waiver
NS_TARGET, CLOSED_MAX = 484*FT, 520*FT
CLOSED_SELECT = 519*FT                            # selected variant keeps >= 1 ft margin under 520
START_END_GAP = 2.                                # physical ramp-end to start-line gap when repositioned
CLUSTER_PITCH = 3.6                               # min along-route spacing between side-switching cluster groups (m)
OSC_HALF = .5
# Shallow-shape limits relative to the fitted source trace (r2 measured +2 deg / 0.94x / 0.95 m on this family;
# r1-style hairpins measured ~83 deg swings and would fail every limit).
SHAPE_LIMITS = dict(max_tangent_extra_deg=5., excursion_ratio=1.25, silhouette_max_deviation_m=1.25)
RAMP_RISE, RAMP_RUN, RAMP_DECK, RAMP_SIDE = .30, 2.145, .4, .3
TARGET_LAP = 500*FT
LAP_RANGE = (480*FT, 520*FT)
DS = .02
GRID = .05
SMOOTH_SIGMA = 1.5                                # fixed periodic Gaussian (m); attempt-1 used 0.6 and folded at corners
TAPER = 3.                                        # width transitions (moving average, m)
FLANK = W_RIGHT/2+RAMP_SIDE+.05+R_DRUM
GAP_STEP = .01                                    # cross-section step; each measured gap is reduced by 2 steps
MARKER_44FT = 44*FT

# Traced reference controls (image px), copied from ReferenceMapBuild.cs (T-0089, trace sha b3ddd391...).
OUTER = ((142, 248), (147, 213), (162, 181), (190, 158), (230, 129), (271, 106), (316, 79), (349, 68), (384, 61), (414, 67),
         (451, 82), (493, 99), (537, 117), (578, 133), (614, 145), (644, 141), (680, 128), (724, 114), (772, 94), (822, 74),
         (864, 64), (901, 63), (937, 76), (967, 98), (987, 128), (1001, 163), (1005, 209), (1004, 305), (1003, 438), (1003, 503),
         (1004, 637), (1005, 711), (1006, 841), (1005, 986), (1003, 1040), (991, 1076), (973, 1101), (945, 1125), (916, 1140),
         (882, 1142), (846, 1131), (810, 1116), (769, 1101), (729, 1083), (689, 1063), (650, 1049), (611, 1042), (577, 1047),
         (539, 1060), (499, 1076), (459, 1092), (422, 1110), (386, 1130), (348, 1122), (311, 1100), (275, 1078), (239, 1054),
         (205, 1037), (175, 1012), (159, 989), (148, 957), (142, 925))
INNER = ((199, 248), (202, 228), (229, 216), (274, 199), (319, 181), (354, 173), (389, 170), (427, 177), (469, 190), (511, 203),
         (555, 216), (591, 229), (619, 232), (648, 226), (687, 211), (730, 196), (773, 180), (815, 165), (849, 150), (880, 137),
         (899, 137), (911, 154), (916, 180), (917, 241), (917, 327), (917, 439), (916, 503), (916, 637), (917, 711), (918, 848),
         (918, 986), (915, 1018), (902, 1042), (881, 1052), (849, 1047), (814, 1031), (774, 1014), (734, 995), (694, 975),
         (657, 957), (626, 946), (601, 946), (568, 955), (529, 970), (488, 983), (448, 998), (415, 1006), (383, 1010), (350, 1006),
         (314, 995), (279, 983), (242, 967), (217, 954), (202, 944), (200, 926))
RAMP_PY, NORTH_START_PY, SOUTH_START_PY = 570, 439, 711


def catmull(controls, step=2.):
    """Same open Catmull-Rom as ReferenceMapBuild.Curve (straight vertical runs kept straight), in pixels."""
    c = np.array(controls, float); n = len(c)

    def straight(i):
        return 0 <= i < n-1 and abs(c[i+1, 0]-c[i, 0]) <= 2 and abs(c[i+1, 1]-c[i, 1]) >= 60
    out = [c[0]]
    for i in range(n-1):
        p0, p1, p2, p3 = c[max(i-1, 0)], c[i], c[i+1], c[min(i+2, n-1)]
        if straight(i-1): p0 = p1-(p2-p1)
        if straight(i+1): p3 = p2+(p2-p1)
        steps = max(2, int(math.ceil(np.hypot(*(p2-p1))/step)))
        for k in range(1, steps+1):
            t = k/steps
            out.append(p1+(p2-p1)*t if straight(i) else
                       .5*(2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3))
    return np.array(out)


def resample(points, spacing, closed):
    pts = np.vstack([points, points[:1]]) if closed else points
    seg = np.hypot(*np.diff(pts, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(round(s[-1]/spacing)))
    t = np.linspace(0, s[-1], n, endpoint=not closed)
    return np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], 1)


def trace_midline():
    """Closed reference midline in pixels, counter-clockwise in the field (y up), with an NML flag."""
    from scipy.spatial import cKDTree
    outer, inner = resample(catmull(OUTER), 2., False), catmull(INNER)
    mid = (outer+inner[cKDTree(inner).query(outer)[1]])/2
    mid = mid[::-1]                                     # image order is clockwise in the field
    top, bottom = mid[-1], mid[0]
    nml = resample(np.array([top, bottom]), 2., False)[1:-1]
    pts = np.vstack([mid, nml])
    flag = np.concatenate([np.zeros(len(mid), bool), np.ones(len(nml), bool)])
    return pts, flag


def section_of(px, py, nml):
    if nml: return 'nml'
    if px >= 870 and py < 215: return 'corner-NE'
    if px >= 870 and py > 985: return 'corner-SE'
    if px >= 930: return 'right'
    if px < 230: return 'corner-NW' if py < 580 else 'corner-SW'
    return 'top' if py < 580 else 'bottom'


def allowances():
    return dict(left=MARGIN+2*R_DRUM+W_NML/2, right=MARGIN+FLANK+R_DRUM,
                top=MARGIN+TAPE+W_CORRIDOR/2, bottom=MARGIN+TAPE+W_CORRIDOR/2)


def fit(scale=1., iso=False, physical_starts=False):
    """Fit the reference midline into the field box (scale 1) or a uniformly enlarged box (scale > 1).
    iso=True keeps the source image aspect (one m/px scale); the footprint then follows from the shape."""
    pts_px, flag = trace_midline()
    a = allowances()
    lo, hi = pts_px.min(0), pts_px.max(0)
    sx = (FIELD_W-a['left']-a['right'])/(hi[0]-lo[0])*scale
    sy = (FIELD_H-a['top']-a['bottom'])/(hi[1]-lo[1])*scale
    if iso:
        sx = sy
    field = (a['left']+a['right']+(hi[0]-lo[0])*sx, a['top']+a['bottom']+(hi[1]-lo[1])*sy)

    def to_field(px, py):
        return np.stack([a['left']+(np.asarray(px)-lo[0])*sx, a['bottom']+(hi[1]-np.asarray(py))*sy], -1)

    def to_px(x, y):
        return lo[0]+(np.asarray(x)-a['left'])/sx, hi[1]-(np.asarray(y)-a['bottom'])/sy
    raw = to_field(pts_px[:, 0], pts_px[:, 1])
    dense = resample(raw, DS, True)
    sigma = int(round(SMOOTH_SIGMA/DS)); k = np.exp(-.5*(np.arange(-4*sigma, 4*sigma+1)/sigma)**2); k /= k.sum()
    pad = len(k)//2
    smooth = np.stack([np.convolve(np.r_[dense[-pad:, i], dense[:, i], dense[:pad, i]], k, 'valid') for i in (0, 1)], 1)
    p = resample(smooth, DS, True)
    pxy = np.stack(to_px(p[:, 0], p[:, 1]), 1)
    # NML flag: nearest raw sample's flag.
    from scipy.spatial import cKDTree
    nml = flag[cKDTree(raw).query(p)[1]]
    sec = np.array([section_of(px, py, f) for (px, py), f in zip(pxy, nml)])
    start = int(np.flatnonzero(sec == 'right')[np.argmin(p[sec == 'right', 1])])
    p, pxy, sec = (np.roll(v, -start, axis=0) for v in (p, pxy, sec))
    d = np.diff(np.vstack([p, p[:1]]), axis=0)
    h = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    seg = np.hypot(*d.T)
    dh = np.diff(np.r_[h, h[0]+2*np.pi])
    k_curv = dh/seg
    base = np.array([{'right': W_RIGHT, 'nml': W_NML}.get(s, W_CORRIDOR) for s in sec])
    win = int(round(TAPER/DS)); w = np.convolve(np.r_[base[-win:], base, base[:win]], np.ones(2*win+1)/(2*win+1), 'valid')
    s = np.concatenate([[0], np.cumsum(seg[:-1])])
    return dict(p=p, px=pxy, h=h, k=k_curv, w=w, sec=sec, s=s, length=float(seg.sum()), raw=raw,
                field=field, scale=scale, sx=sx, sy=sy, to_field=to_field, iso=iso, physical_starts=physical_starts)


def build(variant='field-120x100'):
    if variant == 'field-120x100':
        geo = fit(1.)
    elif variant == 'length-500ft':
        k = 1.
        for _ in range(3):                              # bounded: lap length is ~linear in the uniform scale
            k *= TARGET_LAP/fit(k)['length']
        geo = fit(k)
    elif variant == 'rules-485':
        # Selected variant (legacy name; r4 target 484 ft). ISOTROPIC source aspect. The exported mission runs north
        # start -> south start: scale uniformly (bounded, 3 steps) so that run is ~484 ft. If the image-scaled start
        # spacing would push the closed loop past CLOSED_SELECT, the start lines are repositioned to the physical
        # ramp ends +- START_END_GAP (disclosed in the report) and the scale is recalibrated (3 steps).
        def calibrate(physical):
            k = 1.
            for _ in range(3):
                g = fit(k, True, physical); k *= NS_TARGET/north_to_south(g)
            return fit(k, True, physical)
        geo = calibrate(False)
        if geo['length'] > CLOSED_SELECT:
            geo = calibrate(True)
        if geo['length'] > CLOSED_SELECT:
            geo = fit(geo['scale']*CLOSED_SELECT/geo['length'], True, True)
    else:
        raise ValueError(variant)
    ramp, starts = ramp_and_starts(geo)
    return geo, build_drums(geo, ramp), ramp, starts


def north_to_south(geo):
    _, starts = ramp_and_starts(geo)
    return float((geo['s'][starts['south']]-geo['s'][starts['north']]) % geo['length'])


def osculating_radius(p, half=OSC_HALF):
    """Local osculating-circle radius of the closed nominal centreline: circumradius of the samples +-half m apart."""
    m = max(1, int(round(half/DS)))
    a, b, c = np.roll(p, m, 0), p, np.roll(p, -m, 0)
    ab, bc, ca = (np.hypot(*(u-v).T) for u, v in ((a, b), (b, c), (c, a)))
    area2 = np.abs((b-a)[:, 0]*(c-a)[:, 1]-(b-a)[:, 1]*(c-a)[:, 0])
    return ab*bc*ca/np.maximum(2*area2, 1e-12)


def shape_check(geo):
    """Shallow-shape regression vs the fitted source trace (same scale). Limits are stated in SHAPE_LIMITS."""
    from scipy.spatial import cKDTree
    p, sec = geo['p'], geo['sec']
    raw_sec = sec[cKDTree(p).query(geo['raw'])[1]]

    def shape(points):
        d = np.diff(points, axis=0); ang = np.degrees(np.arctan2(np.abs(d[:, 1]), np.abs(d[:, 0])))
        dy = np.sign(np.round(d[:, 1], 4)); dy = dy[dy != 0]
        return dict(excursion_m=float(np.ptp(points[:, 1])), max_tangent_deg=float(ang.max()),
                    direction_reversals=int(np.sum(dy[1:] != dy[:-1])))
    out, issues = {}, []
    deviation = float(cKDTree(geo['raw']).query(p)[0].max())
    if deviation > SHAPE_LIMITS['silhouette_max_deviation_m']:
        issues.append(f'silhouette deviates {deviation:.2f} m from the source trace')
    for s in ('top', 'bottom'):
        src, prop = shape(geo['raw'][raw_sec == s][::10]), shape(p[sec == s][::25])
        out[s] = dict(source_trace=src, proposed=prop)
        if prop['direction_reversals'] != src['direction_reversals']:
            issues.append(f"{s} connector reversals {prop['direction_reversals']} != source {src['direction_reversals']}")
        if prop['max_tangent_deg'] > src['max_tangent_deg']+SHAPE_LIMITS['max_tangent_extra_deg']:
            issues.append(f"{s} connector tangent {prop['max_tangent_deg']:.1f} deg exceeds source+{SHAPE_LIMITS['max_tangent_extra_deg']}")
        if prop['excursion_m'] > src['excursion_m']*SHAPE_LIMITS['excursion_ratio']:
            issues.append(f"{s} connector excursion {prop['excursion_m']:.2f} m exceeds {SHAPE_LIMITS['excursion_ratio']}x source")
    return dict(silhouette_max_deviation_m=deviation, connector_shape=out, limits=SHAPE_LIMITS, issues=issues)


def nearest_in(geo, section, key):
    idx = np.flatnonzero(geo['sec'] == section)
    return int(idx[np.argmin(np.abs(key(geo['px'][idx])))])


def ramp_and_starts(geo):
    def at(py):
        return nearest_in(geo, 'right', lambda q: q[:, 1]-py)
    i = at(RAMP_PY); x, y = geo['p'][i]; half = RAMP_RUN+RAMP_DECK/2
    ramp = dict(x0=x-W_RIGHT/2-RAMP_SIDE, x1=x+W_RIGHT/2+RAMP_SIDE, y0=y-half, y1=y+half,
                rise=RAMP_RISE, run=RAMP_RUN, deck=RAMP_DECK, grade=RAMP_RISE/RAMP_RUN)
    north, south = at(NORTH_START_PY), at(SOUTH_START_PY)
    if geo.get('physical_starts'):
        idx = np.flatnonzero(geo['sec'] == 'right')
        north = int(idx[np.argmin(np.abs(geo['p'][idx, 1]-(ramp['y1']+START_END_GAP)))])
        south = int(idx[np.argmin(np.abs(geo['p'][idx, 1]-(ramp['y0']-START_END_GAP)))])
    return ramp, dict(north=north, south=south)


def frame(geo, i):
    h = geo['h'][i]
    return geo['p'][i], np.array([math.cos(h), math.sin(h)]), np.array([-math.sin(h), math.cos(h)]), geo['w'][i], i


def frac_index(geo, section, fraction):
    idx = np.flatnonzero(geo['sec'] == section)
    return int(idx[min(len(idx)-1, int(round(fraction*(len(idx)-1))))])


# Drum layout. Intended class is fixed BEFORE measurement. Top/bottom stations are the diagram's x positions;
# NML interior obstacles keep diagram order, evenly spaced (r1 measured chokes at diagram spacing); all 95 present (r6
# restored the two end singles near the NML ends).
PLUS = ((0, 0), (.72, 0), (-.72, 0), (0, .72), (0, -.72))
TRIANGLE = ((-.36, -.31), (.36, -.31), (0, .31))
ROW_ACROSS = ((0, -.72), (0, 0), (0, .72))
TOP = [(813, 'side', 'outer', 1), (799, 'side', 'inner', 1), (681, 'centre', None, 1), (625, 'centre', None, 1),
       (566, 'centre', None, 1), (518, 'side', 'outer', 1), (496, 'side', 'inner', 1), (447, 'side', 'outer', PLUS),
       (389, 'side', 'inner', PLUS), (334, 'side', 'outer', PLUS), (274, 'centre', None, 1)]
BOTTOM = [(248, 'centre', None, 1), (313, 'side', 'outer', TRIANGLE), (383, 'side', 'inner', PLUS), (441, 'side', 'outer', TRIANGLE),
          (503, 'side', 'inner', 1), (515, 'side', 'outer', 1), (578, 'centre', None, 1), (617, 'centre', None, 1),
          (660, 'centre', None, 1), (802, 'side', 'inner', 1), (820, 'side', 'outer', 1)]
NML_WEST = [(272, 'Red'), (332, 'Green'), (401, 'Black'), (471, 'Yellow'), (525, 'Red'), (584, 'Green'), (646, 'Black'),
            (698, 'Yellow'), (747, 'Red'), (812, 'Green'), (866, 'Black'), (930, 'Yellow')]
NML_EAST = [(265, 'Yellow'), (311, 'Black'), (363, 'Green'), (421, 'Red'), (472, 'Yellow'), (532, 'Black'), (594, 'Green'),
            (656, 'Red'), (715, 'Yellow'), (775, 'Black'), (837, 'Green'), (889, 'Red')]
NML_INNER = [(357, 'side', 'outer', 1), (362, 'side', 'inner', 1), (406, 'centre', None, 1), (504, 'centre', None, ROW_ACROSS),
             (585, 'centre', None, ROW_ACROSS), (675, 'centre', None, ROW_ACROSS), (727, 'centre', None, 1),
             (786, 'side', 'outer', 1), (788, 'side', 'inner', 1),
             (311, 'centre', None, 1), (861, 'centre', None, 1)]   # r6: restored (ids nml09/nml10; earlier ids kept)
NML_OMITTED = ()
NML_STATIONS = (357, 406, 504, 585, 675, 727, 786)
# r6: the restored singles sit 0.35 of a station gap from each NML end (0.5 = midway passed only the 5 cm raster;
# the conservative 10 cm raster closed there), so the other 93
# drums keep their r4 stations exactly.
NML_END_SINGLES = {311: .35/(len(NML_STATIONS)+1), 861: 1-.35/(len(NML_STATIONS)+1)}


EXPECTED_COLOURS = {'Yellow': 77, 'Red': 6, 'Green': 6, 'Black': 6}   # all 95 reference markers


def expected_groups():
    """Every reference marker's group identity (95 drums incl. cluster members); counts alone are not enough."""
    groups = {}
    for name, table in (('top', TOP), ('bottom', BOTTOM)):
        for n, (_, _, _, pattern) in enumerate(table):
            groups[f'{name}{n:02d}'] = 1 if pattern == 1 else len(pattern)
    for n, (_, _, _, pattern) in enumerate(NML_INNER):
        groups[f'nml{n:02d}'] = 1 if pattern == 1 else len(pattern)
    for side, column in (('outer', NML_WEST), ('inner', NML_EAST)):
        for n, _ in enumerate(column):
            groups[f'col-{side}{n:02d}'] = 1
    for tag in ('gate-top-o', 'gate-top-i', 'gate-bot-o', 'gate-bot-i', 'corner-ne-o', 'corner-ne-i', 'corner-se-i', 'corner-se-o'):
        groups[tag] = 1
    for tag in ('flank-n', 'flank-s'):
        for side in ('inner', 'outer'):
            groups[f'{tag}-{side}'] = 1
    return groups


def inventory_issues(drums):
    issues = []
    # Ramp-flank drums carry their group name as id; every other group numbers its members -0, -1, ...
    want = {g if g.startswith('flank-') else f'{g}-{j}' for g, n in expected_groups().items() for j in range(n)}
    have = [d['id'] for d in drums]
    if len(have) != len(set(have)): issues.append('duplicate drum ids')
    if set(have) != want:
        issues.append(f'drum identities differ: missing {sorted(want-set(have))[:6]} extra {sorted(set(have)-want)[:6]}')
    colours = {c: sum(d['colour'] == c for d in drums) for c in EXPECTED_COLOURS}
    if colours != EXPECTED_COLOURS or len(drums) != sum(EXPECTED_COLOURS.values()):
        issues.append(f'drum inventory {len(drums)} {colours} != 95 {EXPECTED_COLOURS}')
    return issues


def nml_t(py):
    return min(1., max(0., (py-248)/678))


def nml_station_t(py):
    if py in NML_END_SINGLES:
        return NML_END_SINGLES[py]
    return (NML_STATIONS.index({362: 357, 788: 786}.get(py, py))+1)/(len(NML_STATIONS)+1)


def star_ts():
    rows = [nml_station_t(py) for py, *_r in NML_INNER if _r[2] == ROW_ACROSS]
    return (nml_t(250), (rows[0]+rows[1])/2, (rows[1]+rows[2])/2, nml_t(928))


def hull_half(pattern):
    return R_DRUM if pattern == 1 else max(abs(a) for _, a in pattern)+R_DRUM


def build_drums(geo, ramp):
    drums = []

    def put(i, kind, side, colour, group, pattern, lateral, passage=None):
        p, tan, nrm, w, _ = frame(geo, i)
        base = lateral(w, pattern)
        for j, (along, across) in enumerate([(0, 0)] if pattern == 1 else pattern):
            c = p+tan*along+nrm*(base+across)
            drums.append(dict(id=f'{group}-{j}', group=group, colour=colour, intended=kind, side=side, passage=passage,
                              x=round(float(c[0]), 4), y=round(float(c[1]), 4)))

    def in_lane(side):
        def fn(w, pattern):
            if side is None: return 0.
            reach = w/2-.1-hull_half(pattern)
            return reach if side == 'inner' else -reach
        return fn
    for name, table in (('top', TOP), ('bottom', BOTTOM)):
        # Diagram x stations; r4 enforces CLUSTER_PITCH along the route between consecutive groups that switch
        # sides when either is a cluster (isotropic scale compressed them into a 5 ft choke). Shifts are recorded.
        idx = np.flatnonzero(geo['sec'] == name)
        prev = None
        for n, (x, kind, side, pattern) in enumerate(table):
            i = nearest_in(geo, name, lambda q, x=x: q[:, 0]-x)
            if prev is not None and (pattern != 1 or prev[1] != 1) and side != prev[2]:
                want = prev[0]+CLUSTER_PITCH
                if geo['s'][i] < want:
                    i = int(idx[np.argmin(np.abs(geo['s'][idx]-want))])
            shift = float(geo['s'][i]-geo['s'][nearest_in(geo, name, lambda q, x=x: q[:, 0]-x)])
            first = len(drums)
            put(i, kind, side, 'Yellow', f'{name}{n:02d}', pattern, in_lane(side),
                None if kind == 'centre' else ('inner' if side == 'outer' else 'outer'))
            for d in drums[first:]:
                d['station_shift_m'] = round(shift, 3)
            prev = (geo['s'][i], pattern, side)
    for n, (py, kind, side, pattern) in enumerate(NML_INNER):
        put(frac_index(geo, 'nml', nml_station_t(py)), kind, side, 'Yellow', f'nml{n:02d}', pattern,
            lambda w, _p, s=side: 0. if s is None else (1 if s == 'inner' else -1)*(R_DRUM+PASS/2+.15),
            None if kind == 'centre' else 'middle')
    for side, column in (('outer', NML_WEST), ('inner', NML_EAST)):
        sign = 1 if side == 'inner' else -1
        for n, (py, colour) in enumerate(column):
            put(frac_index(geo, 'nml', nml_t(py)), 'boundary', side, colour, f'col-{side}{n:02d}', 1,
                lambda w, _p, s=sign: s*(w/2+R_DRUM))
    for section, t, side, tag in (('corner-NW', .85, 'outer', 'gate-top-o'), ('corner-NW', .5, 'inner', 'gate-top-i'),
                                  ('corner-SW', .15, 'outer', 'gate-bot-o'), ('corner-SW', .5, 'inner', 'gate-bot-i')):
        sign = 1 if side == 'inner' else -1
        put(frac_index(geo, section, t), 'boundary', side, 'Yellow', tag, 1, lambda w, _p, s=sign: s*(w/2+TAPE+R_DRUM+.02))
    for section, t, side, tag in (('corner-NE', .15, 'outer', 'corner-ne-o'), ('corner-NE', .85, 'inner', 'corner-ne-i'),
                                  ('corner-SE', .15, 'inner', 'corner-se-i'), ('corner-SE', .85, 'outer', 'corner-se-o')):
        put(frac_index(geo, section, t), 'side', side, 'Yellow', tag, 1, in_lane(side), 'inner' if side == 'outer' else 'outer')
    xc = (ramp['x0']+ramp['x1'])/2
    for y, tag in ((ramp['y1']+.4, 'flank-n'), (ramp['y0']-.4, 'flank-s')):
        for sign, side in ((1, 'inner'), (-1, 'outer')):
            drums.append(dict(id=f'{tag}-{side}', group=f'{tag}-{side}', colour='Yellow', intended='flank', side=side,
                              passage=None, x=round(xc-sign*FLANK, 4), y=round(y, 4)))
    return drums


# ---------------------------------------------------------------- measurement
def offset(geo, d, idx=None):
    h = geo['h'] if idx is None else geo['h'][idx]
    p = geo['p'] if idx is None else geo['p'][idx]
    return p+np.stack([-np.sin(h), np.cos(h)], 1)*np.asarray(d)[:, None]


def metadata(geo, starts):
    """Spawn and the six broad goals only (field frame + odom transform); no course geometry."""
    ns = geo['p'][starts['north']]
    goals = [('top-right gate', geo['p'][frac_index(geo, 'corner-NE', .5)], 3.)]
    goals += [(f'waypoint star {n+1}', geo['p'][frac_index(geo, 'nml', t)], 2.) for n, t in enumerate(star_ts())]
    goals.append(('south start/finish', geo['p'][starts['south']], 2.))
    return dict(frame='field metres, x east, y north, origin field SW corner',
                spawn=dict(field_xy=[round(float(ns[0]), 4), round(float(ns[1]), 4)], heading='north'),
                odom_from_field='odom_x = y - spawn_y ; odom_y = spawn_x - x (spawn heading north)',
                goals=[dict(name=n, field_xy=[round(float(q[0]), 4), round(float(q[1]), 4)], radius_m=r) for n, q, r in goals])


def measure(geo, drums, ramp, starts, grid=GRID, meta=None):
    from scipy.spatial import cKDTree
    from scipy import ndimage
    p, w, k, sec = geo['p'], geo['w'], geo['k'], geo['sec']
    n = len(p); taped = sec != 'nml'; fw, fh = geo['field']
    rep = dict(sampling=dict(centreline_m=DS, raster_m=grid, cross_section_m=GAP_STEP, smoothing_sigma_m=SMOOTH_SIGMA))
    rep['lap_length_m'] = geo['length']; rep['lap_length_ft'] = geo['length']/FT
    rep['lap_definition'] = 'nominal closed centreline (measuring convention; it passes through centred drums)'
    rep['field_ft'] = [fw/FT, fh/FT]; rep['uniform_scale_vs_field_fit'] = geo['scale']
    rep['fit_scale_m_per_px'] = dict(x=geo['sx'], y=geo['sy'], anisotropy=geo['sx']/geo['sy'])
    rep['section_lengths_m'] = {s: float(np.sum(np.r_[np.diff(geo['s']), geo['length']-geo['s'][-1]][sec == s]))
                                for s in dict.fromkeys(sec)}
    # Start-to-finish (north start, counter-clockwise, to the south start) vs the closed loop.
    rep['north_to_south_start_m'] = float((geo['s'][starts['south']]-geo['s'][starts['north']]) % geo['length'])
    rep['north_to_south_start_ft'] = rep['north_to_south_start_m']/FT
    rep['closed_margin_to_520_ft'] = (CLOSED_MAX-geo['length'])/FT
    rep['fit_isotropic'] = bool(geo.get('iso'))
    rep['start_lines'] = ('repositioned to the physical ramp ends +- %.1f m (image pixel spacing would exceed the closed-loop limit)' % START_END_GAP) if geo.get('physical_starts') else 'image pixel stations (py 439 / 711)'
    rep['lap_definitions'] = dict(closed_loop='closed nominal centreline, includes the ramp stretch between the starts',
                                  north_to_south='nominal centreline from the north start counter-clockwise to the south start '
                                                 '(the exported mission run)')
    # Silhouette and shallow-shape regression vs the source trace.
    shp = shape_check(geo)
    rep['silhouette_max_deviation_m'] = shp['silhouette_max_deviation_m']
    rep['connector_shape'] = shp['connector_shape']; rep['shape_limits'] = shp['limits']
    # Width: nearest distance from each centreline sample to its OWN left and right inner-edge polylines.
    left, right = offset(geo, w/2), offset(geo, -w/2)
    lt, rt = cKDTree(left[taped]), cKDTree(right[taped])
    width = lt.query(p[taped])[0]+rt.query(p[taped])[0]
    rep['usable_width_taped_m'] = dict(min=float(width.min()), max=float(width.max()), resolution_m=DS,
                                       method='centreline-to-own-edge nearest distances, summed (not the construction offset)')
    rep['usable_width_nml_m'] = dict(value=W_NML, note='authoring assumption: between coloured drum-column inner edges')
    # Curvature.
    radius = osculating_radius(p)
    inner = radius-w/2
    rep['radius'] = dict(interpretation='II.2 turning radius >= 5 ft applied to the local osculating-circle radius of the '
                                        f'nominal centreline (three-point circumradius, samples +-{OSC_HALF} m apart); '
                                        'inner tape-edge radius = nominal - half width, reported separately; driven-route '
                                        'curvature is unverified',
                         nominal_min_m=float(radius.min()), inner_edge_min_m=float(inner.min()),
                         inner_edge_below_5ft_fraction=float(np.mean(inner < PASS)), fold=bool(inner.min() <= 0))
    # Field bounds.
    outer = np.concatenate([offset(geo, w/2+TAPE)[taped], offset(geo, -w/2-TAPE)[taped]])
    dxy = np.array([[d['x'], d['y']] for d in drums])
    xs = np.concatenate([outer[:, 0], dxy[:, 0]-R_DRUM, dxy[:, 0]+R_DRUM, [ramp['x0'], ramp['x1']]])
    ys = np.concatenate([outer[:, 1], dxy[:, 1]-R_DRUM, dxy[:, 1]+R_DRUM, [ramp['y0'], ramp['y1']]])
    rep['extent_m'] = dict(x=[float(xs.min()), float(xs.max())], y=[float(ys.min()), float(ys.max())], field=[fw, fh])
    rep['inside_field'] = bool(xs.min() >= 0 and ys.min() >= 0 and xs.max() <= fw and ys.max() <= fh)
    # Lane-to-lane clearance between non-local parts of the loop.
    edge = w/2+np.where(taped, TAPE, 2*R_DRUM)
    tree = cKDTree(p)
    sub = np.arange(0, n, 10)                           # 0.2 m subsample bounds the pair set
    pairs = sub[np.array(sorted(cKDTree(p[sub]).query_pairs(edge.max()*2+1.)))]
    ds = np.abs(geo['s'][pairs[:, 0]]-geo['s'][pairs[:, 1]]); ds = np.minimum(ds, geo['length']-ds)
    need = edge[pairs[:, 0]]+edge[pairs[:, 1]]
    far = ds > math.pi/2*need
    dist = np.hypot(*(p[pairs[:, 0]]-p[pairs[:, 1]]).T)
    rep['min_lane_to_lane_clearance_m'] = float((dist-need)[far].min()) if far.any() else None
    dtree = cKDTree(dxy)
    rep['min_drum_edge_gap_m'] = float(dtree.query(dxy, 2)[0][:, 1].min()-DRUM_D)
    # Per-drum cross-sections (all drums jointly), intended class checked against conservative measured gaps.
    checks, failures = [], []
    for d in drums:
        c = np.array([d['x'], d['y']]); i = tree.query(c)[1]
        _, _, nrm, wi, _ = frame(geo, i)
        lat = float(np.dot(c-p[i], nrm))
        if d['intended'] in ('boundary', 'flank'):
            ok = abs(lat)-R_DRUM >= wi/2-1e-3
            checks.append(dict(id=d['id'], intended=d['intended'], outside_usable=ok))
            if not ok: failures.append(f"{d['id']}: {d['intended']} drum intrudes into the usable width")
            continue
        t = np.arange(-wi/2, wi/2+1e-9, GAP_STEP)
        line = p[i]+np.outer(t, nrm)
        blocked = np.zeros(len(t), bool)
        for j in dtree.query_ball_point(p[i], wi/2+R_DRUM+.01):
            blocked |= np.hypot(*(line-dxy[j]).T) <= R_DRUM
        runs, cur = [], None
        for m, b in enumerate(blocked):
            if b and cur is None: cur = [t[m], t[m]]
            elif b: cur[1] = t[m]
            elif cur is not None: runs.append(cur); cur = None
        if cur is not None: runs.append(cur)
        merged = []
        for r in runs:
            if merged and r[0]-merged[-1][1] < PASS: merged[-1][1] = r[1]
            else: merged.append(list(r))
        own = next((m for m in merged if m[0]-GAP_STEP <= lat <= m[1]+GAP_STEP), None)
        if own is None:
            failures.append(f"{d['id']}: cross-section misses the drum"); continue
        q = merged.index(own)
        outer_gap = own[0]-(merged[q-1][1] if q else -wi/2)-2*GAP_STEP
        inner_gap = (merged[q+1][0] if q+1 < len(merged) else wi/2)-own[1]-2*GAP_STEP
        if d['intended'] == 'centre': ok = min(inner_gap, outer_gap) >= PASS
        elif d['passage'] == 'inner': ok = inner_gap >= PASS
        elif d['passage'] == 'outer': ok = outer_gap >= PASS
        else: ok = (inner_gap if d['side'] == 'outer' else outer_gap) >= PASS
        checks.append(dict(id=d['id'], intended=d['intended'], passage=d['passage'], side=d['side'], inner_gap=round(float(inner_gap), 4),
                           outer_gap=round(float(outer_gap), 4), ok=ok))
        if not ok: failures.append(f"{d['id']}: intended {d['intended']}/{d['passage']} gaps inner {inner_gap:.3f} outer {outer_gap:.3f}")
    rep['drum_checks'] = checks
    rep['drum_intended_passage_min_m'] = float(min(
        min(c['inner_gap'], c['outer_gap']) if c['intended'] == 'centre' else
        (c['inner_gap'] if c['passage'] == 'inner' else c['outer_gap'] if c['passage'] == 'outer' else (c['inner_gap'] if c['side'] == 'outer' else c['outer_gap']))
        for c in checks if 'inner_gap' in c))
    # Raster 5 ft corridor and ordered route witness (grid estimate).
    nx, ny = int(math.ceil(fw/grid)), int(math.ceil(fh/grid))
    gx, gy = np.meshgrid((np.arange(nx)+.5)*grid, (np.arange(ny)+.5)*grid)
    cells = np.stack([gx.ravel(), gy.ravel()], 1)
    dist_c, near_c = tree.query(cells)
    slack = grid*math.sqrt(2)/2
    free = (dist_c <= w[near_c]/2-PASS/2-slack) & (dtree.query(cells)[0] >= R_DRUM+PASS/2+slack)
    free = free.reshape(ny, nx)
    ns = starts['north']; pn, tn, nn, wn, _ = frame(geo, ns)
    rel = cells-pn
    cut = ((np.abs(rel@tn) < grid) & (np.abs(rel@nn) < wn/2+.5)).reshape(ny, nx)
    free_cut = free & ~cut
    labels, _ = ndimage.label(free_cut)

    def cell(q):
        return int(q[1]/grid), int(q[0]/grid)
    a_, b_ = cell(pn+tn*.4), cell(pn-tn*.4)
    rep['corridor_loop_connected'] = bool(labels[a_] and labels[a_] == labels[b_])
    meta = meta or metadata(geo, starts)
    rep['witness'] = witness(free_cut, a_, b_, meta, gx, gy, grid)
    # 44 ft marker along the route from the north start (may follow the curve).
    sm = (geo['s'][ns]+MARKER_44FT) % geo['length']
    mi = int(np.searchsorted(geo['s'], sm)) % n
    rep['marker_44ft'] = dict(field_xy=[float(p[mi, 0]), float(p[mi, 1])], section=str(sec[mi]))
    rep['ramp'] = dict(grade=ramp['grade'], y=[ramp['y0'], ramp['y1']])
    rep['start_lines_y'] = dict(north=float(p[starts['north'], 1]), south=float(p[starts['south'], 1]))
    rep['ramp_between_starts_with_clearance'] = bool(p[starts['south'], 1]+.3 < ramp['y0'] and ramp['y1'] < p[starts['north'], 1]-.3)
    issues = list(failures)
    lo, hi = rep['usable_width_taped_m']['min'], rep['usable_width_taped_m']['max']
    if lo < LANE_MIN or hi > LANE_MAX: issues.append(f'taped lane width {lo:.4f}-{hi:.4f} m outside 10-20 ft (no tolerance)')
    if not LANE_MIN <= W_NML <= LANE_MAX: issues.append('NML width outside 10-20 ft')
    if rep['radius']['nominal_min_m'] < PASS: issues.append(f"nominal radius {rep['radius']['nominal_min_m']:.3f} m < 5 ft")
    if rep['radius']['fold']: issues.append('tape inner edge folds (radius <= half width)')
    if not rep['inside_field']: issues.append('geometry outside the stated field')
    if rep['min_lane_to_lane_clearance_m'] is not None and rep['min_lane_to_lane_clearance_m'] <= 0: issues.append('lanes overlap')
    if rep['min_drum_edge_gap_m'] < 0: issues.append('drums overlap')
    if not rep['corridor_loop_connected']: issues.append('5 ft corridor does not close the lap')
    wit = rep['witness']
    if not wit['found']: issues.append('no ordered collision-free 5 ft route witness on the raster')
    elif not wit['goals_in_order']: issues.append('route witness misses a goal region or its order')
    issues += shp['issues']
    ns_ft = rep['north_to_south_start_ft']
    if not LAP_RANGE[0] <= rep['north_to_south_start_m'] <= LAP_RANGE[1]: issues.append(f'north-to-south nominal run {ns_ft:.1f} ft outside 480-520 ft')
    if not LAP_RANGE[0] <= geo['length'] <= CLOSED_MAX+1e-9: issues.append(f"closed nominal loop {rep['lap_length_ft']:.1f} ft outside 480-520 ft")
    deviations = []
    if abs(fw-FIELD_W) > 1e-6 or abs(fh-FIELD_H) > 1e-6:
        deviations.append(f'footprint {fw/FT:.1f} x {fh/FT:.1f} ft differs from the II.2 120 x 100 ft area (user-authorized larger footprint)')
    rep['authorized_deviations'] = deviations
    if ramp['grade'] > .15: issues.append('ramp grade > 15%')
    if not rep['ramp_between_starts_with_clearance']: issues.append('ramp does not fit between the start lines')
    rep['drum_count'] = len(drums)
    rep['drum_colours'] = {c: sum(d['colour'] == c for d in drums) for c in ('Yellow', 'Red', 'Green', 'Black')}
    rep['drums_omitted'] = [dict(diagram_py=py, colour='Yellow', region='NML interior centre single') for py in NML_OMITTED]
    issues += inventory_issues(drums)
    rep['issues'] = issues
    rep['reported_not_gated'] = ['witness length is an 8-connected inflated-raster grid estimate, not a bound',
                                 'witness is not curvature-limited', 'inner tape-edge radius below 5 ft is reported only',
                                 '44 ft marker may lie on a curve']
    rep['unverified'] = ['Unity integration/rendering', 'sensors', 'navigation', 'judged timing', 'ramp physics']
    rep['authorized_geometry_met'] = not issues
    rep['full_rule_compliance'] = False if (issues or deviations) else 'not claimed: judged timing and Unity unverified'
    rep['measured_constraints_met'] = rep['authorized_geometry_met']
    return rep


def witness(free, src, dst, meta, gx, gy, grid):
    """8-connected Dijkstra on free cells (diagonals only with both orthogonal neighbours free)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    ny, nx = free.shape
    ids = -np.ones(free.shape, int); ids[free] = np.arange(free.sum())
    rows, cols, cost = [], [], []
    for dy, dx, c in ((0, 1, 1.), (1, 0, 1.), (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2))):
        a = free[max(0, -dy):ny-max(0, dy), max(0, -dx):nx-max(0, dx)]
        ys, xs = np.nonzero(a); ys = ys+max(0, -dy); xs = xs+max(0, -dx)
        ok = free[ys+dy, xs+dx]
        if dx and dy: ok &= free[ys+dy, xs] & free[ys, xs+dx]
        rows.append(ids[ys[ok], xs[ok]]); cols.append(ids[ys[ok]+dy, xs[ok]+dx]); cost.append(np.full(ok.sum(), c*grid))
    rows, cols, cost = map(np.concatenate, (rows, cols, cost))
    m = int(free.sum()); s, t = ids[src], ids[dst]
    if s < 0 or t < 0:
        return dict(found=False, goals_in_order=False, goal_hits=[], reason='start or end cell not free')
    dist, pred = dijkstra(coo_matrix((cost, (rows, cols)), shape=(m, m)).tocsr(), directed=False, indices=s,
                          return_predecessors=True)
    if not math.isfinite(dist[t]):
        return dict(found=False, goals_in_order=False, goal_hits=[], reason='no path')
    flat = np.flatnonzero(free.ravel()); path, v = [], t
    while v != s and v >= 0: path.append(flat[v]); v = pred[v]
    path.append(flat[s]); path.reverse()
    pts = np.stack([gx.ravel()[path], gy.ravel()[path]], 1)
    hits, last = [], -1
    for g in meta['goals']:
        inside = np.flatnonzero(np.hypot(*(pts-np.array(g['field_xy'])).T) <= g['radius_m'])
        later = inside[inside > last]
        hits.append(dict(name=g['name'], visited=bool(len(later))))
        if len(later): last = later[0]
    # Indicative witness curvature: circumradius of points 1 m apart along the path (not a constraint).
    sp = resample(pts, .5, False); a, b, c = sp[:-4], sp[2:-2], sp[4:]
    ab, bc, ca = (np.hypot(*(u-v).T) for u, v in ((a, b), (b, c), (c, a)))
    area2 = np.abs((b-a)[:, 0]*(c-a)[:, 1]-(b-a)[:, 1]*(c-a)[:, 0])
    rad = ab*bc*ca/np.maximum(2*area2, 1e-12)
    return dict(found=True, length_m=float(dist[t]), length_ft=float(dist[t])/FT, goals_in_order=all(h['visited'] for h in hits),
                goal_hits=hits, indicative_min_radius_m=float(rad.min()),
                note='grid estimate on an inflated 8-connected raster; not a bound, not a gate, not curvature-limited')


def geometry_doc(variant, geo, drums, ramp, starts):
    taped = geo['sec'] != 'nml'; step = 5

    def poly(arr):
        return [[round(float(a), 4), round(float(b), 4)] for a, b in arr[::step]]
    runs, cur = [], []
    for i in range(len(taped)):
        if taped[i]: cur.append(i)
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    tapes = [dict(side=name, width_m=TAPE, centre=poly(offset(geo, sign*(geo['w'][r]/2+TAPE/2), np.array(r))))
             for r in runs for sign, name in ((1, 'inner'), (-1, 'outer'))]
    return dict(status='PROPOSED - not Unity, not rule-certified', variant=variant, units='m',
                frame='x east, y north, origin field SW corner', field=list(geo['field']),
                centreline=poly(geo['p']), widths=[round(float(v), 4) for v in geo['w'][::step]], tapes=tapes, drums=drums,
                drum=dict(diameter_m=DRUM_D, height_m=DRUM_H), ramp=ramp,
                start_lines={k: [round(float(c), 4) for c in geo['p'][i]] for k, i in starts.items()},
                waypoint_stars=[[round(float(c), 4) for c in geo['p'][frac_index(geo, 'nml', t)]] for t in star_ts()],
                interpretations=['centreline = smoothed midline of the traced reference tapes, NML closed by a straight',
                                 'black diagram circles are black drums, not potholes', 'optional 2 ft potholes omitted',
                                 'NML boundaries are the coloured drum columns; no tape across NML',
                                 'all 95 reference drums present; NML interior obstacles evenly spaced in diagram order; the two '
                                 'NML centre singles (diagram py 311/861) sit 0.35 of a station gap from each NML end'])


def unity_input(variant, geo, drums, ramp, starts):
    """JsonUtility-friendly AUTHORING input for the Unity adapter (point objects, flat records). Render/build
    only: it is never player data or policy input. Field frame metres (x east, y north)."""
    taped = geo['sec'] != 'nml'
    runs, cur = [], []
    for i in range(len(taped)):
        if taped[i]: cur.append(i)
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == len(taped)-1:
        runs = [runs[-1]+runs[0]]+runs[1:-1]           # the closed loop wraps inside the taped run: one continuous tape
    tapes = []
    for r in runs:
        idx = np.array(r)[::5]
        for sign, name in ((1, 'inner'), (-1, 'outer')):
            pts = offset(geo, sign*(geo['w'][idx]/2+TAPE/2), idx)
            tapes.append(dict(side=name, width=TAPE, points=[dict(x=round(float(a), 4), y=round(float(b), 4)) for a, b in pts]))

    def line(name):
        q, tan, _, w, _ = frame(geo, starts[name])
        return dict(name=name, x=round(float(q[0]), 4), y=round(float(q[1]), 4), hx=round(float(tan[0]), 6),
                    hy=round(float(tan[1]), 6), width=round(float(w), 4))
    north = line('north')
    return dict(task='T-0091', variant=variant, status='PROPOSED authoring input, not certified',
                frame='field metres, x east, y north, origin field SW corner',
                fieldW=round(float(geo['field'][0]), 4), fieldH=round(float(geo['field'][1]), 4),
                spawn=dict(x=north['x'], y=north['y']),
                spawnHeadingOffNorthDeg=round(math.degrees(math.atan2(north['hx'], north['hy'])), 4),
                tapeWidth=TAPE, drumDiameter=DRUM_D, drumHeight=DRUM_H,
                tapes=tapes, drums=[dict(id=d['id'], colour=d['colour'], x=d['x'], y=d['y']) for d in drums],
                ramp=dict(x0=ramp['x0'], x1=ramp['x1'], y0=ramp['y0'], y1=ramp['y1'], rise=ramp['rise'],
                          run=ramp['run'], deck=ramp['deck']),
                startLines=[north, line('south')])


def render(variant, geo, drums, ramp, starts, rep, out, reference=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    fw, fh = geo['field']
    cols = 2 if reference and Path(reference).exists() else 1
    fig, axes = plt.subplots(1, cols, figsize=(9*cols, 8.2))
    ax = axes[0] if cols == 2 else axes
    ax.add_patch(Rectangle((0, 0), FIELD_W, FIELD_H, fill=False, ls='--', lw=1.2, ec='#c0392b'))
    if variant != 'field-120x100':  # larger footprint shown in grey
        ax.add_patch(Rectangle((0, 0), fw, fh, fill=False, ls='--', lw=1, ec='0.4'))
    taped = geo['sec'] != 'nml'
    for sign in (1, -1):
        e = np.where(taped[:, None], offset(geo, sign*(geo['w']/2+TAPE/2)), np.nan)
        ax.plot(e[:, 0], e[:, 1], color='#3b4a8f', lw=1.6)
    ax.plot(geo['p'][:, 0], geo['p'][:, 1], color='0.6', lw=.6, ls=':')
    colours = dict(Yellow='#f2c12e', Red='#d1261c', Green='#1f9e4a', Black='#111111')
    for d in drums:
        ax.add_patch(Circle((d['x'], d['y']), R_DRUM, fc=colours[d['colour']], ec='0.2', lw=.4))
    ax.add_patch(Rectangle((ramp['x0'], ramp['y0']), ramp['x1']-ramp['x0'], ramp['y1']-ramp['y0'], fc='0.8', ec='0.3'))
    for key, name in (('north', 'North start/finish'), ('south', 'South start/finish')):
        q, _, nrm, wi, _ = frame(geo, starts[key])
        a, b = q-nrm*wi/2, q+nrm*wi/2
        ax.plot([a[0], b[0]], [a[1], b[1]], color='#2a6fb0', lw=3)
        ax.text(min(a[0], b[0])-.4, q[1], name, ha='right', va='center', fontsize=8)
    for t in star_ts():
        q = geo['p'][frac_index(geo, 'nml', t)]
        ax.plot(q[0], q[1], marker='*', ms=13, color='#1b3a6b')
    m = rep['marker_44ft']['field_xy']; ax.plot(m[0], m[1], marker='D', color='#8e44ad', ms=6)
    ax.text(m[0], m[1]+.6, '44 ft', color='#8e44ad', fontsize=8, ha='center')
    ax.text(fw/2, fh/2, 'PROPOSED', fontsize=30, color='#c0392b', alpha=.3, ha='center', va='center', rotation=20)
    status = 'authorized geometry met (not full II.2 compliance)' if rep['authorized_geometry_met'] else f"{len(rep['issues'])} open issue(s)"
    ax.set_title(f"PROPOSED {variant} (not Unity): N->S {rep['north_to_south_start_ft']:.1f} ft, closed loop {rep['lap_length_ft']:.1f} ft, field {fw/FT:.1f} x {fh/FT:.1f} ft, "
                 f"lane {rep['usable_width_taped_m']['min']:.2f}-{rep['usable_width_taped_m']['max']:.2f} m, "
                 f"R_nom {rep['radius']['nominal_min_m']:.2f} m - {status}\nred dashed = 120 x 100 ft field", fontsize=8)
    ax.set_xlim(-1, max(fw, FIELD_W)+1); ax.set_ylim(-1, max(fh, FIELD_H)+1); ax.set_aspect('equal')
    ax.set_xlabel('x east (m)'); ax.set_ylabel('y north (m)')
    if cols == 2:
        axes[1].imshow(plt.imread(reference)); axes[1].set_title('Original source image', fontsize=9); axes[1].axis('off')
    fig.tight_layout(); fig.savefig(out/'plan.png', dpi=110); fig.savefig(out/'plan.svg'); plt.close(fig)


def run(variant, out, reference=None, grid=GRID):
    geo, drums, ramp, starts = build(variant)
    rep = measure(geo, drums, ramp, starts, grid)
    out.mkdir(parents=True, exist_ok=True)
    enc = dict(indent=1, default=lambda o: o.item())
    docs = dict(geometry=geometry_doc(variant, geo, drums, ramp, starts), metadata=metadata(geo, starts),
                **{'unity-input': unity_input(variant, geo, drums, ramp, starts)})
    for name, data in docs.items():
        (out/f'{name}.json').write_text(json.dumps(data, **enc)+'\n')
    rep['variant'] = variant
    rep['sha256'] = {f'{n}.json': hashlib.sha256((out/f'{n}.json').read_bytes()).hexdigest() for n in docs}
    (out/'report.json').write_text(json.dumps(rep, **enc)+'\n')
    render(variant, geo, drums, ramp, starts, rep, out, reference)
    return rep


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--variant', choices=('field-120x100', 'length-500ft', 'rules-485', 'both'), default='both')
    args = parser.parse_args(argv)
    variants = ('field-120x100', 'rules-485') if args.variant == 'both' else (args.variant,)
    summary = {}
    for v in variants:
        rep = run(v, args.out/v, args.reference)
        summary[v] = {k: rep[k] for k in ('lap_length_ft', 'north_to_south_start_ft', 'closed_margin_to_520_ft', 'fit_isotropic', 'start_lines', 'connector_shape', 'field_ft', 'fit_scale_m_per_px', 'usable_width_taped_m', 'radius',
                                          'silhouette_max_deviation_m', 'inside_field', 'min_lane_to_lane_clearance_m',
                                          'min_drum_edge_gap_m', 'drum_intended_passage_min_m', 'corridor_loop_connected',
                                          'marker_44ft', 'drum_count', 'issues', 'authorized_deviations', 'authorized_geometry_met', 'full_rule_compliance')}
        summary[v]['witness'] = {k: rep['witness'].get(k) for k in ('found', 'length_ft', 'goals_in_order', 'indicative_min_radius_m')}
    print(json.dumps(summary, indent=1, default=lambda o: o.item()))
    return 0 if all(s['authorized_geometry_met'] for s in summary.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
