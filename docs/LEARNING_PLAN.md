# Learning plan — privileged teacher, sensor-only student, unchanged safety shell

Proposed 2026-10-01. Status: **proposal**; nothing below is implemented unless marked.

## Goal and the one rule

Many simulated runs should make the robot better at choosing a path in real time
on a course it has never seen, and the same loop should keep working on the
real robot. The rule that makes this transferable:

> **Training may use anything; the robot at run time uses only its sensors and
> the six broad GPS destinations.**

The full-course "oracle" (Reference Lab, `course.json`) is a **teacher** that
grades and labels decisions after the fact. It is never an input to the
running robot. This is the standard "learning by cheating" / privileged-teacher
pattern (Chen et al., 2019), combined with DAgger to fix distribution shift.

## Why a hybrid, not end-to-end learning

The current stack already has what a learner should not replace: whole-body
swept checks, freshness watchdogs, recovery budgets, and audit acceptance. What it
does poorly is **choose between safe options**: which corridor candidate,
which side of a barrel, how far ahead to commit, how fast to go. Those are
hand-weighted scores today, for example
`lane_corridor_policy._propose_lane_corridor` (`distance + .5(1-gps) - 1.5·confidence`),
`sensor_route_policy._forward_goal` node/edge costs, and a constant speed limit.
A learned **scorer** inside those choices is data-efficient, inspectable, and
safe by construction:

```
observations ─► existing candidate generation ─► HARD CHECKS (unchanged) ─► admissible set
                                                                               │
                         final score = heuristic + w · learned_score  ◄────────┘
                         (w = 0 reproduces today's behaviour exactly)
```

## The loop

```
         ┌────────────── many seeds / randomised conditions ──────────────┐
         ▼                                                                │
  run student in sim (Unity + ROS, sensor-led) ── logs decision snapshots │
         │        (observed costmap, lane points, pose, goal, candidates, │
         │         chosen action, timing, outcome, audit)                 │
         ▼                                                                │
  TEACHER labels each snapshot in hindsight (full map):                   │
   • cost-to-go of every admissible candidate (HPA* on the full map)      │
   • which obstacle side / commitment distance was best                   │
   • safe target speed (lap-time profile ∩ observed stopping distance)    │
         ▼                                                                │
  aggregate dataset (DAgger) ─► train small student on OBSERVED features ─┘
         ▼
  gate: held-out seeds, independent audit pass-rate non-inferior,
        time/backups improved under comparable load ─► promote profile/model
```

**Real robot, same loop.** The robot can't know the map before a run, but
after a practice run it has one: its own accumulated sensor map (costmap/SLAM
of everything it saw). The hindsight teacher runs on that map exactly as it
runs on `course.json` in sim. So real practice runs become labelled training
data with the same code: only the teacher's map source changes.

## Components

| # | Component | Runs where | Notes |
| --- | --- | --- | --- |
| 1 | **Decision log v2**: add admissible candidates, chosen action, search timing and outcome link to each snapshot | robot (sim + real) | Today candidates/choice live only in `run.json` plans; join is fragile |
| 2 | **Hindsight teacher / labeler** | offline (`tools/reference_lab label`) | Reuses the C# HPA*/corridor/lap-sim; input = course.json (sim) or an occupancy map (real) |
| 3 | **Robust parameter search** (Bayesian opt / CMA-ES) over allowlisted profile params across seeds | offline driver + sim batches | Cheapest transferable win; the output is a ROS profile, not a network |
| 4 | **Student scorer**: gradient-boosted trees or a tiny MLP on observation-only features (candidate geometry, observed clearance, unknown-cell fraction ahead, lane confidence, GPS alignment, heading change, recent progress) | trained offline; inference in-process with numpy from a JSON model | No GPU or torch on the robot; `w` is a profile parameter |
| 5 | **Speed governor**: v ≤ √(2·a_brake·d_free_observed) and observed curvature, then learned residual from teacher speed labels | robot | Inserts at `sensor_course.py` `/speed_limit` (`min(learned, --speed, max)`) |
| 6 | **Domain randomisation**: sensor noise, latency/dropouts, GPS noise, wheel slip, camera pitch error, lighting | Unity + bridge | Without it, anything learned overfits ideal sensors; required before real-world claims |
| 7 | **Batch runner**: N sequential trials per sandbox session, rotating seeds/conditions, automatic audit | Windows + WSL | Today's iteration harness needs a clean git tree and is fixed to seed 2027 |

## Fidelity ladder and throughput

| Tier | What | Speed | Used for |
| --- | --- | --- | --- |
| A | Offline replay of saved snapshots (no Unity) | ~seconds per decision, parallel | Scorer training/evaluation, teacher labelling, regression |
| B | Unity + ROS sandbox trials, one lease | ~4–6 min per trial, roughly 80–100 overnight | DAgger rollouts, parameter search, acceptance |
| C | Real robot practice runs | as available | Hindsight-labelled fine-tuning, validation of transfer |

Parallel Tier-B instances need a separate Unity port, ROS domain and session
directory per instance; that is later infrastructure, not a prerequisite.

## Evaluation and promotion

Held-out seeds never used for training. Promote only if the independent audit
pass rate is non-inferior and elapsed time/backups improve under comparable
load. Report failures, not just successes. Keep `w = 0` (baseline) runnable at all times. Ideal
sim results are not hardware evidence (see AGENTS.md).

## Status, 2026-10-02

Implemented and tested offline:
- **Batch runner:** `tools/sandbox.ps1 -Batch plan.json`. Plans carry `arms` or `trials` with seed, difficulty
  and settings. The launcher generates each layout; the panel swaps world and mission per trial and quits at the end.
  Report: `tools/sandbox_batch_report.py`.
- **Decision log v2:** `decisions/outcomes.jsonl`, with candidates, chosen plan, admission, action and progress
  (`tools/navigation_decisions.py`). Also a bounded startup goal retry, and a startup error that names the missing inputs.
- **Hindsight teacher:** `dotnet run -c Release --project tools/reference_lab -- label --run <run>` writes
  `artifacts/learning/labels/<run>/` (labels, summary, traps).
- **Search driver:** `tools/param_search.py search|validate|status`, with 5 offline tests. It needs
  `sudo apt install python3-sklearn python3-scipy`; until then it uses random search.

Live evidence: 9 real-time trials over seeds 2027, 2031, 2032 and 2033.
- **Success rate:** the accepted settings reached 6/6 in 3 of 9 trials, and none passed the strict audit.
- **Dominant failure:** every navigation failure was the same kind. The robot commits to the wrong side of a barrel
  group on the **west-leg slalom**, enters a pocket whose exit it cannot yet see, stalls, and the checked short
  backup cannot escape ("no observed collision-free backup" or "recovery budget exhausted"). The teacher
  identifies the wrong-side obstacle in each run.
- **Health:** sporadic processing-health failures occur without any Reference Lab load (5, 17 and 4 samples).
- **Startup failure:** one seed-2032 trial timed out waiting for startup inputs. The cause is not established;
  the error now names the missing inputs.

Implication: the largest available gain is structural (commitment and escape), not the five global
parameters. Recommended order: a sensor-legal *retrace* escape that backs out along the robot's own
recently driven, observed-free path; then the learned side-commitment scorer trained on teacher labels from
these traps. Parameter search continues as an unattended background job.

## Parallel simulations (2026-10-02)

`tools/parallel_batch.py <plan.json> --instances N` (run in WSL) splits a plan across isolated
instances. Each is `tools/sandbox.ps1 -Instance n -Hidden` with:
- TCP port 10000+n and ROS domain 60+n;
- its own `artifacts/sandbox-instance-n/`, `artifacts/session/instance-n/` and lease;
- no RViz.

Shared steps (overlay check, layout generation) run once, before any instance starts. Leaving
`IGVC_INSTANCE` unset keeps the original single-simulator paths and port.

Isolation was verified live: an instance listened only on its own port, its topics appeared only in its
domain, and every session file stayed in its own folder. Calibration on four layouts
(`tools/parallel_calibration.py`, `artifacts/sandbox/batch/calibration-summary.json`):

| Instances | 6/6 | Health fail rate | Search p50 / p95 | Lane interval p95 | Readback | Frame |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 3/4 | 0.71% | 0.195 / 0.70 s | 0.204 s | 32.7 ms | 16.7 ms |
| 2 | 2/4 | 0.29% | 0.220 / 0.73 s | 0.205 s | 32.6 ms | 16.7 ms |
| 4 | 3/4 | 0.03% | **0.328** / 0.78 s | 0.207 s | 32.5 ms | 16.7 ms |

Sensing and rendering were unaffected at 4 instances (24-core host). The wall-clock-budgeted planner
search slowed by 68% at the median.

Policy (revised after 60 runs at four instances, data round 0):
- **Two instances** for anything where outcomes matter, including A/B evaluation and success rates.
- **Four instances** only for decision-level training data, with latched runs flagged.

Why the revision: in data round 0, 9 of 60 runs at four instances ended in a **perception-freshness latch**
(`Autonomy latched off: perception freshness expired`, camera age about 0.75 s). The latches were spread across
all instances and clustered in time, which points to machine-wide load spikes. None occurred in about 22 runs at one
or two instances. The four-trial calibration was too small to detect a failure rate of about 15%. Decisions made
before a latch are still valid observed data; the run outcomes are not.

## Escape A/B and first learned scorer (2026-10-02)

**Retrace escape** (`--escape retrace`; default stays `legacy`). Balanced A/B on two instances, five layouts
(`artifacts/sandbox/batch/ab-escape-1/`):

| Mode | 6/6 | Audit pass |
| --- | --- | --- |
| legacy | 2 of 4 | 1 of 4 |
| retrace | 0 of 4 | 0 of 4 |

Retrace never executed a retrace manoeuvre. It also exposed a design bug: a trap region covered the final
destination. That bug is fixed (a stall within the goal radius is no longer remembered). Not promoted.

**Infrastructure fixes found live:**
- The supervisor's status write retry was extended from 0.25 s to 1 s; it had crashed under parallel load.
- Batches now wait 5 s to settle after a layout swap, and repeat a trial once (recorded, excluded from
  summaries) when it fails at startup because a stream or Nav2 was not ready.
- The startup error now names the missing input (it was the costmap).

**Data round 0:** 60 runs at four instances over 20 new seeds (2101–2120), accepted settings, in
`artifacts/learning/data-round-0/`.
- 31 of 60 reached 6/6; 9 passed the audit.
- 15 ended in the trap stall; 9 in the perception latch (see above).

**Learned route scorer:**
- Data: 92 runs replayed with route alternatives (fraction 0.5), labelled by the teacher.
- Model: gradient-boosted trees on 23 observed-only features, `artifacts/learning/models/route_scorer_round0.json`.
- Evaluation: 5-fold cross-validation grouped by course (27 courses), 1,590 decisions with at least 2 route options.

| | Model alone | Heuristic | Hook at weight 1 |
| --- | --- | --- | --- |
| Top-1 agreement with the teacher | 75.9% | 55.7% | 58.3% |
| Mean regret | 0.17 m | 0.60 m | 0.55 m |
| Better / worse where picks differ | 586 / 265 (p≈1e-28) | — | 58 / 16 (p≈1e-6) |

Limits:
- Offline only.
- Alternatives at the live default (0.1) are sparser than in this replay.
- The scorer covers route-search choices; lane-corridor commitments, which decide many traps, are not yet scored.
- Next: wire `--learned-scorer/--learned-weight` (kept out of snapshot `planner_options`) and run a two-instance live A/B on held-out seeds.

## Live A/B of the learned scorers (2026-10-04)

Setup:
- Plan: `artifacts/sandbox/batch/ab-learned-1/` (plus `-resume` for the 8 trials lost when a session ended).
- 10 held-out seeds (2301–2310, registered as never-train), two instances, three balanced arms.
- Models: the promoted round-0 models (route `d9b39350…`, corridor `8d05294f…`).
- Wiring: `sensor_course.py --route-scorer/--route-weight --corridor-scorer/--corridor-weight`, set from the sandbox
  settings `route_weight/corridor_weight`. The models load once and reach the planner process at submit time, never
  in snapshots. Run records hold model hashes; re-rank decisions are in the run.json plan diagnostics.

| Policy | 6/6 | Audit | Mean destinations | Lap time (6/6) | Ends |
| --- | --- | --- | --- | --- | --- |
| Baseline | 4/10 | 2 | 3.9 | 368 s | 4 trap stalls, 2 recovery budget |
| **Route w=8** | **8/10** | 3 | **5.0** | 424 s | 1 stall, 1 perception latch |
| Route + corridor 8+8 | 3/10 | 2 | 3.9 | 391 s | 5 trap stalls |

Interpretation:
- The route scorer completed every seed the baseline did, plus 4 more (2303, 2304, 2306, 2309).
- Per seed it reached more destinations on 4 seeds and fewer on 1. With n = 10 this is encouraging but not conclusive
  (exact McNemar p ≈ 0.13 for 6/6). Laps were about 15% slower.
- In one live trial it re-ranked 15 decisions and changed 9, with no errors.
- **Corridor scorer vetoed for live use** (`live_veto` in `models/current/manifest.json`). Offline gains did not transfer.
  Its teacher cost uses a straight line to the corridor entry and ignores obstacles between robot and entry.
- `run_round.py` keeps a vetoed kind at weight 0 even if a later round promotes it offline. Only a person lifts a veto,
  after a winning live A/B.

## Learning round 1 (2026-10-05)

Command: `python3 tools/learning/run_round.py --round 1 --instances 4 --seeds 20 --repeats 3` (WSL).
Report: `artifacts/learning/rounds/round-1/report.md`. Collection used the promoted policy (route w=8, corridor vetoed
to 0) on 20 new seeds (2311–2330), DAgger-style. The round was resumed twice (background time limit; export-parity
stop) without redoing finished steps.

**Collection: 20/60 at 6/6, 6 audit passes, 24 perception latches.** These success rates are not evidence about the scorer:
- Unity frame time doubled to 42 ms during one quarter of the run, because other programs were loading the machine.
- Only 5 of the 24 latched runs had slow frames, so the latch spike is **not fully explained**.
- Serializing the scorer to the planner per request was measured and ruled out (107 KB, about 1 ms).
- In the controlled A/B, each scorer arm had 1 latch in 10 against 0 for baseline. That is too few to conclude
  anything; it remains an open question.

Reports now flag `disturbed` (mean frame > 18.5 ms) and `perception_latch` per row, and count `clean_six_of_six`.
Close heavy programs before collection runs.

**Gate (fair retrain-per-fold, 47 courses): nothing promoted.**

| Kind | Decisions | Regret, new / current / heuristic | New vs current | New vs heuristic |
| --- | --- | --- | --- | --- |
| Route | 2,656 | 0.184 / 0.182 / 0.62 m | 145/129, p=0.37 | 983/455, p≈1e-45 |
| Corridor | 12,397 | 0.037 / 0.037 / 0.115 m | 982/1057, p=0.10 | 7058/3983, p≈1e-190 |

The round-0 models already generalise to the new courses. More data on the same features and labels has plateaued.
Next levers, in order:
1. A path-aware corridor teacher cost: a grid cost-to-go from the robot to the corridor entry, replacing the straight
   line, which is the likely reason the corridor scorer failed live.
2. Investigate the perception-latch rate with the scorer on and off at two instances.
3. Then another round.

**Fix:** exported trees now round features to float32 exactly as scikit-learn does. A 2e-4 export mismatch stopped
round-1 training; round-0 exports were already exact.

## Phases

0. **Live verification of the Reference Lab** (pending simulator access): batch
   A/B, baseline vs ghosts + trail, health and timing compared.
1. Batch runner (7) + decision log v2 (1) + hindsight labeler (2).
2. Robust parameter search (3) on seeds/difficulties: the first measurable gain.
3. Student scorer (4) offline on Tier A, then DAgger on Tier B.
4. Speed governor (5) and domain randomisation (6).
5. Real-robot logging + hindsight labelling from its own map.

Each phase: one hypothesis, scoped files and owners (≤2 workers + integrator,
per AGENTS.md), held-out evaluation, then documentation.
