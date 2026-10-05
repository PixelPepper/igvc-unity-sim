---
id: T-0002
title: Add an append-only benchmark ledger for every live run
status: integrated
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0002-benchmark-ledger-opus
base: 3b7fa5aac8c679552c21e7bab56f5f2a92d6a873
candidate: f667d570386edaeec91e24d5ef8cfc09099baaef
claim: tested
lease: none
updated: 2026-10-05
---

# T-0002: Add an append-only benchmark ledger for every live run

## Packet

Finalized for the existing interactive Opus implementer on October 5. Sonnet
reviews code and Sol independently reviews evidence. No other implementation
worker is assigned in this slice.

- **Objective:** `tools/benchmark_ledger.py` reads a saved run directory (`run.json`,
  audit JSON, `profile.yaml`, `provenance.json`) and appends one row to
  `docs/evidence/benchmark_runs.csv`. Columns: run_id, utc, git_sha, profile_sha,
  player_sha, seed, controller, requested_speed_mps, elapsed_s, destinations,
  backups, min_clearance_m, return_distance_m, health_failed_samples,
  audit_passed, source (sandbox | iteration | batch), notes.
- **Why:** [competition context](../COMPETITION_CONTEXT.md#what-to-copy-in-order) item 2.
  Without one ledger, cross-agent comparisons are anecdotes.
- **Owned paths:** `tools/benchmark_ledger.py`, `tools/tests/test_benchmark_ledger.py`,
  `docs/evidence/benchmark_runs.csv` (new).
- **Must not:** recompute or override audit results. Copy them verbatim. A missing field
  stays empty and is never guessed. Do not filter out failed runs.
- **Evidence:** Read primary-checkout artifacts (they are ignored and absent in
  the worktree): `artifacts/iterations/2026-10-01/admissible-endpoints/` has
  run.json, audit.json, live.json, config.json, profile.yaml; the sandbox run
  `artifacts/sandbox/runs/20261002T035715-45c98a0f/` has run.json,
  handoff-audit.json, provenance.json, profile.yaml. Preserve both formats.
- **Truthfulness:** Accept explicit run IDs and audit paths if discovery is
  ambiguous; never substitute current HEAD for missing run provenance. Record
  source artifacts/hashes and metric semantics in notes or added columns. An
  existing row with conflicting evidence must fail clearly, not silently win.
  Missing/invalid audit verdict is unknown, never a pass; malformed input must
  not damage the existing ledger. Do not imply different course/profile hashes
  represent controlled comparable runs.
- **Acceptance:** backfill rows for the accepted 2026-10-01 run and lap
  20261002T035715, and they must match the handoff's numbers (363.37 s / 376.124 s, 6/6,
  audit pass / fail). Re-ingesting the same run must not duplicate a row (idempotent on run_id).
- **Behavior checks:** Cover both real source layouts, pass/fail/unknown audit,
  absent provenance, repeat ingestion, conflicting duplicates, and preservation
  of the ledger after invalid input. Keep dependencies to Python standard library
  if practical. CLI help/docstring must explain backfill, append and limitations.
- **Worktree:** `C:/Users/brand/.codex/worktrees/igvc-t0002-opus/IGVC SIM`.
  Edit and commit only the three owned paths there. Append interactive messages
  and Handback only in this canonical primary task file; never commit task docs
  in the worker worktree.
- **Live trial:** none.
- **Budget:** Existing interactive claude-opus-5-5, 35 minutes and three focused
  offline check invocations before handback; no recursive agents. Reserve $10
  implementation allowance, $5 Sonnet and $5 Sol for this October 5 cycle under
  the user's renewed request. Interactive usage UNMETERED; these reservations
  are workflow allowances, not actual charges or a hard billing cap. No extra
  paid tasks or live trials in this slice. Stop at handback, limit, or ownership
  conflict; do not broaden scope to policy, perception or auditor changes.

## Handback

Revision 2 by claude-opus-5-5. Candidate f667d57 on top of r1 ac49e9e (not amended). r2 changes:
1. An exclusive `<ledger>.lock` file (O_EXCL) covers read, validate and append. It waits up to --lock-timeout,
   then fails, and is never broken. Six concurrent processes appended with no lost rows.
2. The same run_sha256 under another run_id is rejected. run_id is validated (dot paths are resolved first;
   `..` and empty IDs are rejected). Existing rows are validated for field count, run_id, run_sha256 and uniqueness.
3. --ledger and --lock-timeout are accepted after the subcommand. Non-object JSON, non-UTF-8 profiles and corrupt
   ledgers give clear errors. Existing bytes and line ending (CRLF or LF) are preserved byte-for-byte on append.
   New column profile_binding: matched | unverified_profile_missing | no_recorded_hash.
4. Column semantics are now in the module docstring. Correction: the r1 Handback wrongly claimed they were
   already there. Seed comes only from a structured run.json `seed`, with a realistic fixture. backfill is
   all-or-nothing.
Schema change: the owned CSV was regenerated with the new column; both rows keep identical values.
r2 evidence: `wsl -d Ubuntu-24.04 -- python3 -m unittest discover -s tools/tests -p test_benchmark_ledger.py`
→ Ran 10 tests, OK. The first r2 run failed 2 tests because fixtures reused identical run bytes, which the new
rule correctly rejected; the fixtures were fixed. A ResourceWarning comes from unclosed stderr pipes in the
concurrency test (harmless, unfixed). Real backfill exit 0: both rows audit_binding and profile_binding matched.
Three focused invocations used. Claim: tested.

Revision 1 (superseded identities below). Candidate ac49e9e.

```text
Hypothesis and outcome: Implemented an offline, append-only ledger that backfills both preserved runs.
  Rows match the handoff: 363.3706 s / 376.1241 s, 6/6 both, audit true / false, backups 1 / 1,
  return 0.39517 / 0.39871 m, health fails 0 / 4. Audit values are copied, never recomputed.
Changed files / candidate: ac49e9e on codex/t0002-benchmark-ledger-opus (base 3b7fa5a):
  tools/benchmark_ledger.py, tools/tests/test_benchmark_ledger.py, docs/evidence/benchmark_runs.csv
Provenance rules: values come only from each run's artifacts (iteration: live.json; sandbox:
  provenance.json). The audit binds only if its run_sha256 equals the run.json bytes; a mismatch is an
  error. An audit without run_sha256 is recorded as audit_binding=unbound with verdict unknown and no
  audit values. Profile bytes must equal the recorded hash. A non-boolean verdict is unknown. The sandbox
  run records no git commit or player hash, so those stay empty (never HEAD). Added columns:
  certification_status, geometric_full_loop, course/mission/run/audit sha256, audit_file, audit_binding.
  The two rows have different course and profile hashes, so they are not a controlled comparison.
Tests and evidence:
  wsl -d Ubuntu-24.04 -- python3 -m unittest discover -s tools/tests -p test_benchmark_ledger.py
    → Ran 8 tests, OK (both layouts, pass/fail/unknown/unbound, foreign-audit bytes, profile mismatch,
      idempotent re-ingest, conflicting duplicate, malformed input, foreign header; ledger bytes preserved)
  backfill <primary>/artifacts/iterations/2026-10-01/admissible-endpoints <primary>/artifacts/sandbox/runs/20261002T035715-45c98a0f
    → exit 0, two rows appended. One earlier invocation used a mistyped path and failed safely (no ledger created).
  Three focused invocations used.
Live result: none. Lease: none. Claim level reached: tested.
Remaining risks / questions:
  Q1 seed is empty for the iteration run. It is recorded only as the course label `course=seed-2027` in
     sim_status, not as a seed field. Should that label populate seed? Course hash remains the identity.
  - elapsed_s is the mission elapsed_wall_s; min_clearance_m is the audit's conservative swept lower bound;
    backups is the count of recorded recoveries. The semantics are in the module docstring.
  - Git warned that it may convert this CSV to CRLF on Windows checkout. The csv reader tolerates that, but a
    rewrite emits LF. Consider a .gitattributes rule (not an owned path).
  - Batch layout is unsupported.
```

## Log

### 2026-10-04T22:30-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Drafted from the report's `benchmark_runs.csv` recommendation. Check field names
against the actual `run.json`/audit schema before dispatch.

### 2026-10-05T00:12:43-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
T-0002 is ready. User explicitly resumed IGVC work with Opus 5.5, Sonnet 5.5 and GPT-6.1 Sol. Read this finalized Packet, README and project invariants, then ACK exact model identity and implement only the three owned paths in C:/Users/brand/.codex/worktrees/igvc-t0002-opus/IGVC SIM, branch codex/t0002-benchmark-ledger-opus, base 3b7fa5aac8c679552c21e7bab56f5f2a92d6a873. Primary artifact paths are in Packet. Existing interactive session only; 35-minute bound, three focused checks, no agents/live trial/Unity build. Build a truthful offline append-only benchmark ledger and backfill both preserved runs; no current-HEAD provenance guesses, unknown audit != pass, conflicting duplicate != silent success. Commit owned source/test/CSV paths only, update Handback and append immutable candidate SHA. Sonnet and Sol review afterward. Ask through this log if input semantics are ambiguous. Usage remains UNMETERED and full allowance reserved; no headless implementer is launched.

### 2026-10-05T00:12:50-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received. Identity: claude-opus-5-5 (Claude Opus 5.5), interactive Claude Desktop session.
Worktree igvc-t0002-opus, branch codex/t0002-benchmark-ledger-opus, base 3b7fa5a. Three owned paths only,
up to 3 focused checks, 35 min from now. No agents, live trials or builds. Questions, if any, will follow after I inspect the schema.

### 2026-10-05T00:13:46-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
Input check: both real audits carry run_sha256 and source_run, plus sensor_health_evidence.interval_totals (accepted fail=0; sandbox fail=4). Please bind audit data to the supplied run bytes when the audit provides run_sha256; do not attach an unrelated passing audit to a failed run. A mismatch should fail clearly without modifying the ledger. This is part of provenance correctness, not a new auditor/recomputation scope. Coordinator is preparing reviewer context independently.

### 2026-10-05T00:15:24-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate ac49e9e (three owned paths; base 3b7fa5a). The Handback section is filled. Eight tests pass. Real
backfill: two rows matching the handoff numbers (accepted run audit true, sandbox lap audit false with 4 health
fails). Audit is bound to the run bytes per your NOTE; an unbound audit gives verdict unknown. Three checks used.
Claim tested; usage UNMETERED. One open question (Q1, seed label) is in the Handback. Ready for Sonnet and Sol.

### 2026-10-05T00:15:54-07:00 · gpt-6-astra → claude-opus-5-5 · ANSWER
Q1: Keep iteration seed empty for r1. A descriptive course label is not a structured seed field; source course hash remains the identity. Reviewers will assess the omission and semantics. Handback received at candidate ac49e9e917bf31138d76b02bb73946c7bce214ca; please remain idle while Sonnet and Sol review. No new implementation or live trial assigned.

### 2026-10-05 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Task: T-0002   Candidate: ac49e9e917bf31138d76b02bb73946c7bce214ca   Scope: code
Verdict: request-changes

Findings (ranked, ≤ 5):
1. [major] tools/benchmark_ledger.py:171-195: Concurrent appends silently lose rows.
   Mechanism: `add()` does an unlocked read-modify-write. Two processes that read the same ledger each write `existing + own`, and the later `os.replace` drops the other's row. Both report "appended". An append-only evidence ledger can then lose a run with no error.
   Evidence: code read. UNVERIFIED by execution. No lock and no concurrency test.
2. [major] tools/benchmark_ledger.py:104,109,135,172: Idempotency is keyed only on run_id, and run_id is not validated.
   Mechanism: The same run bytes ingested via `--run-id other`, or from a moved or renamed directory (default id is `parent/name`), add a duplicate row with the same run_sha256. `.` yields run_id `/` or empty, and an empty `--run-id` is accepted.
   Evidence: code read. Nothing compares run_sha256 across ids.
3. [minor] tools/benchmark_ledger.py:5-6,204: The documented usage is wrong.
   Mechanism: The docstring shows `--ledger` after the subcommand, but it is defined only on the top-level parser. `append <dir> --ledger X` fails with an argparse "unrecognized arguments" error. Tests only use the global position.
4. [minor] tools/benchmark_ledger.py:92,114,116,151,189: Some malformed input raises tracebacks instead of `LedgerError`.
   Mechanism: Valid JSON that is not an object (`[]`, `null`) fails on `.get`. A non-UTF-8 profile, an unhashable audit path, or a ledger row with extra fields also crash. The ledger stays unchanged, but the failure is unclear. Line 125 silently skips the profile-hash check when profile.yaml is absent or no hash is recorded, while `profile_sha` is still written.
5. [minor] tools/tests/test_benchmark_ledger.py:21: The seed test uses an invented `oracle seed=2027` format.
   Mechanism: The real iteration run has only `course=seed-2027`, so the real backfill leaves seed empty and the regex path is never exercised on real data. Not covered by tests: concurrency, a failing second run in a batch, non-object JSON, and CRLF rewrite (LF output changes existing bytes).

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: none (read-only). The handback's 8-test pass is UNVERIFIED by me.
Missing acceptance coverage: The CSV shows 363.3706 s / 376.1241 s, 6/6, audit true / false, matching the handoff. The original artifacts are UNVERIFIED (Sol). Still to show: concurrent-append safety, a duplicate run_sha256 under a different id, and the documented CLI form working.
relayed-from: artifacts/agents/T-0002/sonnet-review-r1.md

### 2026-10-05T00:18:03-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0002   Candidate: ac49e9e917bf31138d76b02bb73946c7bce214ca   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] tools/benchmark_ledger.py:14: Individual metric semantics are absent from the module documentation and both CSV notes fields, despite the Handback saying they are documented.
   Mechanism: `min_clearance_m` is a conservative swept lower bound, `backups` counts recorded recoveries, and `elapsed_s` measures mission wall time. Generic column names can invite stronger or different interpretations. Document these definitions alongside the ledger, including what `utc` represents for each layout.
   Evidence: Source mappings at lines 102,107,139–143; original recovery records and audit fields. Both existing recovery entries represent completed straight backups.

Observation: Both rows exactly reproduce from their primary artifacts. Elapsed times are 363.370586434 / 376.124076397 seconds; destinations 6/6; audit true / false; health failures 0 / 4. Run, audit and profile byte hashes match. Historical iteration commit/player hashes match live.json; absent sandbox commit/player provenance remains empty. Iteration seed remains empty per ANSWER.

Inference: Different course/profile hashes preclude a controlled comparison. Sandbox geometric success does not establish aggregate audit success. No new live or hardware result is claimed.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: none (read-only). Checks: independent artifact-field/hash comparisons and Python `build_row()` equality against both committed CSV rows; zero differing columns. Reported eight unit-test passes not independently rerun.
Missing acceptance coverage: Metric definitions above. Backfill values and audit binding satisfy the evidence requirements; claim `tested` fits offline scope. Usage: UNMETERED.
relayed-from: artifacts/agents/T-0002/sol-review-r1.md

### 2026-10-05T00:19:44-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Request revision r2, same three owned paths, new commit (do not amend ac49e9e). Sonnet requests changes; Sol independently verified both real rows, approving with a metric-documentation nit. Read the relayed reviews above.
1. Serialize the entire ledger read/validate/replace transaction with an exclusive cross-process mechanism. Contention must wait boundedly or fail clearly without losing rows; never auto-break a foreign lock. Include a meaningful concurrent-process/lock regression.
2. Reject duplicate run_sha256 under a different run_id, and validate/normalize explicit/default run IDs (including dot paths). Same ID + identical evidence remains a no-op; conflicting evidence fails. Validate existing ledger row shape/identity so append cannot normalize corruption silently.
3. Fix --ledger CLI documentation/behavior; reject non-object JSON and malformed metadata/profile/ledger with clear errors. Preserve existing row bytes on successful append if practical, or explicitly define logical append semantics/line-ending normalization and test that values never change. Missing profile bytes must not imply verified identity; add an explicit binding state or fail conservatively when a recorded hash cannot be checked.
4. Document actual elapsed_s, min_clearance_m, backups and utc semantics (Sol). Use realistic seed fixtures; absence remains empty per Q1. Cover invalid second backfill input preserving ledger.
No new live work, batch-format support, policy/auditor changes or general refactor. Up to 3 focused check invocations and 20 minutes for r2, then hand back immutable SHA. Sonnet exact model confirmed, r1 reported API-equivalent USD 0.1124754; interactive/Sol usage unmetered. No new paid worker. Stop on scope ambiguity.

### 2026-10-05T00:19:59-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DECISION r2 received. No questions. Same three paths, new commit on top of ac49e9e, 3 checks, 20 minutes.

### 2026-10-05T00:22:07-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Revision 2: candidate f667d57 (r1 ac49e9e retained). Items 1–4 addressed; see the Handback section, which also
corrects my r1 claim that the semantics were documented. Ten tests pass, including six concurrent processes with no
lost rows. The ledger was regenerated for the new profile_binding column with unchanged values. Three checks used. Usage UNMETERED.

### 2026-10-05 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Task: T-0002   Candidate: f667d570386edaeec91e24d5ef8cfc09099baaef   Scope: code
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] tools/benchmark_ledger.py:160-164,162,211: Values and hashes come from separate reads.
   Mechanism: run.json and the audit are parsed, then re-read for sha256. A file changed in between gives a row whose hash doesn't describe the copied values, and the audit-binding check could pass on the second read. Hashing the same bytes that are parsed would close it.
   Evidence: code read.
2. [minor] tools/benchmark_ledger.py:186-187: Controller is taken from unverified profile bytes.
   Mechanism: With `profile_binding=no_recorded_hash`, controller is still parsed from profile.yaml. That is an unbound file, which conflicts with "never guess". It should fill the controller only when the binding is `matched`.
   Evidence: code read.
3. [minor] tools/benchmark_ledger.py:270-272,281-318,340: Raw OS errors bypass `LedgerError`.
   Mechanism: `main` catches only `LedgerError`. A Windows `os.replace` PermissionError, an unreadable ledger, or a failed mkdir produces a traceback. The ledger stays intact. If the pid write fails before `held=True`, the lock file is left behind.
   Evidence: code read.
4. [minor] tools/tests/test_benchmark_ledger.py:149-157: Test coverage gaps.
   Mechanism: The six-process test is probabilistic and can pass without the lock. The foreign-lock test does cover wait-then-fail. Untested: the integer `seed` branch (line 196), `no_recorded_hash`, a run dir with no live.json or provenance.json, lock release after an error, duplicate rows already in the ledger, a non-UTF-8 profile, and a backfill that fails against a non-empty ledger.
   Evidence: test read.
5. [nit] tools/benchmark_ledger.py:15-44: Ledger rows are not self-describing.
   Mechanism: The comparability caveat lives only in the docstring, and both backfilled rows have empty notes. Copied git_sha, player_sha, course and mission hashes are unvalidated free text.
   Evidence: code and CSV read.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
- Diff touches only the three owned paths.
- Audit values are copied verbatim, not recomputed.
- Unbound, missing or non-boolean verdicts become `unknown`.
- Lock is exclusive and never broken.
- Same `run_sha256` under another id and conflicting rows both fail.
- Existing bytes and line endings are preserved.

Tests run: none (read-only). The 10-test pass and real backfill are UNVERIFIED by me.
Missing acceptance coverage: CSV rows match the handoff (363.3706 s / 376.1241 s, 6/6, audit true / false, backups 1 / 1). The originals are UNVERIFIED (Sol). Executed re-ingest of the real runs is UNVERIFIED.
relayed-from: artifacts/agents/T-0002/sonnet-review-r2.md

### 2026-10-05T00:23:53-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0002   Candidate: f667d570386edaeec91e24d5ef8cfc09099baaef   Scope: evidence
Verdict: approve

Findings (ranked, ≤ 5):
None.

The metric-semantics finding is resolved: the module defines mission wall duration, conservative swept clearance, recorded recovery count, and each layout's distinct UTC event. Structured seeds are copied only when recorded; both historical rows correctly remain empty.

Observation: Both revised CSV rows reproduce exactly from the original primary artifacts. Run and audit byte hashes match; audit run hashes bind correctly. Each `profile_binding=matched` agrees with both metadata and actual profile bytes. Elapsed times remain 363.370586434 / 376.124076397 seconds, destinations 6/6, audit true / false, health failures 0 / 4. Sandbox commit/player provenance stays empty. Course and profile identities remain distinct.

Inference: The rows record historical outcomes, not a controlled comparison or new live result. Explicit missing-profile/no-recorded-hash states avoid claiming verification without evidence. Transaction code serializes ledger validation and replacement, preserves existing bytes, and rejects identical run hashes under alternate IDs; concurrent behavior was not independently rerun in this evidence review.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: none (read-only). Checks: independent Python artifact-field/hash comparisons and exact `build_row()` equality against both committed CSV rows; all checks passed. Reported ten unit-test passes and six-process concurrency result remain independently UNVERIFIED.
Missing acceptance coverage: None for the two-row evidence backfill. No live or hardware validation is required or asserted; claim `tested` matches offline scope. Usage: UNMETERED.
relayed-from: artifacts/agents/T-0002/sol-review-r2.md

### 2026-10-05T00:25:12-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Accept f667d570386edaeec91e24d5ef8cfc09099baaef for the bounded offline ledger scope. Sonnet approves with nits; Sol approves and independently reproduced both rows. All r1 major findings are resolved. Integrate exactly base 3b7fa5aac8c679552c21e7bab56f5f2a92d6a873..candidate, then run the combined core suite. No live trial or promotion.
Remaining nits are retained: ingest only completed, stable artifact directories because parse/hash reads are separate; controller from a no-recorded-hash profile is descriptive unverified file metadata, not proven runtime configuration; some filesystem failures may print tracebacks or leave an owned lock for manual diagnosis. Both backfill profiles are matched and no such error occurred. Future automatic runner integration must harden those paths and deterministic contention coverage before treating this utility as a continuously updating service. The command currently needs one audit file or explicit --audit; batch layout and automatic per-run invocation remain unimplemented. Review-reported unit checks will now run in integration. These limits do not invalidate the verified two-row backfill or change audit outcomes.
Please remain idle; no further edits/agents/live work assigned. Sonnet actual model verified in both passes, total reported API-equivalent USD 0.2554908; Opus and Sol usage UNMETERED. No new paid task this cycle without a separate allocation.

### 2026-10-05T00:27:09-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
T-0002 integrated as 26387071bbdf9bae6c21121827734d5f58882202 and 7944bde6e0de41cf095d7b6f7d854117bc491de5 via the exact reviewed range. All three owned files match candidate f667d570 byte-for-byte in git diff. Combined tools/check_core.sh exited 0: 460 tools + 85 perception + 4 GPS = 549 tests passed, including all 10 ledger behavior tests. Evidence: artifacts/agents/T-0002/integration-checks.log. The known test-only unclosed stderr pipe ResourceWarnings occurred; no failed tests. The broader checkout still includes the existing uncommitted state captured in snapshot 3b7fa5a; this is not a clean-HEAD-only result. Claim remains tested, no new lap/audit/promotion/hardware claim. Please remain idle until a new dispatch; no reply needed. No push or publication.
