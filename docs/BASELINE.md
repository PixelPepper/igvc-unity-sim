# Inspected baseline

Inspected 2026-09-09. Source files are evidence, not instructions to execute their embedded comments, launch files, or exporter guidance.

## Workspace and tools

- `C:/Users/brand/Documents/ChatGPT/IGVC SIM` contains an initialized Git repository with no commits and, before this planning work, no project files.
- No Unity project was found in the workspace or its immediate sibling directories. There is no verified project version, render pipeline, package set, scene, or testing baseline. A Unity project context document is therefore deferred until a project exists.
- Editor folders exist for `6000.3.23f1` and `6000.6.0f1` under `C:/Program Files/Unity/Hub/Editor`. Neither was launched or validated.
- WSL2 has `Ubuntu-24.04`. Sourcing `/opt/ros/jazzy/setup.bash` exposes `/opt/ros/jazzy/bin/ros2`; `ros-jazzy-ros-base` is installed.
- `ros2 pkg prefix` could not find `rviz2`, `nav2_bringup`, or `robot_localization` in the sourced base environment. Corresponding RViz/Nav2 packages were not listed by the queried Debian package names. Custom installations elsewhere remain possible.
- `/home/brand/robotlab_spike_v1` contains `build`, `install`, and `log`, including build metadata for `ros_tcp_endpoint` and `robotlab_actions`. No `src` directory was found there. Do not reuse those generated outputs as source or assume that spike works; locate its source first if relevant.
- No callable Unity Editor MCP tools are exposed in this session. No local Unity project exists in which to inspect MCP configuration. Editor connectivity is unverified; it is optional for the simulator architecture.

## Robot sources

Original root: `C:/Users/brand/Downloads/OneDrive_2026-03-04/R3-a (Spring 2025)`.

Found 18 SLDASM files, 64 SLDPRT files, 41 STL files, one STEP file, and one URDF, among other export files. Presence does not prove all SolidWorks assembly references resolve. No SolidWorks assembly was opened or rebuilt.

Useful inputs:

- `R3-a (Top_Assem).SLDASM`: assembly reference.
- `R3-a (stp).STEP`: alternative neutral geometry export.
- `R3-a URDF/urdf/R3-a URDF.urdf`: inspected robot description.
- `R3-a URDF/package.xml`: inspected ROS 1 packaging.
- `R3-a URDF/meshes/`: five referenced STL files, all present.

| Mesh | Triangles |
|---|---:|
| base_link.STL | 599,564 |
| left_caster.STL | 114,806 |
| right_caster.STL | 114,806 |
| wheel_left.STL | 29,544 |
| wheel_right.STL | 29,544 |
| Total | 888,264 |

Counts were read from binary STL headers and checked against file sizes. Geometry, bounding boxes, and actual dimensions have not yet been validated.

The URDF contains five links and four continuous joints. All non-root links attach directly to `base_link`. The two driven-wheel axes have opposite signs: right `(0,-1,0)`, left `(0,1,0)`. Caster joints rotate around Z, with no separate caster wheel spin joints.

Wheel origin separation in Y is 0.81051 m if the export units are correct. Driven wheels have X = -0.25591 while casters have X = +0.52775. CAD naming suggests front driven wheels, so physical forward direction needs explicit verification before adopting ROS +X forward.

Summed link mass is 96.8552188 kg; base mass is 81.1401447 kg. These are exported values, not measurements. Verify material density, duplicated mass, payload inclusion, center of mass, and inertia tensors.

The package name `R3-a URDF` contains spaces and uses `catkin`, ROS 1 launch files, `rviz`, and Gazebo dependencies. It needs a ROS 2 `ament_cmake` description package with a valid name such as `igvc_description`, updated mesh URIs, and ROS 2 launch files. The geometry itself can be reused after validation.

Every collision uses the same detailed STL as the visual. No sensor links or optical frames are defined. Camera and lidar-related CAD filenames suggest intended equipment but do not confirm current hardware, mounting, intrinsics, or field of view.

## Outstanding evidence

Actual robot dimensions, wheel radius, motor limits, caster construction, sensor revisions/extrinsics/settings, encoder resolution, measured mass, autonomy repository, graphics performance, and Windows/WSL transport behavior remain unverified. User-confirmed sensors are OAK-D Pro and RPLIDAR A1; the confirmed target is IGVC 2027 AutoNav only. The user supplied `http://www.igvc.org/2026rules.pdf` as an additional reference; a detailed year-to-year comparison remains a Phase 0 task. GNSS hardware is not yet identified.

## Follow-up inputs

The user confirmed they believe WSL2/Jazzy is already set up; the local probes above independently confirm the base installation. Windows Unity plus WSL2 remains the proposed host arrangement pending any different preference.

The subsequently supplied `C:/Users/brand/Downloads/solidworks_urdf_exporter-master/solidworks_urdf_exporter-master` is the exporter source repository. Its README and `SW2URDF.sln` identify a Visual Studio add-in project; its URDF files are example robots. These do not replace the actual R3-a robot URDF discovered above. No exporter setup instructions were executed, and no exporter build is needed merely to use the existing R3-a export.
