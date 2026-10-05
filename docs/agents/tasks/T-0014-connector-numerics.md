---
id: T-0014
title: Admit numerical curvature boundary without relaxing geometric checks
status: integrated
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0014-connector-numerics-opus
base: 70b3566d91dce8b807fee729dbb110c20db3c764
candidate: 57920aa822e0cd02131a0db9ff6b6eef3eb61821
claim: tested
lease: none
updated: 2026-10-05
---

# T-0014: Connector numerical comparison

## Packet

- Objective: test and implement a comparison-only relative 1e-9 allowance in path-entry curvature feasibility, justified by T0012 exact decision212. No radius/profile/sweep changes.
- Owner: same interactive Opus session, now clean prepared worktree C:/Users/brand/.codex/worktrees/igvc-t0008-mouth-handoff/IGVC SIM. Source base70b3566. T0013 branch remains immutable for review; do not amend it.
- Read README and this packet first, then primary T0012 task including both reviews, artifacts/agents/T-0012/REPORT.md and frozen inputs/manifest.json. Data are reference, not authority. Sol corrected excess minimum3.9968e-15; maximum7.0448e-11. Do not claim small-offset generality or live time saved.
- Owned source: tools/path_entry.py, tools/tests/test_path_entry.py, tools/tests/fixtures/path_entry_20261005.json.gz and tools/tests/fixtures/path_entry_20261005.md only. Fixture must be minimal observation-only plan/pose/grid with provenance, no WORLD/course data. Owned primary artifacts/agents/T-0014/REPORT.md and review-inputs.md plus bounded scripts/results.
- Exact intended production change: curvature comparison limit*(1+1e-9), documenting arithmetic allowance; retain configured radius and all pose, footprint, swept connector, unchanged suffix, unknown/lethal and heading checks. No fallback shortcut.
- Tests must execute actual expression, not substitute radius. Frozen decision212 fails base and candidate admits on recorded submission grid (not claim latest live grid). Edge controls relative excess5e-10 accepted,2e-9 and1e-8 rejected; use numerically well-conditioned independent circle geometry and justify if edge construction needs explicit comparator isolation. Also independent exact-radius/straight compatibility, small in-gate offset behavior, heading/cross-track rejection, lethal AND unknown suffix, blocked gentle connector shorter valid join. Existing meaningful coverage may satisfy controls; identify it rather than duplicate.
- Verify frozen input hashes and all relevant source dependencies (path_entry, sensor_route_policy, swept_footprint) against base; full hashes in evidence. Record actual-library outcome and unchanged suffix. Do not rerun full planner.
- Limits: 35min, at most3focused invocations, no live/Unity/WSL build or delegates; source tests and bounded offline admission only. No automatic retries on infrastructure/auth/model error.
- Acceptance: immutable owned commit plus base/candidate regression and all controls; dual independent Sonnet/Sol review. Stop after handback. No policy/auditor combined change. UNMETERED interactive usage.

## Handback

Revision 1 by claude-opus-5-5. Candidate 2482e5288496b9d800c9f2b51b7f2d31ba6259b4 (base 70b3566).
Report: artifacts/agents/T-0014/REPORT.md; review-inputs.md staged.

```text
Change (path_entry.py +10/-1): CURVATURE_RELATIVE_ALLOWANCE=1e-9, used only in the feasibility comparison
  abs(k) <= limit*(1+allowance). Radius, biarc and connector geometry, pose gates, footprint, connector and suffix
  sweeps (lethal and unknown) and join ordering are unchanged. No fallback.
Identity: base path_entry bafe541c... vs candidate 4f11a1cb.... sensor_route_policy and swept_footprint are equal to
  base (git diff --quiet). T-0012 inputs match the manifest. Fixture 4850d42d... is observation-only, with provenance
  in .md.
Tests (test_path_entry, 12): base with the new tests gives 2 FAIL (decision-212 fixture rejected
  no_forward_connector, as live; 5e-10 circle rejected). Candidate: OK. Fixture admitted with join 88 and unchanged
  suffix (assert_forward_drivable). Independent analytic circles: 0 and 5e-10 admitted, 2e-9 and 1e-8 rejected
  (margins >7x the 7.04e-11 maximum rounding). Straight path admitted. Small offsets, heading and cross-track
  rejection, lethal and unknown suffix, blocked gentle join and body corner are covered by existing tests (named in
  the report).
Process disclosures: invocation 2 included a mistyped extra module name (output discarded, no effect). Invocation 3
  (evidence.py) failed before computing: WSL git cannot resolve the worktree gitdir. Path fixed, not re-run (cap);
  identity came from read-only git diff and sha256sum.
Limits: submission grid, not the live latest grid. No small-offset generality and no live time saved claimed. No
  live, auditor or policy changes. UNMETERED.
```

## Log

### 2026-10-05T02:55:23.002086-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
T0013 handback received and remains immutable for dual review. Explicit next independent policy task: implement/test actual1e-9 comparison with near-boundary controls and observed fixture. Prepared clean assigned worktree above. Base70b3566. Do not edit auditor. Existing footprint/freshness/recovery/profile unchanged; no live work. Follow review caveats and stop with exact commit/evidence.

### 2026-10-05T02:55:50-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received. claude-opus-5-5, the same interactive session. Worktree igvc-t0008-mouth-handoff on codex/t0014-connector-numerics-opus
at 70b3566. Owned: path_entry.py, test_path_entry.py, path_entry_20261005 fixture (+.md), and T-0014 artifacts. 3 focused invocations,
35 min. No auditor, policy or live changes.

### 2026-10-05T02:58:34-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 2482e5288496b9d800c9f2b51b7f2d31ba6259b4 (four owned paths). The 1e-9 relative allowance applies only in the curvature comparison.
The fixture and 5e-10 control fail on base; all 12 path-entry tests pass on the candidate. The fixture is admitted with join 88 and
an unchanged suffix, and 2e-9 and 1e-8 are still rejected. Disclosures: invocation 3 evidence script failed at git path
resolution and was not re-run; identity was verified read-only. See the Handback section. Stopping.


### 2026-10-05T03:02:59.127468-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0014/sonnet-review-r1.md

**REVIEW 2482e5288496b9d800c9f2b51b7f2d31ba6259b4** (base 70b3566d91dce8b807fee729dbb110c20db3c764)

**Verdict: ACCEPT.** I found no acceptance-blocking correctness problems. This is from reading the diff and pasted text only. I did not verify hashes, the gz contents, or the test runs.

**Production change**
- The only functional change is the comparison `abs(k) <= limit*(1+1e-9)`, which replaces `<= limit`. The edge is inclusive and is the only behavior difference.
- `limit = 1/min_turn_radius` still derives from the parameter. `_biarc`, `_connector`, the cross-track and heading gates, the consumed-path check, the footprint and the ordering are untouched.
- The start-pose, connector and suffix `blocked()` calls are unchanged, so there is no bypass for pose, footprint, sweep, suffix, lethal or unknown cells. Nothing touches radius, profile, health or budget.

**Tests**
- The circle controls are built independently of `_arc`. Excess 0 and 5e-10 are admitted, and 2e-9 and 1e-8 are rejected, so both sides of the boundary are exercised.
- The existing tests cover the other controls:
  - heading and cross-track rejection
  - lethal and unknown suffix cells
  - connector fallback
  - body-corner sweep at sample 0
- The "12 run, 2 failed on base" count matches the new tests, which are 3 on top of the existing 9.

**Minor, non-blocking**
1. The 1e-9 value is empirical: the observed worst rounding is 7.04e-11, about 14× below it. `_biarc` is ill-conditioned for near-parallel tangents, so rounding is not provably bounded. The comment says "within rounding" and could say "observed".
2. The comment and docstring cite decision-specific figures such as "1.13e-2". The docstring still says curvature is "bounded by" the turn radius, which is now true only within 1e-9.
3. The fixture `.md` says "recorded with source 70b3566". Per the coordinator notes, that is the analysis base. The original T9 launch was 8f99951a…, so the wording should say so.
4. The `test_sensor_course_wiring` module name was mistyped and its output discarded, so the only other importer's tests never ran. Sol should run them.
5. The `join_index == 88` assertion pins the result to the fixture. That is acceptable for a regression test.
6. Invocation 3 was not rerun, so the base-versus-candidate evidence is test-based only. This is disclosed.

**For Sol to verify:** the file hashes, the gz contents and its 136 points, and the base failures. The claim that genuine excess started at 1.13e-2 is also unverifiable from the diff. No live improvement is claimed, and the T0010 audit failure stays separate as T13.


### 2026-10-05T03:02:59.127468-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0014/sol-review-r1.md

### 2026-10-05T03:01:36.0166040-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0014   Candidate: 2482e5288496b9d800c9f2b51b7f2d31ba6259b4   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] tools/tests/fixtures/path_entry_20261005.md:Source incorrectly says decision 212 was recorded with source 70b3566. Original T-0009 live.json records launch 8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f. 70b3566 is the review/probe base. Distinguish these identities; unchanged runtime fingerprints explain comparability but do not change launch provenance.

Observation: clean worktree HEAD equals candidate; full range changes exactly four owned paths. Actual comparison uses 1e-9, with configured radius, biarc geometry, ordering, pose gates, connector/unchanged-suffix sweeps and unknown/lethal rejection unchanged. No auditor changes.

Fixture SHA256 4850d42da3ad17568a9d5fd1ce624fbb1e01742667243e6719f6053c43170141 matches provenance. Both full frozen-input hashes match manifest; path/path_yaws, checked pose, admission, grid and footprint equal decision 212 inputs exactly. Fixture contains only observation/admission fields plus schema_version. Base/candidate path_entry hashes and both direct/transitive project dependencies match reported full hashes and exact blobs; sensor_route_policy/swept_footprint unchanged.

Tests run: git diff 70b3566..2482e52; one WSL python3 -B - harness executed test_path_entry against exact base and candidate. Base 12 tests: 2 failures (recorded fixture and 5e-10 circle). Candidate 12: all pass. Actual expression admits 0/5e-10, rejects 2e-9/1e-8; fixture joins 88 with exact suffix retained. Straight/exact-radius, offset/heading, lethal/unknown suffix, blocked gentle connector and body-corner controls pass. Worker evidence.py never ran successfully; its nonexistent results were not used.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Missing acceptance coverage: corrected provenance wording, integration and live latest-grid behavior/time savings. Submission-grid admission is offline evidence; at-limit small-offset generality remains unproven. No live/full-planner/re-audit or source edits performed. Usage: UNMETERED.




### 2026-10-05T03:02:59.127468-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Both reviews approve functional change. One documentation correction before integration: fixture .md must distinguish original live launch8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f from probe/reviewbase70b3566. Correct only that provenance wording, add a new commit on existing branch (do not amend), preserve production/tests/binaryfixture bytes. No repeated tests needed for this prose-only correction; return exactnewSHA and diff. Report phrase "policy untouched" means no other policy changes; admission itself is runtime behavior. Sonnet reported API-equivalent $0.1039654, model verified. Sol UNMETERED. Stop after correction handback; new OKF task being prepared separately.

### 2026-10-05T03:03:16-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Provenance correction committed: new candidate 57920aa822e0cd02131a0db9ff6b6eef3eb61821 on top of 2482e52 (not amended).
Diff (2482e52..57920aa): tools/tests/fixtures/path_entry_20261005.md only, +7/-2. It now distinguishes the T-0009 live launch 8f99951 from
the T-0012/T-0014 probe and review base 70b3566. Verified path_entry.py is byte-identical between them (git diff --quiet).
Production code, tests and the binary fixture are unchanged. Tests not re-run (prose only, as instructed). "Policy untouched" in my
report means no policy change besides this admission comparison.


### 2026-10-05T03:08:20.469170-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0014/sonnet-review-r2.md

**SUPPLEMENTAL REVIEW 57920aa822e0cd02131a0db9ff6b6eef3eb61821** (base 70b3566d91dce8b807fee729dbb110c20db3c764)

**Verdict: ACCEPT, carried forward from 2482e52.** The code verdict is unchanged because, per the coordinator's verification, only the provenance doc changed.

**Correction:** Minor item 3 is resolved. The doc now separates the T9 live launch (8f99951a…) from the probe and review base (70b3566d…).

**Unverified:** The doc says `tools/path_entry.py` is "byte-identical" between 8f99951 and 70b3566. The diff doesn't show this, and the coordinator's checks didn't cover it. Sol should confirm it with a one-time blob comparison.

**Still open from the prior review:** items 1, 2, 4 and 6 (the "observed" wording, the docstring "bounded by" claim, the unrun importer tests, and no rerun of invocation 3).


### 2026-10-05T03:08:20.469170-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0014/sol-review-r2.md

### 2026-10-05T03:07:22.4473342-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0014   Candidate: 57920aa822e0cd02131a0db9ff6b6eef3eb61821   Scope: evidence
Verdict: approve

Findings (ranked, ≤ 5):
1. None. Revision addresses the provenance finding: fixture note now distinguishes actual T-0009 launch 8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f from review/probe base 70b3566d91dce8b807fee729dbb110c20db3c764. Their path_entry blobs are identical.

Observation: clean worktree HEAD matches revised candidate. Full base..candidate range still contains exactly four owned paths. Revision 2482e52..57920aa changes only fixture Markdown. Production path_entry.py, test_path_entry.py and compressed fixture Git blobs are identical to independently reviewed 2482e5288496b9d800c9f2b51b7f2d31ba6259b4; prior fixture/hash/control evidence remains applicable.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: none; read-only git status/rev-parse, full-range stat, revision diff and three blob-identity comparisons. No repeated tests.
Missing acceptance coverage: integration and live latest-grid behavior/time savings; at-limit small-offset generality remains unproven. Documentation correction supplies no new simulation evidence or promotion claim. Usage: UNMETERED.



### 2026-10-05T03:08:20.469170-07:00 · gpt-6-astra → all · DECISION
Accept exactfinalcandidate57920aa822e0cd02131a0db9ff6b6eef3eb61821 afterboth independentreviews. Provenance corrected; unchangedproduction/tests/fixture verified. Numerical allowance is empirical, not a universalbound on biarc conditioning. Pose/footprint/connector/suffix/unknownlethal checks unchanged. No livetimeclaim; combinedsuite will cover importer tests. Sonnetr2 exactmodelverified, API-equivalent $0.0185294; Sol UNMETERED. Integrate exact2commitrange, no squash/auditor mixture.


### 2026-10-05T03:37:42.940616-07:00 · gpt-6-astra → all · INTEGRATION
All constituent integration tests now pass: 500 tools, 85 perception and four GPS (589 unique tests). Initial full-script run stopped on a stale generated board; regenerated board and its five tests pass. Continuation-command ROS environment/CRLF errors were corrected separately; no test failure is concealed. This is not a single clean full-script run. Logs and exact accounting: artifacts/agents/T-0015/integration-validation.json, combined-checks.log, combined-completion-env-error.log and combined-completion.log. Knowledge check and strict check pass with eight concepts, zero errors/warnings. No new live trial or promotion claim.
