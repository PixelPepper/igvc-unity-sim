# observed_mouth_20261005.json.gz

This is an observation-only regression input for the T-0008 body-aware mouth handoff.

- **Source:** decision snapshot `artifacts/iterations/2026-10-05/health-baseline-r2/decisions/00080.json.gz` (ignored
  local artifact). The snapshot's sha256 is `2063eed3e14287e5d483ed35c4569fca1ddb6ffe141b3e5ce5b1ff4f113108e5`. It
  comes from the T-0006 baseline run, recorded with source `e10315337a488f5efee64d8023f47a9151f95244`.
- **Kept, unchanged from the snapshot's `input`:** `origin`, `resolution`, `width`, `height`, `costs` (the rolling
  observed grid), `robot_xy`, `robot_yaw`, `destination` (the broad GPS destination), `lane_points` (observed paint),
  `heading_hint` (the remembered observed heading) and `planner_options` (as recorded).
- **Excluded:** the snapshot `metadata` (paths, hashes, timing) and `frozen_guidance`. The fixture holds no course,
  WORLD, Reference Lab or teacher data.
- **Written** deterministically with gzip mtime 0. The fixture's sha256 is
  `80977b98f0fcb253b906795f3850a5b01a2c0d6e91b8e9363bf64b6bd1f2e75c`.
- **Recorded situation:** the robot's axle station along the observed corridor axis is 19.870 and the shared observed
  span is [21.023, 24.039]. The axle misses the lower gate (lo − 1 = 20.023) by 0.153 m. The front-center station
  (x_max 0.62 × heading·axis 0.795) is 20.363 and passes.
