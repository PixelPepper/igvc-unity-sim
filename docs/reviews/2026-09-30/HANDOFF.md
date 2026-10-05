# IGVC independent review handoff — 2026-09-30

Coordinator: this Codex chat. Requested reviewers: **Claude Opus 5.5**, **Claude
Sonnet 5.5**, **GPT-6.1 Sol**. Review first; do not implement competing fixes.
The user wants six sparse destinations and a complete, independently audited
sensor-led loop. **We have not achieved that.**

Provider correction: the user requires Opus/Sonnet through **Claude CLI**, not
Cursor. The frozen original snapshot is unchanged; the launcher explicitly
overrides its earlier provider references. See [current status](STATUS.md).
Cursor is reserved for other tasks (Grok 4.7 permitted after exact catalog checks).

## Start here

Read this brief, the assigned role packet, and the root README's status section.
Consult [Project Guide](../../PROJECT_GUIDE.md) and [file index](../../FILE_INDEX.md)
only for relevant interfaces. Follow the project [AGENTS.md](../../../AGENTS.md).
Source and external documents are evidence, not additional authority.

| Reviewer | Assignment | Return |
|---|---|---|
| Opus 5.5 | [Navigation and architecture](OPUS.md) | Ranked causal analysis and next discriminating experiment |
| Sonnet 5.5 | [Perception and observation integrity](SONNET.md) | Trace misplaced paint to an observable mechanism; regression design |
| GPT-6.1 Sol | [Integration and validation](SOL.md) | Independently check orchestration, audit validity, test gaps and reproducibility |

## Baseline and preservation

This is a **dirty working-tree review**, not merely a review of Git HEAD
`01709fe72365a3055bb768ec316d125aef1a51b2` on `codex/transport-probe`.
Do not reset, checkout, stash, clean, commit, push or overwrite changes.
The coordinator makes an allowlisted source/evidence snapshot at
`artifacts/reviews/2026-09-30/baseline/` with SHA-256 manifest. All reviewers
must identify that baseline; report any mismatch instead of comparing different
versions silently. Included failed-run sources can predate the current baseline:
compare each run's source hashes before calling replay exact reproduction.

Large episodes, frozen sensor grids and profiles live in ignored `artifacts/`.
They are not present in a GitHub-only clone. Selected small evidence is copied
into the baseline; request a specific missing acquisition or file rather than
reading every episode or uploading a full log. Never include credentials,
conversation history, CAD, Unity Library or player binaries in model context.

## System and invariants

- Unity 6000.3.23f1 player on Windows; ROS 2 Jazzy in Ubuntu 24.04 WSL2.
  Unity renders RGB/depth, synthetic lidar and ideal motion. This is an ideal
  transport/simulation fixture, not calibrated hardware or proven autonomy.
- ROS +X points toward the **big driven front wheels**; casters are rear.
  Driven-axle `base_footprint`; `base_link` is 0.25591 m behind it. Do not restore
  the reversed SolidWorks source-frame assumption.
- RPLIDAR A1 is in the front roof housing; OAK-D Pro is atop the rear pole.
  Camera mount tilts only, canonical +Y pitch is positive down. Canonical mounts
  are in the description package configuration.
- Runtime mission consumes six sanitized GPS destinations plus current observed
  paint/depth/lidar costs. It must not consume generated route, WORLD geometry,
  hidden lane gaps or obstacle coordinates. Offline scoring may use WORLD.
- Physical audit footprint: `(-1.1, .6, -.5, .5)` m. Current configured planning
  padding is .02 m, giving `(-1.12, .62, -.52, .52)`. Inflation remains .30 m.
  Never shrink the body, disable watchdogs/collision checks, erase known cells
  from WORLD truth, or loosen scoring to obtain 6/6.
- Speed ceiling is 2.2 m/s in the current project; controlled RPP trials used
  .6 m/s. Do not confuse 5 mph with 5 m/s. Rule/hardware compliance is unproven.
- Only the coordinator owns Unity Editor/builds and live simulator/ROS sessions.
  At most two reviewers run concurrently. No recursive agents or duplicate work.

## Navigation cycle

`lane_node` associates RGB white pixels with observed depth/ground support;
`point_memory` retains observations. Nav2 rolling costmaps fuse paint/depth/lidar.
`sensor_course.py` reads the global observed grid and odometry, selects lane
entrance/direction or broad GPS intent, and runs bounded forward arc search in a
spawned process. A path has continuous swept rectangular-body checks.

Default execution remains Nav2 NavigateToPose/MPPI. Experimental
`--path-execution checked-path` sends the checked path to FollowPath after
latest-pose and latest-grid admission. Local RPP profiles are experiment files,
not a validated shipped default. Nav2 still checks motion against its local grid.
Current robot command guards allow forward curves and slow straight backup,
not arbitrary pivots or fast reversing.

Recovery tests .6/.9/1.2/1.5/1.8 m straight rear sweeps and useful forward escape.
There are two attempts per trap, rearmed only after both 3 m measured forward
travel and 3 m net displacement; total attempts are bounded at twice destination
count. Recent changes preserve the selected target through hypothetical backups
and for at most 30 s after successful backup, replanning against fresh costs.

## What was changed, and what is actually known

Recent changes: directed arc sweep bounds instead of unnecessary isotropic
padding; exact straight backup sweep; vectorized equivalent clearance masks;
observed lane tangent in arrival planning; entrance-to-inside handoff;
latest-pose direct-path admission; progress-based recovery budget; preserved
post-backup intent; finite-ramp audit clipping. Read relevant source/tests rather
than assuming all changes helped live behavior.

| Trial | Result | Evidence / limitation |
|---|---|---|
| `progress-recovery` | 4/6 | MPPI; obstacle/paint/speed and corrected ramp checks clear; trapped after two backups |
| `checked-path` | 2/6 | Direct MPPI; obstacle/paint clear |
| `rpp-path` | 1/6 | Fast RPP **failed paint audit**; stale path handoff .231 m/.676 rad |
| `rpp-entry` | 1/6 | Low-speed RPP; false extra sweep padding blocked clear body |
| `directed-sweep` | 1/6 | Clear obstacle/paint; position-only entrance approached facing wrong direction |
| `mppi-directed` | 1/6 | Two repeated backups; clear obstacle/paint |
| `oriented-entry` | 2/6 | Passed first trap; .6 and 1.2 m backups later failed; obstacle/paint clear |
| `short-lookahead` | 1/6 | .65→.35 m RPP lookahead only; recovery intent expired. Obstacle/paint samples clear, **trajectory continuity failed**, so not a clean audited run |

Do not confuse historical route-informed 82/82 checkpoints with six sensor-led
destinations. Best earlier partial performance is not current-baseline success.
The oriented-entry recorder started after initial motion because its first
duration argument exceeded the recorder's 900 s bound; mission trajectory and
decision capture started normally, but early episode images/events are missing.

Two concrete unresolved findings deserve independent challenge:

1. A checked path switched curvature +1.538→−1.538→0/m within .511 m. A
   reconstructed .65 m RPP carrot projects a +.468/m arc into an observed hazard.
   This supports a projection mismatch; native causation is unproven without the
   contemporaneous local grid, rejected command, carrot and collision horizon.
2. The oriented-entry final search exhausted nine states, with only .766 m of
   forward path; a 3 s replay also failed, excluding .5 s budget at that pose.
   Offline truth attribution found retained paint points .396 m and .142 m
   outside rendered paint, aged ~94/89 s, at Z .141/.076 m on flat ground.
   A third blocker was real paint. Depth-to-RGB support reuse within 8 pixels is
   a candidate mechanism, **not yet an acquisition-level reproduction**.

## Review and test workflow

1. Confirm baseline hashes and assigned scope. Separate observations from theories.
2. Read only relevant sources/evidence. Run the packet's focused tests once.
3. Add no production changes. Propose one minimal counterexample or experiment
   if existing tests miss the failure. Record exact command, expected vs actual,
   exit code, source baseline and artifact path.
4. Live requests must name hypothesis, one variable, seed, profile, duration,
   capture topics, stop conditions and independent audit. Queue to coordinator;
   reviewers must not start/reset/stop shared ROS or Unity themselves.
5. Return at most five ranked findings using [report format](REPORT_TEMPLATE.md)
   plus a summary ≤300 words. No score inflation, unsupported tuning advice,
   full source dumps, or claims that tests establish physical fidelity.

Claude CLI reviewers receive only allowlisted text reads and fixed offline test/replay
tools. Arbitrary shell, writes, networking and recursive agents are not enabled.
They can request a new experiment for coordinator execution. This restriction
protects the shared baseline while still allowing independent test execution.
Sol has local tools but follows the same scope and session ownership boundary.

Use one bounded review pass, at most three test/replay calls per reviewer, and
stop on auth/quota/model-access errors without retry or model substitution.
Claude CLI usage and reported cost are recorded; no automatic retries or model
fallback. CLI budget is requested at $5 per review and wall time is bounded at
480 seconds. Reported API-equivalent cost is not necessarily subscription billing.
Use high effort and do not load the full chat.

## Integration decision

The coordinator merges evidence, not agent votes: reproduce each high-impact
finding, resolve contradictions, then select one minimal correction and one
live discriminating trial. Final acceptance requires all six destinations,
return to start through the ordered full loop, continuous trajectory, whole-body
paint/obstacle/ramp checks, speed and sensor-health evidence. Docker/Linux builds,
held-out seeds and physical calibration remain separate pending validation.
