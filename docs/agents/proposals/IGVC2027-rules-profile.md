# Proposal: IGVC 2027 rules course profile (user-directed, 2026-10-12)

Author: claude-opus-5-5. Status: proposal for ASTRA decomposition and dispatch. Not a task header.

## User request
"Make a 2027 rules profile and start with those": rule potholes, real barrel size, no barricades,
narrower lanes and dashed lines, and score laps against the 6-minute limit. The user asked that the
work be split across sub-agents, including ASTRA and Sol.

## Source
IGVC 2027 rules v7 (July 26), AutoNav pages 5-14; text extracted to
`.claude/worktrees/sim-realism/artifacts/scratch/igvc2027_v7.txt` (pages 11, 15, 16 are images and
were not read). The user supplied the barrel size: 39.7" H x 23.5" W. The rules give none.

| Rule (page) | Current simulator |
| --- | --- |
| 6-minute run (II.2 p10, II.3 p12) | Successful laps take 353-389 s |
| Track 10-20 ft, "approximately ten feet"; turn radius >= 5 ft (p10) | 6 m lane (19.7 ft); Unity rejects lane_width_m < 4 |
| Lines 3-4 in white tape, continuous or dashed (p10) | 0.12 m (4.7 in), continuous, one unmarked stretch |
| Obstacles: non-lipped construction barrels/drums (p10) | Barrels 0.60 x 0.90 m, plus barricades |
| Potholes: 2 ft solid white circles; contact ends the run (p10) | Dark bowls by default; rule circles opt-in (b517a99) |
| >= 5 ft passage between line and obstacle on one side (p10) | Violated on most normal/hard seeds: best-side gap down to 0.4 m (tools/course_passage.py survey) |
| Ramps <= 15% (p10); light rain runs (p12) | Ramp present; rain not modelled |
| Two waypoint pairs; No Man's Land entry/exit crossed either way (p10) | Six broad GPS destinations |
| Penalty table II.4 (p13); internal line crossing ends the run (p12) | Audit has contact/line checks, no ticket scoring |

## Proposed split (disjoint ownership; at most two implementers)

1. **P1 course profile** (Opus, branch `claude/sim-realism`, worktree `.claude/worktrees/sim-realism`).
   Owns `tools/generate_course_variant.py`, `tools/course_passage.py`, `tools/tests/test_rule_potholes.py`,
   a new `tools/tests/test_course_profile_2027.py`, and the `tools/sandbox.ps1` course flags.
   - `--profile igvc2027`: rule potholes, no barricades, barrels 0.597 x 1.008 m.
   - Reject layouts that break the 5 ft passage rule.
   - Optional narrower lane width and dashed boundary marking.
   - Default layouts byte-identical.
2. **P2 Unity rendering** (needs ASTRA, which owns Unity builds; a second implementer could take it).
   Owns `CourseVariant.cs`, `RealisticObstacles.cs` (uncommitted in the worktree), `SandboxDocument.cs`.
   - Painted potholes, realistic drum and barricade models, dashed paint.
   - Lane width validation below 4 m.
   - Build plus visual check.
3. **P3 rules scoring** (second implementer, e.g. Sonnet; must not collide with the T-0083/T-0084 auditor work).
   Owns a new observation-only report, `tools/rules_score_2027.py`, plus tests.
   - The 360 s budget and the II.4 ticket table.
   - Leaves the existing audit verdicts unchanged.
4. **Reviews.** Sonnet reviews the code of P1-P3. Sol reviews the rules extraction (now) and each piece's evidence.

## Open questions for ASTRA
- **Lane width.** "Approximately ten feet" cannot coexist with a centred 2 ft barrel and 5 ft each side
  (that needs about 12 ft), and the robot footprint is 1.0 x 1.7 m. Proposal: vary the width per
  sector, 10-20 ft, with obstacle sectors wide enough to satisfy the passage rule.
- **Mission structure.** Two waypoint pairs instead of six destinations is an autonomy-contract change, so it is deferred.
- **Speed.** Meeting the 6-minute budget likely needs a higher requested speed. Measure that only after the profile exists.
