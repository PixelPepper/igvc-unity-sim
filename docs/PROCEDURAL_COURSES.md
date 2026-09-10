# Procedural course variants

Newly generated variants now include a ramp and reduced-order caster suspension. Current seed 2027 / normal has 82 ordered checkpoints and 34 obstacles (24 barrels, eight barricades, two potholes). The [integrated course-ramp slice](COURSE_RAMP.md) passed 11 live checks at 0.6 m/s over 1,042 joined observations, reaching 0.400000046 m axle height with zero line-guard blocks and sensors present. This is a bounded manual traversal, not an autonomous ramp full-course pass; that validation remains pending.

**Historical flat seed 2027 / normal completed all 78/78 checkpoints** with dynamic body TF, [terrain-relative RGB lane/hazard projection](TERRAIN_LANES.md), depth filtering and steady ROS timers. That archived course used planar motion; the separate [terrain bench](TERRAIN_BODY.md) is selected with `terrain-build` / `terrain-start -Visible` and has manual ramp validation only. Its [run](../artifacts/courses/seed-2027/previous-20260909T202724060370Z/run.json) and [geometric validation](../artifacts/courses/seed-2027/previous-20260909T202724060370Z/validation.json) passed with no pauses, recoveries, line-guard blocks or timestamp gaps: minimum sampled clearance 0.70579 m, conservative swept clearance 0.54300 m, finish error 0.29383 m and maximum observed speed 2.2 m/s. [Depth and health evidence](DEPTH_CAMERA.md) covers the current pipeline; [timer diagnostics](ROS_TIMING.md) explain the earlier paused regression and unchanged watchdog thresholds.

Seed 2028 / easy completed 78/78 and seed 2029 / hard completed 81/81 before depth integration. Earlier [RGB sensor verification](../artifacts/courses/seed-2027/previous-20260909T141807592352Z/sensors.json) recorded three fresh positive hazard frames, up to 139 manifest-matched hazard points and 1,461 marked costmap-cell observations; these historical observations are not new measurements from the latest run or 1,461 distinct hazards. Earlier validation includes 53 camera checks, 42 perception tests, 25 tool tests (six generator, thirteen audit and six speed tests), three GPU terrain fixtures, the Unity build and seven ROS package builds. Those sensor/math checks were not rerun for this body-TF regression; terrain, drive and course players were rebuilt. The preceding terrain-lane run is [archived](../artifacts/courses/seed-2027/previous-20260909T165937347415Z/validation.json). The imported-course result remains separate in [FULL_COURSE.md](FULL_COURSE.md).

## Generate and run

Historical validated flat layouts (all capped at 2.2 m/s, with no reset, audit gaps or paint-guard interventions):

| Seed / difficulty | Checkpoints | Barrels / barricades / potholes | Minimum sampled clearance |
| --- | --- | --- | --- |
| [2027 / normal](../artifacts/courses/seed-2027/previous-20260909T202724060370Z/validation.json) | 78/78 | 24 / 8 / 2 | 0.706 m |
| [2028 / easy](../artifacts/courses/seed-2028/validation.json) | 78/78 | 16 / 4 / 1 | 0.850 m |
| [2029 / hard](../artifacts/courses/seed-2029/validation.json) | 81/81 | 36 / 12 / 3 | 0.711 m |

The archived seed-2027 flat run included terrain-relative depth filtering and RGB lane/hazard projection onto a fresh preceding depth plane. The previous depth/timer run is [archived](../artifacts/courses/seed-2027/previous-20260909T164059627191Z/validation.json). Easy/hard results and the archived RGB pothole sensor check predate depth integration.

The refreshed [comparison plot](../artifacts/courses/variant-comparison.png) overlays the historical flat seed-2027 trajectory with historical seed-2028/easy and seed-2029/hard trajectories. [Combined validation](../artifacts/courses/validation-summary.json) retains all three results; `suite.json` records only the most recent batch invocation. These displayed completed attempts finished without manual resume. The hard layout used one bounded 0.5 m backup, then retried the same checkpoint; its ordered full-loop audit still passed. Easy and normal needed no recovery. Prior failed development attempts remain archived. Three passing layouts do not guarantee every seed or real-world terrain will pass. The current camera/hazard appearance is synthetic and lighting is fixed.

Use PowerShell at the project root. Stop the existing simulator before generating or selecting a variant:

```powershell
.\tools\igvc.ps1 stop
.\tools\igvc.ps1 variant-generate -Seed 2027 -Difficulty normal
```

`-Difficulty` accepts `easy`, `normal` or `hard`. The same seed and difficulty regenerate the same geometry and mission with the same generator version. Existing run evidence is archived into a timestamped `previous-*` directory before regeneration. Outputs live under `artifacts/courses/seed-2027/`; the directory name is seed-based, so changing difficulty for the same seed replaces its active variant.

`variant-start` generates the selected variant and starts the Unity player plus its ROS bridge. It requires an existing course build (`course-build`) and does **not** start Nav2:

```powershell
.\tools\igvc.ps1 variant-start -Seed 2027 -Difficulty normal -Visible
.\tools\igvc.ps1 nav-start
.\tools\igvc.ps1 rviz
.\tools\igvc.ps1 loop-run
```

`variant-start` also regenerates the files; running `variant-generate` first is useful for inspection but is not required. In another terminal:

```powershell
.\tools\igvc.ps1 loop-status
.\tools\igvc.ps1 loop-cancel
.\tools\igvc.ps1 variant-audit -Seed 2027
```

The auditor reads the saved variant `course.json` and `run.json`. An interrupted or incomplete run is not a pass. `loop-resume` explicitly resumes a paused mission at the next unvisited checkpoint; it does not regenerate geometry or skip checkpoints. See [the full-course guide](FULL_COURSE.md) for observation continuity and stopped process-resume requirements.

## Bounded multi-seed runs

Run a suite from PowerShell:

```powershell
.\tools\run_variant_suite.ps1 -Seeds 2028,2029 -Difficulty normal -TimeoutSeconds 180 -Visible
```

The single difficulty applies to **every** listed seed; this example runs both at normal. Use separate invocations to test different difficulties. The timeout is per mission, defaults to 180 seconds and accepts 60–600 seconds. The suite cancels an existing mission, then stops/restarts the simulator and Nav2 for each regenerated variant. Prior evidence is archived by the generator. It records per-seed validation and `artifacts/courses/suite.json`.

A pause, failure or timeout triggers cancellation and audit; the suite does not automatically resume a paused attempt. It waits for the observer to exit before switching maps and stops the suite if cancellation is not acknowledged. The last course remains available and stopped for inspection. A suite summary can contain failed runs; inspect each validation result.

## What varies

The generator applies bounded lateral offsets and chicanes to the verified reference layout, retaining its overall topology and ordered mission. It places barrels, barricades and occasional potholes with geometric clearance checks. This provides reproducible variations of one course family, not arbitrary topology generation, an exact 2027 competition layout or configurable lighting.

Unity creates native ground and obstacle geometry. Potholes use cutouts in the otherwise flat ground and dark, depressed bowl meshes. New variants add a 3 m wide, 0.4 m high ramp starting at ROS (2,0), with a 3 m rise, 2 m deck and 3 m descent. The opening guide crosses its center with ordered approach/start/deck/exit checkpoints; obstacles are excluded from the ramp plus approach/exit and side margins, including full pothole rims. Body support and provisional rear spring/damper travel follow the explicit ground geometry. This remains kinematic support, not vertical wheel contact, traction or falling into holes. The rendered bowls are perception/avoidance fixtures. An ideal geometric depth stream is now available; stereo matching and its errors are not simulated.

The generator's known geometry supports GPS guide construction, physical checkpoint auditing and offline clearance scoring. It does not inject pothole locations or obstacle detections into autonomous perception.

## Camera and hazard observations

The camera defaults to **10° downward**, positive about ROS +Y, configured by `default_simulation_pitch_rad` in `ros2/src/igvc_description/config/camera_mount.json`. Runtime absolute pitch commands use `/sim/camera_pitch_command` (`std_msgs/Float64`, radians); reset restores the configured default. This is a project setting, not a measured angle from the reference report.

RGB/CameraInfo and acquisition-time TF project dark compact image regions onto a fresh preceding depth-estimated ground plane, with no fixed-Z fallback. This assumes locally stationary planar terrain; it does not validate nonplanar transitions or ramp contact. The detector rejects broad patches, image-edge silhouettes and orange-adjacent regions; shadows and other dark objects can still resemble the synthetic bowls. This is not general negative-terrain reconstruction.

`/perception/hazards/points` carries camera-derived odom points; `/perception/hazards/debug` carries the image mask. Current hazard counts appear in `/perception/lanes/status`. Both Nav2 costmaps use a separate hazard layer, independent of lidar clearing. It replaces observations and expires stale clouds after 0.75 wall seconds; the detector separately keeps up to eight seconds of bounded point history. The existing independent paint guard remains enabled.

## Evidence to collect

The run and variant audit record ordered completion, speed, interventions, timestamp continuity and sampled clearance. `tools/verify_variant_sensors.py --course <course.json> --duration 100`, run through `tools/run_ros.sh` in WSL, additionally writes sibling `sensors.json`, `hazard-rgb.png` and `hazard-mask.png` when positive observations are captured. It compares projected points with manifest potholes only for verification and reports unobserved cases explicitly.

Reference rationale and source limitations are documented in [2026_WINNER_LESSONS.md](2026_WINNER_LESSONS.md). In particular, the supplied video is a 2023 Sooner run, while the supplied report is their 2026 design submission.
