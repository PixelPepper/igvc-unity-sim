# RPLIDAR A1 front housing

The user supplied `rp-lidar-a1-inventor-reassembly-1.snapshot.8.zip` and marked the front lid housing in a screenshot. The archive's IGES assembly is the visual source; the original Inventor files, IGES and robot CAD remain unchanged.

The housing was located by analysing the original full-resolution robot mesh, then transforming coordinates into the confirmed physical-forward frame. Four mounting holes have approximately 2.100001 mm radius. Their canonical base-frame centers are `(0.298022802, ±0.028031233)` and `(0.228022798, ±0.020031230)` metres. Matching the lidar's 70 mm mounting-pair spacing places its rotor axis at `(0.2700228, 0)` metres. The motor end points toward negative X, into the smaller rear end of the housing.

The feet seat on raised bosses at base-relative Z=0.295 m, rather than the roof panel at Z=0.283175 m. The seating origin is therefore `(0.2700228,0,0.295)` m. The scan frame adds the sensor's estimated internal scan-plane height; this is kept distinct from the mechanically measured seating plane.

The IGES laser instance is 44.6 mm above the foot datum (the detector instance is 43.6 mm). The provisional scan plane uses the laser instance height, placing `lidar_link` at `(0.2700228,0,0.3396)` m in `base_link`. The mesh is offset -0.0446 m within that link, so its feet remain on the bosses. The CAD instance placement is not proof of the device's effective optical origin or zero-azimuth calibration.

The converted mesh uses metres, +Z upright, rotor axis at XY zero and feet at Z zero. Its motor end faces -X. It contains 30,000 triangles, making the Unity robot plus lidar 179,986 visual triangles. Its maximum overall-bound deviation after simplification is 1.111 mm; fine mounting/optical details are not manufacturing geometry.

`config/lidar_mount.json` in `igvc_description` records the final mechanical and scan transforms. The description generator adds a fixed `base_link -> lidar_link` joint and its mesh. Robot state publisher owns that TF; the adapter no longer publishes a competing lidar transform in R3-a mode. Unity imports the same joint and casts `/scan` rays from that transform, with ROS +X as angle zero and +Z as the scan axis.

This is a CAD-derived installation. The internal optical plane and zero-angle calibration still need confirmation against the actual device. Synthetic scans remain ideal, without rotor motion, robot self-occlusion, noise or sunlight effects. The model is visual geometry and does not add a physical collision model.

Validation on 2026-09-09: Unity built successfully and passed the existing 18 kinematics and 12 command-protection checks. All 27 live ROS checks passed, including the mounted lidar TF and the expected forward wall distance from its new origin. The 30-second load interval delivered RGB 13.37 Hz, lidar 5.23 Hz, odometry 50 Hz and real-time factor 0.99999. The Unity close-up was inspected with a 5 mm near clip plane to avoid cutting into the sensor at close range. Simplification causes visible faceting and up to 1.111 mm cap deformation, so this preview is not an exact surface model.

Reproduction and evidence:

- `tools/prepare_lidar.py`: IGES conversion and normalized visual asset provenance.
- `tools/locate_lidar_mount.py`: housing circle fits and seating-plane intersections.
- `tools/prepare_description.py`: canonical robot plus configured lidar joint.
- `artifacts/checks/lidar-mount-analysis.json`: robot housing measurements.
- `artifacts/checks/lidar-unity-mount.json`: imported scan transform and visual bounds in Unity world coordinates.
- `artifacts/checks/lidar-mount-editor.png`: close-up offscreen render of the generated Unity scene.
- `artifacts/checks/live-r3a.json`: live ROS scan geometry and sensor TF acceptance.
