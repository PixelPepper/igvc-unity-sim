#!/usr/bin/env python3
"""Bounded read-only wall-time health observer; never commands the simulator."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


class HealthObserver(Node):
    def __init__(self):
        super().__init__('igvc_perception_health_observer')
        self.started=time.monotonic()
        self.wall_started=time.time()
        self.streams={}
        self.negative_reasons={}
        self.status_errors=Counter()
        self.autonomy=None
        self.falling_edges=[]
        for key,topic in (
                ('lanes_valid','/perception/lanes/valid'),
                ('lanes_healthy','/perception/lanes/healthy'),
                ('depth_healthy','/perception/depth/healthy'),
                ('autonomy_enabled','/sim/autonomy_enabled')):
            self.streams[key]=self.empty_stream(topic)
            self.create_subscription(Bool,topic,lambda msg,k=key:self.boolean(k,msg),50)
        for key,topic in (('lanes_status','/perception/lanes/status'),
                          ('depth_status','/perception/depth/status')):
            self.streams[key]=self.empty_stream(topic)
            self.negative_reasons[key]=Counter()
            self.create_subscription(String,topic,lambda msg,k=key:self.status(k,msg),50)

    @staticmethod
    def empty_stream(topic):
        return dict(topic=topic,count=0,positive_count=0,negative_count=0,
                    first_update=None,last_update=None,last_positive=None,
                    max_positive_gap_s=None,max_update_gap_s=None,last_value=None,
                    last_negative_reason=None,last_status=None)

    def receive(self,key,positive):
        now=time.monotonic();s=self.streams[key]
        s['count']+=1
        if s['first_update'] is None:s['first_update']=now
        if s['last_update'] is not None:
            gap=now-s['last_update']
            s['max_update_gap_s']=max(s['max_update_gap_s'] or 0.,gap)
        s['last_update']=now;s['last_value']=positive
        if positive:
            s['positive_count']+=1
            if s['last_positive'] is not None:
                gap=now-s['last_positive']
                s['max_positive_gap_s']=max(s['max_positive_gap_s'] or 0.,gap)
            s['last_positive']=now
        else:s['negative_count']+=1
        return now

    def ages(self,now):
        return {key:dict(last_positive_age_s=None if s['last_positive'] is None else now-s['last_positive'],
                         last_update_age_s=None if s['last_update'] is None else now-s['last_update'],
                         last_value=s['last_value'],last_negative_reason=s['last_negative_reason'])
                for key,s in self.streams.items()}

    def boolean(self,key,msg):
        now=self.receive(key,bool(msg.data))
        if key=='autonomy_enabled':
            # An initial false is observed state, not a witnessed falling edge.
            if self.autonomy is True and not msg.data:
                self.falling_edges.append(dict(elapsed_wall_s=now-self.started,
                    unix_wall_s=time.time(),streams=self.ages(now),
                    recent_status={k:self.streams[k]['last_status'] for k in self.negative_reasons}))
            self.autonomy=bool(msg.data)

    def status(self,key,msg):
        try:
            value=json.loads(msg.data)
            if not isinstance(value,dict) or not isinstance(value.get('valid'),bool):
                raise ValueError('Status must be an object with boolean valid')
        except (ValueError,TypeError):
            self.status_errors[key]+=1
            self.receive(key,False)
            self.negative_reasons[key]['invalid_json_or_missing_valid']+=1
            self.streams[key]['last_negative_reason']='invalid_json_or_missing_valid'
            return
        self.receive(key,value['valid'])
        self.streams[key]['last_status']=value
        if not value['valid']:
            reason=str(value.get('reason','unspecified'))
            self.negative_reasons[key][reason]+=1
            self.streams[key]['last_negative_reason']=reason

    def report(self):
        now=time.monotonic();streams={}
        for key,s in self.streams.items():
            streams[key]={k:v for k,v in s.items() if k not in ('first_update','last_update','last_positive')}
            streams[key].update(self.ages(now)[key])
            streams[key]['first_update_elapsed_s']=None if s['first_update'] is None else s['first_update']-self.started
            streams[key]['last_positive_elapsed_s']=None if s['last_positive'] is None else s['last_positive']-self.started
            # Unlike completed positive-to-positive gaps, this includes a final outage.
            tail=None if s['last_positive'] is None else now-s['last_positive']
            streams[key]['max_positive_gap_including_open_tail_s']=(
                max(s['max_positive_gap_s'] or 0.,tail) if tail is not None else None)
        return dict(started_unix_wall_s=self.wall_started,duration_wall_s=now-self.started,
                    streams=streams,negative_status_reasons={k:dict(v) for k,v in self.negative_reasons.items()},
                    invalid_status_counts=dict(self.status_errors),autonomy_falling_edges=self.falling_edges,
                    autonomy_falling_edge_count=len(self.falling_edges),
                    limitations='Read-only receipt-time diagnostics, not simulation/acquisition time or causal proof. '
                        'Independent subscriptions can deliver status and gate transitions in different orders. '
                        'Initial autonomy=false is not a falling edge; pre-observation history is unknown. '
                        'Null positive gaps mean fewer than two positive updates, not zero delay. '
                        'This observer does not declare mission success or change watchdog policy.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=float,default=30)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if not math.isfinite(args.duration) or not 10<=args.duration<=180:
        parser.error('duration must be 10..180 wall seconds')
    rclpy.init();node=HealthObserver()
    try:
        deadline=time.monotonic()+args.duration
        while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.05)
    except KeyboardInterrupt:
        pass
    finally:
        report=node.report()
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(report=str(args.report),duration_wall_s=report['duration_wall_s'],
                             autonomy_falling_edge_count=report['autonomy_falling_edge_count'],
                             stream_counts={k:v['count'] for k,v in report['streams'].items()}),indent=2))
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
