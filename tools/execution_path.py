"""Convert a checked forward search path to controller-scale samples.

No shortcut/smoothing or map access: every output pose is an existing checked
pose, with its actual primitive orientation. Nav2 still checks live collisions.
"""
import math


def controller_path(plan, spacing=.05):
    points, yaws = plan['path'], plan['path_yaws']
    if (len(points) < 2 or len(points) != len(yaws) or not 0 < spacing <= .1
            or any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in points)
            or not all(math.isfinite(yaw) for yaw in yaws)):
        raise ValueError('Expected finite checked poses and matching primitive orientations')
    result = [(*points[0], yaws[0])]
    travelled = 0.
    for i in range(1, len(points)):
        segment = math.dist(points[i-1], points[i])
        if segment > .1:
            raise ValueError('Checked path has an unsupported gap')
        travelled += segment
        # Preserve a sharp change even if the path is extremely short.
        turn = abs(math.atan2(math.sin(yaws[i]-result[-1][2]), math.cos(yaws[i]-result[-1][2])))
        if travelled >= spacing or turn >= .08 or i == len(points)-1:
            result.append((*points[i], yaws[i]))
            travelled = 0.
    return result
