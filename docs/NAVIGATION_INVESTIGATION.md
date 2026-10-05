# Lane re-entry investigation — September 30, 2026

This follows the five-step investigation: record the failure, replay perception,
compare selected and executed routes, test observed entrance memory, then tune
control. It extends [the reliability milestone](RELIABILITY_MILESTONE.md).
The full sensor-led lap gate remains open. These are native WSL Jazzy tests with
the ideal Unity fixture, not hardware validation or a Docker release test.

## Follow-up: invisible support gap beside a pothole

The final post-ramp stop in `entrance-verified-run` was an execution failure
inside Unity. Three recorded stationary intervals lasted 18, 22 and 20.6 seconds
despite median accepted ROS forward commands of 0.0568, 0.0696 and 0.0981 m/s.
That separates this failure from absent planner routes, but ROS publication
alone did not prove Unity delivery. An independent Unity reproduction then
isolated the ground geometry.

At recorded pose `(-1.278669, 41.644755, -2.563953)`, current wheel support
passed, but the next 10 ms forward preview failed at all four tested speeds:
0.02, 0.05, 0.10 and 0.50 m/s. Adding only the already-rendered pothole rim to
the support set made all four previews pass. `CourseVariant.Ground` removes
coarse 0.5 m cells around potholes. The flat rim replaces those cells visually,
but `Bowl` previously omitted it from the wheel-support surfaces. Rejected
previews invalidated motion, producing a false Nav2 progress failure beside
visible flat ground.

[CourseVariant.cs](../unity/IGVCSim/Assets/IGVC/Runtime/CourseVariant.cs) now
registers the flat rim and initializes ground support even in variants without
ramps. Both generator and loader also reject pothole pairs whose flat rims would
cover the other depression (opening-to-opening clearance below 0.85 m). The
actual depression remains unsupported. No obstacle inflation,
footprint, speed limit, navigation input or route was relaxed.

[CourseSupportChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/CourseSupportChecks.cs)
provides six portable behavior checks: overlapping-rim rejection, support without a ramp, continuous flat
annular support, an unsupported hole center, support at the recorded stop, and
200 consecutive low-speed movement previews. They passed in Unity 6000.3.23f1
and are now part of the course-build gate. Its separate `Reproduce` entry point
requires the local generated seed-2027 manifest; it is a forensic diagnostic,
not an input to robot autonomy.

`/sim/status` adds cumulative `terrain_support_rejects` and
`terrain_budget_rejects`, reset by `/sim/reset`. These count attempted moving
steps rejected by support or distance-budget checks, respectively. The episode
recorder also captures `/cmd_vel/nav`, `/sim/drive_command` with its original
stamp, and `/sim/suspension_state`. The focused recorder suite passed all 15
tests in the native Jazzy environment. These observations distinguish command
generation, adapter admission and simulator motion on future runs.

The updated Windows course player was built successfully. The 15 course-generation
tests also passed, including independent pothole separation assertions over six
seeds and three difficulties. Seed 2027's generated world is unchanged.

The fresh `entrance-support` trial ran for **383.43 seconds**, reached **4/6**
destinations and stopped at the west slalom after two completed backups
(0.6067 m and 0.6020 m). Both Unity rejection counters stayed at zero.
The independent audit passed obstacle clearance (minimum 0.1048 m), whole-body
paint clearance and the speed bound (peak 1.2093 m/s). The ramp was traversed,
but conservative body-side containment failed with a -0.0496 m margin. It did
not return to start or certify a full lap. This resolves a reproduced simulator
support defect, not the separate controller/guidance and ramp-containment gates.

The run retained 244 exact-input decisions without drops/errors. The expanded
episode recorder wrote 1,022 frame bundles and 87,580 events; its bounded queue
dropped one frame and 62 events, and drained with no write errors. These are
sampled diagnostic records, not a lossless bag. See the compact
[support evidence](evidence/navigation-2026-09-30/terrain-support.json) and
[independent audit](evidence/navigation-2026-09-30/terrain-support-audit.json).
This trial is separate from the six historical experiments below, which used
the earlier support geometry. Docker and Linux player rebuilds were not tested
in this follow-up.

The trial's old stop text, `No safe forward route after limited backup recovery`,
also covered stalled execution with an available plan. It is not evidence of
an empty search result. Subsequent reports distinguish an exhausted backup budget
from an unavailable backup action server; `recovery_limit` records plan
availability, controller failures, stationary time and attempt count. This
reporting-only change passed the five mission-contract checks and Python
compilation; it does not increase the allowed number of recoveries.

The [final 60-second command review](evidence/navigation-2026-09-30/support-stall-review.json)
found no forward-command-guard violations in 623 Nav2 commands, and no adapter
zeroing of a recent nonzero Nav2 command among 696 matched output samples.
Both stops began with zero commands from Nav2. At the second stop, decisions
235–236 still proposed routes, while action 234 returned error 208. The
installed Jazzy `nav2_msgs/action/ComputePathToPose.action` defines 208 as
`NO_VALID_PATH`; the planner log independently reports no valid path from
`(-9.12,23.33)` to `(-10.39,19.39)`. The preceding successful Nav2 path and the
custom proposal had the same endpoint and differed by at most 0.0503 m over
the first metre. Those samples do not establish that both searches used the
same costmap instant, start state or collision discretization when failure
occurred. The next isolated experiment should compare the planners on matched
observed grids and poses before altering controller weights or command gating.

## What the recordings establish

1. **Planning inputs can age while the robot moves.** In baseline decision 7,
   the robot moved 4.98 m during a 5.56 s decision. Its selected goal was only
   1.01 m away by completion. Several other searches allowed 2–3.5 m movement.
   Continuing an earlier Nav2 action while computing a new goal makes search
   latency a navigation issue even when ROS callbacks remain healthy.
2. **Remembered heading can drift away from an observed entrance.** Decision 81
   accepted an entry at `(25.216,44.070)` m. When the paint pair disappeared,
   subsequent goals extrapolated the direction from the moving robot. Decision
   87 targeted `(13.73,50.11)` instead. The broad destination was `(13.49,44.5)`.
   These are recorded odometry coordinates, not generated course instructions.
3. **Fresh paint can be too short for the straight-pair detector.** Near the
   failed entrance, fresh projected paint covered only about 0.97–2.03 m, below
   the detector's 3 m segment/overlap requirement. Curves and one-sided visibility
   can therefore reject real lanes. Thousands of retained points do not establish
   a fresh visible entrance; their median ages in inspected frames were 115–167 s.
4. **A white barrel enters the pixel mask but was rejected in 3D.** In the saved
   frame, 811 cap pixels passed the white-feature detector. None became eligible
   ground-painted-lane projections when using the actual source depth surfaces.
   That example does not establish barrel contamination as the cause of re-entry
   failure. The [small recorded fixture](../fixtures/white_barrel_cap/metadata.json)
   and [behavioral regression](../ros2/src/igvc_perception/test/test_recorded_lane_projection.py)
   preserve both the mask false positive and the working ground rejection.

The image recorder pairs lane status with the **actual ground source acquisition**,
which can precede the RGB exposure. It records that source's depth, surface flags,
camera intrinsics and acquisition-time transform. Missing exact sources are
explicitly marked; nearest frames are comparison-only. Capture at 2 Hz is a
diagnostic sample, not a full-rate ROS bag or deterministic simulator replay.

## Controlled trials

All use a fresh seed-2027 scene and cleared perception before starting. Runtime
navigation receives only observed sensors and six sanitized geographic regions.
Full WORLD geometry is read **afterward by the independent judge**. MPPI is
stochastic and sensor/worker timing varies, so one seed is not one fixed execution.

| Trial | Forward search budget | Memory | Result | Important independent checks |
|---|---:|---|---|---|
| Baseline | 5.0 s | Extrapolated heading | Stopped at 2/6 | Obstacles/paint clear; ramp not reached |
| Short budget | 0.5 s | Extrapolated heading | 5/6 at 360 s timeout | Obstacles/paint clear; ramp traversal and body containment passed |
| Short budget repeat | 0.5 s | Extrapolated heading | Stopped at 4/6 | Obstacles/paint clear; ramp traversed but body containment failed |
| Fixed entrance | 0.5 s | Fixed observed point | 5/6; stopped 0.500 m from start | Obstacles, paint, ramp traversal/body containment passed; return failed |
| Held goals (bounded 180 s) | 0.5 s | Extrapolated heading | 1/6 at timeout | Obstacles/paint clear; ramp not reached |
| Arrival repair repeat | 0.5 s | Fixed observed point + acquisition refresh | Stopped at 3/6 | Obstacles, paint and ramp checks passed; bounded recovery exhausted |

Decision input-age p95 changed from **5.64 s** in the baseline to **1.17 s** in
the short-budget trial and **1.11 s** in its repeat. Lane extraction and collision
preprocessing sit outside the expansion budget. Four saved decisions replayed
with both 0.5 and 1.0 s budgets found checked proposals; that does not establish
the shorter budget can find every necessary detour.

The fixed-entrance trial exposed a separate final-arrival bug. At 0.500 m from
the start, the first 0.255 m search primitive entered the 0.25 m planner arrival
band. Search stopped, then endpoint selection rejected its displacement as less
than the mandatory 0.40 m. The search now continues past unusable short endpoints.
Replaying the **same frozen observations** changes `no_route` to a checked goal
at `(0.0103,0.00715)` m, 1.3 cm from the start. The compact
[before/after replay](evidence/navigation-2026-09-30/arrival-replay.json) preserves
the snapshot and patched-source hashes. No footprint, destination radius,
unknown-cell rule or collision threshold was reduced. Unit tests also reject
extending that final approach into unknown space. This offline repair still needs
a successful fresh full-run check. The repeat stopped earlier, so it did not
exercise the repaired final approach in live execution.
The near-complete run visited all 77 independently required WORLD cross-sections;
the final 0.500 m return distance kept both topology and full-lap checks failed.

The selected Python path is a checked **proposal**. The mission sends its local
goal to Nav2, whose Smac planner computes another path. The new analyzer compares
those paths only when frame, endpoint, acquisition time, start proximity and
active goal lifetime match. `nav_msgs/Path` has no action UUID, so this association
is heuristic; a difference can be valid replanning. It is not proof of collision
or proof that MPPI ignored the selected route.

The held-goal comparison issued 14 decisions in 180 s and reached one broad
destination, with peak measured speed 0.854 m/s. It did not improve progress in
this trial. Rolling goal updates remain the default; fewer replacements alone
are not an adequate performance objective. The held trial included the independent
arrival-search repair, though it never approached the final destination.

The corrected-entrance repeat stopped after 429 s near `(-1.28,41.64)` m,
after two 0.6 m backups at the same destination (plus one earlier corner backup).
It continued to select observed forward goals, but Nav2 reported failure to make
progress. The final observed padded footprint was clear, with 1.8 m sampled rear
clearance; those facts do not prove the entire intended forward maneuver was
executable. This remaining case needs global/local path and execution agreement
investigation, alongside curved-boundary reacquisition. It is not evidence that
the robot needs a smaller body or lower obstacle blocking threshold.

No candidate has passed the full independent audit. The closest trial stopped
0.500 m from start. Consequently **heading/5 s defaults remain unchanged**, fixed
entrance and shorter budgets remain explicit experiments, and increased-speed
or critic-weight tuning is gated on reliable entry and execution. All six attempts
and failures are retained; successful partial checks are not full-lap claims.

## Implemented experiments and defaults

- `--planning-budget SECONDS`: expansion budget, 0.05–5 s; default **5 s** stays
  unchanged pending reliable validation. The outer worker deadline remains 8 s.
- `--goal-policy rolling|hold`: default `rolling`. `hold` retains the accepted
  Nav2 goal until result, changed broad destination, or existing stall/failure
  handling. Nav2 still replans internally and checks its costmap. This isolates
  goal replacement; it does not freeze the path or bypass sensing.
- `--guidance-memory heading|entrance`: default `heading`. Experimental `entrance`
  stores the actual supported point, confidence and two observed paint segments.
  It never translates that target with robot motion or invents unseen lane bounds.
  It expires at 60 s/20 m travel, is consumed within 0.7 m or after passing its
  approach plane, and clears at each broad destination. A passed lateral miss
  requires reacquisition; it is not counted as a successful lane re-entry.
- Entrance refresh requires recent observations on **both** supporting segments:
  at least three distinct 0.075 m cells spanning 0.5 m per side, within 0.22 m
  of the fitted segment. Per-point age plus reception delay must be ≤1.5 s.
  Repeated old geometry cannot renew the target's lifetime. A strictly newer
  acquisition proof can refresh an active identical entrance; consumed geometry
  cannot revive without clearing or a different observed target. A new cloud
  header alone cannot turn old retained paint into fresh evidence. This gate
  applies to memory refresh, not every current corridor fitted from retained paint.
- In entrance mode, an already-reached inside-corridor endpoint yields to broad
  intent instead of issuing a tiny goal indefinitely. All observed painted cells
  remain blocking. A remembered entrance can override skewed broad GPS intent;
  it must still pass the same observed full-footprint collision search.

Inflation stays **0.30 m**; actual footprint, padding and patched MPPI collision
checks remain mandatory. Speed stays capped at **2.2 m/s**. A shorter search,
entrance hypothesis or accepted local goal never authorizes unobserved space.

## Record, replay and compare

From the repository root, with configured native ROS and a built course player:

```powershell
powershell -ExecutionPolicy Bypass -File tools/igvc.ps1 stop
powershell -ExecutionPolicy Bypass -File tools/igvc.ps1 variant-start -Seed 2027 -Visible
powershell -ExecutionPolicy Bypass -File tools/igvc.ps1 nav-start

# Terminal 1: read-only, bounded sensor/TF/path/decision capture.
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/record_navigation_episode.py --output artifacts/checks/my-episode --duration 645 --image-hz 2

# Terminal 2: commands motion; always use new report/capture paths.
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/sensor_course.py --mission artifacts/courses/seed-2027/autonomy.json --report artifacts/checks/my-run.json --capture-dir artifacts/checks/my-decisions --timeout 600 --planning-budget 0.5 --guidance-memory entrance

# Offline after the run. A failed/partial audit correctly exits 1.
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/analyze_navigation_episode.py --episode artifacts/checks/my-episode --output artifacts/checks/my-analysis.json
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/replay_navigation_decision.py --snapshot artifacts/checks/my-decisions/00001.json.gz --output artifacts/checks/my-replay.json
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/audit_sensor_run.py --run artifacts/checks/my-run.json --course artifacts/courses/seed-2027/course.json --output artifacts/checks/my-audit.json
```

`--diagnostics-only` replays just lane extraction. Change one gate per offline
experiment using `--heading-gate`, `--segment-span` or `--pair-angle-deg`; none
changes production defaults. Shorter segment span does not relax the separate
3 m overlap requirement. Replaying collision search with a wall-time bound need
not return a bit-identical route on a different machine.

`/mission/decision` contains requested/evaluated/sent/retained/result/end events.
Use action UUID and `action_sequence` to associate a result with its goal; the
event envelope's `sequence` identifies the decision current at callback time.
`--capture-dir` records exact frozen planner inputs, source hashes and acquisition
metadata as compressed JSON. It is bounded and reports drops/write errors.
Entrance-mode captures now also include frozen per-point refresh evidence and
receipt age; evaluation events retain the support clock and decision. Ordinary
replay consumes the already-frozen hint: it does not automatically reconstruct
historical memory transitions. Early trials predate this extra refresh payload;
their episode bundles remain the supporting source.
The episode recorder saves PNG/NPZ bundles and JSONL events with bounded queues.
Inspect its final counters before assuming a complete capture.

The arrival-repair repeat exposed a telemetry size limit: putting all per-point
refresh rows in ROS decision strings caused **202 oversized requested events**
to be dropped. All 272 exact decision snapshots and evaluated events were saved,
so route replay remains available; the episode event history is not complete.
The final publisher now keeps full rows only in the compressed snapshots and
sends count/age summaries in events. A focused full-capacity test and a live ROS
publisher-to-recorder smoke cover this correction; that telemetry change has
not been followed by another full lap.

Compact versioned [trial summaries](evidence/navigation-2026-09-30/summary.json)
retain configuration, source/report hashes, recording counters and independent
audit results. Large episodes and exact grids remain in ignored `artifacts/`;
the compact summaries alone cannot reproduce full recorded runs after cloning.

`/perception/lanes/evidence` is an optional PointCloud2 published only when
subscribed: `x,y,z,age_wall_s,observations,confirmed,stamp_sec,stamp_nanosec`.
The first four fields are FLOAT32, the remaining four UINT32 (32-byte points).
The header follows the current RGB acquisition; each point carries its own last
observation stamp and age. Rebuild ROS to install this publisher; Python tools
are used directly from the checkout. Rebuild the Docker image before expecting
this topic or these tools in a previously published container.

## Control tuning gate and alternatives

### Follow-up toward six destinations

The progress-based recovery trial still stopped at **4/6**. It passed the
obstacle, paint, speed and corrected finite-ramp audits. Two 0.6 m backups
returned to the same barrel trap; allowing a fresh recovery budget after a
genuine 3 m forward departure did not solve this local failure. The total
mission recovery ceiling remains twice the number of sparse destinations.
See [the recorded trial](evidence/navigation-2026-09-30/progress-recovery.json).

The earlier ramp failure was a scoring error: it tested the entire body against
infinitely extended ramp edges as soon as the front entered. The rear corner
was still 1.469 m before the ramp. The judge now clips the body to the finite
longitudinal ramp slab and retains conservative between-sample motion bounds.
Real side overhang and premature departure turns still fail. The corrected
entrance-support trial has 0.772 m conservative ramp-side clearance, but remains
an incomplete loop.

Frozen-grid comparisons also found that custom accepted paths and native Smac
paths are not interchangeable. Heading/cell rounding can reject an exact
continuous-footprint path, while native success alone does not prove the same
filled-footprint sweep. Adding 32/64 custom heading choices did not resolve five
captured traps; the original 16 choices remain. Clearance-mask vectorization
preserves the original cells and margins while reducing calculation overhead.

`sensor_course.py --path-execution checked-path` is an **experimental** alternative
to the default `nav2-goal`. It sends the observed, swept-checked forward path to
Nav2's `FollowPath` action with actual primitive orientations. It keeps live
MPPI collision checks, sensor watchdogs and bounded straight backup recovery.
Every new checked path replaces the previous reference even when its endpoint
is similar. It does not use generated route geometry. The direct MPPI trial
stopped at 2/6 with clear obstacle/paint audits. An experimental RPP profile
at 2.2 m/s stopped at 1/6 and **failed the paint audit**: a captured handoff was
0.231 m off the checked path and 0.676 rad away from its checked heading.
Direct-path admission now trims only a nearby aligned suffix and checks its
whole sweep against the latest observed grid. A misaligned or newly blocked
path is canceled and replanned. This is an admission check, not a guarantee of
subsequent controller tracking.

Two slower RPP trials also stopped at 1/6: one on the unchanged sensor freshness
watchdog, another beside a cell that was clear of the configured body but inside
unnecessary direction-independent sweep padding. Short arc intervals now use
directed conservative enclosures; straight backup sweeps use their exact
longitudinal rectangle union. Neither change reduces the configured footprint
or permits unknown space. A terminal escape reaching its actual observed target
no longer requires a metre of path beyond that target; partial escape paths
still require the reserve and all original-trap progress checks.

The subsequent directed-sweep RPP trial remained at 1/6, with clear independent
obstacle and paint audits. Frozen inputs from both earlier 4/6 traps now admit
checked backup escapes, but that replay alone is not evidence of a live lap.
The RPP experiment has not replaced the production MPPI profile. No successful
direct-path full loop has been established. A focused combined suite of 65
geometry, route, path-entry, recovery and budget tests passed after these fixes.

To select an explicit local controller experiment, stop the existing managed
navigation session and use `tools/ros_session.py start nav --params-file PATH`
inside the ROS environment. This validates that the profile exists and passes
it to the launch file. Without the option, the installed package profile is
used. Keep the profile with the run evidence; changing the file does not change
an already-running controller. The experimental RPP YAML remains in ignored
artifacts, not a shipped or validated default.

The next frozen-input diagnosis found a separate guidance defect: closely
tracked paths reached a northbound entrance facing nearly west. Forward search
now optionally uses the observed lane tangent as an arrival constraint. Broad
GPS destinations still have no prescribed heading. Unknown cells and all
observed paint/obstacles retain the same clearance rules.

Recovery selection is now separated from collision search. Select the target
once at the actual stopped pose, then test candidate backups against that same
intent. Previously each hypothetical backup redetected a different nearby
mouth, sometimes only 0.224 m from the trap, making the required 0.5 m escape
progress impossible. Preserving the current target yielded a checked 0.6 m
backup and useful continuation in that frozen observation. After a live backup,
only the small target/direction record is retained; the old path is discarded
and fresh observations must admit every new path. A 30 s bound stops the mission
if useful forward progress never clears this intent. These are development
guards, not physical calibration or competition certification.

The subsequent MPPI comparison also stopped at 1/6 with clear obstacle/paint
audits before the target/direction fixes. The [compact controller trial
record](evidence/navigation-2026-09-30/followpath-trials.json) retains failures
as well as checks that passed. No partial trial is a six-destination result.

The oriented-entry trial progressed to 2/6 and passed obstacle/paint audits, but
stopped after 0.6 m and 1.2 m backups. Its final search exhausted nine states in
both 0.5 s and 3 s replay budgets: increasing search time was not the remedy.
The longest checked forward path was only 0.766 m, insufficient for the existing
continuation reserve. Recorded tracking included a 0.078 m / 0.211 rad departure.

One frozen path changed curvature from +1.538 to -1.538 to zero per metre within
0.511 m. Reconstructing the 0.65 m pure-pursuit carrot produced a single +0.468/m
arc that intersected observed cost geometry, although the original checked path
was clear. This supports a lookahead/projection mismatch, but the native failure
was not proved: contemporaneous local grid and rejected command/carrot data were
not recorded. The next isolated trial reduces only lookahead to 0.35 m, retaining
0.6 m/s speed, 0.02 m padding, 0.30 m inflation and collision checking. Nav2's
[Jazzy RPP reference](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/configuring_regulated_pp/)
describes the lookahead and time/carrot-limited collision projection parameters.

Validation: **320 core behavioral tests passed** (236 tools, 80 perception,
4 GPS), followed by four focused decision-recorder tests after the payload fix.
The latter include one new capacity regression; existing checks were not all
rerun after that isolated logging change. Local Markdown references and Git
whitespace checks passed. That earlier slice did not modify Unity; the support
repair above subsequently changed and rebuilt the course player. The ROS
evidence publisher was built and exercised natively; Docker rebuild, remote CI,
held-out course seeds and physical sensors remain untested in this slice.
The [validation record](evidence/navigation-2026-09-30/validation.json) retains
test counts, source hashes and the live compact-event smoke result.

First prove entrance selection, footprint clearance, ramp containment and a full
return over repeated runs and held-out seeds. Then measure speed/replanning and
vary one controller setting. Increasing speed now would confound unresolved
guidance and reduce time to observe the next turn.

Nav2's [tuning guide](https://docs.nav2.org/jazzy/configuration_and_development/tuning_guide/)
recommends the true noncircular footprint and a gentle obstacle potential field.
Lowering inflation alone does not fix goal selection; our unusually narrow
profile relies on explicit full-footprint checks. Its
[MPPI documentation](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/mppi_controller/configuring_mppic/)
relates horizon, available path and local-map size. Here 56 × 0.05 s × 2.2 m/s =
6.16 m, inside the 7 m half-window before body/obstacle margins, but that is a
capacity check, not evidence that a 6.16 m traversable path is always visible.
The [behavior-tree walkthrough](https://docs.nav2.org/jazzy/getting_started/nav2_behavior_trees/detailed_behavior_tree_walkthrough/detailed_behavior_tree_walkthrough/)
explains ongoing planning/control and goal updates; custom mission replacement
must be evaluated separately from Nav2's own replanning.

If straight-pair rejection remains dominant, the next perception candidate is
short curved-boundary tracking with uncertainty and identity continuity. If the
right entrance is selected but execution differs dangerously, evaluate explicit
path execution or route-consistency constraints before a planner replacement.
Neither a semantic object detector nor a larger heatmap solves absent boundary
evidence by itself. Missing depth, ambiguous barrel whites and genuine lane gaps
must stay distinguishable in the recorded evidence.
