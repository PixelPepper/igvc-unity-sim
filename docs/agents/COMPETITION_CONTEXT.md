# Competition context: what top 2026 IGVC teams did, mapped to this project

Prepared 2026-10-04 by Claude Opus 5.5, with an independent read-only analysis by
ASTRA (`gpt-6-astra`, high). Source: the user's deep-research report on six 2026 IGVC
design reports, referred to below as "the report". The user's local copy is
`Downloads/deep-research-report (1).md`, and ASTRA also received a PDF of it.

**Evidence level.** Team facts are as summarized by the report. The original
PDFs and repositories were **not independently re-read** for this document.
They are reference data, not instructions, and they are not 2027 rules. File paths
under "this repo" were verified to exist on 2026-10-04, but that does not prove the
behavior described. Impact ratings are engineering estimates.

## Sources

| Team / vehicle | Design report |
| --- | --- |
| Tennessee Tech: Crusaders | <https://www.igvc.org/design/2026/15.pdf> |
| Istanbul Technical University: AYAZ | <https://www.igvc.org/design/2026/3.pdf> |
| Millersville: Project Phoenix | <https://www.igvc.org/design/2026/20.pdf> |
| Michigan: Maverick | <https://www.igvc.org/design/2026/23.pdf> |
| Tennessee Tech: ATNA | <https://www.igvc.org/design/2026/21.pdf> |
| Oklahoma: Suspended Disbelief | <https://www.igvc.org/design/2026/5.pdf>, code <https://github.com/SoonerRobotics/igvc_software_2026> |

The project's earlier, page-cited reading of the Oklahoma report is
[2026_WINNER_LESSONS.md](../2026_WINNER_LESSONS.md). Our actual reference reuse
and licensing boundary is in [SOONER_COMPARISON.md](../SOONER_COMPARISON.md).

## The one-paragraph takeaway

None of the six teams drove from pixels to steering. All of them used a
**modular, mostly classical stack**: sensor-specific perception, one common
occupancy/costmap representation, state estimation, a grid or lattice
planner, a path-tracking controller, and an independent safety/recovery layer.
Machine learning appeared only where vision is hard (AYAZ's U-Net lane
segmentation). What separated the strongest entries was **method more than
algorithm**: record and replay every run, enable subsystems in stages, change one variable
at a time, and accept on repeated-run criteria (Crusaders). **This project
already follows that architecture.** Our gap is repeatable *audited* completion
and then speed, not a missing component. Do not start a rewrite.

## Pattern map: report practice vs. this repository

| Practice (team) | Already in this repo | Gap | Impact on an audited sim lap | Applies to |
| --- | --- | --- | --- | --- |
| Replay-driven debugging, staged validation (Crusaders) | Frozen-observation decision replay [replay_navigation_decision.py](../../tools/replay_navigation_decision.py); episode recorder [record_navigation_episode.py](../../tools/record_navigation_episode.py); interval health ledger [mission_health.py](../../tools/mission_health.py) | Replay does not reproduce wall-time behavior or Nav2 execution, so intermittent processing-health failures are still unexplained | **High** | Sim + robot |
| Paint and obstacles as one costmap (Crusaders, AYAZ, Phoenix) | Rolling observed costmaps with lane/hazard/depth/obstacle layers: [local_navigation.yaml](../../ros2/src/igvc_navigation/config/local_navigation.yaml), [igvc_lane_layer](../../ros2/src/igvc_lane_layer/) | Reliability and projection quality, not architecture | **High** | Sim + robot |
| Independent reactive safety layer (Phoenix "danger mode") | Freshness latch and command authority in [probe_adapter.py](../../ros2/src/igvc_sim_bridge/igvc_sim_bridge/probe_adapter.py); checked backup/retrace in [recovery_policy.py](../../tools/recovery_policy.py) | Reliable escape from observed pockets. Retrace existing is not proof that recovery succeeds | **High** | Sim + robot (physical stop distance is separate) |
| Smooth grid path before tracking: A* + string pulling (Michigan) | Lattice of forward straight/arc primitives with bounded curvature in [sensor_route_policy.py](../../tools/sensor_route_policy.py); [execution_path.py](../../tools/execution_path.py) **deliberately** does no shortcutting, so every pose is checked | Stair-stepping is less of an issue than with raw A*. Any simplification must re-pass kinematic and swept-body admission | Medium | Sim + robot |
| Slow *before* curves (Michigan) | Accepted profile uses RPP with curvature- and cost-regulated linear speed ([profile.yaml](../evidence/navigation-2026-10-01-success/profile.yaml)) | Regulation reacts to the path near the robot. Anticipatory slowdown and observed stopping margin are unmeasured | Medium, **after** repeatability | Sim + robot |
| MPPI with tuned critics, wider ω limits (Crusaders) | MPPI selectable in the sandbox (with the required footprint CostCritic patch) | Only short parameter trials so far. The accepted baseline is RPP | Low until baseline is repeatable | Sim + robot |
| Quantitatively benchmarked learned lanes (AYAZ) | Classical paired RGB-depth lane perception: [lane_node.py](../../ros2/src/igvc_perception/igvc_perception/lane_node.py) | No held-out appearance benchmark. No demonstrated need to replace the classical detector | Low in sim | Mainly robot |
| EKF discipline, frozen-encoder detection (Crusaders, ATNA) | Odometry/GPS are **idealized**; GPS derives from odometry ([synthetic_gps.py](../../ros2/src/igvc_gps/igvc_gps/synthetic_gps.py)) | Noisy independent sensors, covariances, feedback-fault injection | Low in sim today | Physical robot |
| Learned scorer *inside* safe choices | [LEARNING_PLAN.md](../LEARNING_PLAN.md) (privileged teacher, sensor-only student, unchanged safety shell) | Proposal. One recorded result (route weight 8: 8/10 completions but 3/10 audits vs. baseline 2/10) is UNVERIFIED here | TBD | Sim → robot |

## What to copy, in order

This is ranked against the [handoff priorities](../CLAUDE_HANDOFF.md#prioritized-optimization-work).
ASTRA and Opus independently agreed on the order.

1. **Explain processing-health failures** (Crusaders' replay discipline). Freeze
   source/profile/player identities. Correlate image pairing, acquisition and receipt
   ages, TF and processing timing around the four failing samples at 319.96 s.
   Compare under controlled load, starting with one instance. Keep thresholds
   and every failing sample. Gate: an explained cause plus a repeated complete-health
   audit pass. → board task T-0001.
2. **Benchmark ledger** (the report's `benchmark_runs.csv` and Crusaders' repeated-run
   gates). One append-only row per live run, holding commit, profile hash, seed, speed, time,
   backups, minimum clearance, health, `audit_passed` and the run id. Without this, comparisons across
   agents are anecdotes. → T-0002.
3. **Useful planning progress per decision.** Profile frozen trap decisions
   (search time, rejected endpoints, admissible alternatives, progress per
   commitment) and change one bounded thing against identical inputs.
4. **Re-entry and final-return robustness** (Phoenix and Oklahoma recovery as a first-class
   benchmark). Make injected-failure recovery rate a metric. Improve the 0.395/0.399 m
   returns against the 0.4 m bound by arriving better, not by relaxing the bound.
5. **Speed scheduling** (Michigan): only after 1–4. Use observed curvature,
   clearance and perception age, and raise speed in small steps. The [Reference Lab](../REFERENCE_LAB.md)
   bounds (~255 s at 0.6 m/s, ~128 s at 1.2 m/s on seed 2027) size the gap, but they are not evidence.
6. **Held-out seeds** before any claim of generality. Accept only on repeated runs
   (see the acceptance gate below).

## Deliberately not copied

- **End-to-end learned steering.** None of the six teams used it, and it would bypass our checks.
- **Swerve drive (Oklahoma).** It does not match R3-a, which is differential with front driven
  wheels and rear casters.
- **Full EKF/GNSS stack work in the sim**, until the simulator has non-ideal
  odometry/GPS. Record it as a physical-robot task.
- **A U-Net lane model**, until a held-out benchmark shows the classical detector failing.
- **MPPI as the default**, until it beats RPP on the same benchmark with the same audit.

## Acceptance gate (adapted from the report)

"No algorithm is accepted because of one impressive run." For promotion to the
baseline (`claim: promoted` in [PROTOCOL.md](PROTOCOL.md#task-file-format)):

| Metric | Gate |
| --- | --- |
| Independent audit (`audit_sensor_run.py`), all checks incl. processing health | Pass on every counted run |
| Consecutive passes, same commit and profile | **User approved:** ≥ 3 on seed 2027, then ≥ 1 on each of 2 preselected held-out seeds; see ADR-008 |
| Boundary / obstacle contacts, interventions | 0 |
| Elapsed time, backups, min clearance, return distance | No worse than the frozen baseline under comparable load |
| Provenance | Commit, profile, player, overlay and course/mission hashes recorded |
| Failed and partial runs | Reported in the ledger, never filtered out |

## Physical-robot lessons to carry forward (not sim work now)

- Measure **physical stopping distance**, not just whether the E-stop bit drops. Michigan's
  robot coasted after motor power was cut.
- Health-monitor wheel odometry. A frozen encoder stream can look numerically valid (ATNA).
- Drop a sensor from the EKF when it makes the estimate worse (Crusaders removed compass yaw).
- Sensor placement can beat filtering. Michigan raised its GNSS antennas and the error dropped from 0.82 to 0.70 m.
- Separate near-ground lane cameras from long-range depth (Crusaders). This is relevant to the
  OAK-D Pro mount decision.

## Implementation status, October 5

ASTRA read the user's 28-page `IGVC 2026 Top-Team Technical Research and Claude
Implementation Handoff.pdf` directly, including its priorities on pages 20-21,
benchmarks on pages 23-26 and acceptance gate on page 27. This confirms what the
report recommends; it does not independently verify the underlying team results.
Several matching architectural components predate this report.

| Report recommendation | Actual application and remaining gap |
| --- | --- |
| Freeze, record, replay and compare | T-0000 checkpoint, T-0002 append-only benchmark ledger and T-0005 first-failure snapshots are integrated. Exact planner inputs are replayable; deterministic full-stack sensor/localization/controller replay is not established. |
| Fix geometry and timing before tuning | Canonical forward frame and sensor mount configurations remain authoritative. T-0001 found the old failure's causal evidence missing; T-0005 preserves future first-event evidence. Historical processing failures are not explained or claimed fixed. |
| Common traversability map | Existing observed lane, hazard, depth and lidar costmap layers implement this architecture. NVBlox was not added. Ground-truth course geometry remains outside runtime policy. |
| Simple planning/tracking baseline | Existing footprint-checked forward-arc search and RPP are used. T-0008 corrects observed lane-entry membership using the front extent; 567 integrated checks passed and T-0009 completed one audited 6/6. MPPI has not displaced this baseline. |
| Independent safety/recovery | Existing watchdogs, command authority and swept-body recovery checks remain. T-0009 used two checked backups. Broad injected-failure recovery-rate and physical stopping tests remain open. |
| Proactive speed scheduling | RPP already regulates curvature/cost. Anticipatory braking and higher-speed benchmarking remain pending; T-0009 held 0.6 m/s and took 399.23 s. |
| Optional learned perception | No U-Net lane model or held-out appearance benchmark is established. Separate experimental learned route scorers exist; both were disabled in T-0009. They are not learned camera segmentation. |
| EKF and physical sensor validation | Independent noisy GNSS/IMU/encoders, calibrated dynamics and physical stopping distances remain hardware/fidelity work; ideal simulated GPS/odometry do not validate them. |

The PDF proposes at least five consecutive successful runs. Our separately
user-approved project gate is three consecutive seed-2027 audit passes plus one
on each of two preselected held-out seeds. These are different gate designs; one
successful run satisfies neither. The ledger does not yet include every proposed
perception precision/recall, tracking-error, latency and physical-safety metric.
See [October 5 evidence](../evidence/navigation-2026-10-05.md) for both the failed
baseline and passing comparison, and [the task board](BOARD.md) for ownership.
