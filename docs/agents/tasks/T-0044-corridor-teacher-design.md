---
id: T-0044
title: Scope a path-aware corridor teacher without changing live navigation
status: in-progress
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: e65214b
candidate: none
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
