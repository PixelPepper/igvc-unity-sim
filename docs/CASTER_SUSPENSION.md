# Experimental rear caster suspension

The same caster assemblies now also have [motion-aligned swivel yaw](CASTER_SWIVEL.md). Vertical slider displacement and yaw are published separately through their existing joint chain. The provisional suspension support sample locations do not move with caster yaw; this remains a simplified contact approximation.

[Turning validation](CASTER_TURNING.md) now covers a full ramp pivot and measured left/right arcs, alongside 48 Unity checks at oblique headings. All passed without a runtime suspension change. `tools/igvc.ps1 terrain-turn-test` runs the bounded manual experiment from a fresh suspension bench origin.

The terrain bench uses a reduced-order rear spring/damper model. The driven axle stays rigid, with front support locations at local Unity X ±0.405255 m. Two rear supports sit at X ±0.24612 m, Z −0.85 m. Each rear spring uses a provisional 12,000 N/m stiffness and 700 N·s/m damping, with 30 kg effective rear sprung mass and ±0.04 m vertical travel. Static sag is compensated at the nominal pose. Defaults belong in `ros2/src/igvc_description/config/caster_suspension.json`; these values are not measured R3-a calibration.

The solver evolves one rear body height/velocity state and pitches the body relative to an approximately rigid front axle. It reports individual left/right travel, but does not provide independent body roll from two suspension degrees of freedom. Spring inputs are vertical support heights; gravity/static sag is compensated at the nominal pose. The contact footprint remains yaw-only. Missing support or infeasible cross-axle travel rejects movement; hard stops use kinematic clamping, not impulse physics. This models provisional support response, not actual tire contacts, gravity-driven free motion, traction, collision clearance or full suspension dynamics. Normal flat mode uses zero suspension-joint displacement.

`/sim/suspension_state` is a 50 Hz `sensor_msgs/JointState` with the same acquisition stamp as odometry and `/sim/body_transform`. Its names are `rear_body_height`, `left_compression`, `right_compression`; positions are relative rear body height and the two vertical compressions in metres, and velocities are their rates in m/s. `/joint_states` adds `left_caster_suspension_joint` and `right_caster_suspension_joint`, translating along body +Z. Each joint displacement equals its vertical compression divided by body-up's world vertical component. The dynamic `base_footprint -> base_link` TF retains the bridge as its sole authority.

The bench retains the 0.4 m ramp described in [terrain body](TERRAIN_BODY.md). A 0.025 m high, 0.16 m wide strip at Unity X=−0.24612 m spans ROS X=0.6–1.4 m. Only the left caster crosses this strip; the more widely spaced front wheels miss it. This provides an asymmetric response fixture before the main ramp.

From the repository root in PowerShell, with the built terrain player:

```powershell
.\tools\igvc.ps1 stop
.\tools\igvc.ps1 terrain-build
.\tools\igvc.ps1 terrain-start -Visible
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/verify_caster_suspension.py --speed .6
```

Suspension is enabled by default for the terrain bench. `terrain-start -Visible -RigidTerrain` selects rigid support instead; the older `verify_terrain_body.py` requires that rigid mode. Start each traversal at a fresh stationary origin. Neither verifier resets the simulator or enables autonomy.

The bench uses the existing spectator controls: scroll to zoom, hold right mouse to orbit, `F` to follow the robot and `H` for the ramp overview.

To inspect the published travel from another terminal: `ros2 topic echo /sim/suspension_state`. For the visual slider positions, inspect the two `*_caster_suspension_joint` entries in `/joint_states`.

The new verifier requires a fresh exact-stamp join of odometry, body transform, joints and suspension diagnostics before moving. It publishes manual forward commands at 20 Hz for at most 55 wall seconds, stops forward commands at X≥11 and repeatedly sends zero for two seconds on exit. It checks finite values, travel limits, body offset/pitch, prismatic projection, independent support heights, unequal strip response, ascent/descent, final settling and 3D axle chord speed. Strip-edge samples within 2 mm are excluded only from the discontinuous support-height equation check. It requires at least 100 joined records and rejects a static `base_link` TF. Dynamic slider TF is independently compared at exact joint timestamps against canonical mounts plus the body-Z displacement. Separate bounded caches accommodate either arrival order; the verifier requires at least 50 comparisons and observations from both sides, and rejects static slider edges.

`--speed` accepts 0.1–2.2 m/s; `--report` overrides the default `artifacts/checks/caster-suspension-live.json`. The final [terrain Unity build](../artifacts/logs/terrain-body-unity-build.log) passed 13 spring checks, 11 caster-terrain checks and 13 pre-existing rigid-support checks. Five canonical-description unit tests passed, covering unchanged source, zero-displacement chain preservation, slider geometry/travel and rejected invalid inputs.

Both live traversals passed all ten checks with no errors and returned to flat, settled suspension:

| Evidence | Exact-stamp joins | TF comparisons per side | Maximum absolute compression | Maximum axle 3D chord speed |
| --- | ---: | ---: | ---: | ---: |
| [0.6 m/s](../artifacts/checks/caster-suspension-live.json) | 1,067 | 344 | 0.02345047 m | 0.6000000 m/s |
| [2.2 m/s](../artifacts/checks/caster-suspension-fast.json) | 392 | 130 | 0.02757282 m | 2.2000000 m/s |

The slow traversal observed 0.02500000 m left/right compression difference over the strip. These are model-consistency measurements, not measured hardware spring performance. Terrain, drive and course players were rebuilt. The [28-check normal-drive regression](../artifacts/checks/caster-drive-live.json) passed, including reset/pause/stop, canonical frames and zero flat caster travel. The [seven-check course stream regression](../artifacts/checks/caster-course-live.json) also passed over 20 seconds, checking the expanded joint message and zero slider displacement. These are targeted compatibility checks; no new full autonomous loop was run for this suspension slice. The bench results do not establish hardware suspension fidelity or autonomous ramp capability.

The [rigid fallback regression](../artifacts/checks/caster-rigid-regression.json) passed at 0.6 m/s with 977 matched pairs, all six checks and no errors after the spectator-camera addition. This preserves the prior three-point bench as a comparison mode. Five description tests are recorded in [the test output](../artifacts/checks/caster-description-tests.txt). `build_ros.sh` now installs the seven packages sequentially after a parallel build exposed a setuptools egg-info read/removal race; dependency versions were unchanged.
