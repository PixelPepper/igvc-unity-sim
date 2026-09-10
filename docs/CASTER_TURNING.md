# Caster turning bench validation

The suspension bench now has a bounded manual turning test in addition to [straight ramp traversals](CASTER_SUSPENSION.md). It approaches ROS X=3.4 m, stops on the ramp, pivots through a full revolution, stops again, then performs left/right/left arcs. This extends validation of the provisional support model; it does not add contact physics or autonomous terrain navigation.

From the repository root in PowerShell, start a fresh suspension-enabled bench at its stationary origin:

```powershell
.\tools\igvc.ps1 stop
.\tools\igvc.ps1 terrain-start -Visible
.\tools\igvc.ps1 terrain-turn-test
```

Use `terrain-build` first if the player needs rebuilding. The test does not reset the simulator or rearm autonomy. It commands manual motion, bounds each phase, aborts subsequent phases when a required phase fails, and repeatedly sends zero for two seconds on exit. It requires fresh joined observations throughout. Measured near-zero linear/angular velocity must persist for 0.3 simulation seconds at stops; elapsed waiting alone is insufficient. The pivot checks accumulated yaw and maximum observed axle drift, while each arc requires translation and signed yaw change.

The verifier independently samples the surveyed ramp/strip geometry at four heading-rotated support locations. It checks compression, body offset and normal, support limits and 3D axle speed against exact-stamp odometry/body/diagnostic observations. Only compression equations near actual contact positions within 3 mm of strip boundaries are exempted for discontinuous-edge ambiguity; pose/travel bounds remain active.

The [live report](../artifacts/checks/caster-turning-live.json) passed all 12 checks over 1,353 joined samples with no errors. The pivot covered 6.39 rad with zero maximum observed axle drift. Arc endpoint displacement and signed yaw changes were:

| Arc | Displacement | Yaw change |
| --- | ---: | ---: |
| Left | 0.5115 m | +0.32375 rad |
| Right | 1.1351 m | −0.65080 rad |
| Return | 0.5811 m | +0.29580 rad |

The [Unity build log](../artifacts/logs/terrain-body-unity-build.log) records 48 passed checks. These results verify the experimental model and bounded maneuver execution. They do not measure tire forces, traction, real caster calibration or full suspension/contact dynamics; sampled zero drift is not a general guarantee for other terrain or commands.
