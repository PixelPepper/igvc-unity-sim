# GPT-6.1 Sol assignment

Read HANDOFF.md and root README status first. Use `gpt-6.1-sol`, high effort.
Independently review integration, run ownership, evidence quality and acceptance
tests. Do not repeat Opus's controller design or Sonnet's projection analysis.

Inspect tools/sensor_course.py, recovery_intent.py, navigation_decisions.py,
record_navigation_episode.py, capture_observed_clearance.py, audit_sensor_run.py,
course_judge.py and the relevant tests. Examine the new preserved-guidance replay
schema, action cancellation/backup ordering, invalid/expired intent handling,
source/profile provenance and report claims. In particular, explain what the
short-lookahead trajectory-continuity failure means before a trial can pass.

Work from the frozen source at artifacts/reviews/2026-09-30/baseline once supplied.
First inspect its manifest; do not mistake HEAD for the working-tree baseline.
Use the shared offline check `integration`; one additional targeted replay or
minimal negative-control test is allowed if justified. No broad rerun just to
accumulate a passing count. Write only your assigned report/experimental files
under artifacts/reviews/2026-09-30/sol/. Do not change production or baseline files.
No Unity/ROS sessions, builds, installs, Git mutations, networking, credential
reads, or recursive delegation. Queue any live test request to the coordinator.

Report ≤5 ranked findings with path/line, mechanism, evidence vs uncertainty,
actual test commands/results and missing acceptance coverage. Write report.md
and return summary ≤300 words. Do not claim a new sensor-led 6/6 success: none
exists in the provided record. Stop after one bounded review pass.
