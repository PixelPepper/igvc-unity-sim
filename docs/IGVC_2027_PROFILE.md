# IGVC 2027 AutoNav profile

`config/competition/igvc-2027-autonav.json` pins the **7 July 26 Version** of the
[official 2027 rules](https://gl-systems-technology.net/uploads/3/4/7/2/34727963/igvc_2027_rules_version_7_july_26.pdf),
Sections I and II, retrieved September 30, 2026. Its SHA-256 is
`4a7162913bce181839228041f1a79512035f597861514cd9edfe7d7181d080b3`.
The profile is reference data, not an assertion that the fixture or R3-a meets
competition rules. It does not close the PLAN.md hardware or autonomy gates.

Implemented: a stdlib-only, read-only checker with structured JSON output:

```powershell
python tools/check_competition_profile.py --course artifacts/courses/seed-2027/course.json --autonomy artifacts/courses/seed-2027/autonomy.json
# Optional evidence:
python tools/check_competition_profile.py --course path/to/course.json --autonomy path/to/autonomy.json --settings path/to/settings.json --run path/to/run.json
```

Output goes to stdout; the checker never changes any input, starts a simulator,
or downloads the rules. Exit codes are 0 pass, 1 fail, 2 unknown. `status`
aggregates every check, with fail taking precedence over unknown;
`configuration_status` aggregates declared configuration checks. Each check has
`id`, `scope`, `status`, `detail`, `observed`, and `expected`. Input file hashes
bind a report to its exact bytes. Hardware/judge requirements remain unknown,
so even passing configuration produces overall unknown and `certification=false`.
A CI caller should inspect check IDs/scopes and accept exit 2 only deliberately.

| Requirement | Exact comparison | Reference |
| --- | --- | --- |
| Maximum speed | 5 mph = 2.2352 m/s | I.2 p6, I.4 p9, II.1 p10 |
| Run budget | At most 360 seconds | II.2 p10, II.3 p12 |
| Ramp grade | rise / horizontal run <= 0.15, about 8.53 degrees | II.2 p10 |
| Optional simulated potholes | 2 ft = 0.6096 m diameter, solid white circles | II.2 p10 |
| Passage | At least 5 ft = 1.524 m clear obstacle-to-line opening | II.2 p10 |
| Supplied guidance | Two waypoint pairs, four destinations | II.2 p10 |

The whole-run average must exceed 1 mph (0.44704 m/s). The opening-speed
narrative specifies 44 ft / 30 seconds (II.2 p10); the traffic table specifies
88 ft / 60 seconds (II.4 p13), whose narrative returns to 44 ft. These distances
give the same nominal speed but different evaluation windows. Both are retained
as an unresolved conflict requiring organizer clarification. The checker does
not choose a definitive window or treat sampled chord average as judged distance.

Keep `autonomy.json` in the runtime's strict current schema: exactly
`schema_version`, `origin`, `goals`, and `max_speed_mps`. Optional metadata goes
in a **separate settings receipt**, never injected into autonomy:

```json
{
  "timeout_wall_s": 360,
  "requested_speed_mps": 2.2,
  "waypoint_pairs": [[0, 1], [2, 3]],
  "guidance": "organizer_waypoints"
}
```

Pair indices must cover four goals exactly once. A declaration of organizer
guidance checks compatibility; it does not prove coordinates came from judges
or verify crossing semantics. Missing receipts/settings return unknown. Existing
six-region training missions fail the competition destination-count comparison.
The checker never converts them or removes their goals.

The existing course schema uses `units="m"`, `ramps[].height` and
`ramps[].rise_length`; the latter is horizontal run, not sloped surface length.
Potholes use `kind="pothole"`, `length`, `width`, `depth`, `color`, and an optional
explicit `representation="solid_white_circle"`. A positive depth or dark color
fails that representation check, even if the declaration says white circle.
Missing appearance evidence stays unknown. Potholes and ramps are optional;
explicit empty lists are supported. Course `passage_widths_m` optionally records
all applicable measured clear openings; lane width alone cannot establish them.
The checker trusts declared clearance measurements and does not derive openings
from geometry or verify the completeness of that inventory.

Optional run fields `timeout_wall_s` and `requested_speed_mps` are runtime
ceilings; `elapsed_wall_s` is recorded wall duration. None proves hardware
qualification or correspondence with the judge's clock. A run `course_sha256`
is compared to the supplied course bytes. `trajectory` samples are
`[time_s, x_m, y_m, ...]` with strictly increasing timestamps. Chord speeds above
the limit fail; samples below it stay unknown because they cannot bound motion
between samples. Coordinate resets/teleports invalidate physical interpretation
and must be excluded by the run producer; this checker is not a trajectory audit.

Tested through `tools/tests/test_competition_profile.py`: unit boundaries,
percent-versus-degree grade, white-circle versus depression appearance, time and
speed ceilings, training guidance mismatch, pairing, missing clearance evidence,
sampling limits, input immutability, digest mismatch, and nonfinite input rejection.

Pending: measured physical geometry, payload, safety light, hardware governor,
E-stops, onboard-only processing and control, qualification, judge semantics,
organizer guidance provenance, and resolution of the opening-speed conflict.
Nominal course dimensions are retained as guidance without invented tolerances.
