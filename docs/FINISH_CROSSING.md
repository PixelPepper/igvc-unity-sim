# Finish crossing contract (`finish-crossing/1`)

The user asked that the robot only has to cross the start/finish line, not stop
on a specific point. This document defines the crossing contract. The pure
helper is `tools/finish_crossing.py`, with source-only tests in
`tools/tests/test_finish_crossing.py`. The auditor and runtime will adopt it in
separate later slices. This slice changes neither of them, so current reports
and the current mission keep their existing semantics.

## Line identity

| Field | Value | Source |
|---|---|---|
| Frame | odom = local ENU, `x_east_y_north_z_up` | public mission `origin.world_frame`/`axes` |
| Center | (0, 0) | public mission origin (lat/lon/alt → ENU origin) |
| Normal (forward) | (1, 0), ROS +X / east | fixed by contract |
| Half span | 3.0 m | fixed by contract (`FIXTURE_HALF_SPAN_M`) |

I checked that the current generator supports this definition.
`generate_course_variant.generate` builds its loop from the anchors `(0,0)` →
`(right-6, 0)`, then four bends that end at `(left+6, 0)`, and closes at `(0,0)`.
So the lane leaves the origin along +X and comes back to it along +X on `y = 0`.
The slalom shift applies only where `7 < y < 37`. `resample` pins both ends to
`(0,0)`, and `headings` forces `yaw = 0` at both ends. As a result, the
`boundaries()` paint at the origin lies at `y = ±lane_half_width = ±3 m`
(`|y-44.5| > .7`). `export_autonomy_mission` already requires every exported
loop to start and finish at the GPS origin. The line is therefore set entirely
by the public origin and the fixed +X direction. It does not use the armed
heading, the last WORLD tangent, a centerline, the teacher route or any course
file. The robot's initial and final headings play no part in the decision.

Limitation: the mission JSON does not carry the half span. It is a protocol
constant that matches the generator's 6 m lane. A course that is not straight
along +X through the origin, or whose half width there is below 3 m, cannot use
this contract. The audit must reject such a course explicitly (see below) and
must not fall back to another line definition.

## Reference point

The crossing point is the canonical `base_footprint` origin, which is the
driven-axle center. The audit's asymmetric footprint `x=[-1.1,0.6]` is measured
from this same point. The decision does not use the body: the front of the body
is 0.6 m past the line when the axle crosses. Body, paint, corridor and ramp
checks still apply on their own terms, so a crossing at a 2.5 m offset passes
this contract even if a body-paint check fails.

## Decision (`FinishCrossingTracker.observe(stamp_s, x, y, eligible=...)`)

Each sample gets a deterministic decision. The tracker credits at most one
crossing, and it latches (`already_crossed`) after that. Here, `along` is the
displacement along the normal, and a point on the line (`along == 0`) counts
as behind it. Gates are checked in this order:

- `invalid_sample`: a value is non-finite, not numeric (bools included), an int too large for a float (for example `10**400`), or `eligible` is not a bool. The same outcome applies when finite but extreme values overflow the projection, interval or step arithmetic (for example `x` jumping from `-1e308` to `+1e308`). The tracker drops the previous sample and disarms. Overflowed intermediates are never recorded, so decisions and reports never contain inf or nan.
- `already_crossed`: a crossing has latched. A malformed sample still reports `invalid_sample` first.
- `first_sample` / `continuity_restart`: there is no continuous predecessor. A sample like this never arms the tracker and never crosses.
- `discontinuous_interval`: `dt <= 0` or `dt > 0.5 s` (the audit's gap limit). The tracker breaks continuity and disarms.
- `step_too_long`: displacement > 1.2 m (absolute bound). The tracker breaks continuity and disarms.
- `speed_too_high`: displacement > (2.2 + 1e-6) m/s × `dt`. This checks the actual speed over the interval, so a 0.22 m jump in 0.01 s (22 m/s) is rejected even though it is inside the 1.2 m bound. The comparison does not divide, so a tiny `dt` cannot produce inf. The tracker breaks continuity and disarms.
- `reverse`: `before > 0 >= after`. The tracker disarms.
- `stationary` / `no_crossing`: no `before <= 0 < after` transition. The outcome is `stationary` when the step is <= `MIN_MOTION_M` (1e-6 m). An exactly stationary sample never counts.
- For a forward transition, the tracker interpolates the crossing at `f = -before/(after-before)`, records it as a candidate and disarms. Then:
  - `tiny_jitter` if the step is <= `MIN_MOTION_M` (1e-6 m).
  - `ineligible` if the first five destinations have not been visited in order.
  - `not_armed` if no eligible, continuous sample has reached `along <= -1 m` with `|lateral| <= 3 m` since the last disarm.
  - `outside_span` if the interpolated `|lateral| > 3 m`.
  - `crossed` otherwise.

There is no heading, direction-cosine or alignment requirement. Any forward
crossing within the line span counts. `direction_cosine` is recorded as
provenance only.

Every forward candidate records its provenance: sample indices, interpolated
stamp, x/y, lateral offset, before/after `along`, step, interval, speed,
direction cosine and contract version. `report()` gives the policy (including
the speed limit, allowance, minimum motion and audit tolerance) plus either
the crossing or an explicit `crossed: false`. It also keeps bounded failure
provenance. `last_outcome` holds the scalar fields of the latest decision.
`last_candidate` holds the latest forward candidate with its outcome, including
a rejected one such as `outside_span`, `not_armed` or `tiny_jitter`. The report
keeps only these two entries, so its size does not grow with the run.

These rules give no credit at startup (not eligible, and starting on the line
counts as behind it). They also give no credit when the robot is stationary,
jitters forward by at most 1e-6 m, backs up, crosses early, crosses far from
the lane, teleports, moves faster than 2.2 m/s, or crosses again after a
reversal without first re-approaching from at least 1 m behind. Crossing
anywhere within ±3 m succeeds. There is no final 0.4 m radius and no
requirement that the endpoint return to the origin.

Observation-level limitation: the tracker judges received odom samples only.
A forward odom step larger than 1e-6 m does not prove that the robot
physically moved. The minimum-motion and speed gates do not exclude sensor
noise, odom drift or estimator jumps that stay within the limits. The
contract makes no physical, noise or live claim.

## Destination 6 replacement

The first five exported destinations still need independent, ordered radius
visits. The crossing replaces only destination 6 (the origin with `radius_m` 0.4).
The caller supplies `eligible=True` only for samples after its fifth ordered
visit. The helper never computes visits.

## Audit adoption (separate slice)

The audit has to establish the same line on its own:

1. Mission origin maps to ENU (0,0) with `axes == x_east_y_north_z_up`. The course `frame == 'odom'`.
2. WORLD centerline compatibility, all with `AUDIT_TOLERANCE` = 1e-6: `points[0]` and `points[-1]` each lie within 1e-6 m of (0,0). The normalized directions of the first and last segments each match (1,0) within 1e-6 per component. The half width at the origin is at least 3.0 − 1e-6 m. If any of these fails, report `finish_contract_unsupported`, which is a failure. Never fall back to a WORLD tangent as the definition.
3. Run `FinishCrossingTracker(FIXTURE_LINE)` over the axle samples, with `eligible` set to `sample_index > visits[4].sample_index`.
4. Add new checks, `finish_line_crossed_after_ordered_visits` and `five_destinations_independently_visited_in_order`, plus a `finish_crossing` report block. Replace `returned_within_0_4_m` and the radius-based sixth visit. Replace topology's `progress >= total-.4` and end-distance ≤ 0.4 with "all gates visited, then crossing accepted". Keep the ordered corridor through the crossing sample.
5. Keep reporting `final_distance_to_origin_m` for information only.

Contract selection reads `run.finish_crossing.contract_version`. The helper's
`select_contract(run)` encodes the rule:

- No `finish_crossing` key: legacy. The report follows the old rules (`returned_within_0_4_m`, six radius visits, topology end ≤ 0.4 m). Do not reinterpret or regrade old reports.
- A `finish_crossing` block whose `contract_version` is exactly `finish-crossing/1`: this contract.
- Anything else (a block that is not a mapping, a missing version or a different version): fail closed with an error. Never fall back to legacy.

The new auditor selects the contract explicitly and records the version.

## Runtime adoption (separate slice)

The runtime remains observation-only. It uses odom `base_footprint` plus the
existing sanitized broadGPS mission (origin and goals), and it does not import
ROS into the helper. The current final goal stops at its goal radius
(`min_goal_distance`), short of a line it may never cross. The later slice
should instead do the following:

- After the fifth arrival, plan through toward `origin + 2.5 m · (+X)`. This target comes only from the public origin and the fixed normal, and it lies past the line. Feed every odom sample to the tracker.
- End the mission on `crossed`, not when the robot arrives at the plan-through target. If the robot reaches the target, or recovery is exhausted, without a crossing, log a failure and do not upgrade it.
- Keep the costmap, corridor, speed ≤ 2.2 m/s, health/freshness, identity and recovery guards. The target is a hint and must not override them.
- Record each tracker decision that changes the outcome, plus `report()`, in the mission ledger next to the existing completion evidence.

## Test status

The helper foundation tests at commit `b3c0fb9` ran from the repository root:
11 PASS. This revision changes both the helper and the tests, and the revised
tests are UNRUN. Run `python -m unittest tools.tests.test_finish_crossing`
under all three locks after the live session ends. This task changes no
auditor or runtime code, and there is no live evidence yet.
