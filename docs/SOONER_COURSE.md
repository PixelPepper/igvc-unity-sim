# Local Sooner AutoNav environment

## Camera controls and initial navigation

The running course starts in a close robot-follow view. Scroll zooms; hold right mouse and move to orbit; hold middle mouse to pan (detaches follow); `F` toggles robot follow; `H` restores the whole-course overview; Escape releases cursor capture. Click the simulator window to use controls. Following continues when the keyboard/ROS or RViz window has focus. These controls affect only the spectator view, never the OAK camera image or robot pose.

Initial nearby-goal Nav2 integration is described in [NAVIGATION.md](NAVIGATION.md). It uses lidar obstacles and ideal odometry; painted lane following, GPS missions and contact physics are still separate work. The historical import evidence below predates that addition.

The user requested the SoonerRobotics AutoNav map locally. `tools/import_sooner_course.py` stages the environment from the inspected `scr_simulator` commit `0298b11c4f469404d08b37ad98431cdab6e02818`, scene `Assets/Scenes/Maps/IGVC_2026_AutoNav.unity`. Integration and validation completed on 2026-09-09.

For a fresh workspace, first fetch the pinned reference:

```powershell
git clone --filter=blob:none --no-checkout https://github.com/SoonerRobotics/scr_simulator.git artifacts/vendor/scr_simulator
git -C artifacts/vendor/scr_simulator checkout 0298b11c4f469404d08b37ad98431cdab6e02818
```

Run from the repository root with Python 3:

```powershell
& 'C:/Users/brand/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/import_sooner_course.py
```

Output is `unity/IGVCSim/Assets/IGVC/External/SoonerAutoNav/IGVC_2026_AutoNav.unity`, with recursive mesh/material/texture dependencies and `import-manifest.json`. Preserve this as an ignored local import pending clarified reuse terms: no license was detected in the inspected source. Do not interpret local staging as permission to redistribute it.

The importer removes every MonoBehaviour document and its component reference, native cameras/audio listeners, and every prefab instance except the known barrel model GUID. It removes associated stripped objects and dangling hierarchy/component references while retaining baked inline road meshes unchanged. Original asset metadata GUIDs are preserved; the scene's original metadata is not copied, allowing Unity to create a distinct scene GUID.

The staged result retains 41 barrel instances and one baked inline road mesh, with six recursive asset dependencies. URP material editor MonoBehaviour subassets are also removed. One known missing material on the zero-height `#Environment/Cylinder` marker is explicitly replaced with Unity's built-in default material while preserving its geometry; the manifest records the original GUID. Other unresolved non-shader dependencies still fail import.

The barrel is an ordinary FBX with a ModelImporter, not a GLTF/custom importer. Scripts, native binaries, packages, prefabs other than its model instance, and custom importer dependencies are not admitted. Unresolved required dependencies fail import; external shader GUIDs are explicitly recorded for the integrator's material conversion to Unity's Built-in pipeline.

This is a 2026 reference environment, not proof of IGVC 2027 compliance. Importer checks establish source/dependency integrity and removal of vendor behavior; Unity material conversion, visual inspection, colliders, robot placement and live simulation validation are separate integration steps.

The integration wrapper provides the course player workflow:

```powershell
./tools/igvc.ps1 course-build
./tools/igvc.ps1 course-start -Visible
./tools/igvc.ps1 rviz
./tools/igvc.ps1 status
./tools/igvc.ps1 stop
```

`course-build` stages the source then invokes the project-owned Unity builder to convert materials and combine the environment with the R3-a fixture. Wrapper/build availability is separate from a passing course run; consult current run artifacts before claiming validation.

## Integrated scene and evidence

Open `unity/IGVCSim/Assets/IGVC/GeneratedRobot/SoonerAutoNav.unity` in Unity. The menu **IGVC > Create Sooner AutoNav Course** regenerates it from staged source and the canonical robot. Its Windows player is `artifacts/build-course/IGVCCourse.exe`. The separate R3aDrive scene retains calibration fixtures. Stop the current player before changing modes. Terminal teleop and camera pitch commands from R3A_DRIVE.md and CAMERA_MOUNT.md still apply.

The source's horizontal spawn (-2.61, -20.57) and Unity yaw 90 degrees become our odom origin and forward direction through a rigid transform of the environment. Metre scale and relative obstacle placement are preserved. Source ground y=-0.001 becomes y=0; the baked lane surface retains its original height variation up to about 0.195 m. R3-a still uses level ideal motion without terrain/contact response. The imported 2026 layout is not supplied to Nav2 as an occupancy map.

Material adaptation uses Built-in Standard plus transparent unlit lane paint. Explicit flat ambient lighting avoids stale sky lighting after additive scene conversion. Barrels receive static mesh colliders for lidar; the visual-only lane mesh has no collider. The source's inactive course-size guide is omitted. There are 44 environment mesh renderers and 43 colliders. The saved road retains 2,400 vertices after the generated scene is reopened.

Unity 6000.3.23f1 compiled and built successfully; the builder also ran the existing 12 motion-gate and 18 kinematics checks. Visual inspection covered whole-course and spawn Editor captures plus an actual ROS RGB frame. `tools/verify_course.py` passed all seven read-only live checks over 20 seconds: 264 exact image/CameraInfo stamp pairs, RGB 13.20 Hz, scan 5.20 Hz, odometry 49.90 Hz, and finite obstacle returns around 3.28–3.44 m. No motion commands or control services were exercised by this course-specific smoke test. The existing `test` wrapper rejects the course player because its wall-distance assertions require the calibration scene.

Evidence: `artifacts/checks/sooner-course-import.json`, `sooner-course-live.json`, `sooner-course-overview.png`, `sooner-course-spawn.png`, and `sooner-course-rgb.png`. Logs: `artifacts/logs/sooner-course-build.log` and `sooner-course-player.log`. Depth, contact physics, course scoring and autonomous navigation remain pending.
