# Opus 5.5 navigation and architecture review — IGVC sensor-led loop, 2026-09-30

**Model:** `claude-opus-5-5`, Claude CLI, high effort, Fast off. No fallback model or recursive agents, and no edits or live sessions.

**Baseline:** all three checks reported manifest `77f2ebe7ceaa71cb58f9d014a1e3965936ca616b823c8f2485268da79319b1fa`, which matches the one you gave. I could not hash the files myself.

**What I read:** `trial-summary.json` (first 120 lines), both oriented-entry diagnoses (in part), `recovery_intent.py`, `path_entry.py`, `execution_path.py`, `recovery_policy.py`, `sensor_route_policy.py:1-320`, `sensor_course.py:300-559`, and `checked-path-rpp.yaml:1-120`.

**Limits:** the read budget ran out before I reached `observed_navigation.py`, `swept_footprint.py`, the tests, `rpp-short-lookahead.yaml`, `local_navigation.yaml` and the remaining trial entries. I had no contemporaneous local grid, rejected command or carrot.

## Findings (ranked)

### 1. Backup recovery does not use the escape path that justified it — High, supported
- **Where:** `sensor_course.py:466-519`, `:456`, `:365`; `recovery_policy.py:58-61, 117-127`.
- **Trigger:** `select_backup_recovery` finds a backup distance by also finding a forward plan from the backed-up pose. The mission loop then keeps only `distance_m` and diagnostics and throws `escape['forward_plan']` away.
  - The backup is straight, so the yaw does not change.
  - `preserved_guidance` keeps the same target, including for the second attempt (`:455`).
  - The robot then replans from scratch and can pick the same corridor again.
- **Evidence:** after the backups, goals 121 and 123 were straight ahead toward broad GPS (`goal_yaw` equalled the send yaw). The robot was trapped again at y=28.458, which is before the original anchor at y=28.768. It had moved only 1.52 m forward, short of the 3 m needed to rearm the budget, so recovery was exhausted with 10 of 12 global attempts unused. The planner diagnosis's own `next_fix` names the same issue.
- **Expected:** the continuation that justified the backup should be executed, or at least preferred.
- **Smallest correction:** after a backup, send the escape plan through `prepare_controller_plan` and hold it until its local goal is reached or it is rejected. A second attempt at the same trap should require a different escape heading.
- **Falsifying test:** the queued offline experiment below.

### 2. The checked path and what the controller can track do not match — High, supported (geometry); controller causation unproven
- **Where:** `sensor_route_policy.py:128-129, 161`; `execution_path.py:15-27`; `checked-path-rpp.yaml:72`.
- **What the planner produces:** paths made of 0.255 m segments with curvature κ ∈ {−1.538, 0, +1.538}/m, switching abruptly. They are checked with only 0.02 m padding. `controller_path` resamples these exactly.
- **What the controller does:** pure pursuit cuts corners. On a κ=1.538 arc, a chord to a carrot L ahead is off by about κL²/8:
  - 0.081 m at L=0.65 m;
  - 0.024 m at L=0.35 m.

  Both exceed the 0.02 m padding.
- **Recorded tracking:** cross-track error reached 0.046 m and heading error 0.173 rad (execution diagnosis, sequence 80). Because the body reaches 1.12 m behind the driven axle, that puts the rear corner about 0.046 + 1.12·sin 0.173 ≈ 0.24 m off the checked sweep.
- **Plan replacement:** direct-path goals are replaced roughly every 1.5 s (`:343`, and `:523` exempts direct paths from goal retention). Recorded goal results are mostly status 5 (cancelled), so stateful RPP keeps restarting. I have not separated controller rejection from the mission cancelling its own goals.
- **Impact:** whole-body clearance proved by the planner is not inherited at execution. Safety rests on Nav2's separate local check. This is consistent with the +1.538 → −1.538 → 0 switch and the fast-RPP paint failure.
- **Correction (a contract, not a new controller):** pick one of these.
  - Pad the planner's footprint by a stated tracking bound.
  - Or require each constant-curvature segment to be at least as long as the lookahead, with limited curvature change.
  - Or have admission simulate the controller's closed loop and sweep the body along the simulated trajectory.
- **Falsifying test:** offline pure-pursuit plus unicycle rollouts on the recorded checked paths. If the maximum body deviation stays at or below 0.02 m, this finding is refuted.

### 3. The final oriented-entry trap is a real geometric wedge, made decisive by retained paint — High, supported
- **Evidence:** `oriented-entry-planner-diagnosis.json:160-330`, plus my `replay-oriented` run (`no_route`).
- **Turning left:** blocked by front-left paint at (26.025, 29.225), aged 11 s with 75 observations.
- **Turning right:** blocked by the rear tail swing. With the turn centre on the axle line at R=0.65 m, the rear-left corner swings on a 1.62 m radius versus 1.17 m for the side, up to about 0.45 m outward. That swing hits paint retained 94 s earlier at Z 0.141 m, which sits only about 0.03 m beyond the body side.
- **Straight ahead:** only 0.766 m is available, so the 1 m continuation reserve rejects it (`sensor_route_policy.py:105`). The cells blocking the straight branch were not recorded.
- **Not the cause:** search budget. A 3 s replay gives the same result.
- **Correction:** do not loosen the body, unknown-cell blocking or the reserve. Point-memory attribution belongs to Sonnet's scope.
- **Falsifying test:** a non-shippable offline counterfactual that removes only the cells for the two elevated, aged paint points. If a plan then appears, perception is the deciding blocker. If not, the cause is navigation geometry or unknown space.

### 4. The path-entry connector can ask a differential-drive robot to move sideways or backward — Medium, supported (code)
- **Where:** `path_entry.py:20-35`.
- **Trigger:** the entry point is the nearest path *vertex*, not a forward projection. The connector is a straight line in position with yaw interpolated linearly. At 0.10 m cross-track it can point roughly 90° from the robot's heading, or back to a vertex behind the robot. The body sweep is checked, but the motion is not drivable.
- **Impact:** low in this run, since most sends had cross-track ≤0.02 m. The contract is still unsound.
- **Correction:** project onto path segments with forward progress only. Reject the entry, or join with a checked arc, when the heading of the connector itself exceeds the limit.
- **Falsifying test:** robot 0.08 m to the side of a straight path, then assert the connector bearing is within 0.15 rad of the robot's yaw. I proposed this test; I did not run it.

### 5. The orientation gate can create another local dead end — Medium, hypothesis
- **Where:** `sensor_route_policy.py:206-208` and `:227-234`; `recovery_policy.py:126-127`.
- **Mechanism:** a candidate end point must make at least 0.1 m progress toward the destination. Within 0.7 m of a lane mouth, a misaligned approach is blocked. The only valid plans left are full re-approach loops, which are rarely possible between paint lines with forward-only motion at R=0.65 m. A straight backup keeps the same misalignment, and escape progress is still measured toward the same target. The gate turns "approached facing the wrong way" into a guaranteed stall rather than a correction.
- **Not proximate here:** the final oriented-entry trap used broad GPS with `yaw=null`.
- **Falsifying test:** mouth 0.6 m ahead, 0.5 rad misaligned, 2 m of free space behind and to the sides. Expect either a plan or a backup escape.

## Tests run
| Check | Exit code | Result |
|---|---|---|
| `navigation` | 0 | 40 tests OK in 1.05 s (`test_observed_navigation`, `test_path_entry`, `test_recovery_policy`, `test_recovery_intent`). None of them covers findings 1, 2 or 4. |
| `replay-oriented` | 0 | `no_route` with broad GPS. Matches the diagnosis. The diagnosis reports that the planner-module hashes match, but I did not compare `sensor_course.py`, so this is consistent but not an exact reproduction. |
| `replay-directed` | 0 | **Counterfactual:** found a route, but stopped on the time budget at 512 expansions. The outcome depends on wall-clock time. |

## Requested experiment (queued, not run)
- **What:** an offline comparison. For each oriented-entry backup, rerun `select_backup_recovery` on the last captured grid with the recorded guidance. Compare its escape path with the first main-loop replan after the backup:
  - lateral and heading separation at 0.5, 1.0 and 1.5 m;
  - distance from each path to the blocking cells;
  - whether each path comes within 0.3 m of (26.95, 28.458).
- **Stop rule:** stop if a capture is missing; report it as missing rather than substituting. Label anything with mismatched module hashes as counterfactual. CPU time under 5 min.
- **Discrimination:** if the escape diverges but the replan re-enters the trap, finding 1 is confirmed. If they match, the cause moves to the escape criterion or to perception.
- **Follow-up if confirmed:** one live A/B trial changing only one variable, executing the escape plan (seed 2027, oriented-entry profile, same speed).

## Remaining uncertainties and next integration step
- Native RPP causation still needs the contemporaneous local grid, carrot and collision check.
- Cancelled goals versus preemption is unresolved.
- I could not identify what blocked the straight branch.
- Replays that hit the time budget are not deterministic. Use expansion-count budgets for replay comparisons.

**Next step:** settle finding 1 offline, then write the trajectory contract from finding 2 into tests before the next live trial.

## Summary (≤300 words)
Most trials end with "Backup recovery budget exhausted", and the clearest navigation-side cause is in the mission loop (`sensor_course.py:466-519`). The forward escape plan that justified a backup is thrown away. Only the backup distance is used, the yaw is unchanged and the target is preserved, so the robot replans into the same corridor. In oriented-entry it was trapped again 0.31 m short of the first trap (y=28.458 against the 28.768 anchor) after 1.52 m of forward travel, which is under the 3 m rearm threshold.

There is also a missing contract between planner and controller. The planner checks bang-bang paths of 0.255 m segments at κ=±1.538/m with 0.02 m padding. RPP corner-cutting (0.081 m at 0.65 m lookahead) and recorded heading error of 0.17 rad give about 0.24 m of rear-corner deviation from the checked sweep, so whole-body clearance is not inherited at execution. Fix this by padding for a tracking bound, limiting how often curvature switches, or rolling out the controller at admission — not by switching controllers.

The final oriented-entry no-route is a genuine wedge: real front-left paint plus a 1.12 m tail swing into paint retained for 94 s at elevated Z. Replay confirmed `no_route`, and planning budget is excluded. Perception attribution decides it.

The path-entry connector can ask for sideways motion. The orientation gate plausibly adds a stall near lane mouths (hypothesis).

Tests: the `navigation` group passed (40 tests, exit 0) but covers none of these findings. `replay-oriented` returned `no_route`. `replay-directed` found a route only as a counterfactual, after stopping on its time budget.

I queued one offline experiment, comparing each backup's escape path with the replan that followed it, before any live A/B. The six-destination goal is not achieved, and nothing here establishes it.