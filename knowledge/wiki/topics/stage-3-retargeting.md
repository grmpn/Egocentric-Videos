# Stage 3 — Fixed-base trajectory preparation

Part 1 implemented and validated · 2026-10-14 · [Acceptance evidence](../experiments/gravity-alignment-bundled.md).
Part 2 implemented and validated · 2026-10-15 · [Acceptance evidence](../experiments/robot-workspace-purdue.md).
Part 3 implemented and validated · 2026-10-16 · [Acceptance evidence](../experiments/retargeting-bundled.md).
The user's [spec](../../../Stage-3-Spec.md), updated through Part 3 on 2026-10-16,
is preserved local input (untracked; unavailable in a fresh clone). This page owns
implemented contracts; the [approved Part 3 plan](../plans/milestone-3-part-3-placement-and-segmentation.md)
owns placement/segmentation scope and acceptance.
Stage 3 means roadmap Milestone 3; its three parts are the user's decomposition,
not HuRo's numbered stages. All three approved part plans are fulfilled within
their documented positional scope; dynamic simulation and physical execution are unverified.

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
| 2. Robot workspace | Separate left/right FK clouds → 2 cm occupancy grids → EDT signed-distance tensors → trilinear queries, with interactive 3D review. | Implemented; numerical and interactive acceptance complete. |
| 3. Placement and episode export | Camera segmentation → base XYZ/yaw fitting → expanded manipulation intervals, base-frame hands and positional IK playback. | Implemented; bundled numerical and interactive checks passed. |

Part 2 can be developed independently of human capture after its own approval.
Part 3 depends on both previous outputs. Use one fixed base placement throughout
each accepted episode; never optimize the base independently at every frame.
The updated spec explicitly requests XYZ translation and yaw. Part 3 uses
free Z without a calibrated floor constraint; this does not establish physical
pedestal placement.

## Target embodiment and later acceptance decisions

The specified asset source is
[purdue-alex-assets](https://github.com/PatrizioAcquadro/purdue-alex-assets).
Its [README at inspected revision `9ac4bd45`](https://github.com/PatrizioAcquadro/purdue-alex-assets/blob/9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b/README.md)
identifies Purdue Alex with SAKE EZGripper as the default fixed-base profile and
`assets/robots/alex_purdue/urdf/baseline/alex_purdue_full_convex.urdf` as its
canonical URDF. WSG32/UMI is opt-in. These are source claims from static inspection,
not simulation validation. Part 2 now loads the pinned URDF locally and verifies
batched against ordinary FK; no simulator is installed for this workflow.

Part 2 uses the base/TCP frames and positional sampling below. The
[Part 3 plan](../plans/milestone-3-part-3-placement-and-segmentation.md) owns
segmentation thresholds, validity handling, base optimization, interval
expansion and IK acceptance. Its direct wrist-to-TCP position mapping, missing-hand
rule and free-height placement were approved on 2026-10-16. Positional SDF
coverage and joint-limit-valid IK do not establish orientation reachability,
collision clearance or dynamic executability. Unchecked constraints remain
unverified. Preserve source timing and task coverage in the review evidence;
the bundled walking example does not establish semantic manipulation detection.

The [activity-mode reference](vlm-annotation-workflow.md#later-fixed-base-filtering)
provides a possible semantic input: manipulation cores, optional context expansion
under one base placement, and semantic task instructions. That hierarchy/mode
workflow is not implemented; Stage 3 does not implicitly authorize it.

## Joint base and pose trajectory contract

Implemented 2026-10-20 under the [approved extension](../plans/milestone-3-joint-base-optimization.md).
[README commands](../../../README.md#joint-base-and-wrist-pose-trajectory-fitting)
select this method or compare it with the existing workspace method. Numerical,
visual and timing acceptance is recorded in the [joint/base evidence](../experiments/joint-base-bundled.md).
The baseline contract below remains supported.

Both methods can now process only the retained camera-motion seeds, without
expansion. Joint fitting always uses these regions: one shared base XYZ/yaw and
sampled configurations of all 14 arm joints plus `NECK_Z`, `NECK_Y`. Fingers
remain zero. Base roll/pitch stay gravity-aligned; free height is not floor
calibration. Camera position is used for segmentation, base initialization and
diagnostic errors, with no translation loss. Initialization aligns the neutral robot camera-mount centre with the median
human camera centre, subtracting the rotated base-to-camera offset. Following the
user's median-initialization amendment, yaw uses `atan2` of the component-wise
median of normalized horizontal optical forward vectors. This avoids taking a
median of wrapped angles; it is a vector-component median, not a circular angular
median. Vertical/cancelling directions fail explicitly. Saved reports identify
the initialization rule; earlier mean-heading runs remain unchanged.

The human wrist matches `p_robot_wrist + R_base_from_tool @ [0.05, 0, 0]`:
5 cm toward the extended gripper fingers from `LEFT/RIGHT_WRIST_X_LINK`.
The offset is in tool coordinates and rotates with the gripper. It does not
translate the source hand geometry. The linear Jacobian includes the wrist
Jacobian plus angular velocity crossed with the rotated offset; all seven arm
joints can contribute. Physical robot wrist, shifted match point and actual TCP
are separately saved and labeled. Hand orientation matches the EZGripper
palm/TCP rotation at the shifted point. Earlier joint runs and the workspace
method retain their physical-wrist endpoint.

The pinned URDF gives each gripper one independent pitch joint downstream of
`WRIST_X_LINK`: `LEFT_GRIPPER_Y` / `RIGHT_GRIPPER_Y`, local axis `[0,1,0]`,
limits ±0.785398 rad (±45°), with no mimic coupling. The palm adapter and TCP
attachments are fixed. Changing this joint leaves the upstream wrist frame's
position and orientation unchanged, but moves the TCP and the rotating 5 cm
match point. A [2026-10-21 ordinary-FK check](../../../outputs/retargeting/iphone-no-infill-20261021/gripper-articulation-check.json)
held every other joint at zero and turned each gripper by 30°: wrist pose change
was zero, tool rotation was 30°, TCP displacement was 0.12284 m and match-point
displacement was 0.02588 m. Both joints are already active in joint/base fitting
and span approximately −45° to +45° in the saved iPhone rerun. This is model/FK
evidence, not hardware validation; the position-only wrist baseline keeps these
downstream joints at zero as described below.

Fixed MANO-root-from-palm rotations use
the zero-shape, neutral licensed models: X points wrist→middle MCP; Y points
pinky→index MCP after orthogonalization; Z is their cross product. Target tool
rotation is `R_aligned_from_MANO @ R_MANO_from_palm`. Left/right offsets differ;
finger articulation and observed geometry are never changed. This defines an
embodiment mapping, not a calibrated human/tool attachment.

`HEAD_ZED_X_MINI_LINK` is the nominal camera mount. Its X-forward/Y-left/Z-up axes
are converted to optical Z-forward/X-right/Y-down with
`R_mount_from_optical = [[0,0,1],[-1,0,0],[0,-1,0]]`, consistent with
[REP 103](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst)
and the [ZED image convention](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/coordinate-frames).
Tests verify these directions against ordinary URDF FK, including the mount's
0.3633-radian pitch. The optical origin uses the mount centre; lens-centre
calibration is unverified. Revision 4 removes the camera-position objective from
both stages; camera rotation remains fitted. Camera translation error remains
available as a diagnostic. Saved revision 3 runs retain their original objective
and viewer explanation.

The installed scikit-robot supplies batched FK and geometric Jacobians. Bounded
trust-region reflective optimization fits the combined residual, with a
[CUDA sparse solver](#gpu-sparse-solver) or the historical SciPy CPU reference.
Position residuals are in
metres; orientation residuals are rotation-matrix differences divided by
sqrt(2), with configurable radian scales. Acceptance uses geodesic angular
error, not the matrix residual. URDF bounds are hard constraints; neutral posture
is a soft cost. Shared-base fitting uses region-relative indices `0, 2, 4, ...`
(`base_frame_stride=2`), including 26 of 52 and 16 of 31 bundled frames. The
base then freezes. Source-time linear interpolation initializes all joint poses,
with endpoint hold when the final frame was unsampled; every original frame
enters the fixed-base velocity/acceleration and pose optimization. No source
observation is interpolated, and no retiming occurs. Reports save sampled indices
and full-resolution frame counts. `joint_solution_before_smoothing_rad` now
contains the interpolated seed: it can already be smoother than the final fit,
so acceleration improvement is not guaranteed and remains an acceptance gate.

`hand_position_weight` and `hand_orientation_weight` multiply the respective
scaled residuals, defaulting to 1.0. `neutral_weight` is 0.5 for all 16 joint
deviations. Squared-cost coefficients are the squares of these multipliers;
reported posture RMS is the unweighted deviation in radians. Acceptance uses
unweighted physical errors and is unchanged by these weights.
The [configuration](../../../configs/joint_retargeting.json) owns weights,
tolerances and finite evaluation budgets. On 2026-10-21 the user selected the
last hand-weight-1 experiment settings as defaults for the iPhone run; the
existing configuration already matched every setting (`20261021-iphone-001`
in the [action log](../logs/2026-10.jsonl)). Failed region fits can retry up to
three seeded starting postures. All attempts, termination messages and selection
are recorded; budget termination does not imply either pose failure or optimality.
IKPy and Robotics Toolbox were considered; their target-pose APIs do not remove
this shared-base/multiple-target/temporal objective. The original CPU implementation
added no dependency; the later CUDA backend is described below.

Since 2026-10-21, both retargeting methods use the per-hand observation mask
`retarget_valid = export_valid & ~motion_infilled`. Infilled hands are missing
data: they contribute no targets, observed errors, success claims, meshes or
paths. A directly estimated opposite hand remains eligible. All-missing frames
stay unknown and count toward the gap limit. Original source arrays retain their
dtype and bytes. Joint predictions may continue through gaps, labeled unobserved;
the workspace method leaves missing joints NaN. Missing or malformed boolean
`motion_infilled [T,2]` provenance rejects new inputs with regeneration guidance.

Version 5 joint reports identify this observation policy, `method: joint_base`,
the shifted endpoint and explicit `camera_position_objective: false`. Historical
joint versions 3–4, workspace versions 1–2 and TCP runs remain readable using
their original observation mask; the viewer labels that their fit may include
infill. New arrays include:

| Field | Contract |
| --- | --- |
| `retarget_valid` | `[T,2]` boolean eligible observations, in left/right order; distinct from preserved source validity. |
| `joint_solution_rad`, `joint_solution_before_smoothing_rad` | `[T,16]`, recorded left-arm/right-arm/neck order; NaN outside solved regions. |
| `joint_angles_rad`, `neck_joint_angles_rad` | `[T,2,7]` arms and `[T,2]` neck, including explicit failed/missing-hand predictions inside regions. |
| `joint_prediction`, `ik_success` | `[T,2]`: missing-observation prediction label / observed position **and** orientation acceptance. A prediction never establishes observed success. |
| `wrist_orientation_target_aligned`, `wrist_orientation_target_base`, `tool_orientation_base` | `[T,2,3,3]` proper rotations; target matrices are NaN for missing observations. |
| `rotation_mano_from_palm` | `[2,3,3]` fixed left/right orientation mappings. |
| `target_position_base_m`, `robot_wrist_position_base_m`, `tcp_position_base_m` | `[T,2,3]` shifted match point / physical robot wrist / actual TCP. Version 3 target positions remain physical wrists; the separate robot-wrist field is new in version 4. |
| `ik_residual_m`, `orientation_residual_rad` | `[T,2]` observed position/geodesic orientation error, NaN for missing observations. |
| `camera_position_base_m`, `camera_rotation_base_from_optical`, `camera_rotation_error_rad` | `[T,3]`, `[T,3,3]`, `[T]` saved head FK and angular residual. |
| `camera_position_error_m` | `[T]` Euclidean camera-centre error; NaN outside solved regions. Diagnostic in version 4, fitted in revision 3, absent in original rotation-only runs. |

Each report episode owns its unexpanded `region`, `pose` metrics and smoothing
result. Every available hand must pass 5 mm and 10°; unknown frames count toward
the gap limit and do not enter the observed denominator. Demonstration requires
**>95%** observed-frame coverage, ≤0.2 s gaps, ≥1 s duration and reduced acceleration
RMS. Rejected regions remain inspectable. The viewer displays head motion,
orientation axes/residuals, MANO and optional explicitly labeled unverified
robot poses; it never solves IK during playback. White marks the shifted match
point, pink the physical robot wrist and cyan the TCP in new runs. Camera position error is reported
separately from the wrist gate. Legacy rotation-only runs keep their original
viewer explanation and remain readable.

The comparison alternates three sequential runs of each production method using
identical seeds. Solver times include retries and both optimization stages;
loading, export and video generation are timed separately. Workspace construction
is reported from its historical build and is not rerun. Common pose errors,
failures, camera position/angle errors, unweighted posture deviation and finite
consecutive joint-motion statistics accompany timing; the
baseline has no orientation/head/smoothness objective, so this is a workflow
comparison rather than an isolated solver benchmark.

### GPU sparse solver

The 2026-10-22 [approved GPU plan](../plans/milestone-3-gpu-ik.md) adds
`solver_backend: "cuda"` to the default joint configuration. An explicit `cpu`
selects historical SciPy TRF/LSMR; configurations without the key remain CPU.
The CLI's `--solver-backend` overrides either setting. GPU setup is documented in
[environment/README.md](../../../environment/README.md#cuda-trajectory-ik).

[gpu_least_squares.py](../../../src/egocentric_pipeline/gpu_least_squares.py)
reuses SciPy 1.15.3's bound reflection, Coleman–Li scaling, two-dimensional trust
region, Jacobian scaling and termination helpers. Its limited driver is adapted
with the upstream BSD notice because SciPy's public optimizer does not accept a
custom sparse linear solver. CuPy assembles the scaled sparse normal matrix on
CUDA; NVIDIA cuDSS factors and solves it in float64. This replaces LSMR's
iterative subproblem. Existing scikit-robot FK, residuals, geometric Jacobians,
small trust-region operations and cuDSS symbolic planning remain on CPU. The
sample profile attributes 94%/98% of base/trajectory time to LSMR, which motivated
targeting this step rather than duplicating the inexpensive FK implementation.

Both backends minimize exactly the same objective and keep hard joint/base
bounds, residual-evaluation budgets, masks, timestamps and demonstration gates.
Direct normal equations square conditioning; each GPU solve checks a normalized
backward error (limit 1e-8) and finite results, with explicit failure rather than
silent fallback. This does not guarantee forward accuracy or the same local
optimum. Direct versus iterative steps and GPU floating-point ordering can change
termination, restart selection and final trajectories, including between repeats.

Per-stage reports identify backend, device, precision, linear-solve time/count
and maximum backward error; run reports record GPU package versions. Cold CUDA
initialization and kernel compilation are included in wall time. Timings compare
complete solver paths, including their different linear algorithms, rather than
isolating a GPU-versus-CPU hardware effect. Version 5 trajectory/viewer contracts
remain unchanged. The [iPhone evidence](../experiments/retargeting-iphone.md)
owns measured speed and quality results.

### Hand targets, base prior and adjacent regions

Implemented 2026-10-22 under the [approved refinement plan](../plans/milestone-3-hand-pose-refinement.md).
New configuration keys default to disabled behavior, including when omitted from
historical configurations. The installed SciPy 1.15.3 provides the filter and
coefficients; no dependency was added.

`hand_position_window_s` and `hand_orientation_window_s` independently enable
centred offline Savitzky–Golay filtering; zero disables either. Windows round to
the nearest odd number of samples (ties upward), which must exceed
`hand_filter_polyorder` (default 2). Enabled filtering requires uniform timestamps
(atol 1e-7 s, rtol 1e-5); disable both windows for irregular input. Each hand's
contiguous `retarget_valid` span inside a retained region is independent. A span
shorter than the requested window is unchanged and reported. XYZ uses SciPy
`mode="interp"`; endpoints evaluate a polynomial on the first/last full window.
For orientation sample i, filter local rotation vectors `log(R_i.T @ R_j)` with
SciPy coefficients at i, then compose `R_i @ exp(filtered vector)`. This avoids
global angle wraparound and quaternion sign ambiguity. Windows containing a
relative angle within 1e-6 rad of pi leave that sample unchanged and report it;
shorter windows may be necessary for such motion. Polynomial recovery is exact
for XYZ and fixed-axis angular polynomials; general noncommuting rotations are
an approximation. Negative coefficients can introduce overshoot. Filtering is
not evidence of more accurate reconstructed motion.

`merge_adjacent_regions` merges chains only after the existing duration filter,
with exact equality of previous stop and next start. Discarded intervals remain
gaps. `seeds` preserves the heuristic diagnostics; `regions` adds the fitted
intervals and contributing `seed_indices`. Initialization is recomputed over each
merged interval. Alternate-frame sampling restarts at its beginning, and the
first contributing seed index controls its RNG. Merging changes sampling parity
and restarts for later constituent intervals; comparisons must disclose this.

`base_initialization_weight` multiplies a four-component residual: XYZ offset
from median-camera initialization divided by `base_prior_translation_scale_m`,
and wrapped yaw offset divided by `base_prior_yaw_scale_rad`. Both scales default
to 1. The cost is half the squared residual norm. Zero weight omits the term.
It applies only during base fitting, with unchanged hard bounds and camera
rotation terms; fixed-base trajectory fitting has no prior. Each attempt reports
prior cost, translation drift and wrapped yaw drift. There is no per-frame
camera-position objective.

Report schema 6 preserves all existing fields and raw-observation semantics.
`wrist_position_filtered_aligned_m [T,2,3]` and
`wrist_orientation_filtered_aligned [T,2,3,3]` save separate fitting targets;
`filtered_ik_residual_m [T,2]` and `filtered_orientation_residual_rad [T,2]` save
errors against those targets. Ineligible observations remain NaN. Existing
residuals, success masks, restart pose-ranking and demonstration gates use the
**original** eligible observations. The viewer continues to display those raw
observations and saved robot poses. Both CPU and CUDA paths share this objective.

World-space hand smoothing can increase jitter when projected through unchanged
camera poses, because it disrupts shared camera/hand motion cancellation. See the
[frame-1050 diagnosis](../experiments/hand-pose-refinement.md#frame-1050-projection-jitter-diagnosis)
for measured evidence; world smoothness alone does not establish overlay fidelity.

## IK benchmark and gripper targets

Implemented under the [approved benchmark plan](../plans/milestone-3-ik-benchmark.md).
[README commands](../../../README.md#ik-benchmark-with-config-2-gripper-targets)
run an experiment and open its viewer. The [iPhone comparison and acceptance](../experiments/ik-benchmark-iphone.md)
verify this scope and preserve the remaining tracking, limit and collision failures.

`hand_target_mode: gripper_palm` consumes a full-source saved direct mapping;
all shared source fields must match the alignment before fitting. Actual robot
palm FK replaces the rotating wrist surrogate. The mapped palm's XYZ and SO(3)
orientation are filtered with the existing per-hand/span/region filter before
both stages. Raw mapped targets still own the historical demonstration gates
and restart ranking; the benchmark independently scores common filtered Config 2
targets. A direct-mapping failure excludes that target and is counted explicitly.

Schema 7 appends two opening leader angles to the existing 16 arm/neck variables:
left arm 0:7, right arm 7:14, neck 14:16, left/right opening 16:18. The pinned
asset command defines `angle = 1.30 * (1 - action)` radians, action 0 closed / 1
open. Each side's two independent leaders are tied to the same optimized angle;
ordinary URDF FK propagates their mimics. `coupled_joint_leaders` records the
second leader→optimized leader relationship; these joints are not locked.
Opening remains bounded to action [0,1] intersected with both leaders' URDF
bounds. Its neutral initialization is action 0.5. Only fixed-base fitting adds
the observed opening-angle residual, multiplied by `gripper_opening_weight` (20).
Base fitting retains posture regularization without an opening target.

`missing_hand_velocity_weight` (5 in the new config) multiplies extra source-time
joint-velocity residuals when the edge's destination has no target for that hand.
It covers that arm's seven joints and its opening, including entry into a gap;
the edge returning to an observed target is unconstrained by this extra term.
Neck columns are always zero. Weight zero disables the term. Existing temporal
weights remain 1.0/0.5; both backends consume the same residual/Jacobian.

The [IK tuning plan](../plans/milestone-3-ik-tuning.md) adds optional second-stage
`velocity_limit_weight` and `acceleration_limit_weight` signed-hinge residuals:
zero inside a limit and proportional to excess outside it. They use the existing
source-time derivative operators, including nonuniform intervals. Velocity caps
come from the pinned URDF; `acceleration_limit_rad_s2` defaults to the same
10 rad/s² proxy as the benchmark, with optional named joint overrides. Limits
are reduced through coupled leaders and mimic multipliers. `motion_limit_margin`
in (0,1] optionally leaves headroom; it changes the fitting objective only. All
new weights default to zero, preserving earlier configurations.

`base_velocity_weight` and `base_acceleration_weight` optionally regularize the
sampled pose sequence during base fitting, using the sampled source timestamps.
Both default to zero. They address discontinuous joint branches before the base
is frozen; missing-hand and motion-limit penalties still belong only to stage two.

Optional `position_huber_m` applies isotropic vector Huber loss to each observed
hand's position error in both fitting stages. Zero retains squared error; a
positive cutoff uses SciPy's Huber cost and an exact transformed-residual
Jacobian shared by CPU/CUDA. This limits the influence of large target jumps
without discarding observations or modifying saved errors and benchmark scoring.

Optional `position_deadzone_m` and `orientation_deadzone_rad` define fitting
tolerances (default zero). Hand tracking residuals are zero inside those radii
and measure radial excess outside. Rotation uses the equivalent chordal-matrix
radius `2 sqrt(2) sin(angle/2)`; camera orientation remains unchanged. Position
Huber loss, if enabled, applies to the excess after its fitting tolerance.
Saved errors and benchmark thresholds still use the original complete targets.

Optional `position_cauchy_m` and `orientation_cauchy_rad` apply vector Cauchy
loss to the corresponding hand pose blocks after fitting deadzones. Zero keeps
the existing objective. Cutoffs use metres and the angular cutoff's chordal
radius, respectively. All observations outside a fitting deadzone still exert
influence, including large errors. Camera, opening, temporal, motion-limit and
base-prior residuals are unchanged. An exact residual Jacobian is shared by CPU
and CUDA. Position Huber and Cauchy are mutually exclusive. Saved errors and
benchmark thresholds are independent of these fitting losses.

`refine_base_with_trajectory: true` allows the second stage to adjust the shared
base alongside the source-timed joint trajectory and gripper opening. The default
still freezes it. Refinement retains the original camera-seed bounds and prior;
it does not recenter the permitted box around the first fitted base. For report
compatibility, second-stage timing remains under `fixed_base_trajectory`, with
`base_refined` recording whether the base was free.

CUDA linear solving retains its symbolic cuDSS plan while the normal matrix's
CSR shape, row pointers and column indices are unchanged. Values and the RHS
are updated in-place and numerically refactorized every iteration; any structural
change rebuilds the plan. Solver reports include the number of symbolic plans.
Backward-error checks remain active on every solve, and GPU resources are freed
on both return and error. This reduces host work without changing constraints.

Optional `base_placement_method: sdf` replaces movable-base pose fitting with the
original seeded SDF search over XYZ/yaw. It requires a separately sampled actual
palm workspace matching the robot, rather than using the historical wrist grid.
The search consumes filtered palm positions and retains the camera-centred
translation/yaw bounds and base prior. Its camera term uses the neutral head;
neck and hand orientation are fitted in subsequent fixed-base pose initialization
and full trajectory optimization, not certified by the positional SDF. Placement
runs once per region; its time is included once across all pose retries. Legacy
`joint` base fitting and unrestricted positional placement remain available.

Source geometry is unchanged. `hand_position_target_aligned_m` saves raw fitting
positions; historical `wrist_*filtered*` and orientation-target field names now
hold palm targets in this mode. `wrist_position_base_m` still means the actual
human wrist for MANO reconstruction. Physical robot wrist, palm match point and
TCP remain separate. `gripper_action_target` / `gripper_action` are [T,2] in
left/right order; predictions through missing observations remain labeled.

As of the 2026-10-30 amendment, benchmark `region_limit: 1` selects the first
retained manipulation region **after** adjacent-region merging, before target
filtering or either solve stage. The general retargeting API defaults to all
regions; its optional `region_limit` is recorded in the trajectory report.
Original source arrays keep their full length and timestamps; unsolved frames
have episode -1 and NaN joint solutions. Scoring applies the same selection to
existing full-length runs, including tracking, motion, limits, collisions,
opening, per-joint diagnostics and invalid-mapping counts. The original iPhone
benchmark used [0,296), with 990 excluded source frames. The user-reviewed
restart uses [0,269), excluding only right-hand frame 29, configured in
[`ik_benchmark_reviewed.json`](../../../configs/ik_benchmark_reviewed.json).
Benchmark `selection.frame_range` uses zero-based half-open source indices;
`excluded_hand_frames` names individual source frames and left/right hands.
The shared selection runs before smoothing, base fitting, trajectory fitting
and scoring. Original arrays remain intact; `retarget_valid` records reviewed
eligibility. The trajectory report records `benchmark_selection`; mismatched
solve/scoring selections or masks are rejected. Use
`--benchmark-config configs/ik_benchmark_reviewed.json --benchmark-directory outputs/ik-benchmark-reviewed`
with the existing benchmark command. Old scores remain in their original directory.

The [benchmark evaluator](../../../src/egocentric_pipeline/ik_benchmark.py) uses
ordinary full-robot FK, independently of saved solver errors. Each tracking score
is 25 times the fraction of observed hand samples passing ≤0.01 m or ≤4°;
joint feasibility and collision-free scores use all selected frames. Failed or
absent robot predictions fail. Empty denominators yield no total, never a free
pass. Source frames outside the shared regions are disclosed. Different source,
mapping settings, robot, regions or scoring definitions cannot share ranked scores.

All 24 physical revolute joints, including mimics, enter limit checks and joint
motion statistics. Speed is a source-time first difference; acceleration is the
difference of interval velocities divided by their midpoint separation. Every
frame checks both incident speeds; endpoint acceleration uses its nearest
interior estimate. Derivatives never cross region gaps. Position bounds allow
1e-9 rad numerical tolerance. RMS/P95 motion uses interval samples, absolute P95;
error medians/P95 use finite observed predictions, with nonfinite counts exposed.
Scores retain failures in their denominators. The 10 rad/s² cap is an explicit
[benchmark assumption](../decisions/ik-benchmark-limits.md).

Collision evaluation reuses scikit-robot's URDF mesh query through trimesh and
new pinned `python-fcl==0.7.0.11`; no simulator is needed. Exclusions cover the
same rigid assembly, adjacent assemblies and the asset's documented convex pairs.
Every excluded pair/reason is saved. No random-pose-derived exclusions are added.
This checks sampled self-intersection, including fingers, without establishing
inter-frame clearance, scene contact or dynamic execution.

Each experiment retains settings, trajectory/report/video, original/filtered
targets, full-joint/frame metrics, collisions and solver attempts under
`outputs/ik-benchmark/`. For tuning, `benchmark_ik.py --skip-video` omits annotated
video export while preserving trajectories, scoring and interactive viewer inputs;
the choice is recorded in `experiment.json`. The default still exports video.

`REPORT.md` is regenerated from preserved experiment and
score records after successes or failures. Its timing sums saved solver durations
for both stages and every retry in the selected region(s), excluding setup/export
and between-solve overhead. Whole-run timing remains in the trajectory report.
It links complete raw-error, opening and per-joint diagnostics. The viewer labels
unverified poses, shows opening/filtered target axes and reads benchmark checks
without solving IK; saved poses outside the evaluation mask are explicitly
labeled as excluded. Previous full-video scores remain linked from the
[comparison evidence](../experiments/ik-benchmark-iphone.md).

## Part 3 placement and IK contract

Implemented 2026-10-16; wrist endpoint amendment implemented 2026-10-20.
[README](../../../README.md#stage-3-part-3-fixed-base-placement-and-positional-ik)
owns run/view commands. The [configuration](../../../configs/trajectory_retargeting.json)
owns adjustable numerical thresholds and search effort. The workflow consumes
completed Part 1 and Part 2 reports/arrays, verifies the prepared RGB/source
timeline and pinned robot assets, and creates a new output directory.

Frame intervals are zero-based **[start, stop)**. Each frame owns time until the
next timestamp; the final support interval uses median dt. Camera smoothing is
Gaussian with default sigma 0.05 s and nearest edge handling; it affects only seed
segmentation and requires uniform prepared timestamps. Threshold comparisons use
XY displacement from each seed's first smoothed camera position. Once a crossing
lasts 0.3 s, its first frame closes that seed, and the following frame starts the
next. Seeds shorter than 1 s, including tails, remain recorded as discarded.

Placement uses physical aligned wrists and each hand's own sampled SDF.
SciPy differential evolution searches XYZ/yaw with a reproducible seed, finite
bounds derived from wrists/workspace extent, and a recorded evaluation budget.
The integer nonpassing-frame count dominates bounded distance/depth tie breakers.
Out-of-domain distances guide search only through a positive penalty and never
pass the actual query test. A stopped iteration budget is a search outcome, not
a global-optimality claim. Free base Z has no calibrated floor interpretation.

A frame is observed if either hand has `retarget_valid`; every observed hand must
meet `distance <= -0.03 m`. Missing hands stay unverified, with all-missing frames
unknown and excluded from the percentage denominator. Unknown frames count toward
the nonpassing gap limit. Observation coverage is reported separately; an empty
denominator cannot pass. All frames are evaluated under each candidate transform.
Expansion selects the longest qualifying contiguous interval containing the seed,
with earlier-start tie breaking. Long nonpassing runs bound the endpoint search.
Overlaps prioritize duration, then observed count, then earlier seed. The longest
qualifying unassigned remainder intersecting a later seed is retained only after
all criteria are checked again; rejected alternatives stay in the report.

IK matches the workspace's recorded `target_frames` to physical human wrists.
The default targets are `LEFT_WRIST_X_LINK` and `RIGHT_WRIST_X_LINK`: the distal
wrist flexion joint origins. Their positions depend on the first five arm joints;
`WRIST_X` and downstream `GRIPPER_Y` stay at zero. All seven angles are exported.
The same targets define workspace sampling, SDF placement and IK residuals.
Settings without `target_frames` retain the historical EZGripper TCP convention.
Each arm starts at zero,
then uses its previous successful solution, with bounded, seeded random restarts
on failure. Other joints stay locked at zero. Every stored success passes finite
URDF position bounds and ordinary-FK error at most 5 mm. Failed or missing joint
samples remain NaN; no gap interpolation or retiming occurs. Adjacent successful
joint changes above 0.5 rad are reported, without asserting dynamic feasibility.
Successive episodes are independent placements; their base/joint changes are not
an executable transition. SDF, IK and their simultaneous intersection each receive
separate coverage/gap checks; demonstrated episodes pass all three.

The preview replays these saved per-frame joint angles with live viewer IK
disabled; it performs no new solve or trajectory optimization. A 2026-10-20
[FK diagnosis](../../../outputs/retargeting/wrist-alignment-20261020/diagnosis.json)
replayed all 240 successful bundled arm samples: TCP-to-human-wrist error remained
at most **0.152 mm**, while the `LEFT/RIGHT_WRIST_X_LINK` joint origins were about
**23.8 cm** from the human wrists. This measured the historical TCP convention,
not a large positional solver residual. Unconstrained tool orientation can also
make the robot gripper and original hand point differently. The
[wrist-alignment amendment](../plans/milestone-3-wrist-alignment.md) changes both
workspace and IK endpoints. Existing TCP outputs remain readable and unchanged;
new wrist runs require regenerated wrist workspaces and placement/IK.
The diagnostic artifact is local-only.

`trajectory_retargeted.npz` preserves every Part 1 array, dtype and byte. For
`T` frames and `C` fitted candidates, additions include:

| Fields | Contract |
| --- | --- |
| `retarget_valid` | `[T,2]` boolean `export_valid & ~motion_infilled`; original validity and geometry remain intact. |
| `camera_position_smoothed_m` | `[T,3]` aligned-frame seed signal; original cameras unchanged. |
| `transform_base_from_aligned`, `transform_base_from_world`, `transform_aligned_from_base` | `[C,4,4]` float64 homogeneous transforms acting on column vectors. World transform composes Part 1 rotation; no rescaling. |
| `candidate_distance_m`, `candidate_query_valid`, `candidate_hand_passed` | `[C,T,2]` signed metres / booleans, left then right. Distances NaN for missing/out-of-domain samples. |
| `candidate_frame_passed` | `[C,T]` available-hand SDF result for every video frame. |
| `episode_id` | `[T]` integer; `-1` means unassigned. Report maps episode to candidate and interval. |
| `wrist_position_base_m` | `[T,2,3]` physical human wrist targets in episode-base metres. Missing/unassigned geometry is NaN. |
| `target_position_base_m`, `tcp_position_base_m` | `[T,2,3]` successful FK of configured robot endpoint / actual gripper TCP, in episode-base metres. Failed/missing/unassigned samples are NaN. Only the first is compared with human wrists for IK residuals. |
| `joint_angles_rad`, `ik_success`, `ik_residual_m`, `ik_attempts` | `[T,2,7]` joints in recorded chain order; `[T,2]` success, metre error and solve counts. Failed joints/residuals are NaN. |
| `joint_step_rad`, `joint_jump` | `[T,2]` maximum absolute adjacent joint change / threshold flag, computed only within episodes with consecutive successes. |

`retargeting_report.json` schema 3 records the observation policy, target frames, locked zero joints,
source directories, model/settings/packages,
transform conventions, all seeds/candidates/episodes, timing and video verification.
A completed run can have `demo_accepted: false`; CLI exit code 2 preserves its
diagnostics. Existing outputs are refused. The annotated video preserves prepared
frame count/FPS and labels missing data, SDF/IK failures and large joint changes.
The viewer animates only verified arm samples, hides missing/failed arms, and
shows the fixed base, full wrist/camera paths and current seed/episode boundaries.
Neither the display nor the workspace heuristic detects semantic manipulation.
Schema 1 TCP runs remain readable: they have no separate target-position array,
so the viewer uses their original TCP array as the target and labels it accordingly.
New wrist runs missing target positions are rejected.

The MANO comparison reconstructs the **original world-frame** translation,
orientation, articulation and shape with the same SMPL-X evaluator and left-hand
shape correction as Part 1. Each episode's `transform_base_from_world` moves all
778 vertices into its base frame. The viewer attaches them beneath the base scene
node, whose `transform_aligned_from_base` places both robot and meshes in the
shared aligned scene. No extra wrist offset, rotation matching, scaling or
gripper deformation is applied. Reconstructed physical wrists must agree with
saved base-frame targets within **10 µm** (float32 geometry consistency, not an
accuracy claim). Meshes are reconstructed in memory; saved trajectories stay intact.

Blue/orange means left/right. The **MANO meshes** toggle and **MANO opacity**
slider control the overlay. White markers show verified robot wrist positions;
cyan markers show actual gripper TCPs. Legacy runs show white TCP targets.
A valid original mesh survives IK failure; missing
hands and frames without a retained base are hidden. Original hand orientations
can differ from robot tools because IK constrains only position. Asset paths
default to the alignment report; `--mano-models LEFT RIGHT` relocates licensed
inputs and `--no-mano` supports review without them. The
[environment instructions](../../../environment/README.md#robot-workspace-environment)
own dependencies; [acceptance evidence](../experiments/retargeting-bundled.md#original-mano-mesh-comparison)
owns geometry and visual checks.

## Part 2 workspace contract

**Implemented and validated.** The
[approved plan](../plans/milestone-3-part-2-robot-workspace.md) and
[wrist amendment](../plans/milestone-3-wrist-alignment.md) own scope and acceptance.
The original Part 2 user spec requests 100,000–1,000,000 FK samples; the user
authorized extending the comparison to 5 million and 10 million per arm on
2026-10-15 (plan revision 2), then selected **10 million samples per arm as the
preferred default**, also the supported maximum. The
[density comparison](../experiments/robot-workspace-purdue.md#density-extension-5m-and-10m-per-arm)
records the supporting coverage and runtime evidence. The workflow supplies
separate left/right occupancy at 2 cm spacing, Euclidean distance transforms and
interpolated SDF queries, movable-camera point/voxel views,
and verification of base-coordinate to voxel-index conversion.

Static inspection on 2026-10-15 of the [canonical URDF at `9ac4bd45`](https://github.com/PatrizioAcquadro/purdue-alex-assets/blob/9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b/assets/robots/alex_purdue/urdf/baseline/alex_purdue_full_convex.urdf)
found root `PEDESTAL_LINK`, a fixed torso attachment, seven bounded revolute joints
per arm (shoulder Y/X/Z, elbow Y, wrist Z/X, gripper Y), and fixed
`LEFT_EZGRIPPER_TCP_LINK` / `RIGHT_EZGRIPPER_TCP_LINK` tool frames. The
original workspaces used these TCP origins with the pedestal fixed and other
movable joints at zero. Since 2026-10-20 the default `target_frames` select
`LEFT/RIGHT_WRIST_X_LINK` origins; `tool_frames` still identify the actual TCPs
and full arm chains. The first five joints influence these wrist positions;
the remaining two stay at zero. Sampling draws the same seeded seven-angle
configurations as before, then zeros those last two entries and evaluates the
wrist endpoint. Thus upstream sample configurations are preserved. Reports record
the actual target, active joints and locked joints. Legacy settings lacking
`target_frames` continue to describe TCP occupancy. The actual model and both FK
paths have been exercised.

Implemented grid convention: one common lattice aligned to the base axes, with
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

The implementation reuses these library capabilities:

- [Scikit-robot reachability maps](https://scikit-robot.readthedocs.io/en/latest/examples_guide/reachability_map.html)
  document seeded sampling, NumPy batch FK, position-only mode and voxel maps.
  This workflow uses its lower-level position-only NumPy batch FK. The high-level
  map adds unused manipulability work and separate unpadded origins; NumPy
  indexing constructs the required common lattice without a new FK engine.
- [SciPy EDT](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.distance_transform_edt.html)
  supports per-axis metric spacing. NumPy/SciPy already have project version pins.
- [PyTorch `grid_sample`](https://docs.pytorch.org/docs/2.10/generated/torch.nn.functional.grid_sample.html)
  uses trilinear interpolation for 5D input with `mode="bilinear"`; axis ordering,
  `align_corners` and out-of-bounds behavior are explicitly handled below.
- [Scikit-robot viewers](https://scikit-robot.readthedocs.io/en/latest/reference/viewers.html)
  provide interactive camera controls. The implementation uses Viser for robot,
  points and voxel cells. Point display
  reduction preserves full saved workspace data; all occupied voxels are available.

The [README](../../../README.md#stage-3-part-2-robot-workspace) owns build commands;
[environment setup](../../../environment/README.md#robot-workspace-environment)
owns installation. The [viewer](../../../src/egocentric_pipeline/workspace_visualization.py)
loads completed exports and the same verified robot revision, holds the robot
at its zero reference pose, and offers separate left/right point and voxel layers.
Point display can be reduced; voxel display uses all occupied cells with LOD off.
The [acceptance page](../experiments/robot-workspace-purdue.md) owns measured results,
screenshots and remaining sampling/physical limitations. New run directories contain:

| Artifact | Contract |
| --- | --- |
| `samples_left.npz`, `samples_right.npz` | Float64 `positions_base_m [N,3]`, `joint_angles_rad [N,7]`, ordered `joint_names [7]`; independent `held_out_positions_base_m` and `held_out_joint_angles_rad`. |
| `workspace_grid.npz` | Float64 `origin_m [3]`, scalar `spacing_m`, boolean `occupancy [2,X,Y,Z]`, float64 `distance_m [2,X,Y,Z]`; explicit `axis_order` and `hand_order`. |
| `workspace_report.json` | Completion/failure, pinned asset and actual package versions, settings, limits/locked joints, FK checks, reload/query evidence, prefix coverage, timing and process peak RSS. |

Use `np.load(..., allow_pickle=False)` for samples and
`WorkspaceGrid.load` from [workspace.py](../../../src/egocentric_pipeline/workspace.py)
for the grid. `indices(points)` returns `[N,3]` integer indices and validity,
with `-1` for invalid rows. `contains(points)` returns `[N,2]` occupancy plus
validity; an out-of-grid false value must not be interpreted as tested infeasibility.
`centers(indices)` returns base-frame metres. Grid cells use a half-open domain.

`query(torch_points)` accepts float32/64 `[N,3]` and returns `[N,2]` distances
plus `[N]` validity, retaining gradients with respect to points. Its domain is the
closed box between outermost cell centers. Values outside it or at nonfinite
inputs are NaN with false validity. Tensor storage is permuted to `[1,2,Z,Y,X]`,
normalized query coordinates remain XYZ, and `align_corners=True` maps extreme
centers to ±1. Interpolated signs can differ from voxel membership near cell
boundaries; no claim of an exact Euclidean SDF or certified reachability is made.

Sampling uses independent NumPy SeedSequence streams `[seed, hand_index, 0]`;
held-out samples use `[seed, hand_index, 1]`. The 100k subset of a million-sample
run shares its lattice and random prefix, allowing a direct density comparison.
All sampled configurations are retained as FK witnesses, but neither voxel volume
nor joint-space sampling frequency measures complete physical workspace coverage.

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
