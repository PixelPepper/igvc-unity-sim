"""Conservative dark-bowl fixture detector; not general negative-terrain perception."""
import cv2
import numpy as np


def hazard_pixels(rgb):
    """Return <=1500 XY image pixels, mono8 mask and accepted component count.

    Assumes the procedural fixture's dark bowls on brighter ground. Border
    components and saturated-color-adjacent patches are excluded. TF/range projection
    and expiry remain the caller's responsibility; shadows can still imitate holes.
    White-barrel dark rings have no color veto and may remain candidates;
    projecting to observed depth alone does not classify them as negative terrain.
    """
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError('Expected HxWx3 uint8 RGB image')
    height, width = rgb.shape[:2]
    if not height or not width:
        raise ValueError('Empty image')
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    dark = cv2.inRange(hsv, (0, 0, 0), (179, 100, 45))
    top_roi = int(height*.55)
    dark[:top_roi] = 0
    # Remove isolated pixel noise without bridging nearby text strokes.
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(dark)
    # Barrel shadows can accompany any saturated body hue. This contextual
    # veto is fixture-specific and cannot reject rings on white barrels.
    colored = cv2.inRange(hsv, (0, 100, 65), (179, 255, 255)) > 0
    accepted = np.zeros((height, width), np.uint8)
    components = 0
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        if area < 30 or area > .08*height*width:
            continue
        # Includes the artificial ROI edge: a truncated sky/robot silhouette
        # cannot become a standalone compact hazard by cropping it.
        if x <= 1 or x+w >= width-1 or y <= top_roi+1 or y+h >= height-1:
            continue
        if max(w, h)/min(w, h) > 6 or area/(w*h) < .45:
            continue
        pad = max(4, min(15, min(w, h)))
        context = colored[max(0, y-pad):min(height, y+h+pad), max(0, x-pad):min(width, x+w+pad)]
        if context.mean() > .08:
            continue
        component = (labels[y:y+h, x:x+w] == index).astype(np.uint8)
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = max(contours, key=cv2.contourArea)
        hull_area = cv2.contourArea(cv2.convexHull(contour))
        if hull_area <= 0 or cv2.contourArea(contour)/hull_area < .8:
            continue
        accepted[labels == index] = 255
        components += 1
    y, x = np.nonzero(accepted)
    stride = max(1, (len(x)+1499)//1500)
    return np.column_stack((x[::stride], y[::stride])), accepted, components
