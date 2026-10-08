---
id: T-0073
title: Bind simulator perception nodes to the simulation acquisition clock
status: ready
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0073-perception-clock-opus
base: 5346e60
candidate: none
claim: none
lease: none
updated: 2026-10-07
---

# Packet

SOLE HEADLESS owner opus-t0073-perception-clock-20261007, separate from INTERACTIVE
T0070 (still reserved). Worktree C:/Users/brand/.codex/worktrees/igvc-t0073-perception-clock/IGVC SIM.
This is a new launch-clock configuration task, NOT a retry of T0072 demo diagnosis.
The four relevant launch/node source files match HEAD; external dirty files excluded.

Read README intro, this packet, ros2/src/igvc_navigation/launch/local_navigation.launch.py,
ros2/src/igvc_perception/launch/perception.launch.py, and perception depth_node.py and
lane_node.py tick()/success_is_fresh(), plus test/test_processing_idle.py.
Both perception nodes compare self.get_clock().now() with simulation image stamps.
Both simulator launch entrypoints omit use_sim_time for lane_detector/depth_processor,
while local_navigation explicitly enables it for Nav2 and scan_ground_filter. Inspect
the actual source and fix the omission if confirmed; do not claim effective parameters
of a historical run are known. Existing clock-regression status counts versus zero
telemetry /clock resets motivate this check but do not prove the cause.

Own ONLY these two launch files and NEW
ros2/src/igvc_perception/test/test_simulation_clock_launch.py. No node policy edits,
dependencies, clocks/threshold changes, telemetry/auditor changes, primary edits,
Unity, tests/imports, providers or delegation. SOURCE ONLY, static ast.parse allowed.
Commit exact owned paths. Root runs checks under all three locks after handback.

Acceptance:
- Explicit simulation-time clock for both camera-processing nodes in both simulation
  launch entrypoints. Preserve lane point_ttl and unrelated parameters/actions.
- Steady timers, monotonic receipt checks, acquisition freshness limits and genuine
  clock regression handling remain untouched. No health bypass or default hardware
  behavior changes inside the node classes.
- Behavioral tests load actual launch descriptions (stub only unrelated package-share
  lookup/MPPI marker using temp files as necessary), resolve effective node parameters,
  catch omission/false for either node/entrypoint, and retain existing lane TTL.
- Include an actual rclpy clock/parameter behavior test where feasible: use the resolved
  parameter with a real node and deterministic ROS clock override or bounded synthetic
  /clock delivery; demonstrate simulated acquisition time remains distinct from wall
  time. No active simulator or external services. Avoid sleeps/unbounded DDS waits,
  private API coupling when public launch/rclpy APIs suffice. Report any unavailable
  ROS dependencies honestly; do not replace behavior coverage with source-string tests.
- Explain compatibility and unverified live effects in <=300-word handback. No claim
  of fixing the audit or CPU/power problem before actual evidence.

Budget exact claude-opus-5-5 high,6min/requested USD5, no retry/substitution. Stop at
handback or bound; root reviews before integration. No live trial is authorized here.

## Log

### 2026-10-07T18:46:19.0528380-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Assign source-only launch-clock fix to named headless owner in isolated worktree. This
is disjoint from T0070 and T0072; neither assignment is retried or transferred. Root
verified relevant source is clean at5346e60. Tests/imports/live work remain prohibited
to this worker; six-minute/USD5 requested bound, no automatic retries.
