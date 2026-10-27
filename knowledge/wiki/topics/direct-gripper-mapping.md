# Direct hand-to-gripper mapping

Implemented under [approved revision 6](../plans/milestone-3-direct-gripper-mapping.md).
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

The default mode is `fingertip_correspondence`. A marker at
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

- `y = normalize(index_tip - thumb_tip)` — preserve the two-tip line.
- `v = thumb_MCP - wrist` — use the true wrist, with no lateral shift.
- `x = normalize(v - dot(v, y) * y)` and `z = x × y` — resolve twist.

Construct the gripper tip frame from its opening-dependent tip midpoint and
thumb-side→index-side marker line. Its forward axis is native palm +X projected
perpendicular to that line. With column-vector transforms,
`T_aligned_from_palm = T_aligned_from_grasp @ inverse(T_palm_from_tip_frame)`.
Consequently each gripper marker maps to its corresponding human fingertip.
`T_aligned_from_TCP = T_aligned_from_palm @ T_palm_from_TCP` retains the fixed URDF
reference, 0.160804 m along palm +X. That nominal TCP need not equal the tip center.
All positions use aligned metres; rotations are proper, without reflection.

Near-zero fingertip/forward vectors and near-collinear constructions are invalid;
thresholds live in [configuration](../../../configs/gripper_mapping.json). No gap
is filled. The [shared forward segment](../../../src/egocentric_pipeline/gripper_mapping.py)
drives the mapper and the displayed true-wrist→thumb-MCP construction line.

Earlier settings without `mapping_mode` retain the `landmark_frame` rule: MCP
closing direction, configurable forward direction/axis priority, fixed local TCP
corrections and clipped linear distance normalization. Revision 5 used a 0.025 m
thumbward wrist shift with forward priority; its prior settings and all earlier
trials remain reproducible. See [historical evidence](../experiments/direct-gripper-iphone.md)
for their measured results. They are not silently converted to exact-tip mapping.

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
| `opening_reachable` | Exact mode: `[T,2]` bool, observed finite distance within the selected branch |
| `gripper_tips_aligned_m`, `tip_error_m` | Exact mode: `[T,2,2,3]` marker positions and `[T,2,2]` Euclidean errors in metres, thumb then index; NaN when invalid |
| `tip_action_range`, `tip_distance_range_m` | Exact mode: `[2,2]`, per-hand lower/upper reachable branch bounds |

`gripper_mapping.npz`, `mapping_report.json`, `settings.json` and standalone
left/right URDFs are saved in a new output directory. Existing outputs are refused.
Older five- and six-landmark runs remain readable. Missing `forward_axis` means
wrist→thumb MCP; explicit thumb MCP→IP, index MCP→PIP and wrist→MCP-midpoint rules
retain their original behavior. Missing `orientation_priority` means closing
priority, and missing `wrist_thumb_offset_m` means zero shift. Nonzero shift is
supported only for the legacy MCP-midpoint forward rule. Current seven-point
landmarks retain thumb IP and index PIP for compatibility and display.
Reports record the source, asset revision/configuration, landmark convention and
per-hand missing/degenerate/unreachable counts, reachable ranges and tip errors. Licensed models and generated
geometry remain local inputs/evidence, outside Git.

The [viewer](../../../src/egocentric_pipeline/gripper_visualization.py) reconstructs
the same raw MANO meshes and checks their landmarks against the saved result.
Source RGB is decoded by original frame index. It initially selects the first
frame with both mappings available, while retaining every frame and missing-data
transition in the slider. Playback uses the saved timestamp differences.

Controls provide both-hand/individual closeups, per-side visibility, hand/gripper
opacity and landmark/axis overlays. In exact mode, small cyan spheres attach to
the articulated gripper tips and coincide with the pink/green human tip landmarks.
Readouts show separation, derived action and maximum tip error. Legacy opening,
wrist-shift and TCP-offset controls are hidden because changing them independently
would violate correspondence. Earlier runs retain their original tuning controls.
**Save mapping snapshot** writes all frames/settings into a new timestamped child
directory and refuses to overwrite an existing result.

**Manual grippers** pauses playback, seeds each available gripper from the current
mapped pose and enables independent position, rotation, opening and drag gizmos.
It is explicitly a preview: mapped output saving is disabled in this mode. Turning
it off restores the current hand-derived mapping. Missing hands/grippers stay
hidden during mapped playback; manual inspection can show a gripper without a hand.

See the [README commands](../../../README.md#direct-hand-to-gripper-review) and
[first-region acceptance evidence](../experiments/direct-gripper-iphone.md).
Thumb-IP/index-PIP center comparison, later regions and reintegration with IK
remain deferred. Physical scale/gravity, grasp/contact accuracy, collisions and
dynamics are unverified.
