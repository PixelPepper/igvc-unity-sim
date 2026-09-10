#!/usr/bin/env python3
"""Correlate ROS timer gaps, host clock steps and Python scheduling; read-only."""
import argparse
import json
import math
from pathlib import Path
import threading
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node


class TimerProbe(Node):
    def __init__(self):
        super().__init__('igvc_timer_clock_observer')
        self.started=time.monotonic()
        self.callbacks={'default':[], 'steady':[]}
        self.steady_clock=Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.05,lambda:self.record('default'))
        self.create_timer(.05,lambda:self.record('steady'),clock=self.steady_clock)

    def record(self,key):
        mono=time.monotonic()
        self.callbacks[key].append(dict(elapsed_s=mono-self.started,monotonic_s=mono,
            realtime_s=time.time(),default_clock_ns=self.get_clock().now().nanoseconds))


def gap_summary(times):
    gaps=[b-a for a,b in zip(times,times[1:])]
    return dict(count=len(times),max_gap_s=max(gaps) if gaps else None,
                gaps_over_0_15s=[dict(from_elapsed_s=a,to_elapsed_s=b,gap_s=b-a)
                                 for a,b in zip(times,times[1:]) if b-a>.15])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=float,default=30.)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if not math.isfinite(args.duration) or not 5<=args.duration<=180:
        parser.error('duration must be 5..180 seconds')
    rclpy.init();node=TimerProbe();stop=threading.Event()
    thread_samples=[];executor_ticks=[]

    def sample_clocks():
        previous=None
        while not stop.is_set():
            before=time.monotonic();real=time.time();after=time.monotonic()
            midpoint=(before+after)/2
            offset=real-midpoint
            thread_samples.append(dict(elapsed_s=midpoint-node.started,monotonic_s=midpoint,
                realtime_s=real,realtime_minus_monotonic_s=offset,
                offset_change_s=None if previous is None else offset-previous,
                sample_bracket_s=after-before))
            previous=offset
            stop.wait(.02)

    worker=threading.Thread(target=sample_clocks,name='clock-offset-sampler',daemon=True)
    worker.start();interrupted=False
    try:
        deadline=node.started+args.duration
        while time.monotonic()<deadline:
            executor_ticks.append(time.monotonic()-node.started)
            rclpy.spin_once(node,timeout_sec=.02)
    except KeyboardInterrupt:
        interrupted=True
    finally:
        stop.set();worker.join(timeout=1.)
        elapsed=time.monotonic()-node.started
        callbacks={key:dict(gap_summary([r['elapsed_s'] for r in rows]),callbacks=rows,
                    last_callback_age_s=elapsed-rows[-1]['elapsed_s'] if rows else None)
                   for key,rows in node.callbacks.items()}
        offset_events=[r for r in thread_samples if r['offset_change_s'] is not None
                       and abs(r['offset_change_s'])>.005]
        report=dict(duration_wall_s=elapsed,interrupted=interrupted,
            default_clock_type=str(node.get_clock().clock_type),
            steady_clock_type=str(node.steady_clock.clock_type),timer_period_s=.05,
            timers=callbacks,clock_offset_samples=thread_samples,clock_offset_steps_over_5ms=offset_events,
            independent_thread_schedule=gap_summary([r['elapsed_s'] for r in thread_samples]),
            executor_spin_schedule=dict(gap_summary(executor_ticks),elapsed_ticks_s=executor_ticks),
            limitations='Default and steady timers share this node executor; the independent sampler is a Python thread '
                'in the same process and shares its GIL/OS scheduling. Its gaps are scheduling observations, not proof '
                'of host-wide starvation. Clock sample brackets expose timestamp-read uncertainty. No clocks are changed.')
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(report=str(args.report),duration_wall_s=elapsed,
            timer_counts={k:v['count'] for k,v in callbacks.items()},
            timer_max_gaps_s={k:v['max_gap_s'] for k,v in callbacks.items()},
            clock_offset_step_count=len(offset_events)),indent=2))
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
