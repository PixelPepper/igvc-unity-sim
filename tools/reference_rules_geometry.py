#!/usr/bin/env python3
"""T-0091 PROPOSED rule-dimensioned AutoNav reference course (geometry prototype only, not Unity).

An explicit course in field metres, with x east, y north and the origin at the field's south-west corner. The
field is 120 ft east-west by 100 ft north-south. The course keeps the diagram's rectangular-loop topology:
- a right (east) straight with the ramp and the north/south start pair;
- wavy upper and lower corridors;
- the open left No Man's Land (NML) with four waypoint regions.
The loop is driven counter-clockwise from the north start (heading north), so the island is always on the left.

The centreline is an exact chain of straights and circular arcs, so the nominal turning radius is known exactly.
Corridor waves are a smooth arc-straight-arc family. Its swing angle is solved deterministically (bisection on a
monotone length function) for the 500 ft nominal lap. Every reported rule quantity is then measured from the
sampled geometry, never assumed from the construction. Drums keep their physical size (0.597 m x 1.008 m),
colour and group intent; each has an INTENDED class that is checked separately against measured gaps.

Outputs (--out DIR): geometry.json (render/authoring world geometry ONLY), metadata.json (spawn + six goals,
the only content allowed to reach a mission exporter), report.json, and plan.svg / plan.png marked PROPOSED.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

FT = .3048
FIELD_W, FIELD_H = 120*FT, 100*FT            # east-west, north-south (m)
MARGIN = .25                                   # tape/drum clearance to the field edge
TAPE = .1016                                   # 4 in
DRUM_D, DRUM_H = .597, 1.008
R_DRUM = DRUM_D/2
PASS = 5*FT                                    # 1.524 m minimum passage
LANE_MIN, LANE_MAX = 10*FT, 20*FT
W_RIGHT, W_CORRIDOR, W_NML = LANE_MIN, 4.4, 6.0     # widened from 3.8/5.6 after r1 measured global chokes
R_CORNER, R_WAVE, WAVES = 4., 2.5, 2
RAMP_RISE, RAMP_RUN, RAMP_DECK, RAMP_SIDE = .30, 2.145, .4, .3
START_GAP = 2.                                 # ramp end to start line
TARGET_LAP = 500*FT
DS = .02                                       # centreline sampling (m)
GRID = .05                                     # corridor raster resolution (m)
FLANK = W_RIGHT/2+RAMP_SIDE+.05+R_DRUM         # ramp-flank drum offset from the centreline

X_RIGHT = FIELD_W-MARGIN-FLANK-R_DRUM
X_LEFT = MARGIN+2*R_DRUM+W_NML/2
Y_TOP = FIELD_H-MARGIN-TAPE-W_CORRIDOR/2
Y_BOTTOM = MARGIN+TAPE+W_CORRIDOR/2
Y0, Y1 = Y_BOTTOM+R_CORNER, Y_TOP-R_CORNER
SPAN = (X_RIGHT-R_CORNER)-(X_LEFT+R_CORNER)


def primitives(theta):
    """Closed centreline chain from (X_RIGHT, Y0) heading north. Arcs carry a signed turn (left positive)."""
    period = SPAN/WAVES
    straight = (period-4*R_WAVE*math.sin(theta))/(2*math.cos(theta))
    if straight < 0:
        raise ValueError('wave swing too small for the corridor span')

    def wave(section):
        out = []
        for _ in range(WAVES):
            out += [('A', R_WAVE, theta, section), ('S', straight, None, section), ('A', R_WAVE, -2*theta, section),
                    ('S', straight, None, section), ('A', R_WAVE, theta, section)]
        return out
    vertical = Y1-Y0
    return ([('S', vertical, None, 'right'), ('A', R_CORNER, math.pi/2, 'corner-NE')]+wave('top')+
            [('A', R_CORNER, math.pi/2, 'corner-NW'), ('S', vertical, None, 'nml'), ('A', R_CORNER, math.pi/2, 'corner-SW')]+
            wave('bottom')+[('A', R_CORNER, math.pi/2, 'corner-SE')])


def width_at(section, fraction):
    taper = {'corner-NE': (W_RIGHT, W_CORRIDOR), 'corner-NW': (W_CORRIDOR, W_NML),
             'corner-SW': (W_NML, W_CORRIDOR), 'corner-SE': (W_CORRIDOR, W_RIGHT)}
    if section in taper:
        a, b = taper[section]
        return a+(b-a)*fraction
    return {'right': W_RIGHT, 'nml': W_NML}.get(section, W_CORRIDOR)


def sample(theta):
    """Exact integration of the chain at DS spacing: position, heading, signed curvature, width, section."""
    x, y, h = X_RIGHT, Y0, math.pi/2
    pts, heads, curv, widths, sections, starts = [], [], [], [], [], {}
    s_total = 0.
    for kind, a, b, section in primitives(theta):
        length = a if kind == 'S' else abs(b)*a
        starts.setdefault(section, s_total)
        n = max(1, int(math.ceil(length/DS)))
        for i in range(n):
            t = i/n*length
            if kind == 'S':
                px, py, ph, k = x+t*math.cos(h), y+t*math.sin(h), h, 0.
            else:
                sign = 1 if b > 0 else -1
                ph = h+sign*t/a
                px = x+sign*a*(math.sin(ph)-math.sin(h)); py = y-sign*a*(math.cos(ph)-math.cos(h)); k = sign/a
            pts.append((px, py)); heads.append(ph); curv.append(k); sections.append(section)
            widths.append(width_at(section, t/length))
        if kind == 'S':
            x, y = x+length*math.cos(h), y+length*math.sin(h)
        else:
            sign = 1 if b > 0 else -1; nh = h+b
            x += sign*a*(math.sin(nh)-math.sin(h)); y -= sign*a*(math.cos(nh)-math.cos(h)); h = nh
        s_total += length
    closure = math.hypot(x-X_RIGHT, y-Y0)
    return dict(p=np.array(pts), h=np.array(heads), k=np.array(curv), w=np.array(widths), sec=np.array(sections),
                s=np.arange(len(pts))*0.+np.cumsum([0.]+[0.]*(len(pts)-1)), length=s_total, closure=closure,
                starts=starts)


def lap_length(theta):
    return sum(a if k == 'S' else abs(b)*a for k, a, b, _ in primitives(theta))


def solve_theta(target=TARGET_LAP):
    lo, hi = math.radians(5), math.radians(88)
    if lap_length(hi) < target:
        return hi
    for _ in range(80):
        mid = (lo+hi)/2
        lo, hi = (mid, hi) if lap_length(mid) < target else (lo, mid)
    return (lo+hi)/2


def frame(geo, section, fraction):
    """Centreline point, tangent, left normal and width at a fractional station of a section."""
    idx = np.flatnonzero(geo['sec'] == section)
    i = idx[min(len(idx)-1, int(round(fraction*(len(idx)-1))))]
    h = geo['h'][i]
    return geo['p'][i], np.array([math.cos(h), math.sin(h)]), np.array([-math.sin(h), math.cos(h)]), geo['w'][i], i


# Drum layout. Diagram stations are converted to section fractions: top corridor t = (880 - px)/681 (westward),
# bottom t = (px - 199)/681 (eastward), NML t = (py - 248)/678 (southward). Lateral side: 'inner' = toward the
# island (left of travel), 'outer' = toward the field edge. Patterns keep barrel size and ~0.72 m pitch.
PLUS = ((0, 0), (.72, 0), (-.72, 0), (0, .72), (0, -.72))
TRIANGLE = ((-.36, -.31), (.36, -.31), (0, .31))
ROW_ACROSS = ((0, -.72), (0, 0), (0, .72))
TOP = [(.098, 'side', 'outer', 'Yellow', 1), (.119, 'side', 'inner', 'Yellow', 1), (.292, 'centre', None, 'Yellow', 1),
       (.374, 'centre', None, 'Yellow', 1), (.461, 'centre', None, 'Yellow', 1), (.532, 'side', 'outer', 'Yellow', 1),
       (.564, 'side', 'inner', 'Yellow', 1), (.636, 'side', 'outer', 'Yellow', PLUS), (.721, 'side', 'inner', 'Yellow', PLUS),
       (.802, 'side', 'outer', 'Yellow', PLUS), (.890, 'centre', None, 'Yellow', 1)]
BOTTOM = [(.072, 'centre', None, 'Yellow', 1), (.167, 'side', 'outer', 'Yellow', TRIANGLE), (.270, 'side', 'inner', 'Yellow', PLUS),
          (.355, 'side', 'outer', 'Yellow', TRIANGLE), (.446, 'side', 'inner', 'Yellow', 1), (.464, 'side', 'outer', 'Yellow', 1),
          (.557, 'centre', None, 'Yellow', 1), (.614, 'centre', None, 'Yellow', 1), (.677, 'centre', None, 'Yellow', 1),
          (.885, 'side', 'inner', 'Yellow', 1), (.912, 'side', 'outer', 'Yellow', 1)]
NML_WEST = [(272, 'Red'), (332, 'Green'), (401, 'Black'), (471, 'Yellow'), (525, 'Red'), (584, 'Green'), (646, 'Black'),
            (698, 'Yellow'), (747, 'Red'), (812, 'Green'), (866, 'Black'), (930, 'Yellow')]
NML_EAST = [(265, 'Yellow'), (311, 'Black'), (363, 'Green'), (421, 'Red'), (472, 'Yellow'), (532, 'Black'), (594, 'Green'),
            (656, 'Red'), (715, 'Yellow'), (775, 'Black'), (837, 'Green'), (889, 'Red')]
NML_INNER = [(311, 'centre', None, 1), (357, 'side', 'outer', 1), (362, 'side', 'inner', 1), (406, 'centre', None, 1),
             (504, 'centre', None, ROW_ACROSS), (585, 'centre', None, ROW_ACROSS), (675, 'centre', None, ROW_ACROSS),
             (727, 'centre', None, 1), (786, 'side', 'outer', 1), (788, 'side', 'inner', 1), (861, 'centre', None, 1)]
STARS_PY = (250, None, None, 928)              # stars 2 and 3 sit midway between the triplet rows
# r1 measured a joint 5 ft choke when the diagram's 9 interior NML stations were compressed into the 100 ft field
# (centred single ~1.2 m ahead of a middle-passage pair). Interior obstacles are therefore spaced evenly in diagram
# order, pairs share one station, and the two end singles (py 311, 861) are OMITTED and reported.
NML_OMITTED = (311, 861)
NML_STATIONS = (357, 406, 504, 585, 675, 727, 786)


def nml_t(py):
    return min(1., max(0., (py-248)/678))


def nml_station_t(py):
    key = {362: 357, 788: 786}.get(py, py)
    return (NML_STATIONS.index(key)+1)/(len(NML_STATIONS)+1)


def build_drums(geo):
    drums = []

    def put(at, kind, side_name, colour, group, pattern, offset_fn, passage=None):
        p, tan, nrm, w, i = at
        base = offset_fn(w, pattern)
        members = [(0, 0)] if pattern == 1 else pattern
        for j, (along, across) in enumerate(members):
            c = p+tan*along+nrm*(base+across)
            drums.append(dict(id=f'{group}-{j}', group=group, colour=colour, intended=kind, side=side_name,
                              passage=passage, x=round(float(c[0]), 4), y=round(float(c[1]), 4)))

    def hull_half(pattern):
        return R_DRUM if pattern == 1 else max(abs(a) for _, a in pattern)+R_DRUM

    def lane_offset(side_name):
        def fn(w, pattern):
            if side_name is None:
                return 0.
            reach = w/2-.1-hull_half(pattern)                 # 0.1 m from the tape's inner edge
            return reach if side_name == 'inner' else -reach
        return fn
    for name, table in (('top', TOP), ('bottom', BOTTOM)):
        for n, (t, kind, side_name, colour, pattern) in enumerate(table):
            put(frame(geo, name, t), kind, side_name, colour, f'{name}{n:02d}', pattern, lane_offset(side_name),
                passage=None if kind == 'centre' else ('inner' if side_name == 'outer' else 'outer'))
    for n, (py, kind, side_name, pattern) in enumerate(NML_INNER):
        if py in NML_OMITTED:
            continue
        def pair(w, _p, s=side_name):
            return 0. if s is None else (1 if s == 'inner' else -1)*(R_DRUM+PASS/2+.15)
        put(frame(geo, 'nml', nml_station_t(py)), kind, side_name, 'Yellow', f'nml{n:02d}', pattern, pair,
            passage=None if kind == 'centre' else 'middle')
    for side_name, column in (('outer', NML_WEST), ('inner', NML_EAST)):
        for n, (py, colour) in enumerate(column):
            sign = 1 if side_name == 'inner' else -1
            put(frame(geo, 'nml', nml_t(py)), 'boundary', side_name, colour, f'col-{side_name}{n:02d}', 1,
                lambda w, _p, s=sign: s*(w/2+R_DRUM))
    for section, t, side_name, tag in (('corner-NW', .85, 'outer', 'gate-top-o'), ('corner-NW', .85, 'inner', 'gate-top-i'),
                                       ('corner-SW', .15, 'outer', 'gate-bot-o'), ('corner-SW', .15, 'inner', 'gate-bot-i')):
        sign = 1 if side_name == 'inner' else -1
        put(frame(geo, section, t), 'boundary', side_name, 'Yellow', tag, 1, lambda w, _p, s=sign: s*(w/2+TAPE+R_DRUM+.02))
    for section, t, side_name, tag in (('corner-NE', .15, 'outer', 'corner-ne-o'), ('corner-NE', .85, 'inner', 'corner-ne-i'),
                                       ('corner-SE', .15, 'inner', 'corner-se-i'), ('corner-SE', .85, 'outer', 'corner-se-o')):
        put(frame(geo, section, t), 'side', side_name, 'Yellow', tag, 1, lane_offset(side_name),
            passage='inner' if side_name == 'outer' else 'outer')
    ramp = ramp_box()
    for y, tag in ((ramp['y1']+.4, 'flank-n'), (ramp['y0']-.4, 'flank-s')):
        for sign, side_name in ((1, 'inner'), (-1, 'outer')):
            drums.append(dict(id=f'{tag}-{side_name}', group=f'{tag}-{side_name}', colour='Yellow', intended='flank',
                              side=side_name, passage=None, x=round(X_RIGHT-sign*FLANK, 4), y=round(y, 4)))
    return drums


def ramp_box():
    mid = (Y0+Y1)/2; half = RAMP_RUN+RAMP_DECK/2
    return dict(x0=X_RIGHT-W_RIGHT/2-RAMP_SIDE, x1=X_RIGHT+W_RIGHT/2+RAMP_SIDE, y0=mid-half, y1=mid+half,
                rise=RAMP_RISE, run=RAMP_RUN, deck=RAMP_DECK, grade=RAMP_RISE/RAMP_RUN)


def build(theta=None):
    theta = solve_theta() if theta is None else theta
    geo = sample(theta)
    geo['s'] = np.arange(len(geo['p']))*0.
    seg = np.concatenate([[0.], np.cumsum(np.hypot(*np.diff(geo['p'], axis=0).T))])
    geo['s'] = seg
    ramp = ramp_box()
    starts = dict(north=ramp['y1']+START_GAP, south=ramp['y0']-START_GAP)
    return theta, geo, build_drums(geo), ramp, starts


# ---------------------------------------------------------------- measurement (from sampled geometry only)
def offset(geo, d):
    nrm = np.stack([-np.sin(geo['h']), np.cos(geo['h'])], 1)
    return geo['p']+nrm*np.asarray(d)[:, None]


def measure(theta, geo, drums, ramp, starts):
    from scipy.spatial import cKDTree
    from scipy import ndimage
    rep = dict(theta_deg=math.degrees(theta), sampling=dict(centreline_m=DS, raster_m=GRID, cross_section_m=.01))
    p, w, k, sec = geo['p'], geo['w'], geo['k'], geo['sec']
    taped = sec != 'nml'
    rep['closure_error_m'] = geo['closure']
    rep['lap_length_m'] = geo['length']; rep['lap_length_ft'] = geo['length']/FT
    rep['section_lengths_m'] = {s: float(np.sum(np.diff(geo['s'])[(sec[:-1] == s)])) for s in dict.fromkeys(sec)}
    # Usable lane width: the lane's OWN paired facing tape edges along the local normal (tape sections only).
    # Intrusion by unrelated tape is covered by the lane-to-lane clearance below; joins by the step checks.
    left, right = offset(geo, w/2), offset(geo, -w/2)
    usable = np.hypot(*(left-right)[taped].T)
    rep['usable_width_taped_m'] = dict(min=float(usable.min()), max=float(usable.max()), resolution_m=DS,
                                       error_allowance_m=.001, note='paired facing inner edges along the local normal')
    pair = taped[:-1] & taped[1:]                              # consecutive taped samples only (NML has no tape)
    step_l = np.hypot(*np.diff(left, axis=0).T)[pair]; step_r = np.hypot(*np.diff(right, axis=0).T)[pair]
    jumps = np.abs(np.diff(geo['h']))
    jumps = np.minimum(jumps, 2*math.pi-jumps)
    rep['joins'] = dict(max_heading_step_deg=float(np.degrees(jumps.max())), max_edge_step_m=float(max(step_l.max(), step_r.max())),
                        abrupt=bool(jumps.max() > math.radians(2) or max(step_l.max(), step_r.max()) > 4*DS))
    col = [d for d in drums if d['group'].startswith('col-')]
    nml_w = [W_NML]  # columns are placed at the NML edge by construction; re-measure from coordinates below
    west = np.array([[d['x'], d['y']] for d in col if d['side'] == 'outer'])
    east = np.array([[d['x'], d['y']] for d in col if d['side'] == 'inner'])
    nml_w = float(east[:, 0].min()-west[:, 0].max()-2*R_DRUM)
    rep['usable_width_nml_m'] = dict(min_between_column_inner_edges=nml_w)
    # Curvature: nominal path radius, and inner-edge radius (fold if <= 0).
    curved = np.abs(k) > 0
    radius = 1/np.abs(k[curved])
    inner = radius-w[curved]/2
    rep['nominal_min_radius_m'] = float(radius.min())
    rep['inner_edge_min_radius_m'] = float(inner.min())
    rep['tape_fold'] = bool(inner.min() <= 0)
    # Field bounds over tape outer edges, drums and ramp.
    outer = np.concatenate([offset(geo, w/2+TAPE)[taped], offset(geo, -w/2-TAPE)[taped]])
    dxy = np.array([[d['x'], d['y']] for d in drums])
    xs = np.concatenate([outer[:, 0], dxy[:, 0]-R_DRUM, dxy[:, 0]+R_DRUM, [ramp['x0'], ramp['x1']]])
    ys = np.concatenate([outer[:, 1], dxy[:, 1]-R_DRUM, dxy[:, 1]+R_DRUM, [ramp['y0'], ramp['y1']]])
    rep['extent_m'] = dict(x=[float(xs.min()), float(xs.max())], y=[float(ys.min()), float(ys.max())],
                           field=[FIELD_W, FIELD_H])
    rep['inside_field'] = bool(xs.min() >= 0 and ys.min() >= 0 and xs.max() <= FIELD_W and ys.max() <= FIELD_H)
    # Lane-to-lane clearance between non-local parts of the loop (no overlapping corridors).
    edge = w/2+np.where(taped, TAPE, 2*R_DRUM)
    tree = cKDTree(p)
    pairs = np.array(sorted(tree.query_pairs(edge.max()*2+1.)))
    ds = np.abs(geo['s'][pairs[:, 0]]-geo['s'][pairs[:, 1]]); ds = np.minimum(ds, geo['length']-ds)
    dist = np.hypot(*(p[pairs[:, 0]]-p[pairs[:, 1]]).T)
    need = edge[pairs[:, 0]]+edge[pairs[:, 1]]
    far = ds > math.pi/2*need
    rep['min_lane_to_lane_clearance_m'] = float((dist-need)[far].min()) if far.any() else None
    # Drum overlap / spacing.
    dtree = cKDTree(dxy)
    nn = dtree.query(dxy, 2)[0][:, 1]
    rep['min_drum_edge_gap_m'] = float(nn.min()-DRUM_D)
    # Per-drum measured cross-section gaps (joint over all drums), compared with the intended class.
    checks, failures = [], []
    for d in drums:
        c = np.array([d['x'], d['y']])
        i = tree.query(c)[1]
        h = geo['h'][i]; nrm = np.array([-math.sin(h), math.cos(h)]); wi = w[i]
        lat = float(np.dot(c-p[i], nrm))
        if d['intended'] in ('boundary', 'flank'):
            ok = abs(lat)-R_DRUM >= wi/2-1e-3
            checks.append(dict(id=d['id'], intended=d['intended'], lateral=lat, outside_usable=ok))
            if not ok:
                failures.append(f"{d['id']}: {d['intended']} drum intrudes into usable width")
            continue
        t = np.arange(-wi/2, wi/2+1e-9, .01)
        line = p[i]+np.outer(t, nrm)
        near = dtree.query_ball_point(p[i], wi/2+R_DRUM+.01)
        blocked = np.zeros(len(t), bool)
        for j in near:
            blocked |= np.hypot(*(line-dxy[j]).T) <= R_DRUM
        runs, cur = [], None
        for n, b in enumerate(blocked):
            if b and cur is None:
                cur = [t[n], t[n]]
            elif b:
                cur[1] = t[n]
            elif cur is not None:
                runs.append(cur); cur = None
        if cur is not None:
            runs.append(cur)
        merged = []
        for r in runs:
            if merged and r[0]-merged[-1][1] < PASS:
                merged[-1][1] = r[1]
            else:
                merged.append(list(r))
        own = next((m for m in merged if m[0]-1e-6 <= lat <= m[1]+1e-6), None)
        if own is None:
            failures.append(f"{d['id']}: cross-section does not contain the drum"); continue
        idx = merged.index(own)
        gap_lo = own[0]-(merged[idx-1][1] if idx > 0 else -wi/2)
        gap_hi = (merged[idx+1][0] if idx+1 < len(merged) else wi/2)-own[1]
        measured = 'centre' if min(gap_lo, gap_hi) >= PASS else ('side' if max(gap_lo, gap_hi) >= PASS else 'blocked')
        inner_gap, outer_gap = gap_hi, gap_lo                 # +normal is the island (inner) side
        if d['intended'] == 'centre':
            ok = measured == 'centre'
        elif d['passage'] == 'inner':
            ok = inner_gap >= PASS
        elif d['passage'] == 'outer':
            ok = outer_gap >= PASS
        else:                                                  # NML pair: the middle passage must be >= 5 ft
            ok = (inner_gap if d['side'] == 'outer' else outer_gap) >= PASS
        checks.append(dict(id=d['id'], intended=d['intended'], passage=d['passage'], measured=measured,
                           inner_gap=round(float(inner_gap), 4), outer_gap=round(float(outer_gap), 4), ok=ok))
        if not ok:
            failures.append(f"{d['id']}: intended {d['intended']}/{d['passage']} but gaps inner {inner_gap:.3f} outer {outer_gap:.3f}")
    gaps = [min(c['inner_gap'], c['outer_gap']) if c['measured'] == 'centre' else max(c['inner_gap'], c['outer_gap'])
            for c in checks if 'measured' in c]
    rep['drum_passage_min_m'] = float(min(gaps))
    rep['drum_checks'] = checks
    # Global 5 ft corridor: free cells for the CENTRE of a 1.524 m disc; must close the loop and reach each goal.
    nx, ny = int(FIELD_W/GRID), int(FIELD_H/GRID)
    gx, gy = np.meshgrid((np.arange(nx)+.5)*GRID, (np.arange(ny)+.5)*GRID)
    cells = np.stack([gx.ravel(), gy.ravel()], 1)
    dist_c, near_c = tree.query(cells)
    # Conservative: cell-centre tests are inflated by half a cell diagonal so straight moves between free cells
    # cannot clip a blocked region; diagonal moves additionally require both orthogonal neighbours free.
    slack = GRID*math.sqrt(2)/2
    free = dist_c <= w[near_c]/2-PASS/2-slack
    free &= dtree.query(cells)[0] >= R_DRUM+PASS/2+slack
    free = free.reshape(ny, nx)
    cut = (np.abs(gy-starts['north']) < GRID) & (np.abs(gx-X_RIGHT) < W_RIGHT)
    free_cut = free & ~cut
    labels, _ = ndimage.label(free_cut)

    def cell(x, y):
        return int(y/GRID), int(x/GRID)
    a, b = labels[cell(X_RIGHT, starts['north']+.3)], labels[cell(X_RIGHT, starts['north']-.3)]
    rep['corridor_loop_connected'] = bool(a and a == b)
    rep['corridor_free_fraction'] = float(free.mean())
    # Ordered route witness: shortest 5 ft-disc-centre path from just past the north start all the way round to
    # just before it, through the lane-restricted free space. It must visit the goal regions in order.
    meta = metadata(geo, starts)
    rep['witness'] = witness(free_cut, cell(X_RIGHT, starts['north']+.3), cell(X_RIGHT, starts['north']-.3), meta, gx, gy)
    rep['goals'] = rep['witness'].pop('goal_hits')
    # Ramp and the 44 ft marker along the actual route.
    rep['ramp'] = dict(grade=ramp['grade'], max_allowed=.15, width_m=ramp['x1']-ramp['x0'])
    ahead = Y1-starts['north']
    rep['north_start_to_straight_end_m'] = ahead
    rep['marker_44ft_on_right_straight'] = bool(ahead >= 44*FT)
    rep['marker_44ft_route_station_after_north_start_m'] = 44*FT
    # Verdicts.
    issues = list(failures)
    lo, hi = rep['usable_width_taped_m']['min'], rep['usable_width_taped_m']['max']
    if lo < LANE_MIN-DS or hi > LANE_MAX+DS: issues.append('taped lane width outside 10-20 ft')
    if not LANE_MIN <= nml_w <= LANE_MAX: issues.append('NML width outside 10-20 ft')
    if rep['nominal_min_radius_m'] < PASS: issues.append('nominal radius < 5 ft')
    if rep['tape_fold']: issues.append('tape inner edge folds')
    if not rep['inside_field']: issues.append('geometry outside field')
    if rep['min_lane_to_lane_clearance_m'] is not None and rep['min_lane_to_lane_clearance_m'] <= 0: issues.append('lanes overlap')
    if rep['min_drum_edge_gap_m'] < 0: issues.append('drums overlap')
    if not rep['corridor_loop_connected']: issues.append('5 ft corridor does not close the lap')
    if not rep['witness']['found']: issues.append('no ordered collision-free 5 ft route witness')
    elif not rep['witness']['goals_in_order']: issues.append('route witness misses a goal region or its order')
    if rep['joins']['abrupt']: issues.append('abrupt join in centreline or tape edges')
    if not 480*FT <= rep['witness'].get('length_m', 0) <= 520*FT:
        issues.append('collision-free route witness outside 480-520 ft (nominal centreline is a measuring convention '
                      'that passes through centred obstacles)')
    if ramp['grade'] > .15: issues.append('ramp grade > 15%')
    if not 480*FT <= geo['length'] <= 520*FT: issues.append('lap outside 480-520 ft')
    if geo['closure'] > 1e-3: issues.append('centreline does not close')
    rep['drum_count'] = len(drums); rep['drums_omitted'] = [dict(diagram_px_y=py, colour='Yellow', region='NML interior centre single', reason='joint 5 ft choke when compressed into the 100 ft field') for py in NML_OMITTED]
    rep['drum_colours'] = {c: sum(d['colour'] == c for d in drums) for c in ('Yellow', 'Red', 'Green', 'Black')}
    rep['issues'] = issues
    rep['unverified'] = ['Unity integration and rendering', 'sensor appearance', 'navigation', 'judged timing (44 ft/30 s, '
                         '>1 mph average, six-minute cap)', 'tape mesh triangulation', 'ramp collider behaviour']
    rep['measured_constraints_met'] = not issues
    return rep


def witness(free, src, dst, meta, gx, gy):
    """8-connected Dijkstra on free cells (diagonals only when both orthogonal neighbours are free)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    ny, nx = free.shape
    ids = -np.ones(free.shape, int); ids[free] = np.arange(free.sum())
    rows, cols, cost = [], [], []
    for dy, dx, c in ((0, 1, 1.), (1, 0, 1.), (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2))):
        a = free[max(0, -dy):ny-max(0, dy), max(0, -dx):nx-max(0, dx)]
        ys, xs = np.nonzero(a)
        ys = ys+max(0, -dy); xs = xs+max(0, -dx)
        ok = free[ys+dy, xs+dx]
        if dx and dy:
            ok &= free[ys+dy, xs] & free[ys, xs+dx]
        rows.append(ids[ys[ok], xs[ok]]); cols.append(ids[ys[ok]+dy, xs[ok]+dx]); cost.append(np.full(ok.sum(), c*GRID))
    rows, cols, cost = map(np.concatenate, (rows, cols, cost))
    n = int(free.sum())
    graph = coo_matrix((cost, (rows, cols)), shape=(n, n)).tocsr()
    s, t = ids[src], ids[dst]
    if s < 0 or t < 0:
        return dict(found=False, goal_hits=[], reason='start or end cell not free')
    dist, pred = dijkstra(graph, directed=False, indices=s, return_predecessors=True)
    if not math.isfinite(dist[t]):
        return dict(found=False, goal_hits=[], reason='no path')
    flat = np.flatnonzero(free.ravel())
    path, v = [], t
    while v != s and v >= 0:
        path.append(flat[v]); v = pred[v]
    path.append(flat[s]); path.reverse()
    pts = np.stack([gx.ravel()[path], gy.ravel()[path]], 1)
    hits, last = [], -1
    for g in meta['goals']:
        inside = np.flatnonzero(np.hypot(*(pts-np.array(g['field_xy'])).T) <= g['radius_m'])
        later = inside[inside > last]
        hits.append(dict(name=g['name'], visited=bool(len(later)), first_index=int(later[0]) if len(later) else None))
        if len(later):
            last = later[0]
    return dict(found=True, length_m=float(dist[t]), length_ft=float(dist[t])/FT, cells=len(path),
                goals_in_order=all(h['visited'] for h in hits), goal_hits=hits,
                note='shortest disc-centre path; hugs inside corners, so it is a lower bound on a driven lap')


def metadata(geo, starts):
    """Spawn and the six broad goals only. Field frame plus the odom transform; no course geometry."""
    ne = frame(geo, 'corner-NE', .5)[0]
    nml = [frame(geo, 'nml', t)[0] for t in star_ts()]
    goals = [('top-right gate', ne, 3.)]+[(f'waypoint star {n+1}', q, 2.) for n, q in enumerate(nml)]
    goals.append(('south start/finish', np.array([X_RIGHT, starts['south']]), 2.))
    return dict(frame='field metres, x east, y north, origin field SW corner',
                spawn=dict(field_xy=[X_RIGHT, starts['north']], heading='north'),
                odom_from_field='odom_x = y - spawn_y ; odom_y = spawn_x - x',
                goals=[dict(name=n, field_xy=[round(float(q[0]), 4), round(float(q[1]), 4)], radius_m=r) for n, q, r in goals])


def star_ts():
    rows = [nml_station_t(py) for py, *_rest in NML_INNER if _rest[2] == ROW_ACROSS]
    return (nml_t(STARS_PY[0]), (rows[0]+rows[1])/2, (rows[1]+rows[2])/2, nml_t(STARS_PY[3]))


def geometry_doc(theta, geo, drums, ramp, starts):
    taped = geo['sec'] != 'nml'
    step = 5                                                    # export every 0.10 m

    def poly(arr):
        return [[round(float(a), 4), round(float(b), 4)] for a, b in arr[::step]]
    runs, cur = [], []
    for i in range(len(taped)):
        if taped[i]:
            cur.append(i)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    tapes = []
    for r in runs:
        idx = np.array(r)
        sub = dict(p=geo['p'][idx], h=geo['h'][idx])
        for sign, name in ((1, 'inner'), (-1, 'outer')):
            tapes.append(dict(side=name, width_m=TAPE, centre=poly(offset(sub, sign*(geo['w'][idx]/2+TAPE/2)))))
    return dict(status='PROPOSED - not Unity, not rule-certified', units='m', frame='x east, y north, origin field SW corner',
                field=[FIELD_W, FIELD_H], wave=dict(theta_deg=math.degrees(theta), radius_m=R_WAVE, periods=WAVES),
                centreline=poly(geo['p']), widths=[round(float(v), 4) for v in geo['w'][::step]],
                tapes=tapes, drums=drums, drum=dict(diameter_m=DRUM_D, height_m=DRUM_H), ramp=ramp,
                start_lines=dict(north_y=starts['north'], south_y=starts['south'], x=X_RIGHT, length_m=W_RIGHT),
                waypoint_stars=[[round(float(q[0]), 4), round(float(q[1]), 4)] for q in
                                (frame(geo, 'nml', t)[0] for t in star_ts())],
                interpretations=['black diagram circles are black drums, not potholes', 'optional 2 ft potholes omitted',
                                 'NML boundaries are the coloured drum columns; no tape across NML',
                                 'drum stations follow the diagram; exact coordinates moved to satisfy passages',
                                 'stars 2 and 3 sit midway between the NML triplet rows'])


def render(geo, drums, ramp, starts, rep, out, reference=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    cols = 2 if reference and Path(reference).exists() else 1
    fig, axes = plt.subplots(1, cols, figsize=(9*cols, 8.2))
    ax = axes[0] if cols == 2 else axes
    ax.add_patch(Rectangle((0, 0), FIELD_W, FIELD_H, fill=False, ls='--', lw=1, ec='0.4'))
    taped = geo['sec'] != 'nml'
    for sign in (1, -1):
        e = offset(geo, sign*(geo['w']/2+TAPE/2))
        e = np.where(taped[:, None], e, np.nan)
        ax.plot(e[:, 0], e[:, 1], color='#3b4a8f', lw=1.6)
    ax.plot(geo['p'][:, 0], geo['p'][:, 1], color='0.6', lw=.6, ls=':')
    colours = dict(Yellow='#f2c12e', Red='#d1261c', Green='#1f9e4a', Black='#111111')
    for d in drums:
        ax.add_patch(Circle((d['x'], d['y']), R_DRUM, fc=colours[d['colour']], ec='0.2', lw=.4))
    ax.add_patch(Rectangle((ramp['x0'], ramp['y0']), ramp['x1']-ramp['x0'], ramp['y1']-ramp['y0'], fc='0.8', ec='0.3'))
    for y, name in ((starts['north'], 'North start/finish'), (starts['south'], 'South start/finish')):
        ax.plot([X_RIGHT-W_RIGHT/2, X_RIGHT+W_RIGHT/2], [y, y], color='#2a6fb0', lw=3)
        ax.text(X_RIGHT-W_RIGHT/2-.4, y, name, ha='right', va='center', fontsize=8)
    for n, t in enumerate(star_ts()):
        q = frame(geo, 'nml', t)[0]
        ax.plot(q[0], q[1], marker='*', ms=13, color='#1b3a6b')
    ax.text(X_LEFT+4, FIELD_H/2, "No Man's Land", fontsize=9)
    ax.text(FIELD_W/2, FIELD_H/2, 'PROPOSED', fontsize=30, color='#c0392b', alpha=.35, ha='center', va='center', rotation=20)
    ax.set_title(f"PROPOSED rule-dimensioned course (not Unity) - lap {rep['lap_length_ft']:.1f} ft, "
                 f"lane {rep['usable_width_taped_m']['min']:.2f}-{rep['usable_width_taped_m']['max']:.2f} m, "
                 f"NML {rep['usable_width_nml_m']['min_between_column_inner_edges']:.2f} m", fontsize=9)
    ax.set_xlim(-1, FIELD_W+1); ax.set_ylim(-1, FIELD_H+1); ax.set_aspect('equal')
    ax.set_xlabel('x east (m) - field 120 ft'); ax.set_ylabel('y north (m) - field 100 ft')
    if cols == 2:
        axes[1].imshow(plt.imread(reference)); axes[1].set_title('Reference image trace (T-0089)', fontsize=9)
        axes[1].axis('off')
    fig.tight_layout()
    fig.savefig(out/'plan.png', dpi=110); fig.savefig(out/'plan.svg')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reference', type=Path, help='reference image for the side-by-side comparison')
    args = parser.parse_args(argv)
    theta, geo, drums, ramp, starts = build()
    rep = measure(theta, geo, drums, ramp, starts)
    args.out.mkdir(parents=True, exist_ok=True)
    docs = dict(geometry=geometry_doc(theta, geo, drums, ramp, starts), metadata=metadata(geo, starts))
    for name, data in docs.items():
        (args.out/f'{name}.json').write_text(json.dumps(data, indent=1, default=lambda o: o.item())+'\n')
    rep['sha256'] = {f'{n}.json': hashlib.sha256((args.out/f'{n}.json').read_bytes()).hexdigest() for n in docs}
    (args.out/'report.json').write_text(json.dumps(rep, indent=1, default=lambda o: o.item())+'\n')
    render(geo, drums, ramp, starts, rep, args.out, args.reference)
    print(json.dumps({k: rep[k] for k in ('theta_deg', 'lap_length_ft', 'usable_width_taped_m', 'usable_width_nml_m',
                                          'nominal_min_radius_m', 'inner_edge_min_radius_m', 'extent_m',
                                          'min_lane_to_lane_clearance_m', 'min_drum_edge_gap_m', 'drum_passage_min_m',
                                          'corridor_loop_connected', 'goals', 'drum_count', 'issues',
                                          'measured_constraints_met')}, indent=1, default=lambda o: o.item()))
    return 0 if rep['measured_constraints_met'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
