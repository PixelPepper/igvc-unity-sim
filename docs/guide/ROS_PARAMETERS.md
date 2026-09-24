# ROS and sensor-mission parameter reference

This reference describes the checked-in profile as of 2026-09-23. It does not assert that a running process has loaded these values. Read live parameters after restarting. The fixture uses ideal transport, ground-truth odometry and synthetic GPS; it is not a calibrated R3-a robot or proof of 2027 compliance or a completed sensor-led lap. Start with the [project guide](../PROJECT_GUIDE.md), [file index](../FILE_INDEX.md) and [README](../../README.md).

`course` runs [sensor_course.py](../../tools/sensor_course.py): sparse GPS destinations, observed costmaps, camera paint and bounded remembered direction. It never loads generated route geometry. `guided-course` is a separate known-guide regression. Historical guided completion counts must not be attributed to sensor-led navigation.

## Contents

- [Where a setting takes effect](#where-a-setting-takes-effect)
- [Costmaps and collision geometry](#costmaps-and-collision-geometry)
- [Nav2 planner and controller](#nav2-planner-and-controller)
- [Sensor-led mission, guidance and recovery](#sensor-led-mission-guidance-and-recovery)
- [Perception and command safety](#perception-and-command-safety)
- [GPS and sensor placement](#gps-and-sensor-placement)
- [Apply changes and validate](#apply-changes-and-validate)

## Where a setting takes effect

| Kind | How to change it | Persistence and application |
| --- | --- | --- |
| Nav2 ROS parameter | Edit [local_navigation.yaml](../../ros2/src/igvc_navigation/config/local_navigation.yaml), or supply the launch argument `params_file` | Restart navigation with the installed file. A successful `ros2 param set` is not a persistent configuration change; dynamic support varies by parameter. |
| Package-specific ROS parameter | Supply a launch/node parameter; declarations are identified below | These Python nodes read their declared settings at construction; restart them. |
| Python argument / constant | Edit the caller or helper source identified below | Not addressable through `ros2 param set`. Restart the mission or node; rebuild Docker when it contains the changed file. |
| Mission or sensor JSON | Edit the relevant input/configuration file | Mission inputs load when the mission starts; installed sensor/description inputs require rebuilding and restarting the relevant consumers. |

The [navigation launch](../../ros2/src/igvc_navigation/launch/local_navigation.launch.py) exposes `params_file` and `autostart` (default `true`), remaps Nav2 `cmd_vel` to `/cmd_vel/nav`, and selects the repository behavior trees. `global` means a larger rolling sensor costmap in `odom`, not a preloaded map.

## Costmaps and collision geometry

All names in this table are ROS parameters under `/global_costmap/global_costmap` or `/local_costmap/local_costmap`; values come from [local_navigation.yaml](../../ros2/src/igvc_navigation/config/local_navigation.yaml).

| Parameter | Global / local current value | Effect and dependency |
| --- | --- | --- |
| `global_frame`, `robot_base_frame` | `odom`, `base_footprint` for both | Canonical +X points toward the front driven wheels. The axle is the footprint origin; the long rear overhang matters in turns. |
| `rolling_window`, `track_unknown_space` | `true`, `true` | Unknown space remains distinct; planner policy blocks it. |
| `width`, `height` | 40 × 40 / 14 × 14 m | Larger windows increase memory and search workload. |
| `resolution` | 0.10 / 0.05 m | Finer cells improve geometric detail while increasing computation. |
| `update_frequency`, `publish_frequency` | 2 / 1 Hz global; 5 / 2 Hz local | Update and publication rates differ. Mission freshness uses received messages. |
| `transform_tolerance` | 0.3 s | Transform timing tolerance; not permission to project camera frames using an unrelated latest TF. |
| `footprint` | `[[0.6,0.5],[-1.1,0.5],[-1.1,-0.5],[0.6,-0.5]]` m | Full rectangle about the driven axle. Keep both costmaps consistent. |
| `footprint_padding` | 0.02 m | Mission reads the global footprint and padding, yielding bounds `(-1.12,0.62,-0.52,0.52)`. This is separate from inflation. |
| `inflation_layer.inflation_radius` | **0.30 m** | User-requested narrow inflation. It is not the robot radius or sufficient collision clearance by itself. |
| `inflation_layer.cost_scaling_factor` | 5.0 | Larger values make cost decay more steeply outside obstacles; they do not shrink the physical footprint. |
| `inflation_layer.inflate_unknown`, `inflate_around_unknown` | `false`, `false` | Unknown rejection is still enforced by the planners. |
| `always_send_full_costmap` | `true` | Mission receives full grids rather than reconstructing updates. |

The 0.30 m profile requires the [MPPI CostCritic patch](../../docker/patch_nav2_cost_critic.py). The launch refuses an installation without `nav2_mppi_controller/igvc-footprint-cost-critic-v1`. [Dockerfile](../../docker/Dockerfile) and [native overlay builder](../../tools/build_native_nav2.sh) build the pinned Nav2 1.3.12 revision and run its `critics_tests` regression. Do not bypass the marker or substitute stock Jazzy MPPI for this profile.

Both `obstacle_layer` instances separate marking from clearing:

| Parameter suffix | `scan` | `scan_obstacles` |
| --- | --- | --- |
| `topic` | `/scan` | `/perception/lidar/obstacles_scan` |
| `marking`, `clearing`, `inf_is_valid` | `false`, `true`, `true` | `true`, `false`, `false` |
| `min_obstacle_height`, `max_obstacle_height` | 0.0, 2.0 m | 0.0, 2.0 m |
| `obstacle_min_range`, `obstacle_max_range` | 0.15, 11.5 m | 0.15, 11.5 m |
| `observation_persistence`, `expected_update_rate` | 0.0, 0.6 s | 0.0, 0.6 s |

Raw `scan.raytrace_min_range=0.0` and `raytrace_max_range=12.0` m retain measured clearing endpoints. Filtering ground returns must not turn them into infinite clearing rays.

The three custom layers use [LaneLayer](../../ros2/src/igvc_lane_layer/src/lane_layer.cpp). Its only package-specific declared parameter is `<layer>.topic`: default `/perception/lanes/points`; `hazard_layer` overrides it to `/perception/hazards/points`, and `depth_layer` to `/perception/depth/obstacles`. It marks cells lethal, accepts at most 8000 finite points, and expires the received cloud after **0.75 s steady time** (hard-coded). Cloud freshness and the age of remembered individual paint points are different limits.

## Nav2 planner and controller

Names below are ROS parameters in the same [YAML](../../ros2/src/igvc_navigation/config/local_navigation.yaml); prefixes are significant.

| Node / parameter | Current value | Interpretation |
| --- | --- | --- |
| `/planner_server`: `GridBased.plugin` | `nav2_smac_planner::SmacPlannerHybrid` | Full-pose path planning. |
| `GridBased.motion_model_for_search`, `allow_unknown` | `DUBIN`, `false` | Forward arcs; unknown cells rejected. |
| `GridBased.minimum_turning_radius` | 0.6 m | Keep compatible with mission proposals and controller command constraints. |
| `GridBased.angle_quantization_bins`, `allow_primitive_interpolation` | 72, `true` | Heading discretization and extra primitives. |
| `GridBased.tolerance` | 0.25 m | Planner endpoint tolerance, distinct from controller arrival tolerance. |
| `GridBased.max_planning_time`, `max_iterations` | 2.0 s, 1000000 | Nav2 search limits; separate from the Python observed-route budget. |
| `GridBased.max_on_approach_iterations` | 1000 | Bounds endpoint approach work. |
| `GridBased.analytic_expansion_max_length` | 6.25 m | Bounds analytic connection length. |
| `GridBased.cost_penalty`, `non_straight_penalty`, `change_penalty` | 2.0, 1.1, 0.0 | Bias cost and turning preferences without replacing collision checks. |
| `GridBased.cache_obstacle_heuristic`, `smooth_path` | `false`, `true` | Recompute for changing observations; smooth planned paths. |
| `/controller_server`: `controller_frequency` | 20 Hz | Matches MPPI `model_dt=0.05` s. |
| `costmap_update_timeout`, `failure_tolerance` | 0.5, 1.0 s | Controller freshness and failure limits. |
| `progress_checker.required_movement_radius`, `movement_time_allowance` | 0.10 m, 15 s | Independent of mission-level stall detection. |
| `goal_checker.xy_goal_tolerance`, `yaw_goal_tolerance`, `stateful` | 0.30 m, π rad, `true` | Wide heading acceptance does not prove a useful next maneuver. Mission rejects nearby non-useful proposals. |
| `FollowPath.plugin`, `motion_model` | `nav2_mppi_controller::MPPIController`, `Ackermann` | Deliberate forward-arc constraint on a differential-drive simulator. |
| `FollowPath.AckermannConstraints.min_turning_r` | 0.55 m | Controller minimum turning radius. |
| `FollowPath.time_steps`, `model_dt` | 56, 0.05 s | 2.8 s prediction horizon. |
| `FollowPath.batch_size`, `iteration_count` | 1000, 1 | Sampling workload; increasing either costs CPU. |
| `FollowPath.vx_std`, `wz_std` | 0.4 m/s, 0.4 rad/s | Velocity sampling spread, not requested cruise speed. |
| `FollowPath.vx_max`, `vx_min`, `vy_max`, `wz_max` | 2.2, 0.0, 0.0 m/s; 1.0 rad/s | Forward-only controller. Backup is a separate behavior. |
| `FollowPath.ax_max`, `ax_min`, `az_max` | 1.0, −1.5 m/s²; 1.5 rad/s² | Acceleration/deceleration constraints. |
| `FollowPath.prune_distance` | 7.0 m | Path context retained for controller scoring. |
| `FollowPath.temperature`, `gamma` | 0.3, 0.015 | Sampling optimizer tuning. |
| `FollowPath.CostCritic.consider_footprint`, `trajectory_point_step` | `true`, 1 | Full footprint scoring at each trajectory point, with the required patch. |
| `FollowPath.CostCritic.cost_weight`, `critical_cost`, `collision_cost`, `near_goal_distance` | 3.81, 300.0, 1000000.0, 1.0 m | Obstacle scoring. Do not weaken collision costs to obtain higher speed. |
| `FollowPath.PathAlignCritic.offset_from_furthest`, `PathFollowCritic.offset_from_furthest`, `PathAngleCritic.offset_from_furthest` | 10, 5, 4 path points | Index offsets beyond trajectory progress, not fixed metre lookaheads. Effects depend on path sampling. |

The YAML also contains each critic's weights and activation thresholds; preserve the complete block when changing controller plugins. The [old tuning script](../../tools/tune_navigation.py) writes older RPP settings and resets inflation to 0.75 m; **do not use it to tune this MPPI profile**.

`/behavior_server` enables only `wait` and `backup`, at `cycle_frequency=10.0` Hz with `transform_tolerance=0.3` s. The mission supplies backup distance, speed and allowance per action; these are not persistent YAML backup distances.

## Sensor-led mission, guidance and recovery

These are Python/CLI values, **not ROS parameters**. [sensor_course.py](../../tools/sensor_course.py) is the actual caller; helper defaults are not necessarily its active settings.

| Setting | Helper default → mission value | Effect |
| --- | --- | --- |
| `robot_radius` | 0.65 → 0.5 m | Circle checks supplement the full supplied rectangle; not a replacement footprint. |
| `lookahead` | 3 → 7 m | Requested local path length; selected goal may be earlier to leave continuation. |
| `max_path_length` | 14 → 14 m | Bounded observed search horizon. |
| `min_progress` | 0.25 → 0.1 m | Minimum endpoint improvement toward the guidance target. |
| `forward_only` | `false` → `true` | Mission uses forward straight/curved primitives, not reverse or pivot escape. |
| `minimum_turn_radius` | 1.25 → 0.65 m | Slightly larger than Nav2's 0.6 m radius. |
| `max_expansions` | 10000 → 50000 | Search cap; more states can find longer detours but cost time. |
| `max_search_seconds` | `None` → 5.0 s | Cooperative expansion budget, checked every 64 expansions; precomputation is outside this timer. Mission has an 8 s external wait limit. |
| `min_goal_distance` | 0 → 0.4 m | Avoids proposals already within Nav2's 0.30 m acceptance zone. |
| `continuation_reserve` | 0 → 1.0 m | Leave checked path beyond a local goal unless the actual planning destination is reached. |

[sensor_route_policy.py](../../tools/sensor_route_policy.py) blocks unknown/lethal squares, blocks centre costs ≥99, and checks continuous full-footprint sweeps with conservative sampling margins. Its 16 heading states use ±π/8 turns and step `max(minimum_turn_radius*π/8, 2*resolution)`. Endpoint selection prefers progress (`remaining + 0.01*travel`); this is a bounded proposal, not proof of global reachability. Full rectangle bounds are read from Nav2, rather than duplicated in the mission.

[observed_navigation.py](../../tools/observed_navigation.py) first seeks a paired observed lane corridor. [lane_corridor_policy.py](../../tools/lane_corridor_policy.py) defaults to `min_width=2`, `max_width=8`, `horizon=14`, `lookahead=3` m; the wrapper passes `min_width=1.2` and the mission's 7 m lookahead. A blocked visible entrance does not silently fall back to a GPS shortcut. [GapHeadingMemory](../../tools/lane_heading_memory.py) defaults to `max_travel=20` m and `max_age=60` monotonic seconds. It remembers observed direction, not invisible lane boundaries. The wrapper uses it only when the destination lies within 60° of that direction; final approaches within 1 m bypass corridor/hint guidance.

[recovery_policy.py](../../tools/recovery_policy.py) tests straight rear distances `(0.6,0.9,1.2,1.5,1.8)` m, default `max_backup_distance=1.8` m (validated maximum 2 m). It checks the entire padded rear sweep, stops at the first obstruction, and shares `max_search_seconds=5` s / `max_expansions=50000` across candidates. A candidate must unlock ≥1 m forward goal displacement/path, ≥1 m checked continuation, a goal ≥0.4 m away from the original trap, and endpoint progress ≥0.5 m toward its guidance target. A clear backup endpoint alone is insufficient.

The mission allows at most two recoveries per destination, commands backup at 0.1 m/s, and sets action allowance to `ceil(distance/speed)+3` s. It cancels the prior action before searching. Search runs in a spawned process while the main process services ROS callbacks. Lack of safe recovery stops the mission; it does not license shrinking the footprint.

Mission CLI defaults are `--speed 2.2` m/s and `--timeout 600` s; `--mission` and `--report` are required. `/speed_limit` is the minimum of CLI speed, mission JSON `max_speed_mps`, and 2.2 m/s. This is a ceiling, not an achieved-speed guarantee. Mission replan spacing is 1.5 s; stall detection uses 20 s without 0.15 m displacement or two failed actions. Monotonic reception-age limits are grid 5 s, odom 1 s, simulator status 3 s, lanes 1.5 s and autonomy-enabled status 1 s (after the initial 1 s grace).

## Perception and command safety

| Source / setting | Current value and kind | Effect / dependency |
| --- | --- | --- |
| [lane_node.py](../../ros2/src/igvc_perception/igvc_perception/lane_node.py): `point_ttl` | ROS parameter, default 8 s; navigation launch overrides **1200 s** | Paint/hazard point memory; limits 8000/4000 points are hard-coded. Longer memory retains observed boundaries behind the camera. Mission resets observations at startup. |
| [depth_node.py](../../ros2/src/igvc_perception/igvc_perception/depth_node.py) | Hard-coded timer 0.2 s, cache 8 frames, initial processing delay 0.04 s, image freshness 0.5 s, prior expiry 0.75 s | Exact image/CameraInfo/acquisition TF matching. It declares no custom ROS tuning parameters. |
| [depth.py](../../ros2/src/igvc_perception/igvc_perception/depth.py): `depth_points(...,stride=4)` | Python default 4 pixels; 320×240 float image; accepted optical Z 0.2–10 m | Must use depth CameraInfo, not unscaled RGB intrinsics. |
| [surfaces.py](../../ros2/src/igvc_perception/igvc_perception/surfaces.py), [ground.py](../../ros2/src/igvc_perception/igvc_perception/ground.py) | Hard-coded observed geometry/connectivity tests | Ground is not inferred from course labels or a global height cutoff. A shallow connected object can remain ambiguous. |
| [scan_ground_node.py](../../ros2/src/igvc_perception/igvc_perception/scan_ground_node.py) | Hard-coded 0.2 s timer, 8-frame caches, 0.04 s delay, preceding depth support ≤0.3 s old in acquisition time and ≤0.75 s arrival age | Exact scan acquisition TF required; absent/invalid support passes raw returns through for marking. No custom ROS parameters. |
| [scan_ground.py](../../ros2/src/igvc_perception/igvc_perception/scan_ground.py): `xy_radius`, `height_tolerance` | Python defaults 0.3 m, 0.04 m | Requires ≥3 non-collinear ground samples within 0.6 m, plane slope ≤20°, fit residual ≤0.025 m, and hit inside observed support. Ambiguous/elevated evidence retains the return. Removed marking ranges become NaN; raw clearing stream remains unchanged. |
| [probe_adapter.py](../../ros2/src/igvc_sim_bridge/igvc_sim_bridge/probe_adapter.py): `r3a_mode`, `require_lanes`, `require_depth` | ROS defaults `false`; [r3a.launch.py](../../ros2/src/igvc_sim_bridge/launch/r3a.launch.py) sets all `true` | Production launch enables the body TF path and perception gates. |
| Adapter freshness | Hard-coded 0.75 s camera/lane and depth; command 0.3 s; clock 0.5 s; timer 0.05 s | Perception expiry latches autonomy off. Missing paint is permitted in unmarked mode, but healthy camera/depth remain required. Manual takeover also disables autonomy. |
| Adapter twist saturation | Hard-coded forward 2.2 m/s, reverse 0.3 m/s, yaw 1 rad/s | Uniform scaling preserves commanded curvature. These manual/output caps differ from the stricter autonomy policy. |
| [navigation_policy.py](../../ros2/src/igvc_sim_bridge/igvc_sim_bridge/navigation_policy.py) | Hard-coded autonomous reverse ≥−0.100001 m/s and `abs(angular)≤1e-6`; forward `abs(angular)≤max(2*linear,1e-6)` | Slow straight backup only; no pivot; forward radius ≥0.5 m when turning. Invalid commands become stops. |

Point retention uses [PointMemory](../../ros2/src/igvc_perception/igvc_perception/point_memory.py): unconfirmed points expire after at most 3 s; five distinct acquisition stamps spanning at least 0.4 s earn the configured longer TTL. These are Python defaults, not ROS parameters. Thus `point_ttl=1200` does not retain every one-frame detection for 20 minutes.

The 2.2 m/s cap leaves margin below the supplied 2026 five-mph reference. It does not certify the unverified 2027 rules. Do not increase watchdog limits to hide missing observations without investigating timestamps, callback latency and compute load.

## GPS and sensor placement

[synthetic_gps.py](../../ros2/src/igvc_gps/igvc_gps/synthetic_gps.py) declares ROS parameter `origin_file`, defaulting to installed [origin.json](../../ros2/src/igvc_gps/config/origin.json). Current fields: latitude 42°; longitude −83°; altitude 0 m; `world_frame=odom`; `axes=x_east_y_north_z_up`; `model=synthetic_ideal_from_odometry`; `noise_stddev_m=0.0`. The node rejects nonzero noise or incompatible model/frame metadata. It converts `/odom` to `/gps/fix` at at most 10 Hz; it does not fuse GNSS or estimate localization.

Mission schema requires `schema_version=1`, `origin`, 1–10 `goals` (latitude/longitude/altitude/`radius_m`) and `max_speed_mps` in `(0,2.2]`. Route geometry and goal headings are forbidden. Each `radius_m` must be 0.4–5 m. Mission origin must equal live `/gps/origin`. Changing the origin requires matching mission inputs and a GPS-node restart.

Sensor mounts are description JSON, not ROS tuning parameters: [camera_mount.json](../../ros2/src/igvc_description/config/camera_mount.json) specifies default pitch `0.17453292519943295` rad (10° down), simulated limits ±π/6 and +Y pitch axis; [lidar_mount.json](../../ros2/src/igvc_description/config/lidar_mount.json) specifies `scan_xyz_m=[0.2700228,0,0.3396]` relative to `base_link`. Camera is on the rear pole; lidar is on the front roof. CAD-derived optical positions and simulated actuator limits are provisional, not hardware calibration. See [camera](../CAMERA_MOUNT.md), [lidar](../LIDAR_MOUNT.md) and [drive conventions](../R3A_DRIVE.md) before changing geometry or regenerated descriptions.

## Apply changes and validate

Run commands from the repository root. These are targeted checks to perform, not results claimed by this document. Coordinate all restart/build/motion operations with the session owner.

Docker copies ROS source/config and Python tools into the image; [Compose](../../compose.yaml) mounts `artifacts`, not the source tree. Editing a host YAML or Python file does not update the running image. After a change, stop the owned session, run `./tools/docker.ps1 build`, then restart with the intended seed/difficulty. Linux equivalents use `bash tools/docker.sh`. Unity changes additionally require `unity-build`; ROS-only tuning does not. See [Dockerfile](../../docker/Dockerfile) for the installed paths and build tests.

Native WSL: run `bash tools/build_ros.sh` after ROS package/config changes, then restart affected launch processes. For initial setup or changes to the pinned MPPI patch, use `bash tools/build_native_nav2.sh`; this checks the pinned Jazzy package/revision, runs its C++ regression, and writes a validation marker only after success. [ros_env.sh](../../tools/ros_env.sh) loads `~/igvc_ws` and the validated `~/igvc_nav2_overlay`. Source it in each diagnostic terminal. Do not run Docker and native sessions simultaneously on port 10000. See the [native workflow](../NATIVE_AUTONAV.md).

```powershell
# Inspect the running Docker profile, without requesting motion:
./tools/docker.ps1 run ros2 param get /local_costmap/local_costmap inflation_layer.inflation_radius
./tools/docker.ps1 run ros2 param get /controller_server FollowPath.CostCritic.consider_footprint
./tools/docker.ps1 run ros2 param get /planner_server GridBased.minimum_turning_radius
./tools/docker.ps1 run ros2 param get /igvc_lane_detector point_ttl
./tools/docker.ps1 run ros2 topic echo /perception/lidar/status --once
./tools/docker.ps1 run ros2 topic echo /sim/autonomy_stop_reason --once
```

Expect 0.3, `true`, 0.6 and 1200 for this launch profile. A mismatch indicates a different installed configuration, launch override or running process. Lidar status reports removed-ground counts and fallback reasons; a passthrough reason is not evidence of obstacle-free terrain. An autonomy stop reason explains a latched gate; do not silently re-enable it.

```bash
# Pure Python behavioral tests; no simulator motion. Run in WSL/Linux with dependencies.
python3 -m unittest discover -s tools/tests -p 'test_recovery_policy.py'
python3 -m unittest discover -s tools/tests -p 'test_observed_navigation.py'
python3 -m unittest discover -s tools/tests -p 'test_sensor_route_policy.py'
# Perception tests in the configured ROS development environment:
python3 -m pytest ros2/src/igvc_perception/test/test_scan_ground.py
```

A passing recovery test demonstrates the synthetic checked behavior, not that every live trap permits backup. A passing filter test does not replace acquisition-time TF and costmap inspection during a ramp traversal. Use [sensor autonomy documentation](../SENSOR_AUTONOMY.md) for the experimental validation boundary; inspect current run reports for actual completion and stop reasons.
