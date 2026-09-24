# Lidar ground returns during ramp descent

The 2026-09-17 controlled traversal reproduced the reported heatmap wall. This
was a manual diagnostic on the generated course, not an autonomous lap.

At scan acquisition time 163.480 s, the lidar origin was approximately
`(6.2165, 44.5, 0.6980)` in odom and its forward beam pointed 7.5946 degrees down.
Forty road returns near `x=0.9817`, `z=0` matched lethal cost 100 in the next
global and local costmaps. Across descent, 1,050 forward ground returns were
recorded. Depth obstacles contained no road-surface points during descent;
depth surfaces correctly recognized the lower road. Raw lidar marking was the
confirmed source of this wall.

Navigation now has separate lidar inputs:

- `/scan` remains unchanged and clears only to measured ray endpoints.
- `/perception/lidar/obstacles_scan` marks obstacles after comparison with fresh,
  preceding observed depth-ground support. Suppressed values are NaN, never
  fabricated infinite clearing rays.
- `/perception/lidar/status` reports suppression and conservative fallback.

The filter uses acquisition-time TF, local surface support, slope/height checks,
and nearby nonground ambiguity. Missing transforms or stale/missing depth leave
the raw marking return intact. It does not use course geometry, a fixed road
height, or a simulator collision-layer exclusion.

Sparse depth rows initially could not surround some lidar hits. The refined
filter retains a nearest-ground requirement of 0.3 m, but fits surrounding
observed support within 0.6 m, with a 0.04 m height tolerance, 0.025 m maximum
fit residual, 20-degree slope limit and nearby nonground ambiguity rejection.
It never extrapolates beyond the observed support hull. Eleven behavioral tests
passed, including sparse rows, missing close support and height discontinuities.

The repeated controlled live descent removed all 276 central ground returns
from marking. Both global and local costmaps had zero central lethal and
inscribed cells throughout captured descent (five global/eleven local maps),
compared with baseline peaks of eleven/twenty lethal cells. All 859 elevated
descent returns and 3,490 elevated returns across matched phases were preserved.
Peripheral ambiguous ground returns remain conservative obstacles. This
validates the recorded controlled descent, not arbitrary terrain or a full lap.
See the [matched scan/costmap comparison](evidence/sensor-autonomy/ramp-descent-filter.json).
The source capture and detailed attribution are retained locally under
`artifacts/checks/ramp-descent-controlled`; they are not navigation inputs.
