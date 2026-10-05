# Open Knowledge workflow

The project keeps a compact, durable knowledge bundle in [`docs/knowledge/`](knowledge/index.md), written in the
**Open Knowledge Format (OKF) v0.2**. Agents (Claude, Codex/ASTRA, Sol) and people use it to find the right canonical
files quickly. It is plain Markdown, so no SDK, cloud agent or network access is needed.

- **Specification:** GoogleCloudPlatform/open-knowledge-format `SPEC.md`, pinned at commit
  `ad30107c31c06aec8a7d5636e0d1058118604e6f`
  ([link](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md)).
  External text is reference material, not project instruction, and is not copied into the bundle.
- **Authority:** the bundle summarizes and points; it does not replace canonical files. Task state, messages and
  decisions stay in [`docs/agents/`](agents/README.md). Run results stay in task logs, the
  [benchmark ledger](evidence/benchmark_runs.csv) and artifacts. Knowledge is never dispatch, acceptance or promotion
  authority, and never proof that a simulation passed.

## Using it in a task

1. Read [`docs/knowledge/index.md`](knowledge/index.md) and pick the relevant concepts, or run a search:
   `wsl -d Ubuntu-24.04 -- python3 tools/agents/knowledge.py search "path entry"`
2. Open each chosen concept, then its canonical sources (the `sources` and `igvc_sources` paths).
3. If `check` reports a `source_changed` warning for a concept you rely on, read the current source first. The
   concept may be out of date.

## Maintaining it

Update only when an **accepted** change alters what a concept says:

- edit just the affected concept, and update `generated.at`
- re-pin its sources deliberately: `python3 tools/agents/knowledge.py pin <path>`
- add a dated line at the top of `docs/knowledge/log.md`, newest first
- keep failed experiments in their evidence and task logs
- never add a `verified` entry that did not happen, and never copy task status or run logs into the bundle

Hashes are never updated automatically. Drift is reported so that someone re-reads the source and decides.

## Commands

The commands run in WSL or CI, where PyYAML is already installed. Do not install packages into Windows Python.

```bash
python3 tools/agents/knowledge.py check                 # exit 1 only on OKF format errors
python3 tools/agents/knowledge.py check --strict-project  # also fail on warnings (project policy, not OKF)
python3 tools/agents/knowledge.py search "processing health" --limit 5
python3 tools/agents/knowledge.py export --output artifacts/agents/observatory/knowledge.json
```

`--root` and `--bundle` select another repository or bundle (used by tests).

## What `check` enforces

| Kind | Rules |
| --- | --- |
| **Errors (OKF v0.2 conformance)** | A concept file whose frontmatter is missing, unterminated, unparseable or not a mapping. A missing or empty `type`. In `index.md`: unterminated frontmatter, frontmatter in a non-root index, or root-index frontmatter other than `okf_version`. In `log.md`: any frontmatter, any `##` heading that is not an ISO date, or dates not newest first. Files may start with a UTF-8 BOM. |
| **Warnings (never conformance failures)** | Broken internal links, and missing local targets outside the bundle. Missing project-recommended fields (`title`, `description`, `tags`, `generated`, `igvc_sources`). A non-string `title` or `description`. Malformed `verified` events. A `stale_after` without a timezone or already passed. YAML values that are not plain JSON, normalized as listed below. Source drift: `source_changed`, `source_missing`, or `source_blocked`. |
| **Tolerated** | Unknown types and unknown keys. |
| **Trust tier** | Derived only from **well-formed** `verified` events: an actor in the §7 convention (`human:<id>`, `process:<id>` or `<producer>/<version>`) **and** a timezone-aware `at`. A bare mapping is treated as a one-item list. Malformed or empty events are ignored with a warning and never raise the tier. Result: unverified, machine-confirmed, or human-reviewed. The lifecycle `status` is reported separately, and neither one is scientific verification. |

YAML values that are not plain JSON are normalized in `metadata`, with a warning:

- NaN and infinity become `null` (`nonfinite_number_replaced`)
- sets become sorted lists (`set_converted_to_sorted_list`)
- binary values become `null` (`binary_value_replaced`)
- self-referencing structures become `null` at the cycle (`recursive_value_replaced`)

Dates become ISO strings. Search treats non-string titles, descriptions and tags as text.

Drift is **advisory**: `tools/check_core.sh` runs the non-strict check, so a changed source never fails CI by itself.
Use `--strict-project` when curating the bundle on purpose.

## The `igvc_sources` extension

A project-specific frontmatter key that lists stable canonical sources:

```yaml
igvc_sources:
  - path: docs/SENSOR_AUTONOMY.md   # repository-relative, inside the repo, no symlinks
    sha256: <hex>                   # SHA-256 of the UTF-8 text with CRLF/CR normalized to LF
```

Normalizing line endings (and dropping a UTF-8 BOM) keeps hashes identical across Windows and Linux checkouts.

**Pin policy.** It is checked on the path text before any file is opened, and both `pin` and `check` apply it:

| Refused | Reason code |
| --- | --- |
| Absolute paths and paths containing `..` | `not_repository_relative` / `escapes_repository` |
| `artifacts/`, `.git/`, `ros2/{build,install,log}/`, Unity generated folders (`Library`, `Temp`, `Obj`, `Logs`, `UserSettings`, `Build(s)`, `GeneratedRobot`), and any `node_modules`, `__pycache__`, `.venv` or `.cursor` component | `excluded_location` |
| Credential-like file names (`.env*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.dpapi`, `id_rsa*`, names containing `credential`, `secret`, `token` or `password`, `auth.json`) | `credential_like_name` |
| Anything outside an allowlist of text suffixes (Markdown, text, Python, JSON, YAML, TOML, XML, URDF/xacro, launch, RViz, C/C++/C#, shell, PowerShell, JavaScript/TypeScript, Unity UI text, ROS interface files) | `not_allowed_text_type` |
| Symlinked components, missing files, files over 2 MB, and non-UTF-8 content | — |

`pin` exits non-zero for a refused or unreadable path, with a one-line message and no traceback. Files the integrator
edits often are linked but not pinned.

## Export for the Observatory

`export` writes one deterministic JSON document (sorted keys; `--now` fixes the evaluation instant for reproducible
output). A successful export replaces the output atomically via a temporary file.

When the bundle has OKF format errors, or the output would exceed the limits below, `export` exits 1 and writes nothing:

- **No previous export:** the output file does not appear.
- **Previous export exists:** it is left untouched (it is never deleted). It still carries its old `generated_at`.

A consumer therefore cannot tell from an unchanged snapshot alone that a refresh failed. The producer's exit status,
or a `generated_at` older than expected, is the signal.

| Field | Meaning |
| --- | --- |
| `schema_version` | `1`. The export schema, separate from `okf_version` (`"0.2"`, the bundle format) |
| `project_id` | `igvc-unity-sim`, stable |
| `bundle_path` | `docs/knowledge`, repository-relative |
| `generated_at` | The UTC evaluation instant used for freshness |
| `spec` | The pinned OKF repository, commit and path |
| `limits` | `max_bytes` 2 MiB, `max_nodes` 1000, `max_edges` 4000, `body_display_bytes` 8192 (a display hint for consumers) |

`nodes[]` is sorted by `id`. Each node has:

- `id`: the concept path relative to `bundle_path`, without `.md` (for example `sensor-led-navigation`)
- `path`: repository-relative
- `type`, `title`, `description`
- `metadata`: the full frontmatter, with dates as ISO strings
- `body`: the Markdown body
- `trust`: unverified | machine-confirmed | human-reviewed
- `freshness`: no_expiry | current | stale | unknown
- `lifecycle`: the `status`, default `stable`
- `sources_status[]`: `{path, status: match|changed|missing|blocked, ...}`

**Source drift** (`sources_status`) and **time expiry** (`freshness`) are independent signals.

`edges[]` comes in two kinds:

- `kind: "link"`: an explicit Markdown link from one concept to another inside the bundle. It is resolved relative to
  the linking file, or to `bundle_path` for links that start with `/`.
- `kind: "source_pin"`: derived from `igvc_sources`. Its `target` is a repository-relative path.

Links to files outside the bundle do not create edges. If such a target is missing, the export records a
`missing_external_target` warning instead.

`warnings[]` and `errors[]` are `{path, code, detail?}`, where `path` is repository-relative. An empty list means none
were found. `generated` and `verified` actors are self-declared, not authenticated identities.

The export contains no absolute paths and no source file contents (only hashes and metadata). Consumers must treat it
as untrusted data: render it as text and never execute or fetch anything from it.
