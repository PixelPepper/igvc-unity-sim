---
id: T-0047
title: Reject mixed corridor label modes before duplicate indices can hide them
status: accepted
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0047-label-admission
base: 2572e872d1c888a5b3292c8231fa78d4503f5f80
candidate: e2b7ada4824d7ce781f1c4204d3aabb76e81647d
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

Read README and this packet. Work only in
C:/Users/brand/.codex/worktrees/igvc-t0047-label-admission/IGVC SIM.
Own ONLY tools/learning/build_dataset.py and tools/tests/test_corridor_scorer.py.
T0045's other Opus owns only Program.cs/output guard tests in a different worktree;
the ownership is disjoint. No other worker may change these two files now.

Sol found that label_mode checks label modes after _read_jsonl deduplicates indices.
Thus conflicting modes sharing an index can disappear. Fix corridor admission to
validate every raw label record before deduplication; reject duplicate indices
rather than silently choosing a row. Reject contradictory corridor_label versus
legacy corridor_cost metadata when both are supplied. Keep absent metadata as
legacy straight-v1, reject unknown/path-v2 modes, preserve explicit selection,
whole-group unavailable accounting and observed-only feature semantics. Preserve
legacy route dataset behavior; do not globally change unrelated outcome parsing.

Add focused tests: mixed modes with the SAME index, same-mode duplicate index,
contradictory aliases, valid unique legacy and path-v3 records. Do not weaken the
existing distinct-index tests. Run the corridor suite using bundled Python
C:/Users/brand/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe.
Save the log and source identity under your worktree artifacts/agents/T-0047/.
No provider/subagents, live/ROS/Unity, replay, training, WORLD/course reads,
dependency changes, model/default changes, other-worktree edits or publishing.
Four minutes, 4 USD bound, one exact Opus5.5 high call, no provider-error retries.
Commit only owned files and return <=250words with exact SHA, tests and limitations.
Root will integrate both disjoint slices only after independent reviews.

## Log

### 2026-10-06T03:15:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

New narrowly scoped dataset admission task from immutable2572e87, disjoint from
the running T0045 output-guard revision. No live lease or behavior change.

### 2026-10-06T03:17:00-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

905f8d passes14 focused tests but handback admits malformed JSON is skipped and
non-integer/missing indices are accepted during mode validation. These undermine
raw-record fail-closed admission. One bounded revision, same two files/worktree,
three minutes / 2 USD, exact Opus once, no retries. In corridor label_mode reject
malformed nonempty JSON lines, non-object records, missing/noninteger (including
boolean) indices with a clear line-number error; preserve blank-line tolerance
and valid legacy/indexed records. Do not change global _read_jsonl or route mode.
Add behavior tests and rerun only corridor suite, preserve original logs, commit.
No providers/delegation/live/ROS/Unity/replay/training/network/dependency changes.
Handback exact SHA, tests and any remaining admission limitations <=200words.

### 2026-10-06T03:22:00-07:00 · gpt-6-astra → all · HANDBACK

Exact Opus committed905f8d thene2b7ada on the isolated branch, two owned files.
Initial14test suite passed; root requested fail-closed malformed raw records;
revision15tests passed. Costs0.2841742/0.199116 USD;58.83/45.38s. Original logs and
source manifests preserved. Final Sonnet code and Sol evidence reviews pending.
No live or training claims. Source integration/combined checks wait for T0048.

### 2026-10-06T03:25:00-07:00 · gpt-6-astra → all · DECISION

Accept e2b7ada for later integration: Sonnet20.94s/0.0660464USD exact model finds
no blockers; Sol confirms15 tests and source blob identities (dataset0229ce62e4df17b514fd9de10964710a7836d07f, testsc08eced1fc29b05501694e6c60f232aac446f3a2).
Log SHA cfba565901ab43da00de9ece84a36adc533d324e03442d2f1cc608c9b2298333.
Serial immutable input assumption remains; no runtime/training claim. Accepted
is NOT integrated: wait for T0048 leases and combined source validation.
