"""Read-only Nav2 footprint-edge diagnostics against a live raw costmap."""
import json
import math
from pathlib import Path
import struct
import time
from types import SimpleNamespace

import rclpy
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from nav_msgs.msg import Odometry
from nav2_msgs.msg import Costmap
from geometry_msgs.msg import PolygonStamped
from sensor_msgs.msg import PointCloud2

ROOT = Path(__file__).resolve().parents[1]


def raster(x, y, ex, ey):
    """Nav2 jazzy LineIterator integer stepping, including both endpoints."""
    dx, dy = abs(ex-x), abs(ey-y)
    sx, sy = (1 if ex >= x else -1), (1 if ey >= y else -1)
    if dx >= dy:
        ix1, iy1, ix2, iy2, den, num, add, count = 0, sy, sx, 0, dx, dx//2, dy, dx
    else:
        ix1, iy1, ix2, iy2, den, num, add, count = sx, 0, 0, sy, dy, dy//2, dx, dy
    for _ in range(count+1):
        yield x, y
        num += add
        if num >= den:
            num -= den
            x += ix1
            y += iy1
        x += ix2
        y += iy2


def main():
    rclpy.init()
    node = rclpy.create_node('igvc_readonly_costmap_diagnosis')
    data = {}
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    for kind, topic, key, profile in (
        (Costmap, '/local_costmap/costmap_raw', 'map', qos),
        (PolygonStamped, '/local_costmap/published_footprint', 'foot', 10),
        (Odometry, '/odom', 'odom', 10),
        (PointCloud2, '/perception/lanes/points', 'cloud', qos_profile_sensor_data)):
        node.create_subscription(kind, topic, lambda m, k=key: data.update({k: m}), profile)
    deadline = time.monotonic()+5
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.1)
    node.destroy_node()
    rclpy.shutdown()
    if not {'map', 'foot'} <= data.keys():
        raise RuntimeError('Missing streams: '+str(data.keys()))
    m = data['map']
    foot = [(v.x, v.y) for v in data['foot'].polygon.points]
    if 'odom' in data:
        odom = data['odom']
        p, q = odom.pose.pose.position, odom.pose.pose.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        pose_source = 'live_odometry'
    else:
        yaw = math.atan2(foot[0][1]-foot[1][1], foot[0][0]-foot[1][0])
        p = SimpleNamespace(x=foot[0][0]-.61*math.cos(yaw)+.51*math.sin(yaw),
                            y=foot[0][1]-.61*math.sin(yaw)-.51*math.cos(yaw))
        pose_source = 'inferred_from_published_footprint_assuming_0.01_padding'
    res = m.metadata.resolution
    ox, oy = m.metadata.origin.position.x, m.metadata.origin.position.y
    width, height = m.metadata.size_x, m.metadata.size_y
    if m.header.frame_id != 'odom' or data['foot'].header.frame_id != 'odom':
        raise ValueError('Expected odom costmap and footprint')
    cloud = data.get('cloud')
    lanes = [] if cloud is None else [struct.unpack_from('<fff', cloud.data, i)[:2]
                                     for i in range(0, len(cloud.data), cloud.point_step)]
    barrels = [b['xy'] for b in json.loads((ROOT/'artifacts/checks/course-route.json').read_text())['barrel_instances']]

    def score(dx, dy, da=0.):
        c, s = math.cos(da), math.sin(da)
        transformed = [(p.x+dx+c*(x-p.x)-s*(y-p.y), p.y+dy+s*(x-p.x)+c*(y-p.y)) for x, y in foot]
        cells = [(int((x-ox)/res), int((y-oy)/res)) for x, y in transformed]
        maximum, bad = 0, None
        for edge, (start, end) in enumerate(list(zip(cells, cells[1:]))+[(cells[0], cells[-1])]):
            linecost = 0
            for cx, cy in raster(*start, *end):
                val = int(m.data[cy*width+cx]) if 0 <= cx < width and 0 <= cy < height else 254
                if val >= 254 and bad is None:
                    wx, wy = ox+(cx+.5)*res, oy+(cy+.5)*res
                    nearest = min(range(len(barrels)), key=lambda i: math.dist((wx, wy), barrels[i]))
                    bad = dict(cell=[cx, cy], world=[wx, wy], raw_cost=val, edge=edge,
                               nearest_lane_m=min((math.dist((wx, wy), xy) for xy in lanes), default=None),
                               nearest_barrel=nearest, barrel_xy=barrels[nearest],
                               barrel_surface_distance_m=math.dist((wx, wy), barrels[nearest])-.2682114)
                if val == 254:
                    linecost = 254
                    break
                linecost = max(linecost, val)
            maximum = max(maximum, linecost)
            if maximum == 254:
                break
        return dict(cost=maximum, first_bad=bad)

    mission = json.loads((ROOT/'ros2/src/igvc_gps/config/full_loop.json').read_text())
    goal = mission['waypoints'][43]['odom_xy']
    bearing = math.atan2(goal[1]-p.y, goal[0]-p.x)
    paths = {}
    for name, angle, sign in [('approach_goal_fixed_heading', bearing, 1),
                              ('forward_current_heading', yaw, 1),
                              ('reverse_current_heading', yaw, -1)]:
        rows = [dict(distance_m=i*.01, **score(sign*i*.01*math.cos(angle), sign*i*.01*math.sin(angle)))
                for i in range(61)]
        paths[name] = dict(first_block=next((r for r in rows if r['cost'] >= 254), None),
                           max_cost=max(r['cost'] for r in rows), samples=rows)
    for name, target in [('rotate_to_goal_bearing', bearing),
                         ('rotate_to_goal_final_yaw', mission['waypoints'][43]['yaw'])]:
        change = math.atan2(math.sin(target-yaw), math.cos(target-yaw))
        rows = [dict(yaw=yaw+change*i/200, **score(0, 0, change*i/200)) for i in range(201)]
        paths[name] = dict(first_block=next((r for r in rows if r['cost'] >= 254), None),
                           max_cost=max(r['cost'] for r in rows), samples=rows)
    report = dict(pose=[p.x, p.y, yaw], pose_source=pose_source, footprint=foot, resolution=res,
                  current=score(0, 0), paths=paths,
                  limitation='Static captured map; translation paths hold current footprint orientation, not an RPP trajectory.')
    output = ROOT/'artifacts/checks/course-costmap-diagnosis.json'
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps({**{k: report[k] for k in ('pose', 'pose_source', 'resolution', 'current')},
                      'paths': {k: v['first_block'] for k, v in paths.items()}}, indent=2))


if __name__ == '__main__':
    main()
