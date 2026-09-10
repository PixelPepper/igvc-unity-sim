# R3-a ideal-motion milestone — 2026-09-09

Current frame update: `base_footprint → base_link` is now dynamic, published from Unity through `/sim/body_transform`; the ordinary flat course preserves its original offset. The separate [terrain support bench](TERRAIN_BODY.md) validates provisional height/attitude interpolation. Historical fixed-body-transform descriptions below are superseded. Rebuilt drive/course/terrain players are required with the updated bridge.

Latest addition: the supplied RPLIDAR model is seated in the front lid housing and `/scan` uses its canonical mounted frame. See [lidar placement and evidence](LIDAR_MOUNT.md). The latest 27-check result supersedes the earlier 26-check pre-mount result described below; RGB remains a provisional mount.

Camera update: RGB now originates on the [pole-top OAK-D Pro pitch mount](CAMERA_MOUNT.md), with terminal tilt and CameraInfo. Earlier fixed RGB fixture coordinates in this milestone history are superseded by `config/camera_mount.json`.

The actual five-link robot now drives from ROS terminal commands in a separate Unity test-pad build. This is `r3a_kinematic_oracle`: exact differential-drive motion with ground-truth odometry. It is a geometry/transport validation mode, with no tire contact, slip, suspension or collision response.

## Run

From PowerShell at the repository root, close the project in Unity Editor before building:

```powershell
.\tools\igvc.ps1 stop
.\tools\igvc.ps1 drive-build
.\tools\igvc.ps1 drive-start -Visible
```

In separate terminals:

```powershell
.\tools\igvc.ps1 rviz
.\tools\igvc.ps1 test -Duration 60
```

The verifier drives, pauses, stops and resets the robot; do not send manual commands concurrently. `status` and `stop` manage either the probe or R3-a session. A running session prevents starting a second simulator. `test` and `rviz` select the configuration from the managed session mode. Omit `-Visible` for background rendering/testing.

For manual driving, use a WSL terminal:

```bash
cd '/mnt/c/Users/brand/Documents/ChatGPT/IGVC SIM'
source tools/ros_env.sh
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel/teleop
```

Or send a bounded forward command stream, then let the watchdog stop it:

```bash
timeout 3 ros2 topic pub -r 20 /cmd_vel/teleop geometry_msgs/msg/Twist '{linear: {x: 0.3}, angular: {z: 0.0}}'
```

The existing `/sim/pause`, `/sim/estop` and `/sim/reset` services apply. Reset preserves the clock and stop latch; resuming requires a fresh command. See [the runbook](RUNBOOK.md) for service commands.

## Frames and ownership

Unity publishes axle-centered `odom -> base_footprint` ground truth and canonical joint names: `leftWheel`, `rightWheel`, `leftCaster`, `rightCaster`. The user confirmed big drive wheels at the front and casters at the rear. The normalized description rotates the exported coordinate bases 180 degrees about Z and swaps exported left/right names to match physical sides. Original source files and mesh coordinates remain unchanged; provenance records the mapping. The adapter publishes odometry and its TF; robot_state_publisher alone publishes the four joint transforms. There is no separate joint-state publisher in drive mode.

The adapter publishes fixed `base_footprint -> base_link` translation `(-0.25591, 0, 0.30385548)` metres. Thus the base lies behind the driven axle and orbits it during a pure yaw command. Unity uses the same rigid offset. Canonical wheel axes give positive left-wheel position and negative right-wheel position during forward motion. Caster angles remain zero in this ideal-motion stage. The base frame's red X axis and the odometry arrow now point toward the drive-wheel end; camera optical axes use their own convention.

CAD-derived wheel radius is 0.229569608 m and track is 0.81051 m; these are not physical calibration. Positive ROS X points toward the front drive wheels, as confirmed by the user. The known 16.85 mm caster contact mismatch remains unresolved. RGB remains a fixture at base-relative `(0.45,0,0.7)`. Lidar is now fitted to the front housing, with scan frame `(0.2700228,0,0.3396)` and optical height still provisional. These face physical forward. Depth, CameraInfo, point clouds, IMU and Nav2 are not part of this build.

## Geometry and evidence

The Unity drive build uses 149,986 visual triangles, reduced from 888,264 (83.1%). Maximum per-link AABB deviation is 1.703 mm. Finite geometry, nondegenerate triangles, normals and repeatable generation hashes passed. The original meshes remain unchanged and RViz still uses them. [Simplification procedure](../ros2/src/igvc_description/meshes/simplified/README.md) records pinned local dependencies and limitations. Bounds checks do not establish detailed surface accuracy or collision suitability.

After the physical-forward correction, the build passed 18 kinematics checks and 12 existing motion/watchdog checks. The running simulator passed all 26 ROS checks, including synchronized wheel travel, canonical wheel signs, base/wheel/caster TF, explicit drive-wheels-front/casters-rear placement, pure-yaw axle stability, stop/pause/reset behavior and stale-command rejection. Over the 60-second sustained-load interval: RGB 13.35 Hz, scan 5.27 Hz, odometry/joints 49.99 Hz and real-time factor 0.99999. This is a short acceptance run, not a long endurance result. The earlier reversed-forward baseline is retained as `live-r3a-before-forward-correction.json`; it is not the current result.

Evidence under `artifacts/checks`: `live-r3a.json`, `r3a-kinematics-checks.json`, `unity-checks.json`, `mesh-simplification.json`, `r3a-drive-rviz.png`, `r3a-rgb.png`, and `r3a-drive-editor.png`. The last image is an offscreen Unity Editor render of the saved drive scene, not a running-player screenshot. RViz and RGB captures came from the live session and were visually inspected. The reduced-mesh player log did not contain the earlier full-mesh upload-buffer sizing warning.

Build reproducibility also required forcing setuptools to refresh Python build/install modules: the host's Windows/WSL clock discrepancy otherwise retained an older adapter. This is implemented in the bridge's setup.py without modifying either host clock.

Next: add depth/CameraInfo and sensor-frame tests, then collision/drive fidelity and Nav2 integration in separately validated stages. This milestone does not close physical-geometry or competition-compliance gates.
