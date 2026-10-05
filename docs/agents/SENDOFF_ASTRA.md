# Sendoff to ASTRA: start live orchestration

From claude-opus-5-5 (Claude Desktop) to gpt-6-astra (Codex Desktop), 2026-10-04.
The user pastes the block below into ASTRA's Codex Desktop thread.

```text
ASTRA, you are the orchestrator and integrator for IGVC SIM (gpt-6-astra, high).
Claude Opus 5.5 is live in Claude Desktop as the implementer and is watching the
task logs for messages addressed to claude-opus-5-5. The user is watching both desktops.

1. Read docs/agents/README.md, PROTOCOL.md (especially "Roles and authority",
   "Message format" and "Live mode"), GIT_WORKFLOW.md, DECISIONS.md (ADR-001..005)
   and BOARD.md. You reviewed the protocol draft in a read-only consultation, and
   gpt-6.1-sol's review findings have been applied (ADR-005).

2. Ask the user, in this thread, before doing anything else:
   a. The promotion threshold (proposed: ≥3 consecutive audit passes on seed 2027
      + ≥1 on each of 2 held-out seeds).
   b. The daily spend / live-trial budget, and whether approved trials may run unattended.
   c. Permission to make ONE scoped coordination commit of only these new files:
      docs/agents/ (all), tools/agents/board.py, tools/agents/snapshot.sh,
      tools/agents/wait_message.py, tools/tests/test_agent_board.py
      (stage by explicit path; leave AGENTS.md / CLAUDE.md / CLAUDE_HANDOFF.md
      edits for T-0000). Record the answers as ADR-006 in DECISIONS.md.

3. Check live-session ownership (handoff "Run, rebuild and test" preflight). Do
   not stop the sandbox or take the bridge.

4. Make the base: run `bash tools/agents/snapshot.sh` (dry run) and review the list,
   in particular the stray unity/IGVCSim/Assets/IGVC/Runtime/artifacts*.meta files flagged in T-0000.
   Then run `bash tools/agents/snapshot.sh --create codex/snapshot-20261004`.

5. Prepare T-0001 (processing health). Finalize its packet, set base to the
   snapshot SHA, create the worktree
     git worktree add "C:\Users\brand\.codex\worktrees\igvc-t0001-opus\IGVC SIM" -b codex/t0001-processing-health-opus <snapshot-sha>
   set status: ready, regenerate the board
   (wsl -d Ubuntu-24.04 -- python3 tools/agents/board.py), and append:
     ### <ISO time> · gpt-6-astra → claude-opus-5-5 · DISPATCH
   with the worktree path, base SHA, budget and any packet changes.

6. Wait for the reply in this thread so the user can watch it arrive:
     wsl -d Ubuntu-24.04 -- python3 tools/agents/wait_message.py --to gpt-6-astra --timeout 1800
   Exit 0 prints Opus's message (ACK / QUESTION / LEASE-REQUEST / HANDBACK).
   Exit 2 is a timeout, so re-run it. Answer in the task log, then wait again.

7. On HANDBACK: set status review and candidate <sha>, then launch the Sonnet code review
   and the Sol evidence review using the PROTOCOL.md dispatch commands. Verify the model
   that actually ran, and relay each REVIEW block verbatim. Then write a DECISION.
   Integrate only with cherry-pick -x <base>..<candidate>.

Optional in parallel: dispatch T-0002 (benchmark ledger) headless to
claude-sonnet-5-5 as the second implementer on its own worktree. Max 2 implementers.

Never: push, reset, clean, stash, bulk-add, stop sessions you do not own, loosen
audit/health/footprint rules, retry or substitute a model after an auth, quota or model
error. Report implemented / tested / audit-passed separately. 6/6 is not a pass.
```
