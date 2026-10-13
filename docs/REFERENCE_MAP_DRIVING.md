# Driving the image-traced reference map (T-0090)

The accepted image-traced map (`ReferenceAutoNav2027`, [REFERENCE_AUTONAV_MAP.md](REFERENCE_AUTONAV_MAP.md)) is combined with the existing R3-a robot, sensors and ROS bridge in a **separate** scene and player. The sandbox, the default course and their sources are unchanged.

## Commands (PowerShell, repository root)
```powershell
powershell -ExecutionPolicy Bypass -File tools/reference-map.ps1 -Action build
powershell -ExecutionPolicy Bypass -File tools/reference-map.ps1 -Action start -Conditions clear-noon
powershell -ExecutionPolicy Bypass -File tools/reference-map.ps1 -Action smoke -Conditions low-sun -Seconds 60
powershell -ExecutionPolicy Bypass -File tools/reference-map.ps1 -Action trial -Conditions clear-noon -MaxSpeed 0.6 -TrialTimeout 180
```
- **build** runs `ReferenceDriveBuild.Build`, which writes the scene `Assets/IGVC/Scenes/ReferenceAutoNav2027Drive.unity`, validates it, and builds `artifacts/build-reference-drive/IGVCReferenceDrive.exe`. Validation and captures go to `artifacts/agents/T-0090/drive-validation.json` and `drive-<preset>-*.png`.
- **build** is bounded to 45 minutes.
- **start**, **smoke** and **trial** export the mission, verify the ROS overlay, start the launcher's **own** managed `r3a` ROS session (domain 42) and launch the visible player.
  - **smoke** fails if the player exits early. It shows only that the process survived; it is not a sensor check.
  - **trial** runs `tools/reference_map_trial.py` once, with no retry:
    1. autonomy gate off and pose reset;
    2. sensor smoke: `/clock`, RGB, depth, `/scan` and `/odom` must be received and the clock must be positive, and the first RGB frame is saved;
    3. navigation profile and its own managed nav session;
    4. clock admission (`use_sim_time` true on the perception nodes);
    5. the unchanged `sensor_course.py`, at speed <= 0.6 m/s and timeout <= 180 s;
    6. gate off, then nav stop.

    It writes `trial-report.json`, `sensor-smoke.json`, `clock-admission.json`, `first-rgb.png`, `profile.yaml`, `mission.log` and the mission's own `run.json`.
- **Ownership:**
  - Every action holds all three simulator locks.
  - It refuses to run if any Unity, IGVC or R3a player, port 10000-10002 (Windows or WSL), or **any managed ROS group** (r3a, nav, perception) is active. Port or process query errors stop it.
  - A ROS session counts as owned only when `ros_session.py start` reports that it newly started it.
  - Cleanup stops only owned processes and sessions and confirms their exit. If it cannot confirm, the launcher keeps holding the real lock handles. It re-checks only what it owned every 30 s, read-only, and keeps `<run>/ownership-retained.json` current with recovery instructions. It releases the locks only when everything owned is verifiably gone, or when root creates `<run>/root-recovery-release`. The status file is not a lease.
  - The managed ROS idle check also runs before `build`.
  - An r3a or nav session is owned only with a fresh-start receipt (`ROS started: PID n`) from this invocation's own start. An "already running" response, or any group without such a receipt, is never claimed or stopped. Instead, the locks stay held and only root's release file can free them.
  - Trial cleanup exit 3, a failed call capture, or any cleanup exception also require root's release file.
  - Automatic release needs the owned processes to be gone **and** r3a, nav and perception all to report stopped (read-only checks).
- **Run directory:** each run writes a new `artifacts/reference-drive/runs/<utc>-<id>/`, containing `launcher.log`, `autonomy.json`, `reference-conditions.json` and `unity.log`. Failed runs are kept.

## Scene
- **Spawn:** the centre of the NORTH start line (image px 960.5, 439) is odom (0, 0). The robot heads north (Unity +z, ROS +x), with the large drive wheels in front. The map is only translated; its geometry is unchanged.
- **Removed from the diagram scene:** annotations (stars, labels, blue markers), its camera and its lights, so nothing from the diagram is visible to the sensors.
- **Lane guard:** built from both edges of the two saved tape meshes. It is simulator truth only. The player runs with `--line-guard scoring`, exactly like the existing sensor-led launches.
- **Terrain support:** the map's ground plus the three ramp colliders.
- **Drums:** the 95 drums keep their original colliders. Each gets a detailed visual: a ribbed tapered body, two reflective bands, a domed top and a rubber base, all within the original cylinder envelope.
- **Surfaces:** lit materials. CC0 Asphalt031 is textured at world-metre scale (tiled every 3 m), and the white tape and the ramp are lit.
- **Lighting:** one soft-shadow sun and a procedural sky.
- **Conditions:** `ReferenceDriveConditions` applies an explicit preset from `--reference-conditions clear-noon|overcast|low-sun` before the sensors start. The depth camera is untouched, and no fog is used.

## Mission (sanitized)
`tools/reference_map_mission.py --out autonomy.json` writes only the schema accepted by `sensor_course.destinations`: a GPS origin, six broad goals and `max_speed_mps` (0.6 by default). There is no route, heading or map geometry.
- **Goals in order:** a top-right gate, the four pictured waypoint stars, then the south start/finish line.
- **Transform:** `odom x = (439 - py) * 0.035`, `odom y = (960.5 - px) * 0.035`.

## Limits (not claimed)
- **Trials are diagnostic only.** Report progress and health, not competition success. Trials are run by ASTRA's root harness with this mission (speed ceiling 0.6 m/s, 180 s each, no retry).
- **No full-lap audit.** The existing auditor needs a generator centreline and guide route. This map has none, and none is fabricated.
- **Possible tight passages:** some traced passages may be narrower than the 1.0 x 1.7 m robot needs. Failures are reported; geometry is never moved.
- **Other limits:** no rain, fog or sensor-noise modelling. Drum dimensions are the user's measurement. The realism code here is a reviewed-in-place adaptation, not an import of the `claude/sim-realism` branch.
