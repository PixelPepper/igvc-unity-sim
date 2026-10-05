# Independent navigation implementation trials

These sensor-led development trials culminated in one independently audited
six-destination full loop. They are not a calibrated R3-a result or competition
qualification. Dates use the
development host's America/Los_Angeles timezone; artifact timestamps use UTC.

## Reproducible setup

The shared snapshot is `00a3e703a449ceb8c65c3e81a3cb04a4318ada52`.
Workers had separate Git branches/worktrees and ROS install overlays. An exclusive
lease serialized the shared TCP10000/domain42 simulator. The compiled Windows
player ran hidden with rendering enabled; no Unity Editor was opened or built.
All trials used seed2027, six broad GPS destinations, observed sensor costs,
checked-path execution, RPP, a 0.6 m/s requested ceiling and a 600 s timeout.
The controller/footprint/inflation profile was not weakened.

- Profile SHA256: `14245726680bb2f4e36aef73ae32de7fb3395d2e38b01dd6d7fbe7c869edbef4`.
- Player Assembly-CSharp SHA256: `6564e85476866ef0b2d1b0a8954af7ae81280b177cb7cef8b5da50d906b429c7`.
- WORLD is offline evaluation input only, never mission guidance.
- Local raw evidence is under `artifacts/iterations/2026-10-01/` (ignored).

## Candidates and measured outcomes

| Candidate | Commit | Offline checks | Live result |
| --- | --- | --- | --- |
| Opus 5.5 forward path entry | `d7fc29aba5f5b7d4e4ebaa537e86423ad0268201` | 66 navigation tests passed | 2/6, stopped on cancellation rejection after 160.52 s |
| Sonnet 5.5 observed surface projection | `cce469028a7f6b9e0b45dab4c4ac92c871fed50f` | 88 perception tests passed | 0/6, no useful observed backup after 18.87 s |
| Forward path entry plus terminal-confirmed cancellation | `354202086ba48542a8e9608b6ea98ad245860cce` | 75 combined navigation/cancellation tests passed | 1/6, no useful observed backup after 83.68 s |

All three live harnesses verified shutdown. The integrated trial passed recorded
trajectory continuity, speed, sampled/swept obstacle clearance and full-footprint
paint checks. It did not establish ramp traversal, return or full-loop acceptance.
These are one-run outcomes; different controller-entry code and observations
confound a causal comparison of 0/6 versus 2/6.

The cancellation helper now waits for a terminal action result (SUCCEEDED,
CANCELED or ABORTED), including bounded delayed delivery after a nonzero cancel
response. It never treats cancellation acknowledgement alone as motion handoff.
The integrated live recording observed code3 with terminal status4 and code0 with
delayed terminal status5. The older failure did not record its cancellation code,
so its exact cause remains unproven. Termination alone does not prove zero velocity.

## Projection evidence and open issue

The Sonnet candidate replaces copying an adjacent sample's optical Z with a
locally observed plane/ray intersection. Synthetic tests cover the demonstrated
0.387 m displacement, ground ranges, ramp slopes, creases and foreground rejection.
It remains on its candidate branch while live coverage is investigated.

A matched offline benchmark used the committed `white_barrel_cap` recorded fixture,
4,445 actual lane query pixels, 2,770 observed surface points, one warmup and three
measured calls per implementation. Median projection time was 3.13 ms baseline
versus 65.12 ms candidate; accepted points were 2,888 versus 2,880. This measures one
projection call on one recorded input, not full-frame throughput or hardware noise.
Details are in `projection-benchmark.json` beside the trial jobs.

Sonnet's final live processing summary was fresh (0.18 s lane acquisition lag;
maximum lane-status gap 0.352 s; 927 current points). Replay instead showed a
visible lane-mouth target only 0.340 m away while recovery required 0.5 m of
improvement toward that same target. A terminal healthy summary does not prove
interval health or geometric accuracy. Paired raw RGB/depth captures are still
needed to isolate live projection coverage effects.

## Observed mouth handoff

Commit `be479536cabf006f92ab78d7690bc4cada09cb19` adds a nearby-mouth handoff
after the cancellation/audit commits. It selects an interior target only within
the overlap of both observed lane boundary segments, preserving corridor yaw.
It does not change collision costs, the robot footprint, heading tolerances or
the GPS mission. The selected target remains guidance; the forward search must
prove a checked path on current observations.

Both saved stopped decisions (`integrated-cancellation/decisions/00055.json.gz`
and `sonnet/decisions/00013.json.gz`) changed from `no_route` to `route_found` in
exact-input replay with the new source. Replay output is saved as
`mouth-replay-integrated.json` and `mouth-replay-sonnet.json`. A combined set of
67 guidance/recovery/memory/replay tests passed. The wall and unknown-space
controls explicitly start with a clear whole-body footprint and prohibit
crossing a blocked strip; missing paint cannot create a corridor handoff.

The first live handoff trial (`observed-mouth`) included a paired acquisition
recorder at 2 Hz. It stopped at 0/6 after 3.20 s because camera/lane age reached
0.778 s, exceeding the unchanged 0.750 s autonomy watchdog. The recorder drained
24 frames and 1,666 events and exited0 after the mission ended. Simulator shutdown
was verified. This early stop cannot validate handoff behavior. A separate
`observed-mouth-light` trial tested the same candidate without the additional
recorder. Recording-load causation is not established by a single comparison.

That trial reached 4/6 in 385.96 s, then stopped with `Backup recovery budget
exhausted: no forward plan available`. It made three checked backups total.
Shutdown was verified. The independent audit passed both ramp axle traversal and
whole-body side containment through departure, continuous trajectory, speed,
obstacle sweeps and whole-footprint paint sweeps. Conservative obstacle-clearance
lower bound was 0.0542 m; paint-clearance lower bound was 0.00971 m. Course/mission
hashes and latest processing evidence matched, but full-loop/return and interval
health acceptance remained open.

At the final pose, recorded observed-cost diagnostics found the current whole-body
footprint clear and sampled rear clearance of 1.8 m. That does not authorize a
backup or prove useful forward continuation. The first post-ramp recovery
selected an observed mouth 1.16 m from the axle, just beyond the new handoff's
1.1 m radial threshold; whether a geometry-based handoff can resolve this is the
next replay investigation.

Commit `1d28d6ff8e55669e24c3b5e7b4ce1f451ef03c3e` removes that radial prerequisite
while retaining the existing observed longitudinal, lateral, heading, forward-target
and collision gates. Exact decision213 replay then found a 4.339 m checked path
with 1.004 m continuation toward `[-9.2473,18.1356]`, within both observed spans.
The updated 14-test guidance suite passed after a test-only missing import was
fixed; the other 55 recovery/memory/replay checks passed in the combined run.
The fresh `post-ramp-handoff` trial uses this commit and the same recorded profile.

It stopped at 2/6 after 186.45 s near a barrel passage, with `No observed
collision-free backup with useful forward clearance`. It made one checked backup.
The obstacle/paint sweeps, continuity, speed and identities passed; ramp/return
were not reached. Shutdown was verified. Thus the post-ramp correction is
replay-validated but its post-ramp live effect is not established. The best lap
progress in this round remains 4/6; repeatability and full 6/6 are unresolved.

The three compact original failure inputs and integrity hashes are now available
in [the recorded handoff fixtures](../../fixtures/observed_mouth_handoff/README.md).

## Agent execution and cost accounting

Claude CLI ran the exact requested Opus/Sonnet5.5 models with bounded file tools,
owned paths, test gates, scoped Git commits and one live request each. The original
detached launch failed before acknowledgement; the integrator repaired infrastructure
and executed each already-requested trial. The models' original reports correctly
say their live results were unavailable; the measured results above are subsequent
integrator evidence, not retroactively model-verified results.

Reported implementation-call API-equivalent costs were Opus $2.030403 and Sonnet
$3.0452796 ($5.0756826 combined). These are CLI usage estimates, not a statement of
subscription charges. Repeated paid polling contributed to Sonnet's usage. The
MCP now rejects stalled-launch polling after 60 s without releasing possible
runtime ownership or automatically retrying. A direct harmless reproduction
confirmed that detached PowerShell exited0 without executing its script. A
persistent detached Node supervisor now owns a hidden, non-detached PowerShell
child. Both MCP regressions pass: tool boundaries/stalled polling, and actual
hidden PowerShell startup surviving MCP process exit. This fixture launches no
ROS or Unity processes; complete live trials above used the integrator launcher.

## Follow-up implementation

### Follow-up toward six destinations

The latest 2/6 snapshot117 exposed an occupied guidance target: the chosen
lane-mouth midpoint's whole-body footprint overlapped an observed lethal cell.
`refine_corridor_guidance` now considers at most 35 lateral positions within
the two detected boundary spans, preserving the observed heading and the padded
footprint. A midpoint before the shared support is projected to the support
start. Full collision search still decides whether the selected position is
reachable. No alternative creates a GPS fallback; ordinary planning can still
make a checked partial approach toward its original intent.

Exact-input replay with the same 0.5 s budget changed `no_route` to a 1.787 m
full-footprint checked path, with 0.01385 rad arrival-heading error. Nineteen
guidance tests passed. The isolated `observed-gate` live trial uses commit
`dd98ac10e2d40901f443ed2e47652be56841f415`, the unchanged player/profile hashes,
and the same six sparse destinations. It stopped at 4/6 after 309.17 s with one
0.6 m backup. The stop snapshot203 has a clear lane target but a currently
blocked padded footprint, so recovery rejects the starting pose before testing
forward escapes. Obstacle and paint sweeps passed. Full geometric acceptance
remained unavailable: two stationary startup timestamp gaps invalidate the
strict continuity/ramp-body audit. Five sampled perception-health failures were
also retained, despite latest processing passing. Shutdown was verified.

New mission evidence also includes a steady-clock sampled processing ledger.
Twelve ledger tests and nineteen audit tests passed; focused malformed-evidence
tests additionally passed after review fixes. The installed Jazzy steady timer
API was exercised. Complete live interval coverage remains a measured gate,
not something inferred from the last sensor status. The next run separates
stationary startup receipts from the armed trajectory, preserving them in
`startup_trajectory` and refusing unexpected pre-arm motion.

The opt-in `--body-clearance-weight` candidate adds a soft preference around
the whole footprint, including unknown cells. Zero preserves the prior search;
positive weights keep every existing hard collision rule. Forty-four route
tests passed. A frozen sequence108 replay at weight3 increased minimum sampled
clearance from 19.4 to 65.6 mm, with somewhat less endpoint progress. This is
not a continuous clearance proof or live tracking result.

The `body-clearance` trial (commit `916545699e64da44e59bd41eca4222c17ddc2277`,
weight3, otherwise unchanged profile) stopped at 2/6 after 163.12 s, following
one 0.6 m backup. This candidate is not promoted. Its armed trajectory passed
continuity, speed, obstacle and paint checks; all 1,633 processing samples
passed, with maximum sampling gap 0.1246 s. The interval audit passed. Full lap
and ramp checks did not pass because the run stopped early. Shutdown verified.

Snapshot102 then showed an endpoint-selection defect: weight3 ranked a 1.276 m
chain first, but it could not satisfy the 0.4 m minimum displacement plus 1 m
continuation reserve. A fully checked alternative with 5.122 m local path and
1.004 m reserve was already present in that same search. Returning `no_route`
after rejecting the single ranked winner discarded this usable alternative.
Commit `ac765e9091cb40c9c248df71e0b02016bb54021f` admits usable endpoint geometry
before accepting a new ranked winner, and keeps searching after rejection.
The same frozen failure now returns a 0.528 m local route with 1.004 m checked
continuation. Forty-five route tests and 53 consumer tests passed. The weight
remains 3; reducing it was not treated as the correctness repair.

Perception tick tests also found a reporting defect: a timer tick with no new
exact pair immediately marked processing unhealthy even when the preceding
successful acquisition remained fresh. Commit `6c80a7d` preserves existing
publications on idle/TF-wait ticks only within both receipt and acquisition
0.5 s bounds; it does not refresh timestamps or republish stale outputs. Errors,
reset and regressions invalidate retention. Five Jazzy node-tick tests passed
with depth/lane subcases. The completed trial below includes this correction.

## Completed sensor-led loop

The `admissible-endpoints` trial at commit
`ac765e9091cb40c9c248df71e0b02016bb54021f` completed **6/6** in **363.37 s**
(armed interval through cleanup). Independent audit exit code was 0 and every
one of its 20 checks passed. Shutdown was verified. This run used observed sensor
costs and six broad GPS destinations; no generated route or WORLD geometry was
supplied as runtime navigation guidance.

| Measurement | Result |
| --- | --- |
| Course | Seed 2027, normal difficulty |
| Requested speed ceiling | 0.6 m/s |
| Travel distance | 157.34 m |
| Return distance from start | 0.3952 m (0.4 m bound) |
| Checked backups | One, requested 0.6 m; actual 0.603 m |
| Conservative swept obstacle clearance lower bound | 0.0793 m |
| Sampled processing health | 3,635 pass; 0 fail; 0 unknown |
| Maximum health sample gap | 0.1246 s (0.25 s bound) |
| Independent geometry | Ordered full loop and destination visits, whole-body paint/obstacle sweeps, ramp axle traversal and body containment all passed |

The [preserved audit](navigation-2026-10-01-success/audit.json) and
[exact Nav2 profile](navigation-2026-10-01-success/profile.yaml) are versionable
evidence. Full local mission/decision/log artifacts remain under
`artifacts/iterations/2026-10-01/admissible-endpoints/`. Source, profile, player,
course and mission identities are preserved with the results. WORLD geometry
is supplied only to the independent offline audit after the mission.

To reproduce the configuration, use the preserved YAML as the `--params-file`
for `tools/ros_session.py start nav`. Run `tools/sensor_course.py` against the
generated seed-2027 `autonomy.json` with these explicit options:

```text
--timeout 600 --speed 0.6 --planning-budget 0.5
--path-execution checked-path --body-clearance-weight 3
```

The actual isolated run used `tools/agents/iteration-live.ps1 -Config <config.json>`
with its exclusive simulator lease, verified ROS overlay and matching rendered
Windows player. A copy of `profile.yaml` belongs in that harness's job directory;
the job config must set `body_clearance_weight` to 3 and `record_episode` to false.
The harness provides the mission/report paths and runs the independent audit.
This recipe records the tested experiment; it does not promote these settings to
the ordinary `course` launcher or establish Docker/Linux parity for this change.

## Remaining gates

- Repeat this configuration and test held-out seeds before claiming reliable
  completion. A single pass cannot isolate the benefit of each integrated change.
- Higher speeds need new measured trials; the successful run requested 0.6 m/s.
- Preserve collision, footprint, paint and recovery gates when tuning. The
  0.3952 m return is close to the existing 0.4 m threshold.
- Processing health is sampled evidence, not proof of perception accuracy or
  continuous hardware health. Older reports without the interval ledger remain
  uncertified even when their latest telemetry passes.
- Physical dimensions, contact dynamics, sensor calibration and hardware noise
  remain separate from this ideal transport fixture.
