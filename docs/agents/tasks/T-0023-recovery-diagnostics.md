---
id: T-0023
title: Preserve actual failed-backup arguments and bounded rejection stages
status: changes-requested
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0023-recovery-diagnostics-opus
base: 0f76a2ac6090de0cf83c8f57bd471874dbffe552
candidate: 8400c991f7f497e54d06971e23e76c5fc8b16f83
claim: tested
lease: none
updated: 2026-10-05
---

# T-0023: Own recovery failure evidence end to end

## Packet

- ADR011 complete bounded ownership: choose design, implement, test, revise and commit
  without intermediate approval. Existing interactive Opus, own prepared worktree
  C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM.
- Read README, knowledge sensor-led-navigation and trial-audit-promotion, task T0022
  accepted diagnosis and artifacts/agents/T-0022/REPORT.md plus comparison.json.
  Exact source inputs: tools/recovery_policy.py select_backup_recovery and
  _accept_continuation; tools/sensor_course.py recovery branch and existing capture
  mechanisms; directly relevant existing tests. Do not load full logs/CAD or WORLD.
- Outcome: a failed legacy backup search must report where and why it returned
  None, and bind those diagnostics to the actual immutable arguments given to the
  worker process. Preserve successful searches' existing motion result.
  Submission-time planner captures are not sufficient recovery provenance.
- Choose a minimal backward-compatible diagnostic transport that works across
  ProcessPoolExecutor. Keep existing select_backup_recovery return contract for
  current callers. Capture actual observed cost grid, pose/frame/stamps, sparse GPS,
  chosen guidance, footprint, forward options, search limits and optional masking/
  trap inputs if applicable; record explicitly unavailable fields rather than infer.
  No course/WORLD geometry. Exact captured arrays/options must match search inputs.
- Bounded diagnostic output: input/validation failure; initial clearance failure;
  blocked rear distance; per-candidate proposal/continuation acceptance or rejection;
  time/expansion exhaustion; actual attempted distances and charged budget.
  Default has five distances. Cap diagnostic payloads, nonfinite-safe JSON and
  bounded capture count; do not log full maps in run.json. Explain costs/overhead.
  Any capture failure must be explicit and must not silently bypass safety gates.
- Owned files: tools/recovery_policy.py; tools/sensor_course.py only recovery
  instrumentation/invocation/report/fingerprints; new tools/recovery_evidence.py
  and tools/tests/test_recovery_evidence.py if useful; directly relevant existing
  recovery tests. No T0021 behavior or recorder changes, ROS interfaces, runner,
  auditor, Unity, profiles, thresholds, planning rules, scoring or motion changes.
- Tests must exercise real branches and transport/serialization where possible,
  comparing original successful/failed return semantics, immutable input binding,
  empty/invalid/unknown/rear-blocked/no-continuation/exhausted cases, diagnostic
  size/nonfinite handling. Do not add source-string tests as evidence of behavior.
  If capture can't prove recovery inputs, state the gap and fix the design.
- T0024 control lap is reserved in DIFFERENT frozen checkout at this same source.
  Light reading/design/source authoring may overlap its exclusive lease; no tests,
  replay or builds until primary
  artifacts/iterations/2026-10-05/replacement-control-1/live.json is finished with
  shutdown_verified=true, OR root explicitly releases this prerequisite.
  Then proceed directly with focused checks without awaiting another permission.
- <=40min active work plus live wait; <=3 focused invocations, no full suite/live/
  Unity build/provider calls/recursive workers. Own-branch commit, bounded report
  and review-inputs.md in primary artifacts/agents/T-0023, <=300word handback with
  exact candidate, tests, overhead and unverified live behavior. No fix/performance
  claim for the failed lap. Stop at handback or genuine boundary.

## Handback

claude-opus-5-5. Candidate 8400c991f7f497e54d06971e23e76c5fc8b16f83 (base 0f76a2a), 4 files +549/-24.
Report: artifacts/agents/T-0023/REPORT.md; review-inputs.md and measurement.jsonl staged.

```text
Design: select_backup_recovery gains optional trace=None (default result and contract unchanged). Bounded
  stage records: validation reason; initial clearance (centre outside/unknown/lethal, body); blocked rear sweep
  interval with the candidates left unattempted; time/expansion exhaustion; per-candidate proposal or
  continuation verdict (first failed condition, original lazy order) with charged expansions. Same checks,
  same order. New recovery_evidence.diagnose_backup_recovery runs in the existing spawn worker: it
  fingerprints the arguments it received (int8 grid bytes, all effective args, planner keywords) and returns
  (unchanged escape, bounded nonfinite-safe evidence). The legacy mission fingerprints what it submitted
  (binding_matches). On failure it writes the full inputs once to capture_dir (exclusive, cap 4) and a map-free
  summary to run.json and an event, before the unchanged stop. Retrace mode untouched.
Tests (after T0024 verified shutdown): 70 OK, including 10 new real-branch tests: unchanged results;
  validation; clearance; unknown/lethal rear sweep; no proposal; rejected continuation; time and expansion
  exhaustion; spawn transport digest equality; capture replay reproduces digest and trace; JSON/size bounds.
Overhead: digest of 262,144 cells median 0.094 ms (max 0.372); capture 8.4 ms (failure only); evidence ~1.5 KB.
Unverified: live ROS wiring and in-mission overhead; why a proposal is None (the planner returns no reason);
  retrace mode. No fix or performance claim for the failed lap. 2 of 3 invocations. UNMETERED.
```

## Log

### 2026-10-05T04:51:13.578594-07:00 · gpt-6-astra → all · NOTE
Prepared complete task; await explicit dispatch after branch preparation and
combined integration checks. T0024 is an unchanged-source off-mode control.

### 2026-10-05T04:52:12.506981-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
T0021 is integrated and all610 combined tests pass. Your clean existing worktree
now has codex/t0023-recovery-diagnostics-opus at0f76a2a. Own this entire new
bounded instrumentation slice; choose design and tests without interim approval.
T0024 is starting now in the different frozen checkout. Light authoring permitted;
wait for its verified shutdown before focused tests, then proceed automatically.
Return one completed source candidate or a supported boundary, not a design-only
handoff. Do not weaken behavior/limits or claim to fix the failed lap.

### 2026-10-05T04:52:22-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0023 accepted on codex/t0023-recovery-diagnostics-opus at 0f76a2a. Reading and authoring only until replacement-control-1 live.json is finished with shutdown_verified=true.

### 2026-10-05T05:00:22.398239-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
T0024 finished: shutdown_verified=true, independent player/port/lease checks pass.
Focused tests may proceed under your existing assignment, without another approval.
Control achieved6/6 and20/20 in368.77s, zero charged backups. New completion telemetry
is present; enabled T0021 remains untested. Preserve your instrumentation-only scope.

### 2026-10-05T05:00:43-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 8400c991f7f497e54d06971e23e76c5fc8b16f83 (4 owned files). A failed legacy backup search now records where and why it returned None (validation, initial clearance, rear sweep interval, exhaustion, per-candidate verdicts with charged budget). The worker digest of the inputs it received is bound to the submitted digest, and the full inputs are written once to capture_dir before the unchanged stop. 70 focused tests OK; overhead measured (digest <0.4 ms, capture 8.4 ms on failure only). Live wiring is unverified. No fix claim. See the Handback section. Stopping.

### 2026-10-05T05:04:45.641208-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW
relayed-from: artifacts/agents/T-0023/root-review-r1.md

Root review, candidate8400c991f7f497e54d06971e23e76c5fc8b16f83.
Reproduced evidence-binding bug: describe_search_inputs uses _grid_digest's
{'unavailable':'TypeError'} as a hashable stand-in for the actual grid. Two
different finite float grids with otherwise identical arguments yield the same
NON-NULL digest, so binding_matches can assert equality without hashing cells.
Example grid2x2, resolution0.1, origin(0,0), robot(.1,.1), yaw0, destination(1,1),
footprint(-.1,.1,-.1,.1): costs[0.,0.,0.,1.25] versus[0.,0.,0.,2.25].
Both grid digests unavailable:TypeError, both outer digests identical/non-null.
Real ROS OccupancyGrid int8 works; this is a provenance/incomplete-input bug,
not a demonstrated live motion bug. Return explicit unavailable binding or
a complete lossless encoding, never a false exact-equality proof.

### 2026-10-05T05:04:45.641208-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Revision round1: correct the binding guarantee within existing owned paths.
Failed/unrepresentable grid hashing must not result in a non-null digest that
can mark two unknown inputs equal. Add a meaningful two-distinct-grid regression,
including continuation grid; keep valid int8 binding behavior and search result.
Also ensure the capture represents partial positional arguments or explicitly
rejects/marks that capture unavailable (current mission partial has none, but
the helper claims complete effective inputs).
Sonnet's initial code review is still running and will be relayed on completion;
incorporate any additional material findings before final handback. No tests
need a lease now. Up to3 focused invocations/25min, no live/fullsuite/build/provider.
You own design and implementation; proceed without another approval.

### 2026-10-05T05:05:58.032584-07:00 · claude-sonnet-5-5 → claude-opus-5-5 · REVIEW
relayed-from: artifacts/agents/T-0023/sonnet-review-r1.md
Candidate8400c991f7f497e54d06971e23e76c5fc8b16f83. Exactmodelverified; USD0.2192594 API-equivalent.

**Verdict: conditional accept.** I found no safety regression in `recovery_policy.py`. The remaining issues are all in the mission wiring and capture path, which is the part that hasn't run live.

**What holds up**
- `blocked()` keeps the original checks and order. Unknown cells (`<0`) are still blocked, and no mask is added.
- `_continuation_verdict` keeps the original order, and each condition is still evaluated lazily. The eager `metrics` only does `.get`, with no comparisons.
- The `return None` / escape-dict contract is unchanged.
- `describe_search_inputs` binds the signature, applies defaults and hashes both grids. It canonicalizes `partial.func`, `.args` and `.keywords` (including `frozen_guidance`), so the planner is covered in code.

**Ranked findings**
1. **Context construction is unguarded.** `recovery_context` (`latest['odom'][1]`, `latest['grid'][0]`, `stamps`, `radius`, `cursor`, `recovery_budget.report()`) is built outside any `try`, before submit. A missing key or name raises on the safety path and changes the stop reason, which contradicts "evidence only". Wrap it. Also confirm `latest['grid']` is the same grid as `recovery_grid`. Otherwise the recorded age and stamp can misdescribe the grid actually searched.
2. **Capture is not exact and can fail on the bad inputs it should record.**
   - `payload['arguments']` and the planner `keywords` are dumped raw with `allow_nan=False`. A NaN pose (the `invalid_inputs` case) or a non-serializable guidance value makes the capture fail.
   - Tuples become lists and dict keys become strings, and `_canonical` erases those differences. So "replay reproduces the digest" does not prove replay behaves identically.
   - `partial.args` is dropped from the capture although the digest includes it.
   - No test uses a real `frozen_guidance` dict.
3. **`check_live` now runs after the capture write and event.** Original order was result, `check_live`, raise. Failures in the block are swallowed, but a gzip write on slow I/O delays the liveness check. Either move `check_live` first or document the order change.
4. **The fingerprint is not tested where it matters.** Tests only mutate one grid cell and `max_expansions`. Nothing varies planner keywords, `frozen_guidance`, `continuation_costs`, `trap_regions` or `goal_footprint`. The spawn test uses a planner with no frozen guidance. `json.dumps(default=repr)` also lets sets or address-bearing reprs produce false `binding_matches=False`.
5. **Trace cap is silent.** `_note` hardcodes 32. With many distances the final record is dropped, `returned_stage = trace[-1]` goes stale, and `trace_records` can never exceed 32. Also, `returned_stage` is `search_ended_without_escape` after any budget break and `candidate` on success. The event should log the terminal reason instead.
6. **Capture and binding are not linked.**
   - The capture is written even when `binding_matches` is false, and nothing records whether the capture digest equals the worker digest.
   - `MAX_CAPTURES` is moot, since the mission stops after the first failure.
   - Verify `args.capture_dir` exists and `Path` is imported in `sensor_course.py`, because the `except` would turn a `NameError` or `AttributeError` into a silent "failed:".
   - Verify `state['recovery_failures']` reaches `run.json` on the `RuntimeError` exit.
   - `recovery_context` floats are not `json_safe`'d in the run.json copy.
7. **Timing.** The worker fingerprint runs before the search's `started`, so it counts against the 8 s deadline but not the 5 s search budget. The report's "inside the 8 s deadline" is accurate but easy to misread.

**Scope.** I have no reason to doubt the 70-test count. The 10 new tests match the report. Scope claims are appropriately limited: no live wiring and no causal fix claim.

**Before live use:** fix 1, 2 and 4, and decide on 3.
### 2026-10-05T05:05:58.032584-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
Consolidate Sonnet's material findings into the SAME revision1 already granted.
Preserve the original liveness check before potentially slow capture I/O. Guard
diagnostic context failure and sanitize the map-free run record. Bind capture to
submitted AND worker digests explicitly; unavailable must not be represented as
equal. Test actual frozen_guidance and relevant argument mutations/process transport.
For unsupported input/callable types, an explicit unavailable capture/binding is
preferable to an unjustified complete-replay claim; no broad serialization framework
is required. Preserve nonfinite evidence honestly or mark exactly what could not be
captured. Do not silently truncate a trace and call its last retained row terminal;
record truncation and an accurate exit reason separately.
Resolve all other points by focused tests or source-supported disposition.
Existing 25min/3focused-invocation revision bounds apply; return partial at a real
boundary rather than weakening provenance or behavior. Final Sol review is deferred
until corrected immutable candidate to avoid duplicate known-blocker review.
