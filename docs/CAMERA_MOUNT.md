# OAK-D Pro pole-top tilt mount

The user confirmed that the pole-top bracket tilts up/down. The simulator mounts the OAK-D Pro on that bracket and moves both the camera and extracted bracket about the measured pitch pin. Physical forward remains toward the large drive wheels; the camera starts facing forward and 10° down from the rear pole.

The enclosure comes from the [official Luxonis OAK-D Pro STEP](https://github.com/luxonis/oak-hardware/blob/master/DM9098_OAK-D-Pro/3D_Models/README.md). It is tessellated into 56,352 triangles without decimation. Small front-surface rings/discs make the three CAD aperture positions visible on the opaque preview; they are appearance overlays, not separate simulated imagers. User-provided pictures were appearance references, not dimensional calibration.

## Placement and tilt

- Base-relative pivot: `(-0.34396836, 0, 0.8)` m; axis ROS +Y.
- Zero pitch: level, optical forward along robot +X. Positive pitch looks down; negative looks up.
- The original CAD bracket pose is approximately +4.09452° downward.
- The 1,760-triangle moving bracket was extracted as a complete connected component. The stationary pole remains in the base mesh. No source mesh was cut heuristically or modified in place.
- Camera rear envelope is centered on the attachment surface. The nominal body origin is `(0.06290043, 0, 0.00447802)` m from the pivot in the level bracket frame.
- The RGB optical-frame datum is `(0.01155045,0,0.00476378)` m from the camera body center, based on the CAD front glass. Effective optical-center and mounting tolerances still need hardware calibration.

`config/camera_mount.json` is the mount record. The generator creates `camera_pitch_joint`, `camera_mount_link`, `camera_link` and `camera_color_optical_frame`. Unity publishes the pitch joint position with the wheel states; robot_state_publisher owns the camera TF. The rendered camera is bound to the same body and aperture datum, with an explicit optical-axis check during the Unity build.

The simulation clamps pitch to ±30° and slews at 1 rad/s. These are test controls, not measured mechanical stops, an actuator model or a claim that the physical mount is motorized. Pause and simulated stop hold pitch and ignore new tilt commands. Reset restores `default_simulation_pitch_rad` (10° down); zero remains the level command datum. Dynamic collision geometry and inertia have not been split/calibrated; the whole robot remains an ideal kinematic simulator.

## Terminal control

Build/start with the existing `drive-build` and `drive-start` commands. In WSL from the repository root:

```bash
source tools/ros_env.sh
# About 11.5 degrees down; use -0.2 for up or 0.0 for level.
ros2 topic pub --once /sim/camera_pitch_command std_msgs/msg/Float64 '{data: 0.2}'
```

RGB remains `/camera/color/image_raw`. New `/camera/color/camera_info` uses the identical acquisition timestamp and optical frame. Its 640×480, 54° vertical-FOV pinhole intrinsics describe the Unity camera, not the physical OAK calibration. Focal lengths are 471.0265 px; principal point is `(319.5,239.5)` px and distortion is zero. Ideal geometric depth is now implemented; see DEPTH_CAMERA.md. Stereo matching and sensor uncertainty remain future work.

## Evidence and reproduction

`tools/prepare_camera.py` records the source STEP hash, conversion and aperture data; `tools/prepare_camera_mount.py --simplify` reproduces bracket extraction and the stationary base visual. Mesh metadata and recipes are in the description package's `meshes/camera` and `meshes/camera_mount` folders.

The live camera verifier passed 48 checks covering neutral/down/up poses, limits, slew, reset, pause/stop, stationary robot pose, exact-stamp body/optical TF, axis conventions, and paired RGB/CameraInfo. Run it independently when the robot is idle:

```bash
bash tools/run_ros.sh python3 tools/verify_camera_mount.py
```

Report: `artifacts/checks/camera-mount-live.json`. Close-up: `artifacts/checks/camera-mount-editor.png` (offscreen Unity Editor render). The verifier waits for active streams before making service calls: early service discovery during connector re-registration previously caused an endpoint service-handle failure. It does not treat mere discovery as readiness. The general live robot regression is recorded separately in `live-r3a.json`.

The updated 10° default passed **53 live checks** in `artifacts/checks/camera-mount-downward-live.json`, including the startup default, level/down/up poses, limits, pause/stop, exact-time optical TF and reset back to the downward default. The verifier restores that default when it finishes.
