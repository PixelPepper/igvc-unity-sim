# October 5: instrumented baseline and a passing mouth-handoff comparison

## Follow-up: one audited full loop

[T-0008](../agents/tasks/T-0008-body-aware-mouth-handoff.md) changed the lower
lane-mouth membership test to account for the existing footprint's front-center
projection. Heading, lateral, upper-span, collision, health and audit checks were
retained. Exact saved-observation replay supported the change; Sonnet and Sol
reviewed candidate `09fb1686ec9bddc07e682e54bb80e039bc86b112`. It was integrated
as `8f5e87766d5a7dffcba68da3917a7f101853d80d`; 567 combined tests passed.

[T-0009](../agents/tasks/T-0009-mouth-handoff-trial.md) then ran once from clean
launch commit `8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f`.

| Recorded measure | Comparison result |
| --- | --- |
| Destinations / independent audit | 6/6; all 20 checks passed |
| Armed-through-cleanup wall time | 399.229339 s |
| Armed processing samples | 3994 pass, 0 fail, 0 unknown; complete coverage |
| Maximum health sampling gap | 0.138817 s |
| Requested / maximum audited interval speed | 0.6 / approximately 0.6 m/s |
| Recoveries | Two checked backups, approximately 0.602 m actual travel each |
| Conservative swept obstacle clearance lower bound | 0.116546 m |
| Return distance | 0.384816 m against the unchanged 0.4 m bound |
| Sampled obstacle collision poses | 0 |
| Runtime cleanup | Runner verified shutdown; supervisor/player and TCP10000 absent afterward |

Course, six-goal mission, RPP profile and player assembly hashes match the failed
T-0006 baseline below. Only `sensor_course.py` and `observed_navigation.py` changed
among recorded source fingerprints, matching the reviewed correction. The trial
used its own verified ROS overlay, `/home/brand/igvc_agent_ws/t0008-mouth-handoff`.
Both learned scorers were disabled. No world geometry was added to policy inputs.
Evidence is in `artifacts/iterations/2026-10-05/mouth-handoff/` and the appended
[benchmark ledger](benchmark_runs.csv) row.

This is **one passing comparison, not baseline promotion or a speed improvement**.
The historical October 1 pass took 363.37 s with one backup; this run is slower and
has two. Host load remains uncontrolled. The return margin remains small. Neither
the user-approved repeatability gate nor physical calibration is established.
There was no failed/unknown health sample, so live first-failure capture remains
unexercised. The failed T-0006 result below is retained without reinterpretation.

## Outcome

The fresh baseline **stopped at 1/6 destinations and failed the independent audit**.
Processing health passed throughout the armed interval. The immediate stop was
`No observed collision-free backup with useful forward clearance`; its algorithmic
cause is being investigated from saved observations in [T-0007](../agents/tasks/T-0007-first-sector-stall.md).
No navigation change or repeatability milestone is claimed.

| Recorded measure | Result |
| --- | --- |
| Mission wall time | 119.2498358 s |
| Destinations | 1/6 |
| Independent audit | Failed |
| Armed processing samples | 1195 pass, 0 fail, 0 unknown |
| Health coverage | Complete; largest sampling gap 0.114540 s |
| Requested speed ceiling | 0.6 m/s |
| Maximum audited interval speed | 0.6000000000002494 m/s (floating-point rounding) |
| Sampled obstacle collision poses | 0 |
| Conservative swept obstacle clearance lower bound | 0.347497 m |
| Paint sweep | Clear on the recorded partial trajectory |
| Final distance from start | 36.551806 m |
| Recovery budget charged attempts | 0 |
| Recovery-list count | Unavailable: run has no `recoveries` array; CSV remains blank |

Incomplete destinations, return, ramp traversal and ordered full-loop checks
failed. Passing local geometry and health checks do not make this a completed lap.

## What changed and was verified

[T-0005](../agents/tasks/T-0005-first-health-failure-capture.md) added immutable,
bounded first-fail/first-unknown subscriber snapshots and an explicit telemetry
monotonic-clock origin. Offline diagnostics keep evidence availability separate
from causal conclusions. Neither navigation policy nor health/audit thresholds
changed in that task. Two Claude Sonnet reviews and two GPT-6.1 Sol reviews covered
the candidate and its correction; the final combined suite passed **562 tests**.

This live run exercised normal telemetry reporting, source fingerprints and the
new exported origin. Both snapshot slots remained null because no health failure
or unknown was sampled. **Live failure-capture overhead and contents remain
unverified.** Node-side execution time, TF waits and hardware timing are not
measured by these subscriber snapshots.

## Provenance and reproduction

- Launch commit: `e10315337a488f5efee64d8023f47a9151f95244`.
- Reviewed instrumentation candidate: `c9ccd8cf2ef6acb3723888977100ba96fcd5c4b9`;
  integrated as `54b9fd3` and `2002dada` before coordination-only commits.
- RPP profile SHA-256: `14245726680bb2f4e36aef73ae32de7fb3395d2e38b01dd6d7fbe7c869edbef4`.
- Course player assembly SHA-256: `6564e85476866ef0b2d1b0a8954af7ae81280b177cb7cef8b5da50d906b429c7`.
- Course SHA-256: `1126a9439558aad6201cd2df235df67d664f90c188ee93652c82cfef6245acb2`.
- Six-goal sanitized autonomy SHA-256: `21f168de29ff528274fe94150b426896d3849b1adda39064366c5c59c1f6eff5`.
- Separate ROS overlay: `/home/brand/igvc_agent_ws/t0005-baseline`; recorded
  installed perception hashes matched source in that overlay.
- Mode: sensor-led, rolling goals, heading memory, checked-path, legacy escape,
  body-clearance weight 3, 0.5 s planning budget, no episode recorder.
- Managed hidden Unity run; no RViz; primary exclusive lease, TCP10000/domain42.
  Runtime stopped cleanly and ownership was independently checked afterward.

Local evidence is under `artifacts/iterations/2026-10-05/health-baseline-r2/`:
`run.json`, `audit.json`, `health-diagnosis.json`, `compact-evidence.json`, copied
course/autonomy/profile, per-decision observations, launch/overlay/shutdown logs.
These large artifacts are ignored locally and are **not downloadable merely by
cloning the repository**. The durable outcome row is in
[benchmark_runs.csv](benchmark_runs.csv), and the experiment log is
[T-0006](../agents/tasks/T-0006-instrumented-baseline.md).

Profile, player, course and mission match the historical October 1 passing run.
Five existing source fingerprints differ, and telemetry is newly fingerprinted.
Host load was not controlled. This is a fresh baseline, not proof of a regression
caused by instrumentation or a controlled comparison of algorithms.

## Preserved launcher failure

The first `health-baseline/` attempt failed before starting any runtime:
Windows PowerShell could not load `Get-FileHash` through Node's inherited module
path. A read-only reproduction showed PowerShell 7/Codex module paths shadowing
the Windows PowerShell 5 utility module. A second probe passed with native
Windows PowerShell module paths. Only the replacement child's environment was
adjusted; global settings and launcher source remained unchanged.

That bootstrap failure remains in its own artifact directory. It has no run or
audit file and no fabricated benchmark row. Its `shutdown_verified=false` is not
a successful-shutdown claim: no owned runtime had started. General launcher
environment hardening remains a follow-up.

## Remaining gate

The user-approved promotion gate remains three consecutive full audit passes on
seed 2027 and one on each of two preselected held-out seeds. This attempt adds
zero passing laps. Hardware calibration and IGVC 2027 rule compliance remain
separate open requirements.
