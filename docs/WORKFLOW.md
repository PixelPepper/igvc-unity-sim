# Workspace and operating workflow

This is the intended full-simulator layout and command experience. The transport probe, ROS package, Unity project and terminal wrapper now exist; use [RUNBOOK.md](RUNBOOK.md) for runnable commands. Package commands below remain future acceptance examples unless listed in that runbook. Delegation follows [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md).

## Repository layout to create during implementation

```text
IGVC SIM/
  README.md
  docs/                         plan, contracts, baseline, decisions, runbook
  unity/IGVCSim/
    Assets/IGVC/
      Runtime/                  Robot, Sensors, Transport, Scenarios, Diagnostics
      Editor/                   repeatable import/build tools
      Scenes/                   TransportProbe, TestPad, IGVCCourse
      Prefabs/                  robot and reusable course objects
      Tests/                    meaningful frame, timing and integration tests
    Packages/                   manifest and package lock
    ProjectSettings/            pinned editor and settings
  ros2/src/
    igvc_description/           canonical Xacro, meshes, physical dimensions
    igvc_sim_bridge/            bridge config/adapters and simulator services
    igvc_localization/          odometry and estimator configuration
    igvc_perception/            camera/depth processing and lane boundaries
    igvc_navigation/            Nav2 parameters, behaviors and mission entrypoint
    igvc_bringup/               launch profiles and RViz configuration
    igvc_evaluation/            scoring, metrics and scenario assertions
  config/                       scenario/sensor profiles and version manifest
  tools/                        setup, doctor, launch, import, build, check scripts
  tests/scenarios/               seeds, expected outcomes and tolerances
  assets/source/                source manifest; large originals remain external
  artifacts/                    ignored local player builds, bags and reports
```

Create packages when their milestone needs them, not as empty scaffolding that implies working software. Separate Unity assemblies for transport, robot physics, sensors, scenarios and editor tooling as dependencies emerge. No Unity runtime dependency on Editor assemblies. ROS launch/config owns autonomy parameters; Unity configuration owns world/physics parameters; the canonical robot description owns mounting geometry.

## Cross-platform source and build policy

Keep this Windows Git checkout as the initial source authority and Unity workspace. ROS reads `ros2/src` through its quoted `/mnt/c/.../IGVC SIM/...` path, but builds into WSL ext4 directories, e.g. `~/igvc_ws/{build,install,log}`. Quote paths containing spaces. Avoid `--symlink-install` until Windows-mounted source behavior is validated. A source-sync helper can stage ROS sources on ext4 if measured build issues justify it; staging must be one-way with a recorded source hash, never two independently edited authorities.

Run colcon with explicit build, install and log locations. Do not accidentally source the old `robotlab_spike_v1` overlay. The doctor script should report the sourced ROS distro, overlay path, selected domain ID and package origins.

Track source code, Unity `.meta` files, scenes, prefabs, project settings, package locks, ROS package files, configs and lightweight test fixtures. Exclude Unity caches, colcon outputs, bags and player builds. Before checking in large derived meshes, decide Git LFS or an artifact store and record checksums; do not blindly import the CAD tree into Git. Preserve originals and record source-to-derived geometry provenance.

Pin exact bridge commits and Unity packages after Phase 1; record installed ROS Debian versions, RMW, Unity editor and OS versions in each run manifest. Use a dedicated ROS domain chosen after checking the existing environment. Runtime ROS bridging and optional Unity Editor MCP are separate connections; MCP is not required to run a built simulator.

## Daily development loop

1. Select one milestone issue with a concrete expected behavior and pass/fail evidence.
2. Make changes on a `codex/` branch when implementation begins; keep CAD import, transport and navigation changes reviewable separately.
3. Run the smallest relevant check: frame/math tests, transport probe, robot motion fixture, sensor fixture, or seeded navigation mission.
4. Record exact versions, scenario seed, profile, command, outcome and relevant log/bag path. Update the decision record when architecture changes.
5. Integrate after the milestone gate passes. Avoid package upgrades while debugging an unrelated subsystem.

## Terminal experience to implement

PowerShell wrapper should manage the Windows player and explicitly invoke WSL for ROS processes. Linux wrapper should work independently for ROS on a native/separate Ubuntu machine. Use a session ID, process ownership and idempotent cleanup. A stop command must stop only processes belonging to that session.

Proposed interface:

```powershell
# Future commands: scripts do not exist yet.
./tools/igvc.ps1 doctor
./tools/igvc.ps1 build
./tools/igvc.ps1 start --scenario test_pad --mode manual --rviz
./tools/igvc.ps1 status
./tools/igvc.ps1 stop
```

Future WSL commands after implementation and setup:

```bash
source /opt/ros/jazzy/setup.bash
source ~/igvc_ws/install/setup.bash
ros2 launch igvc_bringup sim.launch.py scenario:=test_pad mode:=manual use_sim_time:=true
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel/teleop
ros2 topic list
ros2 topic info /scan -v
ros2 topic hz /scan
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 service call /sim/pause std_srvs/srv/SetBool '{data: true}'
ros2 service call /sim/reset std_srvs/srv/Trigger '{}'
```

The ROS launch entrypoint starts the bridge, robot_state_publisher, selected estimator, optional perception/Nav2 and RViz. It checks clock, sensors and TF readiness before activating Nav2; arbitrary sleep delays are not readiness checks. The outer wrapper launches the player first or connects to an already-running Editor instance, with errors identifying which side is missing.

For navigation mode, a terminal goal uses the standard action interface; the goal below is valid only once the configured `map` frame exists and the coordinates are free space:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  '{pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}' --feedback
```

Provide a wrapper command to cancel the active goal, switch control mode, record a session, and run a scenario suite. Keep action logic native to ROS. Recording profiles should separate a small health bag from a full perception bag and estimate disk usage before long sessions.

## RViz and test evidence

Save an RViz configuration with RobotModel, TF, LaserScan, RGB image, depth image, PointCloud2, Odometry, Path, footprint and local/global costmaps. Use `odom` fixed frame for early motion tests, `map` when localization is active. Color ground-truth displays distinctly and disable them in the normal autonomy layout.

Each milestone report records pass/fail and evidence, including packet age/rates and TF connectivity; an attractive screenshot alone is insufficient. Final qualification includes command disconnect, dropped sensor stream, blocked goal, simulation pause, reset, bag replay and ten-minute sensor-load runs. Unknown or unrun checks must stay marked unverified.

The [SoonerRobotics autonomy review](SOONER_AUTONOMY_REVIEW.md) adds an offline perception loop: select a recorded OAK/simulated sensor bag, load the captured calibration and parameter snapshot, run the same perception nodes used live, and inspect raw images, masks, projected boundaries and navigation costs. Add replay as an input profile, never a second concurrent live source. Save stage timings, acquisition age and lane-detection metrics alongside scenario results. Start with an OpenCV baseline before deciding whether a more complex model is needed.
