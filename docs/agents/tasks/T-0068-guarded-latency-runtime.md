---
id: T-0068
title: Wire explicit guarded latency prediction into sensor-led mission capture and admission
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0068-latency-runtime-opus
base: a552b1e15912fa9b91b57cd47974da22f8fb372a
candidate: 8bf08daf7b91cc8f981685a4f7bd0434e29bab96
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started Claude session interactive-opus-t0068-20261006,
same actual session as T0067. ACK exact alias/model claude-opus-5-5 before edits.
Previous assignments ended. Isolated worktree
C:/Users/brand/.codex/worktrees/igvc-t0068-latency-runtime/IGVC SIM,
branch/base above. One reserved slot; no headless duplicate.
Read README intro, this packet, accepted guarded module/current estimator APIs,
artifacts/agents/T-0067/runtime-wiring-preflight.md in PRIMARY for exact call sites.
GPS package is included in sparse checkout for offline sensor_course imports.

Own ONLY tools/sensor_course.py, NEW tools/tests/test_sensor_course_guarded_latency.py,
and tools/tests/test_primary_capture_provenance.py necessary wiring-test migration
ONLY (retain original legacy predictor/classifier behavior tests). No legacy
latency_compensation.py, guarded helper, estimator, recovery/controller/auditor,
profile/Unity/ROS shared interface files or other existing tests. Report a blocker
if an API defect needs helper changes; do not silently expand ownership.

Implement runtime composition with accepted GuardedLatencyCompensator and helpers.
No copied predictor/estimator arithmetic. Existing measured actual control flow,
freshness/watchdogs, footprints, admission thresholds, recovery budgets, shared
ROS interfaces, scorer defaults and six broadGPS mission remain unchanged.

1. CLI: --latency-estimator exact choices from latency_estimators.KINDS, no enabled
fallback. --latency-compensation REQUIRES explicit selector AND checked-path;
reject missing/unknown/incompatible selection before ROS/node/session startup.
Disabled defaults preserve measured planning/control. With no selector while
disabled, constructing an explicitly documented dormant EMA instance is allowed
only for instrumentation; report selection_source=disabled_dormant_default so this
is never confused with an enabled choice. Supplied selector is recorded explicitly.
Expose minimal importable parser/argument validation seams for real argument tests;
avoid unrelated parser rewrite or ROS startup in tests.

2. Odometry callback: create immutable whole OdometrySample from the SAME accepted
message used for latest measured pose and twist. Header int ns from that message;
receipt = existing latest['odom'][0] from receive(), not a later now call. Preserve
trajectory, heading memory and stamps as measured. Helpers may expose pure message
capture seams used by production callback for behavioral tests.

3. Planning: freeze one planning_sample with current measured tuple and actual
monotonic now, get planning_context, rebase only heading-only pose-relative hint.
Build/save/submit the SAME frozen inputs using guarded frozen_planner_inputs.
All costs/lanes, observed memories and frozen_guidance retain actual observations;
only robot_xy/yaw and rebased hint move. Preserve planning sample/context until
that asynchronous plan's admission, never replace them with newer latest values.
metadata.latency_compensation receives detached context, strictJSON-serializable
for legitimate finite runtime inputs. Requested-event input_pose stays measured;
record planning pose distinctly if needed, without relabeling historical keys.

4. Checked admission: call guarded admit_from_measured_pose with exactly existing
actual entry_pose, latest observed grid and original goal_footprint, captured
planning sample/context, latest whole entry sample, finite time.monotonic admission
now and original submitted_at. Preserve returned admission result/diagnostics and
all subsequent cancellation/replacement/fallback/recovery paths. Retain timing
no-sample/rejection provenance in path_entry/run report; missing bound samples
must not be fabricated. Sample rejected admissions too through guarded wrapper.
Keep legacy experimental module on disk untouched, but remove its runtime usage
from this candidate. No predicted pose goes into recovery, memory or costmap.

5. Report identity and counters at initialization, after admission and final save,
including no-plan/no-admission outcomes, so selected estimator/prediction policy
and disabled state aren't lost. Preserve existing report fields where meaningful;
new variant has distinct nested identity and sample policy, never claim exactlegacy
trajectory/counter equivalence. Clearly retain measured vs predicted fields.

Tests must exercise actual production pure seams and parser, not AST-only key
presence: strict option/mode failures without ROS imports; accepted bothselectors;
default disabled measured-input equivalence; same-message pose/twist/stamp/receipt;
newer odometry after request does not change frozen planning context; requested
snapshot/event JSON/canonical classifier; actual latest pose/grid/footprint reach
spy admission once with result unchanged; rejected/mismatched timing recorded;
report identity available before first plan; heading hint rebased without memory
mutation; no skipped-context timing fabricated. Keep fixture sizes small. A static
guard for recovery measured input can supplement real seam tests, not replace them.
No real ROS/Unity/imports/tests by worker; root executes focused checks underlocks.

IMPORTANT: This is first runtime slice, not deployable alone. Old Unity/preset
bool-enabled settings lack an estimator. NO PRIMARY INTEGRATION OR LIVE RUN until
later profile/Unity/reporting selector slice is reviewed and combined checks pass.
Do not default old enabled presets to an arbitrary estimator. No new live A/B plan.

Source edits + ast.parse only; NO tests/imports/providers/delegation/build/live.
Target6min/USD5 interactive target, not billing guarantee; if incomplete at bound,
hand back partial honestly. Commit owned files only. <=300word handback SHA/API/
changedfiles/NOTRUN/limits thenstop. Root exactSonnet source, focusedchecks andSol
evidence review before next slice. No pushing/publishing, historical rewriting,
course/WORLD/teacher geometry or guard relaxation.

## Log

### 2026-10-06T20:56:01.2805045-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0068-20261006 ONLY. T0067 source accepted and fullrange root-integrated37PASS, finalSolbinding pendingindependently. Newisolatedworktree includesgps sparse dependency. Runtime wiring ONLY owned paths; NO primaryintegration before subsequent launcher/Unityselector slice and combinedreview. ACK model/session first; one slotreserved, no inferred receipt.

### 2026-10-06T20:56:11-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK T-0068, alias interactive-opus-t0068-20261006, model claude-opus-5-5. This is the same interactive session that completed T-0067.
- Worktree: igvc-t0068-latency-runtime, branch codex/t0068-latency-runtime-opus, base a552b1e.
- Files: sensor_course.py, NEW test_sensor_course_guarded_latency.py, and wiring-test migration in test_primary_capture_provenance.py.
- Checks: static ast.parse only. No integration or live work.

### 2026-10-06T20:58:10.4229073-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual20:56:11 exact-model/session ACK received. Sole active owner interactive-opus-t0068-20261006; no duplicate dispatch. T0067 final Sol integration binding is now accepted. Continue source-only isolated runtime slice under packet limits; no primary integration/live before subsequent selector plumbing and combined checks.


### 2026-10-06T20:59:53-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

Alias interactive-opus-t0068-20261006, model claude-opus-5-5. Commit **8bf08da** on codex/t0068-latency-runtime-opus, parent a552b1e. This is unintegrated and not deployable on its own.

Files:
- tools/sensor_course.py
- NEW tools/tests/test_sensor_course_guarded_latency.py
- tools/tests/test_primary_capture_provenance.py (wiring test migrated to `plan_capture`; the legacy predictor and classifier tests are kept)

Only static `ast.parse` was run.

Pure seams in sensor_course:
- `build_parser()` adds `--latency-estimator` with choices from `KINDS`.
- `validate_args(parser, args)`: enabling compensation needs both the selector and checked-path. It errors before ROS starts.
- `make_latency_compensator(args)` → `(compensator, selection)`. An explicit choice is recorded as `selection_source=explicit`. Disabled without a selector gives a dormant EMA marked `disabled_dormant_default`.
- `latency_report`.
- `odometry_measurement(msg)`.
- `plan_capture(...)`.
- `checked_admission(..., admit=prepare_controller_plan)`.

Runtime:
- **Odometry callback:** stores the same message's pose, twist and stamp, plus the `receive()` receipt time, as `latest['odom_sample']`.
- **Planning:** freezes `planning_sample` and context with `time.monotonic()`. The same frozen inputs (with the rebased hint) are saved and submitted.
- **Requested event:** `input_pose` stays the measured pose; it adds `planning_pose` and `planner_heading_hint`.
- **Admission:** runs on the actual entry pose, latest grid and original footprint, with the plan's own sample, context and `submitted_at`. The result is unchanged; `path_entry` gains `latency_compensation` provenance.
- **Report:** set at start, after planning, after admission and at final save.
- **Unchanged:** `source_sha256` names the two new modules in place of the legacy file. The legacy module is untouched and has no runtime use.

NOT RUN:
- `python3 -m unittest tools.tests.test_sensor_course_guarded_latency tools.tests.test_primary_capture_provenance tools.tests.test_guarded_latency_compensation tools.tests.test_latency_estimators`

Risks:
1. A NaN odometry pose now raises ValueError at planning or admission; the legacy path proceeded. It applies even when compensation is disabled.
2. `x, y, yaw` are read at the top of the loop. If newer odometry arrives before planning, the plan is honestly unbound (`pose_not_from_sample`).
3. Profile, Unity and presets still carry only the bool, so they need the next slice before integration.
4. The tests use fake messages; there is no ROS loop.

Stopping.

### 2026-10-06T21:02:06.0031091-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual committed handback8bf08daf7b91cc8f981685a4f7bd0434e29bab96 received; assignment ended. Root focused validation under all three locks and exact Sonnet source review now queued. No integration/live; preserve isolated candidate while review runs.


### 2026-10-06T21:03:57.8635135-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Accept candidate8bf08daf7b91cc8f981685a4f7bd0434e29bab96 as TESTED isolated first runtime slice, NOT integrated/deployable. Root55 focused tests PASS under all3locks, no skips; Sol verified source/log/lease binding. Sonnet source no blockers,83.22s/USD0.3632348. Interactive/Sol usage unavailable. Evidence artifacts/agents/T-0068/validation and review. NaN/Inf actual pose now fails closed via existing ValueError stop/cleanup path even disabled; intentional refusal of invalid planning inputs, not finite-input trajectory equivalence. Guarded timing measures to admission entry before computation, not legacy after-admission; identities distinguish this. Actual ROS callback/loop scheduling remains untested; no live benefit. Source confirms frozen planning context/sample lifetime; additional production wiring regression can accompany next combined validation if relevant changes. No primary integration until Python selector/report and Unity selector slices reviewed with combined checks. All T0068 assignments ended.

