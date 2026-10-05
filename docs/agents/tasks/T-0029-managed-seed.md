---
id: T-0029
title: Support explicit held-out seeds in the managed trial runner
status: changes-requested
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0029-managed-seed-opus
base: 2ec0c05e3975e6aa2ebec4c5b30c845a0b770ade
candidate: 4a8d2e3ec936dbc55e72b066cfa105b1bea6d9ac
claim: tested
lease: none
updated: 2026-10-05
---

# T-0029: Prepare the existing held-out validation gate

## Packet

- Existing interactive Opus owns this complete bounded slice. Read README, the
  promotion rule in PROTOCOL/DECISIONS, and this packet. Reuse clean worktree
  C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM on the branch above.
- Current runner hardcodes seed2027 in variant-start, normal mission, audit and
  Unity log capture; iteration-mission.py also hardcodes it for recording mode.
  User-approved held-out seeds2028 and2029 cannot be run consistently through it.
- Add an optional JSON config seed with default2027. Reject bool, null, string,
  fractional, negative and out-of-int32-range values before acquiring the lease
  or starting processes. An explicit nonnegative int32 seed selects all course/
  mission/audit/log locations consistently and is recorded in live.json.
  Preserve every existing option/default, rejection and lease/cleanup rule.
- Both record_episode modes must receive the same selected seed; do not alter
  recorder options, budgets, controllers, geometry or mission goals. If the
  coordinator has prepared inputs for another seed, make mismatched identity
  apparent rather than silently labeling a2027 run as a held-out run. Explain
  how the coordinator prepares matching files; do not launch/generate maps here.
- Owned: tools/agents/iteration-live.ps1; tools/agents/iteration-mission.py;
  one small option/argument helper if needed; focused tests for those options and
  command construction only. No Unity, ROS interface, policy, auditor, profile,
  tools/igvc.ps1 or primary checkout source edits.
- Behaviorally test default2027 and explicit2028/2029 propagation to all consumers,
  invalid inputs before side effects, record_episode routing and unchanged
  revalidate_active_path validation. No source-string-only tests. Choose a small,
  testable design rather than a generic new orchestration framework.
- T0028 is RUNNING in a separate immutable checkout. Light authoring allowed;
  no tests/replay/build until primary
  artifacts/iterations/2026-10-05/recovery-instrumented-2/live.json shows
  stage=finished and shutdown_verified=true. Then test automatically.
  Do not edit the primary runner or interrupt any live process.
- <=25min active work plus live wait, <=2 focused invocations, no full suite/live/
  Unity build/providers/recursive agents. Use Windows PowerShell5 native module
  directories when needed to avoid bundled-runtime PSReadLine startup issues.
- Commit only owned source/tests in your branch. Write primary artifacts/agents/
  T-0029/REPORT.md and review-inputs.md; append <=300-word handback here and stop.
  Root owns integration, input preparation and actual held-out trials. This change
  does not bypass three consecutive seed2027 passes or authorize promotion.
- Knowledge: trial-audit-promotion; ros-unity-transport; agent-handoffs.

## Handback

Current: revision 2 (final), candidate 8be795c7313f6537e93bbb09368445289ec21b33; 107/0 PowerShell, exit 0 (see REPORT.md "Revision 2"). Revision 1 was 4a8d2e3 (partial;
see REPORT.md "Revision 1" and the latest HANDBACK below). Original: claude-opus-5-5. Candidate 85c67c30bd4d7b21a265dd68772680bd1753ee42 (base 2ec0c05), 5 files +231/-18.
Report: artifacts/agents/T-0029/REPORT.md; review-inputs.md staged.

```text
Design: new iteration-options.ps1 helper, dot-sourced by iteration-live.ps1.
  Get-TrialSeed: absent gives 2027. Only a JSON integer in 0..2147483647 is accepted; anything else throws.
  It is checked before live.json, the lease or any process, and the seed is recorded in live.json.
  Get-TrialCommands builds variant-start, the normal and recording missions, the audit and the Unity log
  from that one seed. The 2027 lists are identical to the previous literals.
  Test-SeedInputs runs after variant-start and before nav or the mission: course.json and mission.json must
  state the seed and mission.json must bind course.json by sha256. Otherwise the run fails under the
  unchanged cleanup; on success the hashes are recorded. iteration-mission.py takes --seed (default 2027);
  recorder unchanged.
Coordinator: set "seed": 2028/2029 in the job config. variant-start already generates the seed's files in
  the workspace.
Tests (after T0028 verified shutdown):
  Python, 3 OK: default unchanged; 4 explicit seeds; 10 invalid strings.
  PowerShell 5, 73 passed / 0 failed: validation; per-seed, per-mode propagation; synthetic identity checks;
  the real runner with 6 invalid configs exits before live.json or the lease.
  Harness defects: a mis-quoted parse printout, and a missing final exit 0 (added afterwards, not re-run).
Unverified: live held-out run; runner success path; real generated files. No promotion bypass. UNMETERED.
```

## Log

### 2026-10-05T05:45:34.041347-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Proceed with light authoring now; honor the T0028 test prerequisite above. This
prepares the existing validation plan without changing the running navigation.

### 2026-10-05T05:49:13-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0029 accepted on codex/t0029-managed-seed-opus at 2ec0c05. Authoring only; tests wait for recovery-instrumented-2 live.json to show finished with shutdown_verified=true.

### 2026-10-05T05:52:15-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 85c67c30bd4d7b21a265dd68772680bd1753ee42 (5 owned files). The optional config seed (default 2027) is validated before any side effect, recorded in live.json and propagated to every consumer through one helper. Generated course and mission identity is checked before any mission runs. Python 3 OK; PowerShell 5 73/0, including the real runner rejecting invalid configs before live.json or the lease. Two harness defects are disclosed (see the Handback section). Stopping.

### 2026-10-05T05:52:42.263152-07:00 · gpt-6-astra → claude-opus-5-5 · LEASE-RELEASE
T0028 finished with shutdown_verified=true. Root independently confirmed no
player/listener and available exclusive lease. Your bounded focused checks may
run now. The live run passed6/6 and20/20; review pending. No next trial will start
until your focused work has finished or you explicitly defer it.

### 2026-10-05T05:52:57-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
T-0029 focused work is complete. Both invocations ran after T0028 live.json showed finished with shutdown_verified=true, and the handback (candidate 85c67c3) was posted at 05:52:15. I hold no runtime, lease or running process; the next trial is not blocked by me.

### 2026-10-05T05:56:16.578047-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Root found a concrete identity bug in85c67c3: Test-SeedInputs accepts both
course.json={"seed":2028.5} and malformed course.json={"seed":2028, when mission
claims2028 and binds those bytes. See artifacts/agents/T-0029/root-identity-probe.json.
Parse complete JSON and validate explicit top-level integer seed metadata rather
than the first40-line regex. Keep generated identity checking honest; no claims
that a file hash alone binds sanitized autonomy to a seed.
Also add an explicit resolved absolute path containment check before the test
harness recursively deletes its generated temp directory (Windows workspace rule).
The final success exit was untested; run that corrected harness in this revision.
Sonnet review is pending; consolidate any material findings into this same revision1.
Bounds: same owned paths, <=20min active plus wait, <=2 focused invocations; preserve
all existing runtime/lease/options semantics and stop at handback. T0030 is being
launched NOW. Light authoring allowed; no tests or replay until primary
artifacts/iterations/2026-10-05/recovery-instrumented-3/live.json has stage=finished
and shutdown_verified=true. Then test automatically. No integration during live.

### 2026-10-05T05:57:03.552346-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0029/sonnet-review-r1.md
USD0.1136554 API-equivalent; actual model confirmed.

**Verdict: request changes.** The seed plumbing is sound. Two gaps are narrow and cheap to fix.

**1. Course identity check is weaker than claimed (material, `iteration-options.ps1:Test-SeedInputs`).**
- The regex `"seed"\s*:\s*(-?\d+)` on the first 40 lines takes the first `"seed"` key anywhere, including nested objects.
- It accepts `2028.5`, `2028.0` and `2028e1` as `2028`, because it stops at the digits.
- If the top-level seed sits past line 40, it fails closed after `variant-start` has already spent a simulator start.
- The sha256 binding limits the practical risk, but the "typed, integer, top-level seed" claim does not hold.
- The fix is to parse `course.json` fully, using the repo's JSON metadata parser or `ConvertFrom-Json`, and apply the same strict int/long 0..Int32.MaxValue check as `Get-TrialSeed`.

**2. `mission.json.seed` is compared loosely (material, same function).**
- `$missionJson.seed -ne $Seed` coerces types.
- `"2028"` and `2028.0` pass.
- `true` passes for any nonzero seed.
- `[2028]` yields an empty array from `-ne`, which is falsy, so it passes.
- Reuse the strict validator here too.
- Add negative tests for fractional, nested, string, bool and array seeds. Current fixtures only write a clean top-level integer, so none of this is exercised.

**3. No temp-delete guard (required by your Windows workflow; `iteration-options.tests.ps1`, `finally`).**
- `Remove-Item -LiteralPath $tmp -Recurse -Force` runs unresolved and unchecked.
- `$tmp` is built from `GetTempPath()` plus a fixed prefix and a GUID, so real risk is low, but the guard is absent.
- Before deleting, resolve with `GetFullPath`. Require the result to start with the resolved temp root plus a trailing separator, to differ from the root, and to have leaf `t0029-*`.
- Skip the delete otherwise.

**4. Lower-priority items.**
- The "no lease file" assertion uses `artifacts/iterations/live.lock`. Confirm that is the lease name the runner really uses, or the check is vacuous.
- `Test-SeedInputs` has only run on synthetic files. Before merge, run it once against a real generated `seed-2027` folder, since a header mismatch blocks every held-out run.
- The final `exit 0` was not re-run. It is side-effect-free, so one re-run closes it.
- `test_iteration_seed.py` hardcodes POSIX paths, so it passes under WSL but would fail on native Windows Python. Note this or normalize.

**Verified from the diff, no issues found:**
- The default 2027 commands are identical to the previous literals.
- Every consumer follows the seed: start, mission, audit, Unity log, and the recording-mode `--seed`.
- Body clearance and revalidation remain normal-mode only.
- Seed validation runs before the state, lease and process work.
- A failed input check lands in the existing `finally`, so cleanup and lease rules are unchanged.
- The Python parser is strict, ASCII-only and bounded.

Fix 1 to 3, re-run both suites, then accept.

### 2026-10-05T05:57:03.552346-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
Consolidate these findings into the already granted revision1. Strict validation
must cover BOTH course and mission top-level seed metadata, with explicit presence
(no missing-field default for metadata). Nested-only seed is not a top-level seed;
valid top-level metadata need not reject unrelated nested data. Re-run the corrected
success harness within the existing2-invocation allowance after T0030 release.
A read-only identity check on the actual runtime's generated seed2027 folder after
shutdown should be included in that PowerShell invocation. Current shared lease is
artifacts/iterations/live.lock, so the full-runner negative test checks the right file.
Keep Python tests honestly WSL-only or make them portable without extra scope.
T0030 now owns the live lease; no heavy work until finished/shutdown_verified.

### 2026-10-05T06:04:46.917348-07:00 · gpt-6-astra → claude-opus-5-5 · LEASE-RELEASE
T0030 finished with shutdown_verified=true; root independently confirmed absent
player/listener and available exclusive lease. Your revised focused checks may
proceed now within the existing allowance. Third lap passed all20 checks; held-out
trials remain blocked on reviewed seed support, not on another approval.

### 2026-10-05T06:04:52-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
PARTIAL. Revision 1: candidate 4a8d2e3ec936dbc55e72b066cfa105b1bea6d9ac (parent 85c67c3; 3 files +92/-35).
- Test-SeedInputs parses course.json and mission.json completely. Each needs an explicit top-level
  strict-integer seed equal to the selection; the course bytes are bound by an exact lowercase sha string.
  autonomy.json is recorded by hash only.
- Temp delete is guarded by resolved containment. The Python test is path-portable. Lease path confirmed.
Invocations, after T0030 verified shutdown:
- Python: 3 OK.
- PowerShell: 0 parse errors. The real T0030 runtime seed-2027 folder was accepted read-only (hashes in
  REPORT). 97 passed / 1 failed.
Material harness defect: my Throws helper did not discard the tested call's output, so a returning call
counted as a throw. That failed the one positive repaired-2029 check and makes every Throws-based negative
non-evidence, here and in 85c67c3's 73/0.
Fixed in 4a8d2e3 (Out-Null) but not run: the budget is used.
Still valid: Python tests, parse checks, direct positive checks, and full-runner negatives (exit code, no
live.json or lease, reason).
Request: one PowerShell invocation of artifacts/agents/T-0029/run-r1.ps1 on 4a8d2e3, to establish the strict
negatives, the real 2028 rejection and the success exit 0. Stopping.

### 2026-10-05T06:06:38.794972-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Grant revision2, <=10min active and ONE PowerShell verification invocation, no
Python rerun unless that code changes. The Throws-based negatives from both older
runs are invalidated as you correctly disclosed; preserve those logs and say so.

One additional concrete metadata issue: Read-SeededJson accepts a single-element
root array [{"seed":2028}], because ConvertFrom-Json pipeline unwrapping turns it
into a PSCustomObject. Root reproduced with artifacts/agents/T-0029/root-array-probe.json.
Require the actual JSON root to be an object, not just the unwrapped result, for
both course and mission. Add root-array rejection and known throwing/non-throwing
harness controls, then run the corrected full PowerShell suite once, including
the real generated2027 read-only check and real2028 mismatch. Keep same owned paths;
no broader schema framework. Final candidate, honest test evidence and stop.
No live session is active; tests can run now. Independent final reviews follow.

### 2026-10-05T06:07:56-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Revision 2 (final): candidate 8be795c7313f6537e93bbb09368445289ec21b33 (parent 4a8d2e3; 2 files +19/-4; base..candidate 5 files +303/-18).
- Read-SeededJson now requires the actual file text to start with '{' (after BOM/whitespace) before parsing,
  because ConvertFrom-Json unwraps [{"seed":N}]. This applies to both course and mission.
- New tests: course root array (plain and whitespace-prefixed), mission root array, scalar root, and harness
  controls proving Throws returns a boolean that distinguishes throwing blocks from returning blocks of any type.
Verification, one PowerShell invocation on the exact committed tree (artifacts/agents/T-0029/run-r2.log):
- 0 parse errors
- real T0030 seed-2027 folder accepted read-only; real workspace rejected as 2028
- passed=107 failed=0, exit 0
The Python file is unchanged (3 OK in revision 1). The Throws-based negatives from the 73/0 and 97/1 runs remain
invalid history. No live held-out run. Stopping.
