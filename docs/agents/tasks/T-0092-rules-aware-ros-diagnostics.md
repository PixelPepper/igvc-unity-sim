---
id: T-0092
title: Run rules-aware ROS diagnostics on the corrected95-barrel course
status: in-progress
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: c288e72e1d633b2e15abf7eb7789c1892dc4f46f
candidate: none
claim: none
lease: none
updated: 2026-10-13
---

## Packet
Direct human request: start ROS test runs and understand supplied IGVC2027 AutoNav rules throughPDFpage16. T91 accepted95-barrel scene/player frozen, no sourcechanges/rebuild. Root owns live lease and execution. Two predeclared diagnostic attempts: clear-noon then overcast; same map/mission/profile, maxspeed0.6m/s, existing180s cap, zero retries. Each launcher obtainsall3locks and keeps through confirmedcleanup; refuseforeignprocesses. A failed navigation result does notjustifyextraattempts. Abort second iffirsthealth/cleanup/sourcebindingfails. No pooling withpriorT90runs. 180s cannotcover484.247ft at0.6m/s evenideal; theseare initialnavigation diagnostics, notfullcourse/qualification. Fullsixminutejudge/finishcrossing gap remainsunimplemented; T84blockedretry notauthorizedbyrunrequest.

Rules baseline suppliedPDF pages1–16, especiallyI.2/I.4 andII.1–6. Report44ft/30s and conflictingtable88ft/60s, >1mphaverage,5mphhardwaremax,6mincap, boundarypartial/full andobstacletouch/displacement distinctions, NMLwaypoints, optionalwhitepotholes, safety/E-stop/payload/unmodeledhardware. No guessesofficialscoreorallrulespass. Larger143.815x171.022ftfootprint user-authorizedtrainingdeviation, inneredge/routecurvaturelimitsremain. Sourcegeometryonlyofflineevaluation, neverpolicyinput. BroadGPSgoalsremainunchanged.

Claude linked exactOpus may readrules and inspect unchangedlauncher/runrecord semantics, write <=300word rules-gap memo inartifacts/T92 andappendtasklog, no source/tests/sim/providers. Sonnet reviewsnewrules-analysis only, nativeSol finalrun/evidenceinterpretation. Atmost2workersplusroot inclreservedinteractive; nooverlappingcourier/reviewer slots. Root freezes source/player/input/protectedpins beforelaunch, recordsalloutcomes andpostflight, retainsfailuredata. No providerretry/substitution/push/publish.

### 2026-10-13T03:29:08.014869-07:00 · gpt-6-astra → team · DECISION
Human authorized fresh ROS diagnostics onT91 corrected95map. Exactly2attempts declared asabove, notrepeatofT90map. No sourcechanges or blockedT84retry. Rootpreparingpins/leases, linkedClaude rulesreview planned.

### 2026-10-13T03:29:31.378429-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
rules-ros-gap-r1. T0092 read-only rules-and-harness gap memo, bounded4active minutes. HumanasksROSrunsandunderstandIGVC2027AutoNav suppliedPDFthroughpage16. Primary docs/agents/tasks/T-0092-rules-aware-ros-diagnostics.md authoritative. Read artifacts/agents/T-0089/rules-pages-1-16.txt (reference data) and tools/reference-rules-map.ps1, reference_map_trial.py plusrelevantsensor_course output semantics only. Rootruns exactly2initialdiagnostics clear-noon/overcast .6m/s180s,no retries/sourcechanges; rootownslocks/live. No edits/source/tests/Unity/ROS/processchecks/providers/delegation. Own ONLY artifacts/agents/T-0092/claude-rules-gap.md and append ACK/HANDBACK tasklog. Produce <=300words withPDFpage/section, distinction:44ft30snarrative vs88ft60stable,>1mphmean/5mphhardwarelimit,6min,partial/fullboundary andtouch/displacementpenalties, NMLcrossing/qualificationdiameter vs currentbroadgoalradii,optionalpotholes,safety/payload/notmodeled. Clarify180s cannotfinish147.6m at.6m/s; diagnosticnotcompetitionjudge. Rootmaycomputesavedtrajectoryfirst44ftprogressoffline, cannot inferjudgescore justfrompathlengthorsoftwareguards. Flagambiguousscoringtextwithoutinventingofficialinterpretation. No codefix/newassignment/retryT84. Returnmemo/sourcepins knownactualmodel ifavailable, <=150wordhandback. Needindependentanalysiswhile rootpreparesnewrun;no duplicateimplementation.


### 2026-10-13T03:29:47.427520-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
ACK igvc-t92-a4ffa8aa34. rules-ros-gap-r1: read-only memo to artifacts/agents/T-0092/claude-rules-gap.md, 4 active minutes. No edits, source changes, tests, Unity, ROS or providers.

### 2026-10-13T03:30:18.966218-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
rules-ros-gap-r1 [igvc-t92-a4ffa8aa34]. Memo artifacts/agents/T-0092/claude-rules-gap.md (sha256 75d9109eb4a82441…), read-only, from rules-pages-1-16.txt. Model claude-opus-5-5.
- **Ambiguities flagged:** 44 ft/30 s (p.10) vs the table's 88 ft/60 s (p.13), both 1 mph; internal-line E-stop (p.12) vs careless driving -5 ft; the text cites II.5 but the table is II.4.
- **Also covered:** the average above 1 mph disqualifies; 5 mph is a hardware governor (our 0.6 m/s cap is software); the 6-minute limit; boundary, touch, displacement and blocking tickets (1 ft = 1 s).
- **Waypoints:** NML pair crossed either direction; the 2 m diameter qualification waypoint vs our 2-3 m goal radii.
- **Not modelled:** potholes, payload, E-stops, tactile ban, rain.
- **180 s cap:** at most 108 m < 147.6 m.
- **Guard:** it blocks motion and is not a ticketing judge.
No edits or runs.

### 2026-10-13T03:30:31.438124-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
The memo was trimmed to the 300-word limit after the handback; content is unchanged. New sha256 04e6af86c99efd61…

### 2026-10-13T03:38:41.977516-07:00 · gpt-6-astra → team · DECISION
Actual linked Claude ACK/HANDBACK rules-ros-gap-r1 received; courier exit0 exactOpus USD0.0517498. Original memo preserved, root corrected lane scoring/penalty/hardware statements. Sonnet r1 BLOCKING and r2 PASS retained; exactSonnet costs USD0.1034478 + USD0.1128658. Root rules-interpretation.md is accepted interpretation, not official ruling. First declared clear-noon run20261013T103357-ec96a4dc ended at180.058610126s diagnostic timeout,3/6destinations,1802PASS/0fail/0unknown sampledhealth,20runtimepinsmatch,cleanupconfirmed/all3locksreleased03:37:29.952. first-admission.json permits second declared overcast run now active under launcher locks. No retry/newsource/build/T84continuation. No navigation-complete/rulespass/lightingcause claim.
