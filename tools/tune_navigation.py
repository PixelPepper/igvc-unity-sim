"""Apply the checked-in navigation tuning live with bounded, verified ROS RPCs."""
import argparse
import json
from pathlib import Path
import rclpy
from rcl_interfaces.srv import SetParameters, GetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--speed',type=float,default=1.)
    args=parser.parse_args()
    if not 0<args.speed<=2.2:parser.error('Requested speed must be in (0,2.2] m/s')
    groups={
        '/controller_server':{'goal_checker.xy_goal_tolerance':.3,'FollowPath.desired_linear_vel':args.speed,
            'FollowPath.approach_velocity_scaling_dist':2.0,
            'FollowPath.lookahead_dist':1.5,'FollowPath.use_velocity_scaled_lookahead_dist':False,
            'FollowPath.rotate_to_heading_min_angle':.6,'FollowPath.cost_scaling_dist':.65,
            'FollowPath.inflation_cost_scaling_factor':5.,'FollowPath.regulated_linear_scaling_min_radius':1.5},
        '/global_costmap/global_costmap':{'inflation_layer.inflation_radius':.75,'inflation_layer.cost_scaling_factor':5.,'footprint_padding':.02},
        '/local_costmap/local_costmap':{'inflation_layer.inflation_radius':.75,'inflation_layer.cost_scaling_factor':5.,'footprint_padding':.02,'resolution':.05}}
    rclpy.init();node=rclpy.create_node('igvc_live_navigation_tuning');report={}
    try:
        for target,values in groups.items():
            client=node.create_client(SetParameters,target+'/set_parameters')
            if not client.wait_for_service(timeout_sec=5):raise RuntimeError(target+' unavailable')
            params=[]
            for name,value in values.items():
                p=ParameterValue(type=ParameterType.PARAMETER_BOOL,bool_value=value) if isinstance(value,bool) else ParameterValue(type=ParameterType.PARAMETER_DOUBLE,double_value=float(value))
                params.append(Parameter(name=name,value=p))
            future=client.call_async(SetParameters.Request(parameters=params))
            rclpy.spin_until_future_complete(node,future,timeout_sec=8)
            if not future.done() or not all(r.successful for r in future.result().results):raise RuntimeError(target+' update rejected/timeout')
            reader=node.create_client(GetParameters,target+'/get_parameters')
            if not reader.wait_for_service(timeout_sec=5):raise RuntimeError('Readback unavailable')
            future=reader.call_async(GetParameters.Request(names=list(values)))
            rclpy.spin_until_future_complete(node,future,timeout_sec=8)
            if not future.done():raise RuntimeError('Readback timeout')
            actual={name:(v.bool_value if isinstance(values[name],bool) else v.double_value) for name,v in zip(values,future.result().values)}
            if actual!=values:raise RuntimeError('Readback mismatch '+target)
            report[target]=actual
        print(json.dumps(report,indent=2))
        (Path(__file__).resolve().parents[1]/'artifacts/checks/navigation-tuning.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:node.destroy_node();rclpy.shutdown()

if __name__=='__main__':main()
