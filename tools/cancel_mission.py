"""Bounded cancellation of this workspace's mission observer, including idle use."""
import time
import fcntl
from pathlib import Path
import rclpy
from std_srvs.srv import Trigger


def main():
    rclpy.init()
    node = rclpy.create_node('igvc_cancel_mission')
    try:
        client = node.create_client(Trigger, '/mission/cancel')
        if not client.wait_for_service(timeout_sec=2.):
            print('No active mission cancellation service')
        else:
            future = client.call_async(Trigger.Request())
            rclpy.spin_until_future_complete(node, future, timeout_sec=5.)
            if not future.done() or future.exception():
                raise RuntimeError('Mission cancellation did not respond within five seconds')
            response = future.result()
            if not response.success:
                raise RuntimeError(response.message)
            print(response.message)
        lock_path = Path(__file__).resolve().parents[1]/'artifacts/session/full-course.lock'
        if lock_path.exists():
            with lock_path.open('r') as lock:
                deadline = time.monotonic()+10.
                while True:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            raise RuntimeError('Previous mission has not released its workspace lock')
                        time.sleep(.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
