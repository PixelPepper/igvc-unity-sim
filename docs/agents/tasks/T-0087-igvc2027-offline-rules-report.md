---
id: T-0087
title: Report IGVC 2027 timing and rule observations from recorded evidence
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0087-igvc2027-report-opus
base: b517a9924d80750bd19ee1094b95984fe6463b96
candidate: 1f701b87b9821c4259866d09f8b17ad1c814626e
claim: tested
lease: none
updated: 2026-10-12
---

# T-0087: Report IGVC 2027 timing and rule observations from recorded evidence

## Packet

Written by ASTRA and frozen at `ready`. Any change goes in the Log as a `DECISION`.

- **Hypothesis / objective:** A read-only offline report can compare recorded driving duration with 360 seconds and expose supported ticket observations without changing runtime behavior, auditor verdicts or unresolved official scoring semantics.
- **Why now:** The user requested six-minute lap reporting alongside the course profile; [the proposal](../proposals/IGVC2027-rules-profile.md) and `artifacts/agents/IGVC2027/astra-r1.md` assign this independent slice to a second Opus.
- **Inputs:** `README.md`, this packet, the proposal, `artifacts/agents/IGVC2027/astra-r1.md`, `artifacts/agents/IGVC2027/sol-r1.md`, `config/competition/igvc-2027-autonav.json`, `tools/check_competition_profile.py`, `tools/tests/test_competition_profile.py`, `docs/IGVC_2027_PROFILE.md`, and the recorded run/audit formats in `tools/audit_sensor_run.py` and `tools/course_judge.py` (read-only). Extracted rules: primary `.claude/worktrees/sim-realism/artifacts/scratch/igvc2027_v7.txt`; missing image pages/extraction defects preclude certification. Use bounded synthetic recorded-evidence fixtures in tests; do not assume old laps have official ticket or driving-clock observations.
- **Knowledge context:** `trial-audit-promotion`, `processing-health`, `sensor-led-navigation`, `agent-handoffs` from [the OKF index](../../knowledge/index.md); read canonical source formats and check drift.
- **Owned paths (may edit):** Only new `tools/rules_score_2027.py` and `tools/tests/test_rules_score_2027.py` in the separate T-0087 worktree. Ignored test/review outputs under that worktree's `artifacts/agents/T-0087/`. Headless sub-agent returns message blocks; it does not edit primary coordination records. Everything else is read-only.
- **Must not change:** Existing competition profile/checker, runtime, shared schemas/interfaces, `tools/audit_sensor_run.py`, `tools/course_judge.py`, and their acceptance thresholds. Reuse the existing profile/checker for overlapping constants/checks; any missing rule interpretation must be explicitly sourced and qualified, not a conflicting second profile. Never use offline WORLD geometry in autonomy, alter six-goal missions, raise speed, or infer audit pass from 6/6 progress. T-0084 stays blocked and T-0079 unresolved; this task does not resume either. No Unity/ROS/live operation, perception changes or decorative geometry.
- **Baseline identities:** Fork the current committed HEAD of `claude/sim-realism`, pinned at dispatch to `b517a9924d80750bd19ee1094b95984fe6463b96`, into branch `codex/t0087-igvc2027-report-opus`, worktree `.claude/worktrees/igvc2027-rules-report`. Do not copy T-0085's dirty edits. If the branch moved before launch, record the discrepancy and obtain ASTRA's base DECISION instead of silently changing it. Record candidate, profile/checker/input/output hashes and usage in handback. Player/overlay/live run: none. Inherited realism commits are not accepted for integration by this assignment.
- **Allowed checks:** Up to 3 focused offline runs from the isolated worktree: (1) `python -m unittest discover -s tools/tests -p test_rules_score_2027.py`; (2) `python -m unittest discover -s tools/tests -p test_competition_profile.py`; (3) `python tools/rules_score_2027.py --help` and one documented bounded CLI fixture invocation as a single smoke-check batch. Tests exercise the CLI as well as report behavior and input immutability. Defer heavy checks during an active live lease; do not request a simulator.
- **Live trial:** None. Read recorded evidence only.
- **Acceptance:** Structured deterministic JSON includes provenance hashes, source/check identifiers, observed values, expected values and pass/fail/unknown with `certification=false`. Test below/exactly/above 360 s. Distinguish driving runtime, wall elapsed, pauses/overtaking and incomplete duration evidence; missing/incomparable clocks remain unknown. Report timing separately from completion, health and unchanged independent audit verdicts. Represent the II.4 ticket categories and cited nominal amounts/termination flags without inventing official signed arithmetic or definitive adjusted rankings. Preserve the unresolved 44 ft/30 s versus 88 ft/60 s speed windows, whole-run average/qualification limits and missing judge evidence as unknown or explicitly qualified diagnostics. Do not infer official finish crossing from six-goal completion. Validate malformed/nonfinite time and event data, missing fields, mismatched hashes, unfinished runs, failures, and input immutability; no absent event is proof of no violation. Any passage observation must disclose provenance: centered obstacles need 1.524 m on both sides to the inner paint edge, and per-obstacle best-side samples cannot establish absence of staggered bottlenecks. Geometric derivation belongs to T-0085; missing adequate geometry evidence stays unknown. Return a scoped SHA and bounded evidence for Sonnet code review and Sol evidence review; official scoring, hardware fidelity and competition compliance remain UNVERIFIED.
- **Stop condition:** Hand back on completion or 35 minutes / budget, or stop partial if required evidence/schema authority is missing, an edit exceeds ownership, a hard invariant would change, two hypotheses fail or auth/quota/model-access fails. No automatic retries, model substitution or sub-agent delegation by this worker.
- **Budget:** Second `claude-opus-5-5`, high effort, `--max-budget-usd 10` for headless launch, 35-minute wall limit. If launched through interactive sub-agent tooling without a budget switch, USD 10 is a tracked task target, not an enforced cap; record actual model/usage. One review per handback per reviewer, at most two revision rounds.

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

Assigned to a SECOND claude-opus-5-5 implementer, to be launched as a sub-agent by the already-running interactive Opus session that owns T-0085.
The user explicitly authorizes this single delegation exception to the protocol's no-recursive-delegation default. The child must not delegate again; at most two implementers, with disjoint files.
Create/use its own worktree `.claude/worktrees/igvc2027-rules-report` and branch `codex/t0087-igvc2027-report-opus` from current committed `claude/sim-realism` HEAD `b517a9924d80750bd19ee1094b95984fe6463b96`; verify identity and preserve any existing path rather than overwriting it.
Do not inherit dirty T-0085 implementation files or full conversation history. Supply this packet and exact referenced inputs; verify actual model claude-opus-5-5, no substitutions.
Packet is final: high effort, `--max-budget-usd 10` where supported, 35 minutes, actual usage recorded, no automatic retries, no live trial/build.
Return ACK and final HANDBACK message blocks for relay into this primary task log, with scoped commit/evidence. Interactive Opus may relay with provenance; ASTRA alone changes headers/board and integrates. `ready` awaits worker ACK.
This dispatch records assignment only; ASTRA launches no worker and commits nothing in this recording-only turn.

### 2026-10-12T19:15:00-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Relay with provenance. The T-0087 worker was launched headless from this interactive session at 18:20 in `.claude/worktrees/igvc2027-rules-report`. It ran `claude -p --model claude-opus-5-5 --effort high --max-budget-usd 10`, acceptEdits, with tools limited to file edits, git and WSL. Actual model per `modelUsage`: claude-opus-5-5 only. is_error=false, 41 turns, 422 s, USD 2.51. Raw JSON: artifacts/agents/T-0087/opus-r1.json; extracted result: opus-r1-result.md. Candidate 559119c, parent b517a99, only the two owned files. Its ACK and HANDBACK follow verbatim. The worker hashed working-tree copies, which match HEAD per its note; committed blobs were not re-hashed from Ubuntu.

### 2026-10-12T18:22-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
Packet understood. Worktree `.claude/worktrees/igvc2027-rules-report`, branch `codex/t0087-igvc2027-report-opus`, HEAD = base `b517a9924d80750bd19ee1094b95984fe6463b96`, clean tree, both owned files absent before start. Actual model `claude-opus-5-5`, interactive sub-agent; USD 10 is a tracked target, not an enforced cap. No questions.

### 2026-10-12T18:30-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
Hypothesis and outcome: Confirmed. A read-only, stdlib-only report (stdout JSON, sorted keys, deterministic) compares a hash-bound declared driving clock (wall/trajectory/declared, minus overtaking-only pauses) with 360 s inclusive. Wall elapsed and trajectory span are listed as non-driving clocks. Sections for timing, completion (no finish crossing inferred from 6/6), II.4 tickets (verbatim values/E-stop/measurement columns; arithmetic not_computed), unresolved 44/88 ft windows, passage disclosure and the audit verdict copied unchanged. Reuses profile/checker constants and run checks.
Changed files / scoped commit (candidate SHA): 559119cad155fb90d65842580342d4a1bb5e1159 — tools/rules_score_2027.py (+446), tools/tests/test_rules_score_2027.py (+262) only.
Baseline and candidate identities: base b517a99; tool sha256 59be1bc6…435e; test f0bc2bee…a9b4; checker 32c8cf29…0ec (unchanged); profile bb0ce544…7390; rules text 7bbd0dad…f9d4; fixture report 630c9d9d…bc51 (ignored artifacts/agents/T-0087/fixture/).
Tests and replay evidence (commands + results): (1) python3 -m unittest discover -s tools/tests -p test_rules_score_2027.py → 13 OK. (2) …-p test_competition_profile.py → 11 OK. (3) bash artifacts/agents/T-0087/fixture/smoke.sh → help exit 0; report exit 1 (synthetic careless-driving ticket); exactly 360.0 s → pass; finish unknown; inputs unchanged.
Live result: destinations, time, backups, clearance, health, audit status: None (no live run).
Shutdown/lease verification: None used.
Claim level reached: tested
Remaining risks and next experiment: No existing lap has an observations receipt, so real laps report timing unknown. The receipt schema (igvc2027-recorded-observations/1) is tool-local and needs ASTRA approval. Ticket events are trusted declarations; none are derived from the audit. Passage measurements are declared only; geometry is T-0085's. UNVERIFIED: official scoring/sign, judge clock alignment, image pages 11/15/16, hardware fidelity, competition compliance. Usage ≈ USD 2.44.
Knowledge concepts affected (IDs, source changes or none): trial-audit-promotion (new offline report consumer); otherwise none.
```

Both handbacks are ready for your review requests: T-0085 at 6eeb552 and T-0087 at 559119c. Sonnet reviews code, Sol reviews evidence. T-0087 proposes a tool-local receipt schema (igvc2027-recorded-observations/1) that needs your decision.

### 2026-10-12T18:45:22-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
**Reviews.** Two read-only reviews of candidate 559119c were run from this session, Sonnet and Sol in parallel, using the dispatch form. They are relayed verbatim below:
- Sonnet: claude-sonnet-5-5 per `modelUsage`, USD 0.55. Relayed from artifacts/agents/T-0087/sonnet-review-r1.json. Its heading time is the model's own.
- Sol: log header `model: gpt-6.1-sol`. Relayed from artifacts/agents/T-0087/sol-review-r1.md.

**Timestamp correction.** My relay NOTE above, headed 19:15, was actually written at about 18:33.

### 2026-10-12T20:00:00-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Task: T-0087   Candidate: 559119cad155fb90d65842580342d4a1bb5e1159   Scope: code
Verdict: approve-with-nits

Candidate identity: worktree `HEAD` is 559119cad155fb90d65842580342d4a1bb5e1159 with parent b517a9924d80750bd19ee1094b95984fe6463b96. `git show --stat` lists only `tools/rules_score_2027.py` (+446) and `tools/tests/test_rules_score_2027.py` (+262), so the SHA matches and the review stands. The checker and profile are untouched.

Findings (ranked, ≤ 5):
1. [minor] tools/rules_score_2027.py:331: The checker's run checks are copied into the output as `profile_checker_run_checks`, but they never reach `checks`, `section_status` or `status`.
   Mechanism: `validate()` emits `run_elapsed`, which passes or fails on raw wall seconds, and `sampled_run_speed`, which fails when a chord speed exceeds the cap. Take a run with wall 400 s, a declared 40 s overtaking pause, and a complete declared clock. The timing section says `pass` at 360.0 s, while the embedded `run_elapsed` says `fail`. A checker-proven speed-cap `fail` also leaves the overall status at `unknown` (exit 2). The two views contradict each other, and a reader could take the embedded `fail` as a driving-time verdict.
   Evidence: read lines 331, 405 and 408-416 of the tool and the checker's run block (check_competition_profile.py:131-159). The existing tests never inspect this key. UNVERIFIED by execution.
2. [minor] tools/rules_score_2027.py:239: The 360 s boundary is compared after float subtraction, and the receipt does not say whether `elapsed_s` is gross or net of pauses.
   Mechanism: `base - sum(end - start)` with fractional values can land a hair off the intended number. The tests only hit 360.0 exactly with no pauses or integer-valued pauses. A receipt with wall 400.3 and a pause of 40.3 s can compute to 360.00000000000006 and report `fail` for an exact-limit run, or the reverse. Also, `declared` gets the overtaking pauses subtracted as well. A receipt author who already excluded the pause from `elapsed_s` would be double-subtracted, which could turn a 380 s driving time into a false `pass` at 350 s. The schema lives only in the code, and nothing says which clock `declared` is on.
   Evidence: read lines 225-245 and the tests (test_below_exact_and_above_360_seconds and test_selected_run_clock_and_overtaking_pauses). Neither exercises fractional pauses. UNVERIFIED by execution.
3. [minor] tools/rules_score_2027.py:442 and the `main()` error path: Exit code 1 means both "report status fail" and "malformed input or I/O error". Argparse usage errors exit 2, the same as `unknown`.
   Mechanism: A caller that scripts on exit codes cannot tell an observed ticket (1) from a bad receipt (1), or a missing `--run` (2) from an `unknown` report (2). The `error` key in stdout separates the first pair only if the caller parses it.
   Evidence: read `main()`. The CLI test asserts 2 for the happy path and 1 for NaN and bad-receipt input. The exit-1 path for an observed ticket is covered only by the unrelated in-process assertion `result['status'] == 'fail'`, and the handback's smoke script is not in the tree, so it is not reproducible from the candidate.
4. [nit] tools/rules_score_2027.py:113 and :237: Some malformed receipts raise differently, or kill the whole report instead of staying `unknown`.
   Mechanism: Sorting pauses with a non-numeric `start_s` (for example `"5"` against `0`) raises `TypeError` before the field validators run. `main()` catches it, but a direct `report()` call surfaces a `TypeError` instead of the `ValueError` the validator's contract implies. A pause past the selected clock aborts the whole report (exit 1, no sections) rather than marking only timing `unknown`. Separately, contrived but finite extreme trajectory values (±1e308 times) can produce `inf` or `nan` in the diagnostics. The `json.dumps(..., allow_nan=False)` call sits outside the `try`, so this would produce a traceback instead of the structured error.
   Evidence: read only. No test covers non-numeric pause fields or extreme values.
5. [nit] tools/rules_score_2027.py:69, 298: Two classifications are loose. `time_limit_e_stop`, which the quote itself calls "no additional penalty", is reported as a `fail` event next to real violations. `too_slow` has `ends_run=False` with `disqualifies=True`, though it is a run-ending disqualification.
   Mechanism: The `fail` status conflates "an event was recorded" with "a rule was violated". Consumers reading `ends_run` alone would under-report the disqualification.
   Evidence: ticket table and the OTHER_END_EVENTS quotes compared with the extracted rules text.

What I checked and found sound:
- **360 s boundary:** The comparison is inclusive. Below, equal and above map to pass/pass/fail, and the tests cover 359.999, 360.0 and 360.001.
- **Clock selection and unknowns:** Wall elapsed and trajectory span are explicitly `is_driving_runtime=False`. Driving runtime requires a hash-bound declared clock, a pause list, overtaking-only pauses and a terminal run. A missing pause list, a non-overtaking pause reason, a non-increasing trajectory, an unfinished run and unbound observations all give `unknown`. A run already over 360 s gives `fail`.
- **Finish crossing:** It is never inferred from six-goal progress, and the report states this.
- **Malformed and nonfinite input:** `number()` and `load()` come from the checker, so bools, strings, NaN and Inf are rejected. Observation shapes, pause overlap and event categories are validated.
- **Hash binding:** Observations and audit are compared with sha256 of the exact run bytes, and mismatched observations are ignored. The audit field name `run_sha256` matches `audit_sensor_run.py:490`.
- **Input immutability:** The report copies with `dict(item, ...)` and `sorted()` and does not mutate inputs. A deepcopy test covers this, and the CLI test compares input bytes before and after.
- **Tickets:** The ten-row table, the E-stop and measurement columns and the "End of Run", "Disqualified" and "0 Feet" values match the extracted v7 text lines 407-416. `arithmetic.status` is `not_computed` with a null adjusted score, and only per-event unsigned magnitudes are listed.
- **Passage:** The threshold is derived from the profile (`minimum_passage_width_ft` × `metres_per_foot`). Centered obstacles need both sides measured to the inner paint edge. A pass requires a declared complete connected-corridor inventory, so per-obstacle samples cannot clear staggered bottlenecks.
- **Reuse:** It imports `DEFAULT_PROFILE`, `aggregate`, `load`, `number` and `validate`. The 360 s limit, the metre conversions and `opening_speed_conflict` come from the profile, with no second profile. The ticket table is not in the profile or checker (grep finds no `ticket`), so the local `TICKETS` and `SOURCES` are new rule data. They are sourced and qualified by `TEXT_BASIS`, which is acceptable under the packet. Nothing in the profile and checker is contradicted.
- **Scope:** Two owned files only, with no runtime, auditor or judge edits.
- **Would the tests fail without the change?** Yes, both files are new, and the assertions check statuses and values rather than restating the implementation.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓   (no autonomy, mission, WORLD geometry, speed or runtime path is touched; claim level `tested` is not conflated with audit-passed, and the official-scoring and compliance unknowns are kept explicit)
Tests run: none (read-only). My attempts to run the unit tests and probes were not permitted in this environment, so the handback's "13 OK / 11 OK" and smoke results are UNVERIFIED by me.
Missing acceptance coverage:
- Fractional-pause boundary at exactly 360 s, and the documented gross-versus-net meaning of `declared.elapsed_s`.
- The `profile_checker_run_checks` section's relation to the timing verdict.
- CLI exit code 1 for an observed ticket, and exit 2 versus argparse errors.
- Non-numeric pause fields, a nonfinite value inside the observations or audit file through the CLI, and non-dict inputs.
- A CLI-level hash-mismatch case with real files.
- The receipt schema (`igvc2027-recorded-observations/1`) needs ASTRA's decision, as the handback says.
- Live or real-run replay, because no existing lap carries a receipt.
- Official scoring, signed ticket arithmetic, the 44 ft/30 s versus 88 ft/60 s window, image pages 11/15/16 and the extraction defects remain UNVERIFIED.

### 2026-10-12T18:41:15-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0087   Candidate: 559119cad155fb90d65842580342d4a1bb5e1159   Scope: evidence
Verdict: request-changes

Findings (ranked, ≤ 5):
1. [major] tools/rules_score_2027.py:366: `minimum_passage=pass` exceeds the geometry evidence represented by the receipt.
   Mechanism: `method=connected_corridor` and `inventory_complete=true` promote passing per-obstacle clearances into an overall passage pass. The schema supplies no connected-passage measurements or explicit bottleneck-verification result. Alternating obstacle openings can individually pass while their connecting passage fails.
   Evidence: Read receipt validation at lines 139–154, aggregation at 365–373, and tools/tests/test_rules_score_2027.py:153, which expects a pass from per-obstacle scalars alone. Keep overall passage unknown until adequate connected-passage evidence is supplied. | UNVERIFIED: Actual corridor geometry; no geometry evaluation performed.

2. [major] tools/rules_score_2027.py:261: Excess total driving duration is treated as proof that finishing within 360 seconds did not occur.
   Mechanism: A bound capture lasting 370 seconds could contain a finish crossing at 359 seconds. The receipt records only a crossing boolean and source, without its timestamp or a guarantee that the selected clock ends at that crossing. Nevertheless, this branch reports “the course was not completed within the run time.” The duration exceedance is supported; that finish conclusion is not.
   Evidence: Read finish receipt validation at 123–127 and timing/completion logic at 242–274. Existing finish tests do not cover a crossing before the deadline followed by later recording. Require crossing-time evidence or leave the finish-time conclusion unknown. | UNVERIFIED: Dynamic reproduction; finding follows the accepted schema and branches.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓ for implemented/tested/live/unverified claim separation; individual rule conclusions require the changes above.

Tests run: none (read-only). Verified clean HEAD, branch, parent b517a9924d80750bd19ee1094b95984fe6463b96, and two-file scope. Recomputed tool, test, checker, profile, rules-text, fixture-input and report hashes match the handback/saved report. Raw worker JSON verifies only claude-opus-5-5, is_error=false, USD 2.505764; the relay corrects the handback’s USD 2.44. The saved smoke report supports declared 360-second timing pass, finish unknown despite 6/6, careless-driving failure, and certification=false. II.4 values/flags match the supplied extraction; signed arithmetic and 44/30 versus 88/60 remain unresolved. The handback explicitly discloses the receipt schema as tool-local and awaiting ASTRA approval.

Missing acceptance coverage: Connected-passage evidence and finish-time chronology above. The reported 13 report tests and 11 profile tests lack saved execution output and were not independently rerun; “tested” remains the worker-reported ceiling. No live, official-scoring, hardware or competition-certification claim is supported. Schema approval remains pending.

### 2026-10-12T18:52:28-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Relay with provenance: T-0087 revision 1, the second Opus worker launched headless from this session.
- Invocation: same worktree, branch and caps as r1, with both r1 reviews supplied.
- Actual model per `modelUsage`: claude-opus-5-5 only. is_error=false, 23 turns, 371 s, USD 1.96.
- Raw output: artifacts/agents/T-0087/opus-r2.json; extracted result: opus-r2-result.md.
- Candidate: 62202ba, parent 559119c.
- Saved check output: `.claude/worktrees/igvc2027-rules-report/artifacts/agents/T-0087/rev1/`.

The worker's HANDBACK follows verbatim.

### 2026-10-12T18:51:41-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

```text
Hypothesis and outcome: Revision 1 addresses both Sol majors and all five Sonnet items.
- Sol 1, fixed: overall minimum_passage passes only when the receipt carries passage.connected_check with tool, tool_sha256, a course_sha256 equal to run.course_sha256, a result and min_clear_width_m measured to the inner paint edge. Per-obstacle samples never produce a pass. I removed the connected_corridor method. Geometry is not evaluated here.
- Sol 2, fixed: added optional finish_crossing.time_s. Finish-within-time is decided from the crossing's own driving time. A total over 360 s with no crossing time is unknown.
- Sonnet 1, fixed: the checker output is renamed profile_checker_run_diagnostics (aggregated_into_status=false, with a note). The checker's speed-cap fail is restated as speed/sampled_speed_cap and now reaches the report status.
- Sonnet 2, fixed: pause subtraction and the 360 s boundary use exact Fraction(repr(x)) arithmetic. declared elapsed_s must carry elapsed_kind='gross'.
- Sonnet 3, documented: exit codes stay consistent with the checker (1 = fail or error, 2 = unknown or usage error). They are stated in the --help epilog and tested.
- Sonnet 4, fixed: pause fields are validated before sorting. A pause past the clock makes timing unknown instead of aborting. json.dumps now runs inside the try.
- Sonnet 5, fixed: time_limit_e_stop moved to the timing section with penalty_stated=no_additional_penalty and traffic_violation=false. Added outcome; too_slow is disqualifies_run_result.
Changed files / scoped commit (candidate SHA): tools/rules_score_2027.py and tools/tests/test_rules_score_2027.py; 62202bae7fec4aaba510b11a21bf1aa9600bea9f
Baseline and candidate identities: base b517a99 → r1 559119c → 62202ba. Tool 7ab78c5a…5bf8, test c5c6209f…1a73, checker 32c8cf29…0ec (unchanged), profile bb0ce544…7390 (unchanged).
Tests and replay evidence (commands + results): all output is in artifacts/agents/T-0087/rev1/.
(1) Report unit tests: 19/19 OK, saved in check1-test_rules_score_2027.txt.
(2) Profile unit tests: 11/11 OK, saved in check2-test_competition_profile.txt.
(3) smoke.sh: --help exits 0; the fixture report exits 1 with inputs unchanged; a usage error exits 2. Saved in check3-smoke.txt and report.json (28170e95…084e).
Live result: none
Shutdown/lease verification: no simulator or lease used
Claim level reached: tested
Remaining risks and next experiment: UNVERIFIED: the receipt schema, including the new connected_check, time_s and elapsed_kind fields, still needs ASTRA approval. Also UNVERIFIED: official scoring and signed arithmetic, the 44 ft/30 s versus 88 ft/60 s window, image pages 11/15/16, real-run replay, and the T-0085 checker's output format.
Knowledge concepts affected (IDs, source changes or none): none
```

### 2026-10-12T18:55:09-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Revision 1 reviews of candidate 62202ba, relayed verbatim below:
- Sonnet: claude-sonnet-5-5 per `modelUsage`, USD 0.61. Relayed from artifacts/agents/T-0087/sonnet-review-r2.json.
- Sol: log header `model: gpt-6.1-sol`. Relayed from artifacts/agents/T-0087/sol-review-r2.md.

Both return request-changes, and they converge on the finish-within-time gate. I am launching revision 2, the last one the protocol allows, with the same worker setup.

### 2026-10-12T19:00:00-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Task: T-0087   Candidate: 62202bae7fec4aaba510b11a21bf1aa9600bea9f   Scope: code
Verdict: request-changes

Candidate identity: worktree `HEAD` is 62202bae7fec4aaba510b11a21bf1aa9600bea9f. `git diff --stat 559119c 62202ba` lists only `tools/rules_score_2027.py` (+285/-) and `tools/tests/test_rules_score_2027.py` (+184/-). The SHA matches, so the review stands. The checker and profile are untouched.

Findings (ranked, ≤ 5):
1. [major] tools/rules_score_2027.py:338-340 (with 330-332, 308): `finished_within_run_time` returns `pass` for a timed crossing without requiring the clock to be declared complete or the run to be terminal.
   Mechanism: The `crossing is not None` branch needs only a computable `driving`. The timing check demands `complete` and `terminal` before it reports `pass`, but this branch does not. Take a declared clock `{elapsed_s: 100, pauses: [], no 'complete'}` on a run with `status: 'running'`, with `finish_crossing {observed: true, time_s: 50}`. Then `driving_runtime_within_limit` is `unknown` ("duration evidence incomplete"), yet `finished_within_run_time` is `pass`. A clock that does not cover start signal to crossing can understate driving time at the crossing, because a late-started clock makes a late crossing look early. Only the `fail` side (over the limit) is safe on a partial clock; `pass` is not. This reintroduces the overclaim class Sol raised in r1 through a new path, and it contradicts the acceptance rule that incomplete duration evidence stays unknown.
   Evidence: Traced lines 285-309 and 328-353 for the inputs above. The tests only exercise `time_s` with `complete: True` (`test_over_limit_duration_needs_crossing_time_to_decide_finish`, and the setUp default). No test covers a crossing time with `complete` absent or false. UNVERIFIED by execution: both Python probes (the scratch-file write and the inline env-var call) were denied in this environment. Suggested fix: require `complete` before reporting a crossing-based `pass` and leave the `fail` side as is. Add one test.
2. [minor] tools/rules_score_2027.py:469-478: The `connected_check` pass is self-declared. The "course hash equality" binds the receipt to `run.course_sha256`, a field the run itself recorded.
   Mechanism: The CLI has no `--course` input, so nothing checks that hash against actual course bytes. `tool_sha256` is only format-validated. The chain is receipt, then `run_sha256`, then `run.course_sha256`, then the declared result. A receipt author can assert `result: pass` with any width ≥ 1.524 and any well-formed tool hash. The report does disclose `geometry_evaluated_by_this_report=false`, which makes this acceptable for a tool-local schema. But the section still reads `pass`, and the packet said missing adequate geometry evidence stays unknown. ASTRA's schema decision should state that this is a trusted declaration, or the report should bind it to a supplied course file.
   Evidence: Read lines 204-212, 460-482 and the test at 255-273. The equality path itself is correct. A missing run hash gives `unknown`, a different hash gives `unknown`, and a bound `fail` with width ≥ the minimum gives `unknown`.
3. [minor] tools/rules_score_2027.py:34-37, 531-557: Exit 1 still conflates a report `fail` with malformed input or an I/O error. Argparse exit 2 still equals `unknown`.
   Mechanism: This is documented and tested, and it matches the checker, which is a defensible disposition of Sonnet r1 item 3. It is a nit for callers that script on exit codes. The `error` key separates the two cases only when stdout is parsed.
   Evidence: Read the epilog, `main()` and the CLI test (exit 1 with `error`, exit 1 without `error`, usage exit 2 with empty stdout).
4. [nit] tools/rules_score_2027.py:394-398 (and 324): A recorded `time_limit_e_stop` is not cross-checked against the timing verdict.
   Mechanism: A bound receipt can show `driving_runtime_within_limit=pass` (complete clock, ≤ 360 s) while `end_of_run_time_limit_e_stop=fail` says the course was not completed in time. Both appear in the timing section with no note of the conflict. Ticket `time_s` values are validated but never compared with the clock. This is an unflagged internal inconsistency, not a wrong verdict.
   Evidence: Read the code. No test combines the two.
5. [nit] tools/rules_score_2027.py:126-133, 147: `elapsed_kind` is a label, not a semantic check.
   Mechanism: `'gross'` is required and then trusted, so a receipt author who pre-subtracts pauses and still writes `'gross'` is double-subtracted. The `exact(repr(x))` arithmetic itself is sound. Sonnet r1 item 2 is satisfied: 400.3 − 40.3 is exactly 360, and the boundary is tested at 40.4 and 40.3999. Extreme finite trajectory values can still yield non-finite diagnostics, but this now ends in a structured exit-1 error because `json.dumps` sits inside the `try`.
   Evidence: Read lines 126-133 and 147, and the fractional-pause test.

Disposition of r1 items:
- **Sol 1 (passage):** Mostly fixed. Per-obstacle samples never pass. Overall pass needs `connected_check` with a course hash equal to `run.course_sha256`, `inner_paint_edge` and width ≥ the minimum. See finding 2.
- **Sol 2 (finish time):** Partly fixed. `time_s` decides the finish and a total over 360 s is `unknown` without it. Finding 1 is a regression on the `pass` side.
- **Sonnet 1 (checker run checks):** Fixed. The diagnostics are not aggregated, and the speed-cap `fail` now reaches the section and overall status.
- **Sonnet 2 (float boundary and gross/net):** Fixed. Fractional pauses are tested.
- **Sonnet 3 (exit codes):** Documented only. See finding 3.
- **Sonnet 4 (validation):** Fixed. Pause fields are validated before sorting, a pause past the clock gives `unknown`, and `json.dumps` is inside the `try`.
- **Sonnet 5 (classification):** Fixed. `time_limit_e_stop` is timing evidence with no traffic violation, and `outcome` is added.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓   (read-only offline tool; no autonomy, WORLD geometry, mission, speed or runtime path touched; claim `tested` kept below audit-passed; certification stays false. Finding 1 is a result-strength defect rather than an invariant breach.)
Tests run: none (read-only). I read `check1-test_rules_score_2027.txt` (19 OK) and `check3-smoke.txt` (help 0, report 1, usage 2, inputs unchanged), whose hashes match the handback. I could not re-run them or probe from this environment, so those results stay worker-reported and UNVERIFIED by me.
Missing acceptance coverage:
- A timed finish crossing with `complete` absent or false, and with a non-terminal run (finding 1).
- A `time_limit_e_stop` event combined with a timing `pass` (finding 4).
- A connected-check receipt bound to real course bytes (finding 2).
- Real-run replay, since no lap carries a receipt.
- ASTRA approval of the tool-local schema, including the new `connected_check`, `time_s` and `elapsed_kind` fields.
- Official scoring, signed ticket arithmetic, the 44 ft/30 s versus 88 ft/60 s window, and image pages 11/15/16.

### 2026-10-12T18:54:00-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0087   Candidate: 62202bae7fec4aaba510b11a21bf1aa9600bea9f   Scope: evidence
Verdict: request-changes

Findings (ranked, ≤ 5):

1. [major] tools/rules_score_2027.py:344: A timestamp-free finish-within-time pass remains, contrary to the requested crossing-time-only gate.
   Mechanism: With a complete declared 300-second clock and `finish_crossing={observed:true, source:"synthetic judge note"}`, but no `time_s`, this branch returns `finished_within_run_time=pass`. The new schema defines completeness as whole-attempt coverage, so this is a defensible upper-bound inference; nevertheless, it does not use crossing-time evidence as requested. Require comparable crossing time for this verdict or explicitly approve the alternative contract.
   Evidence: Read lines 327–348 and tools/tests/test_rules_score_2027.py:134–135, which deliberately expects this timestamp-free pass. The original over-limit defect is fixed: a 370-second total without crossing time stays unknown; crossings at 359 and 360.5 seconds receive pass and fail respectively. | UNVERIFIED: Independent execution; review used source and saved outputs.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓. Offline two-file scope preserves runtime, interfaces, geometry consumers and auditor thresholds. Passage r1 major is resolved at the declared-evidence boundary: per-obstacle passing samples remain unknown overall; success requires an explicit connected-check result, tool digest, matching course digest, inner-paint-edge measurement and sufficient minimum width. Actual checker execution and geometry remain UNVERIFIED.

Tests run: none (read-only). Verified clean HEAD at the pinned candidate, parent 559119cad155fb90d65842580342d4a1bb5e1159, branch and two-file scope. Recomputed tool, test, checker, profile, fixture-input and report hashes match the handback and saved smoke output. Report hash: 28170e955298c5508f0feb880289cf53edc6e186961205a7642aca8a166d084e. Saved logs support worker-executed `python3 -m unittest discover -s tools/tests -p test_rules_score_2027.py` (19 OK), corresponding profile tests (11 OK), and `bash artifacts/agents/T-0087/rev1/smoke.sh` (exit 0; help 0, report 1, usage 2, inputs unchanged). “Tested” is supported for bounded synthetic behavior. Raw worker JSON records only claude-opus-5-5, is_error=false, USD 1.957421.

Missing acceptance coverage: Crossing-time-only verdict requirement above. The receipt schema, including connected_check, time_s and elapsed_kind, is explicitly disclosed as pending ASTRA approval in source and handback. No real connected-check output, real-run replay or live evidence is supplied. Official signed scoring, conflicting speed windows, missing rule images, hardware fidelity and competition compliance remain UNVERIFIED; certification=false is preserved.

### 2026-10-12T18:58:33-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Relay with provenance: T-0087 revision 2, the final round.
- Actual model per `modelUsage`: claude-opus-5-5 only. is_error=false, 180 s, USD 1.39.
- Raw output: artifacts/agents/T-0087/opus-r3.json; candidate 1f701b8, parent 62202ba.

The worker's HANDBACK follows verbatim.

### 2026-10-12T18:57:55-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Task: T-0087 · Candidate: 1f701b87b9821c4259866d09f8b17ad1c814626e (parent 62202ba) · Branch: codex/t0087-igvc2027-report-opus · Files: `tools/rules_score_2027.py` (+46/−23), `tools/tests/test_rules_score_2027.py` (+72/−1) only.

How each item was handled:
- **Major (Sonnet 1 / Sol 1), fixed:**
  - `finished_within_run_time` = `pass` only when `finish_crossing.time_s`, placed on a complete, terminal, hash-bound driving clock, is ≤ 360 s.
  - `fail` only when that crossing is > 360 s, or when an observed absence of a crossing sits on that same clock.
  - Every other path is `unknown`: no `time_s`, `complete` absent or false, a non-terminal run, an unbound receipt, an incomparable clock, or a crossing past the end of the clock.
  - Fail on an incomplete clock was also removed, because the clock's zero is not known to be the start signal and could be offset either way.
  - Tests cover both counterexamples, the 360 / 360.001 s boundary, and each path.
- **Sonnet 2, documented:** `connected_check` stays a trusted declaration. The output carries `connected_check_trust='declared_unverified'` and a `course_binding` note saying only the run's own `course_sha256` field is compared. Tested.
- **Sonnet 3, kept:** exit codes still match the checker. The epilog now tells scripted callers to parse stdout.
- **Sonnet 4, fixed:** a recorded `time_limit_e_stop` downgrades a contradicting timing `pass` to `unknown` (driving time < 360 s, or a timed finish ≤ 360 s). Driving time of exactly 360 s stays consistent with the E-stop. Tested.
- **Sonnet 5, documented:** the driving clock entry reports `elapsed_kind` with `elapsed_kind_verified=false`, and the detail text warns about double-subtraction. Tested.

Checks, run via WSL using `bash artifacts/agents/T-0087/rev2/run_checks.sh` (outputs in `artifacts/agents/T-0087/rev2/`):
1. `check1-test_rules_score_2027.txt`: 21 tests OK, exit 0.
2. `check2-test_competition_profile.txt`: 11 tests OK, exit 0.
3. `check3-smoke.txt` (from `smoke.sh`): help exit 0, report exit 1, usage exit 2, inputs unchanged. On the complete clock the finish passes at a crossing driving time of 354.7 s.

SHA-256:
| File | Hash |
| --- | --- |
| `rules_score_2027.py` | fd10ee52…e1a |
| `test_rules_score_2027.py` | 7b5f00ad…2c2 |
| `check_competition_profile.py` (unchanged) | 32c8cf29…ec |
| `igvc-2027-autonav.json` profile (unchanged) | bb0ce544…390 |
| `run.json` | 0013789e…3ff |
| `observations.json` | b983ae11…acf |
| `report.json` | 13295663…5f2 |

UNVERIFIED:
- ASTRA approval of the receipt schema.
- Real `connected_check` output and course-byte binding.
- Replay of a real run.
- Official signed scoring.
- The 44 ft/30 s versus 88 ft/60 s speed-window conflict.
- Image pages 11/15/16 of the rules.
- Hardware and competition compliance.

`certification` stays false. Claim ceiling: tested.

Knowledge concepts affected: none.

### 2026-10-12T19:01:58-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Final-round reviews of candidate 1f701b8, relayed verbatim below:
- Sonnet: claude-sonnet-5-5 per `modelUsage`, USD 0.51. Relayed from artifacts/agents/T-0087/sonnet-review-r3.json.
- Sol: log header `model: gpt-6.1-sol`. Relayed from artifacts/agents/T-0087/sol-review-r3.md.

Both return **approve-with-nits** with no blocking finding.

**Requesting your DECISION on candidate 1f701b8** (branch codex/t0087-igvc2027-report-opus). This was the last revision round, so the remaining nits stand as limitations unless you rule otherwise. Open schema items for you:
- igvc2027-recorded-observations/1;
- connected_check, a declared and unverified pass;
- finish_crossing.time_s;
- elapsed_kind.

**Worker usage across 3 rounds:** USD 2.51 + 1.96 + 1.39. **Reviews:** USD 0.55 + 0.61 + 0.51 (Sonnet), plus three Sol passes.

### 2026-10-12T19:10:00-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Task: T-0087   Candidate: 1f701b87b9821c4259866d09f8b17ad1c814626e   Scope: code
Verdict: approve-with-nits

Candidate identity: worktree HEAD is 1f701b87b9821c4259866d09f8b17ad1c814626e, the tree is clean, and `git diff 62202ba 1f701b8 --stat` lists only `tools/rules_score_2027.py` (+46/-23) and `tools/tests/test_rules_score_2027.py` (+72/-1). The SHA matches the pin, so the review stands. `git show 1f701b8:tools/rules_score_2027.py | sha256sum` gives fd10ee52…e1a, the same hash as in `rev2/check3-smoke.txt` and the handback. The checker and profile are untouched.

Blocking findings: none. The convergent major (finish-within-time) is resolved. Non-blocking findings follow.

Findings (ranked, ≤ 5):
1. [minor] tools/rules_score_2027.py:314, 350-353: The `finished_within_run_time` fail for an observed absence of a crossing does not require a computable driving clock.
   Mechanism: `complete` is `clock.complete is True and terminal`, set before and independently of `driving`/`problem`. Take a terminal run, a bound receipt, `complete: true`, and `finish_crossing {observed: false}`. If the pause list is absent, a pause reason is not 'overtaking', or a pause extends past the clock, then `driving` is None and timing is `unknown`. The finish check still returns `fail` ("over a complete whole-attempt clock"). This is a fail on an unvalidated clock. The handback says the fail comes from an observed absence "on that same clock", which is not strictly true here. It cannot produce a pass, so the pass-only-from-explicit-time gate is intact. It follows the receipt's own assertion that nothing crossed.
   Evidence: traced lines 289-314 and 348-353. The new test `test_finish_fail_only_from_late_crossing_or_terminal_complete_absence` uses a valid clock only. UNVERIFIED by execution: a probe script was blocked because Write is disabled here. Suggested fix: add `driving is not None and` to the absence-fail condition, plus one test.
2. [minor] tools/rules_score_2027.py:327-329 vs 360-362: The fail-on-an-incomplete-clock rationale is applied to the finish check but not to the driving-runtime check.
   Mechanism: The finish check now says an incomplete clock's zero "may be offset either way" and refuses to fail on it. `driving_runtime_within_limit` still reports `fail` whenever `driving > 360`, whether or not the clock is complete. A recorder wall clock that includes 30 s of pre-start time reads 380 s against 350 s of true driving, and reports `fail` without `complete`. The reason text calls it "a duration finding only", and an earlier round accepted this branch (the test name says "unless_already_over"). It is an inconsistency, not a pass overclaim.
   Evidence: read lines 325-334 and 360-362 and the test name. The `fail` branch is deliberate, not accidental.
3. [nit] tools/rules_score_2027.py:335, 365: The E-stop cross-check is partial.
   Mechanism: Only a timing `pass` (driving < 360) and a finish `pass` (crossing ≤ 360) are downgraded when `time_limit_e_stop` is recorded. The E-stop's `time_s` is validated but never compared with the clock. A receipt with an E-stop at 100 s on a 360 s complete clock is flagged only by the coarse `driving < limit` test. Exactly 360 s stays consistent, which is intended and tested.
   Evidence: read the code and the test additions. It is internally consistent for the tested cases.
4. [nit] tools/rules_score_2027.py:449-474 (connected_check pass): The pass is still self-declared. This round only adds disclosure: `connected_check_trust='declared_unverified'`, the `course_binding` note and the detail text. The section status stays `pass`. The disposition is honest and tested (`overall['observed']['connected_check_trust']` and the `no course file` string). Whether a declared pass should read `pass` or `unknown` is an ASTRA schema decision, which the handback already flags. Carried forward from r2 item 2, not blocking.
5. [nit] Exit codes (1 = fail or error, 2 = unknown or usage) and `elapsed_kind` (label only, `elapsed_kind_verified=false`) are documented and tested. They are acceptable dispositions of Sonnet r1 items 3 and 5 and r2 items 3 and 5. A caller that scripts on exit codes alone is still warned in the epilog.

Disposition of the convergent major and the other items:
- **Finish-within-time (Sonnet r2 1 / Sol r2 1): resolved.** In `finished_within_run_time`, `pass` is reachable only through the final `else`. Every earlier branch must have failed to match, so `pass` needs all of:
  - a bound receipt (unbound gives `obs = {}`, so `finish` is None and the result is unknown);
  - `observed=true` with an explicit `time_s`;
  - a computable `driving` (a valid clock and pauses);
  - `time_s ≤ base`, so `crossing` is not None;
  - `complete`, meaning `complete: true` and a terminal run status;
  - `crossing ≤ 360` (exact Fraction arithmetic, so 360 passes and 360.001 fails);
  - no recorded `time_limit_e_stop`.
  The two earlier counterexamples are closed. A complete 300 s clock with no `time_s` now gives `unknown`. A timed crossing with `complete` absent or false, or on a non-terminal run, now gives `unknown`.
  `fail` on a timed crossing now requires `complete`. A timed crossing past the clock end gives `unknown`. A 370 s total with a crossing at 359 s passes only on a complete terminal clock, which is the correct answer.
- **Sol r2 1 (timestamp-free pass): fixed.** The test now expects `unknown`.
- **Sonnet r2 1 (partial-clock pass): fixed.** `complete` is now required before any crossing-based result, including fail.
- **Sonnet r2 2 (connected_check trust): documented only.** See finding 4.
- **Sonnet r2 3 (exit codes): documented only.** See finding 5.
- **Sonnet r2 4 (E-stop vs timing): fixed for the pass paths.** See finding 3.
- **Sonnet r2 5 (elapsed_kind): documented, with `elapsed_kind_verified=false` in the output.**

Regressions: none found. Scope is the two owned files, with no runtime, auditor or judge edits. Output keys are only added (`complete_terminal_clock`, `time_limit_e_stops_recorded`, `elapsed_kind`, `elapsed_kind_verified`, `connected_check_trust`, `course_binding`). The tests assert statuses and values (the boundary, each of the five complete/terminal combinations, the E-stop interplay, unbound receipts) rather than restating the implementation. They would fail against 62202ba, since the timestamp-free pass and the partial-clock pass were both present there.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓   (read-only offline tool; no autonomy, WORLD geometry, mission, speed or runtime path touched; claim `tested` kept below audit-passed; `certification=false`; the rule and schema unknowns stay explicit)

Tests run: none (read-only). I did not re-run the tests; my probe script was blocked. I read the worker's saved outputs under `artifacts/agents/T-0087/rev2/`: `check1-test_rules_score_2027.txt` (21 tests OK, exit 0) and `check3-smoke.txt` (help 0, report 1, usage 2, inputs unchanged). `check2-test_competition_profile.txt` (11 OK per the handback) is listed in the directory but I did not read it. These results are worker-reported and UNVERIFIED by me. I did verify the committed tool blob hash against the smoke output. The smoke report's finish pass at a crossing driving time of 354.7 s is consistent with the code path.

Missing acceptance coverage:
- Absence-of-crossing combined with an incomputable clock (finding 1).
- A late-start or pre-start wall clock without `complete` yielding a duration `fail` (finding 2).
- An E-stop whose `time_s` conflicts with the clock (finding 3).
- A connected-check receipt bound to real course bytes, and a real tool hash. ASTRA's approval of the tool-local `igvc2027-recorded-observations/1` schema is still pending, including `connected_check`, `time_s` and `elapsed_kind`.
- Replay of a real run (no lap carries a receipt) and any live evidence. Official signed scoring, the 44 ft/30 s vs 88 ft/60 s window, image pages 11/15/16, hardware fidelity and competition compliance remain UNVERIFIED.


### 2026-10-12T19:00:46-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0087   Candidate: 1f701b87b9821c4259866d09f8b17ad1c814626e   Scope: evidence
Verdict: approve-with-nits

Candidate identity: Clean worktree HEAD matches the pinned SHA, parent 62202bae7fec4aaba510b11a21bf1aa9600bea9f, branch codex/t0087-igvc2027-report-opus. The reviewed diff changes only the two owned files. The stale task-header candidate does not void this explicitly pinned review.

Findings (ranked, ≤ 5):
1. [minor] tools/rules_score_2027.py:350: The HANDBACK overstates the claim that every incomparable-clock path returns unknown.
   Mechanism: `complete` at line 314 checks the receipt flag and terminal status, independently of clock comparability. A bound terminal run with `complete=true`, an overtaking pause extending beyond the selected interval, and `finish_crossing.observed=false` produces driving timing unknown but finished-within-time fail, with `complete_terminal_clock=true`. The absence branch does not require a usable driving clock. This is non-blocking for the requested crossing-pass gate: it creates no unsupported pass, and the explicit absence observation independently supports non-completion. Narrow the handback claim or align this branch with its stated contract.
   Evidence: Read lines 298–314 and 350–373. Tests cover incomparable clocks with observed crossings, but omit this absence combination. | UNVERIFIED: Dynamic reproduction.

Blocking findings: none. The convergent major is resolved. Lines 345–369 allow a finish-within-time pass only from an explicit comparable crossing timestamp on a complete, terminal, hash-bound clock. Timestamp-free, incomplete, running, unbound and out-of-interval observed crossings remain unknown. Saved tests cover both prior counterexamples and the 360/360.001-second boundary.

Minor dispositions:
- Connected-check trust: documented explicitly as `declared_unverified`, including course-field-only binding and unchecked tool/course bytes; actual geometry remains UNVERIFIED.
- Exit codes: intentionally retained, documented and covered; scripted callers are told to parse stdout.
- Time-limit E-stop conflicts: contradicting duration/finish passes become unknown; exactly 360 seconds remains consistent with duration-limit evidence.
- Gross/net semantics: declared gross is required; verification limits and double-subtraction risk are disclosed.
- Earlier checker aggregation, fractional arithmetic, validation and event-classification fixes remain intact. No additional regression found in the reviewed diff and saved report.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓. Runtime, interfaces, mounts, geometry consumers and independent auditors are untouched. Claim ceiling remains tested; certification=false.

Tests run: none (read-only). Independently recomputed all seven source/checker/profile/fixture/report hashes; they match the saved smoke output and handback. Report SHA-256: 13295663bb356c02c287010f094bd6d68ceb7a25f594608ce00bf091a07775f2. Saved logs support worker-executed report tests (21 OK), profile tests (11 OK), and smoke checks (help 0, report 1, usage 2, inputs unchanged). The fixture records a 354.7-second crossing driving time and preserves the careless-driving failure. Execution was not independently rerun. Raw worker provenance records claude-opus-5-5 only, is_error=false, USD 1.3883804.

Missing acceptance coverage: Absence plus incomparable clock above; ASTRA schema approval; real connected-check output/course-byte binding and real-run replay. Official signed scoring, conflicting speed windows, missing rule images, hardware fidelity and competition compliance remain UNVERIFIED. No live evidence is claimed or required for this offline slice.

### 2026-10-12T19:38:24-07:00 · user → gpt-6-astra · DECISION
The user said "accept" in the interactive claude-opus-5-5 session, after a summary that both reviewers returned approve-with-nits on this task's final candidate (1f701b8). claude-opus-5-5 relays this verbatim. Headers, board and integration remain ASTRA's actions under the protocol.

### 2026-10-12T19:41:10-07:00 · gpt-6-astra → all · DECISION

Accept `1f701b87b9821c4259866d09f8b17ad1c814626e` over `b517a9924d80750bd19ee1094b95984fe6463b96`, honoring the user's relayed acceptance and both final approve-with-nits reviews. Accepted commits, in order: `559119c`, `62202ba`, `1f701b8`; only the two new report/test files are included. No inherited realism changes are accepted.
Claim is `tested`: saved worker evidence supports 21 report tests, 11 profile tests and the bounded CLI smoke with unchanged inputs. Independent behavioral execution this turn is UNVERIFIED. Final Sonnet JSON and Sol log header independently confirm the exact requested reviewer models; no further review/revision is requested for this unchanged candidate.
Approve **`igvc2027-recorded-observations/1` as a tool-local, offline declared-evidence receipt**, bound to exact run bytes. It is not a runtime/shared ROS interface, official judging schema or certification. The source comment saying approval is pending is superseded by this decision; update that comment only in a later scoped source change, not by moving this reviewed candidate.
Approve **`passage.connected_check` as a declared result**: its tool/hash, course-hash equality to the run field, inner-paint-edge measurement, result and minimum width describe the supplied assertion. A section `pass` means that assertion satisfies the report's declared-evidence checks, never that this tool executed the geometry checker or verified tool/course bytes. Preserve `connected_check_trust=declared_unverified` and course-binding disclosure. Per-obstacle samples alone cannot pass overall passage; T-0088 must bind actual checker/course bytes before using a receipt as integration evidence.
Approve **`finish_crossing.time_s`** as seconds on the selected gross clock from its declared zero/start signal; subtract only qualifying overtaking pauses up to crossing. A timed pass requires an explicit comparable crossing within the clock interval, a hash-bound receipt, a complete whole-attempt clock, a terminal run and no contradictory time-limit E-stop. Six-goal completion, a short recording or total capture duration alone cannot establish a finish-time pass.
Approve **`elapsed_kind='gross'`** for declared `elapsed_s`: receipts must provide gross start-to-end duration, with pauses subtracted once by the report. This label is trusted, not verified; keep `elapsed_kind_verified=false` and the double-subtraction warning. Other clock selections remain declared interpretations requiring provenance/completeness, not inherently official driving clocks.
Narrow the final handback's "every incomparable-clock path is unknown" claim: explicit observed absence on a bound, terminal, declared-complete attempt can still produce finish `fail` when pause/clock computation is unusable. Accept this non-blocking result as reported non-completion, not validated finish-time arithmetic; timing itself remains unknown. No unsupported pass is introduced.
Accept incomplete-clock duration `fail` only as a declared-duration exceedance diagnostic, not proof of official driving time or late finish; accept partial E-stop timestamp cross-checking as a disclosed limitation. These cases require an explicit caveat if encountered in T-0088 receipts; do not use them as competition verdicts. No third revision is authorized.
Retain documented exit-code ambiguity: consumers must parse stdout/error/checks, not exit status alone. Remaining nits are accepted at this offline scope; real connected-check output, course-byte binding, real-run replay and E-stop chronology remain pending. Official signed arithmetic, conflicting opening-speed windows, missing rule images, hardware fidelity and compliance remain UNVERIFIED; `certification=false` and independent audit verdicts remain unchanged.
