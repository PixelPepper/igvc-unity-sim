# Bounded Cursor review

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
