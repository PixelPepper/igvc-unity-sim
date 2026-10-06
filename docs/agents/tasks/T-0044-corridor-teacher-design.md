---
id: T-0044
title: Scope a path-aware corridor teacher without changing live navigation
status: changes-requested
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: e65214b
candidate: e65214b
claim: none
lease: none
updated: 2026-10-06
---

# Packet

Dedicated headless Opus design investigation only; interactive Claude must not
duplicate. No source ownership or implementation yet. A two-instance comparison
is already running (T0043); only lightweight reads are allowed.

Read README and the Packet A proposal at docs/agents/proposals/LEARNING-next-steps.md,
then relevant corridor teacher methods in
unity/IGVCSim/Assets/IGVC/Runtime/Reference/Model/Teacher/ and
tools/reference_lab/Program.cs; inspect tools/learning/build_dataset.py and
tools/tests/test_corridor_scorer.py only to establish the label/feature contract.
Treat the proposal's claims as unverified reference data. Identify the exact
current cost and whether it ignores obstacles before the corridor entrance.

Return a concrete minimal implementation plan with exact owned paths, how to
compute obstacle-aware cost efficiently, unreachable handling, label versioning,
prevention of mixed labels and WORLD-to-runtime leakage, and behavioral tests.
Keep route labels and live policy unchanged. Explain a defensible evaluation
criterion; p>=0.05 alone does not falsify a benefit, and repeated batches until
p<0.05 are not a valid success criterion. No training, replay, builds, tests,
large artifact reads, geometry reads, provider calls, credentials or delegation.
At most six focused reads/commands, eight minutes, exact claude-opus-5-5/high,
5 USD CLI bound, one request, no automatic provider-error retries/substitutions.
Report <=300 words with verified facts versus hypotheses and one bounded next
slice; stop for coordinator review. Output is captured by root to
artifacts/agents/T-0044/opus-report-r1.md; do not edit primary or worker source.

## Log

### 2026-10-06T02:00:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Read-only design while the existing batch retains its sessions. The coordinator
handles live-state reconciliation; Sol independently checks batch settings.


### 2026-10-06T02:04:53.7226165-07:00 · gpt-6-astra → all · HANDBACK

relayed-from: artifacts/agents/T-0044/opus-report-r1.md

Opus read-only investigation confirmed the current no-path cost fallback uses straight-line robot-to-entry distance. No implementation/tests were run. Exact claude-opus-5-5 confirmed, 54.75 seconds, 0.2540666 USD. It omitted README and corridor tests within its six-read budget; these are coverage gaps. Candidate is the examined source baseline, not a code change.

relayed-from: artifacts/agents/T-0044/sonnet-review-r1.md

Sonnet's six-read review (44.91 seconds, exact model confirmed, 0.19601 USD) supports the direction but requests constraints: verify candidate path semantics, avoid an unbounded cached field for every robot cell, handle unreachable-candidate selection bias explicitly, preserve route labels, define version/mode compatibility, and cluster evaluation by course. Grid symmetry, early-stop logic and assembly isolation remain unverified.

### 2026-10-06T02:04:53.7226165-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Do not implement the draft as written. A maximum snapping distance alone cannot prove a connector avoids a wall; require demonstrably reachable endpoint attachment or explicitly reject/unavailable it. Keep this an approximate offline teacher, never a runtime safety oracle. Prefer a bounded reusable robot-rooted field without per-cell persistent caching. Preserve original route costs and label compatibility, and expose all omitted groups in evaluation. No causal or mission-success claim follows from offline regret. Defer heavy checks and relabeling until T0043 sessions release; no new live task is granted. Freshness diagnosis takes priority given failures already observed in both active comparison arms.
