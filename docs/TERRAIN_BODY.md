# Experimental terrain-supported body

New generated course variants now integrate a ramp and reduced-order caster suspension; see [course-ramp integration](COURSE_RAMP.md). Current seed 2027 / normal has 82 checkpoints and 34 obstacles. Its bounded 0.6 m/s course-ramp traversal passed 11 checks over 1,042 joined observations, reaching 0.400000046 m axle height with zero line-guard blocks and sensors present ([report](../artifacts/checks/course-ramp-20260909-132734.json)). No autonomous ramp full-course pass has yet been established. The rigid bench evidence below remains a separate historical model check.

The default terrain bench now uses [rear caster spring/damper support](CASTER_SUSPENSION.md). The three-point model and evidence below describe the earlier rigid mode, which remains available with `terrain-start -RigidTerrain`. Its original dimensions and analytic checks are intentionally unchanged.

The ramp bench adds kinematic body height and attitude from three provisional support points. `TerrainSupport.cs` samples only explicitly supplied ground colliders: two points at local Unity X ±0.35 m on the driven axle and one at local Unity Z −0.85 m behind it. These are provisional support dimensions, not calibrated tire or caster contact locations. The fitted support normal determines body attitude; a missing sample, degenerate fit or slope above 15° rejects movement. Ground colliders are simulation support inputs, not autonomy perception inputs.

The bench is flat before ROS X=2 m, rises linearly to 0.4 m over X=2–5, stays level over X=5–7, descends over X=7–10, then returns to zero. The body origin retains its axle-relative offset of 0.25591 m rearward and 0.30385548 m upward, rotated by the support attitude. Candidate motion is checked against its actual 3D axle displacement before committing; reducing the planar step prevents the slope-entry overspeed that can occur when scaling only by the previous pitch. The normal motion cap remains 2.2 m/s.

`base_footprint` odometry remains planar (Z=0 and yaw only). Unity publishes `/sim/body_transform` as a stamped `base_footprint -> base_link` transform; the ROS bridge is now the sole TF authority for that dynamic edge. Body height and roll/pitch propagate through the existing relative lidar, camera and wheel frames. Wheel phase and reported velocity still derive from synthetic planar distance, so they are not measured wheel travel on the ramp.

After migrating from a static base transform, restart RViz once to discard its cached static `base_link` edge. Older player binaries must be rebuilt with `course-build` or `drive-build` before using the new bridge/TF arrangement.

From the repository root in PowerShell:

```powershell
.\tools\igvc.ps1 stop
.\tools\igvc.ps1 terrain-build
.\tools\igvc.ps1 terrain-start -Visible -RigidTerrain
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/verify_terrain_body.py --speed .3
```

The verifier performs manual motion: after receiving a fresh stationary-origin odometry/body pair, it commands straight travel at 20 Hz, stops issuing forward commands at X≥11, and repeatedly sends zero in `finally`. It waits at most ten seconds for preflight, limits traversal to 55 wall seconds, and stops on missing fresh pairs or validation failure. It sends no reset, autonomy enable or navigation goal. Deceleration means the final stopped X can exceed 11. For the fast check, start a fresh bench at its origin first, then run:

```powershell
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/verify_terrain_body.py --speed 2.2 --report artifacts/checks/terrain-body-fast.json
```

The Unity build passed 13 terrain-support checks; see [build log](../artifacts/logs/terrain-body-unity-build.log). Both live traversals passed independent analytic support-height/pitch checks, exact-stamp transform pairing, ascent/descent/deck/final-height checks, planar footprint checks and absence of a static `base_link` transform:

| Evidence | Matched pairs | Maximum axle 3D chord speed | Maximum position / pitch error |
| --- | ---: | ---: | ---: |
| [0.3 m/s traversal](../artifacts/checks/terrain-body-live.json) | 1,889 | 0.3000 m/s | 0.000000481 m / 0.000000155 rad |
| [2.2 m/s traversal](../artifacts/checks/terrain-body-fast.json) | 324 | 2.2000 m/s | 0.000000462 m / 0.000000148 rad |

Both observed approximately ±0.13255 rad pitch, a 0.70386 m deck body height and return to 0.30386 m body height. These small errors demonstrate agreement with the implemented ideal model, not hardware accuracy. The historical flat [full-course regression with dynamic body TF](../artifacts/courses/seed-2027/previous-20260909T202724060370Z/run.json) completed all 78 checkpoints without pauses, recoveries or line-guard blocks. Its [audit](../artifacts/courses/seed-2027/previous-20260909T202724060370Z/validation.json) passed with 0.70579 m minimum sampled clearance, 0.54300 m conservative swept clearance, 0.29383 m finish error and 2.2 m/s maximum observed speed. Terrain, drive and course players were rebuilt. That archived normal course retained planar movement; it validated the TF migration in that mode, not autonomous terrain following. The preceding terrain-lane run is [archived](../artifacts/courses/seed-2027/previous-20260909T165937347415Z/validation.json).

This is support interpolation, not gravity, suspension, traction, tire forces or contact collision resolution. It does not establish underbody clearance or safe traversal of arbitrary terrain. Depth ground fitting and RGB projection retain their separate single-plane and terrain-semantic limitations; neither the bench nor these manual tests establish complete ramp autonomy.
