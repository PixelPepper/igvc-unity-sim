# Ramp in procedural courses

New generated variants include one ramp on the opening straight, with reserved obstacle clearance and ordered guide checkpoints. The active seed-2027 normal course has 82 checkpoints, 24 barrels, 8 barricades and 2 potholes. Its previous successful flat-course run is preserved in `artifacts/courses/seed-2027/previous-20260909T202724060370Z/`; that result does not validate this changed course.

The current autonomous [seed-2027 run](../artifacts/courses/seed-2027/run.json) completed all 82 checkpoints. Its [12-check audit](../artifacts/courses/seed-2027/validation.json) passed with no reset, audit gaps or line-guard blocks, maximum observed speed 2.2 m/s, 0.703277464 m sampled clearance and 0.536494889 m conservative swept clearance. See [ramp-edge perception](RAMP_EDGE_PERCEPTION.md) for the surface-based changes and remaining limitations.

## Geometry and behavior

The ramp starts at ROS (2,0), faces +X and is 3 m wide. A 3 m slope rises 0.4 m, followed by a 2 m deck and 3 m descent, ending at x=10. Its approximately 7.59-degree slopes match the validated bench. These are provisional practice dimensions, not a claim of 2027 compliance.

The generator straightens the opening through the ramp, reserves approaches and sides against obstacles (including full pothole rims), and inserts mandatory waypoints at x=1,2,5,7,10,11 in increasing route order. GPS/Nav2 targets remain horizontal coordinates; the simulation's terrain support controls body elevation. No ground mesh or ramp label is supplied to perception.

Unity builds visible, sensor-observable static ramp colliders and supplies only the ground and ramp as body supports. Rear caster suspension and swivels remain active. Body height/pitch and slider TF reach ROS/RViz through the existing dynamic transform chain. The planar axle datum and speed cap remain unchanged. Pothole cutouts provide no flat fallback support; their bowl/rim visuals are not suspension supports. This is still reduced-order motion, without tire friction or contact dynamics.

The nominal 6 m corridor now tapers to white stripe centers at Y=±1.44 m on the ramp. Each 0.12 m stripe extends to ±1.5 m and follows the rise, deck and descent; there is no second outer parallel wide paint line. Existing manifests without `ramps` and the original imported reference course keep their planar behavior. Use `variant-start` for the new ramp course, not `course-start`.

## Validation

The final integration passed 58 perception tests, ten generator tests, 70 Unity ramp checks and the build. The following manual measurements describe the earlier 2026-09-09 integration stage, before the autonomous loop above. They remain historical evidence.


- Nine Python generator tests passed, covering deterministic variants, obstacle clearance and exact ordered ramp checkpoints across seeds/difficulties. The pothole exclusion uses its rendered radius plus 0.85 m rim.
- The course player and seven ROS packages built. Twenty-eight new Unity checks passed: surveyed ray heights across three orientations, continuous sprung crossing, settling and rejection of unsupported slopes. An initial test-source numeric-literal compilation error was corrected before the successful build.
- `artifacts/checks/course-ramp-20260909-132734.json`: all 11 live checks passed at 0.6 m/s, with 1,042 matched body/suspension/joint samples, 346 TF comparisons per caster, 0.400000046 m peak axle height and no lane-guard blocks. Lidar, RGB and depth samples remained present. This is manual motion/transport evidence, not perception correctness.
- The running Unity course was visually inspected after traversal with the ramp behind the robot and continuous surrounding lane paint.
- `artifacts/checks/course-ramp-fast-live.json`: all 11 checks passed at 2.2 m/s (about 4.92 mph), 417 matched samples and 135 TF comparisons per caster. Peak compression was 15.71 mm, peak axle height 0.400000047 m, measured axle speed stayed at the configured cap, and `line_blocks=0`. This remains a manual ideal-model test, not a recommended autonomous ramp speed.

## Run

```powershell
.\tools\igvc.ps1 stop
.\tools\igvc.ps1 variant-start -Seed 2027 -Difficulty normal -Visible
.\tools\igvc.ps1 course-ramp-test
```

The last command drives from a fresh origin at 0.6 m/s, then stops beyond the ramp; it never resets, teleports or arms autonomy. It refuses missing support/sensors, active autonomy or another manual command publisher. Reports use timestamped filenames under `artifacts/checks`. `F` toggles follow, `H` shows the course, scroll zooms, and right-drag orbits.

For camera-only diagnosis, use `perception-start`, then `perception-stop` before Nav2. The [earlier perception failures](TERRAIN_PERCEPTION.md) motivated observed-surface classification and depth-supported RGB projection. The new autonomous loop passed as recorded above; it does not establish calibrated physical ramp capability, general semantic terrain understanding or competition speed compliance.
