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

Each mission clears the Nav2 costmaps before collecting new observations. No
static map, generated route, dense checkpoints or known gap locations enter the
mission. GPS origin defines the coordinate frame; positioning currently uses
ideal simulator odometry, matching the synthetic GPS model. Hardware GPS fusion
and realistic odometry drift remain separate work.

The local selector uses a 0.5 m half-width approximation plus grid padding; Nav2
retains the complete asymmetric rectangular footprint for execution. Nav2's 99
cost cells already represent inscribed inflation and block centres without being
dilated again; lethal 100 paint/obstacles and unknown space receive clearance.
When no route is observed, the mission cancels navigation and waits for new
observations. After ten seconds without a safe forward route it stops. Backup
recovery is disabled by the user's updated preference.

Current forward-motion profile: inflation radius 0.65 m (previously 0.75), decay
factor 8 (previously 5), and local soft-cost multiplier 2 (previously 4). Unknown,
lethal and inscribed cells retain their blocking semantics. Search steps stay
within 80 degrees of the current heading, and destinations behind the robot are
rejected. Nav2 reversing and pivot-to-heading are disabled; final goal orientation
does not trigger a spin. The adapter stops autonomous reverse/pivot commands and
turns tighter than a 1 m radius rather than changing their checked curvature.
Normal forward course bends remain permitted. This can stop in confined areas;
it is not proof against every possible multi-step loop in an observed map.

Forward-profile validation: 15 local-planner tests and two command-policy tests
passed. Four [live command-gate checks](evidence/sensor-autonomy/forward-policy.json)
confirmed reverse, pivot and tight-turn commands stop while a forward command
passes. Live parameters confirmed 0.65 m inflation and disabled pivot-to-heading.
This validates the command policy, not full-course completion.

Initial sensor validation speed is 0.7 m/s; the 2.2 m/s ceiling remains. A simple
observed-grid search is not a complete exploration planner: unseen detours or
dead ends can stop it. It never falls back to the generated guide. Localization,
rendered depth and drive dynamics retain the simulator's ideal assumptions.

## Validation for the public preview (2026-09-16)

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
