# Proposed ROS 2 contract

Implemented terrain projection: `/perception/lanes/status` now includes `ground`, `ground_stamp_ns`, and `ground_age_s` instead of `ground_z`. RGB lane/hazard projection requires a preceding depth plane within 0.35 acquisition seconds and 0.5 receipt seconds, using each RGB acquisition's own TF. Missing estimates invalidate projection without a fixed-ground fallback. See [terrain lanes](TERRAIN_LANES.md). Periodic bridge/perception watchdog work uses explicit steady clocks; sensor message stamps remain simulation acquisition time.

Design specification, not implemented behavior. Hardware is OAK-D Pro plus RPLIDAR A1; final names/rates depend on their configured drivers. Keep the same interfaces between ideal and realistic modes. Use single-robot root topics initially; reserve a consistent namespace policy before adding multiple robots. Inspect a real driver topic/type/QoS snapshot before freezing names, and use launch remaps or explicit encoding adapters to match it. Optional OAK left/right streams and their optical frames are added only if consumed by the team's stack.

Current probe deviations are explicit: `/cmd_vel/teleop` feeds a manual adapter, `/cmd_vel` is inspection output, and Unity consumes `/sim/drive_command` (`TwistStamped`) with original simulation acquisition stamps. The pinned endpoint creates reliable publishers with bounded history; the live verifier and sensor RViz displays use compatible best-effort subscriptions. State queues are 10; RGB/scan queues are 1. WSL Fast DDS has an explicit 8 MiB SHM segment to accommodate image bursts. Ideal ground truth supplies `/odom` and dynamic TF. Reset preserves monotonic time and requires fresh commands. This is the implemented transport fixture in [RUNBOOK.md](RUNBOOK.md), not the complete interface table below.

## Topics and ownership

Camera mount implementation now provides `/sim/camera_pitch_command` (`std_msgs/Float64`, absolute radians, positive down) and `/camera/color/camera_info` synchronized with RGB. Camera joint/body/optical TF comes from the canonical description and Unity pitch feedback. See [camera mount](CAMERA_MOUNT.md). The pinhole calibration describes Unity; physical OAK optics remain uncalibrated. The implemented ideal depth stream is 320x240 32FC1 metres at nominal 10 Hz, uses camera_color_optical_frame, and produces sampled 5 Hz clouds. These explicitly supersede the target depth rates/resolution in the table below; see DEPTH_CAMERA.md.

The implemented [R3-a ideal-motion mode](R3A_DRIVE.md) supplies original robot joint states and an axle-centered `base_footprint` with the CAD base offset. The topic table below remains the target contract; implemented overrides above take precedence. Hardware estimation and sensor fidelity remain incomplete.

`/perception/depth/healthy` (`std_msgs/Bool`) requires a fresh exact-stamp depth/CameraInfo/TF acquisition and confident observed ground plane. The R3-a launch enables `require_depth`: 0.75 wall seconds without a positive update latches autonomy off; recovered perception does not rearm it. Lane freshness is required independently. Manual control remains available. `/perception/depth/status` reports the fitted plane or failure reason; `/perception/depth/obstacles` carries terrain-relative positive obstacles in `odom`.

| Topic | Message type | Producer → consumer | Initial rate / QoS target |
|---|---|---|---|
| `/clock` | `rosgraph_msgs/msg/Clock` | Unity via bridge → all simulation-time nodes | 100 Hz; best effort, volatile, depth 1 |
| `/cmd_vel/teleop` | `geometry_msgs/msg/Twist` | terminal teleop → arbiter | 20 Hz; reliable, volatile, depth 1 |
| `/cmd_vel/nav` | `geometry_msgs/msg/Twist` | Nav2 command chain → arbiter | 20 Hz; reliable, volatile, depth 1 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | arbiter → Unity | 20 Hz; reliable, volatile, depth 1 |
| `/joint_states` | `sensor_msgs/msg/JointState` | Unity → robot_state_publisher, encoder processing | 50 Hz; reliable, volatile, depth 5 |
| `/wheel/odom` | `nav_msgs/msg/Odometry` | ROS encoder integrator using Unity joint feedback → estimator | 50 Hz; reliable, volatile, depth 5 |
| `/odom` | `nav_msgs/msg/Odometry` | selected odometry/estimation authority → Nav2, RViz | 50 Hz; reliable, volatile, depth 5 |
| `/imu/data` | `sensor_msgs/msg/Imu` | Unity → estimator, RViz | 100 Hz; best effort, volatile, depth 5 |
| `/scan` | `sensor_msgs/msg/LaserScan` | Unity RPLIDAR A1 model → costmap/localization, RViz | provisional 5.5 Hz; best effort, volatile, depth 5 |
| `/camera/color/image_raw` | `sensor_msgs/msg/Image` | Unity → perception, RViz | 640x480, RGB8, 15 Hz; best effort, volatile, depth 2 |
| `/camera/color/camera_info` | `sensor_msgs/msg/CameraInfo` | Unity/config adapter → perception, RViz | paired with image; same sensor QoS |
| `/camera/depth/image_raw` | `sensor_msgs/msg/Image` | Unity → depth processing, RViz | 640x480, 32FC1 metres, 15 Hz; same sensor QoS |
| `/camera/depth/camera_info` | `sensor_msgs/msg/CameraInfo` | Unity/config adapter → depth processing | paired with depth; same sensor QoS |
| `/camera/depth/points` | `sensor_msgs/msg/PointCloud2` | ROS depth processing → costmap, RViz | 10–15 Hz; best effort, volatile, depth 2 |
| `/gps/fix` | `sensor_msgs/msg/NavSatFix` | optional Unity GNSS → geographic localization | 5 Hz; best effort, volatile, depth 5 |
| `/tf` | `tf2_msgs/msg/TFMessage` | ROS TF authorities → all TF consumers | dynamic updates; reliable, volatile |
| `/tf_static` | `tf2_msgs/msg/TFMessage` | robot_state_publisher → all TF consumers | on setup; reliable, transient local |
| `/sim/ground_truth/odom` | `nav_msgs/msg/Odometry` | Unity → evaluator | 50 Hz; excluded from realistic autonomy |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | ROS health adapter → terminal/RViz tools | 1 Hz; reliable, volatile |

These are requested DDS policies, not capabilities verified in the candidate bridge. Audit both endpoint publisher and subscriber implementations. Prove QoS compatibility with `ros2 topic info -v`, late subscribers and sensor loss. Configure RViz displays for matching sensor QoS. Keep `/tf_static` native to ROS so late-joining RViz receives fixed transforms.

Explicitly use unstamped Twist initially across the Jazzy command chain, with each relevant `enable_stamped_cmd_vel` setting recorded; verify support on the installed versions. Do not allow Twist and TwistStamped to share a topic. If the existing robot stack uses stamped commands, adopt that consistently or use one named adapter. [Jazzy odometry/command guidance](https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/odom/setup_odom_gz/).

## TF tree

```text
map
└── odom                         localization authority, exactly one
    └── base_footprint           local odometry authority, exactly one
        └── base_link            dynamic body projection, Unity -> bridge TF
            ├── wheel_left      robot_state_publisher + joint_states
            ├── wheel_right
            ├── left_caster_suspension_link  prismatic, robot_state_publisher
            │   └── left_caster             existing swivel joint
            ├── right_caster_suspension_link prismatic, robot_state_publisher
            │   └── right_caster            existing swivel joint
            ├── lidar_link
            ├── imu_link
            ├── gps_link        optional
            └── camera_link
                ├── camera_color_optical_frame
                └── camera_depth_optical_frame
```

Canonical ROS base convention: X forward, Y left, Z up; SI units and radians. Unity position conversion candidate: `(x,y,z)_Unity = (-y,z,x)_ROS`. Rotations, angular velocities and inertia require a consistent handedness-aware transformation; never treat quaternions as interchangeable component arrays. Test positive forward motion, positive yaw, basis axes and a known rotated pose.

Camera optical frames use Z forward, X right, Y down. Include fixed optical transforms in the description. Validate image row order and depth projection with an asymmetric calibration fixture. Export linear optical Z depth, not raw nonlinear graphics depth or ray distance. Define invalid depth as NaN for 32FC1, enforce valid ranges, and pair intrinsics with the actual render dimensions. Mark whether depth is native or registered to color; do not claim registration just because resolutions match.

R3-a now publishes `/sim/body_transform` (`geometry_msgs/TransformStamped`, 50 Hz) with simulation acquisition stamps for `base_footprint → base_link`. Unity derives it from the rendered body pose relative to the planar footprint; the bridge validates and broadcasts it as the sole TF authority for that edge. There is no static body-offset publication in R3-a mode. Normal courses retain the same flat pose; the separate [terrain bench](TERRAIN_BODY.md) adds experimental support height and attitude. `base_footprint` stays on the world Z=0 datum, not the raised surface, in this ideal projection convention. Robot-state-publisher attaches sensor frames to the dynamic body. This is not physical contact or estimated terrain odometry.

The R3-a simulation launch inserts two prismatic joints into its in-memory description: `left_caster_suspension_joint` and `right_caster_suspension_joint`, each along body +Z before the existing caster swivel. The canonical CAD URDF is unchanged. `/joint_states` now contains seven joints, including the camera pitch joint; normal flat players report zero slider displacement. In the suspension bench, `/sim/suspension_state` (`sensor_msgs/JointState`, 50 Hz, reliable/volatile, publisher queue 10) reports `rear_body_height`, `left_compression`, `right_compression` in metres and rates in m/s at the same stamp as odometry/body/joints. It is a diagnostic channel; only the two named slider joints in `/joint_states` feed robot-state-publisher. Their displacement is vertical compression divided by body-up's world vertical component. See [model and calibration limits](CASTER_SUSPENSION.md).

The existing `leftCaster` and `rightCaster` continuous joints now publish motion-aligned yaw angles and angular velocities, rather than constant zero. Angles are unwrapped radians about local ROS +Z (Unity -Y); robot-state-publisher owns their TF edges. `config/caster_swivel.json` supplies provisional response settings. Pause freezes state; reset initializes yaw to zero; zero pivot velocity holds yaw with zero angular velocity. Nominal rear pivot velocity comes from accepted axle twist and is projected into the tilted body's plane. This does not steer the terrain support samples or model physical caster contact. See [swivel evidence](CASTER_SWIVEL.md).

In realistic local mode, the estimator publishes `odom → base_footprint`; raw wheel odometry does not also publish it. AMCL publishes `map → odom` only in mapped-lab mode. Geographic/global estimation owns that edge in GNSS mode. Ideal mode uses a dedicated ground-truth adapter and disables competing authorities. `robot_state_publisher` owns robot joint and fixed sensor transforms. Use startup assertions to catch conflicting publishers.

## Clock, control and reset

Observed surface projection adds `/perception/depth/surfaces` (`sensor_msgs/PointCloud2`, odom, nominal5Hz): FLOAT32 x/y/z/ground at offsets0/4/8/12, point_step16; ground is0or1. It includes all valid stride-four depth returns for occlusion, with connected shallow-ground eligibility. Its acquisition stamp exactly matches `/perception/depth/status`; RGB uses a jointly available preceding pair within .35simulation seconds and .5wallseconds, plus exact RGB acquisition TF. No course geometry is published here. Invalid ground status prevents reuse. Ramp variants now publish raised dynamicbodyTF too. See [implementation and limits](RAMP_EDGE_PERCEPTION.md).

Unity is the only live simulation clock authority. All ROS algorithms and RViz use `use_sim_time:=true`; all sensor stamps are acquisition time in that clock. Publish clock from fixed simulation steps; rendering cadence must not change simulated duration. Pause freezes clock and motion. Use monotonic wall time for connection watchdogs so a paused/stalled simulator cannot preserve an old drive command.

Plan one arbiter with explicit manual/autonomous modes. A simulated E-stop overrides both, latches until cleared and forces zero command. Unity independently clamps speed/acceleration and expires commands after a proposed 0.5 seconds of no fresh reception. Reconnect never replays buffered velocity commands; require fresh commands after reconnect/unpause. Monitor command age during image stress tests.

Proposed ROS controls: `/sim/pause` (`std_srvs/srv/SetBool`), `/sim/reset` (`std_srvs/srv/Trigger`), `/sim/estop` (`std_srvs/srv/SetBool`, explicit clear). Responses acknowledge applied state, not just message receipt. A ROS-side session supervisor coordinates reset: stop commands, deactivate navigation, reset Unity and estimator state, clear TF/costmap history as needed, increment run ID and reactivate after fresh data. Prefer restarting time-sensitive nodes when rewinding clock. Do not advertise reset as complete until the whole session is consistent.

Replay mode stops live simulation publishers. `ros2 bag play --clock` then owns clock; do not simultaneously republish a recorded `/clock` stream as another authority. Record wheel/IMU inputs, sensor data, TF, commands and parameter/run metadata so estimation and autonomy can be rerun.
