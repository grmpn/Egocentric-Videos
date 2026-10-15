# Stage 3 — Fixed-base trajectory preparation

Part 1 implemented and validated · 2026-10-14 · [Acceptance evidence](../experiments/gravity-alignment-bundled.md).
Part 2 spec reviewed and [draft plan](../plans/milestone-3-part-2-robot-workspace.md) added · 2026-10-15.
The user's [spec](../../../Stage-3-Spec.md), updated for Part 2, is preserved local input
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
| 1. Gravity alignment | World hand/camera trajectories → estimated up → one Z-up trajectory frame. | Implemented; bundled-example acceptance complete. |
| 2. Robot workspace | Separate left/right FK clouds → 2 cm occupancy grids → EDT signed-distance tensors → trilinear queries, with interactive 3D review. | Draft revision 1; not approved or implemented. |
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

Part 2 proposes base/TCP frames and positional sampling below. Before approving
Part 3, resolve:

- Base/tool frames, hand-to-tool pose mapping, active arms/joints, locked torso or
  other joints, and sourced joint bounds. Positional FK coverage alone cannot
  establish orientation reachability or simultaneous bimanual feasibility.
- How the Part 2 sampled approximation supports placement and how candidate
  positions receive actual feasibility checks; voxel membership alone is insufficient.
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

## Part 2 proposed workspace contract

**Planning only.** The [draft plan](../plans/milestone-3-part-2-robot-workspace.md)
owns proposed scope and acceptance. The updated user spec requests 100,000–1,000,000
FK samples, separate left/right occupancy at an initial 2 cm spacing, Euclidean
distance transforms and interpolated SDF queries, movable-camera point/voxel views,
and verification of base-coordinate to voxel-index conversion.

Static inspection on 2026-10-15 of the [canonical URDF at `9ac4bd45`](https://github.com/PatrizioAcquadro/purdue-alex-assets/blob/9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b/assets/robots/alex_purdue/urdf/baseline/alex_purdue_full_convex.urdf)
found root `PEDESTAL_LINK`, a fixed torso attachment, seven bounded revolute joints
per arm (shoulder Y/X/Z, elbow Y, wrist Z/X, gripper Y), and fixed
`LEFT_EZGRIPPER_TCP_LINK` / `RIGHT_EZGRIPPER_TCP_LINK` tool frames. Proposed
workspaces use these TCP origins with the pedestal fixed and other movable joints
at zero. These are asset-defined tool points, not calibrated human wrists; the
human-to-tool mapping remains Part 3 work. Runtime model loading/FK is unverified.

Proposed grid convention: one common lattice aligned to the base axes, with
separate hand occupancy arrays. Its stored origin is the lower cell corner
**expressed in the robot base frame**, not necessarily base coordinate zero;
negative coordinates must remain representable. Record spacing, dimensions and
axis order. Integer indices use floor; cell centers add half a voxel. Pad bounds
with empty cells. Occupancy means a cell contains an FK sample; it does not certify
every point in that cell or an attainable tool orientation. Keep holes visible.

For occupancy `O`, use `EDT(~O) - EDT(O)` with metric spacing: negative in sampled
occupied cells, positive outside. Distances are between lattice centers; the
trilinear zero surface is an approximation to the sampled boundary. Neither
sampling nor interpolation creates a certified solid reachable set. The query
contract must distinguish cell membership from the interpolation domain, report
invalid/out-of-domain inputs, and avoid treating tensor padding values as workspace
evidence. Position, axis order, voxel-center offsets and normalized tensor
coordinates need explicit conversion checks.

The dependency direction is supported by official documentation, not yet tested
in this project:

- [Scikit-robot reachability maps](https://scikit-robot.readthedocs.io/en/latest/examples_guide/reachability_map.html)
  document seeded sampling, NumPy batch FK, position-only mode and voxel maps.
  Reuse these where their frame/grid conventions fit; do not recreate an FK engine.
- [SciPy EDT](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.distance_transform_edt.html)
  supports per-axis metric spacing. NumPy/SciPy already have project version pins.
- [PyTorch `grid_sample`](https://docs.pytorch.org/docs/2.10/generated/torch.nn.functional.grid_sample.html)
  uses trilinear interpolation for 5D input with `mode="bilinear"`; axis ordering,
  `align_corners` and out-of-bounds behavior must be set explicitly.
- [Scikit-robot viewers](https://scikit-robot.readthedocs.io/en/latest/reference/viewers.html)
  provide interactive camera controls and a Viser browser option. Use one suitable
  viewer for robot, points and voxel cells; a separate Open3D dependency is not
  initially needed. Display reduction must preserve full saved workspace data.

## Part 1 estimator reference

Static source inspection on 2026-10-14 used HuRo revision
[`aeaae17f`](https://github.com/3587jjh/HuRo/tree/aeaae17f0fd51cc325b030bbef79ceb68a25199e),
its [camera-extrinsics stage](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/stage5_annot_extrinsics.py)
and [MAD helper](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/common/stats.py).
This source review was static; project execution is recorded separately in the
[acceptance evidence](../experiments/gravity-alignment-bundled.md). The relevant external behavior is:

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

HuRo falls back to the unfiltered median when every row is rejected. Our workflow
instead reports failure for that case or fewer than three final inliers;
it must not present rejected evidence as a successful estimate. Retain the small-
sample path explicitly in diagnostics. HuRo's windowed SLAM, smoothing and scale
estimation are outside this adoption; reuse the project's existing camera poses.

## Frame and geometry conventions

Names below define the implemented mathematical contract.
`W` is HaWoR's clip-local world, `C_i` the matching OpenCV camera, and `A` the
new aligned frame. Column-vector transforms map source coordinates to destination.

GeoCalib's [gravity class at HuRo's pinned revision](https://github.com/cvg/GeoCalib/blob/747054d743ca64bf4b0055c26ab709fa6d234996/geocalib/gravity.py)
returns `(0, −1, 0)` at zero roll/pitch. In OpenCV's Y-down camera that is **up**;
HuRo uses it as `u_C`, not physical downward gravity. Thus
`u_W_i = R_W_from_C_i @ u_C_i`. The normalized robust aggregate is `u_W`;
downward gravity direction is `−u_W`. Camera translation does not act on a direction.

The spec's “same 90 degree rotation” needs a reference axis: a single fixed
90° rotation cannot make every possible 3D vector perpendicular to itself.
Implemented deterministic rule, without fitting X to SLAM X:

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
alignment respects that distinction: for the rest root `J(beta)`, the new MANO
translation is `R_A_from_W @ (translation_W + J) - J`. Local articulation and shape
stay unchanged. Every valid frame's reconstructed joints/vertices are checked
against the rigidly rotated originals before acceptance.

The same source's `load_slam_cam` supplies camera-to-world rotation from native
quaternions in (`x,y,z,w`) order and translation multiplied by saved
scale; the inverse world-to-camera translation is different. Use exact prepared
frame indices to pair RGB, cameras and hands. Existing world and per-hand
canonical representations stay intact; the new frame is shared by both hands.

## Implemented Part 1 export

[README](../../../README.md#stage-3-part-1-gravity-alignment) owns the command;
[environment setup](../../../environment/README.md#gravity-alignment-environment)
owns dependencies/model installation. The workflow reads a verified completed run
through the shared [world loader](../../../src/egocentric_pipeline/world_export.py),
then estimates, transforms, saves/reloads, checks and plots into a new directory.
It does not update LeRobot features or annotations.

`trajectory_aligned.npz` copies every source world field byte-for-byte, including
invalid entries and exact clip/source timestamps. Added fields are:

| Fields | Shape / meaning |
| --- | --- |
| `root_translation_aligned_m`, `root_orientation_aligned_axis_angle` | `[T,2,3]` float32 corrected MANO translation and root axis-angle; radians, left/right order. |
| `wrist_position_world_m`, `wrist_position_aligned_m`, `mano_root_offset_m` | `[T,2,3]` float32 physical wrists and model rest root `J(beta)`; metres. |
| `camera_rotation_{world,aligned}_from_camera` | `[T,3,3]` float64 camera-to-frame matrices. |
| `camera_position_{world,aligned}_m` | `[T,3]` float64 camera origins; existing HaWoR scale applied once. |
| `rotation_aligned_from_world`, `rotation_world_from_aligned`, `up_world` | Two `[3,3]` float64 inverse rotations and one `[3]` unit UP direction; origin unchanged. |

Derived hand geometry is NaN wherever `export_valid` is false. Missing hands are
not assigned an invented pose; original confidence and infill masks remain intact.
World and aligned camera poses cover every prepared frame. Native `tstamp` indexes
SLAM keyframes, not the dense `traj` array; it is not used as the full timeline.
Model geometry uses SMPL-X 0.1.28 with HaWoR's left-hand shapedirs correction.

`alignment_report.json` records status, source identities, units/frames, full
settings, packages, transform and numerical checks. `gravity_diagnostics.json`
records sharpness, selected frames, pose rejection, sign changes, MAD decisions
and pre/post-filter angular residuals. The separate visual review records findings;
an automatically completed report does not imply measured physical accuracy.
Use `np.load(..., allow_pickle=False)` and read the report when consuming exports.

## Deliverable and evidence boundaries

The [Part 1 plan](../plans/milestone-3-part-1-gravity-alignment.md#acceptance) owns
acceptance. Saved evidence combines the spec's original/aligned 3D graph
with a reloadable export/transform, synthetic known-direction checks, rigid
geometry invariants, per-frame estimation diagnostics and image-space vertical
cues. Rotating the estimated vector to Z proves transform consistency, not the
estimator's physical accuracy. There is no measured gravity reference for the
bundled example; angular dispersion and visual review must be labeled accordingly.

The original completed 121-frame bundled HaWoR run is recorded in the
[desktop setup evidence](../../../environment/README.md#native-desktop-and-annotation-environments).
Its camera/export artifacts were verified and reused for Part 1. The run's focal
length is an assumption and scale remains unverified. Final estimator support is
clustered in frames 77–96; whole-clip vertical previews expose that limitation.
Gravity alignment cannot repair those uncertainties, recover heading/floor height,
or establish robot reachability. The iPhone recording and later robot checks
remain separate deliverables.
