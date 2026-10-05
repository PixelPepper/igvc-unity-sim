# Sonnet 5.5 assignment

Read HANDOFF.md first. Review sensor projection, observation retention and false
paint obstacles. Use exact model `claude-sonnet-5-5`; no Auto or fallback.
High effort; default context variant, no million-token context.

Focus on the two off-paint retained observations in oriented-entry-paint-truth.
Trace RGB query pixels, acquisition TF, matched depth/surface neighborhood,
plane/support eligibility, output coordinates, confirmation and expiration.
Can valid ground support be reused on another ray and create an elevated or
laterally misplaced point? Can stale confirmed geometry survive contradictory
fresh evidence? Preserve real paint and legitimate ramp edges in any remedy.

Primary files under ros2/src/igvc_perception/igvc_perception:
surface_projection.py, lane_node.py, point_memory.py, lane_detection.py (if present),
terrain_projection.py and surfaces.py. Tests: test_recorded_lane_projection.py,
test_surface_projection.py, test_point_evidence.py. Relevant fixture:
fixtures/white_barrel_cap/metadata.json. The coordinator supplies targeted text
evidence; request a precise frame/stamp if acquisition-level attribution needs it.

Available check IDs: `perception`, `replay-oriented`. At most three total calls.
No production edits, WORLD-derived runtime filters, blanket age-based erasure or
weakened lane blocking. WORLD geometry may be read only as offline diagnostic
truth already reported; proposed runtime algorithms must remain sensor-only.

Deliver ≤5 findings, clearly separating proven code defects from hypotheses.
Supply one synthetic/captured regression design with expected/actual geometry
and negative controls for real paint/ramp markings. Record actual tests and
source hashes. Request at most one new experiment through `request_experiment`.
Final summary ≤300 words; no live sessions or recursive agents.
