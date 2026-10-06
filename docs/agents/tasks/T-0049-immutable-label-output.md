---
id: T-0049
title: Keep generated teacher label outputs immutable
status: in-progress
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0049-immutable-label-output
base: 5411b9e460c7dd085ed956e38653bb8240e2551b
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

Read README and this packet. Reuse the CLEAN worktree
C:/Users/brand/.codex/worktrees/igvc-t0045-teacher/IGVC SIM now on new branch
codex/t0049-immutable-label-output. Own only tools/reference_lab/Program.cs and
tools/tests/test_reference_label_output.py. Preserve all prior task branches/logs.

Sol found5411b9's overwrite guard checks modes but not traps validity/count
consistency. T0045 exhausted its two revision rounds; this is a simpler rescope.
Make output immutable: if ANY generated output name (summary.json, labels.jsonl,
traps.json) already exists as file OR directory, refuse before LoadRun or writes,
regardless of mode/completeness. Missing/empty target and unrelated files remain
allowed; target-as-file is refused. Error must direct a fresh --out. Do not add
force/overwrite/delete, complex consistency validation, transactions or runtime
changes. Retain path-v3 explicit output restriction. Remove misleading promises
about validating existing contents. Serial offline writer assumption remains.

Update focused tests to assert bytes remain identical for same-mode complete,
partial, corrupt/truncated outputs and named-directory collisions; preserve fresh
destination coverage and existing other-mode refusal coverage. NO TESTS OR BUILDS
NOW: T0048 holds live instances1/2. Author tests only, git diff --check and commit
owned files. Root will run combined checks after acquiring all three primary
live/instance locks. Do not run uv, install dependencies, read credentials, call
providers/agents/network, or edit another worktree. Two minutes/3USD, exact Opus
once, no provider-error retries. Return <=200words exactSHA/files, tests NOT RUN,
limits and scope. No user questions or source integration.

## Log

### 2026-10-06T03:24:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Conservative fresh-output policy supersedes same-mode overwrite. Single owner;
light source authoring only while external timing reproduction remains active.
