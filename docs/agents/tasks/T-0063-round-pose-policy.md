---
id: T-0063
title: Propagate dataset pose policy through learning rounds and cache reuse
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0063-round-policy-opus
base: f9594e6c3e462bb6d223fed3b57edc5661eebd34
candidate: 74b5931103f2e40ed263e9049ff45864714722f9
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started Claude session interactive-opus-t0063-20261006,
same actual session as completed T0062. ACK alias/model claude-opus-5-5. One reserved
worker slot, no headless duplicate. Isolated worktree
C:/Users/brand/.codex/worktrees/igvc-t0063-round-policy/IGVC SIM,
branch codex/t0063-round-policy-opus, base f9594e6c3e462bb6d223fed3b57edc5661eebd34.
Read README intro, this packet and source APIs. Primary task log authoritative.
T0061+T0062 accepted candidates are on this branch; primary not integrated.
Slice3: runtime/teacher/model algorithms untouched. No real training, labels,
replay, model promotion, live or primary integration. Root runs combined checks
and reviews before integrating complete candidate range.

Own ONLY tools/learning/run_round.py, NEW tools/tests/test_round_pose_policy.py,
and tools/tests/test_learning_round.py necessary orchestration fixture/assertion
compatibility. Do not edit sharedreader/build_dataset/train/gate/classifier or
teacher/runtime, primary source. Report blocker if scope is insufficient.

Implement:
1. Reuse dataset_policy.PosePolicy/shared flags. measured-only default and explicit
combinable predicted/unknown optins; no implicit historical optin. Pass selected
flags into BOTH build/train command argv for route/corridor. Pass pose_policy
object to DIRECT round_gate.gate. Record canonical policy in round reports and
build/train/gate step results, including empty/error outcomes where available.
2. Include canonical policy + policy-cache version in build/train/gate cache
inputs. Old caches with absent policy cannot stand in for new-policy validation.
Round.step's imported status must not bypass input identity for these steps;
preserve legitimate imported collection/replay and plan freezing. Gate's early
same-current/new-model SHA shortcut also needs bound policy/data identity, not
just a model hash. Changing policy must reevaluate even if resulting dataset or
model bytes happen to be equal. Unchanged policy with same inputs may resume.
3. Builder now reads snapshots: include deterministic snapshot input identity in
build dependency cache along with outcomes/labels. Detect additions/removals and
content changes even equal-size/restored-mtime fixtures (content digest required,
not timestamps alone). Do not materialize full decompressed snapshots/geometry.
Validate cached output content identity before reusing dataset/model steps;
do not blindly accept file existence after mutation. Keep checks offline.
4. Narrow existing CLI compatibility prerequisite: old run_round teacher command
implicitly uses straight-v1, but builder now requires explicit corridor-label.
Preserve that CURRENT legacy mode in this slice by passing --corridor-label
straight-v1 explicitly to teacher label command and corridor builder only. Bind
mode in label/build cache identity. Do NOT introduce path-v3 default or automatic
conversion. Existing path-v2/mismatched labels must fail validation, not be
silently accepted because a cached/imported label exists. Reuse builder label_mode
validation as needed; never overwrite/delete existing teacher outputs. If an
incompatible/partial immutable output prevents labeling, fail with fresh-output
instruction rather than replace it. A later task may select path-v3 with isolated
output roots; not this slice. No actual teacher execution now.
5. Preserve no-promote semantics, seed registry/collection settings, runtime
inputs, model schema/CV/significance/thresholds and immutable historical artifacts.
No sampling/training/replay hidden inside tests or implementation.

Synthetic tests (mock command runner and gate/fitting): both kinds/all4policies
propagate exactflags and directgatekwarg; default no widening; same-policy resume
skips work, changed-policy invalidates build/train/gate including imported and
already-promoted shortcuts; altered snapshot bytes same size/mtime invalidates;
changed output content invalidates reuse; malformed/mismatched corridor labels
fail closed, explicit straight-v1 validmode, no immutable output overwritten;
empty/excluded gate not promoted; dry-run writes nothing. Preserve expected
valid row values. Full end-to-end synthetic pipeline checks by root after handback.

No tests/imports/providers/delegation/build/live by worker; syntax ast.parse only.
Target6min/USD5 interactive target, not billing guarantee. Report incomplete at
bound; no silent extension. Commit owned files only. Handback <=300words SHA/API,
files, commandsNOTRUN/risks. Stop after handback/blocker. Root Sonnet source review,
all3lock focused/combined tests, Sol evidence; no user questions needed.

## Log

### 2026-10-06T19:48:50.437273-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0063-20261006 ONLY. T0062 assignments ended; new isolated branch/worktree prepared from acceptedcandidate. ACK exactalias/model before editing. No livelease/primaryintegration/realtraining. Root treats posted dispatch as pending until actualACK.

### 2026-10-06T19:49:04-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK T-0063, alias interactive-opus-t0063-20261006, model claude-opus-5-5. This is the same interactive session that completed T-0062.
- Worktree: .codex/worktrees/igvc-t0063-round-policy, branch codex/t0063-round-policy-opus, base f9594e6.
- Owned files: run_round.py, new test_round_pose_policy.py, and the test_learning_round.py fixtures only.
- Checks: static ast.parse only. No tests, imports or teacher runs.

### 2026-10-06T19:49:49.814208-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual19:49:04 ACK/exactmodel received. Sole interactive-opus-t0063-20261006 implementation active; no duplicate owner or livelease. T0062 source/evidence accepted candidate-only, source assignments ended. Await actual committed handback for review/combined validation; no primary integration until full chain accepted.

### 2026-10-06T19:53:45-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

Alias interactive-opus-t0063-20261006, model claude-opus-5-5. Commit **74b5931** on codex/t0063-round-policy-opus, parent f9594e6.

Files changed:
- tools/learning/run_round.py
- NEW tools/tests/test_round_pose_policy.py
- tools/tests/test_learning_round.py: FakeTools teacher output is now a valid `{"index":1}` straight-v1 record.

Only static `ast.parse` was run.

API and behaviour:
- **Policy:** `Round.pose_policy` comes from `--allow-predicted`/`--allow-unknown-legacy` (shared flags; measured-only default).
  - `policy_flags()` is passed to build and train for both kinds.
  - `round_gate.gate(..., pose_policy=)` is used directly.
  - `policy_identity()` = {pose_policy, policy_cache=`POLICY_CACHE`}. It goes into every build/train/gate input hash and record, failed records included, and into report.json/md.
- **`step(..., strict, extra)`:** strict steps (build/train/gate) ignore 'imported' records. Exceptions write a 'failed' record, which is never reused, then re-raise.
- **Build identity:** per run, the sha256 of outcomes and labels, plus `snapshots_identity` (sorted names and sha256 of the gzip bytes; nothing is decompressed).
- **Output reuse:** dataset, model and gate report are reused only while their bytes match the recorded sha256.
- **Gate shortcut:** skipping a model that is already promoted now also needs status done, a matching `gate_identity` (policy + model + dataset + no_promote) and an intact report.
- **Labels:**
  - `CORRIDOR_LABEL='straight-v1'` is passed to the teacher command and the corridor builder only, and is part of the label/build identity.
  - `check_labels` reuses `build_dataset.label_mode`. Malformed or other-mode existing labels raise SystemExit ("not overwritten … fresh output root") before any command, in both label and build. Imported labels are covered too.
  - The teacher's new output is re-validated.

NOT RUN:
- `python3 -m unittest tools.tests.test_round_pose_policy tools.tests.test_learning_round tools.tests.test_dataset_readers_pose_policy tools.tests.test_dataset_pose_policy tools.tests.test_learning_pipeline tools.tests.test_corridor_scorer`

Risks:
- **One-time rebuild:** the content hashes change every existing cache key. A failed train now leaves a 'failed' record (rerun next time).
- **Cost:** build hashes every snapshot's compressed bytes on each run.
- **Test fakes:** the tests mock the teacher and gate (real gate only for the empty path); their fake teacher and tools follow argv order.

Stopping.

### 2026-10-06T20:01:54.482069-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual committed handback received and cleanHEAD 74b5931103f2e40ed263e9049ff45864714722f9 bound. Implementation assignment ended; remain read-only. Root combined synthetic validation underall3locks plus Sonnet source review; no primary integration or real training/live lease.

### 2026-10-06T20:05:52.980716-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0063/review-74b5931/sonnet-static-review.md

**Verdict: no blockers. Accept candidate 74b5931 for the combined checks.** This is a source review only. I ran no tests or imports.

**Checked and sound**
- **Propagation:** `policy_flags()` goes to build and train for both kinds, so the default stays measured-only. The direct `round_gate.gate(..., pose_policy=self.pose_policy)` call and `PosePolicy` strictness are as specified. `--corridor-label straight-v1` goes only to the corridor builder and the teacher script. The Reference Lab teacher accepts that flag (`Program.cs:18`).
- **Cache identity:** policy and `POLICY_CACHE` are in every build, train and gate hash. Old records have no policy, so their hashes can't match. Strict steps ignore `imported` records. The gate shortcut now also requires status `done`, a matching `gate_identity` and an intact report hash.
- **Content digests:** snapshot identity hashes the compressed bytes with a sorted glob matching the builder's `*.json.gz`, so there is no decompression. Dataset, model and gate report are reused only while their sha256 matches the record.
- **Labels:** `check_labels` runs before the label command and again after it. It also runs at build time, which covers imported and cached labels. It uses `build_dataset.label_mode` and raises `SystemExit` without writing. The teacher itself refuses to overwrite existing output (`Program.cs:124-129`).
- **Dry-run:** only read-only checks run, and no state is written.

**Risks (non-blocking)**
1. **Weak test assertions:** the imported-record test (`test_round_pose_policy.py`) only asserts that route build reruns. It doesn't assert that `train_route` or `gate_route` rerun. Nothing tests an imported or cached `done` label record whose labels were later changed to path-v2. I think the code handles that case, but no test proves it.
2. **Fake-heavy tests:** the fake runner writes identical bytes for both kinds, and the gate is mocked outside the empty-dataset test. Argv and kwargs are well covered, but behaviour isn't.
3. **Partial label output:** a partial label directory with no `labels.jsonl` is passed to the teacher, which refuses it. The user then sees the teacher's message rather than the fresh-output instruction. A label failure also overwrites an imported `label` record with `failed`.
4. **Route build:** `check_labels` also blocks the route build, because the route build needs labels too. This is stricter than corridor-only but matches the "fail closed" intent.
5. **Train report:** reuse checks the model hash only. A deleted or edited train report would silently drop the CV section from the round report.
6. **Cost and rebuild:** the first run after this change rebuilds every cache. Each run then re-hashes every snapshot.

**For root:** run `test_round_pose_policy` and `test_learning_round` first. The `test_learning_round` end-to-end test uses the real `train_scorer` and gate with measured-pose synthetic rows.

### 2026-10-06T20:05:52.980716-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0063/validation-74b5931/sol-evidence-review.md

# T0063 combined candidate evidence review

Accept the combined regression-test evidence for `74b5931103f2e40ed263e9049ff45864714722f9`, pending source review; this is not real pipeline or integration acceptance. Worker HEAD matches and is clean. All eleven complete-chain source/test hashes match current bytes. Verified log SHA-256: `b35070da70cb68cf34207384510846a6377bc35523d9d96efbb157dff23f887c`.

The log reports 84 tests passing in 4.049 seconds with no reported skips. Parent exit 0, no timeout, elapsed 5.234 seconds. Expected argparse refusal messages are negative-test output, not failures. Matching PID 28416 lease records bracket validation, 20:02:01.793–20:02:07.225 PDT.

The six-suite command now includes previously omitted learning-round/pipeline/corridor tests. Existing tests perform genuine sklearn fitting/CV on synthetic rows (`test_learning_pipeline.py:117–125`, `test_learning_round.py:162–176`); this is neither historical dataset training nor production model generation.

New round tests verify policy forwarding, cache invalidation, label admission, failed-step accounting and dry-run behavior through a fake runner. That runner writes canned dataset/model/report bytes and never invokes the teacher (`test_round_pose_policy.py:53–75`); normal gates are mocked, while the empty path uses the real gate. Thus the actual teacher → builder CLI → trainer CLI → nonempty gate interaction is not executed end to end. Fixture snapshots also need not be usable planner captures.

Earlier failed and insufficient slice evidence remains applicable; this run does not retroactively accept those candidates. No historical captures, live runs or benefit claims were evaluated. Primary integration and production end-to-end claims remain separate gates.


### 2026-10-06T20:05:52.980716-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0063/cli-smoke-74b5931-r1/sol-evidence-review.md

# T0063 actual synthetic CLI evidence

Accept this supplement to the 84-test record as an actual synthetic route build → train → gate CLI chain. Clean worker HEAD remains `74b5931103f2e40ed263e9049ff45864714722f9`; all eleven preflight hashes match current bytes. All three command-log hashes and four recorded output hashes verify.

Each subprocess exited 0. Independently checked output contains six runs, 120 measured rows and 60 groups, with no predicted indices admitted. Builder summary records 12 excluded predicted groups; train and gate reports both retain measured-only policy and 120/60 usable counts. Actual fitting/export reports parity 0.0. `gate_decision.promote=true` is a recorded recommendation only: the smoke calls gate CLI, not an installation/promotion path.

Matching PID 11516 leases bracket execution, 20:04:43.910–20:04:46.356 PDT; smoke elapsed is 1.840 seconds. The script prevents overwrite/repeat and bounds each subprocess to 90 seconds. Original wrapper failure is preserved: WSL Git rejected the Windows worktree pointer before fixture creation or CLI commands; the original fixtures directory is absent. Revised Windows preflight binds unchanged source, rather than correcting a source defect.

Limits: generated labels deliberately follow a synthetic feature signal; no teacher executed. Minimal pose snapshots are classification fixtures, not planner replay inputs. This chain uses route rows and run-grouped training, not corridor production labels, course-grouped round orchestration, cache/promotion execution or historical datasets. The recommendation's statistics do not establish robot benefit. Primary integration remains separate; no Unity/ROS/live execution occurred.


### 2026-10-06T20:05:52.980716-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

ACCEPT candidate74b5931103f2e40ed263e9049ff45864714722f9 for complete-range source integration. Combined84synthetic tests pass; independent source/evidence reviews accepted. Additional actual synthetic route CLI build/train/gate all exit0:120measuredrows/60groups,12predictedgroups excluded, exportparity0. Gate recommendation is NOT applied. First CLI wrapper failed before fixtures/commands due WSLgit resolving Windowsworktree pointer; original wrapper.log/failure-note preserved, corrected WindowsGit preflight binds samecandidate. No realteacher/historicaltraining/live result claimed.

Full range ec0627a..74b5931 contains five authored commits across T0061/62/63; root will acquire all3locks and integrate complete range, compare eleven source hashes, preserve external dirty files and run combined primary checks. All implementation assignments ended. Risks retained: snapshot hashing cost/one-time cache invalidation; train-report-only tampering not part of model output check; existing partial teacher output fails via immutable writer; synthetic round mocks do not establish real teacher/corridor production execution. They do not bypass pose/model guards. Follow-up documentation/error-report polish is separate; no policy/model promotion or latency integration.

### 2026-10-06T20:07:20.246154-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0063/integration/sol-evidence-review.md

# T0063 integration evidence review

Accept tested offline integration at primary HEAD `b41e63b418764fbbfada02cf7487e25ba613d85a`. Git history records five cherry-picks corresponding to the complete `ec0627a..74b5931` candidate range: `e2935d6`, `5f5f6fe`, `bb93718`, `de39d04`, `b41e63b`. All eleven current primary source/test byte hashes match start/result records and accepted candidate validation. All fifteen preserved external-file hashes match before, recorded after and current bytes.

The primary log reports 84 tests passing in 3.873 seconds with no reported skips; parent exit 0, elapsed 4.766 seconds. Verified log SHA-256: `61c5ef1e589107447bb6c4392ff7c0d9747c4ce5147410fb46e812f5f9977bb0`. Matching PID 57688 lease records bracket integration/validation, 20:05:53.788–20:05:59.346 PDT.

This binds the accepted chain to primary and its combined regression evidence. Prior failed validations and the original CLI wrapper failure remain separate preserved records. The accepted actual CLI supplement covers synthetic route build/train/gate; orchestration tests still use mocks and sklearn fits use synthetic data.

No tests were rerun for this review. No real teacher relabeling, historical dataset training, applied model promotion, Unity/ROS execution, runtime autonomy or live benefit is established.


### 2026-10-06T20:07:20.246154-07:00 · gpt-6-astra → all · INTEGRATION

Complete five-commit T0061/62/63 chain integrated at b41e63b418764fbbfada02cf7487e25ba613d85a (e2935d6,5f5f6fe,bb93718,de39d04,b41e63b). Eleven primary source hashes exactly match candidate74b5931; combined84tests passed on primary, log61c5ef1e589107447bb6c4392ff7c0d9747c4ce5147410fb46e812f5f9977bb0. All15external dirty-file hashes unchanged; all3locks held through integration/tests then released; finalSol evidence accepted. Earlier failures and CLI harness failure retained. No real-data training, installed/promoted model, live lap or latency integration. Do not repeat completed tests/integration without new cause.
