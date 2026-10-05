# October 5: instrumented baseline and a passing mouth-handoff comparison

## Current source: promotion blocked by first2029 freshness failure

[T0035](../agents/tasks/T-0035-heldout-2029.md) tested the same frozen d6519e1
runtime, profile and player as the three passing2027 laps. The first2029 attempt
stopped at **2/6 after121.428575356s**. The adapter latched autonomy off when
camera/lane/depth receipt ages reached0.772s and clock age0.907s, exceeding the
unchanged0.750s freshness limit. The cause upstream of those observations remains
undetermined. Endpoint disconnect was logged10.072s later during cleanup and
does not establish the original cause.

The audit passed12/20 checks over6026 samples. Two health checks failed; the other
failed checks reflect the incomplete course/return/ramp/loop. Collision, paint
and speed checks passed, with zero collision poses and0.275208236m conservative
swept clearance. Health recorded1209pass/7fail/0unknown with complete coverage
and maximum sample gap0.123985376s. The first failing subscriber snapshot is bound
to the health ledger. No recovery was charged or recorded; no failed-search
capture or new retreat behavior was exercised.

Sonnet reviewed the interpretation; Sol independently verified the raw19 source
hashes, profile/player/input identities, full audit binding and cleanup. The
failed attempt remains in the benchmark ledger. T0036 investigates its timing;
no timeout increase, automatic re-enable or retry has been used. Seed2030 remains
ungenerated/uninspected and is not a replacement for this failure.

Artifacts: artifacts/iterations/2026-10-05/nearer-gate-2029-1.
Run SHA256: `1443e227c0347e767f5ed7e962c961ffbcb92d83cdfd8deeb3c9db9544249fe6`.

[T0036](../agents/tasks/T-0036-freshness-interruption.md) added an offline
diagnostic section showing open receipt gaps at the bound first-failure snapshot,
separate from completed interarrival maxima. Clock age at that snapshot was
0.394011062s against a0.104247074s completed maximum. This is a different observer
and instant from the adapter's0.907s latch report; final telemetry tail0.926s is
also separate. Both reviewers accepted the report change, integrated asb1aada7,
and36 focused tests passed in the primary checkout. This repairs evidence
presentation, not runtime delivery. Unity/connector/network/subscriber scheduling
remain unresolved alternatives.

T0037 integrated opt-in frame/connector-warning capture as20a18f3. Final19 Editor
checks and rendered Win64 build passed. A stopped-player smoke test produced zero
trace records with the environment variable absent, and11 records when enabled
(header,9 windows,terminal stopped). Shutdown triggered the component's disable
handler. No ROS endpoint ran in those smoke tests; expected connection refusals
are retained. Threaded connector warning capture and overhead are still unverified.
Set `IGVC_TRANSPORT_TIMING_TRACE=1` only in the intended player process environment
to enable the bounded schema2 records in its Unity log; ordinary launches stay off.
The header documents local UTC brackets, unsynchronized host clocks, asynchronous
warning observations, frame-gap ambiguity and finite coverage. No queue-depth or
wire-delivery measurement is claimed.

T0038 now runs one diagnostic2029 repeat with the same19 policy files, profile
and course/mission/autonomy bytes. Its new player assembly hash is
`cf8f4a64b4847bd1d6156d679c0af19ea8f7219b7b4d53458b0f87bf9fa426c3`.
The old d6519e1 player is preserved separately. No result or causal fix is yet
claimed, and this repeat cannot replace the original failed first2029 attempt.

## Three verified seed2027 passes

[T0034](../agents/tasks/T-0034-nearer-gate-qualification.md) qualified the
seed2027 stage on frozen source **d6519e1ee323db0e66fd5953959f07cc56508cc5**.
Both reviewers verified all three sequential, separately granted attempts.

| Attempt | Elapsed seconds | Audit | Health pass/fail/unknown | Maximum gap seconds | Return distance metres |
|---|---:|---|---|---:|---:|
| 1 | 332.553487 | 20/20 | 3328/0/0 | 0.121141 | 0.363768 |
| 2 | 358.873351 | 20/20 | 3590/0/0 | 0.127246 | 0.391660 |
| 3 | 336.905819 | 20/20 | 3371/0/0 | 0.119719 | 0.375731 |

All completed6/6 with zero charged backups and no recovery-gate events. Source19,
profile, actual player and all2027 inputs matched. Full trajectories were audited;
cleanup was independently checked after each run. **The new recovery retreat still
has no live exercise or demonstrated benefit.** Times vary under uncontrolled load.
Smallest return margin was8.340mm; no physical stopping margin is certified.

T0033's2028 pass below is a development regression. Before the first2029
outcome,2030 was additionally preselected
without generation/inspection to retain two untouched validation seeds.
This adds evidence; it does not discard the original2028 failure or its regression
requirement. The failed2029 result above blocks full promotion.

Artifacts: artifacts/iterations/2026-10-05/nearer-gate-2027-{1,2,3}.
Run SHA256 values in order:

- 43021cab417c373915d32f0257c5fb3206ea7872e16444db57bd675e1bd2ba17
- b4b4602251cef5fb8ab78863d2a7d4978e36b619124e262120c14780264c0335
- dfc698e00fd7e332ceddefc042fa72cd8931f241d032a548d887f1c52bcedf93

## New recovery build: passing2028 regression, mechanism unexercised

[T0032](../agents/tasks/T-0032-lane-entry-recovery.md) adds a recovery-only search
for nearer clear targets within the same observed corridor. It retains body,
unknown-space and downstream backup/continuation checks, and keeps newly retreated
targets ahead of the trap by a nominal front offset. Both reviews accepted it.
The integrated source d6519e1 passed643 combined checks (554tools,85perception,4GPS).

[T0033](../agents/tasks/T-0033-nearer-gate-regression.md) then completed
**6/6 and all20 audit checks in382.932130s** on the same2028 inputs/profile/player
as the failed attempt below. All3831 health samples passed; maximum gap0.139015862s.
Final distance0.396002088m leaves only3.998mm return margin; conservative swept
obstacle clearance was0.215131121m, with zero collision poses.

Both reviewers verified the raw source/input identity, audit and cleanup.
**No recovery was requested or charged, so the new retreat behavior was not
exercised live.** The result establishes no causal benefit or explanation of the
earlier failure. This is a development regression:2028 observations informed the
change. The original failure remains below and in the ledger.

Old-version2027 passes do not qualify this source; the new T0034 batch above does.
Untouched2029/2030 checks remain pending. Promotion remains pending.
No speed improvement or hardware fidelity is claimed.

Artifacts: artifacts/iterations/2026-10-05/nearer-gate-2028-1.
Run SHA256: 56aae5b4e290a515905d1f8f1316d283c31d1c27c64dde19cf4053c8c27d1b99.

## Held-out2028 failed: promotion blocked

[T0031](../agents/tasks/T-0031-heldout-2028.md) ran the first preselected2028
attempt on unchanged runtime f1a6ae4, same profile/player and all19 source hashes.
The reviewed coordinator seed runner changed separately at08e8ca5. Preserved course,
mission and autonomy hashes matched generated startup inputs; course/mission seed
metadata and the course binding passed before navigation.

The robot stopped at **1/6 after111.666446s**, with **14/20 audit checks passing**.
Reason: `No observed clear lane-entry position for recovery`. The final gate
selection checked24 candidate targets and reported `observed_gate_blocked`.
This occurs before backup search: the budget records zero charged attempts, and
the failed-search capture branch remains unexercised. The75 saved planner inputs
do not establish exact identity with the later recovery snapshot.

All1118 processing-health samples passed; maximum gap0.122466153s. The partial
trajectory passed collision, paint and speed checks, with0.210571915m conservative
swept obstacle clearance. Completion, return, both ramp checks, full loop and
ordered visits failed. Runner lifecycle `completed` does not mean mission success.
Both reviewers accepted the failed evidence; independent cleanup checks passed.

**The held-out failure blocks promotion.** No retry or course resampling is used
to replace it. T0032 investigates observed target selection without course geometry.
Seed2029 remains untested. Source fixes need fresh qualification, not a transfer of
the three earlier passes. No causal speed or calibrated hardware claim is made.

Artifacts: artifacts/iterations/2026-10-05/heldout-2028.
Run SHA256: 5ba436d86891bbbcca8bb3320a44c0c6596050880b7466061d2f9ac9bb46b853.

## Reviewed diagnostic build: three consecutive passing laps

[T-0027](../agents/tasks/T-0027-recovery-instrumented-trial.md) ran the integrated
recovery-diagnostic build at f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f, with fallback
off and unchanged navigation settings. It completed **6/6 with all 20 audit
checks passing in 364.386478 s**, with zero charged backup attempts.

Processing-health coverage was complete: 3646 passing samples, no failed/unknown
samples, maximum observed gap 0.154392 s against the configured 0.25 s limit.
All 19 runtime fingerprints match the frozen checkout. Player, profile, course
and mission match the prior control, but the diagnostic source differs.
The final recorded distance was 0.394471883 m, only 5.53 mm inside the return bound;
conservative swept obstacle clearance was 0.163087777 m across 18,221 samples.

Both reviewers accepted this single-run evidence. Independent player/port/lease
checks corroborated shutdown. No recovery-search event or failure capture occurred:
**the new failed-search capture branch remains unexercised live**. No causal
speed gain, recovery fix, calibrated hardware claim or promotion is established.
T0028 repeated the same immutable version and completed 6/6 with all 20 checks
passing in **335.561454 s**, again with zero charged backups. Its 3358 health samples
all passed (maximum gap 0.122978 s). Both reviewers verified the second pass.
The return distance was 0.399444509 m: only **0.555 mm inside the bound**.
All 19 runtime hashes and the profile/player/course/mission matched T0027.
Neither run exercised failed-backup capture. T0030 then passed 6/6 and all20 checks in **383.590085 s**, with one checked
1.2 m backup (1.209000018 m actual travel). Its 3838 health samples all passed,
maximum gap0.133848 s; final distance0.389614266 m and conservative swept clearance
0.122843140 m. Both reviewers verified the same19 runtime hashes and inputs.

**The three-consecutive-pass stage on seed2027 is satisfied.** Held-out2028 and2029
still require one pass each before promotion. Earlier failures remain preserved.
Times vary under uncontrolled load; no causal speed improvement is claimed.
The successful recovery logged matching submitted/worker input fingerprints, but
only the submitted digest and match flag were persisted. This is a runtime
assertion, not independently reconstructed provenance. No failed-capture branch
was exercised in any of these three runs.

T0030 artifacts: artifacts/iterations/2026-10-05/recovery-instrumented-3.
Run SHA256: d91f89d49fe59a144851a794d4f06626a76ae2f93a02a89b72843baed4e11ee8.

T0028 artifacts: artifacts/iterations/2026-10-05/recovery-instrumented-2.
Run SHA256: e8242ae844cd33b45ae9088b95a9bf4145363d20ddea8d73b35036c59047c362.

Artifacts: artifacts/iterations/2026-10-05/recovery-instrumented-1.
Run SHA256: 057b7662370e2ebe320c697295bfd478b62300ecfbc60e68009cf942eb6c7843.

## Enabled fallback: logged acceptance, but another failed lap

[T-0025](../agents/tasks/T-0025-replacement-enabled-trial.md) enabled only the
replacement revalidation flag at the same 0f76a2a source as the passing control.
It stopped at **2/6 after 208.661111 s; the independent audit passed 14/20 checks**.
The recorded stop reason was no observed collision-free backup with useful
forward clearance. No backup attempt was charged. Processing health passed
2089 samples with zero failed/unknown samples and a maximum gap of 0.122085 s;
this does not establish adequate lane visibility or correct guidance.

Twenty-six fallback submissions were logged as accepted by the action server.
Sol independently correlated their prior/new IDs, sequence, destination, target,
replacement ID and admission records. Of those actions, 23 ended aborted and
three succeeded. Full transmitted path geometry was not independently captured;
event agreement and reviewed send wiring are the available evidence.

All 18 runtime source hashes, profile, player, course and mission match the control.
Root and Sol verified cleanup through session records, absent player/listener and
exclusive lease availability. Both reviewers accepted the qualified failure record.
The feature remains **off by default**. One partial run under uncontrolled load
establishes neither an improvement nor a causal regression or harmlessness.
Completion, return, ramp and ordered-loop checks failed; collision, paint and
speed checks passed on the recorded partial trajectory.

Local artifacts: artifacts/iterations/2026-10-05/replacement-enabled-1.
Run SHA256: 2a294b916141b09784cfd9bc41ab979213952c4b63ac85179075154ed6b3284e.
Recovery diagnostics in T0023/T0026 are integrated separately at f1a6ae4; this run
does not contain their new exact-input failure capture. Staged validation covers
630 distinct tests after repairing generated-board freshness and the remaining
suite environment. The malformed new knowledge-log heading was also repaired;
strict knowledge validation reports 8 concepts and zero errors/warnings. All failed
check logs are retained. The T0027 normal-path trial is recorded above; its failed-capture branch was not exercised.

## Default-off control after instrumentation: one audited pass

[T-0024](../agents/tasks/T-0024-replacement-control-trial.md) ran at
0f76a2ac6090de0cf83c8f57bd471874dbffe552, with the reviewed replacement fallback
explicitly disabled and completion telemetry enabled. It completed **6/6 with
20/20 audit checks passing in 368.772596 s**. There were zero charged recovery
attempts, 3690 passing processing-health samples and no failed/unknown samples.
All 18 runtime hashes match the frozen checkout; player, profile, course and
mission match the preceding trials. Load was uncontrolled.

The return distance was 0.392415454 m (7.585 mm inside the existing bound);
conservative swept obstacle clearance was 0.109986430 m, with zero collision
poses across 18,438 recorded samples. Both independent reviewers accepted the
evidence. Runner shutdown and an independent player/port/lease check passed.

The new recorder reports six arrivals and five successful cleanup phases.
Final arrival and endpoint refer to the same odometry sample at trajectory index
18437. No new odometry arrived in the approximately 40.55 ms cleanup interval;
reported zero endpoint displacement is **not proof of physical stationarity**.
The 64 retained loop evaluations are only the end of the run, not sensor-rate data.

This validates one normal off-mode run and the recorder's live wiring. The enabled
fallback result is recorded above, failed-recovery capture is a separate pending
change, and the repeatability/held-out promotion gate remains unmet.
Local artifacts: artifacts/iterations/2026-10-05/replacement-control-1.
Run SHA256: d31e3a1ad4489895cae341be6707961c02b689647edde1c008add72d4d29e2a4.

## Preceding reliability result: two passes, then a failed repeat

Three runs used immutable commit `a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7`,
seed 2027, the same 16 runtime source fingerprints, player, profile, course and
six sparse GPS goals. Hidden Unity on Windows and native ROS 2 Jazzy/Nav2 in WSL2
ran through the managed exclusive lease. Speed remained 0.6 m/s.

| Task | Destinations | Full audit | Elapsed | Charged backups | Return distance |
| --- | --- | --- | --- | --- | --- |
| [T-0016](../agents/tasks/T-0016-connector-live-comparison.md) | 6/6 | 20/20 | 380.349 s | 0 | 0.392594 m |
| [T-0018](../agents/tasks/T-0018-connector-repeat.md) | 6/6 | 20/20 | 355.421 s | 1 (0.604 m actual) | 0.398906 m |
| [T-0020](../agents/tasks/T-0020-connector-third-repeat.md) | 2/6 | **Failed: 14/20** | 226.295 s | 0 | 49.08278 m (unfinished) |

The third run stopped with “No observed collision-free backup with useful forward
clearance.” Completion, return, ramp and ordered-loop checks failed. Processing
health passed throughout (2265 passing samples, zero failed/unknown, maximum gap
0.130315 s), and obstacle, footprint-paint and speed checks passed on the partial
trajectory. No collision was recorded. Refusing recovery does not establish that
no possible safe route existed. Follow-up diagnosis found that the corridor gate
was skipped because broad GPS guidance was selected. Its reason string does not
prove stale sensors or missing footprint data. The terminal backup chooser returns
no detailed rejection stage on failure, so whether rear sweeps or forward
continuation failed remains undetermined.

**The consecutive-pass streak is broken.** Neither speed improvement nor promotion
is established. Passing-run return margins are small (7.406 mm and 1.094 mm);
host load is uncontrolled. Both reviewers accepted the failed evidence without
reclassifying the run. Shutdown and lease release were verified for all three
attempts. Raw artifacts remain local under
`artifacts/iterations/2026-10-05/{connector-numerics-1,connector-repeat-2,connector-repeat-3}`;
durable outcomes are in [the benchmark ledger](benchmark_runs.csv).
T-0020 run SHA-256:
`6959f6278a7dc1a5e93175db9d66fb3791a94dbb178c62147c45aecb5e7569bb`.

Completion telemetry from [T-0019](../agents/tasks/T-0019-completion-evidence.md)
was integrated separately at `02cea958ccc9cd051241170c58ed1cbcd929a697`.
Its 598 combined tests passed; these three older frozen runs do **not** exercise
that new recorder. T-0021 subsequently integrated at 0f76a2a with 610 tests passing;
it remains default-off and is not a demonstrated fix for T-0020.

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

## Repeat: completed destinations, original audit exception

[T-0010](../agents/tasks/T-0010-repeat-mouth-handoff.md) ran live Unity on
Windows with ROS 2 Jazzy and Nav2 in an isolated native WSL2 overlay.
Unity was hidden; RViz and Docker were not used in this trial. Launch commit
was 70b3566d91dce8b807fee729dbb110c20db3c764. All 16 recorded runtime
source fingerprints and the player/profile/course/mission matched T-0009.

The robot reached **6/6 in 394.558273 seconds**, with one checked backup
(0.608 m actual travel), 3948 passing processing-health samples and no failed
or unknown samples. Return distance was 0.398244 m against the unchanged
0.4 m bound; swept obstacle clearance lower bound was 0.109255 m.

The original audit **failed 19/20**: topology evaluation raised
"min() iterable argument is empty" after reaching all 77 ordered gates.
At a stationary terminal sample, its lower bound selected a vertex rather
than the last valid segment. Later samples were not assessed, so gate count
alone cannot establish success. The original failed audit and benchmark row
are retained. [T-0013](../agents/tasks/T-0013-topology-terminal.md) addresses
the evaluator separately from navigation changes.

Local evidence: artifacts/iterations/2026-10-05/mouth-repeat-1/.
Run SHA-256: f7be0831c27ec043b160c46f4016bc9608508aeae93b4d3d6463f88e925d9c98.
Runner shutdown and exclusive-lease release were independently checked.
Sonnet and Sol reviewed the evidence. This is not a new passing streak;
the launch SHA differs from T-0009, and host load was not controlled.

### Corrected evaluation of the preserved lap

The separately reviewed auditor correction was integrated as
e886abb569b3a811a41d7bd726f1529779fff58b. A new full re-audit of the unchanged
T-0010 run passes **20/20**, including all 19,727 trajectory samples through the
terminal tail. No corridor, gate, return, footprint or health thresholds changed.
The original failed audit and benchmark row remain intact.

Supplemental local artifact: mouth-repeat-1/audit-t0013-reaudit.json under the
iteration directory above, SHA-256
ebd6d90e7e2537602a3c4c05267b8c9d86053fdcbf9265f997300fddd3e37f95.
The source and before/after input hashes are recorded in
artifacts/agents/T-0013/reaudit-manifest.json.
This is a corrected evaluation of an existing lap, not another live trial or a
same-commit promotion streak. The 1.8 mm return margin remains a concern.

## Optimization investigation

[T-0011](../agents/tasks/T-0011-passing-lap-delay-analysis.md) found 70.9 seconds
across 31 sampled stationary intervals in the passing T-0009 run. A 22.24-second
interval contained 13 repeated connector rejections from an unchanged pose.
These are descriptive associations, not measured time that a fix will save.

[T-0012](../agents/tasks/T-0012-connector-admission-probe.md) reproduced one
rejection from the full-precision observed path and checked pose. Eighty-eight
candidate joins exceeded the configured curvature limit by only
3.9968e-15 to 7.0448e-11 relative; later joins exceeded it by at least 0.0112998.
This supports testing a small numerical allowance in the comparison.
It does not establish arbitrary-offset behavior or a live improvement.
The saved grid represents planner submission, not necessarily the latest grid
at admission. [T-0014](../agents/tasks/T-0014-connector-numerics.md) tests the
actual comparison and close-boundary rejection controls separately.
Its reviewed final candidate 57920aa822e0cd02131a0db9ff6b6eef3eb61821 was integrated
as e33765d and fa8e730. The production comparison adds only a 1e-9 relative
arithmetic allowance. An observed-plan regression and independent near-boundary
circle controls pass; excessive curvature and blocked/unknown sweeps still fail.
The actual configured radius, footprint, pose gates and collision checks remain
unchanged. All 589 constituent tools/perception/GPS tests pass after regenerating
the stale task board and repairing the continuation command environment. The
initial full-script failure is preserved in T-0015 integration evidence; this was
not a single clean full-script pass. A fresh live comparison remains pending.

### Live connector comparison

[T-0016](../agents/tasks/T-0016-connector-live-comparison.md) tested the reviewed
arithmetic correction at launch commit `a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7`.
The hidden Unity/native ROS lap reached **6/6 in 380.348777 s**, with all **20/20
audit checks passing**. Its recorded recovery budget charged zero attempts;
the missing `recoveries` field alone is not evidence of zero backups.

Processing health recorded 3,806 passing samples, zero failed/unknown samples,
and complete sampled coverage with a maximum 0.130448 s gap. The swept obstacle
clearance lower bound was 0.263685 m. Return distance was 0.392594 m, leaving
only 7.4 mm inside the unchanged 0.4 m limit. Managed shutdown and lease release
were independently verified.

Profile, player, course and mission match T-0009/T-0010. Of 16 recorded runtime
sources, only `path_entry.py` changed; the separately reviewed T-0013 auditor
fix remains in use. This lap was 14.21 s faster than T-0010 and 18.88 s faster
than T-0009, but slower than the historical 363.37 s lap. Host load was not
controlled, and fewer recoveries are not proof of causation. This is one passing
comparison, not promotion. Sonnet and Sol reviewed the recorded evidence.

Evidence: `artifacts/iterations/2026-10-05/connector-numerics-1/`; run SHA-256
`f05a5f07593f7d1739189905e4a9525b35d2d5560fc69c43289efbd0149ea772`.
T-0018 repeats the exact source commit and profile in a frozen checkout.

The T-0017 proposal to continue forward after entering the finish radius was
rejected: bounded continuation can still leave the passing region. Its claimed
stopping-distance interval was illustrative, and cleanup callbacks continue
recording before the audited endpoint. T-0019 adds evidence to distinguish the
arrival decision from cleanup and the final recorded pose; it does not change
arrival behavior or audit thresholds.

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
