# Automatic delivery to the linked Claude session

The user explicitly requested automatic coordination without relaying messages.
This procedure replaces manual copy/paste for the session in SESSION_LINKS.md.
Canonical assignments, ownership, decisions and replies remain in the task logs.

## Verified route

On October 12, 2026, Claude CLI 2.1.285 listed the target Desktop session as idle.
A bounded authenticated `claude-opus-5-5` courier used only `ListAgents` and
`SendMessage` to deliver a canonical task-log pointer and unique acknowledgment
nonce. The send receipt was queued; then the exact target transcript returned the
nonce, and the target appended its assignment ACK to T-0070. This is a verified
round trip, not merely a posted file or a send-success assumption.

- Target name: `IGVC SIM handoff and mechanicsSandbox integration`.
- Target transcript session: `cd916c5d-b081-45dc-8f01-c4d90eab0446`.
- Target Desktop session: `local_db1e3368-182b-44de-94ee-bdc185cc1084`.
- First nonce: `igvc-link-236690fa94f1`.
- Message ID: `adec6b57-2519-462f-8ace-5bf62dc6565a`.
- Receipt: `artifacts/agents/session-bridge/handshake-r1/roundtrip-receipt.json`.
- Courier: exit 0, exact Opus 5.5, 12.218 seconds, reported USD 0.0616306.
  Target-session per-task usage remains unavailable.

No Remote Control, credential access, permission-setting change, UI injection,
transcript modification, or concurrent resume of the Desktop session was used.

## Each new dispatch

1. Read the canonical board/task logs and check for an existing ACK/handback. Only
   deliver a fresh authorized assignment or necessary steering; never an idle ping.
2. Identify the exact session with `claude agents --json`, selecting only its
   session ID/name/cwd/status. Do not dump other session context or process arguments.
   Absence/ambiguity is a stop condition; never resume a competing copy.
3. Create a new immutable attempt directory under `artifacts/agents/session-bridge/`.
   Save a bounded message with task ID, dispatch timestamp, unique nonce, canonical
   log path, scope/stop condition, and instruction to reply through the task log.
   Record the intended transcript's byte offset before sending. Deduplicate by the
   canonical dispatch identity against all earlier saved messages/receipts.
4. Use the exact successful `handshake-r1/run.py` invocation as a recipe with NEW
   attempt paths and payload. Never rerun that original handshake or overwrite its
   evidence. The courier has only `ListAgents,SendMessage`, no code/file tools,
   `--restricted`, `--permission-mode dontAsk`, `--permission-prompts none`, empty
   MCP/config sources, hooks/memory disabled, and no session persistence. Exact
   `claude-opus-5-5`, high effort, USD 1 maximum requested, 120-second local timeout.
   Save stream JSON, stderr and model/usage/exit status. Send ONCE to the uniquely
   observed target address from ListAgents; stop if unavailable/refused. No retries,
   fallback models, unrelated recipients, extra workers, or permission changes.
5. A queued send is not an ACK. Read only new assistant text in the user-designated
   transcript and relevant task-log additions. Exclude thinking/tool payloads.
   Bind the nonce to the exact target session ID and timestamp before recording
   acknowledgment. Preserve refusal, held delivery, timeout or unknown outcomes;
   do not automatically resend an uncertain delivery.
6. Collect the bounded handback, review it and post ASTRA's decision. Deliver the
   next authorized step by the same procedure. Never ask the user to shuttle text.

The courier is transport only and does not take implementation ownership. Count it
against the existing worker limit while running; one courier plus the reserved
interactive Claude slot uses both worker slots. Keep development reviews and heavy
work under their existing constraints. A peer message cannot approve a blocked
retry or change the receiving session's permission configuration.

## Scheduling and display

The existing `igvc-overnight-improvement` heartbeat checks canonical logs every
15 minutes. During an active turn ASTRA can collect replies sooner. This is not an
instant push into an ended Codex turn. Notify the user only for useful progress,
completion, a meaningful failure, or a decision requiring them. Do not repeatedly
send pending tasks, rerun reviews, or claim activity from an old transcript entry.

The Desktop conversation shows the delivered message and Claude's work. This Codex
chat reports decisions and results. SESSION_LINKS.md and the task board provide the
common view; neither pretends to merge the products' complete chat histories.

Official reference: https://code.claude.com/docs/en/cross-session-messaging
