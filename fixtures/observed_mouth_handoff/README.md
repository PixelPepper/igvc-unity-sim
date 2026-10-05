# Recorded lane-mouth planning failures

These compressed decision inputs contain observed costmaps, camera lane points,
robot pose and one broad destination. They contain no WORLD geometry or guide
route. Use them only for offline replay. File hashes are in `metadata.json`.

| Snapshot | Original outcome | Correction exercised |
| --- | --- | --- |
| `near_straight.json.gz` | No route toward a mouth only 0.340 m away | Advance within both observed boundary spans |
| `corner.json.gz` | No route toward a nearby mouth behind the corridor station | Allow an observed interior target with room to turn |
| `post_ramp_oblique.json.gz` | No route; the mouth was 1.160 m away | Determine handoff from observed longitudinal/lateral membership, not center distance |

From the repository in Ubuntu/WSL with the project Python dependencies:

```bash
python3 tools/replay_navigation_decision.py \
  --snapshot fixtures/observed_mouth_handoff/post_ramp_oblique.json.gz \
  --output artifacts/post-ramp-replay.json
```

The original source rejected these inputs; the integration replays found checked
forward paths with unchanged observed costs and search budget. The replay reports
source fingerprints, acquisition ages, chosen guidance and full planner diagnostics.
Wall-limited outcomes can vary by machine. Finding a path does not prove controller
tracking, acquisition accuracy, hardware fidelity or a completed course.
