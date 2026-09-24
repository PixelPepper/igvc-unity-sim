# IGVC Unity Simulation

A Unity simulator with Windows and Linux launchers, ROS 2 Jazzy, Nav2, camera perception, synthetic GPS, and RViz in an Ubuntu 24.04 Docker container. The target is **IGVC 2027 AutoNav**. Unity runs on the host, rendering RGB and ideal depth and simulating lidar, robot motion, and a seeded obstacle course.

**New to the project? Start with the [Master Project Guide](docs/PROJECT_GUIDE.md)**
for architecture, startup workflows, parameter editing, rebuild steps and troubleshooting.
Use its [linked file index](docs/FILE_INDEX.md),
[ROS/navigation parameter reference](docs/guide/ROS_PARAMETERS.md) and
[Unity/course editing guide](docs/guide/UNITY_AND_COURSE.md) to find the source for a change.

**Navigation update:** `course` selects local goals from observed camera/depth/lidar
costs using six broad GPS destinations. This experimental mode has no generated
route input. `guided-course` retains the earlier route-informed regression.
The successful lap results below describe that guided mode, not proven sensor-led
autonomy. See [sensor navigation plan and validation](docs/SENSOR_AUTONOMY.md).
For the actual reuse boundary and algorithm differences, see the
[SoonerRobotics comparison](docs/SOONER_COMPARISON.md).

The current 0.30 m costmap inflation profile requires the pinned Nav2 MPPI
footprint-check fix. Docker builds and tests it automatically. For native WSL
Jazzy, run `wsl -d Ubuntu-24.04 -- bash tools/build_native_nav2.sh` once after
initializing rosdep. This builds a separate overlay in `~/igvc_nav2_overlay`,
runs the C++ regression, and enables it through `tools/ros_env.sh` only after
tests pass. Navigation refuses an unpatched installation.
See [native WSL AutoNav commands](docs/NATIVE_AUTONAV.md).

Current generated layout follows the supplied course reference: alternating
barrel passages, random colored barrels in driving sectors, and separate line
gaps around a marked ramp opposite the start. Seed 2027 uses six broad sensor-led
destinations; the separate guided regression has 30 checkpoints.
See [reference layout and validation](docs/REFERENCE_COURSE.md).
Normal difficulty now has 24 colored barrels across the two open ramp approaches,
six in each approach/lateral-side zone, with white markings retained on the ramp itself.
The 82-checkpoint results below refer to the earlier layout.

Use [Linux setup](#linux-setup-ubuntu-2404-x86_64) below or [Windows setup](#windows-prerequisites). Both Windows and Linux players completed the 82-checkpoint course. Linux runtime testing used Ubuntu under WSL2/WSLg, not a second native Linux desktop; see [Linux validation](docs/LINUX_VALIDATION.md).

The Docker-backed seed-2027 run completed **82/82 checkpoints**, including the ramp and return to start, and passed all 12 course-audit checks. Container sensor/TF, camera control, terminal motion/timeout/E-stop checks and RViz rendering passed on the development host. A clean checkout independently downloaded its course assets, built the image and Windows player, and passed environment and live transport checks after restart. See the [delivery plan](docs/DOCKER_PLAN.md) and [validation record](docs/DOCKER_VALIDATION.md). Earlier native-WSL results are retained separately in [history](docs/HISTORY.md).

## Linux setup (Ubuntu 24.04 x86_64)

Use a graphical desktop with X11 or XWayland and an OpenGL-capable graphics driver.
The launcher requires a local `DISPLAY`; an SSH-only shell without a desktop is not
sufficient for the rendered sensors. Unity lists Ubuntu 24.04 in its
[Unity 6.3 requirements](https://docs.unity3d.com/6000.3/Documentation/Manual/system-requirements.html).

Install Docker and preparation tools:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git gh python3 xauth
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in so group membership applies, then confirm `docker info` works
without sudo. Run the launcher as your desktop user. The Linux Compose overlay
runs ROS/RViz with your UID/GID so generated files remain owned by you.

Install [Unity Hub](https://unity.com/download) for Linux, sign in and activate your
license, then install **Unity 6000.3.23f1 with Linux Build Support (Mono)**. Close the
project in the Editor before building. Adjust `UNITY_EDITOR` to the actual path.
No host ROS installation or Windows/WSL executable is needed by these commands.

```bash
# Public checkout; authentication is not required to download.
git clone https://github.com/PixelPepper/igvc-unity-sim.git
cd igvc-unity-sim
export UNITY_EDITOR="$HOME/Unity/Hub/Editor/6000.3.23f1/Editor/Unity"
bash tools/docker.sh prepare-unity
bash tools/docker.sh build
bash tools/docker.sh unity-build
bash tools/docker.sh start --seed 2027 --difficulty normal
bash tools/docker.sh run python3 docker/verify_environment.py
bash tools/docker.sh run python3 docker/verify_integration.py
bash tools/docker.sh rviz
```

In another terminal in the repository:

```bash
bash tools/docker.sh course --seed 2027 --difficulty normal
# audit applies only after an explicitly requested guided-course regression
bash tools/docker.sh status
bash tools/docker.sh stop
```

`bash tools/docker.sh shell` opens an interactive ROS terminal; `run` executes a
single command. For other variants, use the same seed and difficulty for `start`,
`course` and `audit`. The Linux player is
`artifacts/build-course-linux/IGVCCourse.x86_64`; keep its entire build directory
together. The build log is `artifacts/logs/docker-unity-build-linux.log`.

RViz uses a scoped Xauthority cookie and the host X11 socket. On Wayland, enable
XWayland; if the launcher cannot find a cookie, set `XAUTHORITY` to your desktop's
authority file. It does not run `xhost +`. WSLg's local cookieless display is handled
separately. The ROS container uses software rendering for RViz; Unity uses the host
graphics driver. Stop a session from the checkout that started it before switching
checkouts or platforms. Only one session can own TCP port 10000.

Authenticated X11 access was also tested with a cookie-protected virtual display:
Unity, container RViz and all seven live transport checks passed; a client without
the cookie was rejected. Normal desktops use `/tmp/.X11-unix`. For an isolated
display fixture, `IGVC_X11_SOCKET_DIR` can override the Docker bind source; the
same sockets must still be visible to the host player at `/tmp/.X11-unix`.

Native Linux Editor installation/build and native desktop GPU combinations were
not exercised on this Windows host. The Linux executable was cross-built with the
matching Unity version and exercised on Linux; this is not a claim of native
desktop certification. See the [test record](docs/LINUX_VALIDATION.md).

## Windows prerequisites

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

This configuration supports one simulator session at a time, including across checkouts: Compose uses the fixed project name `igvc-sim` and TCP port 10000.

## Download and build

Download the public [repository](https://github.com/PixelPepper/igvc-unity-sim).

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

## Download the prebuilt ROS container

The [GitHub release](https://github.com/PixelPepper/igvc-unity-sim/releases/tag/sensor-autonomy-preview-2026.09.16)
provides `igvc-sim-jazzy-linux-amd64.tar.gz` and `SHA256SUMS`. The image runs
Ubuntu 24.04 with ROS 2 Jazzy, RViz and Nav2. It supports Linux x86-64 and Windows
through the WSL2 Docker setup above; it is not a Windows-container or ARM image.
Unity remains a separate host application and still needs preparation/build.

After downloading both release files, verify the checksum and load the image.
On Linux, in the download directory:

```bash
sha256sum -c SHA256SUMS
docker load -i igvc-sim-jazzy-linux-amd64.tar.gz
```

On this Windows/WSL2 setup (adjust the downloaded path):

```powershell
Get-FileHash "$env:USERPROFILE/Downloads/igvc-sim-jazzy-linux-amd64.tar.gz" -Algorithm SHA256
# Compare with SHA256SUMS, then load through the WSL Docker engine:
$archive = Join-Path $env:USERPROFILE 'Downloads/igvc-sim-jazzy-linux-amd64.tar.gz'
$wslArchive = (wsl -d Ubuntu-24.04 -- wslpath -a "$archive").Trim()
wsl -d Ubuntu-24.04 -u root -- docker load -i "$wslArchive"
```

Loading installs `igvc-sim:jazzy`, so skip the `build` action and use the normal
`prepare-unity`, `unity-build`, `start`, `rviz`, and `course` commands. Check out
the matching release tag to keep Unity and ROS interfaces aligned:
`git checkout sensor-autonomy-preview-2026.09.16`.
For registry-hosted images, Compose also accepts an `IGVC_IMAGE` override.
See [asset provenance](THIRD_PARTY_ASSETS.md); public availability does not grant
a new blanket license for vendor CAD.

## Start, inspect, and drive the course

Stop any existing native ROS simulator session first so TCP port 10000 is available. The Windows player connects to the container through `127.0.0.1:10000`; ROS discovery remains inside the container.

```powershell
./tools/docker.ps1 start -Seed 2027 -Difficulty normal
./tools/docker.ps1 status
./tools/docker.ps1 rviz
```

`start` launches the ROS container and a visible Windows Unity player with a generated course. The Windows launcher also keeps a hidden WSL process alive so Docker does not shut down after the Compose command exits; `stop` releases that helper. Startup alone does not verify that sensors or navigation are ready. RViz uses the tested WSLg/software-rendering path. A first-map GLSL warning was observed, but robot, RGB, depth and costmaps rendered; see the validation record. Keep RViz in its terminal and use another PowerShell terminal for commands:

```powershell
./tools/docker.ps1 run ros2 topic list --no-daemon
./tools/docker.ps1 run ros2 topic echo /clock --once
./tools/docker.ps1 run python3 docker/verify_environment.py
./tools/docker.ps1 run python3 docker/verify_integration.py
./tools/docker.ps1 course -Seed 2027
# audit is only for the separate guided-course regression
./tools/docker.ps1 stop
```

`course` requests experimental sensor-led motion and writes `artifacts/courses/seed-2027/sensor-run.json`.
`guided-course` uses the known guide, writes `docker-run.json`, and can be checked
with `audit`. These are different tests. Use the same seed for start and mission;
difficulties are `easy`, `normal`, and `hard`. `stop` stops the owned Unity player
and removes Compose services. Restart with `start`.

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
