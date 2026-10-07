---
id: T-0057
title: Reduce eager hazard-column enumeration without changing collision decisions
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0057-hazard-enumeration-opus
base: 8547bf53db1a757779d38006f14617ac4d95f1a9
candidate: 159530ca09d0c7c773369b8f28355562f4a4d307
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

Read README introduction. Sole HEADLESS owner opus-t0057-hazards-20261006T1752.
Worktree C:/Users/brand/.codex/worktrees/igvc-t0057-hazard-enumeration/IGVC SIM.
Interactive T0056 remains independently reserved and cannot edit these files.
Root holds artifacts/agents/T-0057/implementation.lock during dispatch.

Hypothesis: _rectangle_clear eagerly builds every hazard column in a row before
testing the first collision. Lazy ascending set-bit enumeration can avoid wasted
work on early rejection without changing any collision decision. This is a
source-level hypothesis, not a measured live bottleneck. T0051's time-limited
diagnosis does not prove this optimization will recover a route.

Own tools/sensor_route_policy.py only within _rectangle_clear and a tiny private
iterator helper if needed; tools/tests/test_rectangle_hazard_enumeration.py (new);
tools/benchmarks/rectangle_hazard_enumeration.py (new). No other edits.
Keep exact cell visitation order, hazard predicate, SAT arithmetic/comparison,
grid-boundary behavior and early-return result. Preserve scalar hazard_rows=None
path. No coordinate quantization, caches, changed masks, footprint shrink, sampling
reduction, budget increases, priority/cost changes, dependencies or dataset access.

Add differential behavior tests comparing optimized hazard-bit rows with the
existing scalar geometry check on deterministic synthetic observed grids. Cover
unknown/lethal cells, cost99 distinction, empty/sparse/dense rows, rotated and
asymmetric footprint, exact boundary/contact cases. Preserve input arrays. Tests
must exercise geometry outcomes, not assert source text or mirror helper logic.

Author a fixed-size microbenchmark accepting an immutable baseline module path
and the candidate path. Use generated synthetic grid fixtures only; no capture,
course/WORLD/teacher input. Compare decisions first and refuse timing on mismatch.
Predefine empty, sparse, dense-early-rejection and mixed batches. Fixed seed, one
warmup and five fixed paired rounds in alternating order; no adaptive repetitions,
significance testing or optional stopping. Cap total benchmark at60seconds, return
all timings/counts and source hashes. No clocks mocked in production. Report raw
strata and mixed medians; do not hide a slower stratum. Root will run once.

Predeclared performance gate: accept as a performance candidate only if mixed
candidate/baseline median ratio <=1.00 and dense early-rejection ratio <1.00, with
neither empty nor sparse ratio >1.10. Failure means retain/reject this candidate,
not rerun until favorable. Passing is microbenchmark evidence, not live benefit.

No tests/imports/benchmark execution during implementation. Root executes focused
tests and exactly one benchmark under all three simulator locks after actual
committed handback. No historical replay or live mission, Unity build, ROS, other
provider/delegation, primary edits or commits outside three owned files. Return
<=300word SHA/files/NOT RUN commands and risks. ExactOpus5.5/high6min/USD5,
no provider-error retries. Sonnet checks semantic invariance/benchmark validity,
Sol verifies actual evidence. Do not integrate or push. Stop at handback/blocker.

## Log


### 2026-10-06T17:51:29-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

HEADLESS opus-t0057-hazards-20261006T1752 only, per packet. Interactive T0056 remains separately reserved; do not duplicate. Root checked all3locks and no simulator processes/ports before preparation, released them; this worker may edit only, no tests. Source policy path is clean at8547bf5. No active prior owner.

### 2026-10-06T17:54:59-07:00 · gpt-6-astra → all · HANDBACK

Opus completed176.01s/USD0.663182 exactmodel, candidatea3a4844, only three owned files, no tests/imports/benchmark executed. Root frozen baseline Git blobs in baseline-8547bf5 with manifest. Implementation assignment ended. Sonnet now reviews code and benchmark before any timing attempt; root runs three geometry suites under all3locks. Performancegate remains preregistered, no reruns after valid measurement failure. Interactive T0056 slot still reserved without ACK; no extra worker.

### 2026-10-06T17:56:39-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0057/review-a3a4844/sonnet-static-review.md

**Verdict: no blockers in the code or tests. The benchmark needs fixes or explicit caveats before the single attempt.** I read the diffs and files only. I ran nothing, so none of this is verified numerically.

**`_rectangle_clear` and `_set_bit_columns`**
- Columns are visited in the same ascending order as the old list, so the first-collision result is unchanged. The function is pure and returns a bool, so order only matters for the decision.
- The SAT arithmetic, bounds check, 0 ≤ value < 100 skip and the 99 handling are untouched.
- `if not bits: continue` is equivalent to iterating an empty list.
- The scalar `range` path is unchanged. The only difference is that `span` is now computed once per call even when `hazard_rows is None`, a negligible cost.

**Tests**
- They compare the bitset path against the scalar path of the same candidate file, not against the baseline. That is acceptable because the scalar path is unchanged.
- Geometry is covered: unknown, 99, 100 and out-of-range values, edge contact, rotated bodies, grid boundaries, rows wider than a machine word, and a random sweep that asserts both outcomes occur.
- The wide-row test has no `expected` value.
- Nothing tests `_set_bit_columns` directly.
- Several cases depend on exact float flooring, so the root run is the check on those.

**Benchmark, fix or document before running**
1. The docstring and report never say GC is disabled during measurement. Add that.
2. There is no explicit limitations text. State these in the report:
   - The fixtures are synthetic and the poses are uniform random, not planner-distributed.
   - It times only `_rectangle_clear`, with 1500 calls per stratum and 5 rounds.
   - The 60 s cap includes fixture generation and the decision pass, and it is only checked between timed calls.
   - Dense is a 60% hazard rate chosen to favour early rejection.
   - Empty is the 99-only grid.
   - Some poses fail the bounds check and return before any enumeration.
3. Round order is not balanced. The warmup uses the baseline-first slot, so the five measured rounds run candidate-first 3 times and baseline-first 2 times.
4. No hash covers the fixtures, the decision vectors or the script. Only the two module SHA-256 values are recorded.
5. The exit code is 0 when the gate fails, and `--output` silently overwrites an existing file. Use a fresh output path, or write with `'x'` mode, so a failed attempt can't be erased. The gate verdict is in the JSON.
6. The baseline must come from `git show 8547bf5:tools/sensor_route_policy.py`. The candidate must be the clean working-tree file at `a3a4844`. Root should check both SHA-256 values against those blobs.

**Permission**
I'd allow one run once items 1–2 and 4–6 are handled. Item 3 can be accepted if `round_orders` is retained and noted as a limitation. A failed gate should be kept and rejected, with no rerun. A passing result is microbenchmark evidence only, not live benefit.

### 2026-10-06T17:56:39-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

SoleHEADLESS opus-t0057-hazards-20261006T1752-r1; previousworkercompleted. Sameisolated igvc-t0057-hazard-enumeration worktree/branch, startinga3a48448cbfbcff6f24f7442a383373bf59f04f5. Rootimplementation.lock. Sonnetfoundnocode/testblockers;60geometrytests PASSED underlocks. Benchmark has NEVER RUN. Edit ONLY tools/benchmarks/rectangle_hazard_enumeration.py to bind evidence before its single attempt. Do NOT change fixtures,seed,calls,roundorder,warmup,timing algorithm,gate thresholds or production. Add explicit GC-disabled measurement field/doc and actual GC priorstate; limitations:synthetic uniform poses, only rectangle routine not wholeplanner/live, dense60% chosen early-rejection, alternating5rounds necessarily3vs2order, capcheckedbetweenbatches notinside. Correct reviewer mistakes: empty fixture has random0..98 plus5%99, not99-only; don't assert boundary exits occur unless measured/checked. Add SHA256 of benchmark script, full generated fixtures (costs,hazardrows,poses deterministic encoding) and baseline/candidate/scalar decision vectors. Preserve allrawtimings. Refuse existing --output BEFORE running; exclusive final write. Gatefailure must remain recorded and visible (returnnonzero onreject withJSON result retained); rootwillparsegate not inferexit0. Sourcehashbaseline/candidate remains, rootpinsGitblobs. No tests/imports/benchmark/providers/delegation/live. Commit only harness returnSHA/NOT RUN <=300words.6min/USD5 exactOpus5.5/high, no provider-error retries. RootwillfocusedSonnetrereview newharness then runexactlyonce underall3locks; source correctness60tests isn't rerun unless changed. Stop atcommit/blocker.

### 2026-10-06T18:00:20.906011-07:00 · gpt-6-astra → all · HANDBACK

Opus revision1 completed87.01s/USD0.35738 exactmodel; sole benchmark revision159530c. No benchmark execution;60 prior tests cover unchanged policy/tests. Assignment ended; focused Sonnet review now occupies released slot. T0056 interactive remains reserved, no ACK. No timing attempt yet.

### 2026-10-06T18:01:02.625488-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0057/review-159530c/sonnet-static-review.md

**Accepted for the single fixed benchmark run, with no performance claim.** I found no blockers. I only read the diff of `159530c` against `a3a4844` and the full file; I executed, imported and edited nothing.

**Unchanged (the diff touches none of these lines):**
- `SEED=57`, `CALLS_PER_STRATUM=1500`, `ROUNDS=5` and the one warmup.
- Fixture generation, the pose generator and `decide`/`timed`.
- The round-order logic, the time-cap check and the four gate checks.

**Provenance hashes:**
- The report now hashes the script, both policy modules (from the loaded files), the per-stratum and combined fixtures, and the scalar, baseline and candidate decisions.
- The fixture and decision encodings are accurate.
- Fixtures are hashed before any call, and the existing input-mutation check covers later changes.

**GC:**
- It is collected once, disabled before the warmup, and restored in `finally`.
- The recorded `enabled_after_timing` is read after restoration. The other two GC flags are static `True` values, which matches the code.
- Mismatch and time-cap returns carry no `gc` block on the mismatch path, which is harmless.

**Limitations:** these match the code. The round order gives candidate first in rounds 1, 3 and 5 and baseline first in the warmup and rounds 2 and 4. The cap is checked per 1500-call batch.

**Output and exit status:**
- An existing `--output` is refused by `parser.error`, exit 2, before anything runs.
- The final write uses mode `'x'`.
- The exit status is 0 only when `gate.accepted` is true. Every return path sets that key, and exceptions exit nonzero.

**Non-blocking caveats:**
1. `swept_footprint.py` is imported by both modules but its hash is not recorded. Record its blob at the commit externally.
2. If the `--output` parent directory doesn't exist, the failure happens after the run. The report is still printed, but that would waste the single run, so confirm the directory exists first.
3. The new fixture hashing and encoding run before timing and count against the 60 s cap. The effect should be negligible, but it is a change from the prior revision.
4. The report holds no git SHA. Capture the commit and a clean worktree outside the report.

Root binds swept_footprint.py in expected.json and frozen baseline manifest; existing output directory and clean candidate checked by driver. One attempt now authorized under all3locks. Sonnet completed33.55s/USD0.087098 exactmodel; slot released.

### 2026-10-06T18:01:42.725057-07:00 · gpt-6-astra → gpt-6.1-sol · DISPATCH

Single fixed benchmark complete underall3locks; all6000 decisions matched, one warmup/five paired rounds retained. Gatepassed: candidate/baseline medians empty0.525555,sparse0.664895,dense0.850027,mixed0.813701. ReportSHA a8bffec01fb3e8af87ddd832e10e60d93ad0c18fad94a72f4d0633bfa7f5387a. No prior timing attempts. Native batch_evidence exactSol reviews sourcebinding/60tests/rawtimings/lease/gate; no execution. No liveperformance claim. Integration prepared but waits evidence verdict.

### 2026-10-06T18:03:01.943057-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0057/benchmark-once/sol-evidence-review.md

# T0057 evidence review

Evidence supports scoped integration of candidate `159530ca09d0c7c773369b8f28355562f4a4d307`, with no live/whole-planner benefit claim.

Verified60 geometry tests passed at a3a4844, exit0; raw log hash matches. Candidate159530c is clean and changes only the benchmark after that validation. Policy/test hashes remain identical. All four expected source hashes match current bytes. Frozen baseline policy/swept-footprint hashes and Git blob IDs match manifest8547bf5; report script/module hashes match their pins.

One attempt marker, one warmup and five paired rounds are preserved. Report/raw log SHA256 matches result.json. Parent0.437s, report0.315s, no timeout; lease PID51996 held18:01:03.623–18:01:04.194 PDT through the three-lock wrapper. The marker refuses repeats, including after failure; no failed timing attempt is recorded. Pre-benchmark harness revision is not a timing retry.

Independently recomputed medians from all five raw rounds:

| Stratum | Baseline→candidate median ns | Ratio |
|---|---:|---:|
| Empty | 2700842→1419441 | 0.52555 |
| Sparse | 2738882→1821070 | 0.66490 |
| Dense early rejection | 4076126→3464817 | 0.85003 |
| Mixed | 4056056→3300417 | 0.81370 |

All preregistered thresholds pass. Counts total6000 fixture cases; clear+blocked equals1500 per stratum. Reported scalar/baseline/candidate decision digests match in every stratum. Fixture/vector hashes are report-bound, not regenerated by this review. Driver exit alone would not establish gate acceptance; the actual gate and ratios were checked.

Limits: synthetic uniform poses, smaller variable bodies than canonical whole-body bounds, GC disabled, candidate-first3/baseline-first2 measured rounds, dense60% hazards favoring rejection, and only _rectangle_clear timed. Boundary-exit frequency is unmeasured; cap checks occur between batches. Canonical runtime footprint/SAT remain untouched. No significance, recovery efficacy, calibrated hardware or live speed claim follows.

Report/log SHA256: `a8bffec01fb3e8af87ddd832e10e60d93ad0c18fad94a72f4d0633bfa7f5387a`.


### 2026-10-06T18:03:01.943057-07:00 · gpt-6-astra → all · DECISION

Accept159530c for scoped integration, based on both reviews, unchanged collision arithmetic and60tests plus single preregistered benchmark. No live/wholeplanner claim, no latency candidate acceptance. Root acquiresall3locks before integration/processchecks and retains through primary focused tests. Only a3a4844 and159530c; external edits preserved.

### 2026-10-06T18:03:53.011715-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0057/integration/sol-integration-review.md

# T0057 integration evidence review

Accept tested integration ending `97e4f768e02ec90db61c6c7a051f15ac61dd86b1`.

Git records show the two scoped cherry-picks:a6c2511abf5de0b7accbd51ada5b2c89a26ac5c1 and97e4f768. They change only the policy, focused test and benchmark. All four recorded primary byte hashes, including swept_footprint, match reviewed candidate159530c pins. Line-ending reconciliation is empty.

Saved primary validation confirms60 tests passed, exit0, no timeout;7.873s suite/7.969s parent elapsed. Log SHA256 independently matches `36175e38e9e8541152d11132be5d206e3a7286d0e3fa2a36d5c911bf90eb3458`. Lease records cover PID45592,18:03:02.755–18:03:11.013 PDT.

This verifies the reviewed source is integrated and passes focused geometry checks. It does not establish live speed, whole-planner latency, recovery success or calibrated autonomy. The earlier synthetic benchmark limits remain unchanged. No benchmark, tests or code review were repeated here.


### 2026-10-06T18:03:53.011715-07:00 · gpt-6-astra → all · INTEGRATION

Integrated a3a4844/159530c as a6c2511/97e4f768e02ec90db61c6c7a051f15ac61dd86b1. Primary60geometry tests passed7.873s, exit0; exact reviewed bytes, no line-ending changes. Source and tests unchanged from candidate; testlog36175e38e9e8541152d11132be5d206e3a7286d0e3fa2a36d5c911bf90eb3458. Both code/evidence reviews complete including new primary validation; all3simulator locks held throughout integration/checks then released. This is tested integration and single synthetic microbenchmark evidence only; no live/wholeplanner/recovery claim. No benchmark repeat, provider errors, live missions, Unity builds or pushes. All implementation/review assignments completed. External dirty files retained. T0056 interactive slot remains reserved without ACK; no duplicate.
