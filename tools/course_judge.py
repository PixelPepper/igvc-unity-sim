"""Privileged offline world scoring. Never import this into mission control."""
import bisect
import math
import re

from generate_course_variant import BODY_RADIUS, box, polygon_distance

FOOTPRINT = (-1.1, .6, -.5, .5)
PAINT_HALF_WIDTH = .06
SWEEP_STEP = .02
# finish-crossing/1 only: after an accepted crossing that follows every gate,
# terminal samples may continue onto the closed loop's start, at most this far.
POST_CROSSING_ARC_M = 6.


def identity_evidence(run, expected_hash):
    """Bind to exact manifest bytes, rather than seed/name or geometry guesses."""
    hashes = re.findall(r'(?:^|\s)course_hash=([^\s]+)', run.get('sim_status', ''))
    if 'course_sha256' in run:
        hashes.append(run['course_sha256'])
    valid_expected = isinstance(expected_hash, str) and re.fullmatch(r'[0-9a-f]{64}', expected_hash)
    passed = bool(valid_expected and hashes and all(h == expected_hash for h in hashes))
    return dict(passed=passed, expected_course_sha256=expected_hash,
                observed_course_hashes=hashes, status='matched' if passed else (
                    'missing' if not valid_expected or not hashes else 'mismatched'))


def world_points(course):
    raw = course.get('centerline', [])
    points = [(p['x'], p['y']) for p in raw]
    if (course.get('frame') != 'odom' or course.get('units') != 'm'
            or not 4 <= len(points) <= 5000
            or any(not all(isinstance(v, (int, float)) and math.isfinite(v) and abs(v) <= 100 for v in p) for p in points)
            or math.dist(points[0], points[-1]) > 1e-6
            or any(math.dist(a, b) <= 1e-8 for a, b in zip(points, points[1:]))):
        raise ValueError('Finite closed odom/metre WORLD centerline required')
    widths = [p.get('half_width') or course.get('lane_width_m', 0)/2 for p in raw]
    if any(not isinstance(w, (int, float)) or not math.isfinite(w) or w < 1 or w > 4 for w in widths):
        raise ValueError('Supported WORLD lane half widths required')
    if any(type(p.get('painted')) is not bool for p in raw):
        raise ValueError('Explicit WORLD paint flags required')
    return points, widths


def painted_polygons(course):
    """Reconstruct rendered miter quads, including stripe width and actual gaps.

    Unity draws a segment only when BOTH endpoints are painted. Its offset is
    the bisector of incoming/outgoing left normals divided by its outgoing dot.
    This does not use generated guide_route_xy or its boundary approximation.
    """
    points, widths = world_points(course)
    offsets = []
    for i in range(len(points)-1):
        previous = points[i-1] if i else points[-2]
        current, following = points[i], points[i+1]
        incoming = tuple((current[k]-previous[k])/math.dist(current, previous) for k in range(2))
        outgoing = tuple((following[k]-current[k])/math.dist(following, current) for k in range(2))
        n0, n1 = (-incoming[1], incoming[0]), (-outgoing[1], outgoing[0])
        normal = (n0[0]+n1[0], n0[1]+n1[1])
        norm = math.hypot(*normal)
        if norm <= 1e-9:
            raise ValueError('Unsupported reversed WORLD paint corner')
        normal = tuple(v/norm for v in normal)
        denominator = sum(a*b for a, b in zip(normal, n1))
        if denominator < .5:
            raise ValueError('Unsupported WORLD paint corner angle')
        offsets.append(tuple(v/denominator for v in normal))
    offsets.append(offsets[0])
    polygons = []
    for i, (a, b) in enumerate(zip(points, points[1:])):
        if not (course['centerline'][i]['painted'] and course['centerline'][i+1]['painted']):
            continue
        for side in (-1, 1):
            def vertex(index, edge):
                return tuple(points[index][k]+offsets[index][k]*side*(widths[index]+edge) for k in range(2))
            polygons.append([vertex(i, -PAINT_HALF_WIDTH), vertex(i+1, -PAINT_HALF_WIDTH),
                             vertex(i+1, PAINT_HALF_WIDTH), vertex(i, PAINT_HALF_WIDTH)])
    return polygons


class PaintIndex:
    """Small spatial buckets keep long recordings bounded by nearby paint."""
    def __init__(self, polygons):
        self.polygons, self.buckets = polygons, {}
        for index, poly in enumerate(polygons):
            for x in range(math.floor(min(p[0] for p in poly)/4), math.floor(max(p[0] for p in poly)/4)+1):
                for y in range(math.floor(min(p[1] for p in poly)/4), math.floor(max(p[1] for p in poly)/4)+1):
                    self.buckets.setdefault((x, y), set()).add(index)

    def clearance(self, pose):
        # Anything outside this query is farther than one sweep step. Capping
        # clearance at SWEEP_STEP is sufficient for a continuous proof.
        x, y, yaw = pose
        reach = BODY_RADIUS+SWEEP_STEP
        indices = set()
        for bx in range(math.floor((x-reach)/4), math.floor((x+reach)/4)+1):
            for by in range(math.floor((y-reach)/4), math.floor((y+reach)/4)+1):
                indices.update(self.buckets.get((bx, by), ()))
        body = box(x, y, yaw, *FOOTPRINT)
        return min([SWEEP_STEP]+[polygon_distance(body, self.polygons[i]) for i in indices])


def interpolated(samples):
    yield 0., samples[0][1:], 0.
    for index, (a, b) in enumerate(zip(samples, samples[1:])):
        angle = math.atan2(math.sin(b[3]-a[3]), math.cos(b[3]-a[3]))
        bound = math.dist(a[1:3], b[1:3])+BODY_RADIUS*abs(angle)
        count = max(1, math.ceil(bound/SWEEP_STEP))
        if count > 10000:
            raise ValueError('Unbounded pose sweep')
        for step in range(1, count+1):
            f = step/count
            yield index+f, (a[1]+f*(b[1]-a[1]), a[2]+f*(b[2]-a[2]), a[3]+f*angle), bound/count


def paint_evidence(samples, course):
    try:
        index = PaintIndex(painted_polygons(course))
        contacts = uncertain = 0
        first = None
        previous = None
        lower = SWEEP_STEP
        for stamp, pose, step_bound in interpolated(samples):
            clearance = index.clearance(pose)
            # 1 mm conservative allowance covers Unity single precision vertices.
            contacts += int(clearance <= .001)
            if clearance <= .001 and first is None:
                first = dict(trajectory_index=stamp, pose=list(pose))
            if previous is not None:
                bound = min(previous, clearance)-step_bound/2-.001
                lower = min(lower, bound)
                uncertain += int(bound <= 0)
            previous = clearance
        return dict(passed=bool(index.polygons) and not contacts and not uncertain,
                    geometry_available=bool(index.polygons), painted_quad_count=len(index.polygons),
                    contact_pose_count=contacts, unproven_sweep_subsegments=uncertain,
                    first_contact=first, conservative_clearance_lower_bound_m=lower,
                    numerical_allowance_m=.001, evaluated_pose_clearance_cap_m=SWEEP_STEP)
    except (ValueError, KeyError, TypeError) as error:
        return dict(passed=False, geometry_available=False, reason=str(error))


def topology_evidence(samples, course, *, open_area_lateral_m=8., gate_spacing_m=2.,
                      finish_crossing=False, crossing=None):
    """Ordered WORLD cross-sections plus reachable unwrapped local projection.

    Bounds are explicit development scoring policy, not competition rules.
    No finish jump, global nearest branch, or stationary progress credit exists.
    Legacy completion needs the final 0.4 m of arc and an end within 0.4 m of
    the origin. With finish_crossing, completion instead needs the audit's own
    accepted crossing (tracker provenance) strictly after the segment that
    visits the final gate. Only after both may the reachable projection window
    continue past the closed arc onto the loop start, bounded by
    POST_CROSSING_ARC_M; the corridor check still applies to every sample.
    """
    policy = dict(open_area_lateral_m=open_area_lateral_m, gate_spacing_m=gate_spacing_m,
                  arc_motion_multiplier=1.5, intended_direction='WORLD centerline array order')
    if finish_crossing:
        policy.update(start_tolerance_m=.4, completion='finish-crossing/1 after final gate',
                      post_crossing_arc_m=POST_CROSSING_ARC_M)
    else:
        policy.update(start_finish_tolerance_m=.4)
    result = dict(passed=False, policy=policy, gates_visited=0)
    try:
        if not (math.isfinite(open_area_lateral_m) and 1 <= open_area_lateral_m <= 20
                and math.isfinite(gate_spacing_m) and .5 <= gate_spacing_m <= 5):
            raise ValueError('Unsupported development topology policy')
        points, widths = world_points(course)
        arcs = [0.]
        for a, b in zip(points, points[1:]):
            arcs.append(arcs[-1]+math.dist(a, b))
        total = arcs[-1]
        last_segment = len(points)-2
        # The closed loop repeated once; reachable only after an accepted crossing.
        raw = course['centerline']+course['centerline'][1:]
        ext_points, ext_widths, ext_arcs = points+points[1:], widths+widths[1:], list(arcs)
        for a, b in zip(points, points[1:]):
            ext_arcs.append(ext_arcs[-1]+math.dist(a, b))
        def at(arc):
            i = min(len(points)-2, max(0, bisect.bisect_right(arcs, arc)-1))
            length = arcs[i+1]-arcs[i]
            f = (arc-arcs[i])/length
            tangent = tuple((points[i+1][k]-points[i][k])/length for k in range(2))
            p = tuple(points[i][k]+f*(points[i+1][k]-points[i][k]) for k in range(2))
            marked = course['centerline'][i]['painted'] and course['centerline'][i+1]['painted']
            width = widths[i]+f*(widths[i+1]-widths[i])
            return p, tangent, width if marked else open_area_lateral_m
        count = max(1, math.ceil(total/gate_spacing_m))
        gates = [(total*i/count, *at(total*i/count)) for i in range(1, count)]
        result.update(gates_required=len(gates), total_arc_m=total, progress_m=0., maximum_progress_m=0.)
        if math.dist(samples[0][1:3], points[0]) > .4:
            raise ValueError('Run did not start at WORLD loop origin')
        crossing_index = None
        completed = 0 if not gates else None
        if finish_crossing and crossing is not None:
            # Crossing segment (previous, index]; only the audit tracker's ints are used.
            crossing_index = crossing['previous_sample_index']
            if (type(crossing_index) is not int or type(crossing['sample_index']) is not int
                    or crossing['sample_index'] != crossing_index+1
                    or not 0 <= crossing_index < len(samples)-1):
                raise ValueError('Invalid finish crossing provenance')
        progress = maximum = 0.
        visited = 0
        limit, limit_segment = total, last_segment
        for index, (a, b) in enumerate(zip(samples, samples[1:]), 1):
            delta = math.dist(a[1:3], b[1:3])
            if (limit == total and crossing_index is not None and completed is not None
                    and index > crossing_index >= completed):
                # Terminal samples after the accepted crossing may pass the
                # origin onto the loop start; the corridor check below remains.
                limit = total+min(total, POST_CROSSING_ARC_M)
                limit_segment = min(len(ext_points)-2, bisect.bisect_left(ext_arcs, limit))
            lo, hi = max(0., progress-1.5*delta), min(limit, progress+1.5*delta)
            # Both ends index segments, not vertices. At the finish (lo == limit)
            # bisect_right returns the last vertex, so clamp as at() and `last` do.
            first = min(limit_segment, max(0, bisect.bisect_right(ext_arcs, lo)-1))
            last = min(limit_segment, bisect.bisect_left(ext_arcs, hi))
            candidates = []
            for i in range(first, last+1):
                length = ext_arcs[i+1]-ext_arcs[i]
                lower, upper = max(0., (lo-ext_arcs[i])/length), min(1., (hi-ext_arcs[i])/length)
                if lower > upper:
                    continue
                t = sum((b[k+1]-ext_points[i][k])*(ext_points[i+1][k]-ext_points[i][k])
                        for k in range(2))/length**2
                t = max(lower, min(upper, t))
                arc = ext_arcs[i]+t*length
                if i <= last_segment:
                    p, _, width = at(arc)
                else:
                    p = tuple(ext_points[i][k]+t*(ext_points[i+1][k]-ext_points[i][k]) for k in range(2))
                    marked = raw[i]['painted'] and raw[i+1]['painted']
                    width = (ext_widths[i]+t*(ext_widths[i+1]-ext_widths[i]) if marked
                             else open_area_lateral_m)
                candidates.append((math.dist(b[1:3], p), abs(arc-progress), arc, width))
            if not candidates:
                # Fail closed with an explicit reason rather than an opaque exception.
                raise ValueError(f'No reachable WORLD projection at sample {index}')
            lateral, _, progress, width = min(candidates)
            if lateral > width+.001:
                raise ValueError(f'Outside ordered WORLD corridor at sample {index}')
            maximum = max(maximum, progress)
            # Only actual positive segment crossings count, including lateral
            # distance at the crossing. Ordered gates cannot be visited in bulk
            # merely by projecting to a distant course branch.
            while visited < len(gates):
                arc, p, tangent, gate_width = gates[visited]
                before = sum((a[k+1]-p[k])*tangent[k] for k in range(2))
                after = sum((b[k+1]-p[k])*tangent[k] for k in range(2))
                if not before <= 0 < after or abs(arc-progress) > 1.5*delta+gate_spacing_m:
                    break
                f = -before/(after-before)
                crossing = tuple(a[k+1]+f*(b[k+1]-a[k+1]) for k in range(2))
                if math.dist(crossing, p) > gate_width+.001:
                    break
                visited += 1
                if visited == len(gates):
                    completed = index
            result.update(gates_visited=visited, progress_m=progress, maximum_progress_m=maximum,
                          last_sample_index=index, last_lateral_m=lateral)
        if finish_crossing:
            # No final-arc or endpoint proximity: the later crossing replaces both.
            result.update(gates_completed_sample_index=completed,
                          crossing_previous_sample_index=crossing_index)
            result['passed'] = (visited == len(gates) and completed is not None
                                and crossing_index is not None and crossing_index >= completed)
            if not result['passed']:
                result['reason'] = ('Missing ordered cross-section visits or no accepted finish '
                                    'crossing after the final gate')
        else:
            result['passed'] = (visited == len(gates) and progress >= total-.4
                                and math.dist(samples[-1][1:3], points[0]) <= .4)
            if not result['passed']:
                result['reason'] = 'Incomplete ordered WORLD loop or missing physical cross-section visits'
    except (ValueError, KeyError, TypeError) as error:
        result['reason'] = str(error)
    return result


def ramp_body_evidence(samples, ramp):
    try:
        return _ramp_body_evidence(samples, ramp)
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        return dict(passed=False, ramp_id=ramp.get('id'), reason=str(error))


def _ramp_body_evidence(samples, ramp):
    """Conservative XY side containment where the body overlaps the finite ramp.

    The rectangle is axle-relative. It is not a physical wheel-support polygon.
    """
    if (len(samples) < 2 or any(len(row) != 4 or not all(math.isfinite(v) for v in row)
                               for row in samples)):
        raise ValueError('Invalid ramp trajectory')
    if any(not 0 < b[0]-a[0] <= .5 for a,b in zip(samples,samples[1:])):
        raise ValueError('Sampling gap or nonincreasing timestamps')
    length = 2*ramp['rise_length']+ramp['deck_length']
    if not all(math.isfinite(ramp[key]) for key in
               ('x','y','yaw','width','rise_length','deck_length')) or length <= 0 or ramp['width'] <= 0:
        raise ValueError('Invalid ramp geometry')
    c, s = math.cos(ramp['yaw']), math.sin(ramp['yaw'])

    def portion(poly, low, high):
        # Clip only longitudinally: a side-overhanging point must remain in the
        # polygon so it can fail containment, rather than be clipped away.
        for boundary, lower in ((low,True),(high,False)):
            clipped = []
            for a,b in zip(poly,poly[1:]+poly[:1]):
                inside_a = a[0] >= boundary if lower else a[0] <= boundary
                inside_b = b[0] >= boundary if lower else b[0] <= boundary
                if inside_a:
                    clipped.append(a)
                if inside_a != inside_b:
                    fraction = (boundary-a[0])/(b[0]-a[0])
                    clipped.append((boundary,a[1]+fraction*(b[1]-a[1])))
            poly = clipped
        return poly

    started = False
    entry = None
    previous = None
    minimum_margin = math.inf
    for index, pose, step in interpolated(samples):
        poly = box(*pose, *FOOTPRINT)
        local = [(c*(x-ramp['x'])+s*(y-ramp['y']), -s*(x-ramp['x'])+c*(y-ramp['y'])) for x, y in poly]
        low, high = min(p[0] for p in local), max(p[0] for p in local)
        if high < 0 and entry is None:
            started = True
        if not started:
            previous = local
            continue
        # Any point between these two poses is within step/2 of its nearest
        # endpoint counterpart. If it overlaps the real ramp, that counterpart
        # lies in this expanded longitudinal slab; its lateral error is also
        # at most step/2. Check both endpoints, including before first entry.
        allowance = step/2
        candidates = [point for endpoint in (previous,local) if endpoint is not None
                      for point in portion(endpoint,-allowance,length+allowance)]
        # Earlier portions of the loop can cross this longitudinal stripe far
        # from the finite ramp. Until actual entry, require possible lateral
        # overlap as well; once entered, every overhanging side point matters.
        possible_overlap = candidates and (
            min(p[1] for p in candidates) <= ramp['width']/2+allowance and
            max(p[1] for p in candidates) >= -ramp['width']/2-allowance)
        actual = portion(local,0.,length)
        if entry is None and actual and (min(p[1] for p in actual) <= ramp['width']/2
                                       and max(p[1] for p in actual) >= -ramp['width']/2):
            entry = index
        if candidates and (entry is not None or possible_overlap):
            bound = ramp['width']/2-max(abs(p[1]) for p in candidates)-allowance
            minimum_margin = min(minimum_margin,bound)
            if bound <= 0:
                return dict(passed=False, ramp_id=ramp.get('id'), reason='Body-side containment unproven',
                            trajectory_index=index, conservative_side_margin_m=minimum_margin)
        if entry is not None and low > length:
            return dict(passed=True, ramp_id=ramp.get('id'), entry_trajectory_index=entry,
                        exit_trajectory_index=index, conservative_side_margin_m=minimum_margin)
        previous = local
    return dict(passed=False, ramp_id=ramp.get('id'), reason='No complete body entry and departure')
