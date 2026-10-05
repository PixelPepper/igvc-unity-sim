---
type: Process
title: Agent handoffs
description: Where tasks, messages and decisions live, and who may change what.
tags: [agents, protocol, git, review, coordination]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T10:19:28Z }
sources:
  - id: protocol
    resource: ../agents/PROTOCOL.md
  - id: git
    resource: ../agents/GIT_WORKFLOW.md
  - id: board
    resource: ../../tools/agents/board.py
# PROTOCOL.md is linked but not pinned: the integrator edits it frequently.
igvc_sources:
  - path: docs/agents/GIT_WORKFLOW.md
    sha256: 82d6dae3e8f4d96169a4d57d9653dec66d71c45061f0249db303d7ed955205c6
  - path: tools/agents/board.py
    sha256: 7cab38234f6900e50bb39c9f68d2967aecdc554cdb55f2265cbed7fb64665248
---

# Canonical locations

These files are authoritative. This concept only points to them and does not copy their content.

- **Task state and messages:** [the board](../agents/BOARD.md) and the task files in `docs/agents/tasks/`.
  - Headers are edited by ASTRA only.
  - Logs are append-only.[^protocol]
- **Decisions:** [DECISIONS.md](../agents/DECISIONS.md).
- **Branches, worktrees and integration:** [GIT_WORKFLOW.md](../agents/GIT_WORKFLOW.md).[^git]

# Rules worth remembering

- Work only on an explicitly dispatched task.
- One owner per file.
- Reviews bind to an immutable candidate SHA.
- Integration uses `cherry-pick -x <base>..<candidate>`, never a merge of a snapshot-based branch.
- No automatic retries or model substitution.

[^protocol]: Agent protocol
[^git]: Git workflow
