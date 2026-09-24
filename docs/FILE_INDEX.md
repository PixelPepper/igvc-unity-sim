# Linked File and Document Index

Companion to the [master project guide](PROJECT_GUIDE.md). Paths are relative to
the repository; links open the real source, not a copied excerpt. This index
covers the major maintained entry points and groups repetitive test/asset files.
Generated output, binary meshes, `.meta` pairs, Python `__init__.py` files and
package boilerplate are described by directory rather than individually.

Reviewed 2026-09-23. **Read-only** means a tool does not command the robot; it can
still write an output report. **Motion/state** means it may move/reset the robot,
alter ROS authority, interrupt a sensor, or restart processes. Read its arguments
and fixture assumptions before running it.

## Index

- [Launch, build, packaging and development support](#launch-and-packaging)
- [ROS packages and interfaces](#ros-files)
- [Unity runtime, builders and assets](#unity-files)
- [Course and mission software](#mission-files)
- [Preparation, diagnostics and live checks](#diagnostic-tools)
- [Tests](#tests)
- [Documentation library](#documents)
- [Generated files and evidence](#outputs)

<a id="launch-and-packaging"></a>
## Launch, build, packaging and development support

| File | Responsibility / when to open it |
|---|---|
| [README.md](../README.md) | Installation, platform-specific prerequisites, downloads and normal startup |
| [AGENTS.md](../AGENTS.md) | Project conventions, physical orientation, file ownership and delegation constraints |
| [.gitignore](../.gitignore) | Excludes build caches, credentials, local artifacts and external course assets; preserves owned Unity metadata |
| [.dockerignore](../.dockerignore) | Limits image build context to required ROS, tools and Docker inputs |
| [THIRD_PARTY_ASSETS.md](../THIRD_PARTY_ASSETS.md) | Asset provenance and redistribution boundaries |
| [compose.yaml](../compose.yaml) | ROS container, domain, loopback TCP port, artifacts/display mounts and RViz rendering environment |
| [compose.linux.yaml](../compose.linux.yaml) | Linux user IDs, Xauthority and display permissions |
| [docker/Dockerfile](../docker/Dockerfile) | Ubuntu/Jazzy image, dependency pins, patched MPPI build/test and installed project source |
| [docker/entrypoint.sh](../docker/entrypoint.sh) | Sources base ROS, patched controller and project environment before commands |
| [docker/simulation.launch.py](../docker/simulation.launch.py) | Starts the robot bridge and navigation launches together |
| [docker/prepare-unity.sh](../docker/prepare-unity.sh) | Fetches pinned external reference assets and invokes preparation for local Unity builds |
| [docker/patch_nav2_cost_critic.py](../docker/patch_nav2_cost_critic.py) | Strict source-hash/revision checked MPPI fix, actual critic regression and installed patch marker |
| [tools/docker.ps1](../tools/docker.ps1) | Windows Docker build/start/stop, RViz, sensor-led `course`, separate `guided-course`, checks and shell |
| [tools/docker-wsl-lifetime.ps1](../tools/docker-wsl-lifetime.ps1) | Owns the hidden WSL keep-alive using recorded process identity; released by Docker `stop` |
| [tools/docker.sh](../tools/docker.sh) | Thin Linux entry point into `linux_session.py` |
| [tools/linux_session.py](../tools/linux_session.py) | Linux player/Compose lifecycle, display authorization, build commands and owned-process checks |
| [tools/igvc.ps1](../tools/igvc.ps1) | Native WSL launch/build/stop, test benches, course variants and legacy guided loop commands |
| [tools/run_ros.sh](../tools/run_ros.sh) | Executes one native command after sourcing the project ROS environment |
| [tools/ros_env.sh](../tools/ros_env.sh) | Domain 42, localhost discovery, Fast DDS settings, native install and validated MPPI overlay |
| [tools/ros_session.py](../tools/ros_session.py) | Owns native ROS process groups, serializes session changes and prevents overlapping managed perception/navigation |
| [tools/build_ros.sh](../tools/build_ros.sh) | Expands canonical Xacro, checks endpoint pin and builds native ROS packages into `~/igvc_ws` |
| [tools/build_native_nav2.sh](../tools/build_native_nav2.sh) | Builds/tests the pinned native MPPI overlay, enabling it only after successful validation |
| [.github/workflows/container.yml](../.github/workflows/container.yml) | Manual release job: image build/environment check, image archive and checksums; no rendered course test |
| [tools/agents/README.md](../tools/agents/README.md) | Optional Cursor/Grok review setup and limits |
| [tools/agents/runner.mjs](../tools/agents/runner.mjs) | Bounded allowlisted text inputs, model selection, review, usage and cancellation accounting |
| [tools/agents/review-motion.task.json](../tools/agents/review-motion.task.json) | Example scoped review packet; not runtime robot configuration |
| [tools/agents/package.json](../tools/agents/package.json), [lock](../tools/agents/package-lock.json) | Cursor SDK and Node dependency constraints |
| [tools/cursor-agent.ps1](../tools/cursor-agent.ps1) | Windows authenticated runner wrapper and effort/Fast options |
| [tools/set-cursor-key.ps1](../tools/set-cursor-key.ps1) | Interactive encrypted per-user credential setup outside the repository; do not put keys in project files |

<a id="ros-files"></a>
## ROS packages and interfaces

Every package has a `package.xml`. C++/resource packages use `CMakeLists.txt`;
Python packages use `setup.py`, `setup.cfg` and `resource/`. Update those manifests
when adding dependencies, executables or installed data. The downloaded
ROS-TCP-Endpoint is an external package, not a seventh first-party package.

### Robot description — `igvc_description`

| File / directory | Responsibility |
|---|---|
| [Package README](../ros2/src/igvc_description/README.md) | Canonical description preparation and limitations |
| [urdf/r3_a.urdf.xacro](../ros2/src/igvc_description/urdf/r3_a.urdf.xacro) | Canonical links, joints, mesh references and sensor/body frames |
| [urdf/r3_a.urdf](../ros2/src/igvc_description/urdf/r3_a.urdf) | Expanded artifact used by consumers; regenerate from Xacro rather than treating it as a second authority |
| [config/camera_mount.json](../ros2/src/igvc_description/config/camera_mount.json) | Camera mounting/pitch configuration; physical pole location and provisional values |
| [config/lidar_mount.json](../ros2/src/igvc_description/config/lidar_mount.json) | Front-roof lidar mounting and visual alignment |
| [config/caster_suspension.json](../ros2/src/igvc_description/config/caster_suspension.json) | Provisional suspension geometry, travel, spring/damping settings |
| [config/caster_swivel.json](../ros2/src/igvc_description/config/caster_swivel.json) | Motion-aligned caster swivel settings |
| [provenance.json](../ros2/src/igvc_description/provenance.json) | Robot source/preparation provenance |
| [meshes/](../ros2/src/igvc_description/meshes/) | Robot visuals; subdirectories hold camera, mount, lidar and simplified visual variants with provenance |
| [launch/display.launch.py](../ros2/src/igvc_description/launch/display.launch.py), [description.rviz](../ros2/src/igvc_description/rviz/description.rviz) | Standalone description visualization; not a live autonomous course |

### Bridge and control — `igvc_sim_bridge`

| File | Responsibility |
|---|---|
| [launch/r3a.launch.py](../ros2/src/igvc_sim_bridge/launch/r3a.launch.py) | TCP endpoint, CAD-mode adapter, description/body transforms and synthetic GPS |
| [launch/probe.launch.py](../ros2/src/igvc_sim_bridge/launch/probe.launch.py) | Earlier simple transport fixture |
| [probe_adapter.py](../ros2/src/igvc_sim_bridge/igvc_sim_bridge/probe_adapter.py) | Manual/autonomous command authority, freshness gates, stamped drive transport, ideal odometry and TF |
| [navigation_policy.py](../ros2/src/igvc_sim_bridge/igvc_sim_bridge/navigation_policy.py) | Forward/reverse/pivot policy applied to navigation commands |
| [suspension_description.py](../ros2/src/igvc_sim_bridge/igvc_sim_bridge/suspension_description.py) | Adds suspension articulation to the expanded description consistently |
| [verify_probe.py](../ros2/src/igvc_sim_bridge/igvc_sim_bridge/verify_probe.py) | Original live transport/motion verifier; fixture-dependent and motion-producing |
| [rviz/nav.rviz](../ros2/src/igvc_sim_bridge/rviz/nav.rviz) | Course navigation view: robot, sensors, perception clouds, costmaps and paths |
| [rviz/r3a.rviz](../ros2/src/igvc_sim_bridge/rviz/r3a.rviz) | CAD robot and basic live sensors |
| [rviz/probe.rviz](../ros2/src/igvc_sim_bridge/rviz/probe.rviz) | Original transport fixture display |
| [ros2/config/fastdds.xml](../ros2/config/fastdds.xml) | Shared DDS transport configuration, including shared-memory sizing |

### Navigation and painted costs — `igvc_navigation`, `igvc_lane_layer`

| File | Responsibility |
|---|---|
| [local_navigation.yaml](../ros2/src/igvc_navigation/config/local_navigation.yaml) | Main tuning authority: Smac, MPPI, footprint, inflation, maps, observation layers, progress and behavior settings |
| [local_navigation.launch.py](../ros2/src/igvc_navigation/launch/local_navigation.launch.py) | Patch guard, Nav2/perception nodes, remappings and lifecycle activation |
| [local_goal.xml](../ros2/src/igvc_navigation/behavior_trees/local_goal.xml) | Single-goal behavior tree, bounded retries/wait behavior |
| [local_through.xml](../ros2/src/igvc_navigation/behavior_trees/local_through.xml) | Through-poses behavior tree for the associated Nav2 action |
| [lane_layer.cpp](../ros2/src/igvc_lane_layer/src/lane_layer.cpp) | Custom costmap layer for observed camera paint/hazards and related point inputs |
| [plugins.xml](../ros2/src/igvc_lane_layer/plugins.xml) | Registers the custom costmap plugin for Nav2 |

### Perception — `igvc_perception`

Paths below are in [igvc_perception/igvc_perception](../ros2/src/igvc_perception/igvc_perception/).
Read [ROS_PARAMETERS](guide/ROS_PARAMETERS.md) before changing timing/thresholds.

| File | Responsibility |
|---|---|
| [lane_node.py](../ros2/src/igvc_perception/igvc_perception/lane_node.py) | ROS RGB/CameraInfo/TF processing, lane/hazard output, observation memory, diagnostics, reset and health |
| [lanes.py](../ros2/src/igvc_perception/igvc_perception/lanes.py) | White-paint segmentation and image-space processing |
| [hazards.py](../ros2/src/igvc_perception/igvc_perception/hazards.py) | Colored/dark image hazard extraction; no physical barrel-coordinate lookup |
| [point_memory.py](../ros2/src/igvc_perception/igvc_perception/point_memory.py) | Candidate/confirmed observation memory with acquisition-time evidence and expiry |
| [depth_node.py](../ros2/src/igvc_perception/igvc_perception/depth_node.py) | Depth/CameraInfo/TF pairing, clouds, ground/surface classification, reset and health |
| [depth.py](../ros2/src/igvc_perception/igvc_perception/depth.py) | Depth image interpretation and point projection utilities |
| [ground.py](../ros2/src/igvc_perception/igvc_perception/ground.py) | Robust ground-plane estimation and bounded observed-prior support |
| [surfaces.py](../ros2/src/igvc_perception/igvc_perception/surfaces.py) | Connected observed shallow-surface eligibility across non-flat terrain |
| [surface_projection.py](../ros2/src/igvc_perception/igvc_perception/surface_projection.py) | Project image observations using depth-supported surface geometry and occlusion |
| [terrain_projection.py](../ros2/src/igvc_perception/igvc_perception/terrain_projection.py) | Terrain-plane projection helpers retained alongside the surface pipeline |
| [terrain_history.py](../ros2/src/igvc_perception/igvc_perception/terrain_history.py) | Bounded causal terrain observation history and timestamp selection |
| [scan_ground.py](../ros2/src/igvc_perception/igvc_perception/scan_ground.py) | Pure depth-supported lidar ground-return filtering |
| [scan_ground_node.py](../ros2/src/igvc_perception/igvc_perception/scan_ground_node.py) | ROS wrapper: scan/surface pairing, exact TF, conservative fallback and obstacle scan publication |
| [launch/perception.launch.py](../ros2/src/igvc_perception/launch/perception.launch.py) | Standalone perception session; do not launch beside navigation's copies of those nodes |
| [setup.py](../ros2/src/igvc_perception/setup.py) | Installs executable node entry points and package data |

### Synthetic geographic positioning — `igvc_gps`

| File | Responsibility |
|---|---|
| [synthetic_gps.py](../ros2/src/igvc_gps/igvc_gps/synthetic_gps.py) | Projects ideal odometry into geographic fixes and publishes origin metadata |
| [geodesy.py](../ros2/src/igvc_gps/igvc_gps/geodesy.py) | Geographic/local coordinate conversion math |
| [config/origin.json](../ros2/src/igvc_gps/config/origin.json) | Simulation geographic origin and model metadata |
| [config/waypoints.json](../ros2/src/igvc_gps/config/waypoints.json) | Small editable geographic mission example |
| [config/full_loop.json](../ros2/src/igvc_gps/config/full_loop.json) | Earlier full-loop mission input, not the current generated sparse mission |
| [synthetic_gps.launch.py](../ros2/src/igvc_gps/launch/synthetic_gps.launch.py) | Standalone GPS node launch; avoid duplicate publisher alongside R3-a launch |

<a id="unity-files"></a>
## Unity runtime, builders and assets

All files below are under [unity/IGVCSim](../unity/IGVCSim/). Runtime belongs to
`Assets/IGVC/Runtime`; batch generation/checks belong to `Assets/IGVC/Editor`.
Build methods regenerate fixtures, so persistent changes belong in the builder
or canonical configuration, not only in a generated scene.

### Runtime

| File | Responsibility |
|---|---|
| [TransportProbe.cs](../unity/IGVCSim/Assets/IGVC/Runtime/TransportProbe.cs) | Runtime coordinator, ROS registration, clock, pose/joints/lidar, simulator services, camera pitch, status and command-line options |
| [ProbeMotion.cs](../unity/IGVCSim/Assets/IGVC/Runtime/ProbeMotion.cs) | Ideal planar motion, speed/acceleration limits, command timeout, pause/reset/E-stop |
| [R3aKinematics.cs](../unity/IGVCSim/Assets/IGVC/Runtime/R3aKinematics.cs) | CAD robot driven-wheel and caster kinematics/frame mapping |
| [ProbeCamera.cs](../unity/IGVCSim/Assets/IGVC/Runtime/ProbeCamera.cs) | Rendered RGB capture, async readback, orientation and CameraInfo publication |
| [ProbeDepthCamera.cs](../unity/IGVCSim/Assets/IGVC/Runtime/ProbeDepthCamera.cs) | Ideal metric depth capture and matching CameraInfo |
| [CourseVariant.cs](../unity/IGVCSim/Assets/IGVC/Runtime/CourseVariant.cs) | Reads course manifest and constructs visible/collidable obstacles, lane paint and course settings |
| [CourseRamp.cs](../unity/IGVCSim/Assets/IGVC/Runtime/CourseRamp.cs) | Raised ramp geometry, surface height and associated lane construction |
| [LaneBoundaryGuard.cs](../unity/IGVCSim/Assets/IGVC/Runtime/LaneBoundaryGuard.cs) | Geometric boundary guard/scoring mechanism; sensor-led mode requires scoring-only operation |
| [TerrainSupport.cs](../unity/IGVCSim/Assets/IGVC/Runtime/TerrainSupport.cs) | Rigid support approximation from sampled terrain |
| [CasterTerrainSupport.cs](../unity/IGVCSim/Assets/IGVC/Runtime/CasterTerrainSupport.cs) | Terrain/body support with simplified caster suspension |
| [CasterSuspension.cs](../unity/IGVCSim/Assets/IGVC/Runtime/CasterSuspension.cs) | Spring/damper state and bounded suspension integration |
| [CasterSwivel.cs](../unity/IGVCSim/Assets/IGVC/Runtime/CasterSwivel.cs) | Motion-aligned caster yaw approximation |
| [CasterSwivelSettings.cs](../unity/IGVCSim/Assets/IGVC/Runtime/CasterSwivelSettings.cs) | Validated swivel settings structure/loading |
| [SpectatorCamera.cs](../unity/IGVCSim/Assets/IGVC/Runtime/SpectatorCamera.cs) | Zoom, orbit/pan, follow and overview camera controls |
| [RobotInspectionView.cs](../unity/IGVCSim/Assets/IGVC/Runtime/RobotInspectionView.cs) | Robot-only inspection view controls |

### Editor generation and checks

| File | Responsibility |
|---|---|
| [ProbeBuild.cs](../unity/IGVCSim/Assets/IGVC/Editor/ProbeBuild.cs) | Generates/builds the original simple transport fixture |
| [RobotInspectionBuild.cs](../unity/IGVCSim/Assets/IGVC/Editor/RobotInspectionBuild.cs) | Imports/stages canonical robot visuals and builds inspection fixtures |
| [R3aDriveBuild.cs](../unity/IGVCSim/Assets/IGVC/Editor/R3aDriveBuild.cs) | Builds the CAD drive test scene/player |
| [TerrainBenchBuild.cs](../unity/IGVCSim/Assets/IGVC/Editor/TerrainBenchBuild.cs) | Generates controlled terrain/suspension test fixtures |
| [SoonerCourseBuild.cs](../unity/IGVCSim/Assets/IGVC/Editor/SoonerCourseBuild.cs) | Constructs the reference-course scene around the owned robot/runtime |
| [CourseLaneBuild.cs](../unity/IGVCSim/Assets/IGVC/Editor/CourseLaneBuild.cs) | Course lane/ground preparation used by the scene build pipeline |
| [GroundRenderChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/GroundRenderChecks.cs) | Current course player build entry points and ground rendering checks |
| [ProbeChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/ProbeChecks.cs) | Pure motion/transport fixture invariants |
| [R3aKinematicsChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/R3aKinematicsChecks.cs) | Canonical drive geometry/frame/kinematics checks |
| [DepthChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/DepthChecks.cs) | Ideal depth fixture/render checks |
| [CourseRampChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/CourseRampChecks.cs) | Procedural ramp geometry and lane consistency |
| [TerrainSupportChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/TerrainSupportChecks.cs) | Rigid terrain support behavior |
| [CasterSuspensionChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/CasterSuspensionChecks.cs) | Suspension integration and limits |
| [CasterSwivelChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/CasterSwivelChecks.cs) | Swivel direction/rate behavior |
| [CasterTerrainChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/CasterTerrainChecks.cs) | Suspension/terrain support integration |
| [CasterTurningChecks.cs](../unity/IGVCSim/Assets/IGVC/Editor/CasterTurningChecks.cs) | Turning/terrain support cases |

### Project/asset locations

| Location | Responsibility |
|---|---|
| [ProjectSettings/ProjectVersion.txt](../unity/IGVCSim/ProjectSettings/ProjectVersion.txt) | Exact Unity Editor version |
| [ProjectSettings/](../unity/IGVCSim/ProjectSettings/) | Project/player/render/input/build settings; respect builder overrides |
| [Packages/manifest.json](../unity/IGVCSim/Packages/manifest.json), [packages-lock.json](../unity/IGVCSim/Packages/packages-lock.json) | ROS-TCP-Connector and Unity dependency pins |
| [Assets/IGVC/Scenes/TransportProbe.unity](../unity/IGVCSim/Assets/IGVC/Scenes/TransportProbe.unity) | Checked-in original fixture scene; not an authoritative map of the current generated course |
| [Assets/IGVC/Materials/](../unity/IGVCSim/Assets/IGVC/Materials/) | Owned fixture materials, with `.meta` files |
| `Assets/IGVC/GeneratedRobot/` | Ignored generated robot visuals; regenerate from canonical sources |
| `Assets/IGVC/External/` | Ignored imported Sooner environment assets; fetched/prepared locally |

<a id="mission-files"></a>
## Course and mission software

| File | Responsibility / mode |
|---|---|
| [generate_course_variant.py](../tools/generate_course_variant.py) | Seeded geometry, colored obstacles, lane gaps/ramp, clearance checks, manifests and previews |
| [export_autonomy_mission.py](../tools/export_autonomy_mission.py) | Produces the allowlisted sparse geographic mission without exporting the solution route |
| [sensor_course.py](../tools/sensor_course.py) | **Current sensor-led motion coordinator**: observations, local goals, Nav2 actions, progress, adequate recovery and reports |
| [observed_navigation.py](../tools/observed_navigation.py) | Chooses observed lane-entry/heading guidance before broad GPS fallback |
| [sensor_route_policy.py](../tools/sensor_route_policy.py) | Bounded forward-arc search through observed costs with swept full-footprint clearance |
| [lane_corridor_policy.py](../tools/lane_corridor_policy.py) | Proposes a corridor/entrance from paired observed paint; does not itself prove a drivable route |
| [lane_heading_memory.py](../tools/lane_heading_memory.py) | Bounded remembered direction through gaps; no inferred hidden lane bounds |
| [recovery_policy.py](../tools/recovery_policy.py) | Selects adequate straight backup from observed rear sweep and useful forward continuation; no commands itself |
| [audit_sensor_run.py](../tools/audit_sensor_run.py) | Read-only offline sensor-run audit; full geometry is scoring-only |
| [full_course.py](../tools/full_course.py) | **Guided regression** mission using ordered known-route checkpoints; not current first-time autonomy |
| [course_progress.py](../tools/course_progress.py) | Fail-closed ordered-route progress/continuity audit for guided runs |
| [approach_speed.py](../tools/approach_speed.py) | Guided waypoint braking cap; distinct from current MPPI/mission speed tuning |
| [gps_mission.py](../tools/gps_mission.py) | Lists/runs editable geographic missions through ROS; running one commands navigation |
| [plan_course_loop.py](../tools/plan_course_loop.py) | Inspects the pinned reference route for the earlier loop workflow |
| [nav_control.py](../tools/nav_control.py) | Motion/state: terminal goal and cancellation interface in `odom` metres/radians |
| [cancel_mission.py](../tools/cancel_mission.py) | Motion/state: bounded cancellation for the older mission observer |
| [recover_course.py](../tools/recover_course.py) | Motion/state: explicit backup for paused guided-course observer; not the new recovery selector |
| [save_stopped_checkpoint.py](../tools/save_stopped_checkpoint.py) | Motion/state: stop/pause and record exact state for a diagnostic rebuild/resume |
| [audit_course_variant.py](../tools/audit_course_variant.py) | Read-only generated guided-run geometry audit |
| [audit_loop_trajectory.py](../tools/audit_loop_trajectory.py) | Read-only sampled footprint/barrel and motion audit |
| [plot_loop_run.py](../tools/plot_loop_run.py) | Offline route/trajectory plot; never commands the robot |
| [render_variant_gallery.py](../tools/render_variant_gallery.py) | Offline geometry/trajectory gallery from saved files |
| [run_variant_suite.ps1](../tools/run_variant_suite.ps1) | Multi-variant experiment runner; inspect its mode before use and treat as session/motion-producing |
| [tune_navigation.py](../tools/tune_navigation.py) | **Historical tuning utility:** writes old RPP keys and 0.75 m inflation; do not use as the current MPPI configuration method |
| [set_nav_tolerance.py](../tools/set_nav_tolerance.py) | Motion/state configuration: bounded live goal-tolerance RPC; not a persisted source edit |

<a id="diagnostic-tools"></a>
## Preparation, diagnostics and live checks

### CAD and scene preparation

| File | Responsibility |
|---|---|
| [audit_robot.py](../tools/audit_robot.py) | Read-only URDF/STL inventory and numerical consistency; not physical calibration |
| [prepare_description.py](../tools/prepare_description.py) | Normalizes unchanged audited SolidWorks exports, including forward orientation and physical left/right naming |
| [simplify_robot.py](../tools/simplify_robot.py) | Creates checked visual-only mesh reductions without replacing canonical mesh authority |
| [locate_lidar_mount.py](../tools/locate_lidar_mount.py) | Read-only source-CAD roof/mount investigation |
| [prepare_lidar.py](../tools/prepare_lidar.py) | Converts supplied lidar model into a checked provisional visual mesh |
| [locate_camera_mount.py](../tools/locate_camera_mount.py) | Read-only top-pole geometry investigation |
| [prepare_camera_mount.py](../tools/prepare_camera_mount.py) | Connectivity analysis and controlled extraction of the moving bracket |
| [prepare_camera.py](../tools/prepare_camera.py) | Tessellates OAK-D Pro enclosure geometry and stages visual provenance |
| [import_sooner_course.py](../tools/import_sooner_course.py) | Imports environment-only reference assets and strips upstream behavior code |

### Observers, capture and replay

| File | Responsibility / effect |
|---|---|
| [capture_rgb.py](../tools/capture_rgb.py) | Read-only: saves an actual ROS RGB image |
| [capture_depth_fixture.py](../tools/capture_depth_fixture.py) | Read-only: exact-stamp depth/CameraInfo/TF fixture |
| [capture_variant_frame.py](../tools/capture_variant_frame.py) | Read-only: RGB/perception snapshot for stopped-course diagnosis |
| [capture_rviz.cpp](../tools/capture_rviz.cpp) | RViz/display capture helper for visual evidence |
| [replay_depth_fixture.py](../tools/replay_depth_fixture.py) | Offline replay through current depth/ground logic; no ROS motion |
| [diagnose_course_costmap.py](../tools/diagnose_course_costmap.py) | Read-only live footprint-edge/costmap diagnostics |
| [trace_perception_stop.py](../tools/trace_perception_stop.py) | Read-only observations around a latched autonomy stop |
| [measure_stream.py](../tools/measure_stream.py) | Read-only sensor/clock receipt-rate measurement with chosen QoS |
| [observe_perception_health.py](../tools/observe_perception_health.py) | Read-only wall-time health observer |
| [observe_ramp_edges.py](../tools/observe_ramp_edges.py) | Read-only surveyed ramp observations; geometry truth is diagnostic, not autonomy input |
| [observe_terrain_perception.py](../tools/observe_terrain_perception.py) | Read-only controlled-bench perception observations |
| [observe_timer_clocks.py](../tools/observe_timer_clocks.py) | Read-only timer, clock-step and scheduling correlations |
| [observe_scheduler.py](../tools/observe_scheduler.py) | Read-only Linux scheduler/clock evidence independent of ROS callbacks |

### Verification entry points

| File | What it checks / effect |
|---|---|
| [docker/verify_environment.py](../docker/verify_environment.py) | Read-only container OS/ROS, packages, controller marker and mesh availability |
| [docker/verify_integration.py](../docker/verify_integration.py) | Read-only live sensor/clock/pairing/TF checks; also usable natively with an explicit report path |
| [docker/verify_controls.py](../docker/verify_controls.py) | **Motion/state:** velocity, timeout and E-stop checks at a clear stopped origin |
| [docker/verify_forward_policy.py](../docker/verify_forward_policy.py) | **Motion/state:** command policy checks; not a full course pass |
| [verify_course.py](../tools/verify_course.py) | Read-only reference-course stream smoke check |
| [verify_variant_sensors.py](../tools/verify_variant_sensors.py) | Read-only procedural-course sensor evidence |
| [verify_depth.py](../tools/verify_depth.py) | Read-only ideal depth stream proof |
| [verify_ground_fixtures.py](../tools/verify_ground_fixtures.py) | Offline saved GPU depth versus analytic fixture metadata |
| [verify_lanes.py](../tools/verify_lanes.py) | Read-only live lane observation validation |
| [verify_terrain_lanes.py](../tools/verify_terrain_lanes.py) | Read-only lane/terrain receipt and timestamp consistency |
| [verify_gps.py](../tools/verify_gps.py) | Read-only GPS/odometry correspondence and endpoint snapshot |
| [verify_camera_mount.py](../tools/verify_camera_mount.py) | **Motion/state:** live camera hinge, TF and calibration checks |
| [verify_navigation.py](../tools/verify_navigation.py) | **Motion/state:** bounded navigation checks on its known fixture |
| [verify_lane_guard.py](../tools/verify_lane_guard.py) | **Motion/state:** geometric boundary enforcement check, including resets; not a sensor-led-lap test |
| [verify_lane_watchdog.py](../tools/verify_lane_watchdog.py) | **Fault injection:** suspends lane detection to verify authority stops |
| [verify_reconnect.py](../tools/verify_reconnect.py) | **Process/state:** restarts the owned endpoint while Unity remains alive |
| [verify_caster_swivel.py](../tools/verify_caster_swivel.py) | **Motion:** bounded flat-pad caster swivel check |
| [verify_caster_suspension.py](../tools/verify_caster_suspension.py) | **Motion:** manual suspension-bench traversal |
| [verify_caster_turning.py](../tools/verify_caster_turning.py) | **Motion:** surveyed ramp pivot/arc experiment |
| [verify_terrain_body.py](../tools/verify_terrain_body.py) | **Motion:** manual terrain-bench body support test |
| [verify_course_ramp.py](../tools/verify_course_ramp.py) | **Motion:** controlled ramp consistency test; does not certify autonomous crossing |

<a id="tests"></a>
## Tests

These are focused source suites, distinct from the live checks above. The current
project also has custom Unity Editor batch checks listed in the Unity table.

| Test / directory | Behavior under test |
|---|---|
| [test_sensor_route_policy.py](../tools/tests/test_sensor_route_policy.py) | Observed-only forward search, cost semantics and swept footprint |
| [test_sensor_mission_contract.py](../tools/tests/test_sensor_mission_contract.py) | Sparse mission validation / accepted input contract |
| [test_autonomy_mission_export.py](../tools/tests/test_autonomy_mission_export.py) | Export omits privileged route/geometry details |
| [test_observed_navigation.py](../tools/tests/test_observed_navigation.py) | Observed corridor/heading guidance still obeys collisions |
| [test_lane_corridor_policy.py](../tools/tests/test_lane_corridor_policy.py) | Paired-paint proposals and invalid/ambiguous line cases |
| [test_lane_heading_memory.py](../tools/tests/test_lane_heading_memory.py) | Bounded direction memory and expiry |
| [test_recovery_policy.py](../tools/tests/test_recovery_policy.py) | Adequate backup, blocked/unknown rear, useful continuation and spawned callback integration |
| [test_navigation_policy.py](../tools/tests/test_navigation_policy.py) | Adapter command limits, pivots and bounded straight reverse |
| [test_point_memory.py](../tools/tests/test_point_memory.py) | Candidate/confirmed observations and acquisition-time evidence |
| [test_course_variants.py](../tools/tests/test_course_variants.py) | Generated course geometry, placement/clearance and seeded variants |
| [test_course_progress.py](../tools/tests/test_course_progress.py), [test_mission_gap_modes.py](../tools/tests/test_mission_gap_modes.py) | Guided route progress and mission gap-mode behavior |
| [test_approach_speed.py](../tools/tests/test_approach_speed.py) | Guided waypoint speed cap |
| [test_docker_reporting.py](../tools/tests/test_docker_reporting.py) | Docker reporting behavior |
| [test_linux_session.py](../tools/tests/test_linux_session.py) | Linux launcher/session ownership behavior |
| [test_suspension_description.py](../tools/test_suspension_description.py) | Canonical description/suspension behavior without live ROS |
| [igvc_perception/test/](../ros2/src/igvc_perception/test/) | Depth, ground, surfaces, projection/history, lidar filtering, lane and hazard cases |
| [test_geodesy.py](../ros2/src/igvc_gps/test/test_geodesy.py) | Geographic conversion math |
| [tools/agents/offline.test.mjs](../tools/agents/offline.test.mjs) | Optional review-runner offline constraints; no paid review required |
| [patch_nav2_cost_critic.py](../docker/patch_nav2_cost_critic.py) | Adds a regression to upstream real `critics_tests`; Docker/native overlay builders compile and execute it |

<a id="documents"></a>
## Documentation library

This indexes the project topic documents. Many contain dated results; their
presence does not make an old configuration current. Prefer the master guide
and its parameter references for orientation, then use the linked source/evidence.

### Current orientation and operation

| Document | What to use it for |
|---|---|
| [PROJECT_GUIDE.md](PROJECT_GUIDE.md) | Master architecture, workflow, interfaces, editing and troubleshooting |
| [FILE_INDEX.md](FILE_INDEX.md) | This linked source and documentation directory |
| [guide/ROS_PARAMETERS.md](guide/ROS_PARAMETERS.md) | Exact current navigation/perception/mission parameters and application workflow |
| [guide/UNITY_AND_COURSE.md](guide/UNITY_AND_COURSE.md) | Exact Unity/world/robot editing paths and regeneration rules |
| [NATIVE_AUTONAV.md](NATIVE_AUTONAV.md) | Native Jazzy patched controller setup and sensor-led launch commands |
| [SENSOR_AUTONOMY.md](SENSOR_AUTONOMY.md) | Current autonomous architecture, observations, experimental results and unresolved failures |
| [REFERENCE_COURSE.md](REFERENCE_COURSE.md) | Current user-reference map interpretation, sectors, gaps and outer ramp barrel bands |
| [RAMP_DESCENT_FILTER.md](RAMP_DESCENT_FILTER.md) | Observed cause and controlled validation of descent lidar ground filtering |
| [SOONER_COMPARISON.md](SOONER_COMPARISON.md) | Actual software/algorithm reuse boundary versus SoonerRobotics |

### Plans, platform and collaboration

| Document | What to use it for |
|---|---|
| [PLAN.md](PLAN.md) | Phase gates, architecture decisions and remaining work; contains historical progress updates |
| [WORKFLOW.md](WORKFLOW.md) | Development workflow and intended repository/process organization |
| [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md) | Task packets, ownership, bounded delegation and review practice |
| [RUNBOOK.md](RUNBOOK.md) | Native tools and fixture commands; distinguish historical guided modes from current native sensor command |
| [BASELINE.md](BASELINE.md) | Initial environment/project inventory, not a live status snapshot |
| [HISTORY.md](HISTORY.md) | Earlier native-WSL setup and result history |
| [DOCKER_PLAN.md](DOCKER_PLAN.md) | Container delivery goals and gates |
| [DOCKER_VALIDATION.md](DOCKER_VALIDATION.md) | Dated Docker integration, commands, builds and guided run evidence |
| [LINUX_PLAN.md](LINUX_PLAN.md) | Linux host/player/container implementation plan |
| [LINUX_VALIDATION.md](LINUX_VALIDATION.md) | Linux/WSLg/display testing evidence and scope limits |
| [AI/UnityProjectContext.md](AI/UnityProjectContext.md) | Accumulated Unity onboarding notes; early sections/settings may be superseded by source |
| [AI/ROS_FRESHNESS_TASK.md](AI/ROS_FRESHNESS_TASK.md) | Scoped freshness investigation packet and context |

### Robot, terrain, sensors and timing

| Document | What to use it for |
|---|---|
| [ROBOT_INSPECTION.md](ROBOT_INSPECTION.md) | Robot import/inspection workflow and findings |
| [ROBOT_GEOMETRY_REVIEW.md](ROBOT_GEOMETRY_REVIEW.md) | Geometry review, assumptions and physical uncertainty |
| [R3A_DRIVE.md](R3A_DRIVE.md) | Driven-axle frames, physical forward orientation and ideal kinematic model |
| [CAMERA_MOUNT.md](CAMERA_MOUNT.md) | Pole-top pitch-only camera placement, command and validation |
| [LIDAR_MOUNT.md](LIDAR_MOUNT.md) | Front roof housing placement and mesh alignment |
| [DEPTH_CAMERA.md](DEPTH_CAMERA.md) | Ideal metric-depth rendering, calibration, processing and proof |
| [CASTER_SWIVEL.md](CASTER_SWIVEL.md) | Motion-aligned caster model and validation |
| [CASTER_SUSPENSION.md](CASTER_SUSPENSION.md) | Simplified suspension model, settings and bench evidence |
| [CASTER_TURNING.md](CASTER_TURNING.md) | Turning/support experiment and model limits |
| [TERRAIN_BODY.md](TERRAIN_BODY.md) | Experimental body-support model and fixture |
| [TERRAIN_PERCEPTION.md](TERRAIN_PERCEPTION.md) | Earlier terrain transition failures and capture/replay evidence |
| [TERRAIN_LANES.md](TERRAIN_LANES.md) | RGB projection using observed terrain and timestamp pairing |
| [RAMP_EDGE_PERCEPTION.md](RAMP_EDGE_PERCEPTION.md) | Surface/lane-edge refinement and historical guided-ramp results |
| [ROS_TIMING.md](ROS_TIMING.md) | Steady watchdog timers versus acquisition/simulation time |
| [ROS_INTERFACE.md](ROS_INTERFACE.md) | Contract design plus implemented overrides; table also includes future interfaces |
| [TRANSPORT_EVIDENCE.md](TRANSPORT_EVIDENCE.md) | Original transport fixture evidence |

### Course, navigation and external reference history

| Document | What to use it for |
|---|---|
| [PROCEDURAL_COURSES.md](PROCEDURAL_COURSES.md) | Generator/variant workflow and earlier settings |
| [COURSE_RAMP.md](COURSE_RAMP.md) | Ramp integration with generated course and terrain model |
| [COURSE_LAYOUT_UPDATE.md](COURSE_LAYOUT_UPDATE.md) | Earlier layout/waypoint reduction; current layout is in REFERENCE_COURSE |
| [NAVIGATION.md](NAVIGATION.md) | Earlier Nav2 integration; controller settings may predate current Smac/MPPI profile |
| [LANE_DETECTION.md](LANE_DETECTION.md) | Lane perception and costmap integration history |
| [GPS_WAYPOINTS.md](GPS_WAYPOINTS.md) | Synthetic geographic model and geographic mission tools |
| [FULL_COURSE.md](FULL_COURSE.md) | Ordered guided full-loop mission/audit; not proof of sensor-led completion |
| [SOONER_COURSE.md](SOONER_COURSE.md) | Pinned environment-only source-course import |
| [SOONER_REFERENCE_REVIEW.md](SOONER_REFERENCE_REVIEW.md) | Reference repository review findings |
| [SOONER_AUTONOMY_REVIEW.md](SOONER_AUTONOMY_REVIEW.md) | Earlier external autonomy review/possible lessons |
| [2026_WINNER_LESSONS.md](2026_WINNER_LESSONS.md) | Lessons from supplied competition material; not a 2027 compliance statement |

### Mesh-specific documentation

| Document | What to use it for |
|---|---|
| [description README](../ros2/src/igvc_description/README.md) | Canonical robot package context |
| [camera README](../ros2/src/igvc_description/meshes/camera/README.md) | Camera mesh source and conversion |
| [camera mount README](../ros2/src/igvc_description/meshes/camera_mount/README.md) | Extracted moving/static bracket geometry |
| [lidar README](../ros2/src/igvc_description/meshes/lidar/README.md) | Lidar visual source and alignment limits |
| [simplified README](../ros2/src/igvc_description/meshes/simplified/README.md) | Visual reduction process and validation |

<a id="outputs"></a>
## Generated files and evidence

These paths are intentionally written as code, rather than links that would be
broken in a clean GitHub checkout.

| Path / pattern | Meaning |
|---|---|
| `artifacts/build-course/IGVCCourse.exe` | Windows course player; keep its companion data/runtime files together |
| `artifacts/build-course-linux/IGVCCourse.x86_64` | Linux course player and companion directory |
| `artifacts/courses/seed-N/course.json` | Complete physical world manifest; privileged simulation/evaluation data |
| `artifacts/courses/seed-N/autonomy.json` | Sparse sensor-led mission input |
| `artifacts/courses/seed-N/mission.json` | Guided regression mission input |
| `artifacts/courses/seed-N/overview.png` | Offline top-down preview; not a camera observation |
| `artifacts/courses/seed-N/sensor-run.json` | Docker sensor-led report; native command chooses `native-sensor-run.json` |
| `*.progress.json`, `*.observations.json` | Live progress and stopped observed-world snapshot for the associated report stem |
| `artifacts/courses/seed-N/docker-run.json` | Explicit guided Docker regression report |
| `artifacts/logs/` | Unity builds, managed native ROS sessions and diagnostic logs |
| `artifacts/checks/` | Local verifiers/captures/replays; ignored and not automatically published |
| `artifacts/session/` | Owned process records, locks and selected-session metadata |
| `artifacts/vendor/` | Pinned downloaded external source, not owned project code |
| `artifacts/agents/` | Optional bounded-review inputs, summaries and usage records |
| `~/igvc_ws/{build,install,log}` | Native ROS generated workspace outputs |
| `~/igvc_nav2_overlay/` | Native patched controller source/build/test/install and success marker |
| `/opt/igvc/install`, `/opt/nav2-patched/install` | Equivalent installed package locations inside the Docker image |

[docs/evidence/](evidence/) is the versionable evidence directory. Important
examples include [the 0.30 m partial audit](evidence/sensor-autonomy/point3-partial-audit.json),
[MPPI regression XML](evidence/sensor-autonomy/point3-mppi-tests.xml),
[ramp descent result](evidence/sensor-autonomy/ramp-descent-filter.json), and
[transport checks](evidence/sensor-autonomy/point3-integration.json). Preserve the
mode/date/limitations of each result when citing it.
