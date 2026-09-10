# Terrain-relative RGB lane and hazard projection

RGB lane paint and dark-bowl hazard pixels now intersect the observed depth ground plane instead of a fixed world Z=0 plane. `lane_node.py` uses `GroundHistory` from `terrain_history.py` to join independently timed depth estimates with RGB acquisitions, then calls `terrain_projection.py:project_plane`. Course geometry is not an input to these perception functions.

Each RGB image still requires exact-stamp CameraInfo and `odom <- camera_color_optical_frame` TF at its own acquisition time. The selected ground estimate must precede or equal that RGB stamp, be at most 0.35 simulation seconds older, and have arrived within 0.5 monotonic seconds. The newest eligible estimate is selected from a bounded eight-entry history. Its confidence must satisfy the depth estimator's existing fraction, RMS and slope limits. Failed or malformed depth status clears the history; backward depth timestamps also clear prior history. There is no fixed-plane fallback when a fresh causal estimate is unavailable.

`project_plane` rotates calibrated optical rays into odom and intersects `normal · point + offset = 0`. It rejects parallel rays, intersections behind the camera, nonfinite results and points outside the default 1–10 m horizontal range from the camera. Lane and hazard clouds retain XYZ in odom. The node accumulates observations in 7.5 cm XY cells with an eight-second monotonic TTL, bounded to 8,000 lane and 4,000 hazard cells. This observation history is distinct from the separate Nav2 layers' 0.75 s cloud-expiry policy.

The 200 ms steady processing timer and existing watchdog thresholds are unchanged; see [ROS timing](ROS_TIMING.md). Missing ground prevents successful projection and publishes invalid/unhealthy status. Fresh ground restores processing but does not automatically rearm autonomy after a latched stop. `/perception/lanes/status` includes `stamp_ns`, `ground_stamp_ns`, `ground_age_s` and the selected `ground` coefficients. Its `valid` flag means sufficient current paint was found; it is not synonymous with successful camera processing in an unmarked zone.

Validation evidence:

- [42 perception tests](../artifacts/checks/terrain-lanes-tests.txt) passed, covering the pure projection/history helpers alongside existing perception checks.
- [Three saved GPU fixtures](../artifacts/checks/terrain-lanes-render.json)—flat, raised and inclined—passed independent surveyed-plane projection checks. Maximum errors were 0.00009243 m, 0.00010562 m and 0.00004270 m respectively, all below 0.000106 m. These are rendered depth fits plus mathematical projection checks, not moving-terrain or RGB segmentation validation.
- The [30-second live join verifier](../artifacts/checks/terrain-lanes-live.json) passed 145 matching ground records and 145 finite nonempty odom clouds, with maximum ground age 0.28 s and no errors. One missing fit was exempted during discovery. It recorded 38 statuses without sufficient paint; accumulated clouds do not prove fresh paint in every frame. This verifies received coefficients/timestamps, not surveyed live geometry or costmap causality.
- All [five depth-watchdog checks](../artifacts/checks/depth-watchdog-live.json) passed: fresh enable, stale-depth stop, depth-loss invalidation of lane projection, no automatic rearm, and restored projection after fresh ground.

The terrain-projection regression [seed-2027 normal run](../artifacts/courses/seed-2027/previous-20260909T165937347415Z/run.json) completed all 78 checkpoints without pauses, recoveries or line-guard blocks. Its [audit](../artifacts/courses/seed-2027/previous-20260909T165937347415Z/validation.json) passed with 0.69034 m minimum sampled clearance, 0.55534 m conservative swept clearance, 0.29352 m finish error and 2.2 m/s maximum observed speed. This is flat-course integration evidence, not moving-ramp validation. The preceding depth/timer regression is [archived separately](../artifacts/courses/seed-2027/previous-20260909T164059627191Z/validation.json). To repeat the read-only live check from the repository root in PowerShell:

```powershell
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/verify_terrain_lanes.py --duration 30
```

The shared plane assumes locally stationary terrain during the permitted age interval. One plane cannot represent nonplanar transitions, steps or multiple surfaces; a broad obstacle top can satisfy the geometric estimator without being traversable ground. Dark-bowl pixels projected onto surrounding ground are approximate hazard locations, not measured negative-obstacle depths. These checks do not validate semantic terrain recognition, actual ramp contact, suspension/body attitude or complete ramp navigation. See [depth-camera limitations](DEPTH_CAMERA.md).
