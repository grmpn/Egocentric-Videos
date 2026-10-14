# Stage 3 — Fixed-base trajectory preparation

Part 1 approved for implementation · 2026-10-14 · Acceptance pending.
The user's [original spec](../../../Stage-3-Spec.md) remains unchanged local input
(untracked; unavailable in a fresh clone). This page preserves its planning content.
Stage 3 means roadmap Milestone 3; its three parts are the user's decomposition,
not HuRo's numbered stages. The [Part 1 plan](../plans/milestone-3-part-1-gravity-alignment.md)
is the only scope approved for implementation.

## Repository role and sequence

The requested Stage 3 output is hand trajectories expressed in the robot base
frame and verified against the target robot's kinematic limits. The target is
fixed-base; mobile-base behavior is deferred. The user explicitly authorized
starting this planning before the iPhone demonstrations are recorded. Milestone 2
remains incomplete under its [approved plan](../plans/milestone-2-lerobot-pilot.md).

This revises this repository's role relative to the older
[roadmap](../../raw/Project-Milestones-and-Timeline.md), which described a complete
gripper/end-effector simulation demo. The raw roadmap is preserved; simulation,
controller ownership and any additional export remain decisions for later parts.
The current request does not authorize real-robot execution.

| Part | Intended result | Current boundary |
| --- | --- | --- |
| 1. Gravity alignment | World hand/camera trajectories → estimated up → one Z-up trajectory frame. | Approved plan; bundled example is the acceptance input. |
| 2. Robot workspace | Forward-kinematics (FK) samples → reachable-position point cloud → SDF, voxels, or mesh for workspace queries. | Planning only; representation and validation remain open. |
| 3. Placement and episode export | Gravity-aligned trajectories + workspace → optimized base position/yaw → valid manipulation intervals and base-frame hand trajectories. | Planning only; final feasibility criteria must be agreed. |

Part 2 can be developed independently of human capture after its own approval.
Part 3 depends on both previous outputs. Use one fixed base placement throughout
each accepted episode; never optimize the base independently at every frame.
The spec leaves translation dimensionality and pedestal/floor constraints open.

## Target embodiment and later acceptance decisions

The specified asset source is
[purdue-alex-assets](https://github.com/PatrizioAcquadro/purdue-alex-assets).
Its [README at inspected revision `9ac4bd45`](https://github.com/PatrizioAcquadro/purdue-alex-assets/blob/9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b/README.md)
identifies Purdue Alex with SAKE EZGripper as the default fixed-base profile and
`assets/robots/alex_purdue/urdf/baseline/alex_purdue_full_convex.urdf` as its
canonical URDF. WSG32/UMI is opt-in. These are source claims from static inspection,
not a local robot-model validation; no robot assets or simulator were installed.

Before approving Parts 2–3, resolve:

- Base/tool frames, hand-to-tool pose mapping, active arms/joints, locked torso or
  other joints, and sourced joint bounds. Positional FK coverage alone cannot
  establish orientation reachability or simultaneous bimanual feasibility.
- Workspace approximation resolution and false-positive checks against the
  kinematic model. A signed-distance representation needs an explicit occupancy/
  boundary convention; a point cloud alone does not define a reliable solid.
- A continuous inverse-kinematics (IK) witness or equivalent verification for
  accepted trajectories. Agree which position, orientation, joint, velocity,
  acceleration and collision constraints apply, which limits are available, and
  whether timing changes are allowed. Pointwise membership cannot certify these.
  Unchecked limits must remain unverified rather than receiving a blanket pass.
- Manipulation interval selection, minimum useful task coverage, infeasible-frame
  handling and the eventual base-frame export contract. Preserve source timing,
  hand identity, validity and the world/aligned/base transform chain. Do not trim
  task-essential motion simply to obtain a feasible interval.

The [activity-mode reference](vlm-annotation-workflow.md#later-fixed-base-filtering)
provides a possible semantic input: manipulation cores, optional context expansion
under one base placement, and semantic task instructions. That hierarchy/mode
workflow is not implemented; Stage 3 does not implicitly authorize it.

## Part 1 estimator reference

Static source inspection on 2026-10-14 used HuRo revision
[`aeaae17f`](https://github.com/3587jjh/HuRo/tree/aeaae17f0fd51cc325b030bbef79ceb68a25199e),
its [camera-extrinsics stage](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/stage5_annot_extrinsics.py)
and [MAD helper](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/common/stats.py).
No inference was run. The relevant external behavior is:

1. Rank grayscale Laplacian variance; select the sharpest 30%, with a minimum of
   50 frames capped by available frames. Use pinhole GeoCalib with a focal prior.
2. Retain downward-looking predictions (`pitch < 0`) with `|roll| ≤ 10°`. Map each
   predicted up vector by its matching camera-to-world rotation before aggregation.
3. Require at least three world estimates; align their signs to the first estimate's
   hemisphere. This can propagate an incorrect first sign, so preserve sign flips
   and check visible vertical cues instead of treating agreement as ground truth.
4. Compute component-wise median absolute deviations (MAD), scaled by 1.4826 with
   a `1e-8` floor. Below five samples use the median directly; otherwise reject a
   row if any component exceeds the threshold: 4 for 5–6 samples, 3.5 for 7–9,
   3 for 10+. Take the retained component-wise median and normalize it.

HuRo falls back to the unfiltered median when every row is rejected. The Part 1
proposal instead reports failure for that case or fewer than three final inliers;
it must not present rejected evidence as a successful estimate. Retain the small-
sample path explicitly in diagnostics. HuRo's windowed SLAM, smoothing and scale
estimation are outside this adoption; reuse the project's existing camera poses.

## Proposed frame and geometry conventions

Names below define the proposed mathematical contract, not an existing schema.
`W` is HaWoR's clip-local world, `C_i` the matching OpenCV camera, and `A` the
new aligned frame. Column-vector transforms map source coordinates to destination.

GeoCalib's [gravity class at HuRo's pinned revision](https://github.com/cvg/GeoCalib/blob/747054d743ca64bf4b0055c26ab709fa6d234996/geocalib/gravity.py)
returns `(0, −1, 0)` at zero roll/pitch. In OpenCV's Y-down camera that is **up**;
HuRo uses it as `u_C`, not physical downward gravity. Thus
`u_W_i = R_W_from_C_i @ u_C_i`. The normalized robust aggregate is `u_W`;
downward gravity direction is `−u_W`. Camera translation does not act on a direction.

The spec's “same 90 degree rotation” needs a reference axis: a single fixed
90° rotation cannot make every possible 3D vector perpendicular to itself.
Proposed deterministic rule, without fitting X to SLAM X:

```text
z = u_W
r = world X, or world Y when abs(dot(world X, z)) > 0.9
x = normalize(cross(r, z))
y = cross(z, x)
R_A_from_W = stack_rows(x, y, z)
```

This is a right-handed orthonormal basis with arbitrary reproducible yaw. It is
computed once per clip, including the fallback; no per-frame axis switching.
The aligned origin remains the world origin. For geometric points and poses:

```text
p_A = R_A_from_W @ p_W
R_A_from_C_i = R_A_from_W @ R_W_from_C_i
t_A_from_C_i = R_A_from_W @ t_W_from_C_i
u_A = (0, 0, 1); downward gravity in A = (0, 0, -1)
inverse rotation = R_A_from_W.T
```

Physical hand joint positions and root orientations follow the same rigid rotation.
However, the current [hand export](lerobot-pipeline.md#dataset-contract) stores
**MANO translation parameters**, not wrist coordinates. HaWoR's
[`cam2world_convert`](../../../external/HaWoR/lib/eval_utils/custom_utils.py)
transforms the reconstructed root joint and reapplies the MANO offset. A new
alignment must respect that distinction; simply rotating the translation
parameter can move reconstructed geometry incorrectly. Verify against reconstructed
wrist/joints or vertices, keeping local articulation and shape unchanged.

The same source's `load_slam_cam` supplies camera-to-world rotation from native
quaternions in (`x,y,z,w`) order and translation multiplied by saved
scale; the inverse world-to-camera translation is different. Use exact prepared
frame indices to pair RGB, cameras and hands. Existing world and per-hand
canonical representations stay intact; the new frame is shared by both hands.

## Deliverable and evidence boundaries

The [Part 1 plan](../plans/milestone-3-part-1-gravity-alignment.md#acceptance) owns
acceptance. Recommended evidence combines the spec's original/aligned 3D graph
with a reloadable export/transform, synthetic known-direction checks, rigid
geometry invariants, per-frame estimation diagnostics and image-space vertical
cues. Rotating the estimated vector to Z proves transform consistency, not the
estimator's physical accuracy. There is no measured gravity reference for the
bundled example; angular dispersion and visual review must be labeled accordingly.

The existing completed 121-frame bundled run is recorded in the
[desktop setup evidence](../../../environment/README.md#native-desktop-and-annotation-environments).
Its camera/export artifacts are candidates for reuse, not freshly revalidated
acceptance. The run's focal length is an assumption and scale remains unverified.
Gravity alignment cannot repair those uncertainties, recover heading/floor height,
or establish robot reachability. The iPhone recording and later robot checks
remain separate deliverables.
