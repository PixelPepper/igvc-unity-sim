# R3-a geometry and frame review

**Physical orientation correction, 2026-09-09:** the user confirmed the big driven wheels are the front and the casters are the rear. The tables below describe the original export frame, whose +X pointed toward the casters. They are historical source measurements, not the current canonical forward convention. The normalized description rotates every link basis 180 degrees about Z and swaps left/right names to match physical sides, while retaining unchanged mesh files through visual-origin rotations. Canonical drive joints are at positive X, casters at negative X, and `base_footprint -> base_link` is `(-0.25591,0,0.30385548)`. See provenance.json for the simultaneous name map. Do not reintroduce the original export's forward assumption.

Read-only analysis of original `C:/Users/brand/Downloads/OneDrive_2026-03-04/R3-a (Spring 2025)/R3-a URDF/urdf/R3-a URDF.urdf`, mesh bounds in `artifacts/checks/robot-audit.json`, and two original binary STLs. Numbers assume metres; physical dimensions, tire compression and CAD export accuracy remain uncalibrated. No source URDF or simulation assets changed.

## Canonical topology and transforms

`base_link` is the sole root. All four joints attach directly to it; all joint RPY and visual/collision origins are zero. Therefore zero-angle base-space mesh bounds equal local mesh bounds plus the joint translation, without additional mesh scale or rotation. Preserve these exact link and joint names:

| Joint | Child link | Parent-frame XYZ (m) | ROS axis |
|---|---|---|---|
| rightWheel | wheel_right | (-0.25591, -0.40526, -0.07445) | (0,-1,0) |
| leftWheel | wheel_left | (-0.25591, +0.40525, -0.07445) | (0,+1,0) |
| rightCaster | right_caster | (+0.52775, -0.24612, -0.03635) | (0,0,+1) |
| leftCaster | left_caster | (+0.52775, +0.24612, -0.03635) | (0,0,+1) |

All are continuous joints. The caster meshes combine fork and wheel into one link with a swivel joint only: no caster wheel rolling joint exists. Do not invent articulation while claiming a faithful import. Drive-joint effort/velocity limits are export values (10,10), not validated motor limits.

## Computed bounds and contact

| Link | Base-space minimum XYZ (m) | Maximum XYZ (m) |
|---|---|---|
| base_link | (-0.339382,-0.377823,-0.131493) | (+0.579818,+0.377823,+0.820000) |
| wheel_left | (-0.485432,+0.329697,-0.303855) | (-0.026388,+0.476993,+0.154955) |
| wheel_right | (-0.485432,-0.477003,-0.303855) | (-0.026388,-0.329707,+0.154955) |
| left_caster | (+0.470600,+0.187192,-0.287003) | (+0.673800,+0.307842,-0.030000) |
| right_caster | (+0.470600,-0.305048,-0.287003) | (+0.673800,-0.184398,-0.030000) |

Drive track from joint origins: **0.81051 m**. Wheel diameter bounds: X=0.4590440 m, Z=0.4588110 m; radius candidates 0.2295220 and 0.2294055 m. Direct scan of all 29,544 left-wheel STL triangles gives maximum radius about its Y axis `max hypot(x,z)=0.229569608 m`. Use approximately **0.22957 m** only as CAD radius, pending rolling-radius calibration. Tire total local Y extent is 0.147296 m; do not confuse axle width with tread width.

Level, zero-angle wheel contact requires base origin world height `0.07445+0.2294054776 = 0.3038554776 m`. At that height the base mesh minimum clears the plane by **0.172362014 m**, its maximum is 1.123855470 m, and caster minimum is **0.016852360 m above ground**. Thus all wheels do not share an exact contact plane in the rigid exported pose. Do not silently translate individual links or assume four-wheel support; resolve pitch/contact geometry or suspension only with physical evidence. A small rendering-only lift may prevent z-fighting but is not calibration.

Zero-angle full projected AABB: X=[-0.485432,+0.673800], Y=[-0.477003,+0.476993], length **1.159232 m**, width **0.953996 m**. Base mesh alone projects to 0.919200×0.755646 m. These are conservative bounding rectangles, not a measured collision hull. Casters can sweep beyond the zero-angle X maximum; a conservative caster XY local radius from bounding-box corners is `sqrt(0.1460501²+0.0617221²)<0.15856 m`, giving overall X maximum below 0.68631 m for arbitrary swivel. Wheels still dominate total Y extent. Add clearance margin separately.

## Forward direction and wheel signs

Left/right names agree with ROS +Y/-Y. Caster pivots sit 0.78366 m ahead of the driven axle in +X, so **+X is the canonical forward candidate**. Geometry alone does not prove operator-facing physical forward: wheel/caster placement and the zero-angle caster trail do not establish intent. Confirm using a labeled photograph or actual commanded motion before hardware control.

For rolling toward ROS +X, angular velocity about +Y is positive: at ground contact `omega × (0,0,-r)` is negative X, canceling translational velocity. Consequently `leftWheel` position/velocity is positive and `rightWheel` negative for straight forward travel. With desired drive-axle forward speed v, yaw rate w, track b and radius r: `qdot_left=(v-w*b/2)/r`, `qdot_right=-(v+w*b/2)/r`. A shared positive sign is incorrect for these original joint axes.

The base origin is **0.25591 m ahead of the drive axle**, not located at its midpoint. For axle lateral velocity zero, ROS base-link lateral velocity is `w*0.25591`; account for the rigid offset when assigning odometry/twist or introducing `base_footprint`. Do not treat the original base origin as an axle-centered differential-drive frame.

## Exact ROS FLU to Unity RUF conversion

Use `C=[[0,-1,0],[0,0,1],[1,0,0]]`, det(C)=-1. Points and linear vectors map `(x,y,z)->(-y,z,x)`, inverse `(X,Y,Z)->(Z,-X,Y)`. Apply once to vertices and once to each local translation; do not additionally rotate the root to compensate. Positive ROS X becomes Unity Z, positive ROS Y Unity negative X, positive ROS Z Unity Y.

Rotations: `R_U=C*R_R*C^T`. Quaternion XYZW may be mapped `(qx,qy,qz,qw)->(qy,-qz,-qx,qw)`. Its equivalent global-negative quaternion `(-qy,qz,qx,-qw)` matches pinned connector `Runtime/ROSGeometry/CoordinateSpaces.cs:35–42`. Convert URDF RPY by forming `Rz(yaw)*Ry(pitch)*Rx(roll)` first; do not directly reorder Unity Euler angles.

Angular vectors are axial: `omega_U=det(C)*C*omega_R=-C*omega_R`. To retain the original scalar joint angle in Unity quaternion construction, transform the rotational axis by **-C**, not C: leftWheel -> Unity +X, rightWheel -> Unity -X, both caster axes -> Unity -Y. Alternatively use C(axis) and negate the angle, but never both corrections. Positive ROS yaw produces negative Unity Y rotation.

Mesh reflection changes orientation. Transform positions with C and normals with normalized C*n (inverse transpose for a general transform). Reverse each triangle's second/third index once so its geometric cross-product normal agrees with transformed normals: `(Ca)×(Cb)=det(C) C(a×b)`. Direct STL check: all 29,544 left-wheel and all 114,806 left-caster nondegenerate face normals agree with original triangle cross products, none oppose. Recalculate bounds; preserve imported normals or recalculate after the winding correction. If a mesh loader already performs reflection/winding conversion, do not repeat it. Validate an exterior face with backface culling enabled; do not mask incorrect orientation using double-sided materials. If tangents are generated, account for the handedness flip in tangent.w.

For future physical import, mass is invariant and inertia transforms `I_U=C I_R C^T`; Unity principal-axis representation needs eigen-decomposition. Original mass total is 96.8552188 kg but inertia/mass export validity is unproven. Detailed visual triangle meshes should not automatically become dynamic convex colliders.
