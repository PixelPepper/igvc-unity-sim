---
id: T-0013
title: Preserve topology evaluation across stationary terminal samples
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0013-topology-terminal-opus
base: 70b3566d91dce8b807fee729dbb110c20db3c764
candidate: 69ceefe223a2eddfa79c5f0043735654cd3c521d
claim: tested
lease: none
updated: 2026-10-05
---

# T-0013: Preserve topology evaluation across stationary terminal samples

## Packet

- Objective: fix topology_evidence empty candidate exception on stationary endpoint without weakening any scoring condition. This is auditor-only; no navigation-policy edits in this task.
- Owner: same interactive Opus session, prepared clean managed worktree C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM now on codex/t0013-topology-terminal-opus at base. Primary docs/task log only append; edit/commit source only in assigned worktree.
- Read first: README.md and this packet, T0010 Sol review artifacts/agents/T-0010/sol-review-r1.md inprimary, tools/course_judge.py topology_evidence and tools/tests/test_sensor_run_audit.py. Source documents reference only.
- Exact finding: terminal progress=total; delta0; lo=hi=total; bisect_right returns vertex index instead of valid segment index; first621>last620 for622vertices. Exception before later samples scored. Do not early-return success when gates complete.
- Owned paths: tools/course_judge.py and tools/tests/test_sensor_run_audit.py only. Owned primary artifacts/agents/T-0013/REPORT.md and review-inputs.md allowed; no runtime policy/config/footprint/threshold edits.
- Minimal intended correction: bound lower segment index to the last valid segment as upper index already does, while preserving projection window and every later sample's corridor/gate/return checks. Examine floating cases but do not widen tolerances or silently accept empty candidates.
- Behavior tests: valid square full-loop plus repeated terminal samples returns pass and checks entiretail; stationary-origin/incomplete/reverse/shortcut remainfail; post-finish excursion beyond corridor fails; retreat from endpoint remainslocallybounded and finalprogress/return still required. Test exact endpoint zero-motion regression fails onbase and passescandidate. Keep existing tests.
- Allowed checks: <=3focused invocations,35minwall. Source tests only; optional read-only topology-only re-evaluation of savedT0010trajectory in new artifact allowed, labeledcandidate. Do not overwrite run/audit/ledger. No full liveaudit orsimtrial; integrator re-audits only afterdualreview/integration. No Unitybuild/delegation/install/authretry.
- Acceptance: scoped immutablecommit, behavior evidence and full invariantpreservation; Sonnet/Sol review. Handback<=300words plus exactrange/tests/hashpaths. Stop afterhandback. UNMETERED interactiveusage.

## Handback

Revision 1 by claude-opus-5-5. Candidate 69ceefe223a2eddfa79c5f0043735654cd3c521d (base 70b3566).
Report: artifacts/agents/T-0013/REPORT.md; review-inputs.md staged.

```text
Defect: topology_evidence lower index first=max(0,bisect_right(arcs,lo)-1) lacked the segment clamp used by at() and
  `last`. At the finish with zero motion, lo==hi==total, so first became the final vertex index and last the final
  segment index. The empty range raised min() and aborted scoring of later samples.
Change (course_judge.py, +6/-1): clamp first with min(len(points)-2, ...). An empty candidate set now raises the
  explicit 'No reachable WORLD projection at sample N' (fails closed). No tolerance, corridor, gate, progress, return or
  window change, and no early success.
Tests (test_sensor_run_audit.py, +33): stationary terminal repeats pass with every sample scored; a 4 m post-finish
  excursion fails as Outside corridor; retreat without return fails; retreat and return passes and is fully scored.
  Existing tests unchanged.
  Base with the new tests: 2 FAIL (the exact 'min() iterable argument is empty'). Candidate: 23 tests OK.
T-0010 candidate topology-only re-evaluation (not an audit; originals unchanged), run f7be0831..., course matching the
  audit's expected 1126a943...: base fails at sample 17418 with min() empty (77/77 gates, progress==total).
  Candidate passes, scoring through 19726 with final lateral 0.398 m.
  artifacts/agents/T-0013/t0010-topology-candidate.json sha256 ab086e50...
Invocations: 3. No live work. No policy edits. Integrator re-audit pending. UNMETERED.
```

## Log

### 2026-10-05T02:49:11.954816-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Explicit independent auditor-only task while T0012 probe undergoes review. Prepared worktree/branch above is clean. Repair terminalsegment indexing and preserve evaluation of every remaining sample. No policy/source changes outsideownedpaths; originalfailedaudit retained. Exactbase70b3566. Commit ownedsource only,35min/3focusedchecks. No live work.

### 2026-10-05T02:49:25-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received. claude-opus-5-5, the same interactive session. Worktree igvc-t0005-health-capture on codex/t0013-topology-terminal-opus
at 70b3566. Owned: course_judge.py and test_sensor_run_audit.py, plus T-0013 report and review-inputs. Auditor-only, 3 focused checks,
35 min. No policy edits.

### 2026-10-05T02:52:51-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 69ceefe223a2eddfa79c5f0043735654cd3c521d (two owned paths). The lower projection index is now clamped to the last
segment, and an empty candidate set fails closed explicitly. The new terminal tests fail on base with the exact T-0010 error
and all 23 pass on the candidate. Candidate topology-only re-evaluation of T-0010: base aborts at sample 17418; candidate
passes, scoring all 19727 samples. See the Handback section. Three invocations. Stopping.


### 2026-10-05T02:58:01.128182-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0013/sonnet-review-r1.md

REVIEW 69ceefe223a2eddfa79c5f0043735654cd3c521d (base 70b3566d91dce8b807fee729dbb110c20db3c764)

**Verdict: APPROVE.** Two non-blocking notes below.

**Findings**
1. **Fix is correct and minimal.** At the finish, `lo == hi == total`, so `first` and `last` are both the final segment. `lower` and `upper` come from the identical expression `(total-arcs[i])/length`, so both are exactly 1.0. The range is no longer empty.
2. **No checks weakened.**
   - Unchanged: corridor test (`lateral > width+.001`), the gate crossing and arc-proximity logic, the 1.5×delta reachability window, the ±.4 m final-return check, and the progress ≥ total−.4 rule.
   - The new `ValueError` is the same exception type the old `min([])` raised, and the existing `except` catches it, so it fails closed with a clearer reason.
   - No early success return was added, and there is no wrap or finish jump.
3. **Every tail sample is assessed.** Each terminal sample still goes through the corridor check and updates `last_sample_index`. The tests assert that index equals `len(samples)-1`.
4. **Tests are meaningful.**
   - The terminal-repeats and retreat-and-return tests fail on base with `min() iterable argument is empty` and pass on the candidate.
   - The excursion test asserts the `Outside ordered WORLD corridor` reason.
   - The retreat-without-return test asserts progress < total−.4.
   - The latter two already failed closed on base, so they guard against regressions rather than prove the fix.
5. **Scope.** The diff touches only the two owned files and no runtime or policy code. Sensors and the 6 sparse GPS fixes are not involved.

**Non-blocking notes**
- The `tail()` helper's docstring says it continues in time, but each `walk()[1:]` restarts timestamps at 0.1. `topology_evidence` ignores timestamps, so these tests are unaffected. Any future reuse with `audit()` (which checks time gaps) would break, so either fix the timestamps or correct the docstring.
- The T-0010 replay's final return is 0.398 m against the 0.4 m tolerance. That passes under policy, but the margin is thin. The integrator's full re-audit should confirm it from the original run.

**Not verified (no tools).** I did not check the file SHA256s against the candidate, the replay JSON hash `ab086e50…`, the 19,727-sample or 77/77-gate figures, or the test run counts. The evidence reviewer should confirm these independently. The topology-only replay is correctly labelled as not a full audit, and the original T-0010 failed audit is preserved.


### 2026-10-05T02:58:01.128182-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0013/sol-review-r1.md

### 2026-10-05T02:57:06.3512381-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0013   Candidate: 69ceefe223a2eddfa79c5f0043735654cd3c521d   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] tools/tests/test_sensor_run_audit.py:tail appends walk() timestamps without offsetting them. Retreat/return fixture resets 40.0→0.1 s and 1.5→0.1 s. These topology-only tests verify geometric behavior, but the claimed continuously timed tail is false. Offset each appended segment's timestamps; retain geometry assertions.
2. [nit] REPORT.md says base stopped at sample 17418: that is the last successfully scored index; the exception occurs on sample 17419. Artifact's last_sample_index is correct.

Observation: clean worktree HEAD matches candidate. Full base..candidate diff contains exactly the two owned auditor/test files. Lower segment clamp fixes the zero-motion endpoint range; empty candidates still fail closed. Reachable projection window, corridor width, ordered gates, progress and final return conditions are unchanged, and every subsequent sample remains evaluated.

Provenance: topology artifact SHA256 ab086e50701d960a4a879a28cd279341876456ff4762c5ccbb9968d09e25468f matches report. Its base/candidate source hashes match exact blob/clean worker source; worker source normalizes to candidate blob. Original run/course hashes match artifact and original audit binding. Candidate topology-only result reaches 19726/19726 with 77/77 gates; it is not a full audit. Original audit remains false with the original exception.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: git diff 70b3566..69ceefe; WSL source /opt/ros/jazzy/setup.bash && python3 -B - ran four new topology tests against base/candidate: base 2 fail, candidate 4 pass. Initial Linux Git worktree-path lookup failed before tests; primary Git lookup resolved it. No broad suite/full audit/live.
Missing acceptance coverage: corrected timestamps; integrated, separately labeled full re-audit. Worker 23-test result inspected, not repeated. No navigation-policy or promotion approval inferred. Usage: UNMETERED.



### 2026-10-05T02:58:01.128182-07:00 · gpt-6-astra → all · DECISION
Accept exact candidate69ceefe223a2eddfa79c5f0043735654cd3c521d: both reviews approve with no blocking findings. Tail helper timestamps reset in moving extensions; these tests call topology_evidence, which intentionally evaluates geometry only. The timing-docstring nit does not invalidate geometric regression; do not reuse that helper as full-audit timing evidence. The saved real run retains original monotonic timestamps and will receive a separate full re-audit. Correct REPORT wording:17418 is last successfully scored sample; exception occurs17419. No threshold/policy changes. Sonnet exactmodel verified, API-equivalent cost $0.1099614; Sol UNMETERED. Combined checks and full re-audit pending.

### 2026-10-05T02:58:47-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Wording correction applied to artifacts/agents/T-0013/REPORT.md: 17418 is the last successfully scored sample and the exception
occurred at sample 17419 (my handback said "fails at sample 17418"). The candidate commit is unchanged. I also acknowledge the tail
helper's timestamps: they are geometry-only test evidence, not full-audit timing evidence.


### 2026-10-05T03:00:27.046612-07:00 · gpt-6-astra → all · NOTE
Integrated auditor-only candidate as e886abb569b3a811a41d7bd726f1529779fff58b. Separate full re-audit artifacts/iterations/2026-10-05/mouth-repeat-1/audit-t0013-reaudit.json passes20/20, scores through19726of19726; run hash unchangedf7be0831c27ec043b160c46f4016bc9608508aeae93b4d3d6463f88e925d9c98. Re-audit SHA256ebd6d90e7e2537602a3c4c05267b8c9d86053fdcbf9265f997300fddd3e37f95. artifacts/agents/T-0013/reaudit-manifest.json records integratedauditor source hashes and before/after originalrun/audit/course/mission/ledger equality. Originalfailed record unchanged. This is a corrected evaluation of an existing lap, not newlive or promotion. Combined checks pending with T0014 integration.


### 2026-10-05T03:08:20.469170-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0013/sol-reaudit.md

### 2026-10-05T03:07:22.4473342-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0013   Candidate: e886abb569b3a811a41d7bd726f1529779fff58b   Scope: evidence (supplemental re-audit binding)
Verdict: approve

Findings (ranked, ≤ 5):
1. None. Separate full re-audit output SHA256 ebd6d90e7e2537602a3c4c05267b8c9d86053fdcbf9265f997300fddd3e37f95 matches manifest and binds preserved run f7be0831c27ec043b160c46f4016bc9608508aeae93b4d3d6463f88e925d9c98.

Observation: all 20 re-audit checks pass; only ordered_world_full_loop differs from original check outcomes. It evaluates all 19727 samples through index 19726, visits 77/77 gates, and reaches full 155.186105 m progress. Final return 0.39824388896267277 m independently matches final trajectory pose.

All six recorded auditor/dependency source hashes match current bytes and normalized integrated-commit blobs. Integrated course_judge.py is identical to reviewed 69ceefe223a2eddfa79c5f0043735654cd3c521d. Run, original audit, course, autonomy and complete benchmark CSV hashes match both manifest before/after values. Original audit remains false with its exception, and original CSV row still binds audit.json with audit_passed=false. The separate result preserves original failure provenance.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: none; hash, blob, JSON-binding, check-count and final-pose calculations only. No repeated code review, re-audit or live run.
Missing acceptance coverage: this corrects assessment of the existing T-0010 trajectory; it creates no new trial, unchanged-commit streak or promotion evidence. Repeatability, held-out seeds and physical calibration remain pending. Usage: UNMETERED.



### 2026-10-05T03:37:42.940616-07:00 · gpt-6-astra → all · INTEGRATION
All constituent integration tests now pass: 500 tools, 85 perception and four GPS (589 unique tests). Initial full-script run stopped on a stale generated board; regenerated board and its five tests pass. Continuation-command ROS environment/CRLF errors were corrected separately; no test failure is concealed. This is not a single clean full-script run. Logs and exact accounting: artifacts/agents/T-0015/integration-validation.json, combined-checks.log, combined-completion-env-error.log and combined-completion.log. Knowledge check and strict check pass with eight concepts, zero errors/warnings. No new live trial or promotion claim.
