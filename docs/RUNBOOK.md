# Transport probe runbook

Docker `course` now runs experimental [sensor-led navigation](SENSOR_AUTONOMY.md).
Use `guided-course` explicitly for the older generated-route regression described
in historical lap instructions. Sensor mode requires rebuilt Unity and Docker;
it refuses an older player that enforces hidden lane geometry.

For the [caster swivel test](CASTER_SWIVEL.md), use a fresh `drive-start -Visible` and run `wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/verify_caster_swivel.py` from the repository root. It commands bounded forward/reverse/pivot/arc phases and stops afterward. All R3-a players must be rebuilt for the new swivel scene references.

Run `terrain-turn-test` after a fresh `terrain-start -Visible` for the [bounded ramp pivot and arc experiment](CASTER_TURNING.md). It drives manually, checks measured motion, and stops afterward; it does not reset the robot or enable autonomy.

For the separate [caster suspension bench](CASTER_SUSPENSION.md), use `terrain-build`, `terrain-start -Visible`, then the bounded `verify_caster_suspension.py` manual traversal. Add `-RigidTerrain` when using the earlier `verify_terrain_body.py` instead. This is not an AutoNav course; `loop-run` rejects the bench profile. Use `stop` before returning to `variant-start`. Rebuild R3-a players after the suspension update: ROS now expects two additional caster-slider joint states. Restart older RViz instances to clear cached descriptions/TF.

The current course build includes [ideal metric depth](DEPTH_CAMERA.md). `nav-start` runs its point-cloud processor, and `rviz` shows RGB plus metric depth. See that guide for topic names, the bounded verifier and flat-terrain limitations.

For the actual CAD robot with ideal differential-drive motion, use [R3-a drive mode](R3A_DRIVE.md). `drive-build`/`drive-start` select that player; shared `rviz`, `test`, `status` and `stop` commands follow the active session. The commands below otherwise describe the original transport fixture.

Implemented fixture; first transport gate passed as of 2026-09-09. This document describes the current scripts. `WORKFLOW.md` and `ROS_INTERFACE.md` also contain future interfaces that this probe does not implement.

## Start and inspect

Run PowerShell from the repository root. Prerequisites are Unity 6000.3.23f1 with Windows build support, WSL distribution `Ubuntu-24.04`, ROS 2 Jazzy, colcon, RViz2 and the ROS message/TF dependencies in `ros2/src/igvc_sim_bridge/package.xml`. Keyboard teleop additionally needs `teleop_twist_keyboard`. The wrapper is not a dependency installer. Close this Unity project in the Editor before batch building.

On this host, Jazzy base was already installed. During implementation the additional packages were installed with `apt-get`: `ros-jazzy-rviz2`, `ros-jazzy-nav2-bringup`, `ros-jazzy-robot-localization`, `ros-jazzy-teleop-twist-keyboard`, `ros-jazzy-robot-state-publisher`, and `ros-jazzy-xacro`. Installing Nav2 does not mean the probe launches or validates navigation.

```powershell
Set-Location 'C:\Users\brand\Documents\ChatGPT\IGVC SIM'
./tools/igvc.ps1 build
./tools/igvc.ps1 doctor
./tools/igvc.ps1 start
./tools/igvc.ps1 status
```

`build` clones the pinned ROS-TCP-Endpoint into `artifacts/vendor`, builds ROS into WSL `~/igvc_ws/{build,install,log}`, runs `ProbeChecks.Run`, and creates `artifacts/build/IGVCProbe.exe`. It regenerates the probe scene through `ProbeBuild.CreateScene`; retain scene changes in that generator. `doctor` reports package origins, including `nav2_bringup`; a missing Nav2 package can fail that check even though this fixture does not run Nav2. A missing bridge overlay before the first build is expected.

`start` manages one ROS launch process group and starts the workspace player. It rejects an already-running workspace player. It does not wait for topic readiness; `status` lists processes/topics, and live checks establish data readiness. Stop other manually started probe players/endpoints before starting a session.

Use `./tools/igvc.ps1 start -Visible` when you want the Unity window shown. Background testing uses the default hidden launch. Camera rendering remains enabled in both modes.

In separate PowerShell terminals:

```powershell
./tools/igvc.ps1 rviz
./tools/igvc.ps1 test -Duration 600
```

RViz runs in the foreground via WSLg using `odom` as its fixed frame. The verifier drives and resets the body and exercises pause/E-stop; do not drive concurrently. `Duration` is the sustained-load interval after behavior checks, so total runtime is longer. A requested 600 seconds is not proof that the full interval completed.

## WSL terminal control

Open Ubuntu with `wsl -d Ubuntu-24.04`, then run:

```bash
cd '/mnt/c/Users/brand/Documents/ChatGPT/IGVC SIM'
source tools/ros_env.sh
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -r cmd_vel:=/cmd_vel/teleop -p repeat_rate:=20.0 -p key_timeout:=0.2
```

Source that environment in each additional WSL terminal. It selects Jazzy, domain 42 (override with `IGVC_ROS_DOMAIN_ID` before sourcing), localhost DDS discovery, Fast DDS, and the `~/igvc_ws/install` overlay. Avoid sourcing unrelated robot overlays. DDS stays inside WSL; Unity connects by TCP to `127.0.0.1:10000` by default.

It also loads `ros2/config/fastdds.xml`, with an 8 MiB shared-memory segment for image payloads. Source the same environment for every ROS participant; restart existing participants after changing that profile. The 900 KiB RGB frames suffered substantial best-effort loss with the smaller default buffer on this host.

```bash
ros2 topic list --no-daemon
ros2 topic info /scan -v
ros2 topic hz /scan
ros2 topic hz /camera/color/image_raw
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 service call /sim/pause std_srvs/srv/SetBool '{data: true}'
ros2 service call /sim/pause std_srvs/srv/SetBool '{data: false}'
ros2 service call /sim/estop std_srvs/srv/SetBool '{data: true}'
ros2 service call /sim/estop std_srvs/srv/SetBool '{data: false}'
ros2 service call /sim/reset std_srvs/srv/Trigger '{}'
```

Pause freezes simulation time and motion; clock messages may continue with the same timestamp. Unpause and clearing E-stop require a fresh command. Reset returns the pose to the origin, increments the run ID and preserves the E-stop latch; it keeps time monotonic. This is a probe pose reset, not an estimator/Nav2 session reset.

`/cmd_vel/teleop` accepts unstamped `Twist`; the adapter publishes `/cmd_vel` for inspection and `/sim/drive_command` as a simulation-stamped `TwistStamped` transport command. Unity consumes the latter, so publishing directly to `/cmd_vel` does not drive this probe. The adapter expires teleop after 0.3 seconds and stale clock reception after 0.5 seconds of wall time. Unity additionally checks transport stamp age and a 0.5-second reception watchdog. Limits are 1 m/s and 1 rad/s, with ideal acceleration limits of 2 m/s² and 3 rad/s².

To launch the ROS side manually instead of the managed session:

```bash
bash tools/run_ros.sh ros2 launch igvc_sim_bridge probe.launch.py rviz:=true
```

Launch the Windows player separately in this mode; do not also use wrapper `start`. For non-default networking the player accepts `--ros-ip` and `--ros-port`, and ROS launch accepts `port:=10000`; the wrapper does not expose these overrides. Addressing outside the default local WSL setup remains unverified.

## Stop and evidence

```powershell
./tools/igvc.ps1 stop
Get-Content ./artifacts/checks/unity-checks.json
Get-Content ./artifacts/checks/live-probe.json
Get-Content ./artifacts/logs/ros-session.log -Tail 40
Get-Content ./artifacts/logs/player.log -Tail 40
```

`stop` stops players matching this workspace executable path and the recorded ROS launch group. Separately launched RViz/teleop processes should be closed with Ctrl+C in their terminals. Build logs are `artifacts/logs/ProbeChecks.Run.log` and `ProbeBuild.Build.log`. Reports/logs are local ignored artifacts and can be overwritten by later runs; retain copies with source/version details for milestone evidence.

The final reports record 12 Unity checks, all 15 live checks over the 600-second load interval, and all 8 reconnect checks passing. Measured RGB 13.34 Hz, lidar 5.26 Hz, odometry 50.00 Hz and real-time factor 0.999966. [Evidence](TRANSPORT_EVIDENCE.md) records the earlier failed baseline and the queue/DDS correction. RViz was captured displaying RGB, scan, TF and odometry with Global Status OK.

To repeat the disruptive reconnect check, run this from WSL with the managed probe session active and no verifier/teleop running:

```bash
bash tools/run_ros.sh python3 tools/verify_reconnect.py
```

It restarts the owned ROS launch group while leaving Unity alive, drives briefly, checks fresh returned feedback, then resets the pose. Results are written to `artifacts/checks/reconnect.json`.

RViz launched through WSLg and reported OpenGL 4.5 without an observed log error; this establishes startup, not correctness of every display. The actual ROS RGB snapshot `artifacts/checks/ros-rgb.png` was inspected as upright with the orange marker on the left. Calibration and TF alignment need separate checks. Inspect each completed report's `status`, individual `checks`, measured rates and real-time factor. Passing the verifier alone does not establish reconnect recovery, complete QoS suitability or command-latency percentiles.

## Optional bounded review delegation
For camera-only bench diagnosis, use `./tools/igvc.ps1 perception-start` after starting R3-a, then `perception-stop` before Nav2. These managed modes are mutually exclusive. The [moving terrain perception workflow](TERRAIN_PERCEPTION.md) includes read-only observation and exact-frame capture/replay commands, measured failures and interpretation limits.


Follow [the agent workflow](AGENT_WORKFLOW.md) and [runner documentation](../tools/agents/README.md). From the repository root, inspect the example review packet before submitting it:

```powershell
./tools/cursor-agent.ps1 doctor
./tools/cursor-agent.ps1 dry-run -Task ./tools/agents/review-motion.task.json
./tools/cursor-agent.ps1 review -Task ./tools/agents/review-motion.task.json
```

The dry run prepares the allowlisted text packet without a provider call; `review` submits one read-only review through the Cursor SDK. Authenticated discovery selected `grok-4.6`, low effort, non-fast. The first review completed with 12,597 reported tokens; its suggestions were checked against the control contract and no changes were warranted. Credentials stay outside the repository or in the calling process environment. Use `./tools/set-cursor-key.ps1` to replace the encrypted credential without echoing it. Review only named files, inspect returned usage, and do not automatically retry authentication, quota or model-access errors. Cancellation thresholds are not hard billing caps.

## Current limits

- One manually controlled ideal transform-driven placeholder body; no imported R3-a CAD, wheel contact physics, measured drivetrain, encoder odometry or competition course.
- Unity publishes a nominal 100 Hz clock, 50 Hz ideal odometry and synthetic joint feedback, RGB8 at 640×480 targeting 15 Hz, and a 360-beam ideal raycast scan targeting 5.5 Hz over 0.15–12 m. Scheduling/transport can lower observed rates. Camera readback allows one pending GPU request; a rendered graphics device is required.
- The ROS adapter owns ideal `/odom`, `odom → base_footprint` and provisional static body/sensor transforms. No robot_state_publisher or real robot description is running. Synthetic joint positions are zero; wheel velocities are transport payloads.
- No CameraInfo, depth, point cloud, IMU, GNSS, wheel estimator, Nav2, autonomous command arbitration, mapping, mission actions or bag/replay workflow yet. OAK-D Pro/RPLIDAR fidelity is not validated.
- The pinned endpoint uses reliable publishers rather than the future per-topic QoS contract. Fixture load, reconnect and basic RViz displays are verified; calibrated sensor geometry, full depth/point-cloud bandwidth and latency percentiles remain future work. The simulated E-stop is not a physical robot safety validation.
