"""Terminal goal/cancel interface. Goals are metres/radians in the odom frame."""
import argparse
import math
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.signals import SignalHandlerOptions
from nav2_msgs.action import NavigateToPose
from action_msgs.srv import CancelGoal
from std_srvs.srv import SetBool


def wait(node, future, seconds):
    deadline = time.monotonic() + seconds
    while not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.1)
    if not future.done():
        raise RuntimeError('ROS operation timed out')
    return future.result()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['goal', 'cancel'])
    parser.add_argument('x', type=float, nargs='?', default=0.)
    parser.add_argument('y', type=float, nargs='?', default=0.)
    parser.add_argument('yaw', type=float, nargs='?', default=0.)
    args = parser.parse_args()
    if not all(math.isfinite(v) for v in (args.x, args.y, args.yaw)):
        parser.error('Goal must be finite')
    # Keep ROS alive while Python's KeyboardInterrupt runs the cancellation cleanup.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('igvc_terminal_navigation')
    gate = node.create_client(SetBool, '/sim/set_autonomy')
    cancel = node.create_client(CancelGoal, '/navigate_to_pose/_action/cancel_goal')
    cancel_through = node.create_client(CancelGoal, '/navigate_through_poses/_action/cancel_goal')
    client = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    enabled = False
    try:
        if not gate.wait_for_service(timeout_sec=5):
            raise RuntimeError('Simulator command gate unavailable; rebuild/restart the simulator ROS session')
        wait(node, gate.call_async(SetBool.Request(data=False)), 5)
        if cancel.wait_for_service(timeout_sec=3):
            wait(node, cancel.call_async(CancelGoal.Request()), 5)
        if cancel_through.wait_for_service(timeout_sec=1):
            wait(node, cancel_through.call_async(CancelGoal.Request()), 5)
        if args.action == 'cancel':
            print('Navigation canceled; manual mode selected')
            return
        if not client.wait_for_server(timeout_sec=30):
            raise RuntimeError('Nav2 unavailable; run nav-start and check its lifecycle log')
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'odom'
        # Zero stamp requests latest transform, independent of host clock skew.
        goal.pose.pose.position.x, goal.pose.pose.position.y = args.x, args.y
        goal.pose.pose.orientation.z = math.sin(args.yaw / 2)
        goal.pose.pose.orientation.w = math.cos(args.yaw / 2)
        handle = wait(node, client.send_goal_async(goal), 10)
        if not handle.accepted:
            raise RuntimeError('Nav2 rejected the goal')
        permission = wait(node, gate.call_async(SetBool.Request(data=True)), 5)
        if not permission.success:
            wait(node, handle.cancel_goal_async(), 5)
            raise RuntimeError(permission.message)
        enabled = True
        print(f'Navigating to odom ({args.x}, {args.y}), yaw {args.yaw}; Ctrl+C cancels', flush=True)
        result = wait(node, handle.get_result_async(), 180)
        print(f'Navigation result status={result.status} (4=succeeded, 5=canceled, 6=aborted)', flush=True)
        if result.status != 4:
            raise RuntimeError('Navigation did not succeed')
    finally:
        if rclpy.ok():
            if enabled:
                wait(node, gate.call_async(SetBool.Request(data=False)), 5)
                if cancel.service_is_ready():
                    wait(node, cancel.call_async(CancelGoal.Request()), 5)
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
