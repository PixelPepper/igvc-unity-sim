---
type: Playbook
title: Knowledge maintenance
description: When and how to update this bundle without creating a second source of truth.
tags: [knowledge, okf, maintenance, workflow]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T10:19:28Z }
sources:
  - id: guide
    resource: ../OPEN_KNOWLEDGE.md
    title: Open Knowledge workflow guide
igvc_sources:
  - path: docs/OPEN_KNOWLEDGE.md
    sha256: f93f091552929fb891489b06c93858253ff5d2e1330ac448864e2598afb7e434
---

# Steps

1. **Before a task:** read [the index](index.md), pick the relevant concepts and open their canonical sources.
2. **After an accepted change** that alters a concept's meaning:
   - Edit only the affected concept.
   - Re-pin its `igvc_sources` deliberately with `knowledge.py pin`.
   - Add a dated line at the top of [the log](log.md).
3. **Keep the record honest:**
   - Keep failed experiments in their evidence and task logs. Do not rewrite history here.
   - Never add a `verified` entry that did not happen.
4. **Validate:** run `knowledge.py check`, then `export` for the Observatory.[^guide]

# Boundaries

- Knowledge is context, never dispatch, acceptance or promotion authority.
- A source-drift warning means "re-read and decide". It is not an automatic hash update.

[^guide]: Open Knowledge workflow guide
