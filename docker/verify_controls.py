"""Bounded terminal velocity/timeout/E-stop check at a clear, stopped course origin."""
import json
import math
import time
from pathlib import Path
import rclpy
from geometry_msgs.msg import Twist
from igvc_sim_bridge.verify_probe import Verify


def main():
    rclpy.init()
    node = Verify('r3a')
    checks = {}
    try:
        deadline = time.monotonic() + 30
        while 'odom' not in node.last and time.monotonic() < deadline:
            node.wait(.2)
        assert 'odom' in node.last, 'No odometry within 30 seconds'
        start = node.xy()
        assert math.hypot(*start) < .5, 'Start at the clear course origin'
        node.wait(1, .3)
        distance = math.dist(start, node.xy())
        checks['velocity_command_moves_robot'] = .12 < distance < .5
        node.wait(.9)
        checks['command_expiration_stops'] = abs(node.last['odom'].twist.twist.linear.x) < .01
        node.service('estop', True)
        stopped = node.xy()
        node.wait(.7, .3)
        checks['estop_overrides_fresh_command'] = math.dist(stopped, node.xy()) < .01
        node.service('estop', False)
        node.wait(.6)
        checks['clear_estop_does_not_rearm'] = abs(node.last['odom'].twist.twist.linear.x) < .01
        result = dict(passed=all(checks.values()), checks=checks, distance_m=distance)
        Path('/opt/igvc/artifacts/checks/docker-controls.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    finally:
        node.pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
