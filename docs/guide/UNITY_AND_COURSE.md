# Unity and course editing guide

This guide describes the checked-in implementation inspected on 2026-09-23. Start with the [README](../../README.md) and [project collaboration rules](../../AGENTS.md). Unity provides an ideal robot, rendered sensors and a generated environment; it is not a calibrated R3-a, full contact simulator, or proof of IGVC 2027 compliance. Older entries in [UnityProjectContext](../AI/UnityProjectContext.md) are historical snapshots and include superseded dimensions, obstacle counts and navigation settings.

## Contents

- [Open and build the project](#open-and-build-the-project)
- [Find the owning code](#find-the-owning-code)
- [Physical frames and sensor mounts](#physical-frames-and-sensor-mounts)
- [Terrain and caster approximation](#terrain-and-caster-approximation)
- [Keep the three course files separate](#keep-the-three-course-files-separate)
- [Change the generated layout](#change-the-generated-layout)
- [Regenerate, restart or rebuild?](#regenerate-restart-or-rebuild)
- [Validate the change you made](#validate-the-change-you-made)

## Open and build the project

Open `unity/IGVCSim` with **Unity 6000.3.23f1**; the exact version is recorded in [ProjectVersion.txt](../../unity/IGVCSim/ProjectSettings/ProjectVersion.txt). Rendering uses the Built-in pipeline. Preserve the dependency versions in [manifest.json](../../unity/IGVCSim/Packages/manifest.json), their lock file and Unity `.meta` files.

The normal Windows commands, from the repository root, are:

```powershell
./tools/docker.ps1 prepare-unity
./tools/docker.ps1 unity-build
```

Close this project's Editor before the batch build. Only one teammate should run the Editor, builds or simulator sessions at a time. [docker.ps1](../../tools/docker.ps1) writes the player to `artifacts/build-course/IGVCCourse.exe` and the build log to `artifacts/logs/docker-unity-build.log`. The corresponding Linux wrapper is [docker.sh](../../tools/docker.sh); its player is `artifacts/build-course-linux/IGVCCourse.x86_64`. Keep the whole player directory, not just the executable.

`prepare-unity` runs [prepare-unity.sh](../../docker/prepare-unity.sh), which obtains the pinned SoonerRobotics reference and runs [import_sooner_course.py](../../tools/import_sooner_course.py). Imported environment assets live under the ignored `Assets/IGVC/External/SoonerAutoNav` directory. Review [asset provenance](../../THIRD_PARTY_ASSETS.md) before redistribution; importing assets does not grant a new license.

The actual course build chain is:

1. [GroundRenderChecks.BuildCourse](../../unity/IGVCSim/Assets/IGVC/Editor/GroundRenderChecks.cs) renders ground fixtures, then calls [DepthChecks.BuildCourse](../../unity/IGVCSim/Assets/IGVC/Editor/DepthChecks.cs).
2. Depth checks call [SoonerCourseBuild.Build](../../unity/IGVCSim/Assets/IGVC/Editor/SoonerCourseBuild.cs), which runs ramp checks and recreates the course scene.
3. Course creation calls [R3aDriveBuild.CreateScene](../../unity/IGVCSim/Assets/IGVC/Editor/R3aDriveBuild.cs), which runs motion/kinematics/swivel checks and calls [ProbeBuild.CreateScene](../../unity/IGVCSim/Assets/IGVC/Editor/ProbeBuild.cs). [RobotInspectionBuild.CreateRobot](../../unity/IGVCSim/Assets/IGVC/Editor/RobotInspectionBuild.cs) imports the canonical URDF and simplified visuals.
4. The builder adds the imported environment, scan colliders, lane guard and spectator camera, then saves `Assets/IGVC/GeneratedRobot/SoonerAutoNav.unity`. `R3aDriveBuild.BuildScene` builds that scene for the selected Windows or Linux target.

**Builds recreate scenes.** Inspector edits to generated scenes, robot objects, materials or camera placement can disappear on the next build. Make durable changes in the responsible builder, runtime script or canonical configuration. The simpler generated `R3aDrive.unity` and static robot inspection player are separate fixtures, not substitutes for the course player.

## Find the owning code

| Area | Primary source and responsibility |
| --- | --- |
| Runtime coordinator | [TransportProbe.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/TransportProbe.cs): startup arguments, manifest loading, 0.01 s clock ticks, ROS connection, drive commands, pose, joints, scan and status |
| Motion | [ProbeMotion.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/ProbeMotion.cs): command limits, timeout, pause/E-stop; [R3aKinematics.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/R3aKinematics.cs): exact constant-twist axle integration |
| Images | [ProbeCamera.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/ProbeCamera.cs): RGB; [ProbeDepthCamera.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/ProbeDepthCamera.cs): metric optical-Z depth |
| Course world | [CourseVariant.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/CourseVariant.cs): manifest validation, generated ground, paint, barrels, barricades and potholes; [CourseRamp.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/CourseRamp.cs): ramp geometry and height queries |
| Paint scoring | [LaneBoundaryGuard.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/LaneBoundaryGuard.cs): geometric footprint/paint checks; [CourseLaneBuild.cs](../../unity/IGVCSim/Assets/IGVC/Editor/CourseLaneBuild.cs): imported reference paint |
| Viewing | [SpectatorCamera.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/SpectatorCamera.cs): user-controlled overview/follow camera |

## Physical frames and sensor mounts

**Large driven wheels are at the front; casters are at the rear.** Canonical ROS +X points toward the drive wheels, +Y is left and +Z is up. [prepare_description.py](../../tools/prepare_description.py) corrects the reversed source SolidWorks frame with a Z-pi rotation and physical left/right name mapping. Never restore source-frame forward or edit external CAD originals in place.

The canonical robot is [r3_a.urdf](../../ros2/src/igvc_description/urdf/r3_a.urdf). In drive mode, `base_footprint` is at the driven axle and `base_link` is 0.25591 m behind it. The Unity body offset also uses 0.30385548 m vertical height on flat ground. Unity positions map from ROS as `(-y, z, x)`; positive ROS yaw maps to negative Unity Y rotation. Kinematics uses CAD-derived wheel radius **0.229569608 m** and track width **0.81051 m**. These are model inputs, not measured calibration. See [R3-a drive](../R3A_DRIVE.md).

| Sensor | Canonical input and verified convention |
| --- | --- |
| Rear pole-top OAK-D Pro | [camera_mount.json](../../ros2/src/igvc_description/config/camera_mount.json): base-relative pivot `[-0.34396836, 0, 0.8]` m; body offset from pivot `[0.06290043, 0, 0.00447802]` m; optical offset from body `[0.01155045, 0, 0.00476378]` m |
| Front roof RPLIDAR A1 | [lidar_mount.json](../../ros2/src/igvc_description/config/lidar_mount.json): `base_link` parent, `lidar_link` scan frame; seat `[0.2700228, 0, 0.295]` m; scan origin `[0.2700228, 0, 0.3396]` m; visual offset `[0, 0, -0.0446]` m |

The camera mount **tilts up/down only**, about ROS +Y. Zero is level; positive pitch looks down. Its default is **0.1745329252 rad (10° down)**, limits are ±pi/6 (±30°), and simulated slew is 1 rad/s. The visual bracket moves with the camera; joint states feed robot_state_publisher's camera TF. Do not reintroduce a fixed fixture optical transform. Lidar TF likewise follows the canonical fixed mount. Optical center/scan-plane assumptions remain provisional; see [camera](../CAMERA_MOUNT.md) and [lidar](../LIDAR_MOUNT.md) evidence.

At startup, the serialized camera default is overridden by `course.json`'s `camera_pitch_rad`, then by `--camera-pitch-deg` if supplied. Reset returns to that startup default. The live command is `/sim/camera_pitch_command`, `std_msgs/msg/Float64`, in radians; pause/E-stop inhibits movement. For example, in a ROS shell:

```bash
ros2 topic pub --once /sim/camera_pitch_command std_msgs/msg/Float64 '{data: 0.2}'
```

This commands about 11.5° down. It is unrelated to spectator controls: scroll zooms (1.5–80 m), RMB orbits, MMB pans and detaches follow, **F** toggles follow, **H** returns to overview, and Escape releases the cursor. Follow starts at 5 m distance and 25° pitch. Moving the spectator does not move the sensor.

RGB is ideal `rgb8`, **640×480**, nominal **15 Hz**, with a **54° vertical FOV** and matching `/camera/color/camera_info`. Depth is a co-located render, **320×240**, nominal **10 Hz**, `32FC1` optical-Z metres; valid range is **0.2–10 m**, otherwise NaN. It is not stereo matching. `/scan` has **360 rays**, a nominal **5.5 Hz** scan interval and **0.15–12 m** range. Actual delivered rates depend on rendering and transport. See [depth implementation](../DEPTH_CAMERA.md) and [ROS interfaces](../ROS_INTERFACE.md).

## Terrain and caster approximation

The robot visual hierarchy has no physical contact colliders. Ideal axle integration drives the body; raycasts against allowed ground/ramp colliders supply support heights. Obstacle colliders support sensing, not a full robot collision/traction model. Motion caps in `ProbeMotion` are 2.2 m/s forward, 0.3 m/s reverse, ±1 rad/s yaw, 2 m/s² linear and 3 rad/s² angular acceleration. ROS owns reverse authorization; a Unity reverse cap does not authorize autonomous reverse.

[TerrainSupport.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/TerrainSupport.cs) provides the rigid three-point fallback. [CasterTerrainSupport.cs](../../unity/IGVCSim/Assets/IGVC/Runtime/CasterTerrainSupport.cs) uses a rigid front axle and one sprung rear body-height state to approximate pitch. Missing support, excessive slope (15° limit) or infeasible travel rejects movement. It does not solve tire forces, slip, gravity-driven motion, independent suspension roll or contact impulses.

[caster_suspension.json](../../ros2/src/igvc_description/config/caster_suspension.json) specifies provisional effective rear mass **30 kg**, each spring **12,000 N/m**, each damper **700 N·s/m**, vertical travel **0.04 m**, joint limit **0.045 m**, front/rear half tracks **0.405255/0.24612 m**, and rear support distance **0.85 m**. [caster_swivel.json](../../ros2/src/igvc_description/config/caster_swivel.json) specifies alignment distance **0.12 m**, maximum swivel rate **4 rad/s**, and stationary threshold **0.005 m/s**. Swivel visuals/joints follow motion; support sample positions remain yaw-only. These values are uncalibrated. Suspension defaults on when terrain support exists; `--caster-suspension off` selects rigid support. See [suspension](../CASTER_SUSPENSION.md) and [turning validation](../CASTER_TURNING.md).

## Keep the three course files separate

[generate_course_variant.py](../../tools/generate_course_variant.py) writes `artifacts/courses/seed-<seed>/`:

| File | Consumer and permitted purpose |
| --- | --- |
| `course.json` | **Physical world manifest**, loaded by Unity using `--course-manifest`. Defines painted centerline, obstacles, ramp and startup camera pitch. Also contains offline `guide_route_xy` and generation diagnostics; those are not autonomy inputs. |
| `autonomy.json` | **Sparse sensor-led mission**, passed to [sensor_course.py](../../tools/sensor_course.py) by `docker.ps1 course`. Allowlisted origin, six broad latitude/longitude/altitude destinations with radii, schema and speed limit. No dense guide, obstacle coordinates, lane modes or ramp checkpoint hints. |
| `mission.json` | **Guided regression oracle**, passed to [full_course.py](../../tools/full_course.py) by `guided-course`. Includes dense route, surface modes, ordered guide goals, explicit ramp poses and course SHA-256. |

The autonomy export uses [export_autonomy_mission.py](../../tools/export_autonomy_mission.py). Generation samples the painted course centerline at fractions `.16, .32, .54, .70, .84`, then returns to the origin: five **2 m** goal radii and a final **0.4 m** radius, with **2.2 m/s** maximum speed. It intentionally omits obstacle-aware guide excursions. `overview.png` shows the offline guide for inspection; it is not perception data.

**Do not tune sensor autonomy using hidden course knowledge.** Do not load `course.json`, `mission.json`, `guide_route_xy`, known barrel positions, ramp approach poses or generated gap modes into perception/planning. Do not densify autonomy destinations to trace the solution. Geometry can be used to construct the test environment and score a saved run independently. Sensor-led tuning must use the sparse mission and observed RGB/depth/lidar, TF/odometry and GPS. A successful guided lap proves a different behavior; see [sensor autonomy](../SENSOR_AUTONOMY.md) and [reference course](../REFERENCE_COURSE.md).

## Change the generated layout

Defaults are seed **2027**, difficulty **normal**. Dimensions are metres; yaw/pitch are radians; manifest frame is `odom`, schema version 1. The generator starts at `(0,0)` heading +X and produces a rounded rectangular loop with 6 m corner radius. Side positions are seeded around X=-9 and X=29, each ±0.35 m. The far straight is Y=44.5 m.

| Difficulty | Total barrels | Barrels in open ramp sector | Barricades | Potholes |
| --- | ---: | ---: | ---: | ---: |
| easy | 28 | 16 | 4 | 1 |
| normal | 44 | 24 | 8 | 2 |
| hard | 60 | 28 | 12 | 3 |

Barrels are 0.6 m diameter × 0.9 m high; colors are `red`, `orange`, `blue`, `green`, `yellow`, `white`. Unity creates contrasting rings, including dark rings on white barrels. Connecting-side groups block unshifted centerline travel near Y=12, 22 and 32 m; the offline guide makes alternating ±1.5 m excursions. The open population is split equally among before/after × left/right zones, in bands **4–5 m from Y=44.5**, with lane-mouth paint clearance. “Left” here is south because travel on that straight is westward. Normal therefore has six barrels per open zone, not 24 barrels total.

The ramp center X is `(left + right)/2`, so it varies with seed. `generate()` overrides the historical X=18 value in `DEFAULT_RAMP`: the actual entrance is **center X + 4**, Y=44.5, yaw pi. Length is **8 m** (3 m rise, 2 m deck, 3 m descent), width **3 m**, height **0.4 m**. Read the generated manifest for the actual entrance; do not copy obsolete absolute ramp positions from older reports.

For lane edits, change `lane_points`, `mode()` and `lane_half_width()` together. Normal half-width is **3 m**. On the ramp it becomes **1.44 m** with 2 m tapers; Unity paints **0.12 m-wide strips**, so their outer edges stay on the 1.5 m half-width surface. Gaps exist on the far straight where `y > 44.45` and `abs(x-ramp_center) > 6`; bend markings remain. `CourseRamp.HeightAt` lifts the paint onto the surface. `centerline` defines world paint; mission `dense_xy` is a separate guide and must not accidentally replace it.

Placement uses bounded rejection, a **0.2 m** geometric margin and axle-relative footprint X=[-1.1,+0.6], Y=[-0.5,+0.5] m. It checks overlap, route sweep, paint and ramp reservation. Exhaustion raises an error rather than relaxing clearance. The guide is sampled about every 0.25 m; sparse guide selection uses up to 8 m arc spacing, 0.6 m chord deviation and explicit mode/ramp transitions. These checks establish ideal guide solvability, not sensor-led success or a unique possible path.

## Regenerate, restart or rebuild?

| Change | Required action |
| --- | --- |
| Seed/difficulty, supported manifest coordinates/colors/paint/ramp dimensions | Regenerate and restart the player; no Unity rebuild for already-supported schema fields. |
| Generator/export Python | Regenerate outputs. Rebuild the Docker image first when using Docker launchers: [compose.yaml](../../compose.yaml) mounts artifacts, not source code. |
| Unity C#, shader, builder or imported visual asset | Rebuild the player, then restart it. Existing executables do not read changed source. |
| Camera/lidar mount transform | Update canonical config and regenerate the canonical description with the appropriate preparation workflow; rebuild Unity and the ROS description installation/image. Editing JSON alone does not relocate an already-built URDF or player. |
| Caster settings or builder camera default | Rebuild Unity because builders serialize these values. Remember the manifest camera pitch overrides the builder default. |
| ROS perception/navigation code or configuration | Rebuild the ROS workspace or Docker image and restart the affected stack; no Unity rebuild unless its interfaces/implementation also changed. |

For a stopped Docker session, `./tools/docker.ps1 start -Seed 2027 -Difficulty normal` generates the files before launching Unity. Native WSL workflows use `./tools/igvc.ps1 variant-generate` / `variant-start`; see [native AutoNav](../NATIVE_AUTONAV.md) and [runbook](../RUNBOOK.md). Startup-only loading means editing `course.json` while a player runs does not update that world. The normal launchers use `--line-guard scoring`; the runtime default is `enforce`. Keep that distinction when comparing runs.

Regeneration archives recognized prior run/evidence files under `previous-<UTC timestamp>` when a run file exists and removes stale current reports. It also overwrites generated missions and preview. Preserve evidence before hand editing outputs; prefer generator changes for reproducibility. Use the same seed and difficulty throughout a run, and compare the SHA-256 reported by Unity with the intended manifest.

## Validate the change you made

| Change | Targeted checks and evidence |
| --- | --- |
| Course placement, paint, ramp, difficulty | [test_course_variants.py](../../tools/tests/test_course_variants.py): seeded counts/zones, overlap, full-footprint clearance, paint, ramp and sparse-guide invariants; inspect the regenerated `overview.png` and runtime view |
| Sparse autonomy export or information boundary | [test_autonomy_mission_export.py](../../tools/tests/test_autonomy_mission_export.py), [test_sensor_mission_contract.py](../../tools/tests/test_sensor_mission_contract.py); verify no guide/geometry hints enter the autonomy input |
| Guided gap modes | [test_mission_gap_modes.py](../../tools/tests/test_mission_gap_modes.py); painted ramp must remain separate from the two unmarked approaches |
| Unity geometry/depth/render changes | Course build chain above, [CourseRampChecks.cs](../../unity/IGVCSim/Assets/IGVC/Editor/CourseRampChecks.cs), then [verify_ground_fixtures.py](../../tools/verify_ground_fixtures.py) / [verify_depth.py](../../tools/verify_depth.py) as relevant |
| Sensor pose or camera controls | [verify_camera_mount.py](../../tools/verify_camera_mount.py), [verify_variant_sensors.py](../../tools/verify_variant_sensors.py), [docker/verify_integration.py](../../docker/verify_integration.py); inspect exact-stamp TF and matching camera information |
| Terrain/suspension/swivel | Relevant `TerrainSupportChecks`, `CasterSuspensionChecks`, `CasterTerrainChecks`, `CasterSwivelChecks`, `CasterTurningChecks` in [Editor scripts](../../unity/IGVCSim/Assets/IGVC/Editor); live [verify_course_ramp.py](../../tools/verify_course_ramp.py) or [verify_caster_turning.py](../../tools/verify_caster_turning.py) from their documented fresh starting fixture |
| Guided end-to-end regression | Explicitly run `guided-course`, then `audit`; reports are `docker-run.json` and `validation.json`. This is route-informed evidence. |
| Sensor-led behavior | Run `course`, then `sensor-audit`; inspect `sensor-run.json` and `sensor-audit.json` plus [sensor autonomy limitations](../SENSOR_AUTONOMY.md). Do not substitute a guided success. |

For example, from a prepared Python environment at repository root, `python3 -m unittest discover -s tools/tests -p test_course_variants.py` checks geometry without running Unity. Live verifiers may command the robot or change camera state; coordinate them with the session owner and use their required starting fixture. A successful build or startup is not a successful sensor/navigation test. Record implementation, tests actually run and remaining limitations separately.
