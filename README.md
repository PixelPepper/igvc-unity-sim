# IGVC Unity Simulation

A Windows Unity simulator with ROS 2 Jazzy, Nav2, camera perception, synthetic GPS, and RViz in an Ubuntu 24.04 Docker container. The target is **IGVC 2027 AutoNav**. Unity renders RGB and ideal depth and simulates lidar, robot motion, and a seeded obstacle course.

The Docker-backed seed-2027 run completed **82/82 checkpoints**, including the ramp and return to start, and passed all 12 course-audit checks. Container sensor/TF, camera control, terminal motion/timeout/E-stop checks and RViz rendering passed on the development host. Clean-checkout validation is pending. See the [delivery plan](docs/DOCKER_PLAN.md) and [validation record](docs/DOCKER_VALIDATION.md). Earlier native-WSL results are retained separately in [history](docs/HISTORY.md).

## Prerequisites

- Windows with WSL2, the `Ubuntu-24.04` distribution, and WSLg for RViz.
- Unity Hub and **Unity 6000.3.23f1**, with Windows build support and an activated Unity license. Use the same editor version as this project.
- Git for Windows to clone this repository.
- Internet access to download container packages, ROS dependencies, and the pinned external course assets.

No native ROS installation is needed on Windows or in the WSL host. ROS runs inside Docker. This wrapper uses **Docker Engine in WSL Ubuntu**, rather than requiring Docker Desktop.

From an administrator PowerShell terminal, install WSL if needed:

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
```

Finish Ubuntu's first-run account setup. In Ubuntu, ensure `/etc/wsl.conf` contains the following, preserving any existing sections:

```ini
[boot]
systemd=true
```

After changing this setting, run `wsl --shutdown` in PowerShell, then reopen Ubuntu. Install Docker and the asset preparation dependencies from PowerShell:

```powershell
wsl -d Ubuntu-24.04 -u root -- apt-get update
wsl -d Ubuntu-24.04 -u root -- apt-get install -y docker.io docker-compose-v2 git python3
wsl -d Ubuntu-24.04 -u root -- systemctl enable --now docker
wsl -d Ubuntu-24.04 -u root -- docker version
wsl -d Ubuntu-24.04 -u root -- docker compose version
```

The wrapper invokes Docker as root in this WSL distribution. Confirm both version commands succeed before building.

## Download and build

The repository is private; sign into GitHub with an account that has access. Source upload is in progress.

```powershell
git clone https://github.com/PixelPepper/igvc-unity-sim.git
cd igvc-unity-sim
./tools/docker.ps1 prepare-unity
./tools/docker.ps1 build
./tools/docker.ps1 unity-build
```

Run these and subsequent commands from the repository root in PowerShell. Close this project in the Unity Editor before `unity-build`. If Unity is installed elsewhere, pass `-Unity 'C:\path\to\Unity.exe'` to `unity-build`. The resulting Windows player is `artifacts/build-course/IGVCCourse.exe`; its build log is `artifacts/logs/docker-unity-build.log`.

`prepare-unity` runs [docker/prepare-unity.sh](docker/prepare-unity.sh). It downloads SoonerRobotics' reference simulator at commit `0298b11c4f469404d08b37ad98431cdab6e02818` and imports the needed environment assets locally. These external assets are **not redistributed in this repository**. Their reuse terms remain unresolved; review upstream terms before redistribution. An existing checkout at another revision is rejected.

The repository retains the robot description, source meshes, configuration, and Unity source assets needed for the simulator. Original SolidWorks inputs remain external and unchanged. Generated Unity/ROS output, downloaded course assets, and local reports stay under ignored paths.

## Start, inspect, and drive the course

Stop any existing native ROS simulator session first so TCP port 10000 is available. The Windows player connects to the container through `127.0.0.1:10000`; ROS discovery remains inside the container.

```powershell
./tools/docker.ps1 start -Seed 2027 -Difficulty normal
./tools/docker.ps1 status
./tools/docker.ps1 rviz
```

`start` launches the ROS container and a visible Windows Unity player with a generated course. Startup alone does not verify that sensors or navigation are ready. RViz uses the tested WSLg/software-rendering path. A first-map GLSL warning was observed, but robot, RGB, depth and costmaps rendered; see the validation record. Keep RViz in its terminal and use another PowerShell terminal for commands:

```powershell
./tools/docker.ps1 run ros2 topic list --no-daemon
./tools/docker.ps1 run ros2 topic echo /clock --once
./tools/docker.ps1 run python3 docker/verify_environment.py
./tools/docker.ps1 run python3 docker/verify_integration.py
./tools/docker.ps1 course -Seed 2027
./tools/docker.ps1 audit -Seed 2027
./tools/docker.ps1 stop
```

`course` requests autonomous motion and writes `artifacts/courses/seed-2027/docker-run.json`. `audit` evaluates that run against its course. Inspect the reports before claiming success. Use the same seed for `start`, `course`, and `audit`; difficulties are `easy`, `normal`, and `hard`. `stop` stops the owned Unity player and removes the running Compose services. Restart with `start`.

For an interactive ROS terminal:

```powershell
./tools/docker.ps1 shell
```

The `run` action executes a command in the running ROS container with its workspace environment loaded. Rebuild the image after changing ROS code or container configuration, and rebuild Unity after changing player code or assets.

If PowerShell blocks a local script, invoke it for that command with
`powershell -NoProfile -ExecutionPolicy Bypass -File ./tools/docker.ps1 status`
(replace `status` with the desired action). This does not change the saved policy.

## Model limits and project references

The driven wheels are at the **front**, the casters at the rear, and canonical ROS +X points toward the driven wheels. The front roof carries the lidar; the rear pole carries the camera with a pitch-only mount. Keep the canonical description and mount configuration when adapting the project.

Motion, sensors, terrain support, and synthetic GPS are approximate models. This is not a calibrated R3-a robot, complete autonomy, hardware-grade localization, or proof of 2027 rule compliance. Container packaging does not change those limits.

- [Docker delivery plan](docs/DOCKER_PLAN.md) and [validation record](docs/DOCKER_VALIDATION.md): implementation gates and current evidence.
- [Historical native-WSL overview](docs/HISTORY.md) and [native-WSL runbook](docs/RUNBOOK.md): earlier workflow and results.
- [Project plan](docs/PLAN.md), [ROS interfaces](docs/ROS_INTERFACE.md), and [Unity context](docs/AI/UnityProjectContext.md): architecture and remaining work.
- [Robot orientation and drive](docs/R3A_DRIVE.md), [camera mount](docs/CAMERA_MOUNT.md), and [lidar mount](docs/LIDAR_MOUNT.md): physical conventions.
- [Ramp-edge perception](docs/RAMP_EDGE_PERCEPTION.md) and [procedural courses](docs/PROCEDURAL_COURSES.md): implementation details and prior experiment evidence.
