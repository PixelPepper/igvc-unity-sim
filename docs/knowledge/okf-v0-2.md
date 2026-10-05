---
type: Reference
title: Open Knowledge Format v0.2
description: The pinned external specification this bundle follows.
tags: [okf, specification, reference]
status: stable
resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T10:19:28Z }
sources:
  - id: spec
    resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md
    title: Open Knowledge Format specification v0.2
    author: team:GoogleCloudPlatform
  - id: guide
    resource: ../OPEN_KNOWLEDGE.md
igvc_sources:
  - path: docs/OPEN_KNOWLEDGE.md
    sha256: f93f091552929fb891489b06c93858253ff5d2e1330ac448864e2598afb7e434
---

# What we rely on

This bundle targets OKF v0.2, pinned to commit `ad30107c31c06aec8a7d5636e0d1058118604e6f`.[^spec] The parts we rely on:

- **Concepts:** markdown with YAML frontmatter and a required non-empty `type`.
- **Reserved files:** `index.md` and `log.md`.
- **Optional families:** `sources`, `generated`/`verified` trust and lifecycle (`status`, `stale_after`).
- **Lenient consumers:** broken links, unknown types and unknown keys are tolerated.

`igvc_sources` is this project's own extension; the [workflow guide](../OPEN_KNOWLEDGE.md) explains it. The
specification text is not copied into this bundle.

# Not claimed

- No concept here is `verified`.
- Trust tiers are advisory OKF signals, not scientific or safety verification.

[^spec]: Open Knowledge Format specification v0.2
