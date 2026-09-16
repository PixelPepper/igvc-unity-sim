# Reference-inspired sectors and colored barrels

The user-supplied course photograph replaces the earlier interpretation of
"barrels anywhere". Obstacles now occupy the driving sectors, not unused midfield.
This is a procedural practice layout inspired by the reference, not a surveyed
reconstruction or a statement of IGVC 2027 rule compliance.

- A rounded loop keeps a clear start straight.
- Two connecting sectors contain alternating barrel groups. Six barrels obstruct
  unshifted centerline traversal; the clearance-checked guide weaves around them.
- An open sector opposite the start contains random barrels and barricades.
  Boundary paint ends before the ramp approaches and resumes after the exits.
  The clarified dense layout has 16 barrels in these two gaps on normal
  difficulty (8 in each), up from 4 total. Easy has 12 and hard has 20. The
  normal course has 36 barrels overall; ramp surface and guide clearance remain
  reserved. The sequence is painted lane → open barrel area → white-edged ramp
  → open barrel area → painted lane.
- The ramp retains white paint along both edges. Its painted section separates
  the two gaps; mission perception modes no longer merge them into one interval.
- Barrel colors are seeded red, orange, blue, green, yellow and white. Legacy
  manifests without a color still render orange. White barrels use dark rings;
  other colors use white rings. Colors are appearance, not navigation commands.
- Seed 2027 has 31 goals, versus 82 in the original dense mission. The dense guide
  remains available to the physical lap audit; it is distinct from lane geometry.

The generator proves a clearance-checked alternating guide, not uniqueness of
that path. It still uses known geometry to author guidance goals, so this fixture
does not prove general autonomous discovery of an unknown competition course.

## Validation

### Denser ramp approaches

The clarified 16-barrel open sector passed all 13 geometry tests, followed by an
uninterrupted 31/31 lap with all 12 [audit checks](evidence/dense-ramp/audit.json)
passing. Minimum sampled clearance was 0.307 m and conservative swept clearance
0.211 m; no resets, recording gaps or line interventions. The initial Nav2
startup encountered a lifecycle service timeout and the startup sensor-rate
check failed; after a ROS container restart, navigation became active and all
seven [integration checks](evidence/dense-ramp/integration.json) passed before
the successful lap. No Unity code changes or player rebuild were needed for
this manifest-only density adjustment. Earlier results below refer to the
four-barrel open sector.

![Denser open areas before and after the marked ramp](evidence/dense-ramp/overview.png)

### Initial sector layout

Geometry: 13 tests passed on Ubuntu across multiple seeds/difficulties, including
barrel coverage, obstruction of unshifted traversal, alternating passage,
footprint clearance, separate gaps, ramp paint and sparse goals.

Perception: 17 RGB tests passed for colored barrel stripes and shadows, including
paint touching stripes. The saturated-color heuristic remains fixture-specific;
colored ground can confuse it. White barrel surfaces rely on depth eligibility
for lane rejection, and their dark rings can remain hazard candidates.

Unity Windows build passed with 3 rendered ground fixtures, 6 depth checks,
70 ramp checks and 12 caster checks. Linux player rebuild/runtime validation was
not performed in this slice.

Windows Unity/Docker Jazzy completed a fresh uninterrupted 31/31 lap and passed
all 12 [route-audit checks](evidence/reference-course/audit.json). No resets,
recording gaps or line interventions; maximum speed 2.2 m/s. Minimum sampled
obstacle clearance was 0.277 m, with conservative swept bound 0.141 m.

The initial debugging lap paused at the ramp exit. A 3 m camera transition buffer
now switches to unpainted mode before nearby paint disappears, while the middle
of the ramp remains painted. Planning requests limit extra goals to 8.5 m, and
resume reapplies the perception mode reset by cleanup. Three mission-mode tests
pass. Debugging pauses are not counted as an uninterrupted success.

The startup transport check failed its rate threshold; timestamps, payloads and
TF passed. That [startup result](evidence/reference-course/startup-integration.json)
is retained. The subsequent [warmed-up check](evidence/reference-course/integration.json)
passed all seven checks (RGB 11.44 Hz, depth 7.89 Hz, scan 4.49 Hz). Runtime
camera imagery was visually inspected for colored barrels. Docker was rebuilt
with the final scripts.

![Course overview](evidence/reference-course/overview.png)

![Live camera image](evidence/reference-course/camera.png)
