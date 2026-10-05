# Reliability milestone — September 30, 2026

This is a bounded improvement to the sensor-led training fixture. It does not
close the full-autonomy or physical-calibration gates in [PLAN.md](PLAN.md).
Unity remains the ideal motion/sensor fixture; no course geometry was supplied
to the navigator. Two GPT-6.1 Sol workers handled independent scoring and rules
validation/review while the integrator owned runtime changes and live sessions.

## Implemented

- [Mission telemetry](../tools/sensor_telemetry.py) distinguishes raw image
  arrivals, acquisition stamps, successful perception and processing failures.
  Reports retain bounded recent distributions/events and full-run counters.
  This observes subscriber delivery; it cannot identify GPU versus transport
  latency by itself. The existing 0.75 s watchdog was not relaxed.
  The standalone recorder exits 0 when it saves a report. Its separate
  `processing_health_summary` checks fresh `/healthy` Bools and processed
  acquisition/status claims; missing or stale evidence remains unknown. Lane
  detection validity is reported separately: too few visible lane points in a
  gap does not mean the camera pipeline failed. No summary authorizes motion.
- [Mission reports](../tools/sensor_course.py) record exact sanitized mission
  and Unity course hashes, requested limits, armed wall duration, and diagnostic
  evidence. The WORLD hash establishes identity without sharing world geometry.
- [Paired capture](../tools/capture_observed_clearance.py) freezes global/local
  grids with the same pose/lane observations after footprint queries. It
  requires fresh messages, bounded stamp skew and a stationary odometry interval,
  then atomically publishes one `pair.json`. Captures remain asynchronous;
  receipt/stamp limits and ages are included, not concealed.
- [Clearance diagnosis](../tools/diagnose_observed_clearance.py) explains which
  observed cells intersect the padded body, including rear corners. Sampled
  reverse clearance is a diagnostic, not permission to back up or evidence of
  useful forward continuation.
- [Global navigation grid](../ros2/src/igvc_navigation/config/local_navigation.yaml)
  now matches the local grid at **0.05 m**. A **24 × 24 m** rolling window uses
  230,400 cells, within the existing 262,144-cell planner limit. Local size stays
  14 × 14 m. Footprint padding and **0.30 m inflation** remain unchanged.
- [Independent course judge](COURSE_JUDGE.md) checks rendered paint with the
  entire body, actual gaps, ordered WORLD loop traversal and ramp body sides.
  It rejects unbound course identity and shortcuts. These checks run offline.
- [Versioned 2027 rules profile](IGVC_2027_PROFILE.md) checks declared settings
  and reports missing evidence explicitly. The current six-destination training
  mission and dark depression hazards differ from the published competition
  requirements. The checker does not silently convert the training layout.
- [Core behavior CI](../.github/workflows/checks.yml) runs planner, recovery,
  perception, geodesy, scoring and launcher tests in a Jazzy/Ubuntu 24.04 image.
  This is source-level validation, not a rendered simulation lap.

## Measured investigation

The native baseline used the current seed 2027, scoring-only line guard, sparse
`autonomy.json`, 2.2 m/s requested cap and a 360 s mission budget. Before motion,
a 45 s timing capture and the 20 s integration verifier passed stream/TF checks.
The baseline mission stopped after **2/6 destinations** with
`No observed collision-free backup with useful forward clearance`.
It successfully executed three checked recoveries: requested/actual distances
of 0.9/0.906 m, 1.5/1.501 m and 0.6/0.609 m.

During the baseline, the maximum observed gaps were approximately 0.150 s RGB,
0.192 s depth, 0.240 s lane status and 0.242 s depth status. The earlier freshness
failure did **not** recur, so this milestone does not claim its cause is fixed.
Independent scoring found zero body/paint contacts and zero unproven paint
sweeps; only 30/77 ordered WORLD gates were visited. This was not a lap.

At the stopped pose, the 0.10 m global grid intersected the padded footprint in
four lethal cells near observed paint, while the 0.05 m local grid showed no
intersection. The independent physical paint distance at that pose was about
0.0606 m for the unpadded scoring body. Grid observations were asynchronous,
so this is evidence of disagreement, not proof that resolution was its only
cause. After restarting Nav2 at the same stopped pose with the finer global
grid, both maps showed the body clear; a subsequently validated atomic capture
confirmed that result.

A single observed-only replay on the aligned global snapshot found a forward
proposal in **0.823 s / 80 expanded states**, with 0.783 m to its local goal and
1.004 m of checked continuation. It stayed over 9.97 m from the grid edge using
a conservative body-radius bound. Heading-memory state was unavailable for
this replay, so no remembered heading was supplied. A short proposal is not
proof of sustained escape or full-course completion.

A paint-only isolation replay then rasterized the **same 3,145 recorded points**
at both resolutions, preserving the same physical grid origin, body and pose.
The 0.10 m cells reproduced all four intersections; 0.05 m produced zero.
Both grids included the same 214 nearby points. This confirms the resolution
effect for paint at that pose without a memory reset; it does not reconstruct
lidar/depth, inflation or unknown-space behavior.

The fresh aligned-grid trial ran to its **360 s wall budget** and reached
**2/6 destinations**, with one requested/actual **1.2/1.201 m** recovery. Its
independent audit found zero paint contacts/unproven paint sweeps and at least
0.0910 m sampled obstacle clearance. Peak interval speed was **1.107 m/s**;
91.57 m of sampled travel does not mean 91.57 m of valid course progress.
The judge visited **40/77 ordered gates**, then rejected leaving its allowed
WORLD corridor near lane re-entry. The robot did not complete a lap or reach
the ramp. These differently terminated single trials do not establish a
statistical speed/reliability improvement.

The original stop message incorrectly reported a route-search timeout when
the overall mission deadline expired during search. The coordinator now
distinguishes those deadlines; the preserved raw report retains its original
message and measured 360.004 s armed duration. The native ROS build and local
core suite passed (164 tools, 75 perception, 4 GPS tests); final recorder
refinements passed 17 focused tests. A final six-second live capture correctly
reported healthy processing with insufficient visible lane points. The GitHub workflow has not run remotely,
and this slice has not been tested as a rebuilt Docker image.

Compact, versioned evidence: [baseline timing](evidence/reliability-2026-09-30/baseline-timing.json),
[transport/TF checks](evidence/reliability-2026-09-30/baseline-integration.json),
[independent baseline audit](evidence/reliability-2026-09-30/baseline-audit.json),
[paired-grid comparison](evidence/reliability-2026-09-30/costmap-comparison.json),
[bounded forward proposal](evidence/reliability-2026-09-30/aligned-grid-proposal.json),
[isolated paint raster test](evidence/reliability-2026-09-30/paint-resolution-ablation.json),
[aligned-run audit](evidence/reliability-2026-09-30/aligned-run-audit.json),
[aligned-run timing](evidence/reliability-2026-09-30/aligned-run-timing.json),
[final recorder smoke](evidence/reliability-2026-09-30/recorder-live-smoke.json),
[competition differences](evidence/reliability-2026-09-30/competition-comparison.json),
and [validation scope](evidence/reliability-2026-09-30/validation.json).
Large raw recordings and grids remain in local ignored `artifacts/`; these
compact reports retain source hashes, not all the inputs needed to replay them
from a clean checkout.

## Diagnostic and validation commands

From a configured Windows checkout with native Jazzy in WSL, run these from the
repository root. The first command records only; it does not command motion.

```powershell
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/record_sensor_health.py --duration 45 --output artifacts/checks/sensor-health.json

# Robot must be stationary; no navigation or reset commands are issued.
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/capture_observed_clearance.py --output artifacts/checks/clearance
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/diagnose_observed_clearance.py --observations artifacts/checks/clearance/pair.json --grid global --output artifacts/checks/clearance/global-diagnosis.json
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/diagnose_observed_clearance.py --observations artifacts/checks/clearance/pair.json --grid local --output artifacts/checks/clearance/local-diagnosis.json

# Offline after a recorded mission; a partial/failed run correctly exits 1.
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/audit_sensor_run.py --run artifacts/courses/seed-2027/native-sensor-run.json --course artifacts/courses/seed-2027/course.json --output artifacts/checks/sensor-audit.json
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/check_competition_profile.py --course artifacts/courses/seed-2027/course.json --autonomy artifacts/courses/seed-2027/autonomy.json

# Requires Jazzy Python types, nav2_msgs, numpy, OpenCV, Pillow and PyYAML.
wsl -d Ubuntu-24.04 -- bash tools/check_core.sh
```

On native Ubuntu, omit `wsl -d Ubuntu-24.04 --`. For a fresh live mission, use
[NATIVE_AUTONAV.md](NATIVE_AUTONAV.md), rebuild ROS after changing YAML, and
restart managed navigation. Docker must rebuild its image to install the new
configuration; an already-running container retains its installed version.

## Limits and remaining work

The finer global window covers less space than the old 40 m window. Sensor
offsets and a 14 m path horizon can encounter its edge; unknown/outside remains
blocked. Finer collision sampling increases CPU work. Keep timing and edge
diagnostics with future tuning rather than enlarging the grid beyond the
planner's accepted bound.

Full first-time autonomy, varied-seed reliability, multi-platform live parity,
physical caster/drive calibration, realistic camera/GNSS noise, negative
obstacle perception and hardware safety qualification remain separate work.
The judge's unmarked-area lateral allowance is explicit development policy,
not an official rule or proof of a unique route through a wide gap. Ramp body
containment does not certify wheel support, traction, suspension or rollover.

The next runtime investigation is lane re-entry selection through open areas:
record synchronized RGB/depth/observed-point and selected-goal history around
the transition, reproduce the decision offline, and require re-entry through
the observed lane opening. Do not solve it by sharing WORLD boundaries or the
generated route with navigation. Speed tuning follows that correctness work.
