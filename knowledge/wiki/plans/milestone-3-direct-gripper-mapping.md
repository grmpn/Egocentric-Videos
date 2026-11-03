# Milestone 3 — Direct hand-to-gripper mapping

Approved revision 10 · 2026-10-28 · User requested Config 4 and full iPhone
comparison, then selected saved overlay MP4s. Recorded as
`20261028-gripper-full-001` in the [action log](../logs/2026-10.jsonl).
Earlier comparisons remain preserved.

## Objective and deliverable

Compare Configs 2, 3 and 4 across the entire prepared iPhone recording:
**1,286 frames, 42.87 seconds**. Deliver three saved MP4s with posed gripper meshes
projected onto the source RGB, plus reloadable mappings and validation evidence.
Keep existing interactive comparison windows available.

## Scope and boundaries

- Config 4 forms a plane from index MCP, index PIP and a thumb point interpolated
  from thumb IP when open to thumb MCP when pinching. Use the same fingertip-forward,
  ideal-open MCP roll reference and absolute-roll smoothstep weights as Config 3:
  weight 0 at ≤30°, weight 1 at ≥45°. Jaw +Y points index MCP→interpolated thumb
  point; +X projects index MCP→PIP perpendicular to it, +Z=X×Y. Preserve this
  explicitly requested direction: the pinch endpoint has the original plane but
  reversed Y/Z. Preserve fingertip-midpoint placement and geometry-derived opening.
- Keep Config 2's rear-palm wrist anchor/fingertip forward and Config 3's aligned
  rotation blend unchanged. Reuse existing original aligned MANO and pinned robot
  assets. Do not rerun HaWoR, solve arm IK or smooth trajectories.
- Process all source frames with unchanged timestamps, metres, rotations and
  left/right identity. Eligibility remains `export_valid & ~motion_infilled`;
  reject degenerate/unreachable geometry and draw no gripper for those samples.
- Render each saved mapping with the existing aligned camera poses/intrinsics
  and ordinary gripper FK, using installed rendering/encoding dependencies.
  Retain full source image dimensions and frame rate. Distinguish configurations
  and missing-hand states in overlays; preserve inputs and previous outputs.
- Keep Config 4's construction/weights inspectable in the existing viewer and
  saved arrays. No new full-length viewer windows are required by this request.
  Physical contact, scene occlusion, collision/dynamics and final default selection
  remain outside this geometric comparison.

## Acceptance

- Focused tests verify interpolated positions, endpoint direction, intermediate
  axes, FK midpoint/opening, rigid-frame equivariance, missing/degenerate samples
  and snapshot/CLI compatibility. Exercise camera transform/projection direction.
- Generate all three full mappings; audit frame/timestamp/source preservation,
  mapping coverage, anchors, Config 4 weights/axes and adjacent orientation changes.
  Confirm prior Config 2/3 first-region results remain unchanged.
- Render all three videos, verify frame count, dimensions, timestamps and decoding,
  and inspect representative open/pinch/late/missing-observation frames.
  Save reports, logs and review images under a new local output directory.
  Update canonical documentation/status/action log and commit verified work.
