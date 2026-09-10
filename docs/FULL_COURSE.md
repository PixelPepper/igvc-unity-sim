# Full-course development run

Current status: **the fresh rolling-horizon run completed all 77/77 checkpoints**. The live audit remained valid and continuous, reaching 99.7987% of the 152.130591 m planned route arc. It measured 153.333311 m traveled and a final position error of 0.293905 m. The recorded trajectory spans 81.12 simulation seconds between its first and last samples, with no timestamp gaps, recoveries, backups or Unity line-guard blocks.

The independent sampled clearance audit passed (`full_run_sampled_evidence_passed=true`): minimum rectangle-to-barrel clearance was 0.212114 m, with no sampled intersections. Maximum observed speed was 2.2 m/s. Across 53 opening-straight intervals at X=3–16 m, minimum speed was 2.1999998 m/s and median speed was 2.2 m/s. Stopped painted/unmarked transitions remain intentional. This validates the ideal kinematic fixture, not tire/contact physics or hardware autonomy.

Evidence: [live run](../artifacts/checks/full-course-live.json), [sampled clearance audit](../artifacts/checks/full-course-clearance.json), and [trajectory plot](../artifacts/checks/full-course-trajectory.png). The associated build passed 28 Unity checks and built all seven ROS packages. Earlier archived attempts remain separate: `course-attempt-20260909-031334` stopped at 35/77 checkpoints; `course-attempt-20260909-030654` has invalid timing evidence.

The planned loop is 152.13 m with 77 ordered GPS guide points. It follows the two imported painted sections and an explicitly planned connection through the unpainted barrel section. The original geometry is unchanged. `config/full_loop.json` under igvc_gps contains named geodetic goals, tangent headings, painted/unmarked tags and a dense route for auditing. `tools/plan_course_loop.py` regenerates it; `artifacts/checks/course-route.png` labels every goal.

Current controller speed is capped at 2.2 m/s, below the 2027 maximum of 5 mph (2.2352 m/s); see [rules version 7, section I.2, page 6](https://www.gl-systems-technology.net/uploads/3/4/7/2/34727963/igvc_2027_rules_version_7_july_26.pdf). Nav2 slows for curvature, obstacles and approaches. Inflation radius is now 0.75 m (previously 1 m), with cost scaling 5 (previously 3) for faster cost decay. The rectangle X=[−1.1,+0.6], Y=[−0.5,+0.5] and 0.02 m padding are unchanged.

`tools/full_course.py` now runs a rolling horizon of three consecutive poses through `NavigateThroughPoses`. Only the physical audit cursor advances the next required checkpoint, using a 0.4 m visit tolerance. The custom behavior tree removes passed poses at 0.35 m. As a checkpoint is passed, the runner preempts the same action with the next horizon without canceling navigation or toggling the gate. It retains stopped transitions between painted and declared unmarked sections. The old `run_stop_go` method remains in the source but is unused.

The runner's speed governor measures distance to the last active horizon pose, normally rolling 4–6 m ahead, rather than braking at every intermediate checkpoint. Final arrival and shortened zone-transition horizons still brake. It uses `approach_speed(distance)` with 2 m/s² braking, 0.2 s latency and a 0.2 m arrival reserve. It clamps the braking-derived limit to 0.05–2.2 m/s; zero means unlimited to Nav2, so arrival/cancel handling supplies the actual stop. Unity retains linear acceleration/deceleration of 2 m/s² and angular acceleration of 3 rad/s². Its launch ramp scales the angular target with achieved linear speed to avoid a tighter initial turn. Both the ROS bridge and Unity proportionally saturate linear/angular commands when limits are exceeded, preserving their curvature; angular velocity remains limited to ±1 rad/s. These are ideal kinematics, not measured drivetrain behavior. See [navigation tuning](NAVIGATION.md).

From the project PowerShell terminal, with the course and Nav2 running and the robot stationary at its original start:

```powershell
.\tools\igvc.ps1 loop-run
```

Use a separate terminal for these commands:

```powershell
.\tools\igvc.ps1 loop-status
.\tools\igvc.ps1 loop-resume
.\tools\igvc.ps1 loop-cancel
```

`loop-resume` explicitly retries the same unfinished waypoint after a paused failure. It never skips a waypoint. `loop-cancel` ends the mission. After a deliberate stopped process restart, `loop-run -Resume` loads the saved audit, requires the same simulation run and pose within 0.1 m, and retains all completed checkpoints. The operator must keep the robot stopped during that observer gap. A reset or invalidated audit cannot be resumed. Do not start a second mission or send competing teleop/goal commands.

The mission continuously audits odometry against local ordered route progress, actual waypoint locations, a 2.2 m centerline deviation limit, a maximum 2 m backwards excursion, and teleport/time/reset checks. Completion needs every physical checkpoint in order, successful final Nav2 arrival and at least 98% of route arc, plus the final goal at the original start. Approaching the start through a shortcut cannot satisfy this. These audit limits supplement the independent Unity paint guard and Nav2 obstacle checks.

A Nav2 goal failure permits one collision-checked 0.5 m BackUp recovery at 0.1 m/s, followed by retrying that same waypoint. Recovery cannot select an earlier route or jump to the final goal. Other failures pause with autonomy disabled and keep the observer alive. The mission does not call reset, clear costmaps or teleport.

Painted sections require current camera lane observations. The declared unpainted connection allows zero paint detections but still requires successful fresh camera/CameraInfo/TF processing, advancing GPS, lidar and odometry. The transition includes a short approach/exit margin because the level camera looks several metres ahead. Any detected paint still marks Nav2 costs and the Unity boundary guard remains enabled. This mode is explicit through `/sim/set_unmarked_mode`; manual teleop clears it. This is a route-assisted development fixture, not a claim of competition-compliant course memorization or hardware autonomy.

RViz's orange `/mission/route` shows the ordered goal guide, and green `/mission/driven` shows the actual trajectory. The guide chords are not collision-free controller paths; Nav2 computes those from current sensors. `artifacts/checks/full-course-live.json` records waypoint results, pauses, run identity, poses and audit status. A file marked paused/failed is not a successful full run.
