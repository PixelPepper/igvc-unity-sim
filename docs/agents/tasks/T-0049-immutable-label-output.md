---
id: T-0049
title: Keep generated teacher label outputs immutable
status: integrated
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0049-immutable-label-output
base: 5411b9e460c7dd085ed956e38653bb8240e2551b
candidate: 1a81e8a459a7f169a76cf755a65c59ba0282564f
claim: tested
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


### 2026-10-06T03:28:00-07:00 · gpt-6-astra → reviewers · HANDBACK

Opus committed 5a57d91 (two owned files). Generated output names are now immutable,
including directory collisions and same-mode complete/partial/corrupt outputs.
Tests authored, NOT RUN while T0048 remains live. Provider completed once in
55.12 seconds, actual USD0.2660788. Final focused review and locked validation
remain required; no source integration or runtime change yet.

### 2026-10-06T03:33:00-07:00 · gpt-6-astra → claude-opus-5-5 · REVISION

Root held all three live locks after players/audits finished. Final13 output
checks had11 passes/two failures: notes.txt and target-file fixture write_text
uses Windows CRLF but assertions hardcode LF bytes. Preserve failed log
artifacts/agents/T-0049/output-tests-final.log and validation-final.json.
Fix only those fixture writes to exact bytes (or snapshot actual before bytes),
keeping assertions strict and runtime untouched. No tests/builds; root reruns
under locks. Commit one test-only revision. Do not overwrite prior handbacks.
PowerShell5 initially aborted on native stderr; launcher-aborted log is distinct
and not an application failure. Subsequent PowerShell7 run produced above result.

### 2026-10-06T03:35:00-07:00 · gpt-6-astra → reviewers · HANDBACK

Final candidate1a81e8a459a7f169a76cf755a65c59ba0282564f changes only two fixture
writes to exact bytes; assertions/runtime unchanged. Sonnet approved the two-line
diff (6.00s,USD0.013196). Opus revision actualUSD0.1051454/21.0s (ignore its rounded
self-estimate). Root held all three live locks03:33:20–03:33:58:
13 output tests PASS,91 C# checks PASS,15 dataset tests PASS at e2b7ada.
Manifest artifacts/agents/T-0049/validation-final.json binds each source/log/hash.
Real-run C# fixture unavailable/skipped; positive output cases only pass the guard
before an invalid placeholder fails loading. No successful real-run relabel,
Unity Editor compilation, training or live navigation benefit is claimed.
Serial writer assumption and dangling-symlink limitation remain explicit.
Previous CRLF failures and the PowerShell5 launcher abort remain archived.
Final Sol evidence review requested before integration of both complete ranges.

### 2026-10-06T03:38:10.6221039-07:00 · gpt-6-astra → all · DECISION

Accept only the combined complete teacher range e65214b..1a81e8a plus dataset
range2572e87..e2b7ada for offline integration. Sonnet code reviews and final Sol
evidence review have no blockers. Final locked tests13/91/15 pass; all log hashes
independently verified. T0045's older candidate is NOT acceptable alone: T0049
and T0047 are mandatory dependencies. Archive pointer for the preserved failed
output log corrected without changing bytes/hash. No runtime/teacher-training
promotion. Integration and check_core.sh wait for active T0050 ownership to end.
Serial output writer and dangling-symlink limitations are documented; no real-run
relabel or Unity Editor compilation claimed. Save other authors' working files.

### 2026-10-06T07:00:52.4162753-07:00 · gpt-6-astra → all · DECISION

Integrated both complete reviewed ranges with cherry-pick -x, ending74967bf.
All3locks held06:44:43–06:57:18; source checks began only after merged auditreport.
13 Windows outputtests,112 C#checks (including primary realcourse/run fixtures),
core604tests with13skipped plus85and4tests passed. The13skips are the Windows-tested
output suite. Knowledge8/0/0. Sol independently verified all3log hashes and exact
source matches to reviewed worker files. No unrelated source entered commits.
See artifacts/agents/T-0049/{integration-validation.json,sol-integrated-review.md}.
No Unity Editor validation, production relabel/retraining or live benefit claimed.
