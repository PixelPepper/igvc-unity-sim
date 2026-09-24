# SoonerRobotics comparison

Source review: 2026-09-16. This project imports reference environment art, not
SoonerRobotics' autonomous driving implementation. The importer strips
MonoBehaviours and excludes upstream source code. See `tools/import_sooner_course.py`.
The simulator asset pin is `0298b11c4f469404d08b37ad98431cdab6e02818`.

| Area | SoonerRobotics source inspected | This project |
| --- | --- | --- |
| Planning | Custom A* over expanded camera configuration space, with GPS waypoints | Observed-costmap forward-arc goal selection, followed by Nav2 Smac Hybrid-A*; six broad GPS destinations |
| Motion control | Pure Pursuit lookahead and heading-error control, with reverse fallback | Nav2 MPPI and asymmetric footprint checks; bounded collision-checked backup; command and sensor freshness gates |
| Vision | HSV thresholding, image masking, perspective warping, configuration-space expansion | Independently implemented HSV/component processing, acquisition-time TF, depth ground/surface classification, lane/hazard point clouds and Nav2 costmap layers |
| Localization | GPS-bearing, dead-reckoning and particle-filter modes; GPS-bearing default | Ideal simulator odometry and synthetic GPS; realistic drift and hardware fusion remain pending |
| Transport | Current Unity drivetrain receives SUS/FlatBuffers CAN-like packets | ROS-TCP Connector and standard ROS sensor/control interfaces |
| Robot and course | Their robot and reference environment | User-supplied R3-a geometry, front driven wheels/rear casters, roof lidar, pole camera, seeded obstacles, lane gaps and marked ramp |

Neither inspected lane detector is a learned segmentation network. Both stacks
use conventional image processing, but their implementation and interfaces differ.
Both target ROS 2 Jazzy/Ubuntu 24.04; sharing the middleware does not make the
algorithms or robot models equivalent.

## Sources

- [2025 simulation launch](https://github.com/SoonerRobotics/autonav_software_2025/blob/main/autonav_ws/src/autonav_launch/launch/simulation.xml)
- [Custom A*](https://github.com/SoonerRobotics/autonav_software_2025/blob/main/autonav_ws/src/zemlin_navigation/src/astar.py)
- [Path resolver/Pure Pursuit](https://github.com/SoonerRobotics/autonav_software_2025/blob/main/autonav_ws/src/zemlin_navigation/src/path_resolver.py)
- [Vision transforms](https://github.com/SoonerRobotics/autonav_software_2025/blob/main/autonav_ws/src/zemlin_vision/src/transformations.py)
- [Cost expansion](https://github.com/SoonerRobotics/autonav_software_2025/blob/main/autonav_ws/src/zemlin_vision/src/expandify.cpp)
- [Localization filters](https://github.com/SoonerRobotics/autonav_software_2025/blob/main/autonav_ws/src/zemlin_filters/src/filters.py)
- [Current Unity drivetrain](https://github.com/SoonerRobotics/scr_simulator/blob/main/Assets/Scripts/Robots/DrivetrainModule.cs)

## Validation limits and useful adaptations

The upstream competition launch currently comments out autonomous nodes. Its
repository alone does not prove which configuration competed or won. Our
successful historical guided laps likewise do not prove sensor-led autonomy.
The current sensor-led implementation has not completed a verified full lap.

Useful future comparisons include running both controllers against identical
recorded observations, testing perspective/HSV robustness under varied lighting,
and introducing GPS/odometry noise before adopting a localization filter. Porting
their controller wholesale would require adapting their messages, state management,
robot dimensions, steering behavior and sensor calibration. Any comparison must
use the same no-prior-course-information constraint.
