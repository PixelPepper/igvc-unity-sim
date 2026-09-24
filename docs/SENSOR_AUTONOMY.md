# Sensor-led navigation

The user requested destinations as broad guidance, with navigation driven by
vision and other sensors. The previous 31-point lap used a generated guide and
known painted/unmarked zones; its success is not evidence of this capability.

Implementation sequence:

1. Export six coarse GPS regions from the course centerline offline. Strip all
   route geometry, headings, obstacle locations and painted-zone annotations.
2. Select nearby goals only from the observed lidar/camera/depth costmap. Unknown
   cells and detected paint/obstacles are blocked; Nav2 checks its full footprint.
3. Permit missing paint while still requiring healthy camera and depth streams.
   Unity counts line contacts without using its lane geometry to stop motion.
4. Validate schema isolation, changed-observation behavior and live closed-loop
   operation before claiming a full course pass. Keep old guided regression separate.

`course` now runs experimental `sensor_course.py` using `autonomy.json`.
`guided-course` explicitly runs the old generated-route regression. `audit` still
audits that old guided report only; it must not be used to certify sensor autonomy.
The sensor report is `sensor-run.json` and RViz can display
`/mission/observed_path`. Start/rebuild Unity with the launchers to enable
`--line-guard scoring`; the sensor mission refuses hidden lane enforcement.

Windows commands, after rebuilding Docker and Unity:

```powershell
./tools/docker.ps1 start -Seed 2027
./tools/docker.ps1 rviz
# Another terminal:
./tools/docker.ps1 course -Seed 2027
./tools/docker.ps1 sensor-audit -Seed 2027
```

Linux uses `bash tools/docker.sh` with the same action names and `--seed 2027`.
`sensor-audit` reads world geometry only after the run. It checks ordered broad
destination visits, obstacle clearance, speed, continuity, lane contact counters,
return distance and actual ramp traversal. It is not hardware or full-body ramp
contact validation. Audit geometry never feeds the mission controller.

Each mission clears camera observation memory and Nav2 costmaps before collecting
new observations. During the run, up to 8,000 paint cells are tracked. Fresh
detections block immediately but expire after three seconds unless five distinct
frames spanning at least 0.4 seconds corroborate them. Confirmed points retain
the 1,200-second limit, so a temporary camera turn does not erase a known boundary.
The same confirmation applies to RGB hazard memory; depth/lidar processing is
unchanged. An isolated false lane projection 2.46 m from actual paint motivated
this change. Its original pixel-level cause remains unproven, and repeated false
detections can still confirm. No
static map, generated route, dense checkpoints or known gap locations enter the
mission. GPS origin defines the coordinate frame; positioning currently uses
ideal simulator odometry, matching the synthetic GPS model. Hardware GPS fusion
and realistic odometry drift remain separate work.

Ground fitting first tries all lower-image depth candidates. If no plane meets
the confidence checks, one bounded attempt uses the nearer horizontal-distance
half. This handles observed platform transitions with two height bands. Each
attempt still requires 100 inliers, 60% support within its selected subset,
two-dimensional extent, at most 20-degree slope, supported camera clearance and
35 mm residual bounds. There is no fixed-height fallback; the existing observed
surface-connectivity classifier remains responsible for traversability.
If both fits fail during partial occlusion, a previously validated plane can
select currently observed points within 35 mm for a new fit. The prior must be
no older than 0.75 seconds in both acquisition and wall time. Current support,
extent, residual, camera clearance and bounded plane change are checked again;
there is no blind reuse. Diagnostics distinguish conditional support from the
fraction of all current candidates. Clock resets and observation gaps clear it.

The local selector uses both a 0.5 m half-width check and the live Nav2
asymmetric rectangular footprint with padding. Nav2's 99
cost cells already represent inscribed inflation and block centres without being
dilated again; lethal 100 paint/obstacles and unknown space receive clearance.
A conservative grid mask provides fast acceptance, with continuous circle/square
checks near boundaries and a swept-arc margin, avoiding false rejection from
blanket cell padding at an otherwise clear pose.
Every forward primitive checks the swept oriented rectangle, including rotation
between samples. Local goal poses are also checked. A clear centre alone is insufficient; if a rear corner
would overlap an observed hazard, selection moves to a nearby valid pose on the
observed proposal. Nav2 independently checks its planned and executed path.
The search runs in a spawned worker process while ROS callbacks continue. It
returns its best checked proposal after 50,000 expansions or five seconds of
search, with budget diagnostics; no safe progress still returns no proposal.
An eight-second external timeout covers preprocessing and worker failures and
stops the mission. Endpoint scoring prioritizes destination progress over a
short dead-end approach while retaining obstacle costs in path search.
When no route is observed, the mission cancels navigation and waits for new
observations. After ten seconds without a safe forward route it may request up to two
collision-checked Nav2 backups, selecting 0.6–1.8 m from observed clearance,
at 0.1 m/s per broad destination. If either
fails or the same destination requires a third backup, it stops. Lack of actual
motion for 20 seconds or two failed Nav2 actions also triggers this bounded recovery.
Navigation cancellation must finish before recovery starts. Final stop and action
cancellation are attempted independently so one service failure cannot skip both.

Current user-requested profile: inflation radius 0.30 m, decay factor 5,
and local soft-cost multiplier 2. This narrows the heatmap; the actual padded
robot footprint and swept collision checks are unchanged. Earlier 1.30 m
inflation results below are historical. Unknown,
lethal and inscribed cells retain their blocking semantics. Forward arc search
tracks heading through bends rather than clipping every step to the initial
heading. Observed detours can initially lead away from a GPS destination.
Nav2 reversing and pivot-to-heading are disabled; final goal orientation
does not trigger a spin. The adapter permits straight backup up to 0.1 m/s, stops pivots and
turns tighter than a 0.5 m radius rather than changing their checked curvature.
Normal forward course bends remain permitted. This can stop in confined areas;
it is not proof against every possible multi-step loop in an observed map.

Nav2 now uses Smac Hybrid-A* with forward Dubins motion, a 0.6 m minimum
turn radius, and the asymmetric footprint, paired with MPPI trajectory control.
This follows the [Nav2 controller/planner pairing guidance](https://docs.nav2.org/jazzy/configuration_and_development/tuning_guide/)
and [Smac configuration](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/planners_plugins/smac/smac_hybrid/configuring_smac_hybrid/).
The differential-drive robot is intentionally constrained to forward arcs for
ordinary navigation. The observed-goal search uses a 0.65 m turn radius and MPPI uses a 0.55 m lower bound; these are simulation tuning values, not measured steering limits. There is no static map or saved route. Dynamic costmap
heuristics are not cached across plans, and unknown space stays blocked.
MPPI uses its Ackermann motion constraint solely to enforce the forward-arc
preference on this differential-drive simulation, with no ordinary reverse
velocity. Its CostCritic checks the full footprint, while path/goal critics
balance progress and obstacle avoidance. The 14 m local costmap accommodates
the 2.8 s prediction horizon. See [MPPI guidance](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/mppi_controller/configuring_mppic/).
The requested inflation radius is smaller than the robot footprint. Smac must
use its full footprint checks rather than relying on inflation as a collision
proxy. Stock Jazzy 1.3.12 MPPI skips footprint evaluation at zero-cost centers;
the Docker build now applies a pinned source fix and runs its C++ collision
regression. Navigation launch rejects an unpatched MPPI installation. Rebuild
the Docker image before using this profile, including on Linux. This is a
user-selected tuning experiment, not proof of successful course completion.

Recovery searches observed rear clearance up to 1.8 m and requires a useful,
collision-checked forward continuation before issuing a backup. It selects the
shortest adequate candidate rather than repeatedly commanding 0.3 m. Nav2 still
collision-checks the actual maneuver; the timeout scales with requested distance,
and measured displacement must reach that distance before forward replanning.

The 0.30 m profile and adequate-recovery slice (2026-09-17) passed eight behavioral
recovery tests, including a synthetic corner requiring 0.9 m rather than 0.3/0.6 m,
and the actual MPPI C++ regression (24 GoogleTests plus its CTest result, no failures).
The rebuilt Docker image loaded the patched MPPI overlay; both live costmaps
reported 0.30 m, and all seven [live integration checks](evidence/sensor-autonomy/point3-integration.json)
passed. The [course attempt](evidence/sensor-autonomy/point3-partial-audit.json)
stopped after 1/6 destinations without executing a backup. No sampled or swept
barrel/barricade intersection was found; paint crossing is not certified by this audit.
Observed cell (206,209), centred at (22.95,2.85), overlapped the padded rear corner
at pose (22.207794,1.800248,-2.592244). Recovery correctly rejected its initial
rear sweep before any forward search. Removing padding would only permit about
0.013 m of reverse before intersection. This is not a backup-length/budget problem;
execution/observed-footprint agreement remains unresolved. A live longer backup
and successful first-time full lap are not yet validated.

`sensor-run.progress.json` exposes current progress. On failure, the observed
costmap is saved as `sensor-run.observations.json` for diagnosis, never loaded
as a navigation input. `/sim/autonomy_stop_reason` identifies latched safety stops.

Observed-goal search runs in a separate process with a five-second search budget
and an eight-second outer deadline. It returns only collision-checked progress
found within that budget. The global-map freshness limit is five seconds because
Smac can hold the map during a two-second search; odometry, local control and
the 0.75-second camera/depth watchdog retain their tighter limits. Every fresh
mission clears lane memory and the observed depth-ground prior before refilling
the costmaps, so earlier attempts do not supply terrain knowledge.
Local goals must be at least 0.4 m from the planning pose, outside Nav2's 0.3 m
arrival tolerance. Intermediate goals retain 1 m of checked continuation; the
reserve is waived when the checked path reaches the actual destination. This
provides stopping room, not a guarantee of an escape route from every dead end.

Lane re-entry now also consumes fresh `/perception/lanes/points`. A bounded,
deterministic geometric detector looks for two supported, nearly parallel paint
segments with at least 3 m overlap and 1.2–8 m separation. It proposes a visible
mouth when outside the pair or an observed centre ahead when inside. Single
stripes, short clusters and intervening parallel barriers cannot establish a
corridor. Every proposal still passes through the observed-grid footprint
planner; a blocked entrance does not silently fall back to direct GPS guidance.
No course geometry or barrel positions are supplied to this detector.
See [ramp descent lidar filtering](RAMP_DESCENT_FILTER.md) for the separately
diagnosed road-return wall and marking/clearing separation.

Eleven corridor geometry tests, two collision/guidance integration tests and five
mission-contract tests passed. At the already-trapped pose, recorded observations
contained only one usable boundary and correctly produced no corridor; practical
re-entry from an earlier approach remains subject to live validation.
Direction memory bridges brief gaps using only the last accepted observed pair,
bounded to 20 m cumulative odometry travel and 60 seconds. It does not infer
lane edges or free space. The broad destination overrides this preference when
more than 60 degrees off the remembered direction, preventing an old straight
from dominating a corner. A fresh mission creates fresh memory.

Previous strict-forward-profile validation: 15 local-planner tests and two command-policy tests
passed. Four [live command-gate checks](evidence/sensor-autonomy/forward-policy.json)
confirmed reverse, pivot and tight-turn commands stop while a forward command
passes. Live parameters confirmed 0.65 m inflation and disabled pivot-to-heading.
This validates the command policy, not full-course completion.

Limited-backup update: 17 planner/command unit tests passed; the local Docker
image rebuilt successfully and both live inflation parameters read 0.5 m.
All six [live command checks](evidence/sensor-autonomy/limited-backup-policy.json)
passed, including slow straight backup and rejection of reverse turns, pivots,
and faster reverse. This does not yet establish full-course recovery success.

Earlier sensor validation used a 0.7 m/s ceiling. The requested ceiling is now
2.2 m/s with 7 m observed lookahead and controller pruning, and wider MPPI
velocity sampling (0.4 m/s standard deviation). These are pending live speed
validation of sustained 2.2 m/s travel. A [60-second live recording](evidence/sensor-autonomy/cruise-speed.json)
measured 1.423 m/s peak and 0.820 m/s mean on samples with yaw rate below
0.1 rad/s and speed above 0.05 m/s; commanded and measured peak speeds matched.
This is a course sample, not a controlled top-speed certification. The supplied
[2026 rules](https://www.igvc.org/2026rules.pdf) specify five **miles per hour**
(2.2352 m/s), not five metres per second; the 2027 limit remains unverified.
A simple
observed-grid search is not a complete exploration planner: unseen detours or
dead ends can stop it. It never falls back to the generated guide. Localization,
rendered depth and drive dynamics retain the simulator's ideal assumptions.

## Validation for the public preview (2026-09-16)

### Subsequent local Smac/MPPI test

Latest outer-band layout test (2026-09-17): 2/6 destinations, four 0.3 m backup
recoveries, then a controlled stop for no safe forward route. The
[audit](evidence/sensor-autonomy/outer-band-partial-audit.json) reports no obstacle
intersections, 0.152 m minimum sampled clearance and 1.474 m/s maximum interval
speed. This run did not reach the ramp or return to start. Lane re-entry and
obstacle recovery remain unresolved; the separate successful manual descent
test does not change that result. All seven live
[sensor/clock/TF integration checks](evidence/sensor-autonomy/lane-ramp-integration.json)
passed. The local Docker image rebuilt and passed environment checks, including
availability of the new scan filter executable. Public image publication and a
fresh native Linux graphical run are not claimed.

The fresh sensor-led run with ground tracking reached 3/6 destinations and
traversed the ramp from entry to exit. The [independent audit](evidence/sensor-autonomy/smac-mppi-partial-audit.json)
found no sampled or swept obstacle intersections, minimum sampled clearance
0.222 m, and maximum interval speed 0.317 m/s. It stopped at an observed lane
boundary after two 0.3 m backups; it did not return to start. Saved-grid replay
found repeated 0.255 m local goals inside Nav2's 0.30 m acceptance tolerance,
and no useful forward continuation in the current search lattice.

The subsequent minimum-goal/continuation safeguards passed all 28 planner tests.
A second fresh-memory run stopped on the opening straight after two backups,
with no obstacle intersections but no destinations completed; [audit](evidence/sensor-autonomy/continuation-partial-audit.json).
Therefore neither this safeguard nor the earlier ramp success establishes a
full lap. Controller/perception behavior near lane edges remains unresolved.

The local Docker image built successfully and independently passed Ubuntu 24.04,
Jazzy, eleven package and ten mesh-reference checks. This is local validation,
not a claim that the public image or a native Linux graphical run was updated.

### Earlier preview evidence

- Windows Unity build succeeded. The rebuilt Docker image passed environment
  checks for Ubuntu 24.04, Jazzy, nine required packages and ten mesh references.
- All 21 planner/export/mission-contract tests and 15 Linux launcher tests passed.
- The rebuilt image connected to the Windows player and passed all seven live
  sensor/clock/TF checks; [record](evidence/sensor-autonomy/integration.json).
- A sensor-led attempt reached two of six broad destinations, passed the first
  bend and barrel section, and stopped when its conservative local search had
  no route. No lane contacts or obstacle intersections were recorded; minimum
  sampled obstacle clearance was 0.299 m at 0.7 m/s. The independent
  [partial-run audit](evidence/sensor-autonomy/partial-audit.json) correctly fails
  completion, return and ramp traversal.
- The subsequent half-width/recovery version stopped on the perception safety
  gate before reaching its first destination. Recovery completion and a full
  sensor-led lap have **not** been demonstrated. The safety gate remains enabled.
- Linux launcher behavior was tested; this Unity change was built and exercised
  on Windows. A new native Linux graphical run remains pending.

This is an experimental release, not a completed autonomous competition robot.
The old guided lap results must not be reported as success for this mode.
