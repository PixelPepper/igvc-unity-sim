# Reference lessons for procedural AutoNav courses

## Source identity and evidence

The supplied [2026 design report](http://www.igvc.org/design/2026/5.pdf) is the University of Oklahoma/Sooner Competitive Robotics report for **Suspended Disbelief**, submitted May 15, 2026. It describes proposed architecture and team-reported testing before that competition; it does not establish a 2026 winning result. Page references below use the report's printed numbering (PDF page = printed page + 2).

The supplied [video](https://www.youtube.com/watch?v=7tZsk3T3STA) is titled **IGVC AutoNav 2023 First Place Run (2:19)**, by Sooner Competitive Robotics. YouTube metadata and its description were retrieved. The description identifies external footage, raw camera imagery, an obstacle view, and particle-filter position/speed/heading plots. Video frames/playback were not reviewed, so no measured course geometry or obstacle dimensions are inferred from it. This is a different year and robot from the 2026 report.

The PDF was retrieved over its original HTTP URL; its HTTPS counterpart failed. Text was extracted and the perception page visually inspected. Local reference: `artifacts/checks/2026-team5-report.pdf`.

## Findings from the 2026 report

- Pages 8 and 10: two calibrated forward-facing global-shutter cameras; AutoNav uses ground-plane perspective projection, while Self Drive additionally uses stereo depth. No numerical camera mounting pitch is specified.
- Pages 10–11: HSV lane segmentation and filtering feed a 5 cm occupancy grid with obstacle inflation. AutoNav obstacle classification uses non-pavement appearance.
- Pages 10 and 15: potholes follow the lane-processing/projection pipeline and are represented as circular occupied regions. No pothole-specific color threshold, physical dimensions, depth estimator, or negative-terrain reconstruction is documented. Figure 5.1 shows lane classifications, not potholes.
- Pages 13–14: local targets combine lane information and waypoint influence; one visible boundary supports offset following. A* and Pure Pursuit handle navigation, with speed reductions for curvature, obstacles and incline.
- Page 17: configurable layouts, lighting and obstacle placement support repeatable scenarios; recorded overlays and occupancy grids support diagnosis.

These are report claims, not independently reproduced performance measurements. The report's swerve drivetrain and Self Drive lane-change behaviors must not be assumed available on R3-a.

## Adaptations for this simulator

The following are project choices inferred from those ideas and the user's procedural-course request, not claims about the reference implementation.

1. **Seeded course variants:** vary curvature, barrels and barricades within a configured lane width while checking full swept-footprint clearance and preserving a connected route. Keep seed, generation settings and validation results with each run. The supplied top-down schematic is a layout reference, not a surveyed metric map or permission to invent rule dimensions.
2. **Separate pothole fixtures:** occasional dark bowls can exercise a camera-ground-hazard path. Their color, radius and depth must be explicit generator parameters. A dark patch detector is a synthetic appearance heuristic; shadows, asphalt repairs and actual depressions require separate validation. A raised planar lidar may miss depressions, so do not create an invisible lidar obstacle to make the test pass.
3. **Configurable downward camera pitch:** start with the project's proposed 10° downward setting and retain synchronized CameraInfo/acquisition-time TF. This angle is ours. Compare near-ground coverage and far-lane visibility against the level baseline; a lower-image mask may need pitch-aware validation. A single ground plane remains inaccurate on slopes and inside bowls.
4. **Keep perception separate from generator truth:** publish camera-derived lane and hazard observations into independently expiring obstacle layers. Use generator geometry only for scoring, clearance checks and debugging; it must not supply runtime detections.
5. **Repeatable visual tests:** include shadows, gray road, orange/white barrels, barricade stripes, faint paint, curves and partially visible boundaries. Save RGB, masks, projected points and the driven trajectory together. Count false hazards and missed hazards separately from lane detection.
6. **Retain smooth local navigation:** preserve the existing rolling horizon and bounded recovery. Evaluate additional seeds with completion, minimum clearance, speed distribution, perception freshness and intervention counts, rather than tuning only for the successful imported course.

This document does not establish 2027 compliance, general pothole perception, physical suspension behavior or successful validation of newly generated variants.
