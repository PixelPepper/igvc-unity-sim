# path_entry_20261005.json.gz

Observation-only regression input for the T-0014 path-entry curvature comparison.

## Source

All sources are frozen T-0012 inputs from T-0009 decision 212. Their hashes were verified against
`artifacts/agents/T-0012/inputs/manifest.json` before extraction.

- **Live run:** T-0009 was launched from `8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f`. That is the source that produced
  these recorded observations.
- **Probe and review base:** `70b3566d91dce8b807fee729dbb110c20db3c764`. T-0012 and T-0014 loaded `tools/path_entry.py`
  from this commit; its source is byte-identical to the live run for this module.

| Source file | sha256 |
| --- | --- |
| `decision-212-events.json` | `127a71a3af599f763e2f80cc7f8e65d382107364b22bb7b2006a9d917f72ba2e` |
| `00212.json.gz` | `66164a15c156f3b7a6a1e0785b97ce38ac2dcce2dcf29359418af715600ebe22` |

## Contents (unchanged values)

| Field | Origin |
| --- | --- |
| `plan.path`, `plan.path_yaws` | The evaluated plan: 136 points, the exact object admission received |
| `checked_pose` | The pose admission used. It equals the plan's first point and yaw |
| `recorded_admission` | The live diagnostic: `no_forward_connector_within_turn_radius` |
| `grid` | The **planner-submission** grid from snapshot 212 (origin, resolution, width, height, costs). It is not necessarily the latest live admission grid |
| `footprint` | The recorded `goal_footprint` |

- **Excluded:** snapshot metadata, lane points, destination and any course, WORLD or teacher data.
- **Determinism:** written with gzip mtime 0. sha256 `4850d42da3ad17568a9d5fd1ce624fbb1e01742667243e6719f6053c43170141`.
