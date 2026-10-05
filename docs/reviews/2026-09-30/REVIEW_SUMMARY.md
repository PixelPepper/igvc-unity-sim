# Integrated independent review

All three requested models completed one bounded review of the same frozen source.
Opus 5.5 and Sonnet 5.5 used **Claude CLI**, following the user's provider correction;
GPT-6.1 Sol used the built-in worker. The earlier Cursor quota failures remain
separate historical attempts. No model substitution, production edits, live ROS/
Unity session or new lap occurred. **Sensor-led 6/6 remains unverified.**

Manifest: `77f2ebe7ceaa71cb58f9d014a1e3965936ca616b823c8f2485268da79319b1fa`.
See [handoff](HANDOFF.md), [status and usage](STATUS.md), and raw reports:
[Opus](OPUS_FINDINGS.md), [Sonnet](SONNET_FINDINGS.md), [Sol](SOL_FINDINGS.md).
Raw agent assertions are review input, not all accepted conclusions.

## Verified problems

1. **Projection can displace ground paint.** The coordinator exercised the unchanged
   `project_observed` with a synthetic camera 1.4 m high, pitched 20 degrees down,
   focal length 471 px and a ground query 6 m away. An eligible ground support point
   7.9 pixels away produced **0.38657 m horizontal error and +0.09020 m elevation**.
   The exact-pixel control returned the true point to numerical precision. This
   demonstrates a limitation of reusing another ray's optical depth, not the cause
   of any particular recorded acquisition. These camera values are experiment
   inputs, not calibrated physical robot measurements.
2. **Path admission checks collision geometry but can admit a non-drivable join.**
   A robot parallel to a straight path, offset laterally by 0.08 m, was admitted.
   The first connector segment points -90 degrees while body yaw remains zero.
   An ideal differential-drive robot cannot execute that position/yaw sequence.
   This proves an entry-contract gap; it does not establish what RPP actually
   executed in a historical trial.
3. **Final acceptance lacks health/mission binding.** Sol's three synthetic controls
   still certified with missing health, failed health or a mismatched mission hash.
   Preserve geometric audit results but require separate interval-health and
   mission-identity evidence before declaring complete sensor-led success.
   [Actual negative-control results](SOL_NEGATIVE_CONTROL.json).

[Integrator results](INTEGRATOR_COUNTEREXAMPLES.json) record the first two
counterexamples and the analytical control below. The executed command was:

```powershell
wsl -d Ubuntu-24.04 -- bash -c 'source /opt/ros/jazzy/setup.bash; export PYTHONDONTWRITEBYTECODE=1; python3 artifacts/reviews/2026-09-30/verify_findings.py'
```

Exit 0; all 186 frozen files were hash-verified before imports. This was a diagnostic
experiment on frozen code, not a production fix or live-motion test. The script and
full snapshot are local ignored review artifacts; JSON results are tracked here.

## Corrections and remaining uncertainty

- **Do not use Opus's chord-sagitta estimate as a pure-pursuit tracking bound.** On
  an ideal circular path of radius .65 m, a .65 m arc-length carrot gives pure-
  pursuit curvature `2*y/(x*x+y*y) = 1/R` to numerical precision. Chord sagitta does
  not demonstrate 0.081 m tracking error. Curvature reversals, real controller
  limits and actual body deviation still warrant measured rollout tests.
- **Recovery-plan replacement is a hypothesis about repeated trapping.** The
  forward continuation helps select a backup, while subsequent planning uses fresh
  observations. The code distinction is real; its causal role needs the requested
  before/after path comparison. Do not blindly execute an old escape plan against
  stale costs, force a different heading, or increase recovery budgets based on
  the raw report alone.
- **The two historical paint acquisitions cannot currently be reproduced exactly.**
  The saved episode has 226 frames spanning 31.79–258.58 simulation seconds, but
  neither RGB stamp 135.500 s nor 140.150 s was saved. The range includes the times;
  exact acquisitions are missing because recorded images were sampled. No nearby
  frame was substituted. [Availability check](ACQUISITION_AVAILABILITY.json).
- Sonnet's proposed plane fitting, parallax thresholds and negative evidence are
  candidate remedies, not validated parameter choices. All need controls preserving
  real thin paint, sloped ramp markings, creases and occlusion. Frozen launch source
  sets `point_ttl=1200.0`, while `lane_node` defaults to 8.0; this does not prove the
  effective installed value during a historical run.
- Short-lookahead failed trajectory continuity; missing motion remains unaccounted
  for. The action-activation delay risk and configuration/build provenance gap from
  Sol still need focused investigation. No reviewer proved controller causation.

## Checks actually completed

| Reviewer | Checks | Outcome |
|---|---|---|
| Opus | Navigation unit group; oriented and directed recorded replays | 40 tests passed. Oriented: `no_route`. Directed: `route_found`, time budget exhausted at 512 expansions; counterfactual, not deterministic live reproduction. |
| Sonnet | Perception unit group; oriented recorded replay | 14 tests passed. Oriented: `no_route`. |
| Sol | Integration group; three acceptance negative controls | 37 tests passed. Negative control exited 1 because all three invalid evidence cases still certified. |
| Coordinator | Frozen projection/entry/circle diagnostic; acquisition availability | Two counterexamples confirmed; circle estimate rejected; two exact acquisitions absent. |

The named replay exit code 0 means replay execution completed, not that navigation
succeeded. Passing unit tests do not certify runtime autonomy. No test group was
rerun just to compare models. The separate launcher protocol test verified only
the three allowed MCP tools and rejection of traversal/arbitrary commands.

## Proposed implementation sequence

1. Preserve these counterexamples as behavioral regressions and close aggregate
   acceptance/provenance gaps before promoting another lap.
2. Correct projection using observed surface geometry and bounded uncertainty;
   validate ground, ramp and occlusion controls before revising long-term memory.
3. Require a kinematically feasible, fresh path entry and quantify controller/body
   tracking on curvature transitions. Test asynchronous activation delay explicitly.
4. Compare backup continuation versus post-backup replanning on recorded observed
   grids. Label changed-source results as counterfactual; never add WORLD guidance.
5. Run one controlled live trial per verified change, preserving the full footprint,
   .30 m inflation, collision guards, continuity, sparse GPS and sensor-only rules.

The next implementation phase is pending. This review does not relax acceptance,
claim physical calibration, or establish 2027 rule compliance.
