# Docker validation — 2026-09-09

Status: Docker live integration passed on this host; clean-checkout validation and
upload remain in progress. Native-WSL course results are not Docker evidence.

## Environment and build

- Windows Unity 6000.3.23f1; WSL2 Ubuntu-24.04 with systemd.
- Installed Ubuntu-packaged Docker Engine 29.1.3 and Compose v2 in WSL.
- Image base is `ros:jazzy-ros-base-noble`, pinned by manifest digest in Dockerfile.
- First clean build exposed unresolved `ament_python` rosdep entries in existing
  manifests. Explicitly skip that build-type key: colcon Python support is installed.
- Windows `tools/docker.ps1 prepare-unity` passed the pinned reference import.
- Windows `tools/docker.ps1 unity-build` exited 0, producing IGVCCourse.exe.
  Log records 3 ground-render fixtures, 6 depth-render checks, 70 ramp checks and
  12 caster-swivel checks. The Unity log also has licensing token and D3D debug
  interface warnings; the player build completed despite those warnings.
- Shell and PowerShell wrapper syntax checks passed.

## Live container evidence

- Environment verifier: Ubuntu 24.04, Jazzy, all seven project/endpoint packages,
  RViz and Nav2; ten description mesh references resolve inside the image.
- Full seeded course: 82/82 ordered checkpoints, all 12 independent audit checks
  pass, no resets/gaps/line interventions, max 2.2 m/s. Sampled clearance 0.70125 m;
  conservative swept clearance 0.53411 m. Report: `docker-run.json` in seed-2027.
- Read-only transport verifier: all seven checks pass over 20 seconds. RGB12.59Hz,
  depth9.39Hz, lidar4.95Hz, odometry47.17Hz; 252 RGB/info and188 depth/info exact
  stamp pairs, no payload errors, and connected robot/sensor TF.
- Camera control verifier passed all 53 checks, including pitch/TF, pause and E-stop
  handling, and RGB CameraInfo. Default pitch restored afterward.
- Terminal control verifier: 0.255 m travel from a bounded0.3m/s command, command
  expiry stops, E-stop overrides fresh commands, clearing E-stop does not rearm.
- Container RViz opened through WSLg/OpenGL4.5 software rendering. Captured window
  shows Global Status OK, robot, TF, RGB, metric depth and rendered costmaps.
  A first-map GLSL sampler error remains observable; this matches the documented
  [upstream first-map warning](https://github.com/ros2/rviz/issues/463). It is not
  suppressed, and zero-warning graphics behavior is not claimed.

## Failed/inapplicable experiments retained

The old `verify_probe` calibration-wall assertion failed when run on the course
(no calibration wall). `verify_course` required finite lidar obstacles at the
clear spawn, outside sensor range. `verify_depth` assumes a flat fixture with
ground normal within0.5degrees; the terrain-body spawn did not meet that condition.
These reports are retained as failed fixture-specific checks, not presented as
passes. The new transport check validates real camera pairs, rates, payloads and
TF without assuming flat ground or obstacles at an arbitrary pose. It does not
establish geometric sensor calibration. The first control-test attempt used an
insufficient fixed discovery wait; it now waits for odometry with a30s deadline.

## Remaining gates

Restart; GitHub source upload and clean checkout.

Local detailed evidence is retained in ignored artifacts and build logs. This
document will record actual outcomes; startup or historical runs do not count.

## Reference documentation

- [Official ROS image](https://hub.docker.com/_/ros)
- [Docker Engine installation](https://docs.docker.com/engine/install/ubuntu/)

This delivery uses Ubuntu's `docker.io`/`docker-compose-v2` packages, as specified
in README, not Docker Desktop or Docker's separate CE package repository.
