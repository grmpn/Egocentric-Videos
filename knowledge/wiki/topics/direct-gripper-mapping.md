# Direct hand-to-gripper mapping

Implemented under [approved revision 5](../plans/milestone-3-direct-gripper-mapping.md).
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

The human grasp frame has its origin at the fingertip midpoint. Define the raw
closing direction `c = normalize(index_MCP - thumb_MCP)`. Shift the wrist
construction point to `w_shifted = wrist - wrist_thumb_offset_m * c`, initially
**0.025 m** toward the thumb. This hand-relative shift uses index→thumb on both
hands; it is not a global leftward translation or a change to the MANO wrist.

With `orientation_priority: forward`, +X is exactly the normalized direction from
`w_shifted` to midpoint(thumb MCP, index MCP). Project the raw closing direction
perpendicular to +X and normalize for +Y; +Z = +X × +Y. The user explicitly chose
this priority because preserving the old closing axis would remove the lateral
shift during orthogonalization. The grasp center and opening rule are unchanged.

Both hands use this rule without a reflection or temporal sign flip. Near-zero
axes or near-collinearity invalidate the mapping; thresholds and shift distance
live in [configuration](../../../configs/gripper_mapping.json). No gap is filled.
The [shared forward-segment calculation](../../../src/egocentric_pipeline/gripper_mapping.py)
drives both poses and the viewer's construction line. The viewer shows a white
sphere at the shifted wrist and a short segment back to the original wrist.

Transforms use column vectors in the existing gravity-aligned frame, metres and
radians. `T_aligned_from_TCP = T_aligned_from_grasp @ T_grasp_from_TCP`; configurable
local translation and XYZ Euler rotation define the correction, initially identity.
`T_aligned_from_palm = T_aligned_from_TCP @ inverse(T_palm_from_TCP)` positions the
detached model. The URDF nominal TCP is 0.160804 m along palm +X. It remains fixed
as the fingers curl, so it must not be described as the actual fingertip/contact
center at every opening.

Action is continuous **0 closed / 1 open**:
`clip((tip_distance - closed_distance) / (open_distance - closed_distance), 0, 1)`.
Defaults are **0.010637088979430357 m** closed and **0.3586942059948014 m** open.
The shared rule fits the user-selected right-hand examples: frame 92 (2.108 cm)
→ **0.03**, and frame 119 (12.550 cm) → **0.33**. The first target is within the
requested <~0.05 range. Fully open is extrapolated; this fit does not imply
physical jaw separation equals human fingertip separation.

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

`gripper_mapping.npz`, `mapping_report.json`, `settings.json` and standalone
left/right URDFs are saved in a new output directory. Existing outputs are refused.
Older five- and six-landmark runs remain readable: settings without `forward_axis`
retain wrist→thumb MCP; `thumb_mcp_to_ip` retains the thumb-based direction. New
seven-point results also support `index_mcp_to_pip`. The current default is
`forward_axis: wrist_to_mcp_midpoint`, `orientation_priority: forward` and
`wrist_thumb_offset_m: 0.025`. Settings missing the last two keys retain closing
priority and zero shift. A nonzero shift is supported only for the MCP-midpoint
forward rule. Index PIP is retained after thumb IP to
preserve the preceding reviewed trial and its overlay. The viewer labels the
active direction and draws that segment; it never silently changes an older saved mapping.
Reports record the source, asset revision/configuration, landmark convention and
per-hand missing/degenerate/opening-saturation counts. Licensed models and generated
geometry remain local inputs/evidence, outside Git.

The [viewer](../../../src/egocentric_pipeline/gripper_visualization.py) reconstructs
the same raw MANO meshes and checks their landmarks against the saved result.
Source RGB is decoded by original frame index. It initially selects the first
frame with both mappings available, while retaining every frame and missing-data
transition in the slider. Playback uses the saved timestamp differences.

Controls provide both-hand/individual closeups, per-side visibility, hand/gripper
opacity, landmark/axis overlays, opening thresholds, thumbward wrist shift and
per-hand local TCP offsets. The wrist-shift control is shown for MCP-midpoint runs.
The GUI uses degrees for editable rotations; saved settings use radians.
**Save mapping snapshot** writes a new timestamped child directory containing all
mapped frames and settings. It does not alter the original run. Invalid opening
thresholds disable saving and retain the last valid preview until corrected.

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
