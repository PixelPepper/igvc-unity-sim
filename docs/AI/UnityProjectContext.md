# Unity project context

## Ramp-edge perception and successful loop — 2026-09-09

Latest active course completed82/82 atseed2027, noreset/noauditgaps/line_blocks0, max2.2m/s, sampledclearance.703277464/swept.536494889m. Robot stoppedat(-.29369,-.00698); Unity+Nav2+RViz remainlive, autonomyoff. artifacts/courses/seed-2027/{run,validation}.json are NEW success, oldfailedattemptarchivedbygenerator. Whitepaint half_width metadata narrows6m corridor tocenter±1.44m,faredge±1.5m on3mrampsurface, thenwidens; paintz viaCourseRamp.HeightAt. Ground classifier surfaces.py uses organizeddepth normals/connectivity seededbynearplane; sparsecrest usesoneendpoint tangent agreement plus slope/gapchecks. Replay oldfixture335falseobstacles->0. New /perception/depth/surfaces PointCloud2 xyz+groundfloat32 feedsRGB project_observed withexactRGBTF andcausallymatcheddepth .35sim/.5wall limits. No infiniteplaneRGBprojection. Lanegroundeligibility excludesobservedoccluders; hazardsuseallobserveddepth. 58perceptiontests10generator70Unityrampchecks passed, sevenROSpackages/courseplayer rebuilt. Observer return-leg edgepositionp95xy.207m/z.164m, notcalibratedprecision; fullrunprimarybehavioralevidence. See docs/RAMP_EDGE_PERCEPTION.md. Older snapshots below arehistorical.

## Course ramp integration — 2026-09-09

Additional integratedcoursefastcheck passed all11 at2.2m/s,417joins135TF/caster,15.71mmcompression,0guardblocks: artifacts/checks/course-ramp-fast-live.json. After both manualchecks, course restartedatfreshorigin; noNav2/perceptionprocessesstarted. ExistingRVizwindowremains. No autonomousrunattempted.

`CourseRamp` builds static rise/deck/descent from optional schema1 `ramps`. Generator defaults startROS(2,0),yaw0,width3,rise3,deck2,height.4; endsx10. Opening straight and reserved obstacle/fullpothole-rim clearance; six exact ordered ramp checkpoints. `CourseVariant.Load` returns nonserialized ground/ramp supports to `TransportProbe` before caster init. Old manifests without ramps remain planar. Status adds terrain_support/caster_suspension booleans. Pothole rims/bowls are not support surfaces. New seed2027normal82checkpoints34obstacles; historical78pass archived previous-20260909T202724060370Z. Nine generator and28Unitychecks passed; 0.6m/smanualcourse11checks1042joins passed. Source/meta and rebuiltcourseplayer present. `igvc.ps1 course-ramp-test` uses freshorigin andtimestampedreports. See docs/COURSE_RAMP.md. Autonomous ramp perception still pending; no newfull-loop claim.

## Moving perception baseline — 2026-09-09

See `docs/TERRAIN_PERCEPTION.md`. Manual ramp motion passed 10 checks/1029 pairs; 45-second perception observation found 39,773 repeated surveyed-ground points labeled obstacles and 96 current lane detections on the unpainted bench. Exact depth fixture `artifacts/checks/terrain-depth-origin.npz` replays 335 ramp-region obstacle points despite 100% lower-image inliers. No perception algorithm changed. New tools capture/replay exact-frame geometry and observe bench data; `igvc.ps1 perception-start/stop` owns camera-only processors, mutually exclusive with managed Nav2 under one lock. Build/live lifecycle/concurrent start checks passed. Current player is stationary at fresh terrain origin with managed perception, no Nav2. Next slice: spatially supported multi-surface ground classification and depth-consistent RGB projections; capture RGB masks to identify false positives. Preserve existing safety/freshness thresholds and do not use survey truth in autonomy.

## Motion-aligned caster swivel — 2026-09-09

`CasterSwivel` now produces continuous yaw/rate feedback for existing leftCaster/rightCaster joints in all R3-a players. `caster_swivel.json` supplies provisional .12 m alignment response distance, 4 rad/s rate cap, .005 m/s stationary threshold. `R3aDriveBuild` wires the original caster transforms beneath suspension sliders. `TransportProbe` uses accepted nominal-pivot velocities (v-w*y,w*x), projects footprint velocity into the tilted body plane, applies Unity -Y yaw and publishes ROS +Z yaw/rate. Zero speed holds angle; pause freezes; reset/restore zero both swivels. No tire rolling joint, trail/friction/contact/shimmy model or steering-dependent suspension footprint was added.

Passed 12 new Unity checks, 18 live flat swivel checks (864 pairs, 288 TF comparisons per side), 29 normal drive checks including reset after nonzero angles, and 13 combined ramp checks (1359 matched odom/body/suspension/joints, zero pivot drift, bounded swivel rate). See [swivel guide](../CASTER_SWIVEL.md). Previous turning evidence remains historical; the current verifier additionally joins/checks swivel joints. Core interfaces retain seven joint names and RSP remains sole caster TF authority.

## Caster turning validation — 2026-09-09

No runtime suspension change was necessary. `CasterTurningChecks.Run()` adds 48 real-collider checks covering eight equilibrium headings on a 10-degree plane, analytic front-axle alignment, transient full turn, slider projection and transactional support rejection. TerrainBenchBuild invokes them; final Windows terrain build passed. `verify_caster_turning.py` passed 12 live checks/1353 matched records: pivot 6.39 rad with zero sampled axle drift, arcs .5115/1.1351/.5811 m with correct signed yaw, sustained stopped states and analytic support/body checks. First weaker test evidence is retained in caster-turning-first-pass.json; current caster-turning-live.json uses measured arc progress, sampled pivot drift and aborts failed phases. CLI `terrain-turn-test` requires a fresh suspension bench profile. Normal drive/course players unchanged. See [evidence](../CASTER_TURNING.md). Bench left at start with suspension enabled.

## Rear caster suspension — 2026-09-09

The default TerrainBench now uses `CasterSuspension` (plain C# bounded spring/damper state), `CasterTerrainSupport` (four supplied-collider samples, preview/commit), and two slider transforms wrapped around the original caster visuals by `R3aDriveBuild`. `config/caster_suspension.json` in igvc_description is the shared provisional configuration. Front driven axle remains rigid; caster travel is independent but body compliance has one rear pitch degree of freedom. Footprint samples rotate by yaw only. Sag is compensated, travel stops are kinematic clamps; no actual tire/contact/traction or suspension calibration claim.

Simulation launch uses `with_caster_suspension` to insert sliders into an in-memory URDF; canonical files stay unchanged. RSP owns both slider/swivel edges, bridge still owns only dynamic body edge. All R3-a players publish seven joint states; normal flat modes set sliders to zero. The bench additionally publishes exact-stamp `/sim/suspension_state` at 50 Hz. Reset initializes support without a kick, pause freezes state, terrain previews copy spring state and only commit after the axle speed budget passes. Arc preview now uses the same sinc expression as R3aKinematics. `-RigidTerrain` selects the previous three-point rigid model and is required by its old verifier.

Passed 13 spring checks, 11 caster-terrain checks, 5 ROS description tests and live bump/ramp traversal at 0.6 and 2.2 m/s (1067/392 joined samples, 344/130 TF comparisons per caster). Both showed 25 mm differential travel, bounded compression and final settling. See [current evidence and limits](../CASTER_SUSPENSION.md). The earlier rigid-mode and full-course results below remain historical. ROS build now installs packages sequentially after observing setuptools metadata removal/read contention during parallel builds; no dependency pins changed.

## Experimental body support — 2026-09-09

New isolated TerrainBench scene/player and `TerrainSupport` sample three provisional support locations only against supplied ground colliders. Kinematic plane alignment raises/tilts the rendered body; absent support or >15deg rejects the candidate move. No gravity/suspension/traction or tirecontact model. Candidate axle3D displacement, including height change at transitions, is limited to commanded speed. Synthetic wheelphase/velocity both use planar integrated distance. Normal AutoNav course keeps terrain mode disabled.

ALL R3-a players now publish `/sim/body_transform` (base_footprint->base_link) every50Hz with simulation acquisition stamps. Bridge validates/broadcasts that dynamicedge and no longer publishes staticbodyoffset. Footprint stays planar Z0 datum. Sensors/RSP inherit bodyattitude. Terrain, drive and course Windows players rebuilt; seven ROS packagesbuilt. Existing oldRViz staticTFcache neededrestart and was restarted.

Passed13Unity supportchecks; two bounded manualbenchtraversals .3 and2.2m/s with1889/324 exactstamppairs, independentanalyticrampheights/pitch, staticTFabsence and3Dspeedcaps. Rampdeckground+.4m, pitch±.13255rad. Fullnormalcourse78/78passedafterdynamicbodymigration, no pauses/recovery/guardblocks, max2.2m/s, sampleclearance.705790m, sweptbound.543000m, finish.293825m. Latestnormalcourse remainsrunning atstart; missionexited. Previousterrainlanerun archivedprevious-20260909T165937347415Z. See [TERRAIN_BODY.md](../TERRAIN_BODY.md). Nextwork: realphysicalcontact/clearance andnonplanarperception beforeautonomousrampqualification; do not labelbench physicalorcompleteautonomy.

## Depth-ground RGB projection — 2026-09-09

RGB lane and dark-bowl hazard projection now use a causal preceding depth-derived plane; `ground_plane_z` is removed from the runtime lane node. `GroundHistory` stores at most8 fits, requires depthstamp<=RGBstamp within.35s and receiptage<=.5s, clears on invalid fit/reset/stamp reversal. `project_plane` intersects RGB rays transformed by exact-acquisition TF with that plane, retaining camera-relative XY range1..10m. No fixed-ground fallback. Lane status includes ground coefficients/source stamp/age. Missing depth invalidates lane health; restoration does not rearm autonomy. Steady timers remain intact.

Passed:42 perception tests, surveyed projection through three saved GPU-ground fixtures (maxerror.000106m), live145 matched RGB/depth-plane records (.28s maxage), depth-loss lane invalidation/restoration checks and new78/78 fullcourseaudit. Latest seed2027: .690336m sampledclearance, .555345m conservative sweptclearance, .293523m finisherror, max2.2m/s, no pauses/recoveries/guardblocks. Earlier timer-only successfulrun is archived at `previous-20260909T164059627191Z`. Unity/RViz remain running at start; mission exited. See [TERRAIN_LANES.md](../TERRAIN_LANES.md). Projection assumes one locally stationary plane; broad obstacle tops, nonplanar transitions and true negative-obstacle geometry remain limitations. No physical ramp/bodycontact or stereo fidelity claim. Prior fixed-Z statements below are historical and superseded.

## Steady timer fix — 2026-09-09

The freshness-stall investigation below is resolved. Host realtime corrections delayed default ROS timers while monotonic expiry advanced. Measured paired50ms timers diverged under natural backward corrections: default maxgap1.0113s, steady.0543s. `probe_adapter`, `lane_node`, `depth_node` now explicitly pass a retained STEADY_TIME clock to their periodic timers. Message/TF stamps, simulation time and expiry thresholds are unchanged. Both lane and depth suspension watchdog checks pass, including no automatic rearm. Verification helpers now wait for service discovery before making a call.

Fresh seed2027/normal passed all78 checkpoints and returned to start: .755520m minimum sampled clearance, .584102m conservative swept bound, .292620m finish error, max2.2m/s, no pauses/recoveries/lineguardblocks/resets/auditgaps. During120s health observation, all581 depth statuses valid; maxdepth updategap~.21s, laneupdategap~.23s. Three autonomy falling edges were planned zone transitions/final stop, with fresh perception, not watchdog trips. The earlier paused17 run is archived in `previous-20260909T162748042090Z`. Unity/RViz remain running; robot stopped at start, mission observer exited normally. See [ROS_TIMING.md](../ROS_TIMING.md). No Unity assets changed for the timer fix; seven ROS packages rebuilt. Current sensor/physics limitations still apply. Historical paragraphs below retain prior evidence and are superseded by this entry.

## Terrain-relative depth update — 2026-09-09

`ground.py` fits a bounded deterministic plane from lower-image depth returns; no fixed Z=0 fallback or course geometry enters depth perception. It filters signed plane heights .12–1.8 m at <=10 m range. `depth_node.py` selects the newest <=.5 s old pair with exact acquisition TF available, publishes fit diagnostics and `/perception/depth/healthy`. R3-a now requires positive depth health within .75 wall seconds for autonomy, independently of lane freshness; loss latches manual and recovery never rearms. RGB lane/hazard projection still assumes Z=0. Broad obstacle tops can satisfy the ground heuristic; neither nonplanar traversability nor physical body contact is solved.

Validation: 32 perception tests, three actual GPU fixtures (flat, +.195 m, 10° slope), Unity Windows build, seven ROS packages, 12 live depth checks and depth-loss watchdog passed. First terrain-estimator full loop passed 78/78 but showed a TF selection race; final selection fixes that race. Final-code regression remains paused at17/78 after three watchdog stops, with two explicit same-checkpoint resumes. Diagnostic observers show shared ~1.15 s ROS update gaps; cause remains unresolved. Keep the .75 s gate intact. Unity/RViz remain running, robot stopped; `loop-cancel` before restarting/building. See [DEPTH_CAMERA.md](../DEPTH_CAMERA.md), `artifacts/checks/ground-course-health-resumed.json`, and the current run report. Do not claim the latest loop passed. Historical evidence below is superseded where noted.

## Metric depth update — 2026-09-09

`ProbeDepthCamera` uses a dedicated same-pose camera and Resources/IGVCMetricDepth.shader to render linear optical Z into RFloat. It publishes 320×240 32FC1 metres and synchronized CameraInfo at nominal 10 Hz, independently timed from RGB, with .2–10 m validity and NaN elsewhere. A single pending GPU readback bounds work; callbacks from an earlier run ID are dropped. `depth_processor` runs with nav-start, projects every fourth pixel using acquisition-time TF, publishes optical XYZ and odom obstacle points. The height filter .12–1.8 m above Z=0 is validated only on flat procedural terrain. Both costmaps use a dedicated .75 s expiring depth layer. RViz adds metric depth and filtered/full cloud views. No stereo matching or contact physics is implied.

Build and checks passed: six known-geometry GPU tests, 24 perception tests including eight depth tests, 12 live checks at 10.11 Hz depth / 5 Hz clouds, and one full depth-enabled seed-2027 loop with all 78 checkpoints, no recovery, no guard blocks, minimum sampled clearance .723 m. See [DEPTH_CAMERA.md](../DEPTH_CAMERA.md). The prior easy/hard procedural runs below predate depth integration; they were not rerun for this slice.

## Procedural AutoNav update — 2026-09-09

`CourseVariant.Load` builds native runtime geometry from a bounded seeded manifest: continuously joined 12 cm paint strips, orange/white barrels and barricades, and occasional dark depressed bowls in ground cutouts. The generator varies the reference loop curvature and obstacle placement; it preserves the ordered loop and checks full-footprint clearance. `variant-start` selects the manifest before ROS publication. The mission and final auditor compare its SHA-256 with Unity's reported hash. Regeneration archives prior evidence. The original imported scene remains separately selectable.

The camera now defaults and resets to 10° down; its updated live verifier passed 53 checks. Lane segmentation retains thin paint and removes orange-surrounded barrel bands before component filtering, preserving paint that touches a stripe. RGB-derived pothole points use exact-time optical TF and a separate bounded cache and Nav2 cost layer; no generator hazard coordinates enter perception. Depth/stereo and physical terrain contact remain unimplemented.

Seed 2027/normal completed all 78 checkpoints and passed clearance, speed, no-reset, no-gap, runtime-hash and line-guard audits. Seed 2028/easy also completed all 78 and passed. Seed 2029/hard completed all 81 checkpoints and passed as well, using one bounded 0.5 m backup before retrying the same checkpoint. Results, commands and limitations belong in [PROCEDURAL_COURSES.md](../PROCEDURAL_COURSES.md). Tests passed: 16 perception, 25 tools (including 13 ordered-route auditor checks), and the Unity player/7-package ROS build. The route projection fix excludes segments outside the reachable arc window without changing any audit tolerance. Historical onboarding claims below are superseded by this update and the current run guides.

## Current tuning and full-course status — 2026-09-09

This update supersedes the initial-speed and pending-navigation descriptions in the historical onboarding notes below. Nav2's forward cap is 2.2 m/s, with 0.75 m inflation radius (formerly 1 m) and cost scaling 5 (formerly 3, now faster decay). The complete axle-relative footprint X=[−1.1,+0.6], Y=[−0.5,+0.5] and 0.02 m padding are unchanged. The cap leaves margin below the 5 mph/2.2352 m/s maximum in [2027 rules version 7, section I.2, page 6](https://www.gl-systems-technology.net/uploads/3/4/7/2/34727963/igvc_2027_rules_version_7_july_26.pdf); this does not establish overall compliance.

`ProbeMotion` retains 2 m/s² linear acceleration/deceleration, 3 rad/s² angular acceleration and ±1 rad/s angular limits. The angular target scales by achieved/requested linear-speed magnitude during launch, preventing the reported excessive initial curvature; zero-linear commands retain in-place rotation. Reverse caps at 0.3 m/s and the ROS boundary owns recovery authorization. The full-course runner applies `tools/approach_speed.py` for goal-distance braking with 0.2 s latency and 0.2 m reserve, clamped to 0.05–2.2 m/s to avoid Nav2's zero/unlimited sentinel.

Current evidence: 28 Unity motion checks, six speed-helper tests and all seven ROS package builds passed. The fresh rolling-horizon run completed **77/77 ordered physical checkpoints**, driving 153.33 m in 81.12 simulation seconds and stopping 0.294 m from the origin. Audit continuity passed, with zero recovery/backwards travel or paint-guard interventions; sampled minimum barrel clearance was 0.212 m. This supersedes the incomplete archived attempts. See [full-course commands and evidence](../FULL_COURSE.md) and [navigation tuning](../NAVIGATION.md). No physics/contact or hardware fidelity is implied by this ideal-motion result.

The runner now uses `NavigateThroughPoses` with three consecutive guide points and updates the same action as the physical auditor passes each checkpoint. It does not stop at ordinary intermediate waypoints. The speed governor brakes toward the rolling horizon endpoint, preserving required stops at declared-zone transitions and final arrival. Bridge and Unity uniformly scale linear/angular commands when either limit is exceeded, preserving requested curvature. The opening straight held 2.2 m/s through checkpoints 1–8, replacing the earlier stop-at-every-waypoint behavior. Evidence: `artifacts/checks/full-course-{live,clearance}.json` and `full-course-trajectory.png`.

<!-- unity-onboarding:generated:start -->

Last analyzed: 2026-09-09. Source state: local working tree; no HEAD commit resolves yet. Project root: `unity/IGVCSim`. The first transport fixture is validated; the full IGVC simulator remains under development.

The actual five-link R3-a description now builds as a separate static inspection player using `RobotInspectionBuild.Build`. Generated meshes/materials/scene are ignored and recreated from `ros2/src/igvc_description`. Five coordinate assertions passed. This player has no ROS connection or drivetrain; RViz separately displays the canonical description on domain 43. See [inspection evidence and limitations](../ROBOT_INSPECTION.md).

## Confirmed environment

Camera update: official OAK-D Pro enclosure plus aperture overlays is attached to an extracted moving pitch bracket on the rear pole. `config/camera_mount.json` defines the frame chain. Camera pitch is published in joint_states and controlled by `/sim/camera_pitch_command` (Float64 radians, +down, zero level). RSP owns camera TF; adapter no longer supplies the old fixed optical transform. RGB has exact-stamp CameraInfo. Dedicated 48-check live camera verification passed. See [camera mount](../CAMERA_MOUNT.md). Depth is still pending.

Mounted lidar: `config/lidar_mount.json` drives generated fixed joint `lidar_mount`; `lidar_link` is scan frame and has the normalized IGES visual offset down to its feet. RSP owns this fixed TF; the adapter skips its old lidar fixture transform in R3-a mode. TransportProbe raycasts from the imported lidar Transform. 27 live checks passed; see [mount evidence](../LIDAR_MOUNT.md). Body plus lidar is 179,986 triangles.

Drive slice: `R3aDriveBuild.Build` composes the existing transport fixture with simplified CAD visuals; `TransportProbe` uses `R3aKinematics` for exact axle integration while retaining ProbeMotion's command protections. `r3a.launch.py` supplies RSP and the mode-specific adapter. After correcting physical forward toward the big drive wheels (casters rear), 18 kinematics, 12 protection and 26 live checks passed. Base offset is -0.25591 m behind the axle. See [drive evidence](../R3A_DRIVE.md). The earlier static viewer remains separate. No contact physics, depth or Nav2 yet.

| Area | Finding | Evidence |
| --- | --- | --- |
| Editor | Unity 6, 6000.3.23f1, revision `09d2ecc7fb28` | `ProjectSettings/ProjectVersion.txt` |
| Rendering | Built-in Render Pipeline; Standard materials | `GraphicsSettings.asset` has no custom pipeline; `Editor/ProbeBuild.cs` |
| Input | Legacy Input Manager selected; driving comes from ROS | `ProjectSettings.asset` activeInputHandler 0; runtime subscription |
| Player | Windows x64 development build, windowed, runs in background | `Editor/ProbeBuild.cs` |
| Transport | ROS-TCP-Connector Git pin `c27f00c6cf750d2d0564349b3039d19aa3925e7c`; `ROS2` define | `Packages/manifest.json`, lock and project settings |
| ROS host | Jazzy on Ubuntu-24.04 WSL; Fast DDS, localhost discovery, default domain 42 | repository `tools/ros_env.sh` |

Package files include Unity built-in modules and Multiplayer Center 1.0.1; no first-party multiplayer behavior is present. No Input System, SRP, DOTS, addressables, DI or Unity Test Framework package is declared. The ROS endpoint pin is `54c1a64b6d5ef6ffa0a0431570bb74329b79b15b` in `tools/build_ros.sh`.

## Structure and startup

Paths below are relative to the Unity project unless prefixed with repository.

| Path | Responsibility |
| --- | --- |
| `Assets/IGVC/Runtime/TransportProbe.cs` | Connection, topics/services, 0.01-second simulation clock, ideal pose, raycast lidar, status HUD |
| `Assets/IGVC/Runtime/ProbeMotion.cs` | Plain C# planar integration, speed/acceleration limits, timestamp and wall-time watchdogs, pause/E-stop/reset |
| `Assets/IGVC/Runtime/ProbeCamera.cs` | RenderTexture RGB capture, one pending async GPU readback, row flip, ROS image publication |
| `Assets/IGVC/Editor/ProbeBuild.cs` | Regenerates the fixture scene/materials and builds the Windows player |
| `Assets/IGVC/Editor/ProbeChecks.cs` | Custom batch method for motion invariants |
| `Assets/IGVC/Scenes/TransportProbe.unity` | Sole enabled build scene: pad, wall, asymmetric markers, placeholder body and two cameras |
| repository `ros2/src/igvc_sim_bridge` | ROS launch, manual command adapter, ideal TF/odom, RViz config, live verifier |

No first-party asmdefs/asmrefs are present: runtime uses Unity's default assembly, and `Editor/` provides the editor assembly boundary. Runtime has no Editor dependency. `TransportProbe.Start` registers generated ROS messages/services, attaches `ProbeCamera`, then connects to the endpoint; registration deliberately happens after Awake. No scene loader or save system exists.

## Architecture and conventions

Confirmed MonoBehaviour composition with a plain C# motion core. Unity owns clock and ideal ground truth; the ROS adapter supplies `/odom` and TF. Pose conversion uses Unity `(-ROS y, ROS z, ROS x)` with negative Unity yaw for positive ROS yaw. No articulated physics or actual robot geometry has been imported.

Runtime namespace is `IGVC`; editor entrypoints are static classes. Current C# uses four-space indentation, Allman braces, private camelCase fields and `[SerializeField] private` scene references. GPU callbacks are used for camera capture; no general async framework is declared. These are observed conventions in the small current codebase.

## Validation and tooling

Use [the runbook](../RUNBOOK.md) for build/start/test commands and limitations. `build` regenerates the scene, so changes intended to survive builds belong in `ProbeBuild.CreateScene`. Keep runtime code independent of Editor APIs. Preserve `.meta` files, package pins and serialized assets; caches and artifacts are ignored.

`ProbeChecks.Run` is a custom check entrypoint, not a Unity Test Framework suite. The final artifact records 12 passed and 0 failed. All 15 live checks passed with a 600-second load interval: RGB 13.34 Hz, lidar 5.26 Hz, odometry 50.00 Hz and real-time factor 0.999966. All 8 reconnect checks passed. RViz/WSLg was captured with RGB, scan, TF, odometry and Global Status OK. The earlier RGB loss was corrected with bounded state queues of 10 and an 8 MiB Fast DDS SHM profile; RGB queue remains 1 and camera readback remains one pending request. [Evidence](../TRANSPORT_EVIDENCE.md) distinguishes fixture verification from unvalidated calibration and the future robot/Nav2 stack. No CI, PlayMode test assembly or full sensor/navigation regression suite exists yet.

Read repository `AGENTS.md` and [the agent workflow](../AGENT_WORKFLOW.md) before delegation: compact briefs, disjoint file ownership, no recursive workers, integrator-only Unity builds. `tools/cursor-agent.ps1` provides bounded read-only Grok 4.6 reviews through the Cursor SDK. Authenticated discovery and the first review completed; actual usage and the coordinator's disposition are in the agent workflow. See the runbook for doctor/dry-run/review commands.

Unity MCP status: no provider is declared in the inspected package files and no Unity-specific MCP tool was exposed during this inspection. Editor connection, console, scene inspection, play mode and profiler access are unverified. Repository tools and batch entrypoints are available; onboarding did not invoke an Editor or build.

## Constraints and unknowns

The target is IGVC 2027 AutoNav with OAK-D Pro and RPLIDAR A1, but this fixture only has nominal 640×480/15 Hz RGB and 5.5 Hz ideal scan. Hardware calibration/mounting, depth, Nav2, real robot modeling, estimator ownership beyond ideal mode, QoS/load limits, reconnect evidence and competition compliance remain unresolved. Static sensor geometry is provisional. See the runbook for precise implemented interfaces rather than assuming every topic in `ROS_INTERFACE.md` exists.

Sources inspected: README, PLAN, ROS_INTERFACE, WORKFLOW, `.gitignore`; Unity package manifest/lock, ProjectVersion, GraphicsSettings, ProjectSettings, EditorBuildSettings, first-party Runtime and Editor scripts; ROS adapter/launch/verifier; PowerShell/WSL build/session/environment wrappers; local check artifacts. No Unity assets were modified for this context document.

<!-- unity-onboarding:generated:end -->
# Sooner course addition — 2026-09-09

Environment-only SoonerRobotics AutoNav 2026 import now builds as GeneratedRobot/SoonerAutoNav.unity through Editor/SoonerCourseBuild.cs. tools/import_sooner_course.py stages pinned external assets locally (ignored, reuse terms unresolved), strips upstream scripts, preserves baked lane mesh/41 barrels. Existing R3-a and ROS runtime unchanged. Course spawn maps source horizontal pose/yaw to odom zero; static obstacle mesh colliders enable scans. Built-in material conversion and flat lighting verified visually. Seven live read-only stream checks passed; no course-specific motion/navigation validation. tools/igvc.ps1 course-build/course-start provide lifecycle. See docs/SOONER_COURSE.md.
# Spectator controls and Nav2 — 2026-09-09

SpectatorCamera on course Overview Camera provides scroll zoom, RMB orbit, MMB pan, F follow toggle, H overview; default follow5m, follows even when Unity unfocused. Sensor camera unchanged. New igvc_navigation package has minimal four-server lifecycle stack, Navfn/RPP .25m/s, odom rolling costmaps, lidaronly, conservativefootprint. ProbeAdapter now arbitrates /cmd_vel/nav via /sim/set_autonomy; manualdefault and teleoplatchedoverride. tools/nav_control.py and igvc.ps1 nav-start/nav-goal/nav-cancel/nav-stop manage goals and separate nav processgroup. stop shutsbothgroups. nav.rviz showscostmaps/plan. Live nearbygoal, detour, arbitration and cancellation passed; unknownoccludedgoal rejected. See docs/NAVIGATION.md forexactevidence. Lane/GPS/depth/contact remainpending.

# Camera lanes and synthetic GPS — 2026-09-09

Supersedes the preceding lane/GPS pending status. CourseLaneBuild derives painted-strip edges from imported UV geometry; LaneBoundaryGuard conservatively sweeps the Nav2 rectangle against these edges for manual and autonomous motion. This is a fixture constraint, never exposed to perception. igvc_perception independently segments actual RGB and projects through acquisition-time optical TF onto ground z=0. igvc_lane_layer writes lethal points after the lidar layer and expires stream data after .75 s. The command gate requires fresh lane validity and latches manual on loss. Nav launch starts perception; R3-a launch starts ideal synthetic WGS84 GPS. gps-list/gps-run operate editable missions with fresh-GPS/origin checks, manual takeover and cancellation.

Current checks: seven ROS packages build; Unity guard build and live crossing/reverse checks pass; live lane cloud ~4.8 Hz and455/455 sampled costmap cells lethal; lane detector suspension latches manual and recovery does not rearm; 2/4/6 m GPS mission succeeds with final error .1942 m and no guard intervention. Reports in artifacts/checks/{lane-guard-build,lane-guard-live,lanes-live,lane-watchdog-live,gps-live}.json. No full-course, varying light, slopes, depth, GNSS noise/fusion or physical-contact qualification. See LANE_DETECTION.md and GPS_WAYPOINTS.md.
