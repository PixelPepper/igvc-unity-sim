# Native WSL AutoNav

Unity runs on Windows; ROS 2 Jazzy and RViz run directly in Ubuntu-24.04 WSL.
Stop the Docker simulation before using this mode. A full sensor-led lap remains
unproven; this is the same experimental navigator, not a prerecorded route.

From PowerShell in the repository root, build the patched controller once:

```powershell
wsl -d Ubuntu-24.04 -- bash tools/build_native_nav2.sh
wsl -d Ubuntu-24.04 -- bash tools/build_ros.sh
```

This requires Jazzy Nav2 1.3.12 and initialized rosdep (`sudo rosdep init` once,
then `rosdep update --rosdistro jazzy` inside Ubuntu). Dependencies may require
sudo. The patch builds in `~/igvc_nav2_overlay`; the environment enables it
after its real C++ critic regression passes, without replacing system packages.

Start the simulator and navigation, then keep RViz running in this terminal:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\igvc.ps1 variant-start -Seed 2027 -Visible
powershell -ExecutionPolicy Bypass -File .\tools\igvc.ps1 nav-start
powershell -ExecutionPolicy Bypass -File .\tools\igvc.ps1 rviz
```

In another PowerShell terminal, also at the repository root, start sensor-led driving:

```powershell
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/sensor_course.py --mission artifacts/courses/seed-2027/autonomy.json --report artifacts/courses/seed-2027/native-sensor-run.json --timeout 600
```

`variant-start` uses scoring-only lane checks, matching Docker. The mission reads
six broad destinations and live observations. `loop-run` remains the separate
route-informed regression and is not a substitute for this command.

Stop with:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\igvc.ps1 stop
```
