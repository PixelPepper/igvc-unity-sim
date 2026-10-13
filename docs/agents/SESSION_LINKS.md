# IGVC collaboration sessions

This local companion identifies the two conversations requested by the user on
October 12, 2026. Automatic prompt delivery to the existing Claude Desktop session
was verified at 23:53 PDT using Claude's supported cross-session messaging. Codex
reads Claude's replies from the shared task logs and its specified local transcript.
Chat histories remain separate. See [delivery procedure](SESSION_DELIVERY.md).

## Open the conversations

- [Claude: IGVC SIM handoff and mechanicsSandbox integration](claude://claude.ai/epitaxy/local_db1e3368-182b-44de-94ee-bdc185cc1084)
- Codex: **Plan Unity IGVC ROS2 simulation**, the chat displaying this companion.
  Thread ID: `01a08621-821d-7d50-8543-ec301e5c3415`.

The Claude link was supplied by the user. Its matching local transcript contains
Claude's same session-link message at `2026-10-13T06:44:44.305Z`.
The deep link has not been launched or verified through this companion.

## Shared work and messages

- [Task board](BOARD.md): declared task state and owners.
- [Map reconstruction / T-0089](tasks/T-0089-reference-autonav-map.md): map handoffs, reviews, and approval state.
- [Sandbox integration / T-0070](tasks/T-0070-unity-latency-selection.md): implementation handoffs and reviews.
- [Collaboration protocol](PROTOCOL.md): ownership and message rules.
- [Observatory](OBSERVATORY.md): existing read-only visualization and freshness limitations.

Both sessions must read the current board and relevant task's latest messages
before acting. Append coordination messages to the primary checkout's task logs;
do not overwrite earlier messages or treat a posted message as acknowledged.
Existing task ownership, review requirements, and simulator leases still apply.
Linking the sessions does not approve a blocked implementation retry.

The user does not need to copy prompts or replies between chats. ASTRA delivers
new authorized assignments through the verified courier route and collects replies
while working or on the existing 15-minute coordination heartbeat. Delivery is
explicit and deduplicated; idle polling does not launch Claude or spend model tokens.

## Local identity record

- Claude desktop session: `local_db1e3368-182b-44de-94ee-bdc185cc1084`.
- Claude transcript session: `cd916c5d-b081-45dc-8f01-c4d90eab0446`.
- Transcript (read-only; not copied into this repository):
  `C:/Users/brand/.claude/projects/C--Users-brand-Documents-ChatGPT-IGVC-SIM/cd916c5d-b081-45dc-8f01-c4d90eab0446.jsonl`.
- Primary checkout: `C:/Users/brand/Documents/ChatGPT/IGVC SIM`.

Transcript activity is historical evidence, not a live process or delivery signal.
Remote Control has not been enabled by this work.

## Acknowledgment

At 2026-10-12T23:49:32-07:00, the user relayed Claude's acknowledgment of this coordination
method. ASTRA recorded its reply and the next bounded read-only assignment in
T-0070, with the integration hold in T-0088. Claude delivery/ACK of that new
assignment is still pending; no automatic chat synchronization is claimed.

At 23:53:18 PDT, the exact transcript session replied `ACK igvc-link-236690fa94f1`
to the automatically delivered message. At 23:53:40 PDT it appended the assignment
ACK to T-0070 and claimed the read-only reconciliation plan. This supersedes the
pending-delivery statement above. Receipt: `artifacts/agents/session-bridge/handshake-r1/roundtrip-receipt.json`.
