# R3-a geometry inspection — 2026-09-09

The canonical forward convention has since been corrected from user confirmation: drive wheels at the front, casters at the rear. Source meshes remain unchanged; the generated description transforms frames and physical side names. Current driving evidence is in [R3-a drive mode](R3A_DRIVE.md). Earlier screenshots in this static-inspection record predate that correction.

The actual exported five-link robot now has a ROS 2 description package and a static Unity inspection scene. Original SolidWorks files remain external and unchanged. The canonical Xacro, copied visual meshes and provenance are in `ros2/src/igvc_description`; `tools/build_ros.sh` expands the Xacro before each build.

From a PowerShell terminal at the repository root:

```powershell
.\tools\igvc.ps1 robot-build
.\tools\igvc.ps1 robot-view -Visible
.\tools\igvc.ps1 robot-rviz
```

The viewer supports left/right arrows to orbit. Close it with `robot-stop`; stop the foreground RViz launch with Ctrl+C. RViz inspection uses ROS domain 43 so its static joint publisher cannot compete with the transport probe on domain 42. The existing probe commands remain available.

Validation: the description passed Xacro expansion, URDF validation and a ROS package build. Unity compiled and built the static viewer, imported five links and 888,264 triangles, and passed five coordinate/rotation assertions. RViz visibly displayed the complete model with Global Status OK. Evidence is under `artifacts/checks`: `robot-unity-import.json`, `robot-rviz.png` and `robot-unity.png`. Unity build logs are under `artifacts/logs`.

Generated Unity meshes, materials and inspection scene live in the ignored `Assets/IGVC/GeneratedRobot` folder and are recreated by `robot-build`. Source scripts and their metadata remain versioned. Full-resolution visual meshes are retained once in the description package for traceability.

The Unity screenshot records the first successful inspection build. A subsequent build passed all five frame checks, but automatic screenshot recapture failed; its camera/material adjustments have not been visually verified. The RViz screenshot was inspected successfully.

This stage has no robot drivetrain, sensor publishers or Nav2 integration. The existing moving transport fixture is separate. The full CAD mesh is too expensive for the final simulation visual budget; the player reports a D3D12 upload-buffer sizing warning. Mesh simplification and measured performance are still required. Collision boxes are provisional geometry envelopes, not validated contact shapes. RViz's KDL warning about root-link inertia reflects the preserved export and does not prevent static visualization.

The geometry review found a provisional 0.81051 m wheel track, approximately 0.22957 m drive-wheel radius, an axle behind the exported base origin, opposite wheel-axis signs, and a 16.85 mm caster contact discrepancy. These are CAD-derived observations, not physical calibration. See [geometry review](ROBOT_GEOMETRY_REVIEW.md) before implementing the drivetrain. Mass/inertia validity, physical forward direction and sensor mounts remain unresolved.

Next: simplify visual meshes, establish drive/contact frames and collision geometry, then integrate a differential-drive model with the existing command/watchdog interface. Add the OAK-D Pro and lidar frames and streams after robot motion and TF agree in Unity and RViz. Phase 2 remains open until its geometry and fidelity gates pass.
