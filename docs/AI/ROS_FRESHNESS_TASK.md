# Shared ROS update stalls: investigation packet

Resolved and validated: a backward system-clock correction delayed default ROS timers while monotonic freshness checks continued. `timer-clocks.json` measured a .942 s default timer gap versus .0524 s steady timer gap during the same correction. Bridge, lane and depth periodic work now explicitly uses STEADY_TIME. Both perception-loss watchdog tests pass with thresholds unchanged. Fresh seed2027 completed all78 checkpoints with no pauses, recoveries or guard blocks; clearance and speed audits passed. Concurrent60s paired timing captured two more clock corrections: default timer gap1.0113s, steady.0543s. See [timing evidence](../ROS_TIMING.md). The original packet below records the failing baseline and must not be read as the current session state.

Read README.md and this packet first. Latest terrain-depth regression is paused at checkpoint 17/78, Unity course seed2027/normal and RViz are open. The live mission observer remains active; use `tools/igvc.ps1 loop-cancel` before stopping or rebuilding. Do not repeatedly rearm autonomy to accumulate a nominal pass.

## Evidence

- `artifacts/checks/ground-course-health-resumed.json`: 100 s independent receipt-time observation; max lane/depth gaps ~1.15 s, autonomy-state gap ~1.00 s. All 477 depth statuses valid. At gate falling edge, depth last-positive age .809 s; lane had just recovered. Independent callback ordering does not establish cause.
- `artifacts/checks/ground-course-health.json`: earlier stop with both positive ages ~.78 s.
- `artifacts/checks/ground-depth-live.json`: final exact-TF selector passes all12 live geometry/rate checks in a stationary30 s window.
- `artifacts/courses/seed-2027/run.json`: three watchdog pauses, two explicit same-checkpoint resumes, no reset, no guard blocks. Current validation is correctly incomplete.
- `artifacts/courses/seed-2027/previous-20260909T155710805753Z/`: earlier terrain-estimator78/78 pass before the depth TF-selection race fix. Do not overwrite archived evidence.
- `artifacts/logs/nav-session.log`: missed control cycles around stops. Endpoint/lane/depth CPU averages were modest at inspection; no established CPU saturation cause.

## Investigation and ownership

Integrator alone controls simulator/ROS launches. Use the read-only bounded `tools/observe_perception_health.py --duration 100 --report PATH` for health evidence. Correlate same-host monotonic scheduling delays, ROS receipt gaps, Unity acquisition stamps and transport queue age. Separate host/WSL scheduling stalls from image decoding, ROS executor work and DDS delivery. Inspect runtime timing before changing parameters. RGB lane node still shows occasional future-TF races; distinguish those from the larger simultaneous update gaps.

Keep .75 s perception expiry, .5 s pair freshness, acquisition-time TF, drive orientation and full-loop order intact. No guessed latest-TF fallback, cached-health renewal, automatic rearming, obstacle clearance weakening or speed-cap increases. Do not kill unrelated Windows/WSL processes or disable unrelated services to obtain a pass.

## Acceptance / stop condition

Identify and address a measured cause; verify the affected behavior and one fresh normal-seed full loop with no unsolicited watchdog stops, all78 physical checkpoints, unchanged speed/clearance/no-reset/paint audits. Then update current evidence links and historical comparison language. If stalls prove external and cannot be resolved within the project, leave the robot stopped and report the remaining cause/evidence precisely. Do not call ideal planar fixture success complete ramp autonomy: RGB projection still assumes Z=0 and there is no body contact physics.
