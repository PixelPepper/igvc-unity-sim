# Bounded Cursor review

## Claude implementation iterations

The user now authorizes scoped edits, local Git commits and worker-controlled
simulation trials. See [iteration workflow](../../docs/AGENT_ITERATION.md).
`claude-iteration.mjs <opus|sonnet>` uses a prepared per-role config under
`artifacts/iterations/2026-10-01`. The managed worktrees start from the same snapshot
commit; no primary index changes, pushes or force operations are performed.

`iteration-mcp.mjs` exposes only assigned reads/writes, focused tests, scoped
commits and one bounded simulation. A commit requires successful tests after the
last write; a trial requires a clean committed candidate. `iteration-live.ps1`
serializes the shared simulator with a file lease and refuses existing players or
an occupied bridge port. Each trial builds its own `IGVC_ROS_WORKSPACE`, checks
installed perception hashes, then runs a hidden existing player, fixed navigation
profile, sensor-led mission and independent audit. It never opens Unity Editor;
rendering stays enabled for RGB/depth. Failed shutdown retains the lease until
the coordinator verifies cleanup. The trial can fail even when the launcher finishes.

Offline tests and edits run concurrently; only live trials are serialized. CLI
attempts use high effort, exact model IDs, a requested $10 maximum API-equivalent
budget and 35-minute wall timeout. No automatic model/auth/quota retries. Agent
timeout does not kill an owned simulation; its bounded trial completes and shuts
down under the separate lease-holder process. Check `live.json` before cleanup.

## Independent project handoff

**Provider correction:** Opus/Sonnet reviews run through the authenticated
**Claude CLI**, not Cursor. Cursor is reserved for separate tasks; the user
permits Grok 4.7, subject to exact catalog verification. The older Grok 4.6 runner
below has not been converted into a Grok 4.7 implementation.

```powershell
node tools/agents/claude-handoff.mjs opus
node tools/agents/claude-handoff.mjs sonnet
```

These commands require Claude CLI already signed in. Each uses the exact 5.5
model with high effort, no fallback, no built-in tools, and a private stdio MCP
server exposing only frozen-text reads, named offline checks and one experiment
request. Ambient settings and hooks are disabled. No credential is read by the
launcher. Results go to `artifacts/reviews/2026-09-30/claude-<role>`; an existing
directory is rejected. The 480-second wall limit and CLI `--max-budget-usd 5`
bound each attempt; reported API-equivalent cost is not necessarily a subscription
invoice. No automatic retries occur. Actual initialized model IDs are checked.

The [2026-09-30 handoff](../../docs/reviews/2026-09-30/HANDOFF.md) defines a common
frozen baseline, three separate assignments, test boundaries and a report format.
See its [status](../../docs/reviews/2026-09-30/STATUS.md) before dispatching: catalog
availability does not establish available inference quota.

`runner.mjs catalog` lists account model IDs and modes without creating an agent.
`prepare_handoff.py` freezes explicit source/evidence paths and hashes them in a
manifest; it refuses to overwrite an existing baseline. `offline_check.py` verifies
those hashes before running a named test group or recorded-grid replay in WSL.

The superseded `review-handoff.mjs` is the original Cursor runner for Opus 5.5 and Sonnet 5.5.
It exposes only bounded frozen-text reads, named offline checks and an experiment
request queue. It enables no arbitrary shell, writes, networking or delegation.
GPT-6.1 Sol runs through the built-in worker API under the same review boundaries.
Do not run more than two reviewers concurrently or give them control of live ROS
and Unity sessions. Root retains session ownership and final verification.

Each Cursor role gets one attempt, high effort with Fast off, a 420-second timer
and a 100,000-token cancellation threshold. These are soft cancellation limits,
not guaranteed billing caps. Actual usage, reports and checks are saved beneath
`artifacts/reviews/2026-09-30/<role>`. Authentication, quota or model-access errors
stop that role without retries or model substitution. Existing output directories
are intentionally not overwritten. A resumed review needs an explicitly prepared
new attempt directory after access is restored; do not delete failure evidence.

## Existing Grok review runner

Default mode is now **medium effort, Fast off**, following the user's preference for faster development with moderate cost. The PowerShell wrapper accepts `-Effort low|medium|high|xhigh` and `-Fast`; direct Node invocation uses `IGVC_CURSOR_EFFORT` and `IGVC_CURSOR_FAST=true`. Requested parameters must exist in the account catalog; no silent effort fallback occurs. Historical low-effort notes below describe the initial integration.

Pinned official `@cursor/sdk` 1.0.31, Node >=22.13. Install with `npm ci --prefix tools/agents`.

From repository root:

```powershell
node tools/agents/runner.mjs dry-run --task tools/agents/review-motion.task.json
node --test tools/agents/offline.test.mjs
node tools/agents/runner.mjs doctor
node tools/agents/runner.mjs review --task tools/agents/review-motion.task.json
```

Authenticated modes use `CURSOR_API_KEY` supplied by `tools/cursor-agent.ps1`, which also supports an encrypted per-user credential outside this repository. To replace that credential, run `./tools/set-cursor-key.ps1` interactively. Never put credentials in task JSON. Doctor only fetches the account model catalog; it does not create an agent. Review requires exactly one catalog entry matching non-fast Grok 4.6; no Auto or alternate-model fallback. It selects low reasoning effort when available and fast=false when supported. The catalog has no prices, so the runner cannot verify the cheapest dollar price.

Each review copies only explicit relative text-file paths into `artifacts/agents/<uuid>/input`, includes numbered text in a prompt capped at 24,000 characters, and performs one send. Prompt requests at most 500 output words; this is not a model output-token cap. Dry-run validates without importing the SDK, authenticating, or creating artifacts.

All agent tools are disabled through `tools: []`, including shell, writes, network tools and subagents. Ambient settings are disabled with `settingSources: []`. The pinned SDK d.ts has no public hook API even though newer online documentation mentions hooks; the tool deny-all fallback is intentional. Hosted inference still sends the approved input to Cursor. SDK infrastructure can read its own runtime/config; this is not an OS sandbox. No full repository scan is requested.

The timer requests cancellation at 180 seconds, and cumulative usage events request cancellation at 50,000 tokens. Usage can arrive only after a model turn, so neither is a hard billing/token cap; cancellation may take time and usage may be absent. Automatic agent retries are disabled. Review writes `summary.md`, `usage.json` and the SDK's local store below the job directory. SDK event/error bodies are not printed by the runner. Inspect artifacts before treating model findings as verified.

Reference: https://prod.cursor.com/docs/sdk/typescript and installed `node_modules/@cursor/sdk/dist/esm/{options,run,agent}.d.ts`.
