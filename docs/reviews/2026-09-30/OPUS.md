# Opus 5.5 assignment

Read HANDOFF.md first. Review navigation architecture and causal failure chain.
Use exact model `claude-opus-5-5`; no Auto or fallback. High effort, Fast off.

Focus: interface between observed guidance, forward primitive search, latest-pose
admission, FollowPath/RPP execution and backup. Is the checked geometric path
actually executable under controller/adapter limits? Does preserved recovery
intent preserve a useful escape, or simply repeat a target? Distinguish genuine
footprint infeasibility, controller projection, target selection and perception.
Challenge whether an orientation gate merely adds another local dead end.

Primary files: tools/observed_navigation.py, sensor_route_policy.py, path_entry.py,
execution_path.py, recovery_policy.py, recovery_intent.py, sensor_course.py.
Use source slices; do not read every log. Relevant evidence is the compact trial
summary, oriented-entry execution/planner diagnosis, and experiment profiles.

Available check IDs: `navigation`, `replay-oriented`, `replay-directed`.
At most three total calls. Tests run on the frozen baseline. Replays use old
observations with current code and must be labeled counterfactual when hashes
differ. No live sessions or source edits. Request at most one new experiment
through `request_experiment` if a focused proof is missing.

Deliver ≤5 findings with exact file/line or evidence references, causal mechanism,
confidence, tests actually run and one highest-value next experiment. Include a
short recommendation on controller/trajectory contracts; avoid proposing a new
controller solely because another trial failed. Final summary ≤300 words.
