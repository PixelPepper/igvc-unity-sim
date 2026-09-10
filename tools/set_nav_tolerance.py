"""Bounded service client; avoid cached ROS CLI graph during long sessions."""
import rclpy
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType
rclpy.init();node=rclpy.create_node('igvc_set_nav_tolerance')
client=node.create_client(SetParameters,'/controller_server/set_parameters')
try:
    if not client.wait_for_service(timeout_sec=5):raise RuntimeError('Parameter service unavailable')
    request=SetParameters.Request(parameters=[Parameter(name='goal_checker.xy_goal_tolerance',value=ParameterValue(type=ParameterType.PARAMETER_DOUBLE,double_value=.3))])
    future=client.call_async(request);rclpy.spin_until_future_complete(node,future,timeout_sec=8)
    if not future.done():raise RuntimeError('Parameter update timeout')
    result=future.result();print(result)
    if not all(p.successful for p in result.results):raise RuntimeError('Parameter update rejected')
finally:node.destroy_node();rclpy.shutdown()
