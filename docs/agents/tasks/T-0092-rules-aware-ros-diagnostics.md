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
