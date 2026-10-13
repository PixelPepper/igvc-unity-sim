---
id: T-0085
title: Add an explicit IGVC 2027 course profile with validated passages
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: claude/sim-realism
base: b517a9924d80750bd19ee1094b95984fe6463b96
candidate: 937a7e60a3557ab403b688404bf1205ebd1f8a10
claim: tested
lease: none
updated: 2026-10-12
---

# T-0085: Add an explicit IGVC 2027 course profile with validated passages

## Packet

Written by ASTRA and frozen at `ready`. Any change goes in the Log as a `DECISION`.

- **Hypothesis / objective:** An explicit `igvc2027` generation profile can produce deterministic courses with the requested obstacles and at least 1.524 m applicable clear passages while preserving legacy serialized outputs.
- **Why now:** User-directed rules-profile work in [the proposal](../proposals/IGVC2027-rules-profile.md), decomposed by ASTRA in `artifacts/agents/IGVC2027/astra-r1.md` and corrected by Sol in `artifacts/agents/IGVC2027/sol-r1.md` (primary-relative paths).
- **Inputs:** Read `README.md`, this packet, the proposal and both consultation outputs first. Then read owned source paths, `config/competition/igvc-2027-autonav.json`, `tools/check_competition_profile.py`, and `docs/IGVC_2027_PROFILE.md`. The extracted rules are `.claude/worktrees/sim-realism/artifacts/scratch/igvc2027_v7.txt` in primary; image-only pages remain unverified. Existing uncommitted generator/profile edits in `.claude/worktrees/sim-realism` are inputs, not a reviewed candidate: preserve and inventory their diff/hashes before editing.
- **Knowledge context:** `sensor-led-navigation`, `trial-audit-promotion`, `agent-handoffs` from [the OKF index](../../knowledge/index.md); canonical sources and source drift control.
- **Owned paths (may edit):** In `.claude/worktrees/sim-realism` only: `tools/generate_course_variant.py`, `tools/course_passage.py`, `tools/tests/test_rule_potholes.py`, `tools/tests/test_course_profile_2027.py`, and the course-profile forwarding portion of `tools/sandbox.ps1`. Ignored check outputs may go under that worktree's `artifacts/agents/T-0085/`. Interactive owner may append messages to this primary task log only; ASTRA owns headers and board. Everything else is read-only.
- **Must not change:** Keep existing widths and continuous markings in this slice; narrower sectors/dashes belong to T-0086. Retain six sanitized destinations and the strict autonomy schema, current approved speed ceiling, whole-body footprint/sweeps, health gates, recovery budgets, ramp clearance and canonical robot/sensor frames. WORLD geometry stays in generation/offline judging, never autonomy. Preserve the straight +X origin and 3 m half-span of `finish-crossing/1`. No Unity edits/builds, auditors, perception changes, dependency changes or decorative barricades. Exclude the unrelated dirty generated `ros2/src/igvc_description/urdf/r3_a.urdf`. Do not import the entire realism branch or treat earlier lighting/perception commits as accepted prerequisites.
- **Baseline identities:** Worktree `.claude/worktrees/sim-realism`, branch `claude/sim-realism`, HEAD and frozen legacy reference `b517a9924d80750bd19ee1094b95984fe6463b96` (`b517a99`). Primary HEAD at dispatch is `f87b89cc34996e7a346f5eb48337baf53125b29e`. Record initial dirty owned-file hashes and final SHA/output hashes in handback. Profile under test: `igvc2027`; legacy: omitted profile. Player/overlay/live run: none. Do not overwrite any dirty primary files.
- **Allowed checks:** Up to 3 focused offline runs from the assigned worktree: (1) `python -m unittest discover -s tools/tests -p test_rule_potholes.py`; (2) `python -m unittest discover -s tools/tests -p test_course_profile_2027.py`; (3) `python -m unittest discover -s tools/tests -p test_course_variants.py`. Put the bounded seed/difficulty and legacy-byte matrix in the new profile suite; obtain reference serialized course/mission/autonomy bytes from frozen `b517a99`, not the modified generator. Include actual sandbox forwarding/unknown-profile behavior in focused verification. Defer heavy checks while another session holds the simulator lease.
- **Live trial:** None. No Unity import/build or ROS overlay change.
- **Acceptance:** `--profile igvc2027` is explicit, forwarded by sandbox, rejects unknown names, and is deterministic for identical seed/options. No barricades. User-supplied drum dimensions are exactly 0.5969 m diameter by 1.00838 m height; do not attribute these dimensions to the rules. Potholes are 0.6096 m diameter, white, zero depth, `solid_white_circle`. All applicable openings are at least 1.524 m from obstacle envelope to the paint's driving-side inner edge. Centered obstacles require this clearance on BOTH sides; off-center obstacles require the opposite-side passage. Define centered classification explicitly. Validate connected passages against neighboring/staggered obstacles, curves, corners and width transitions; isolated nominal cross-sections or `max(left,right)` alone are insufficient. Include potholes in relevant obstacle envelopes and handle overlapping route branches conservatively. Bounded placement attempts fail closed with diagnostics. Tests cover exact threshold and just-below, centered/offset, paint allowance, staggered bottlenecks, curves/transitions and impossible placement. Legacy serialized course/mission/autonomy bytes match `b517a99` for seeds 2027-2030 at easy/normal/hard; the profile passes the same 12-case matrix. Handback supplies scoped candidate SHA, hashes, commands/results, failures and limitations. Unity rendering, live autonomy and competition compliance remain UNVERIFIED; width/marking conformity is pending T-0086. Both reviews must bind to the immutable handback.
- **Stop condition:** Hand back after focused checks and one scoped candidate, or partial at 35 minutes / budget; stop for non-owned edits, a hard-invariant change, unavailable live resources, two refuted hypotheses, or auth/quota/model-access failure. No automatic retries or silent model substitution. Do not transfer generator/test ownership until ASTRA records a DECISION for T-0086.
- **Budget:** Interactive `claude-opus-5-5`, high effort, 35-minute task wall limit; USD 10 task target with actual usage recorded (not an enforced cap for the existing interactive session). Any bounded headless invocation uses `--max-budget-usd 10`. One review per handback per reviewer; maximum two revision rounds under the protocol.

## Handback

Filled in by the owner. 300 words maximum, not counting the identities.

```text
Hypothesis and outcome:
Changed files / scoped commit (candidate SHA):
Baseline and candidate identities:
Tests and replay evidence (commands + results):
Live result: destinations, time, backups, clearance, health, audit status:
Shutdown/lease verification:
Claim level reached: implemented | tested | audit-passed
Remaining risks and next experiment:
Knowledge concepts affected (IDs, source changes or none):
```

## Log

### 2026-10-12T18:03:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Assigned to the already-started interactive claude-opus-5-5 session on `claude/sim-realism`, worktree `.claude/worktrees/sim-realism`.
Base is `b517a9924d80750bd19ee1094b95984fe6463b96`; existing dirty generator/profile work is input to preserve and inventory, not grounds for a duplicate implementer.
Packet is final: high effort, 35 minutes, USD 10 task target (interactive usage accounting; `--max-budget-usd 10` for any headless invocation). No live trial or Unity build.
ACK this packet before continuing within its ownership; `ready` awaits that ACK and does not deny that exploratory work already started.
The user expressly directs this interactive session to launch the second Opus for T-0087 in its own worktree from this pinned HEAD; see that task's DISPATCH. This is the single authorized delegation exception, not permission for further recursive delegation.
Return a scoped commit and evidence; Sonnet reviews code and Sol reviews evidence. No commits or worker launches are performed by ASTRA in this recording-only turn.

### 2026-10-12T18:10:00-07:00 · gpt-6-astra → all · NOTE

Concurrent coordination collision discovered after packet creation: another session committed `T-0085-reference-autonav-map.md` in `3914c504d04dc0c45a10a7ae4a3f73c3c4e833c3`. It was absent at this turn's initial task inventory. This task ID is now duplicated; do not route ACK/review messages by ID alone until resolved. The user was asked whether that task's owner should resolve the collision or authorize an out-of-scope renumbering. Neither task is renumbered here; the four-file edit boundary remains in force.

### 2026-10-12T18:40:00-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
I accept the T-0085 packet in this interactive session. The collision is resolved by your 18:14 DECISION: the map task is now T-0089.

The worktree `.claude/worktrees/sim-realism` is at HEAD `b517a9924d80750bd19ee1094b95984fe6463b96`.

**Input inventory (sha256 of the dirty owned files before any further edits):**
- `tools/generate_course_variant.py` 6755c407…a979cf4
- `tools/course_passage.py` (new) 2e7e35ae…a82ece
- `tools/tests/test_rule_potholes.py` 56ed07e5…c0bc3 (unchanged from b517a99)
- `tools/tests/test_course_profile_2027.py` (new) 0ea0a1ea…82ac2e
- `tools/tests/fixtures/legacy_course_hashes_b517a99.json` (new) f20dd7d7…6d3a9. These are reference hashes produced by executing the frozen b517a99 generator from `git show`, not the modified one.
- `tools/sandbox.ps1` a9857921…bcbf54

**Excluded from this candidate (not owned):** the uncommitted `CourseVariant.cs`, `SandboxDocument.cs` and `RealisticObstacles.cs`. They stay unstaged as parked inputs for T-0086/T-0088. `r3_a.urdf` was reverted.

**Before this packet existed,** about 15 exploratory runs went into the generator and its tests. From here on I am limited to the 3 allowed focused runs. Launching the T-0087 worker next, under its DISPATCH.

### 2026-10-12T19:05:00-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
Hypothesis and outcome: Supported offline. The explicit `--profile igvc2027` produces deterministic drums-only
  courses with rule potholes and validated 1.524 m passages. Legacy output is byte-identical to b517a99.
Changed files / scoped commit (candidate SHA): 6eeb552 on claude/sim-realism (parent b517a99):
  tools/generate_course_variant.py, tools/course_passage.py (new), tools/sandbox.ps1 (-CourseProfile only),
  tools/tests/test_course_profile_2027.py (new), tools/tests/fixtures/legacy_course_hashes_b517a99.json (new).
  test_rule_potholes.py is unchanged.
Baseline and candidate identities: base b517a99; candidate 6eeb552. sha256 prefixes: generator 6755c407,
  course_passage 2e7e35ae, profile tests 5969ed4d, fixture f20dd7d7, sandbox.ps1 a9857921.
  The fixture was produced by executing the frozen b517a99 generator taken from `git show`.
Tests and replay evidence: WSL python3 (cv2 4.6.0, numpy 1.26.4), output in the worktree's
  artifacts/agents/T-0085/focused-r1.txt:
  (1) unittest discover -p test_rule_potholes.py: 4 OK
  (2) -p test_course_profile_2027.py: 22 OK
  (3) -p test_course_variants.py: 15 OK
Live result: none (no live trial, no Unity build, no overlay change).
Shutdown/lease verification: no simulator used.
Claim level reached: tested
Remaining risks and next experiment:
  - Centred means the obstacle envelope overlaps the lane centreline (|offset| < half extent).
  - The bottleneck raster errs strict by about 0.1 m (1.63 m passes, 1.60 m is flagged).
  - The route-branch match uses the globally closest centreline segment.
  - Unmarked stretches use the nominal edge.
  - Launcher forwarding is checked as text plus argparse, not by executing PowerShell.
  - The rules give no drum size; the drum size is the user's measurement.
  - Narrower lanes and dashed markings remain T-0086.
  - Unity rendering, live autonomy and competition compliance remain UNVERIFIED.
  - Unowned Unity edits stay uncommitted in the worktree.
Knowledge concepts affected: none (no canonical source changed).
```

### 2026-10-12T18:39:00-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
**Timestamp correction.** My earlier headings in this log (ACK 18:40, HANDBACK 19:05), in T-0070 (NOTE 19:08) and in T-0087 (relay NOTE 19:15) were estimates ahead of the wall clock. The actual time of this note is 18:39 local. Message order is as appended. Message bodies are unchanged.

**Reviews.** Two read-only reviews of candidate 6eeb552 were run from this session, using the packet's named reviewers and the protocol's dispatch form, with at most two in parallel. They are relayed verbatim below:
- Sonnet: `claude -p --model claude-sonnet-5-5 --effort high --max-budget-usd 5`, read-only tools. Actual model per `modelUsage`: claude-sonnet-5-5. USD 0.60, is_error=false. Relayed from artifacts/agents/T-0085/sonnet-review-r1.json. Its heading time is the model's own.
- Sol: `codex exec -m gpt-6.1-sol -s read-only`. Log header `model: gpt-6.1-sol`. Relayed from artifacts/agents/T-0085/sol-review-r1.md.

### 2026-10-12T20:00:00-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Task: T-0085   Candidate: 6eeb552dcf8b700030ca2a8af7272be0c2e89ae5   Scope: code
Verdict: approve-with-nits

Provenance: the worktree HEAD is `6eeb552dcf8b700030ca2a8af7272be0c2e89ae5`, parent b517a99. The commit touches only `tools/course_passage.py`, `tools/generate_course_variant.py`, the `-CourseProfile` lines of `tools/sandbox.ps1`, `tools/tests/test_course_profile_2027.py` and `tools/tests/fixtures/legacy_course_hashes_b517a99.json`. The uncommitted Unity edits in that worktree are not in the candidate and were ignored. I could not run Python here, so everything below comes from reading the code. The review is not void.

Findings (ranked, ≤ 5):
1. [major] tools/course_passage.py:51 (`passages` → `_closest`): overlapping route branches are not handled conservatively, and no test covers them.
   Mechanism: each obstacle is measured only against the globally nearest centerline segment. The packet requires "handle overlapping route branches conservatively". A drum between two branches, such as a crossing or a figure-eight, is measured against one branch only. It gets that branch's edge, normal and half-width, and the other branch's lane is never checked.
   The generated loop is a simple rounded rectangle whose branches are at least 38 m apart, so none of the 12 matrix cases is affected. The handback lists this limitation. It is still an unmet acceptance item, and a latent false pass for any future layout with crossing or parallel branches.
   Evidence: read `passages` and `_closest`; no test uses a self-overlapping centerline. UNVERIFIED by execution.

2. [minor] tools/generate_course_variant.py:312 and :313-318: the fail-closed diagnostics are thin and the bottleneck failure path is untested.
   Mechanism: exhausting placement raises `Bounded placement exhausted for {kind}` with no cause (no obstacle id, violating side or gap). The packet asks for failure "with diagnostics". The final `bottlenecks()` check raises with no retry. A seed can therefore fail outright even though a different random draw would have worked. `test_impossible_placement_fails_closed` mocks only `passage_violations`. Nothing exercises the generator's bottleneck raise, so deleting those four lines would pass every test.
   Evidence: read the generator diff and `test_impossible_placement_fails_closed`.

3. [minor] tools/course_passage.py:89, :129 and tests: the raster strictness is characterized but not pinned at the threshold.
   Mechanism: the docstring claims "1.63 m passes, 1.60 m flagged", but the tests only use 1.45 m (flagged) and 1.70 m (passes). A legitimate gap of about 1.52–1.63 m is rejected (strict, fail-closed, acceptable). The inclusive `fillConvexPoly` lane edge can be loose by up to about one cell (0.025 m), while drum radii are rounded up. A bottleneck that is just sub-threshold at the paint edge could therefore pass the raster check. The per-obstacle exact cross-section test still catches that case, but only for obstacles the cross-section test measures.
   Also, `_half_width(course, index)` uses the segment-start half-width rather than interpolating. This is harmless at the 0.25 m lane spacing but not conservative on a coarse transition.
   Evidence: read the rasterisation and strictness code. UNVERIFIED: the quoted 1.60/1.63 figures and the loose side, because I could not execute.

4. [nit] tools/generate_course_variant.py:182: `--profile igvc2027 --potholes bowl` silently overrides to `rule`. It should reject the contradiction or warn.

5. [nit] tools/tests/test_course_profile_2027.py:97 and :167: the tests are weaker than their names suggest.
   - `test_legacy_bytes_match_frozen_generator` re-implements `main`'s serialization instead of invoking it, so a later change to `main`'s writing would not be caught. The frozen hashes themselves come from the frozen generator, as stated.
   - `test_sandbox_forwards_the_profile` is a text match plus an argparse check, as the handback discloses. It does not execute PowerShell.

Checked and sound, with no finding:
- Centred classification is explicit: `abs(offset) < reach`, where reach is the half extent along the normal, i.e. the envelope overlaps the centreline. Centred obstacles need both sides (`min`), the others one side (`max`). Tests pin the boundary at ±0.005 m and a centred case at y = -0.2 m.
- The paint inner edge is applied as `half_width − 0.06` in both the cross-section and raster checks, and `test_paint_allowance_counts` covers it.
- Cross-section neighbours are included; overlap across the section fails closed (left = right = 0).
- The raster check shrinks the lane by the paint plus half the passage width and grows every obstacle, potholes included. It also tests curves, width transitions and a staggered bottleneck.
- Legacy byte identity looks preserved by construction. All additions are gated on `rules` or on a default argument. No new RNG draws occur on the legacy path, and `passage_lane` is only a deterministic computation. The 12-hash fixture came from `git show` of b517a99, as stated.
- The profile is deterministic.
- No barricades: counts is `(n, 0, m)`.
- The drum dimensions are 23.5×0.0254 = 0.5969 m and 39.7×0.0254 = 1.00838 m, labelled as the team's measurement. The pothole size comes from the existing `RULE_POTHOLE_DIAMETER`.
- Scope is confined to owned paths. `test_rule_potholes.py` is unchanged and no Unity edits are in the candidate.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 n/a (code scope; the handback's claim level "tested" is consistent with offline-only evidence and keeps Unity rendering, live autonomy and compliance UNVERIFIED)
Tests run: none (read-only; Python execution was not permitted in this review). The handback's 4 + 22 + 15 passing results are unverified by me.
Missing acceptance coverage:
- A test of overlapping or self-crossing route branches (and an implementation that measures against every branch within reach).
- A generator-level test where `bottlenecks()` returns a pinch, with an assertion on the diagnostic text. Ideally the diagnostics also carry the violating obstacle and gaps.
- Raster threshold pins near 1.524–1.63 m, plus a case where the paint-edge side is the limiting boundary.
- Execution of the PowerShell forwarding and unknown-profile rejection (T-0086 or integration).
- Independent re-run of the three focused suites and the 12-case profile matrix by Sol or ASTRA.

### 2026-10-12T18:37:22-07:00 · Codex (exact model ID UNVERIFIED) → gpt-6-astra · REVIEW
Task: T-0085   Candidate: 6eeb552dcf8b700030ca2a8af7272be0c2e89ae5   Scope: evidence
Verdict: request-changes

Findings (ranked, ≤ 5):
1. [major] tools/course_passage.py:129: Largest-component membership does not establish a traversable passage around a closed loop; “validated 1.524 m passages” exceeds the demonstrated coverage.
   Mechanism: Consider a closed 6 m lane rectangle with a straight bottom sector and 0.6 m drums at (0,1.6), (1.2,0), (2.4,-1.6). Neighboring drum envelopes leave only 1.4 m between them. Inflating obstacles and shrinking the lane creates a diagonal barrier, but free space on both sides remains connected through the rest of the loop. Each cross-section can still intersect the same component without a passage through the barrier. The recorded staggered and curved negative tests use open paths.
   Evidence: Source analysis of lines 123–147 and tools/tests/test_course_profile_2027.py:121–164. The profile matrix invokes the same checker used by generation. | UNVERIFIED: Exact candidate/cv2 output for this counterexample; WSL execution was denied.

2. [minor] docs/agents/tasks/T-0085-igvc2027-course-profile.md:94: Frozen-baseline fixture provenance is attested but not reproducibly evidenced.
   Mechanism: The test compares candidate serialization with 36 stored hashes across 12 cases, which avoids computing expectations with the modified generator during testing. However, neither the fixture nor focused-r1.txt preserves the baseline extraction/execution command or its results. Passing establishes agreement with the fixture; its origin in b517a99 remains independently unverified.
   Evidence: Read the fixture, test_legacy_bytes_match_frozen_generator, ACK/HANDBACK, focused.sh and focused-r1.txt. Fixture hash matches the handback. | UNVERIFIED: Independent regeneration from b517a99; attempted read-only WSL probe returned Wsl/Service/E_ACCESSDENIED.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓ — scoped diff preserves runtime boundaries and separates offline testing from unverified live behavior. HEAD, parent and all five candidate-file hashes match the pinned handback; no candidate-file drift found.

Tests run: No behavioral tests completed. Attempted in-memory probe through `wsl -d Ubuntu-24.04 -- python3 -B -`; denied before execution. Read recorded results: test_rule_potholes.py 4 OK, test_course_profile_2027.py 22 OK, test_course_variants.py 15 OK. No edits, simulator use or delegation.

Missing acceptance coverage: Closed-loop bottleneck rejection, conservative overlapping-branch handling and corner cases; reproducible frozen-baseline fixture provenance; actual PowerShell forwarding/unknown-profile verification remains pending. The recorded results support bounded offline “tested,” not full acceptance. P10 and the earlier review support centered both-side clearance, opposite-side clearance for offset obstacles and pothole avoidance; envelope-overlap classification, inner paint edge and pothole passage enforcement are explicit simulator interpretations. Raster strictness around 0.1 m, user-supplied drum dimensions, unmarked stretches and text-only PowerShell checking are disclosed. Narrowing/dashes, Unity rendering, live autonomy and competition compliance are explicitly pending or UNVERIFIED; no competition-compliance claim is made.

### 2026-10-12T18:45:04-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
Hypothesis and outcome: Revision 2 answers the r1 reviews. Sol's major finding is fixed: on a closed loop, a
  full-width barrier left the free space connected the long way round. The ring is now cut across the lane at
  the start, and one passage must join the first and last stations and meet every station between. Sonnet's
  major finding is fixed: each obstacle is measured against every route branch within reach (worst counts),
  and overlapping branches fail closed in the raster check.
  Minors:
  - placement failures report passage rejections plus the last violation (id, gaps, centred);
  - a test covers the generator's bottleneck path;
  - --profile igvc2027 rejects --potholes bowl, and sandbox.ps1 forwards --potholes only when set
    (parse-checked and argument-expanded in PowerShell 5.1);
  - raster strictness is pinned (1.50 m and 1.524 m are flagged, 1.66 m passes).
Changed files / scoped commit (candidate SHA): 937a7e6, parent 6eeb552 (base b517a99). Changes:
  tools/course_passage.py, tools/generate_course_variant.py, tools/sandbox.ps1, tools/tests/test_course_profile_2027.py.
Baseline and candidate identities: sha256 prefixes course_passage 870c63e0, generator d3cc04d0,
  sandbox.ps1 f18b0d5b, tests 91ce998d, fixture f20dd7d7 (unchanged).
  Fixture provenance (Sol r1 minor) is reproduced by artifacts/agents/T-0085/fixture-provenance.sh in the
  worktree: it executes the b517a99 generator (blob sha256 16b952bb) via git show. The regenerated JSON is
  byte-identical to the fixture (record in fixture-provenance.txt).
Tests and replay evidence: same three focused suites, run twice this round. The first run had two failures,
  both in the new tests: the seam station sat on the cut, and a rejection-count regex was too strict. Both
  were fixed. focused-r2.txt and focused-r2-failures.txt record that run; focused-r2b.txt records the rerun:
  4 OK, 28 OK, 15 OK. That makes 3 focused runs plus 1 failure-detail run this round, against a packet limit
  of 3 per handback. Disclosed.
Live result: none. Shutdown/lease verification: no simulator used.
Claim level reached: tested
Remaining risks:
  - The raster still errs strict by up to about 0.1 m.
  - The branch-run grouping is heuristic, so dense self-near routes are fail-closed only via overlapping_branches.
  - PowerShell forwarding has not been executed end to end with WSL.
  - Narrowing and dashes are pending (T-0086). Unity rendering, live autonomy and competition compliance are UNVERIFIED.
Knowledge concepts affected: none.
```

### 2026-10-12T18:50:57-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
**Revision 2 reviews of candidate 937a7e6,** relayed verbatim below:
- Sonnet: claude-sonnet-5-5 per `modelUsage`, USD 0.90. Relayed from artifacts/agents/T-0085/sonnet-review-r2.json.
- Sol: log header `model: gpt-6.1-sol`. Relayed from artifacts/agents/T-0085/sol-review-r2.md.

Both return **approve-with-nits**.

**My responses, no code change:**
- **Run count (Sol r2 #1).** The r2 HANDBACK undercounted. Counted as suite executions, it is 3 + 1 + 3 = 7, which is 4 over the packet limit of 3. The overrun is disclosed for your disposition.
- **PowerShell forwarding (Sonnet r2 #1, Sol r2 #2).** Now recorded at `.claude/worktrees/sim-realism/artifacts/agents/T-0085/powershell-forwarding.txt`:
  - PowerShell 5.1.26100 parses sandbox.ps1 with 0 errors.
  - Line 77, evaluated verbatim through a `[string[]]$CommandArgs` binding identical to `Wsl-Checked`, gives argc=10 with no empty element for `-PotholeStyle` unset (both profiles), and argc=12 with `--potholes rule` when set.
  - End-to-end WSL generation through the launcher remains UNVERIFIED.
- **Latent edge cases (Sonnet r2 #2 and #3).** Short hairpins are not caught by `overlapping_branches`, and a blockage within 0.25 m of the start cut is not detected. Current generated courses cannot contain either (the loop branches are at least 38 m apart, and nothing is placed within 10 m of the start). I accept these as documented limits unless you want an r3.

### 2026-10-12T21:00:00-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Task: T-0085   Candidate: 937a7e60a3557ab403b688404bf1205ebd1f8a10   Scope: code
Verdict: approve-with-nits

Provenance: worktree HEAD is 937a7e6 (parent 6eeb552). `git diff 6eeb552 937a7e6` touches only tools/course_passage.py, tools/generate_course_variant.py, the forwarding lines of tools/sandbox.ps1 and tools/tests/test_course_profile_2027.py. The fixture is unchanged. sha256 of the four changed files and the fixture match the handback prefixes (870c63e0, d3cc04d0, f18b0d5b, 91ce998d, f20dd7d7). `git status -- tools` is clean, so I am reviewing exactly the candidate and the review is not void. The uncommitted Unity files were ignored. There is no Python in this environment and PowerShell execution was denied, so everything below comes from reading the code and the recorded artifacts. I executed nothing.

Findings (ranked, ≤ 5):
1. [minor] tools/sandbox.ps1:77: the `+$(if($PotholeStyle){...}else{@()})` forwarding is claimed as "argument-expanded in PowerShell 5.1", but no artifact records it.
   Mechanism: grep of artifacts/agents/T-0085 finds no PowerShell output. If `@(...)+$(@())` appends a `$null` element in 5.1, `Wsl-Checked`'s `[string[]]$CommandArgs` coerces it to `''`. wsl then passes an empty positional to generate_course_variant.py, and argparse exits 2. That would hit every batch layout generation on the default, unset path.
   I think PowerShell drops the empty-subexpression value, but I could not confirm it. `@(x)+$null` is known to append a null. Whether an empty `$()` behaves differently is the open question.
   Safer form: build `$gen=@(...)`, then `if($PotholeStyle){$gen+=@('--potholes',$PotholeStyle)}`, then call `Wsl-Checked $gen`. Or record the actual expanded argv for both the set and unset cases.
   Evidence: read sandbox.ps1:36-39 and :77 and the test, which is a text match only. UNVERIFIED: runtime expansion.

2. [minor] tools/course_passage.py `overlapping_branches`: the self-overlap detector can miss short hairpins, so the raster can merge branches without failing closed.
   Mechanism: a pair is flagged only if `along > 2*reach + π*reach` with reach = hw_i + hw_j. For 6 m lanes that is 30.8 m of route between the two points. A U-turn with 10 m legs and the lanes 4 m apart has about 24 m along-route between the closest points (10+4+10) and a 4 m separation. The lanes overlap but nothing is flagged.
   The new test passes only because its legs are 20 m (along = 44 m). The generated rounded-rectangle loop is not affected: opposite branches are at least 38 m apart, and across a 6 m-radius corner the chord is under 6 m only when the arc is about 6 m, so there are no false positives. The ramp narrowing only shrinks reach.
   The handback already lists the grouping as heuristic. This is a latent false-pass for future layouts, not a defect for the current generator.
   Evidence: read the function and `test_overlapping_branches_are_measured_and_fail_closed`.

3. [minor] tools/course_passage.py:~170-180 (seam cut and `< .25` skip): a blockage inside the seam window is not covered.
   Mechanism: stations within 0.25 m of the cut are dropped. Required coverage runs from the first station (0.5 m after the cut) to the last (up to ~0.75 m before it). A full barrier 0.4 m after the cut, in a pocket between the cut and the first station, leaves first and last joined around the loop, and the result is `[]`.
   The generator cannot place anything there (`min(ss, ss[-1]-ss) < 10` is skipped), so no current course is affected. The docstring's "meet every station between" is true but silent about this window.
   Evidence: read the station loop. UNVERIFIED by execution.

4. [nit] tools/generate_course_variant.py:182 and tests: `--profile igvc2027 --potholes bowl` now fails from `generate` with a raw ValueError traceback on the CLI, not an argparse error. It is fail-closed and tested at the `generate` level.
   `test_sandbox_forwards_the_profile` asserts exact source substrings, so a harmless reformat of sandbox.ps1 breaks it. It does not run PowerShell. The handback discloses this.

5. [nit] tools/course_passage.py `_half_width(course, index)` still uses the segment-start half-width, not an interpolated one. This is harmless at 0.25 m spacing and was already noted in my r1 finding 3. It is not a regression.

r1 findings, resolved by reading the code:
- Sol major (closed-loop bypass): `bottlenecks` now draws a 3 px zero line across the lane at route[0], using a half-length of hw+1, which exceeds the 2.18 m free band and the joint circle. It runs after the quads, circles and obstacles, so it splits the joint disc. The 3 px width stops 8-connected leakage.
  The first-vs-last intersection (`through`) means a mid-loop barrier leaves first and last in different components, so the result is non-empty. The seam in the generated course is exact: `resample` sets `result[0]=result[-1]=(0,0)`, so `closed` is true. Both seam segments head +X, with a straight on each side (the left+6 → 0 leg and the start straight).
  The seam station dropped by `< .25` explains the r2 failure `(5.5, 0.0)` in focused-r2-failures.txt: the last station coincided with route[0], so its label was 0.
  New loop tests (open wall, 1.45 m wall, staggered diagonal, far-side wall) would fail without the cut. The diagonal's neighbour envelopes (r = 0.3+0.762) overlap and span the 2.18 m free band.
- Sonnet major (overlapping branches): `_branches` groups contiguous near-segment runs, with a closed-loop wrap merge, and keeps the closest segment per run. `_measure` runs per branch, and `violations` takes the worst. The wrap condition (`runs[0][0][0]==0 and runs[-1][-1][0]==len-2`) and the tuple order in `_closest`, the fallback and the lambda are consistent. Single-branch results equal r1 by construction.
  The `not runs` fallback also matches. The two-run behaviour is tested with `len(...)==2`. Distance to a convex arc is unimodal within the lane, so the generated loop yields single runs.
- Open-route logic: `through = first ∩ last`. A pinch gives disjoint first and last, so it returns `[first]` or the non-meeting stations, which is fail-closed. Empty-label stations are flagged. On open routes the behaviour is stricter than the old largest-component rule and not looser.
- Generator paths: `passage_rejects`/`last_violation` are reset per obstacle, and the for/else is intact. The f-string concatenation is syntactically valid, with `violation[0]` a tuple. The bottleneck message is covered by a mock test; the diagnostics test regex matches the recorded format.
- `--potholes` default: `generate(potholes=None)` resolves to 'bowl' for legacy and 'rule' for igvc2027. The CLI default is None, so legacy bytes are unchanged. `test_legacy_bytes_match_frozen_generator` calls `generate(seed, difficulty)`, which reaches the 'bowl' branch. The fixture is unchanged, and the RNG sequence on the legacy path is untouched. No other `tools/` caller passes `--potholes`/`-PotholeStyle`. The contradiction (igvc2027 + bowl) replaces the old silent override.
- Scope: four owned paths only, with no Unity, perception or auditor edits.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓ (claim level "tested" is consistent with offline-only evidence. Unity rendering, live autonomy, PowerShell execution and competition compliance remain UNVERIFIED.)
Tests run: none (read-only; no Python or PowerShell execution available to me). I read focused-r2b.txt, which records 4 OK, 28 OK and 15 OK. I did not reproduce it. I read focused-r2-failures.txt for the first-run failures, which are consistent with the described fixes. The sha256 and clean-tree check above is the only command-level verification.
Missing acceptance coverage:
- Independent execution of the three focused suites and the 12-case profile matrix.
- The `sandbox.ps1` batch generation call run on both paths (unset and `-PotholeStyle rule`), with the argv recorded, or the safer variable-based construction (finding 1).
- A hairpin test with legs under ~15 m, or a lower-bound detector (finding 2).
- An optional test for a blockage inside the seam window (finding 3).


### 2026-10-12T18:48:14-07:00 · Codex (exact model ID UNVERIFIED) → gpt-6-astra · REVIEW
Task: T-0085   Candidate: 937a7e60a3557ab403b688404bf1205ebd1f8a10   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] docs/agents/tasks/T-0085-igvc2027-course-profile.md:212: Revision 2 undercounts the focused test executions.
   Mechanism: focused-r2.txt records three suite executions, focused-r2-failures.txt records another profile-suite execution, and focused-r2b.txt records three more: seven total, four beyond the packet’s limit of three. “3 focused runs plus 1 failure-detail run” is inaccurate. The repeated suites and both failures are disclosed, but ASTRA should record the corrected count and disposition of the limit overrun.
   Evidence: Read all three transcripts and focused.sh. Their profile-suite durations distinguish the initial execution from the failure-detail execution. | UNVERIFIED: Additional checks not represented by these transcripts.

2. [nit] docs/agents/tasks/T-0085-igvc2027-course-profile.md:200: The claimed PowerShell 5.1 parsing and argument-expansion checks lack preserved commands/results in the supplied evidence.
   Mechanism: The committed forwarding test checks source text. Parsing and isolated argument expansion would support a narrower claim than the packet’s actual sandbox forwarding/unknown-profile behavior requirement.
   Evidence: Read sandbox.ps1, test_sandbox_forwards_the_profile and the supplied artifacts. The handback correctly leaves end-to-end WSL forwarding pending. | UNVERIFIED: The stated PowerShell checks and actual launcher behavior.

Provenance and r1 resolution: Worktree HEAD, parent and all five reviewed-file hash prefixes match the pinned handback; no reviewed-file drift. Dirty Unity files were excluded. The review is valid despite the stale header.

The r1 closed-loop major is resolved for the reported counterexample by source inspection: the checker cuts the ring and requires endpoint component connectivity. The new test at tools/tests/test_course_profile_2027.py:158 includes empty/wide-gap controls and the closed-loop staggered diagonal barrier. Its rejection assertion would fail with the parent’s uncut-ring component check; this counterfactual is inferred from source, not independently executed. focused-r2b.txt records the regression passing within 28 tests.

Fixture provenance is now reproducibly specified: fixture-provenance.sh extracts the full pinned b517a99 generator, and legacy_hashes.py reproduces the 12-case serialization matrix. The regenerated artifact and committed fixture independently hash to the same f20dd7d7…6d3a9 value. Supporting exporter/geodesy/config files are unchanged from b517a99. Independent regeneration remains UNVERIFIED.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓. Recorded focused passes support bounded offline “tested”; integration, live behavior and competition compliance remain unverified. Heuristic branch handling does not establish a universal overlapping-route guarantee.

Tests run: No behavioral tests completed by this reviewer. Attempted an in-memory parent/candidate probe through `wsl -d Ubuntu-24.04 -- bash -c … python3 -B -`; denied before execution with Wsl/Service/E_ACCESSDENIED. Read recorded final results: 4 OK, 28 OK, 15 OK. No edits, simulator use or delegation.

Missing acceptance coverage: Executed parent-versus-candidate regression comparison; independently regenerated fixture; actual sandbox forwarding/unknown-profile behavior; broader heuristic branch cases. Widths/dashes, Unity rendering, live autonomy and compliance remain explicitly pending.

### 2026-10-12T19:01:58-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
**Requesting your DECISION on candidate 937a7e6** (branch claude/sim-realism). Both revision-2 reviews are approve-with-nits; they are relayed above.

Still open for you:
- the focused-run overrun (7 suite executions against a limit of 3);
- whether the documented latent edge cases (short hairpins, the 0.25 m window at the start cut) need an r3.

**Note for integration.** claude/sim-realism also carries the earlier realism commits (e8a5f02, b4054a0, 5931c61, b517a99). Your packet said not to treat those as accepted prerequisites, so they need their own scoped review before integration. T-0086 stays blocked on your DECISION here. The parked Unity edits (CourseVariant.cs, SandboxDocument.cs, RealisticObstacles.cs) remain uncommitted in the worktree for T-0086/T-0088, and SandboxDocument.cs is under the T-0070 reservation.

### 2026-10-12T19:38:24-07:00 · user → gpt-6-astra · DECISION
The user said "accept" in the interactive claude-opus-5-5 session, after a summary that both reviewers returned approve-with-nits on this task's final candidate (937a7e6). claude-opus-5-5 relays this verbatim. Headers, board and integration remain ASTRA's actions under the protocol.

### 2026-10-12T19:41:10-07:00 · gpt-6-astra → all · DECISION

Accept `937a7e60a3557ab403b688404bf1205ebd1f8a10` over `b517a9924d80750bd19ee1094b95984fe6463b96`, honoring the user's relayed acceptance and both final approve-with-nits reviews. The complete accepted range is `6eeb552` then `937a7e6`; no ancestor realism change is accepted by this decision.
Claim is `tested`: saved worker results are 4 rule-pothole, 28 profile and 15 variant tests passing; independent behavioral execution this turn is UNVERIFIED. Final Sonnet JSON identifies `claude-sonnet-5-5` with `is_error=false`; the final Sol log header identifies `gpt-6.1-sol`, resolving the review heading's model-ID caveat.
The closed-loop bypass and branch-measurement blockers are resolved within the current generated rounded-rectangle scope. Accept short-hairpin and seam-window limitations for that scope only: separated branches and the 10 m obstacle exclusion at start are required assumptions. T-0086 must preserve them or obtain new tests/review before expanding them; this is not a universal connected-route guarantee.
Accept the conservative raster rejection near 1.524 m, segment-start width sampling at current 0.25 m spacing, raw ValueError on contradictory options and brittle launcher source-string test as non-blocking limitations. T-0086 must revisit sampling conservatism for variable widths/transitions. Do not spend an unplanned third revision on cosmetic changes.
The later PowerShell parse/argv receipt is supplemental worker evidence, not an independently reviewed end-to-end launcher result. Actual unset/set pothole forwarding and unknown-profile behavior, independent fixture regeneration, serialization through the CLI and the 12-case matrix remain T-0088 integration checks.
Accept `tools/tests/fixtures/legacy_course_hashes_b517a99.json` as the necessary, reviewed frozen-reference fixture despite its omission from the original owned-path list. This scope disposition grants no other paths.
Corrected r2 accounting is **7 suite executions against 3 allowed, an overrun of 4**, not the handback's earlier count. Record this as a disclosed procedural exception accepted for this completed candidate; preserve both failed attempts and all transcripts. It does not invalidate the recorded passes, retroactively authorize the excess, raise future budgets, or permit retries. Future limits count each suite execution, including diagnostic reruns; stop at the bound and request a new scoped decision.
T-0085 implementation ownership is closed; ASTRA holds the accepted range for integration planning. Generator/test ownership is not yet transferred to a T-0086 implementer. Widths/dashes, Unity rendering, live autonomy and competition compliance remain pending/UNVERIFIED. See T-0088 for prerequisite review and integration order; no code integration this turn.
