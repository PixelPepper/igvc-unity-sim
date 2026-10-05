Status: all reads and both checks are done, and one experiment is queued. Here is the report.

# Sonnet 5.5 review: perception and observation integrity

**Model:** claude-sonnet-5-5, Claude CLI, high effort as assigned. No fallback model was used.
**Baseline manifest SHA-256:** `77f2ebe7…19b1fa`. Both check outputs report this manifest hash, so it matches.
**Read:** `surface_projection.py`, `point_memory.py`, `lane_node.py`, `surfaces.py`, the three perception tests, `tools/tests/test_point_memory.py`, the fixture metadata (first 120 lines), `oriented-entry-paint-truth.json` and the first 100 lines of the planner diagnosis.
**Not available:** `terrain_history.py`, `lanes.py`, launch/config values for `point_ttl`, and the acquisition frames. I computed no per-file hashes myself.

## Findings

**1. The 8 px support radius lets projected paint float above ground and shift along the viewing ray.**
- **Severity:** High. **Confidence:** supported. I derived the mechanism from code and the evidence geometry. It is not an acquisition-level reproduction.
- **Where:** `surface_projection.py:94-95`, with the radius check at `:90`.
- **Trigger:** A white pixel `q` has no depth sample of its own. The code takes the nearest eligible ground sample and scales the ray through `q` by that sample's optical Z. It never intersects the ray with the ground. Depth samples are stride 4 on 320×240, which is about 8 RGB px apart (`surfaces.py:37`), so the 8 px radius is roughly one grid cell.
- **Why it grows with range:** On flat ground, Z changes by about z²/(f·h) per pixel. With f=471 that is about 0.05 m/px at 6 m (camera height h assumed ≈1.4 m). Eight pixels of neighbour offset therefore gives a ~0.3–0.4 m radial error. Z error is roughly Δz·(h/z).
- **Evidence match:** The two retained points sit at Z=+0.141 and +0.076, with in-plane offsets of 0.396 and 0.142 m from paint (`oriented-entry-paint-truth.json`). The Z/offset ratios of 0.34–0.48 imply a ray depression of about 18–26°. That is a ray toward the camera, not random noise. The real-paint control row (cell 220,255) has Z=−0.002 and distance 0.006 m. A nearer-than-true neighbour gives +Z, a farther one gives −Z, so the error is symmetric. Only the +Z side registers as a body-height hazard.
- **Actual vs expected:** Expected output is on the ground surface within the stripe half-width (0.06 m). Actual output can be about 0.4 m off paint and 0.14 m above ground.
- **Smallest correction:** Intersect the query ray with a local plane fitted to at least 3 non-collinear eligible samples within the radius, with a small residual (about 1.5 cm). Reject if fewer samples fit, if an occluder is present, or if the ray is near-grazing. A cheaper fallback is to reject any output farther than about 0.15 m (3D) from its supporting sample. The fallback loses far paint, whereas the local plane keeps it, including on ramps.
- **Falsifying test:** See the regression design below. The queued experiment is the acquisition-level test.

**2. Temporal confirmation measures repetition, not independent viewpoint.**
- **Severity:** High. **Confidence:** supported.
- **Where:** `point_memory.py:50-53`.
- **Trigger:** Confirmation needs 5 distinct stamps spanning 0.4 s. A stationary or slow robot re-projects the same view-dependent bias into the same 7.5 cm cell every frame. The cell is keyed on the already-biased XY (`lane_node.py:185-187`).
- **Evidence:** The spurious point has 6 observations (6 frames, just over the threshold of 5), and the other has 16. The control paint point has 75. Once confirmed, a point lives for the full `ttl` (about 94 s here). Tests use 1200 s, but I did not read the production value.
- **Impact:** A single short view can plant a 20-minute-class ghost. Real paint is later re-observed from other poses in its true cell and survives. A biased point lands in a different cell from each pose and is never reinforced.
- **Smallest correction:** Make confirmation require parallax. For example, require at least 2 distinct acquisitions whose camera positions differ by ≥0.5 m or whose bearings differ by ≥10°. Keep candidate-only exposure for single-view points.
- **Falsifying test:** Feed 6 frames from an identical pose at 0.1 s spacing. Currently this confirms. Expected: stays a candidate and expires in 3 s. Feed the same cell from two distinct poses. Expected: confirms.

**3. Memory has no contradiction path.**
- **Severity:** Medium. **Confidence:** proven by code, since there is no negative-evidence code. Whether it mattered here is a hypothesis.
- **Where:** `point_memory.py:31-35`. Only age expiry exists.
- **Impact:** Fresh unoccluded ground-eligible samples showing no white mask at a retained cell cannot remove it. One retained point sits about 0.8 m behind the final pose, out of the camera's forward view. I did not establish that its frame was in view earlier, so this is unproven for it.
- **Smallest correction (hypothesis):** Add near-range negative evidence only. Require the cell to project into the image at under 3 m, with an unoccluded eligible sample within about 2 px and no mask pixels within a dilated radius, then decrement the count. This is not blanket age erasure.
- **Falsifying test:** A ghost point is placed, then seen from 1.5 m with no mask. Expected: removed. A real thin stripe at 1.5 m in the same cell with the mask present must stay.

**4. Test gap.**
- **Severity:** Medium. **Confidence:** proven.
- **Where:** `test_surface_projection.py:26-29`.
- **What the tests do:** `test_query_ray_uses_local_observed_depth` asserts the unbounded approximation on a fronto-parallel point, and the sloped test queries exact sample pixels. Neither compares the output to the true ray-ground intersection on grazing ground, so the passing suite cannot detect finding 1.
- **Falsifying test:** The regression below.

**5. The planner blocker was partly caused by perception, but attribution is incomplete.**
- **Severity:** Medium. **Confidence:** hypothesis.
- **What is known:** Of the three blockers, two are retained off-paint points and one is real paint.
- **Limitation:** The truth file itself notes that attribution is geometric proximity, not pixel origin.
- **Not established:** Fixing perception alone would clear this trap. That needs the final-pose replay with those points removed.

## Regression design (synthetic, no WORLD at runtime)

**Setup:**
- Camera at (0,0,1.4), pitched 20° down, f=471, 640×480.
- Flat ground z=0. Ground samples are placed on an 8 px raster with the ground flag set.
- Paint queries are placed at 4 px from the nearest sample, at ground ranges of about 2 m and 6 m.

**Expected (after fix):** At 6 m the output is within 0.03 m of the true ray-ground intersection, with |Z|≤0.02, or the point is rejected.
**Actual (current code):** I predict an error of order 0.3–0.4 m and Z up to about +0.1. I did not run this test.

**Negative controls (must still project):**
1. A query at an exact sample pixel.
2. Near paint at 2 m, error ≤0.03 m.
3. A 15° ramp, eligible, with paint at ramp height +0.008. The output lies on the ramp plane within 1 cm, so a global-plane flatten is rejected.
4. A crease or ramp edge. The fit must not interpolate across the crease, so it rejects or uses one side.
5. The existing barrel cap, which stays rejected.

## Tests actually run

| Check | Exit code | Result |
|---|---|---|
| `perception` | 0 | 14 tests OK (surface_projection, recorded_lane_projection, point_evidence), manifest `77f2ebe7…` |
| `replay-oriented` | 0 | `status: no_route`, guidance `broad_gps`, `plan_diagnostics: null`. It replays old observations with frozen code and may not be the original source revision. |

Passing tests do not refute finding 1. They show the existing tests do not exercise it. Neither check touches point memory, and `tools/tests/test_point_memory.py` was read but not run.

## Requested experiment (queued, offline)

Replay the unchanged `lane_pixels` and `project_observed` on RGB acquisitions 135.500 s and 140.150 s. For each point, compare the query pixel, the matched sample, its pixel distance and Z, and the ray-versus-local-plane intersection. If those frames were not recorded, report that and stop.

## Remaining uncertainty and next step

I did not verify the production TTL, the ground-to-RGB stamp skew limits, or the camera height. These are assumed in the range estimates.

**Next step:** Run the queued experiment. If it confirms, implement a local-plane projection with a metric support bound, add the regression above, and then consider parallax confirmation.

---

## Summary (≤300 words)

**Main finding (supported, not reproduced from an acquisition):** `project_observed` (`surface_projection.py:94-95`) projects each white pixel with the optical Z of the nearest eligible ground sample within 8 px. It never intersects the query ray with the ground. Depth samples are about 8 RGB px apart, and the Z error per pixel grows with the square of range (about 0.05 m/px at 6 m). Eight pixels of neighbour offset therefore gives a ~0.3–0.4 m shift along the viewing ray, toward the camera and above ground. The two off-paint retained points fit this: Z=+0.141 and +0.076, offsets 0.396 and 0.142 m, and the implied ray depression of 18–26° is consistent between them. The real-paint control row has Z≈0 and 0.006 m error.

**Compounding code gaps (proven):**
- Confirmation at `point_memory.py:50-53` needs only 5 distinct stamps in 0.4 s. A stationary view repeats the same bias into the same cell, and the spurious point has 6 observations.
- Memory has no contradiction path, only age expiry.
- The projection tests never compare output to the true ray-ground intersection on grazing ground, so all 14 tests pass despite the defect.

**Smallest fix:** Intersect the ray with a local plane fitted to at least 3 coplanar eligible neighbours, and reject if the fit is poor, occluded or near-grazing. This keeps real paint and ramp markings. A fallback is a metric support bound of about 0.15 m. Separately, require parallax for confirmation.

**Checks run:** `perception` (exit 0, 14 tests OK) and `replay-oriented` (exit 0, `no_route`, `plan_diagnostics: null`). The baseline manifest `77f2ebe7…` matched.

**Experiment queued:** An offline replay of acquisitions 135.5 s and 140.15 s to test the mechanism directly.

**Unproven:**
- Whether these ghosts alone blocked the final trap.
- The production TTL and camera height.
- Whether any acquisition-level reproduction exists.