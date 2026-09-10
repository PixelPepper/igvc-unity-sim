# Synthetic GPS waypoint missions

`igvc_gps` publishes ideal `/gps/fix` from the driven-axle `/odom` pose at up to 10 Hz. WGS84 origin is explicitly **42° latitude, −83° longitude, 0 m ellipsoid altitude**, an arbitrary synthetic location with no claim to represent the course's actual site. ROS odom +X is east, +Y north, +Z up. Odometry remains the pose authority: there is no receiver, GNSS fusion, navsat_transform or new estimator.

The canonical settings are `ros2/src/igvc_gps/config/origin.json`, installed with the package. Launch accepts `origin_file:=...`; pass the same file to the client using `--origin`. `/gps/origin` is reliable, transient-local JSON metadata, compared exactly against the mission and selected config before motion. `/gps/fix` uses simulation odometry stamps, `gps_link`, STATUS_FIX/SERVICE_GPS, and known zero ENU covariance because this ideal sensor adds no noise. This is model covariance, not a measured hardware uncertainty. The node alone owns identity static TF `base_footprint → gps_link`; do not add a duplicate broadcaster.

GPS starts automatically with the R3-a ROS launch used by `drive-start` and `course-start`. Do not launch a second publisher in that session. From PowerShell at the repository:

```powershell
./tools/igvc.ps1 gps-list
./tools/igvc.ps1 gps-run
./tools/igvc.ps1 gps-list -Mission 'C:\path with spaces\my-waypoints.json'
./tools/igvc.ps1 gps-run -Mission '/tmp/my-waypoints.json'
```

The default is checked-in `ros2/src/igvc_gps/config/waypoints.json`. `-Mission` accepts a Windows path (relative to the current PowerShell directory or absolute) or an absolute WSL path. `gps-list` only previews converted coordinates; `gps-run` requests motion through the safety gate. Use `nav-cancel` or Ctrl+C to cancel.

For editing and direct operation in sourced WSL ROS 2:

```bash
source tools/ros_env.sh
# Existing Unity, R3-a bridge (including GPS), and Nav2 must already be running.
python3 tools/gps_mission.py list ros2/src/igvc_gps/config/waypoints.json
python3 tools/gps_mission.py init /tmp/my-waypoints.json
# Edit named latitude/longitude/altitude/yaw points, then explicitly run:
python3 tools/gps_mission.py run /tmp/my-waypoints.json
```

`init` refuses to overwrite an existing file. Default editable points correspond to odom (2,0), (4,0), (6,0) metres. Yaw is ROS radians counterclockwise from east, not compass bearing. Conversion passes through WGS84 ECEF and a tangent ENU frame; altitude uses the ellipsoid, not mean sea level. The example stores the tiny ellipsoid-height changes needed to represent zero ENU height exactly.

The source course spline segment around spawn runs from source Unity (9.014, −20.582) to (−8.96, −17.77), with curved tangents; source position maps to odom `(sourceX + 2.61, sourceZ + 20.57)`. Sampling its cubic Bézier at 10,001 parameters, with knot rotations applied to tangents, gives centerline distances of 0.02672, 0.02469 and 0.01506 m for the 2, 4 and 6 m goals. The nearest barrel is at odom (−0.420, 3.519), away from that segment. These facts justify a short demonstration candidate, **not lane clearance for the entire robot**. Live lane safety must qualify each goal; the client never bypasses a rejected gate. The editable six-metre example is not a whole-course route.

The client waits up to 20 wall seconds for fresh advancing fixes, matching origin, autonomy state and Nav2. It requires manual mode initially and never resets the simulator. Each goal is bounded to 90 wall seconds by default (`--goal-timeout`, maximum 300). A fix stale for 3 wall seconds, simulation-time reversal, origin mismatch, action failure, or any autonomy-off event after enable ends the mission. Manual takeover never automatically resumes. Ctrl+C disables the gate and cancels the owned action with ROS still alive for cleanup. An unavailable cleanup service is reported; the bridge's independent command watchdog remains necessary. The gate may additionally reject motion because camera/lane perception is invalid.

Validation: pure-math unit checks cover WGS84 reference axes, global/polar round trips, local course points, east/north direction and invalid inputs. Live mission execution and lane-qualified traversal are separate integration checks.

## Integrated lane/GPS validation — 2026-09-09

The default `gps-run` mission completed the 2 m, 4 m and 6 m Nav2 goals in order with the camera lane layer and Unity boundary guard enabled. Final odom was (5.805800, approximately 0) m: 0.1942 m from the final goal, within the configured 0.20 m goal tolerance. `line_blocks=0` throughout the final session status, and completion returned to manual mode with zero velocity. `artifacts/checks/gps-live.json` records 58 matching GPS/odom acquisition stamps and maximum ENU discrepancy 1.11e-9 m. This validates the ideal coordinate mapping and a short straight mission, not whole-course autonomous traversal or measured GPS accuracy.
