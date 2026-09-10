# Motion-aligned caster swivel

The existing `leftCaster` and `rightCaster` joints now use continuous, unwrapped swivel angles. The nominal pivots relative to the driven axle are ROS X=−0.78366 m and Y=±0.24612 m, derived from the canonical mounts. For footprint twist `(v,w)`, each pivot's planar velocity is `(v − w*y, w*x)`. The implementation projects that velocity into the tilted body frame before calculating its target angle. Positive joint rotation is ROS +Z, corresponding to Unity −Y.

Provisional defaults in `ros2/src/igvc_description/config/caster_swivel.json` are a 0.12 m exponential alignment distance, a 4 rad/s angular-rate cap and a 0.005 m/s stationary deadband. Motion aligns the caster toward the local velocity; stopping holds the angle, pause freezes it and reset returns it to zero. The shared implementation is the default for rebuilt R3-a players.

These are motion-aligned meshes and TF, not a no-slip caster model. Trail, friction, contact forces and shimmy are not simulated. Swiveling does not move the fixed suspension-support sample locations. The whole CAD mesh in each original caster URDF link rotates; no separate wheel-rolling joint has been added.

From the repository root in PowerShell, start a fresh drive pad at its stationary origin:

```powershell
.\tools\igvc.ps1 stop
.\tools\igvc.ps1 drive-build
.\tools\igvc.ps1 drive-start -Visible
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/verify_caster_swivel.py
```

The verifier commands bounded manual forward, reverse, pivot and arc phases, separated by measured stops. It requires fresh exact-stamp odometry/joint observations before driving, aborts failed phases and repeatedly sends zero for two seconds on exit. It does not reset the simulator, rearm autonomy or send navigation goals. Its optional `--report PATH` changes the output location.

The [flat-pad live report](../artifacts/checks/caster-swivel-live.json) passed all 18 checks with 864 joined records and 288 exact-stamp TF comparisons per caster. Measured forward/reverse progress was +0.969/−0.972 m; the pivot covered 1.647 rad, and the arc covered 1.122 m with −0.70125 rad yaw change. Maximum swivel rate was 4 rad/s, stopped angular drift was zero and maximum settled target error was 0.002591 rad. These checks also enforce continuous angle increments, reverse alignment near π, distinct pivot angles and caster TF consistency.

The [drive build log](../artifacts/logs/r3a-drive-build.log) records 12 pure Unity swivel checks. The [29-check drive regression](../artifacts/checks/caster-swivel-drive-live.json) passed, including reset after nonzero caster angles, pause/stop protections, sensor rates and real-time factor.

The rebuilt terrain player passed the [combined swivel/suspension ramp test](../artifacts/checks/caster-swivel-terrain-live.json): 13 checks and 1,359 joined records, full 6.414 rad pivot with zero measured axle drift, three measured arcs, maximum 24.524 mm compression and bounded 4 rad/s swivel rate. The turning verifier now joins joint states as well as body/odometry/suspension diagnostics. This tests their coexistence on the provisional support model; it does not establish steered tire contacts, terrain autonomy or calibrated physical caster behavior.

Drive, terrain and course players were rebuilt. The [20-second course stream regression](../artifacts/checks/caster-swivel-course-live.json) passed all seven checks, including the existing joint schema and zero flat suspension displacement. No full autonomous course loop was rerun for this visual/joint-feedback slice.
