# Independent review status

Review packet date: 2026-09-30 (local). Provider attempts occurred 2026-10-01 UTC.

Start with [HANDOFF.md](HANDOFF.md), then the assigned packet and
[report format](REPORT_TEMPLATE.md). No navigation source was changed for this review.

## Frozen baseline

- Git baseline: `01709fe72365a3055bb768ec316d125aef1a51b2` on `codex/transport-probe`,
  plus the explicitly captured dirty working tree. Git HEAD alone is insufficient.
- Local snapshot: `artifacts/reviews/2026-09-30/baseline`, 186 files.
- Manifest SHA256: `77f2ebe7ceaa71cb58f9d014a1e3965936ca616b823c8f2485268da79319b1fa`.
- Coordinator check: `review-check.sh integration` verified the manifest and passed
  all 37 tests in 20.2 seconds. This does not prove a completed live lap.
- Portable local copy: `artifacts/reviews/2026-09-30/IGVC-review-baseline.zip`
  (923,321 bytes). All 186 archived files were independently checked against the
  same manifest. It excludes SDK stores, credentials and unrelated workspace files.
- Handoff tooling: four Node tests passed, including exact-model/mode selection
  without fallback; focused `git diff --check` passed.

## Dispatch status

| Reviewer | Scope | Actual result |
|---|---|---|
| [Opus 5.5](OPUS.md), Claude CLI `claude-opus-5-5`, high effort | Navigation architecture, controller/path agreement, recovery | Completed; 40 navigation tests passed, two recorded replays. [Raw report](OPUS_FINDINGS.md). |
| [Sonnet 5.5](SONNET.md), Claude CLI `claude-sonnet-5-5`, high effort | Perception, surface projection, retained lane evidence | Completed; 14 perception tests passed, one recorded replay. [Raw report](SONNET_FINDINGS.md). |
| [GPT-6.1 Sol](SOL.md), built-in `gpt-6.1-sol`, high effort | Contracts, integration, audit reliability, reproduction | Completed: 37 integration tests passed; three negative controls exposed acceptance gaps. [Full findings](SOL_FINDINGS.md). |

The original Cursor attempts appeared in the authenticated account catalog, but inference
was refused. Cursor reported the allowance resets on **2026-10-26**, with a paid
spend limit as another provider option. No billing setting was changed, alternate
provider/model substituted, or failed role retried. Token usage was unavailable;
do not interpret missing usage as a verified zero charge. Local failure records
remain in `artifacts/reviews/2026-09-30/{opus,sonnet}/`. The user subsequently
corrected the provider to **Claude CLI**, which is installed and authenticated.
New explicit attempts use `claude-opus/` and `claude-sonnet/`, preserving the same
manifest and the old failures. No Cursor inference was attempted again.

Both Claude CLI attempts completed with exact initialized model IDs, exit 0 and
no fallback. Reported list-price/API-equivalent costs were **$1.1627178 Opus** and
**$0.438788 Sonnet**, totaling **$1.6015058**. These are CLI-reported estimates,
not a claim of extra charges to the Claude subscription. Each stayed within the
requested $5 limit. Detailed usage remains in each provider attempt's `usage.json`.

**Read the [integrated findings](REVIEW_SUMMARY.md) before acting on raw reports.**
The coordinator reproduced two counterexamples, identified missing acquisition
frames and rejected one Opus tracking-error calculation. No live lap or production
navigation change was made in this review.

## Findings received and next steps

1. **Confirmed acceptance gap:** synthetic runs with missing sensor-health evidence,
   explicitly failed health, or a mismatched mission hash still received
   `full_loop_certified=true`. Sol's targeted rejection test exited 1 as intended.
   The coordinator inspected the audit qualification path and confirmed that it
   does not consume these fields. Geometry checks remain useful; a final acceptance
   layer must separately require interval health and matching mission identity.
   [Recorded negative-control results](SOL_NEGATIVE_CONTROL.json) preserve the
   actual outputs; the test command is in the full Sol report.
2. **Unresolved historical evidence gap:** the short-lookahead trial is 1/6 and
   fails trajectory continuity. Clear sampled geometry cannot establish what
   happened during missing samples. Inspect the original offending interval before
   attributing a cause; keep the existing rejection threshold.
3. **Untested integration hypothesis:** motion between path admission and delayed
   controller activation could invalidate the admitted starting pose. Test a fake
   action server with controlled acceptance delay before proposing a correction.
   This is not proof of the historical controller failure.
4. **Provenance limitation:** bind future run records to effective controller
   configuration and installed source/build identities, not only selected mission
   Python hashes. Existing profile files alone do not establish what ran.

These are Sol's integration findings. The subsequent perception/navigation results
and proposed implementation order are in the integrated findings linked above.
No live lap was run or certified during this handoff. No source fix or new 6/6
result is claimed.

## Provider routing and preserved attempts

Use Claude CLI for Opus/Sonnet and reserve Cursor for other tasks. The CLI runner
keeps the baseline immutable and creates a separately named provider attempt with
the same manifest and assignment. It refuses an existing role output folder,
deliberately preventing accidental retries.
Do not erase prior failures to bypass that safeguard. Reviewers may run only the
named offline tests; extra experiments return to the coordinator. Live session
ownership and final acceptance stay with the coordinator.

The baseline is local and ignored by Git. For an external handoff, transfer only
the verified allowlisted snapshot and packets through the approved review path;
do not send the full workspace, conversation, credentials or CAD/build outputs.
