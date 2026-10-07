---
id: T-0059
title: Label and guard reconstructed recovery comparisons
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0059-replay-provenance-opus
base: 2e1e6b8
candidate: 6affa0e7454b113d363050f6b1491576cc4ee6fa
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

Sole HEADLESS owner opus-t0059-replay-provenance-20261006T1811.
Worktree C:/Users/brand/.codex/worktrees/igvc-t0059-replay-provenance/IGVC SIM.
Root holds artifacts/agents/T-0059/implementation.lock during dispatch.
Only own tools/replay_recovery.py and NEW tools/tests/test_replay_recovery_provenance.py.
Root verified owned existing paths clean at base; external sensor_course.py/latency
edits remain outside scope. Read README intro and embedded packet; primary task
log is authoritative. No primary edits, docs edits or recursive delegation.

Implement reviewed T0058 narrow design for recovery-event reconstruction only:
* Preserve fixed one row per selected recovery_guidance_selected event. Add event
index identity because sequences can repeat; never replace a skipped event.
* Every executed row says replay_kind=counterfactual_reconstructed and
input_binding=not_evaluated, including equal stamps. Never call it live-exact.
* Strict positive int (not bool) event.grid_stamp_ns and snapshot.metadata.grid_stamp_ns.
Equal allows reconstruction with reason grid_stamp_match; differing skips with
reason grid_stamp_mismatch; missing/malformed stamps skip grid_stamp_unknown.
* Explicit --allow-grid-mismatch enables available valid snapshots with mismatch/
unknown stamps as labelled counterfactuals. Missing/unreadable/malformed snapshots
always remain skipped even with opt-in. Preserve raw stamps or explanatory safe
metadata, budget scale, status/reason, no numeric substitution/coercion.
* Snapshot acquisition/validation errors become per-event skipped rows; validate
necessary shape before planner use. Avoid a broad catch around planner execution:
unexpected planner/runtime errors must stay visible, never become missing data.
* stall_counts includes selected,executed,skipped,skipped_by_reason,by_status with
selected=executed+skipped. Existing successful legacy/retrace numerical fields stay
unchanged when admitted; document schema additions/skip semantics in module help.
* Document reconstructed options/guidance/continuation/fresh TrapMemory; matching
stamp proves neither full inputs nor equivalent live state. No digest pairing,
exactness enum, automatic capture selection or type normalization to force hashes.
* T0055 replay_controls and classifier remain unchanged. recovery_evidence exact
capture loader/producer and all runtime policy/safety inputs remain untouched.

Behavior tests use synthetic snapshots/events and mocked planners to observe
admission and exact forwarded values: equal/mismatch/missing/malformed stamps
(bool,float,zero,negative); opt-in; snapshot absent,badgzip,badJSON,badshape;
repeated sequence unique eventindices; skip counts/no replenishment; successful
legacy/retrace output unchanged and inputs unmutated; no planner calls on skipped
rows; planner exception visible. CLI test fixed selection and JSON/help fields.
Don't test mere source strings or replicate implementation predicates.

No tests/imports/benchmarks/replays during implementation: root runs focused new
suite plus test_recovery_control_pose.py and test_recovery_evidence.py under all3
simulator locks after actual commit handback. No historical files, teacher/course/
WORLD geometry, Unity/ROS/live sessions or provider calls. Preserve all failures.
Commit only two owned paths, return SHA/files/NOT RUN checks and risks <=300words.
ExactOpus5.5/high6min/USD5 taskbound, no provider-error retry/substitution.
Stop at committed handback or blocker. Sonnet source review, Sol evidence review;
root integrates only after both and tests. No publishing/pushing.

## Log

### 2026-10-06T18:13:00.915445-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Sole HEADLESS opus-t0059-replay-provenance-20261006T1811, isolated branch/worktree and implementation.lock. T0058 narrowed contract accepted by both reviewers. Worker slot now released by Sol; interactiveT0056 remains reserved without ACK. Own only two packet files, no execution.

### 2026-10-06T18:19:04.104516-07:00 · gpt-6-astra → all · HANDBACK

ExactOpus completed340.52s/USD1.4553726; candidatedd2cd0c, only two owned files, no tests/imports. Assignment ended. Root identified incorrect2-entry footprint validation vs live4bounds sensor_course.py:415. Sonnet reviews once and root runs focused suites underall3locks; preserve results even if passing tests miss known regression. No integration.

### 2026-10-06T18:20:10.348200-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0059/review-dd2cd0c/sonnet-static-review.md

**Verdict: blocked.** I read the code and tests only. I ran nothing and edited nothing. The task doc `docs/agents/tasks/T-0059-recovery-replay-provenance.md` is not in this worktree, so I checked against your brief and the module docstring.

**Blockers**
1. **Footprint validator rejects real snapshots.** `tools/replay_recovery.py:168` requires `_numbers(goal_footprint, 2)`.
   - `tools/sensor_course.py:412` records 4 entries (xmin, xmax, ymin, ymax).
   - `tools/recovery_policy.py:123` and `:293` require `len == 4`. They also require `[0] < [1]` and `[2] < [3]`, at `:133` and `:305`.
   - Every real snapshot would therefore be skipped as `snapshot_malformed/goal_footprint`, even with `--allow-grid-mismatch`.
   - Fix: require 4 finite numbers with the min<max ordering. Docstring and help should not imply otherwise.
2. **The synthetic fixtures hide this.**
   - `tools/tests/test_replay_recovery_provenance.py:32` uses `[.4, .3]`.
   - The assertions at about `:288` and `:291` expect `(.4, .3)`.
   - The malformed-footprint case at about `:187` uses `[.4]`.
   - The planners are mocked, so nothing contradicts the fixtures.
   - Fix: use a valid 4-entry footprint such as `[-1.1, .6, -.5, .5]`. Add rejection cases for 2 entries, mis-ordered entries and non-finite values. Assert the 4-tuple is forwarded unchanged.
3. **The test module has a syntax error.** In `tools/tests/test_replay_recovery_provenance.py`, line 301 (`self.forward.assert_not_called()`) is dedented out of the `for` loop. Line 302 then has an unexpected indent, which is an `IndentationError`, so no test in the module would run. Fix: move line 301 after the loop, or reindent the `forward.keywords` assertion into it.

**Non-blocking test gaps**
- Only the `select_backup_recovery` exception path is tested. Add an exception from `select_trap_escape`, which runs after the legacy call.
- No test uses non-empty teacher traps, so the `grade` and `match_trap` output is unexercised.
- Nothing asserts that `replay_controls` and the exact-capture paths are unchanged. They are untouched in the diff, and `tools/tests/test_recovery_control_pose.py` covers controls separately.

**What looks fine on reading**
- Row labelling: executed rows always carry `replay_kind` and `input_binding`.
- Strict stamps: bool, float, zero, negative and string stamps are unknown, and default is skip with explicit opt-in.
- Unusable snapshots skip regardless of the opt-in.
- `event_index` selection is fixed before any snapshot is read, and counts reconcile.
- Planner exceptions are not caught.
- Numeric arguments to both planners are unchanged.

### 2026-10-06T18:20:10.348200-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Original worker/reviewer ended. Sole HEADLESS opus-t0059-replay-provenance-20261006T1811-r1 owns same twofiles/isolatedworktree, fromdd2cd0c. Root60? NO: focused tests could not import new module due IndentationError302; exit1, testlog4f0d09980976df76cf9e8a1178258b48619e709d045160cc64e2c815b138c248, no tests ran. Preservefailure. Sonnet46.94s/USD0.2026208exactmodel confirms footprint/syntaxblockers. Fix only blockers plus escapeexceptiontest: require4finite ordered footprint bounds matching recovery_policy, correctsyntheticfixtures4tuple forwarded unchanged, reject2/unordered/nonfinite, repair testindent. Add select_trap_escape exception propagation. No historicalteacherfixture needed; unchanged grading notnewscope. No execution/tests/imports/providers; root rerunsfocused suite afternewcommit.6min/USD5 exactOpus/high. PriorSonnet failed toopenprimarypacketrelative; nextreview gets embeddedbrief.

### 2026-10-06T18:21:09.594070-07:00 · gpt-6-astra → all · HANDBACK

Opus revision completed42.73s/USD0.268501 exactmodel, candidatee8b8e88c8531a91c82d6946278d0bd2d51c36f97. Two owned files only, no tests/imports. Assignment ended. Fourbounds and testsyntax corrected, escapeexceptions covered. Root now runs samefocused suite underall3locks because changedsource/newtests; Sonnet focusedreview ofrevision. Priorfailure retained, no historical replay/live.

### 2026-10-06T18:22:36.329924-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0059/review-e8b8e88/sonnet-static-review.md

**Verdict: no blockers found in the two prior blockers or the main contract points. One validation gap is worth fixing, and I could not check against the task doc.**

**Not verified:** `docs/agents/tasks/T-0059-recovery-replay-provenance.md` is not in this worktree. No `*0059*` file is tracked, and the file tools are confined to this directory. I checked against the contract text in the `replay_recovery.py` docstring and the `recovery_policy.py` validators instead. I did not run tests, per instructions.

**Prior blockers: fixed**
- **Footprint:** `tools/replay_recovery.py:181-183` requires four finite, non-bool numbers with `xmin<xmax` and `ymin<ymax`. This matches `tools/recovery_policy.py:123,133-134` and `293-306`.
- **IndentationError:** the file reads as syntactically valid around 300-313, though I did not compile it. The odd indentation at 308 and 351 is legal and was not touched by this diff.
- **Root import:** the tests import `replay_recovery` at module level, so an import failure surfaces as a test-module failure.

**Contract points checked**
- **Labelling:** executed rows get `replay_kind=counterfactual_reconstructed` and `input_binding=not_evaluated` (`:224-225`), and skipped rows carry `replay_kind=None`.
- **Admission:**
  - Bool, float, zero, negative, string and absent stamps are never coerced and map to `unknown`.
  - Mismatch and unknown rows skip by default and run only with `--allow-grid-mismatch`.
  - Missing, unreadable, invalid-JSON and malformed snapshots skip even with the opt-in.
- **Event selection:** indices are taken from `run.json` order before any snapshot read, skipped events are never replaced, and `stall_counts` is consistent with the rows.
- **Planner exceptions:** only snapshot acquisition is caught, and tests cover both the backup and escape planners raising.
- **Unchanged paths:** the `reconstruct_event` body, `replay_controls` and `control_counts` are untouched by this diff, so admitted arguments and results are unchanged.
- **Tests:** they mock both planners and assert forwarded positional and keyword arguments, immutability, and the "forward planner never called" and "no planner on skip" cases. The CLI test confirms an unselected sequence 5 is never loaded.

**Gap (non-blocking, fix or accept)**
1. `event_problem` (`:140-142`) checks only `target[:2]`. A selection target of length 3 or more is admitted, then `exclude_trapped_guidance` calls `math.dist(target, stall_xy)` (`tools/trap_memory.py:207`). That raises `ValueError` instead of producing an `event_malformed` skip. Require `len(target)==2` and add a test.
2. The grid costs check admits any int, but both planners require values in [-1, 100]. An out-of-range grid executes and returns `legacy=None` and `retrace=None` rather than skipping. This is untested and is a labelling question rather than a correctness bug.
3. The tests have no case for a non-dict event or a non-finite `odom_stamp_ns`. `event_problem` appears to handle both.

No performance claim.

### 2026-10-06T18:22:36.329924-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

52focusedtests pass e8b8e88, log6d452ee92cb6bebe574fc2cfde5c109898a6aa13174f15246d54540d2f2b0672. Sonnet59.69s/USD0.2237504exactmodel priorblockersfixed; found malformedtarget/costgaps. SoleHEADLESS opus-t0059-replay-provenance-20261006T1811-r2 sameworktree/twofiles. Require selection.target exactly2numbers (notprefix), costs ints[-1,100] matchingrecoveryvalidator. Add behavior tests malformed3target, outofrangecosts bothwith/withoutoptin no-plannercalls, ensure-1/0/100valid. Add nonfiniteodom/non-dictevent tests ifsmall. No broaderCLI/control/runtimechanges. No execution/providers;commit andhandback. Bound3min/USD2 exactOpus/high. Nextreview embeds packet asfileaccessoutsideworkerconfined; previousreview checkedexplicitbrief/docstring notcanonicalfile.

### 2026-10-06T18:23:58.526065-07:00 · gpt-6-astra → all · HANDBACK

Revision2 completed64.09s/USD0.2896428 exactmodel; candidate6affa0e, onlytwofiles, notests. Newsource addressesexact2target/costrange/newtests. Assignment ended. FocusedSonnetreview newdiff with originalpacketembedded, root53? tests notyetcounted: run3focused suites underlocks; prior52pass retained.

### 2026-10-06T18:24:56.539287-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0059/review-6affa0e/sonnet-static-review.md

**Verdict: no blockers. I accept `6affa0e` as source. I read the diff and the surrounding code only; I ran no tests.**

**Target fix (`tools/replay_recovery.py:140-141`)**
- `event_problem` now requires `selection.target` to be a list or tuple of exactly two finite numbers (`_numbers(..., 2)`). This replaces the old `[:2]` slice, which let a 3-element target through.
- Bool and NaN values are still rejected by `_number`. A missing target gives `selection.get('target')` of `None`, which is also rejected.
- The comment about `math.dist` is accurate and matches the surrounding style.

**Cost range fix (`tools/replay_recovery.py:163`)**
- Costs must now be `type(c) is int and -1 <= c <= 100`. Bools are still excluded, and the length check is unchanged.

**New and changed tests**
- `costs_above` (101) and `costs_below` (-2) are added to the broken-snapshot loop. That loop checks skipping with and without opt-in, and that no planner is called.
- Targets of length 3 and 1, a NaN `odom_stamp_ns`, and a non-dict event (`[event(4)]`) are added to the malformed-event test. The non-dict event reaches `event_malformed` through `event_not_object`, and `grid_stamp` handles it safely.
- `test_cost_range_endpoints_are_valid` uses 16 costs for the 4×4 grid, including -1 and 100. It asserts `executed` / `grid_stamp_match`. `backup[0][0][4]` is the costs argument of `select_backup_recovery`, so the forwarded values are checked directly.

**Adverse changes:** none. Only these two owned files changed. The other validators, the admission logic and the planner path are untouched, and the tests use mocks rather than source strings.

**Residual risk:** I could not confirm the new tests pass. Root's lock-gated run has to do that.

### 2026-10-06T18:24:56.539287-07:00 · gpt-6-astra → gpt-6.1-sol · DISPATCH

Final source review accepted (24.91s/USD0.0768062, exact Sonnet). Candidate6affa0e passed53 focused tests, 1.562s suite, exit0; log05ec8906223beeea7970a9f067ba56c91f1ec96959f83eabe68d1702f23b3e00. Earlier dd2cd0c import failure and e8b8e88 52pass retained. Native Sol reviews only bounded evidence/hash/lease/test claims, no execution. Two-minute target, no source re-review. Integration remains prepared until verdict.

### 2026-10-06T18:25:27.857046-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0059/validation-6affa0e/sol-evidence-review.md

# T0059 candidate evidence review

Accept the focused offline validation evidence for `6affa0e7454b113d363050f6b1491576cc4ee6fa`; integration remains separate. Worker HEAD matches and is clean. Both current source/test byte hashes match `result.json`: replay `9238762fc3c74873843ce2533a6e909d18519c4ecb577d8b05acec903714f318`, test `d65f04fd3ceb1857b88a6644e7db13fd77e616e024f0d5dc283e4b7282f10e4e`.

The saved log reports 53 tests, 1.562 seconds, OK; parent recorded exit 0, no timeout, 1.812 seconds. Verified log SHA-256: `05ec8906223beeea7970a9f067ba56c91f1ec96959f83eabe68d1702f23b3e00`.

The retained initial log shows an IndentationError before test execution; the intermediate result records success. All three recorded log hashes verify. Syntax/footprint repairs and the subsequent exact-target/cost-range changes justify revised validation; failures were not overwritten. Sonnet's final static review reports no blockers.

The wrapper holds all three exclusive simulator locks, checks processes and Windows/WSL listeners, and rejects dirty/changed candidates or repeated output. Matching PID 16796 lease records bracket validation, 18:24:09.641–18:24:11.608 PDT.

Mocks establish admission/skips and forwarded arguments, not real planner outcomes. Controls and exact-capture preservation rely on source reviews. No historical captures, replay, integration, live benefit, or runtime promotion was evaluated.


### 2026-10-06T18:25:27.857046-07:00 · gpt-6-astra → all · DECISION

Accept candidate6affa0e for scoped integration based on Sonnet source acceptance and Sol validated53tests/hash/lease evidence. Preserve all three commits and initial failed import. Claims remain tested offline guards, not real planner/historical/live performance. Integrate complete dd2cd0c/e8b8e88/6affa0e range under all3locks, verify reviewed bytes then run53focused tests in primary. Other authors and runtime files remain outside scope.

### 2026-10-06T18:26:19.686616-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0059/integration/sol-integration-review.md

# T0059 integration evidence

Accept tested offline integration at `daecdaaa6b3cb9152f66373fa41e96f684b98384`. Primary HEAD and both file hashes match the integration record and reviewed `6affa0e` candidate. Saved Git output records all three cherry-picks: `371f25a`, `e832b98`, `daecdaa`; line-ending reconciliation is empty.

The log reports 53 tests passing in 1.680 seconds; parent exit 0, no timeout, 1.953 seconds. Its verified SHA-256 is `e13c0b6b48d4d9eeb5318541f08870066d5c1b66135df8478c1e40088e925103`. Matching PID 23604 held/released records bracket validation, 18:25:28.693–18:25:30.990 PDT.

This confirms integrated focused-test evidence only. No historical replay, real planner outcome, runtime autonomy, live benefit, or promotion claim follows.


### 2026-10-06T18:26:19.686616-07:00 · gpt-6-astra → all · INTEGRATION

Integrated complete dd2cd0c/e8b8e88/6affa0e range as371f25a/e832b98/daecdaaa6b3cb9152f66373fa41e96f684b98384. Primary53tests passed1.680s, exit0; exact reviewed source bytes and empty line-ending reconciliation. All3locks held PID23604 18:25:28.693–18:25:30.990 Pacific. LogSHA e13c0b6b48d4d9eeb5318541f08870066d5c1b66135df8478c1e40088e925103. Sonnet source acceptance and Sol candidate/integration evidence acceptance complete. Initial import failure and intermediate52pass preserved. All worker/reviewer assignments ended. Tested offline report/admission only: no historical replay, actual planner outcome, runtime change, live trial, Unity build or push. T0056 remains reserved;18:25 delivery refresh posted without presuming ACK.
