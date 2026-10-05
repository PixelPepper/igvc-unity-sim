# Offline sensor-run course judge

`tools/audit_sensor_run.py` evaluates recorded axle poses against the WORLD
manifest after navigation finishes. `tools/course_judge.py` is privileged scoring
code. Neither its geometry nor its progress may enter mission control. The
judge ignores `guide_route_xy`, generated guide checkpoints, and guided reports.
This is ideal fixture evidence; it does not certify hardware or 2027 rules.

```powershell
# Use the configured Python interpreter on Windows.
python tools/audit_sensor_run.py --run artifacts/courses/seed-2027/native-sensor-run.json `
  --course artifacts/courses/seed-2027/course.json `
  --output artifacts/courses/seed-2027/native-sensor-audit.json
```

The CLI computes SHA-256 of the exact evaluation manifest bytes. The recorded
`sim_status` must contain Unity's `course_hash=<64 lowercase hexadecimal chars>`
or the run must carry the same hash as `course_sha256`. If both exist, every hash
must match. A seed or filename alone cannot establish identity. Direct Python
callers must pass `audit(..., course_sha256=<exact file-byte hash>,
mission_sha256=<exact mission file-byte hash>)`. The CLI also hashes the exact
`autonomy.json` bytes (or explicit `--mission`) and compares the run's recorded
`mission_sha256`. Historical
reports without this binding remain readable but are explicitly `uncertified`
and cannot pass.

October 1: `geometric_full_loop_certified` preserves the geometry-only result.
`passed` and `full_loop_certified` additionally require matching mission identity,
valid latest processing evidence and verified health over the mission interval.
The original schema-1 telemetry cannot prove the entire interval: its recent events
are bounded and its health summary is only the latest observation. Such reports
are explicitly `uncertified`, even when all geometric checks pass. Individual
paint, topology and ramp results remain available. Implementing an interval
health recorder is an open gate, not permission to interpret missing evidence as
healthy. A legitimate gap with `lanes.valid=False` is distinguished from a failed
lane-processing health Boolean.

Whole-footprint paint scoring reconstructs the Unity rendered 0.12 m wide
mitered stripe quads. A segment exists only when both WORLD endpoints have
`painted: true`; transitions and actual unpainted gaps are honored. The
asymmetric axle-relative rectangle is `x=[-1.1,0.6], y=[-0.5,0.5]` metres.
Translation plus maximum corner radius times rotation bounds each sweep.
Interpolated subdivisions have at most 0.02 m corner motion; endpoint clearance
minus half the bound proves continuous clearance. A 1 mm conservative allowance
covers single-precision rendering vertices. Contact or an unproven interval
fails. Paint certification does not rely on `line_blocks=0`.
Spatial indexing caps evaluated pose clearance at 0.02 m, sufficient for the
sweep proof; the reported lower bound is conservative rather than an exact
minimum distance when the robot remains farther from paint.

Loop scoring starts within 0.4 m of the WORLD centerline's first point and
requires travel in its array order. Initial robot yaw is not prescribed.
Projection is constrained to the reachable local unwrapped arc interval:
maximum arc movement is 1.5 times measured XY displacement, with no additive
per-sample progress credit. Closed endpoints and nearby branches cannot award
an immediate lap. Physical positive-direction cross-section crossings, spaced
at most 2 m apart, must occur in order and within their lateral extent.
Completion also requires reaching the final 0.4 m of arc and returning within
0.4 m of the WORLD origin. Reverse recovery is allowed; a reversed lap fails.

Marked lateral extent follows interpolated WORLD `half_width`. Unmarked areas
use an explicit **development scoring tolerance** of 8 m from the centerline;
`--open-area-lateral-m` exposes that policy. This accommodates open-area barrel
detours, but it is neither an official rule nor a proof of a unique mathematical
homotopy within a wide gap. Larger detours remain uncertified under that policy.
Ordered physical gates and locally reachable projection remain required in
gaps. Six broad destination visits alone do not establish a loop. The policy is
reported in `world_topology.policy` for review, and can be tightened offline.

Ramp evidence reports the legacy axle entry-to-exit check separately from
`ramp_body_containment`. Body scoring requires approach before the leading
corner enters, side containment while the XY rectangle overlaps the ramp, and
departure after its trailing corner clears the exit. Side clearance uses the
same conservative interpolated sweep bound. Body or axle passage does not
prove wheel support: the rectangle is not the physical wheel-contact polygon.
Wheel support, body height/pitch, suspension, traction, rollover and contact
physics remain explicitly uncertified (`wheel_support_certified: false`).

`passed` now requires identity, existing destination/mode/status/motion checks,
obstacle clearance, independent paint clearance, ordered WORLD loop, axle ramp
traversal and body ramp containment. Existing report keys are retained.
`topology_certified` and `paint_crossing_certified` also require identity,
continuous timestamps and valid speed evidence; `full_loop_certified` requires
the complete audit to pass. Missing geometry, unsupported corners and overly
large sweeps fail closed. The judge assumes linear XY translation and shortest
yaw interpolation between recorded poses; timestamp gaps cannot be certified.

Focused behavioral fixtures are in `tools/tests/test_sensor_run_audit.py`.
They cover a complete loop, paint gaps, side/corner intersections, rotation and
translation sweeps, false region-only completion, shortcuts with and without
paint, reversed traversal, course mismatches, timestamp gaps, and axle/body
ramp differences. A passing synthetic fixture is not a live autonomy lap.

New runs also record `mission_health_interval` from `tools/mission_health.py`.
The ledger starts before autonomy is enabled and ends after managed shutdown
commands. A steady wall-clock timer samples lane/depth processing status every
0.1 s. Acceptance requires all samples to pass, at least two distinct samples,
and no first/interior/tail sampling gap over 0.25 s. Failures and unknowns stay
latched even after the bounded event history rolls over. The audit binds the
ledger to odometry indices and rejects motion outside that monitored interval.
This establishes sampled processing coverage under that gap bound, not
continuous health, accurate perception or physical safety between samples.
