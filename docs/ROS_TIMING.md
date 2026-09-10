# ROS timer clock correction

The bridge and perception nodes now schedule their periodic work with explicit `rclpy` `STEADY_TIME` clocks. This fixes a clock-domain mismatch: default node timers followed system time, while freshness expiry used monotonic elapsed time. A backward system-clock correction could delay a processing callback long enough for otherwise active perception to expire and latch manual mode.

The [scheduler baseline](../artifacts/checks/scheduler-clock-baseline.json) observed approximately a 0.946 s backward correction: realtime advanced by -0.9256 s while monotonic time advanced by 0.0202 s. Its largest monotonic sampling gap was 0.0290 s. A separate [paired timer observation](../artifacts/checks/timer-clocks.json) measured a 0.8923 s backward correction. During that 30 s observation, two nominal 50 ms timers sharing one executor behaved differently:

| Timer clock | Callbacks | Largest monotonic callback gap |
| --- | ---: | ---: |
| Default node clock | 582 | 0.9420 s |
| Explicit steady clock | 600 | 0.0524 s |

The independent sampling thread and executor loop remained active, with maximum gaps of 0.0332 s and 0.0299 s respectively. This supports a timer clock correction cause for that observation; it does not prove that scheduling stalls can never occur. Both samplers share the process and Python GIL.

The changed timers are `probe_adapter.py` at 50 ms, and `lane_node.py` and `depth_node.py` at 200 ms. Acquisition timestamps, simulation `/clock`, and stamped TF lookup retain their existing semantics. Freshness thresholds remain unchanged, including the 0.75 s perception gate. No host or WSL clocks were changed, and stale-data protection was not relaxed.

Both the [lane watchdog](../artifacts/checks/lane-watchdog-live.json) and [depth watchdog](../artifacts/checks/depth-watchdog-live.json) passed: fresh perception permits enable, stale perception latches manual, and recovered data does not automatically rearm. The timer-fix [seed-2027 course run](../artifacts/courses/seed-2027/previous-20260909T164059627191Z/run.json) completed all 78 checkpoints without pause events, recoveries or line-guard blocks; its [geometric audit](../artifacts/courses/seed-2027/previous-20260909T164059627191Z/validation.json) passed. This establishes a completed ideal fixture run, not physics or general terrain fidelity.

A second [60-second paired-clock observation during the course](../artifacts/checks/timer-clocks-course.json) captured two backward clock corrections. The default timer's maximum gap was 1.0113 s (1,162 callbacks); the steady timer held a maximum 0.0543 s gap (1,200 callbacks). The [120-second health capture](../artifacts/checks/steady-course-health.json) received 581 depth-health updates, all true, with a maximum 0.2092 s gap. Lane updates continued with a maximum 0.2318 s gap. The 8.40 s gap between positive lane detections belongs to the declared unmarked connector; positive camera-health updates had a maximum 0.4016 s gap, including two transient TF misses. Three autonomy falling edges matched the designed zone stops and final completion, with fresh perception at each, rather than watchdog pauses. Receipt-time diagnostics alone do not establish causality; this interpretation also uses the completed mission's event history.

To observe both clocks without publishing commands or changing clocks, run from the repository root in PowerShell:

```powershell
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/observe_timer_clocks.py --duration 30 --report artifacts/checks/timer-clocks-repeat.json
```

The utility records callback intervals using monotonic time, realtime-minus-monotonic offset changes, clock-read uncertainty, and independent thread/executor intervals. A run without a naturally occurring clock correction does not reproduce the failure by itself.
