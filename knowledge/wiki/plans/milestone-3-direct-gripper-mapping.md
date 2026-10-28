# Milestone 3 — Direct hand-to-gripper mapping

Approved revision 8 · 2026-10-28 · User-requested comparison and clarified wrist/roll reference recorded as `20261028-gripper-comparison-001` in the [action log](../logs/2026-10.jsonl). Revision 7 remains the preserved comparison baseline.

## Objective and deliverable

Compare two additional direct hand-to-gripper mappings with revision 7 so the
user can select a method. Keep the current viewer on port 8091 open, and launch
separate synchronized RGB/MANO/gripper viewers for both new configurations on
iPhone frames **[0,296)**. Each result must be independently reloadable.

## Scope and boundaries

- Preserve pinned Purdue gripper assets, coupling/limits, original aligned MANO
  geometry, metres, radians, timestamps and left/right identity. Use
  `export_valid & ~motion_infilled`; do not interpolate missing observations.
- Config 1: plane through index MCP, index PIP and thumb IP. Jaw +Y points
  **index MCP→thumb IP**; forward +X is index MCP→index PIP projected perpendicular
  to +Y, toward PIP; +Z = +X × +Y. Preserve fingertip-midpoint placement using
  the opening-dependent gripper tip frame.
- Config 2: the gripper's rear palm/base origin coincides with the physical hand
  wrist. Forward +X points wrist→midpoint(thumb MCP,index MCP). Roll about +X
  follows the projected thumb MCP→index MCP line. Zero roll is the ideal open
  MANO hand with the same shape/current wrist orientation; align its forward
  axis to current forward with the shortest rotation before measuring signed
  roll. Reject undefined axes/references without inventing a pose.
- Both variants retain geometry-derived opening from fingertip distance and
  the existing uncrossed, increasing-separation branch. No gripper scaling or
  silent clamping. Config 2 intentionally replaces fingertip-midpoint placement
  with wrist attachment; its tip offsets remain visible diagnostics.
- Show method names, construction geometry, axes, tips and relevant anchor
  errors; show Config 2's zero-roll reference and signed roll. Retain playback,
  scrubbing, closeups, visibility, snapshots, manual controls and older results.
- No arm IK, reconstruction reruns, filtering, hardware control, physical contact,
  collision or dynamics validation. Later regions and selecting a new default
  remain deferred until the user's comparison review.

## Acceptance

- Test axis signs, proper rotations and rigid-frame equivariance, Config 1's
  real-FK midpoint, Config 2's exact wrist anchor and 0°/±90° roll, unchanged
  opening, missing/degenerate/unreachable inputs and historical compatibility.
- Generate both results and audit all eligible samples, original fields and
  timestamps. Exercise CLI, snapshots/reload and representative visual playback
  for both hands, frames 92/119, endpoints and gaps. Confirm the original viewer
  remains available. Save settings, logs, audits and screenshots under a new
  local comparison directory; update wiki/status/log and commit verified work.
  Acceptance establishes an inspectable geometric comparison, not simulation
  execution or physical contact accuracy.
