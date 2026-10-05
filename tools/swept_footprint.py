"""Conservative directed sweeps for a rectangle moving on a constant-curvature arc."""
import math


def arc_sweep_box(start, end, footprint):
    """Return x,y,yaw,bounds enclosing the complete short-arc body sweep.

    Each corner follows a circle about the same instantaneous turn centre.
    Its arc deviates from its endpoint chord by at most (R + corner_radius)
    times the angle's sagitta factor. The midpoint-oriented box contains every
    endpoint corner and therefore their convex hull; that small extra margin
    encloses the continuous arc. For a straight interval, the union is exact.
    Inputs must describe one constant-curvature forward or backward primitive.
    """
    turn = math.atan2(math.sin(end[2]-start[2]), math.cos(end[2]-start[2]))
    if abs(turn) > math.pi/2:
        raise ValueError('Split sweep into short arc intervals')
    yaw = start[2]+turn/2
    x,y = (start[0]+end[0])/2,(start[1]+end[1])/2
    c,s = math.cos(yaw),math.sin(yaw)
    corners=[]
    for px,py,angle in (start,end):
        ca,sa=math.cos(angle),math.sin(angle)
        for bx in footprint[:2]:
            for by in footprint[2:]:
                dx,dy=px+ca*bx-sa*by-x,py+sa*bx+ca*by-y
                corners.append((c*dx+s*dy,-s*dx+c*dy))
    radius=math.hypot(max(abs(footprint[0]),abs(footprint[1])),
                      max(abs(footprint[2]),abs(footprint[3])))
    # 1-cos(a) expressed through sin avoids cancellation on tiny intervals.
    margin=(math.dist(start[:2],end[:2])/2*math.tan(abs(turn)/4)
            +2*radius*math.sin(turn/4)**2)
    return x,y,yaw,(min(p[0] for p in corners)-margin,max(p[0] for p in corners)+margin,
                     min(p[1] for p in corners)-margin,max(p[1] for p in corners)+margin)
