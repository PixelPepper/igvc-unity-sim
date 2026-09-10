# Initial nearby-goal navigation

`igvc_navigation` provides a provisional Nav2 Jazzy profile for the Unity kinematic course robot. It plans toward nearby goals using ideal `/odom`, lidar and camera-detected paint boundaries. RGB/CameraInfo are processed by `igvc_perception` and projected with acquisition-time TF; the custom `igvc_lane_layer` marks these observations separately from lidar. A separate Unity ground-truth guard prevents fixture line crossings. There is no sensor-driven localization, SLAM or static map; this remains initial course navigation, not completed AutoNav. The short GPS mission and the fresh 77-checkpoint full-course mission passed; see the separate evidence below.

## Nodes and command ownership

The integrated Windows wrapper is the normal entry point (PowerShell at the repository root):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\igvc.ps1 course-start -Visible
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\igvc.ps1 nav-start
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\igvc.ps1 nav-goal -X 2 -Y 0
```

Start the course only once; if it is already running, proceed to `nav-start`. Goals use absolute odom metres, with `-Yaw` in radians. The goal helper cancels previous goals, waits for Nav2, and enables the navigation command gate only for the accepted goal. It returns to manual mode on completion, error, or Ctrl+C. In another terminal, `nav-cancel` cancels a goal and selects manual mode; `nav-stop` also stops the managed Nav2 process group. `stop` shuts down the simulator, Nav2 and the ROS bridge. `rviz` automatically selects the navigation display configuration when a managed Nav2 session exists.

The bridge defaults to manual mode. Any finite teleop command, including zero, immediately latches navigation authority off. To resume a goal intentionally, submit it again with `nav-goal`. Navigation cannot automatically reclaim control when keyboard messages stop. Both inputs retain command limits and the 0.3-second wall-time expiry; stopped clocks also stop command forwarding. The Unity acceleration limits and simulated stop latch remain in force. Direct `ros2 action send_goal` commands below require explicit `/sim/set_autonomy` enable; prefer the wrapper, which manages that boundary.

Launch starts planner, controller, BT navigator, behavior server (Wait and bounded BackUp), their lifecycle manager and the lane detector. Do not start another lane detector manually. Nav2 uses simulation time; the lane detector's processing/staleness timers intentionally use wall time while image stamps and TF use simulation time. Unity must be unpaused with an advancing `/clock` before lifecycle startup. No additional ROS endpoint, robot state publisher, TF or simulator is created.

In the course profile, enabling autonomy requires fresh valid camera lane observations. If no valid lane update arrives for .75 wall seconds, the bridge stops forwarding and latches manual mode. A later valid image does not automatically resume the goal; explicitly submit/enable navigation again. See [lane detection](LANE_DETECTION.md) for topics, projection limits and reset handling.

The controller uses Navfn plus Regulated Pure Pursuit with a current forward cap of **2.2 m/s** and collision checking enabled. This leaves a small margin below the 5 mph (2.2352 m/s) maximum in section I.2, page 6 of the [2027 rules, version 7](https://www.gl-systems-technology.net/uploads/3/4/7/2/34727963/igvc_2027_rules_version_7_july_26.pdf). It is a speed ceiling, not an expected average or evidence of complete rule compliance. The earlier nearby-goal evidence below used the initial 0.25 m/s profile. Normal path following does not reverse; the full-course runner's bounded recovery is described in [full-course commands and limits](FULL_COURSE.md).

Ideal Unity motion ramps linear acceleration/deceleration at 2 m/s² and angular velocity at 3 rad/s², with angular magnitude capped at 1 rad/s. During nonzero-linear launch, the angular target scales with achieved linear speed before the angular ramp, preserving commanded curvature when that ramp can track it. Both the bridge and Unity proportionally saturate linear/angular commands to preserve curvature at their limits. Zero-linear commands still allow in-place rotation. The independent wall-time watchdog stops immediately. Reverse speed is capped at 0.3 m/s; command ownership controls when recovery is authorized. No separate velocity smoother is added.

The full-course runner uses a rolling three-pose `NavigateThroughPoses` horizon. It advances only when the physical audit visits the next checkpoint within 0.4 m; the custom BT uses a 0.35 m passed-goal radius. Horizon updates preempt the same action without an intermediate cancel or gate toggle. Painted/unmarked transitions still stop before changing gate mode. The old stop-at-each-goal runner remains unused.

The full-course runner publishes a speed cap based on distance to the last active horizon pose, normally rolling 4–6 m ahead, with final-arrival braking using `tools/approach_speed.py`: `sqrt((a*t)^2 + 2*a*max(distance-reserve,0)) - a*t`, with a=2 m/s², latency t=0.2 s and reserve=0.2 m. The cap is clamped to 0.05–2.2 m/s because Nav2 interprets a zero SpeedLimit as unlimited. Arrival handling must stop the robot; the positive floor itself is not a stop command.

Both potential velocity-producing servers explicitly set `enable_stamped_cmd_vel: false` and remap output to **`/cmd_vel/nav` (`geometry_msgs/msg/Twist`)**. This is an input to the integrator-owned arbiter, not direct transport control. Confirm the arbiter's navigation mode, teleop priority, timeout and stop behavior before sending a goal. Launching this package alone does not authorize bypassing the arbiter.

## Sensor costmaps and limits

Current inflation radius is **0.75 m**, reduced from 1.0 m, and cost scaling is **5.0**, increased from 3.0 for faster decay away from obstacles. These tune the surrounding cost field; the full axle-frame footprint and its 0.02 m padding remain unchanged. Smaller inflation is not a smaller robot or a physical clearance guarantee.

Both costmaps roll in `odom`: global40×40m at0.10m, local8×8m at0.05m. They contain lidar obstacles, the independent custom lane layer and inflation. New lane clouds replace active observations; the layer revisits old bounds so superseded marks disappear when the master costmap rebuilds. Clouds expire after .75 wall seconds. Lidar clearing cannot erase active lane observations. The detector separately retains an eight-second bounded history of paint points. Unknown cells remain unknown and the planner disallows unknown paths. Valid infinite laser readings clear to the 12 m sensor range; nearby finite readings mark obstacles. Prefer goals within 5 m and observed clear space. A 40 m window does not imply 40 m sensing.

Paint projection currently assumes ground Z=0. The imported road varies in elevation up to .195 m; one plane is provisional and errors grow with slope/range. White objects, faint paint and transverse lines remain perception limitations. The simulator guard is an independent constraint, not an autonomy input or evidence of camera-only boundary compliance.

The footprint is axle-frame rectangle X=[−1.1,+0.6], Y=[−0.5,+0.5], plus 0.02 m padding. Source CAD bounds X=[−0.485432,+0.673800], Y≈±0.477003 become canonical base X=[−0.673800,+0.485432] after the confirmed180° frame normalization; subtract 0.25591 m to express them about the driven axle. Conservative caster sweep expands rear extent to approximately−0.94222m, so the chosen rectangle covers these bounds. The robot's large driven wheels are FRONT; the original source orientation in `ROBOT_GEOMETRY_REVIEW.md` is historical. These margins and CAD dimensions are uncalibrated. Navfn is a 2D path planner; full-body collision checking by the controller can still reject a path in a narrow gap.

## Build and launch

Run alongside the already-started course and R3-a ROS session, using the same workspace environment/domain. From the repository in WSL:

```bash
source tools/ros_env.sh
source "$HOME/igvc_ws/install/setup.bash"
ros2 launch igvc_navigation local_navigation.launch.py
```

The normal workspace build must first include the new ament_cmake package. To override parameters: `params_file:=/absolute/path/local_navigation.yaml`; `autostart:=false` permits manual lifecycle operation. No map or initial-pose publication is required. In RViz use fixed frame `odom`, add `/global_costmap/costmap`, `/local_costmap/costmap` and `/plan`.

Before a first goal, inspect `/odom`, confirm the robot is stationary and the chosen goal lies in observed free space. Example **only when odom (1,0) is verified clear**:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  '{pose: {header: {frame_id: odom}, pose: {position: {x: 1.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}' --feedback
```

Coordinates are absolute `odom` positions, not displacements from the current robot pose. For another orientation use quaternion z=sin(yaw/2), w=cos(yaw/2).

Cancel all NavigateToPose goals explicitly; interrupting the CLI is not a reliable cancellation mechanism:

```bash
ros2 service call /navigate_to_pose/_action/cancel_goal action_msgs/srv/CancelGoal \
  '{goal_info: {goal_id: {uuid: [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]}, stamp: {sec: 0, nanosec: 0}}}'
```

Verify zero navigation commands and stopped odometry; use existing `/sim/estop` if an immediate simulated stop is needed. Before reset or changing scenes: cancel navigation, disable arbiter navigation authority, then reset/restart. Reset jumps ideal odometry and invalidates the costmap history; restart this navigation launch after reset. Stop navigation with Ctrl+C in its launch terminal; the bridge watchdog remains responsible for stale command expiry.

## Validation status and sources

The fresh rolling-navigation run **completed 77/77 physical checkpoints** with a valid continuous audit and no timestamp gaps. It traveled 153.333311 m against a planned 152.130591 m route, reached 99.7987% route arc, and finished 0.293905 m from the start. The sampled trajectory spans 81.12 simulation seconds. There were zero recoveries, backups and Unity line-guard blocks; declared zone transitions still stopped by design.

The sampled clearance audit passed with minimum barrel clearance 0.212114 m and no sampled intersections. Maximum observed speed was 2.2 m/s; 53 opening-straight intervals at X=3–16 m had median 2.2 m/s and minimum 2.1999998 m/s. See the [live run](../artifacts/checks/full-course-live.json), [clearance audit](../artifacts/checks/full-course-clearance.json), [trajectory](../artifacts/checks/full-course-trajectory.png), and [full-course guide](FULL_COURSE.md). These are ideal kinematic and sampled geometric results, not contact-physics validation. The associated build passed 28 Unity checks and built all seven ROS packages. Earlier archived incomplete attempts and the historical results below remain separate evidence.

Live integration passed on 2026-09-09. All four managed servers activated alongside the course; terminal goals at (2,0) and (1,0) succeeded. Six command-boundary checks passed: manual rejection of navigation, fresh-command enable, enabled forwarding, teleop-zero takeover, no automatic resumption, and stale-command stopping.

Subsequent stationary lane validation passed at 4.80 Hz with 727 odom points and 455/455 corresponding global costmap cells marked lethal; the saved debug mask showed two paint boundaries (`lanes-live.json/png`). The independent Unity guard stopped a lateral crossing attempt near odom (-.0873,1.931) m without crossing, and reverse-away motion worked. These checks validate marking and fixture enforcement separately; the earlier nearby-goal runs predate the new lane constraints and do not establish lane-constrained mission completion.

The first test aimed directly behind the nearest barrel into lidar-occluded unknown space and correctly failed planning; its diagnostic report remains `artifacts/checks/navigation-live-first-attempt.json`. A single lateral alternative at odom (-1.35,5.8) was visible to lidar but a straight route would intersect the conservative robot footprint with the barrel. Nav2 planned a 6.567 m detour and completed it with 0.192 m position error. Minimum measured rectangle-to-barrel clearance along sampled odometry was 0.652 m, using a scan-derived barrel radius of 0.268 m. This is ideal geometric evidence, not a physical contact test or a full-course benchmark.

Cancellation plus disabling autonomy stopped the robot within the 600 ms check, with 0.039 m of measured coasting. Cleanup canceled goals, disabled autonomy and reset the robot to (0,0), then cleared both costmaps. Evidence is `artifacts/checks/navigation-live.json`; verifier source is `tools/verify_navigation.py`. The verifier moves the simulator and must not run concurrently with user goals or teleop. Its `--adaptive` mode uses the preserved first-attempt report for this exact course fixture; it is not a general benchmark.

The Unity build compiled successfully. Follow mode, whole-course shortcut and scroll zoom were exercised in the visible player; right-mouse orbit and middle-mouse pan are implemented in `SpectatorCamera.cs`. `artifacts/checks/spectator-live.jpg` records the player view. RViz rendered the robot, sensor imagery and lidar costmaps with Global Status OK (`nav-rviz.png` and `nav-detour-rviz.png`). RViz logged an initial indexed-image GLSL sampler link message, but subsequent costmap rendering was visibly verified.

Prepared against installed `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml`, `navigation_launch.py`, installed plugin descriptors and default BT XML. YAML/XML/Python syntax, frame/topic policies, installed planner/controller plugin identifiers, and launch-description construction were checked before the live validation above.

Official references: [Jazzy controller server](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/controller_server/), [Regulated Pure Pursuit](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/configuring_regulated_pp/), [obstacle layer](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/costmap_2d/costmap_plugins/obstacle/). Jazzy uses unstamped Twist by default; the profile makes that explicit.

Historical short lane-constrained mission: the default synthetic GPS 2/4/6 m sequence completed successfully with final position (5.805800, approximately 0) m, .1942 m goal error and zero guard interventions. See `gps-live.json` and GPS_WAYPOINTS.md. Suspending the owned lane detector for 1.5 seconds latched the gate to manual; recovery did not rearm it (`lane-watchdog-live.json`). Earlier adaptive detour evidence above predates lanes; do not rerun that lane-crossing fixture as a current acceptance test. That short-test cleanup restarted Nav2 after resetting the robot to origin; it does not describe the fresh rolling-horizon validation session.
