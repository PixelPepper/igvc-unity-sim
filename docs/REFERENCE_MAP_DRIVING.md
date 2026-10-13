# Driving the image-traced reference map (T-0090)

The accepted image-traced map (`ReferenceAutoNav2027`, [REFERENCE_AUTONAV_MAP.md](REFERENCE_AUTONAV_MAP.md)) is combined with the existing R3-a robot, sensors and ROS bridge in a **separate** scene and player. The sandbox, the default course and their sources are unchanged.

## Commands (PowerShell, repository root)
```powershell
powershell -ExecutionPolicy Bypass -File tools/reference-map.ps1 -Action build
powershell -ExecutionPolicy Bypass -File tools/reference-map.ps1 -Action start -Conditions clear-noon
powershell -ExecutionPolicy Bypass -File tools/reference-map.ps1 -Action smoke -Conditions low-sun -Seconds 60
```
- **build** runs `ReferenceDriveBuild.Build`, which writes the scene `Assets/IGVC/Scenes/ReferenceAutoNav2027Drive.unity`, validates it, and builds `artifacts/build-reference-drive/IGVCReferenceDrive.exe`. Validation and captures go to `artifacts/agents/T-0090/drive-validation.json` and `drive-<preset>-*.png`.
- **start** and **smoke** export the mission, verify the ROS overlay, start the managed `r3a` ROS session (domain 42) and launch the visible player. A smoke run stops after `-Seconds` (at most 180). No mission is driven by this script.
- **Locks:** every action holds all three simulator locks. It refuses to run if any Unity editor or player, or ports 10000-10002, are in use. It only stops what it started.
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
