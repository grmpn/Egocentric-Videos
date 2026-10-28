# Direct hand-to-gripper mapping

Implemented under [approved revision 10](../plans/milestone-3-direct-gripper-mapping.md).
This workflow reuses the existing iPhone reconstruction/alignment, MANO evaluator,
Purdue assets and Viser stack. It computes gripper poses directly; it does not fit
an arm/base, solve IK or apply the earlier target filters.

## Geometry and opening

The [gripper model](../../../src/egocentric_pipeline/gripper_model.py) extracts each
palm-rooted subtree from the pinned canonical Purdue URDF. Each standalone URDF
contains the palm, four finger links and nominal TCP, with the original mesh
geometry, joint bounds and mimic relationships. Generated mesh references point
to the local pinned assets; source files are unchanged. The asset's
`alex_purdue_ezgripper_targets` helper commands both leader joints to
`1.30 * (1 - action)` radians; scikit-robot propagates the two mimics. This is the
existing nominal kinematic opening rule, not a physical contact simulation.

[Landmark reconstruction and mapping](../../../src/egocentric_pipeline/gripper_mapping.py)
use the original aligned MANO root poses, articulation and shape. The physical
wrist is joint 0, index MCP/PIP are joints 1/2, and thumb MCP is joint **14**, not the
thumb CMC at joint 13. The thumb chain is 13/14/15 (CMC/MCP/IP). This interpretation
matches the [manopth native-to-21-joint ordering](https://github.com/hassony2/manopth/blob/master/manopth/manolayer.py)
and [named 21-joint convention](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/python/solutions/hands.py).
Fingertips use the installed SMPL-X MANO vertex definitions: thumb 744 and index
320, on both hands. These are mesh landmarks, not separate regressed tip joints.

The default mode is `mcp_plane`. A marker at
**[0.057395, 0, 0.009680] m** in each distal (L2) link is the center of the mesh's
most distal edge (maximum local X). This is an explicit nominal tip definition,
not a calibrated pad contact. Finger **2 maps to the thumb**, finger **1 to the
index**, on both hands; their uncrossed difference follows native palm +Y.

First solve the existing scalar opening command so the FK tip separation equals
the human fingertip separation. The pinned mechanism's markers cross slightly at
command 0 and reach maximum separation before command 1. Use the uncrossed,
increasing-separation branch: commands approximately **0.001741–0.947485**, spanning
**0–0.280114 m**. This preserves the original command convention; it does not
renormalize the branch. Out-of-range separation invalidates the mapping; there is
no clipping or model scaling. The earlier fitted opening anchors are superseded
for this trial. Right frames 92 and 119 now command **0.063020 / 0.327544**.

The human grasp frame has origin `h = (thumb_tip + index_tip) / 2` and axes:

- `y = normalize(index_MCP - thumb_MCP)` — preserve the MCP jaw line.
- `v = index_PIP - index_MCP` — choose the forward sign toward index PIP.
- `x = normalize(v - dot(v, y) * y)` and `z = x × y`.

The +X/+Y directions span the plane through thumb MCP, index MCP and index PIP.
The origin stays at the human fingertip midpoint; the wrist does not set the axes.

Construct the gripper tip frame from its opening-dependent tip midpoint and
thumb-side→index-side marker line. Its forward axis is native palm +X projected
perpendicular to that line. With column-vector transforms,
`T_aligned_from_palm = T_aligned_from_grasp @ inverse(T_palm_from_tip_frame)`.
Consequently the gripper tip midpoint matches the human fingertip midpoint, and
its jaw line follows the MCP line. The opening still matches fingertip distance;
individual gripper tips generally differ from human tips because the two lines
need not be parallel. These offsets are measured, not treated as a failed center
constraint.
`T_aligned_from_TCP = T_aligned_from_palm @ T_palm_from_TCP` retains the fixed URDF
reference, 0.160804 m along palm +X. That nominal TCP need not equal the tip center.
All positions use aligned metres; rotations are proper, without reflection.

Near-zero fingertip/forward vectors and near-collinear constructions are invalid;
thresholds live in [configuration](../../../configs/gripper_mapping.json). No gap
is filled. The [shared forward segment](../../../src/egocentric_pipeline/gripper_mapping.py)
drives the mapper and displayed index-MCP→PIP construction line. A translucent
triangle shows the three points defining the orientation plane.

## Comparison configurations

The default remains `mcp_plane` until the user selects a method.
[Config 1](../../../configs/gripper_thumb_ip_plane.json), `thumb_ip_plane`, uses
the index MCP/index PIP/thumb IP plane. Its +Y points **index MCP→thumb IP**;
+X projects index MCP→index PIP perpendicular to +Y, toward PIP; +Z = +X × +Y.
It retains the opening-dependent tip-midpoint placement and opening above.
This deliberately reverses the general jaw direction relative to the baseline's
thumb→index direction. Tip-offset diagnostics retain finger 2→thumb / finger
1→index labels; they do not minimize distance over swapped tip assignments.

[Config 2](../../../configs/gripper_wrist_roll.json), `wrist_roll`, puts the
gripper **rear palm origin** at the physical hand wrist, with no translational
offset. Its current `forward_axis: wrist_to_tip_midpoint` makes +X normalized
wrist→midpoint(thumbtip,index tip). Missing `forward_axis` preserves the earlier
wrist→MCP-midpoint rule; explicit `wrist_to_mcp_midpoint` also selects it. +Y projects
thumb MCP→index MCP perpendicular to +X, and +Z = +X × +Y. This preserves
forward exactly and lets the MCP line determine roll. Here the human grasp
transform is the palm transform; the fixed TCP follows from ordinary FK.
Opening still matches fingertip distance, but fingertip-midpoint placement is
not a constraint. Tip offsets therefore measure both orientation and attachment.

Config 2's zero-roll reference is the same MANO model/shape/root pose evaluated
with identity local joint rotations. The installed `MANOLayer` matrix interface
does not add a pose mean, so this is the ideal open hand, not the learned mean
articulation. Construct open forward using the same selected midpoint rule and
projected MCP jaw axes, then apply the
shortest rotation taking open forward to current forward. If its transported
jaw axis is `y0`, current jaw is `y`, and current forward is `x`, signed roll is
`atan2(dot(x,cross(y0,y)), dot(y0,y))`, in [-π,π]. Applying that X rotation to
the zero-roll frame reproduces the mapped palm. Whole-hand motion carries the
reference with it; left/right can have opposite signed roll. The scalar wraps
at ±π without changing the rotation matrix. Degenerate reference axes and
near-antiparallel forward directions are invalid, using the axis thresholds.
No frame interpolation, physical calibration or artificial 90° gain is applied.

[Config 3](../../../configs/gripper_roll_blend.json), `roll_blend`, combines the
two plane orientations using the signed MCP roll from updated Config 2, with
its fingertip-forward reference. Both endpoints use fingertip-midpoint placement
and the same FK opening. As explicitly approved, the Config 1 endpoint is first
right-multiplied by `diag(1,-1,-1)`: +X stays fixed and +Y/+Z reverse. Its jaw
then points thumb side→index side, avoiding the near-half-turn between the
original directed conventions. This changes the Config 1 endpoint orientation
and finger assignment inside Config 3; it does not alter the standalone result
or assume that every gripper surface is symmetric.

Let `u = clip((abs(roll_degrees)-low)/(high-low), 0, 1)`, and original weight
`w = u²(3-2u)`. Defaults are **low=30°, high=45°**; require finite
`0 ≤ low < high ≤ 180°`. The output rotation is the shortest SO(3) interpolation
`R_open * Exp(w * Log(R_open.T * R_original))`, implemented with SciPy `Rotation`.
It equals aligned Config 1 below low and the original above high; weight and
its slope are continuous at both thresholds. This is per-frame pose-dependent
blending, not temporal smoothing. Source jitter and steep changes in measured
roll can still cause visible motion. Both planes and the roll reference must be
valid, even at endpoint weights; there is no fallback across undefined geometry.
The viewer exposes both thresholds, signed roll, original weight, both construction
planes and the final axes. Invalid threshold edits keep the last valid preview
and disable saving; reset restores the loaded settings and snapshots retain tuning.

[Config 4](../../../configs/gripper_thumb_point_blend.json), `thumb_point_blend`,
uses the same roll measurement and smoothstep thresholds as Config 3, but blends
a landmark before constructing axes. With MCP weight `w`, the thumb point is
`q = (1-w)*thumb_IP + w*thumb_MCP`. Set `y = normalize(q-index_MCP)`, project
`index_PIP-index_MCP` perpendicular to `y` for +X, then +Z=X×Y. The plane passes
through index MCP, index PIP and `q`; FK retains fingertip midpoint and separation.
At weight 0 it exactly matches standalone Config 1. At weight 1 it uses the
original plane with Y/Z reversed, as required by the user's index→thumb jaw
choice. It does not inherit Config 3's endpoint jaw reversal. Consequently the
fixed finger 2→thumb / finger 1→index error labels can report large assigned-tip
offsets even when the unordered fingertip geometry looks close. No relabeling or
orientation sign guessing occurs. Undefined interpolated planes remain invalid.
The viewer displays this triangle and jaw segment, signed roll and MCP weight;
its thresholds, reset and snapshots work as for Config 3.

All modes use original observations, units, timestamps and opening limits.
The [latest comparison evidence](../experiments/direct-gripper-iphone.md#full-video-configs-234-2026-10-28)
owns measured results, viewer links and remaining selection work.

## Historical mappings

Earlier `fingertip_correspondence` runs remain exact: +Y uses thumbtip→index tip,
+X projects true wrist→thumb MCP, and the same opening-dependent placement maps
each tip individually. Revision 7 intentionally changes the orientation constraint
while preserving opening and midpoint placement.

Earlier settings without `mapping_mode` retain the `landmark_frame` rule: MCP
closing direction, configurable forward direction/axis priority, fixed local TCP
corrections and clipped linear distance normalization. Revision 5 used a 0.025 m
thumbward wrist shift with forward priority; its prior settings and all earlier
trials remain reproducible. See [historical evidence](../experiments/direct-gripper-iphone.md)
for their measured results. They are not silently converted to the current plane mapping.

## Input/output and review

The preparation CLI consumes a completed alignment directory and a half-open
source frame interval. `export_valid & ~motion_infilled` defines eligible hands.
Original frame indices, clip/source timestamps, left/right order and selected
MANO/provenance fields are copied without alteration. Saved arrays include:

| Field | Contract |
| --- | --- |
| `landmarks_aligned_m` | `[T,2,7,3]`, wrist/thumb MCP/index MCP/thumbtip/index tip/thumb IP (joint 15)/index PIP (joint 2), NaN for missing/infilled observations |
| `observation_valid`, `mapping_valid` | `[T,2]` bool; the second additionally rejects invalid geometry |
| `transform_aligned_from_grasp`, `transform_aligned_from_tcp`, `transform_aligned_from_palm` | `[T,2,4,4]` rigid transforms; entire matrix NaN when mapping-invalid |
| `transform_palm_from_tcp` | `[2,4,4]` fixed nominal URDF reference |
| `fingertip_distance_m`, `gripper_action` | `[T,2]`; action is NaN when mapping-invalid; distance can remain available for a degenerate orientation |
| `opening_reachable` | Geometry-derived opening modes: `[T,2]` bool, observed finite distance within the selected branch |
| `gripper_tips_aligned_m`, `tip_error_m` | Geometry-derived opening modes: `[T,2,2,3]` marker positions and `[T,2,2]` Euclidean tip offsets in metres, thumb then index; expected nonzero in plane mode; NaN when invalid |
| `tip_action_range`, `tip_distance_range_m` | Geometry-derived opening modes: `[2,2]`, per-hand lower/upper reachable branch bounds |
| `open_hand_landmarks_aligned_m` | Roll modes: `[T,2,N,3]`, N=3 or 5: ideal-open wrist/thumb MCP/index MCP, plus thumb/index tips for fingertip-forward, in aligned metres; missing NaN |
| `zero_roll_rotation_aligned` | Roll modes: `[T,2,3,3]`, aligned-from-zero-roll basis at measurement forward, NaN where mapping-invalid; in Config 3 this measures roll, not the blended orientation |
| `gripper_roll_rad` | Roll modes: `[T,2]`, signed MCP-line roll about measurement forward relative to that basis, [-π,π], invalid NaN |
| `blend_original_weight` | Config 3: `[T,2]`, original weight in [0,1]; 0 means aligned Config 1, invalid NaN |
| `thumb_mcp_weight` | Config 4: `[T,2]`, interpolation weight in [0,1], 0=thumb IP, 1=thumb MCP; invalid NaN |
| `interpolated_thumb_aligned_m` | Config 4: `[T,2,3]`, interpolated plane point in aligned metres; invalid NaN |
| `blend_endpoint_angle_rad` | Config 3: `[T,2]`, shortest rotation angle between aligned endpoint frames, invalid NaN |

`gripper_mapping.npz`, `mapping_report.json`, `settings.json` and standalone
left/right URDFs are saved in a new output directory. Existing outputs are refused.
Older five- and six-landmark runs remain readable. Missing `forward_axis` means
wrist→thumb MCP; explicit thumb MCP→IP, index MCP→PIP and wrist→MCP-midpoint rules
retain their original behavior. Missing `orientation_priority` means closing
priority, and missing `wrist_thumb_offset_m` means zero shift. Nonzero shift is
supported only for the legacy MCP-midpoint forward rule. Current seven-point
landmarks retain thumb IP and index PIP for compatibility and display.
Reports record the source, asset revision/configuration, landmark convention and
per-hand missing/degenerate/unreachable counts, reachable ranges, tip offsets and
maximum tip-midpoint or wrist-anchor error and roll range. Licensed models and generated geometry remain local
inputs/evidence, outside Git.

The [viewer](../../../src/egocentric_pipeline/gripper_visualization.py) reconstructs
the same raw MANO meshes and checks their landmarks against the saved result.
Source RGB is decoded by original frame index. It initially selects the first
frame with both mappings available, while retaining every frame and missing-data
transition in the slider. Playback uses the saved timestamp differences.

Controls provide both-hand/individual closeups, per-side visibility, hand/gripper
opacity and landmark/axis overlays. Small cyan spheres attach to the articulated
gripper tips. Plane modes display their selected three-landmark triangle and
reports midpoint error separately from individual tip offsets; exact-tip mode
retains coincident tip markers and its original error readout. Wrist-roll mode
shows wrist-anchor error, signed roll and tip offsets. Config 3 shows signed
measurement roll, original weight, midpoint error and both endpoint planes.
The longer thin axes at
the wrist show zero roll; shorter axes show the mapped palm. Method names
distinguish comparison windows. Legacy opening,
wrist-shift and TCP-offset controls remain hidden for geometry-derived modes.
Earlier landmark-frame runs retain their original tuning controls.
**Save mapping snapshot** writes all frames/settings into a new timestamped child
directory and refuses to overwrite an existing result.

**Manual grippers** pauses playback, seeds each available gripper from the current
mapped pose and enables independent position, rotation, opening and drag gizmos.
It is explicitly a preview: mapped output saving is disabled in this mode. Turning
it off restores the current hand-derived mapping. Missing hands/grippers stay
hidden during mapped playback; manual inspection can show a gripper without a hand.

See the [README commands](../../../README.md#direct-hand-to-gripper-review) and
[first-region acceptance evidence](../experiments/direct-gripper-iphone.md).
Configs 2/3/4 now cover the full iPhone recording. Default selection, alternative
position targets and reintegration with IK remain deferred. Physical scale/gravity, grasp/contact accuracy, collisions and
dynamics are unverified.

## Saved RGB overlays

[render_gripper_overlay.py](../../../scripts/render_gripper_overlay.py) consumes a
saved mapping and writes a new MP4 plus a JSON validation report. It reuses the
alignment's original pinhole intrinsics and per-frame aligned-from-camera poses;
CV camera axes (+X right, +Y down, +Z forward) become OpenGL (+X right, +Y up,
−Z forward) with `diag(1,-1,-1)`. Gripper meshes follow ordinary FK and the saved
TCP poses/openings. Installed **pyrender 0.1.50** (already a scikit-robot dependency,
now explicitly pinned) supplies EGL mesh rasterization and depth testing;
FFmpeg decodes/encodes the source at its original dimensions and frame rate.
No custom rasterizer or new package installation was needed.

Left/right meshes are blue/orange at default opacity 0.7. Invalid mappings are
hidden and labeled. The top banner identifies method, original frame/time and
hand availability. Meshes depth-test against each other, but there is no real
scene-depth occlusion. Physical contact and reconstruction accuracy are not
established by this visualization. The output covers every selected frame,
including gaps; timestamps start at zero for a selected interval. Frame count,
dimensions, frame rate, timestamps and full decoding are verified before the
completion report is written. Existing outputs are refused.
