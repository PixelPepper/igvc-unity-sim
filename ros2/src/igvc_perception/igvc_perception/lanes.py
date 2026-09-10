"""Image geometry and ground projection without simulator/course dependencies."""
import cv2
import numpy as np


def lane_pixels(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, (0, 0, 220), (179, 50, 255))
    orange = cv2.inRange(hsv, (0, 100, 70), (28, 255, 255)) > 0
    above, below = np.zeros_like(orange), np.zeros_like(orange)
    for distance in range(1, 25):
        above[distance:] |= orange[:-distance]
        below[:-distance] |= orange[distance:]
    # Remove the band itself, not the whole connected component: lane paint
    # can touch a barrel's white stripe in the camera image.
    barrel_band = cv2.dilate((above & below).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    mask[barrel_band] = 0
    # Downward camera pitch lifts distant ground paint above the image midpoint.
    # Acquisition-time ray/plane projection rejects remaining sky/horizon pixels.
    mask[:int(rgb.shape[0]*.40)] = 0
    # Opening erases one-pixel antialiased distant paint. Keep its continuity;
    # component area, shape and orange-context checks below reject noise.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    mask[barrel_band] = 0
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    accepted = np.zeros_like(mask)
    components = 0
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] < 60:
            continue
        y, x = np.nonzero(labels == index)
        points = np.column_stack((x, y)).astype(np.float32)
        center = points.mean(axis=0)
        _, _, axes = np.linalg.svd(points-center, full_matrices=False)
        extent = np.ptp((points-center) @ axes.T, axis=0) + 1
        # A turning lane can be almost horizontal or globally crescent-shaped.
        left, top, width, height, area = stats[index]
        local = (labels[top:top+height, left:left+width] == index).astype(np.uint8)
        thickness = 2 * cv2.distanceTransform(np.pad(local, 1), cv2.DIST_L2, 5).max()
        curved_thin = (extent[0] >= 60 and extent[0]/max(thickness, 1) >= 4
                       and area/(width*height) < .45)
        if extent[0] < 30 or (extent[0]/extent[1] < 3.5 and not curved_thin):
            continue
        accepted[labels == index] = 255
        components += 1
    y, x = np.nonzero(accepted)
    # Bound projection cost while retaining paint boundaries.
    stride = max(1, len(x)//3000)
    return np.column_stack((x[::stride], y[::stride])), accepted, components


def rotation_matrix(quaternion):
    x, y, z, w = quaternion
    length = np.linalg.norm(quaternion)
    if not np.isfinite(length) or abs(length-1) > .01:
        raise ValueError('Invalid TF quaternion')
    x, y, z, w = np.array([x, y, z, w])/length
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def project_ground(pixels, k, rotation, origin, ground_z=0., minimum=1., maximum=10.):
    k = np.asarray(k, dtype=float).reshape(3, 3)
    origin = np.asarray(origin, dtype=float)
    if not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0:
        raise ValueError('Invalid camera intrinsics')
    rays = np.column_stack((pixels, np.ones(len(pixels)))) @ np.linalg.inv(k).T
    rays = rays @ np.asarray(rotation).T
    dz = rays[:, 2]
    valid = np.isfinite(rays).all(axis=1) & (dz < -1e-5) & (origin[2] > ground_z)
    scale = np.zeros(len(rays))
    scale[valid] = (ground_z-origin[2])/dz[valid]
    points = origin + rays*scale[:, None]
    distance = np.linalg.norm(points[:, :2]-origin[:2], axis=1)
    valid &= (scale > 0) & (distance >= minimum) & (distance <= maximum)
    return points[valid].astype(np.float32)
