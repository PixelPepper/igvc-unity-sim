# R3-a description preparation

Canonical model: `urdf/r3_a.urdf.xacro`. The user confirmed that the large drive wheels are at the front and the casters at the rear. Every link coordinate basis is rotated by Z pi so canonical +X points toward the drive wheels. Source left/right link and joint names are simultaneously swapped to match physical left/right. Mass and physical geometry are preserved; joint origins/axes and inertia tensors are transformed into the new basis. The root remains `base_link`, with no sensor mounts or `base_footprint` added.

Visual STL bytes and filenames remain unchanged under `meshes/visual`; each visual origin applies the Z pi rotation. Consequently canonical `wheel_left` uses the source `wheel_right.stl`, and conversely. `provenance.json` records source hashes and the complete name/basis mapping. The drive axle is +0.25591 m from `base_link`; a separate axle-ground `base_footprint` therefore requires a -0.25591 m X offset to `base_link`. Canonical left drive joint is at (+0.25591, +0.40526, -0.07445) with +Y axis; the right is at (+0.25591, -0.40525, -0.07445) with -Y axis. Casters lie at X=-0.52775 m.

Collision boxes conservatively enclose each visual mesh in its local axes. They are provisional clearance geometry, especially unsuitable for validated wheel contact physics. The exported mass, dimensions, frame orientation and units still need physical confirmation. No calibrated robot dynamics or competition readiness is claimed. Asset redistribution rights have not been established; retain private use until provenance is clarified.

From WSL in the repository root, regenerate using the unchanged originals:

```bash
python3 tools/prepare_description.py --urdf '/mnt/c/Users/brand/Downloads/OneDrive_2026-03-04/R3-a (Spring 2025)/R3-a URDF/urdf/R3-a URDF.urdf'
source tools/ros_env.sh
xacro ros2/src/igvc_description/urdf/r3_a.urdf.xacro -o ros2/src/igvc_description/urdf/r3_a.urdf
check_urdf ros2/src/igvc_description/urdf/r3_a.urdf
```

The `.urdf` is a derived static export; edit the generator/canonical source deliberately and regenerate it. Build with the repository ROS build script before launch. In a separate session with the probe stopped:

```bash
ros2 launch igvc_description display.launch.py
```

The launch starts robot_state_publisher and uses joint_state_publisher_gui when available, otherwise the non-GUI publisher. Disable RViz with `rviz:=false`, or request non-GUI joints with `gui:=false`. Defaults use wall time. This viewer has no odometry or simulator clock and must not compete with the probe's TF publishers.
