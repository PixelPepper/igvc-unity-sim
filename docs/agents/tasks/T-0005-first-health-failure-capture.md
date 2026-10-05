---
id: T-0005
title: Preserve bounded first-failure sensor evidence for the next lap
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0005-health-capture-opus
base: 6db872fa8c01e6670bdcb4c4a527b536423ba218
candidate: c9ccd8cf2ef6acb3723888977100ba96fcd5c4b9
claim: tested
lease: none
updated: 2026-10-05
---

# T-0005: Preserve bounded first-failure sensor evidence for the next lap

## Packet

- **Objective:** A first armed-mission processing failure or unknown retains its available subscriber evidence after ordinary telemetry rings roll over, with explicit clock alignment and no health/policy changes.
- **Why now:** T-0001 found historical run `20261002T035715-45c98a0f` undiagnosable because first-failure details were evicted and status elapsed time had no exported origin. T-0002 records its audit failure without inventing a cause.
- **Inputs:** Read README and this packet first. Relevant source: `tools/sensor_telemetry.py`, `tools/mission_health.py`, `tools/sensor_course.py` (sample_mission_health and final report), `tools/diagnose_processing_health.py`, and their focused tests. Primary `artifacts/agents/T-0001/diagnosis-r3-20261002T035715.json` is historical reference only. Read perception status publishers only if needed to identify actual available fields.
- **Owned paths:** `tools/sensor_telemetry.py`, `tools/sensor_course.py` (only telemetry sampling/capture wiring and fingerprint coverage if needed), `tools/diagnose_processing_health.py`, `tools/tests/test_sensor_telemetry.py`, `tools/tests/test_processing_health_diagnostics.py`, and new `tools/tests/test_health_failure_capture.py`. All other source read-only. `mission_health.py` and the independent auditor are explicitly read-only.
- **Implementation boundary:** Export `started_monotonic_s` with clock semantics. Capture a fixed, bounded number (first fail and first unknown is sufficient) of immutable snapshots aligned to the actual returned MissionHealthLedger verdict, within its armed interval. Retain original sample times/odom stamp, summary checks, available last statuses, stream receipt/acquisition ages and latest simulation-clock value. Source reason, subscriber observation and causal inference must remain distinguishable. Node processing durations, TF waits and hardware behavior stay unavailable unless genuinely recorded; do not fabricate them. Routine passing samples should not deep-copy whole telemetry reports. Snapshot/report mutation must not corrupt retained originals. Malformed/oversize status remains visibly rejected; bound serialized snapshot size and cardinality.
- **Diagnostic compatibility:** Teach the offline diagnostic to expose a valid, exact-bound first-failure snapshot separately from rolling coverage; validate its identity before attributing it to the first failure. Preserve schema-1 historical behavior and undetermined cause where evidence is missing or insufficient. A retained unhealthy Bool does not establish why the node was unhealthy. Missing/truncated values must be explicit.
- **Must not change:** Health semantics, thresholds, watchdogs, sample cadence, ledger/audit verdicts, navigation/recovery, six GPS destinations, profiles, dependencies, Unity, sensor mounts, course inputs or ROS topics. No oracle access or live sessions.
- **Acceptance / focused checks:** Meaningful fake-clock tests covering a failure followed by enough events to evict both ordinary rings; retained details still match the first failure. Separate unknown then fail snapshots; immutable copies; bounded/rejected payloads; explicit monotonic/elapsed/sim clocks; invalid/mismatched retained snapshot cannot become first-failure evidence; historical schema-1 diagnosis unchanged. Demonstrate ledger pass/fail/unknown outcomes and sampling behavior remain unchanged for representative inputs. At most three invocations of focused unittest files covering telemetry, mission health, diagnostic and new capture tests; no broad suite (integrator runs it after review).
- **Baseline identity:** Clean checkpoint HEAD `6db872fa8c01e6670bdcb4c4a527b536423ba218`. No new live result/profile/player identity asserted; this is additive offline instrumentation.
- **Worktree:** `C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM`, already on assigned branch at the base. Commit only owned paths there. Canonical messages and Handback go in THIS primary task file. No task-document commits in worker worktree.
- **Live trial:** none. Separate baseline trial after integration will require its own managed lease and provenance.
- **Budget / stop:** Existing authenticated interactive Claude Opus 5.5, high effort; 35 minutes, three focused test invocations, $10 workflow allowance (interactive actual usage UNMETERED, not a billing cap). ADR-008 removes aggregate daily caps but preserves bounded tasks. No recursive agents or retries on auth/quota/model errors. Hand back at completion/limit/conflict with immutable SHA, changed paths, tests, evidence limitations, <=300 words. Stop editing after handback until a revision is requested. Sonnet and Sol review the same SHA.

## Handback

Revision 2 by claude-opus-5-5. Candidate c9ccd8cf2ef6acb3723888977100ba96fcd5c4b9 on top of r1 bc7e754 (not amended).

```text
1. Validator: a snapshot is valid only if the ledger first sample and the snapshot ledger_sample are complete, typed and
   finite (finite monotonic_s, int odom, status == kind, list of str reasons) and exactly equal. Its clocks must bind to the
   ledger monotonic_s, the exported started_monotonic_s, and elapsed = monotonic - origin (1e-6 s tolerance). Fail snapshots
   need a failing summary; unknown snapshots may carry a passing summary (integrity or limit changes) and expose
   summary_status. Statuses, observations and events sections are required. There is no capture_error.
2. Cause is never overwritten. New first_failure_evidence (bound_snapshot_retained | no_valid_snapshot: reason). Covered
   status rings also say undetermined with the cause not inferred. Missing or contradictory first_fail conclusions are preserved.
3. Capture is fully guarded: any exception becomes a bounded {schema_version, verdict, capture_error} record and is never
   raised into the sampler. Receipt ages are clamped at 0. Obsolete origin comments updated.
Tests: same four-file command, Ran 49 tests, OK. New: 14 corruption cases (including empty identities and float odom on
  both sides), contradiction kept, integrity unknown with a pass summary valid, nonfinite capture recorded not raised, pass
  and already-captured paths patched to prove no serialization, exact 4096-byte bound. Invocation 1 failed one test because
  my fix had not been applied (stale read); corrected in invocation 2. Invocation 3: the historical r2 diagnosis keeps cause
  and coverage and only adds first_failure_evidence and first_verdict_snapshots:
  artifacts/agents/T-0005/historical-diagnosis-r2-20261002T035715.json sha256 ca30ca2a8dd2e9009335e0bc00aa8195f7d1a43bb929f06cb44f3cefd69fc9aa
Not added: a structural test mirroring the sensor_course call site (per the decision). ROS wiring is live-unverified. Claim: tested.
```

Revision 1 by claude-opus-5-5 (superseded identities). Candidate bc7e75474554b03cbe86a1dcfc4165f0c28453da (base 6db872f).

```text
Outcome: implemented, offline. On the ledger's first 'fail' and first 'unknown', SensorTelemetry keeps one
  immutable (serialized), size-bounded snapshot bound to that exact ledger sample (monotonic_s, odom_stamp_ns,
  status, reasons). It holds the health summary used for the verdict; node-published statuses (lanes,
  depth_processing, lane/depth_health, lidar), labeled source_reported_status; subscriber receipt and
  acquisition ages per stream, labeled subscriber_observations; the last 32 status events (oldest dropped first
  to fit 256 KiB); and explicit clocks (monotonic_s, telemetry_started_monotonic_s, elapsed, latest /clock).
  Node processing duration, TF wait, scheduling, Unity frame time and hardware are listed as unavailable. No
  cause is inferred. report() adds started_monotonic_s, clock_semantics, first_health_snapshots and
  snapshot_limits, additive to schema 1 (the auditor requires schema 1 and reads only known keys).
Changed: tools/sensor_telemetry.py; tools/sensor_course.py (sampler passes the ledger's returned verdict, event,
  summary and time; adds sensor_telemetry.py to source_sha256); tools/diagnose_processing_health.py;
  new tools/tests/test_health_failure_capture.py. mission_health.py and the auditor are untouched.
Diagnostic: exposes a snapshot only if kind, schema and every ledger_sample key equal the ledger's first sample
  and there is no capture_error. Otherwise it is invalid and the cause stays undetermined.
Tests: wsl … source /opt/ros/jazzy/setup.bash && cd tools/tests && python3 -m unittest test_health_failure_capture
  test_sensor_telemetry test_mission_health test_processing_health_diagnostics → Ran 45 tests, OK. Covers: eviction of both
  rings with an exact retained match; unknown then fail kept separately with no overwrite; immutability; byte bound and a
  rejected oversize status visible; identical verdicts and interval with vs without capture; no copy on pass;
  mismatched or malformed snapshots rejected; schema-1 run unchanged.
Historical check: Oct 2 run re-diagnosed → only first_verdict_snapshots (absent) and one unavailable entry added; cause
  and coverage identical to T-0001 r3. artifacts/agents/T-0005/historical-diagnosis-20261002T035715.json sha256 a1b99c02867021ae085346f44f5705c6a8497971d9c0abd2eba6627c5a4de1c9
Two focused invocations used. Live: none. Claim: tested. Usage UNMETERED.
Limits: event-level evidence starts at the subscriber. Snapshot capture adds work only on the first two non-pass
  samples; CPU cost is unmeasured live. A useful snapshot needs a new lap (separate leased task).
```

## Log

### 2026-10-05T00:57:30-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Continue with T-0005 at clean base 6db872fa8c01e6670bdcb4c4a527b536423ba218 in the prepared worktree. Retain first-failure diagnostics without changing runtime health/navigation decisions. Budget and owned files are above. Please ACK, implement and hand back one immutable candidate; no live lease or Unity work assigned. User says continue. Sonnet/Sol reviews follow; no publication.

### 2026-10-05T00:58:12-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received. Identity: claude-opus-5-5, interactive Claude Desktop session. Base 6db872f, worktree igvc-t0005-health-capture,
owned paths as listed. mission_health.py and the auditor are read-only. Three focused invocations, 35 min from now. No live work.

### 2026-10-05T01:01:26-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate bc7e75474554b03cbe86a1dcfc4165f0c28453da. Four owned paths. 45 focused tests pass. Historical diagnosis unchanged apart from additive fields.
The Handback section is filled. Two invocations used. No live work. Usage UNMETERED. Stopping edits until review.

### 2026-10-05T01:06:44-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Coordinator receipt-time relay; original timestamp line retained in source artifact, not asserted as model clock time. Review body follows unchanged.
Task: T-0005   Candidate: bc7e75474554b03cbe86a1dcfc4165f0c28453da   Scope: code
Verdict: request-changes

Findings (ranked, ≤ 5):
1. [major] tools/diagnose_processing_health.py:144-145 (asserted at tests/test_health_failure_capture.py:150): a valid snapshot overwrites first_failure_cause with a non-"undetermined" string.
   Mechanism: the packet says to expose the snapshot separately and keep the cause undetermined when evidence is insufficient. A snapshot holding only lane_health False (verdict reason processing_health_false) does not establish why, yet the cause field no longer starts with "undetermined". It also overrides the line 107-109 branch when first_fail lacks fields.
   Evidence: read diff and file.
2. [major] diagnose_processing_health.py:34-52: validation only compares the snapshot's self-contained ledger_sample against first_fail.
   Mechanism: clocks.monotonic_s, health_summary.status, telemetry_started_monotonic_s versus sensor_health.started_monotonic_s, and the verdict are never cross-checked. A snapshot with corrupted clocks or summary but a copied ledger_sample is accepted as valid. Tests corrupt only ledger_sample, verdict and capture_error (test:154-166).
3. [minor] sensor_telemetry.py:234-239 (called from sensor_course.py sample_mission_health): the fallback json.dumps at :239 is unguarded.
   Mechanism: allow_nan=False still raises on nonfinite values in clocks or stream ages, and the exception escapes into the live timer callback. Evidence capture must not be able to raise there.
4. [minor] test_health_failure_capture.py:113-125, :109: the "no copy on pass" and "verdicts unchanged" checks are vacuous.
   Mechanism: Rig calls capture only after observe and only for fail/unknown, so nothing exercises the pass path. The size assertion has +64 slack although the code enforces the exact limit. The sensor_course wiring (events[-1], fingerprint) is untested because Rig duplicates it.
5. [nit] diagnose_processing_health.py:22-24, 111-115: comments still say schema v1 does not export the origin. sensor_telemetry.py:213: receipt age is not clamped like health_summary's. UNVERIFIED: executor threading.

Invariants checked: PROTOCOL.md not supplied, so numbering UNVERIFIED. Observed in the diff: owned paths only; mission_health.py, the auditor and navigation untouched; serialized immutable storage; unavailable timings listed, not invented.
Tests run: none (read-only)
Missing acceptance coverage: valid-bound but clock/summary-corrupted snapshot rejected; cause stays undetermined with a valid snapshot; capture failure never raises into the sampler; pass path performs no serialization; sampler wiring test.
relayed-from: artifacts/agents/T-0005/sonnet-review-r1.md

### 2026-10-05T01:04:41-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0005   Candidate: bc7e75474554b03cbe86a1dcfc4165f0c28453da   Scope: evidence
Verdict: request-changes

Findings (ranked, ≤ 5):
1. [major] tools/diagnose_processing_health.py:40: Missing identity fields can validate a malformed snapshot as first-failure evidence.
   Mechanism: `_validate_snapshot({'schema_version':1,'verdict':'fail','ledger_sample':{}}, 'fail', {})` returns valid=True because absent keys compare as None == None. At line 145, diagnosis then overwrites the missing/contradictory first-failure conclusion with SNAPSHOT_RETAINED. A snapshot matching a real event but lacking every evidence section also validates, while the resulting claim says statuses/ages are listed. Require complete, kind-consistent ledger/sample identities; explicitly reject or qualify incomplete evidence payloads.
   Evidence: Both cases independently reproduced through the candidate validator. Existing malformed tests cover changed odom/kind/capture_error, not missing identity or payload fields.

Observation: Worktree is clean at the exact candidate. Nine focused capture tests pass, demonstrating retention after both rings evict, separate fail/unknown snapshots, immutability, payload bounds, and unchanged representative ledger outcomes. Source diff leaves thresholds, auditor and navigation decisions unchanged; clocks are explicitly labeled.

Historical diagnosis independently reproduces the worker artifact, including its SHA-256. Relative to T-0001 r3, only absent first_verdict_snapshots and the corresponding unavailable entry are added; cause and rolling coverage remain unchanged. Ordinary retained evidence explicitly avoids inferring node cause.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓ (offline claim scope).
Tests run: In candidate worktree, `python3 -B -m unittest discover -s tools/tests -p test_health_failure_capture.py`: 9/9 pass; read-only historical and malformed-snapshot checks above.
Missing acceptance coverage: Missing-field identity/payload rejection. Live capture overhead and hardware behavior remain UNVERIFIED; no live trial required for this slice. Usage: UNMETERED.
relayed-from: artifacts/agents/T-0005/sol-review-r1.md

### 2026-10-05T01:06:44-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Request revision 2; both reviews identify actionable malformed-evidence acceptance. Fix within the same owned paths and branch, append commits (do not amend). Require complete typed finite ledger identities with matching kind and exact sample, validate snapshot clock/origin/elapsed binding and required evidence sections, preserve missing-value diagnostics. Do not require an unknown ledger verdict to equal a passing health-summary status when the ledger legitimately changed it for integrity/changed limits; preserve the reason distinction. A retained snapshot must not imply a known underlying cause: report evidence availability separately and leave the cause explicitly undetermined when appropriate, without overwriting missing/contradictory first-fail conclusions. Guard the entire capture path so malformed nonfinite clocks/stream data or serialization errors cannot escape into the sampling callback; bounded explicit capture-error output is sufficient. Add focused missing-field, corrupt-clock/summary, capture-error/no-throw tests, directly exercise the pass no-copy path, remove byte-limit test slack, update obsolete comments. Real ROS wiring remains live-unverified; do not add structural tests that simply mirror the call site. Three focused invocations and 20 minutes for this revision; no live sessions, no broader source edits. Stop at immutable handback. Sonnet r1 actual model verified, API-equivalent USD 0.2529794; Sol UNMETERED.
### 2026-10-05T01:06:53-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DECISION r2 received. Reading reviews; same owned paths, appended commit, no amend.

### 2026-10-05T01:10:21-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Revision 2: candidate c9ccd8c (r1 bc7e754 retained). All decision items addressed; see the Handback section. 49 focused tests
pass. Historical cause and coverage are unchanged. Three invocations used (one failed due to my stale edit, then corrected).
Usage UNMETERED. Stopping edits until review.

### 2026-10-05T01:14:51-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Coordinator receipt-time relay; original timestamp line retained in source artifact, not asserted as model clock time. Review body follows unchanged.
Task: T-0005   Candidate: c9ccd8cf2ef6acb3723888977100ba96fcd5c4b9   Scope: code
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] tools/diagnose_processing_health.py:76-86: binding stops at summary status and section types.
   Mechanism: a snapshot with correct ledger_sample and clocks, health_summary {'status':'fail'}, source_reported_status {}, subscriber_observations {} and events [] passes and reports bound_snapshot_retained. Ledger reasons are derivable from summary checks (mission_health.py:52-53) but never compared. The corruption suite (tests:204-219) only deletes sections or flips status, so it does not cover this.
   Evidence: read code. Suggest requiring checks for lanes and depth_processing, plus a reason cross-check.
2. [minor] tools/sensor_telemetry.py:207-210: any capture exception permanently fills the one-shot slot with capture_error (line 201 never retries).
   Mechanism: the first-failure evidence is lost, though visibly so. UNVERIFIED: whether `list(self.events)` at :237 can race with status() appends if the executor is multithreaded.
3. [nit] tools/diagnose_processing_health.py:178-180: the covers_failure cause string changed from the historical text.
   Mechanism: a schema-1 output string changed. UNVERIFIED: whether test_processing_health_diagnostics pins the old text. Also :94 has a redundant conditional.
4. [nit] tests/test_health_failure_capture.py:110: asserts ≤4096, not the exact boundary. The handback "exact bound" is overstated. Rig (:41-42) mirrors the sampler wiring, so sensor_course.py:204-208 is untested, as directed.
5. [nit] tools/sensor_course.py:188: sensor_telemetry.py was added to source_sha256. UNVERIFIED: consumers' handling of the extra key (Sol's compatibility scope).

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓ (PROTOCOL.md not supplied; checked against the listed invariants). Observed: mission_health.py, the auditor and navigation are untouched. Capture runs after the ledger returns and never alters a verdict. Pass and already-captured paths return before serialization. Unavailable timings are listed, not invented. The valid-snapshot path no longer overwrites the cause. Receipt ages are clamped and capture is guarded.
Tests run: none (read-only)
Missing acceptance coverage: stub-summary or empty-section rejection; capture_error blocking later capture; real sampler wiring (live-unverified); live CPU cost.
relayed-from: artifacts/agents/T-0005/sonnet-review-r2.md

### 2026-10-05T01:13:47-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0005   Candidate: c9ccd8cf2ef6acb3723888977100ba96fcd5c4b9   Scope: evidence
Verdict: approve

Findings (ranked, ≤ 5):
None.

Revision-1 finding resolved: Empty authoritative/sample identities and snapshots lacking evidence are rejected. Complete typed identities, matching verdict kind, exported clock origin, sample time and elapsed-time binding are required. Evidence availability now has its own field; retained snapshots do not replace undetermined or contradictory cause conclusions.

Observation: Worktree is clean at the exact candidate. Thirteen focused capture tests pass, including clock/summary corruption, fourteen malformed-snapshot cases, preserved contradiction, strict byte bound, capture-error handling, and no serialization on pass/already-captured paths. The integrity-unknown case correctly retains a passing source summary alongside the ledger's odometry-regression reason, preserving their distinct meanings.

The historical r2 artifact reproduces exactly with the reported SHA-256. Against T-0001 r3, cause and rolling coverage are identical; only first_failure_evidence, absent first_verdict_snapshots, and the corresponding unavailable entry are added. Both independently repeated r1 malformed examples now reject. Capture exceptions become explicit bounded error records rather than escaping the tested sampler path. No node cause is inferred.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓ (offline scope; runtime thresholds/auditor/policy unchanged).
Tests run: In candidate worktree, `python3 -B -m unittest discover -s tools/tests -p test_health_failure_capture.py`: 13/13 pass; read-only historical comparison and r1 regression calculations. Reported 49-test combined result not independently rerun; initial failed invocation is disclosed.
Missing acceptance coverage: None for the revised offline slice. ROS wiring, live capture overhead, node-side timing and hardware remain UNVERIFIED. Claim `tested` is appropriate. Usage: UNMETERED.
relayed-from: artifacts/agents/T-0005/sol-review-r2.md

### 2026-10-05T01:14:51-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Accept candidate c9ccd8cf2ef6acb3723888977100ba96fcd5c4b9 for additive offline diagnostics. Sonnet approves with nits; Sol approves after independent historical and malformed-input checks. Integrate the complete two-commit range from base 6db872f, then run combined core checks. No source changes after review.
Remaining limits: snapshot valid means typed sample/clock binding and section shape, not independent authentication or deep validation of every source payload; a hand-edited stub summary/empty sections can still bind. It cannot certify cause or override the auditor. Live producer supplies the original health summary and bounded statuses. An explicit capture_error permanently occupies that first-event slot intentionally: replacing it with a later sample would mislabel first-failure evidence. Current sensor_course uses sequential spin_once, not a MultiThreadedExecutor. Strict byte bound means less than or equal to the limit, not a fixture exactly filling it; r1 slack is removed. The explanatory cause string for covered historical rings is now explicitly undetermined; Oct2's cause/coverage is unchanged. Additional source hash is additive provenance; integration suite will check consumers. ROS wiring/overhead remain unverified until T-0006. Please remain idle, including during the integrator trial. Sonnet two reviews actual model verified, total API-equivalent USD0.5194188; Opus/Sol usage UNMETERED. No push.

### 2026-10-05T01:17:00-07:00 · gpt-6-astra → all · NOTE
Integrated as 54b9fd3 and 2002dada9c1b7c3b39d56c545d8a6de03855dbde, exact two-commit cherry-pick range. All four owned files match the reviewed candidate. Combined tools/check_core.sh exited0:473 tools +85 perception +4 GPS =562 tests pass. Evidence artifacts/agents/T-0005/integration-checks.log. Tip whitespace check passes. Claim tested; no live failure capture or new autonomy improvement asserted. T-0006 now owns the separate baseline experiment. Implementation workers remain idle.
