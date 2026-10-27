# Milestone 3 — Direct hand-to-gripper mapping

Approved revision 7 · 2026-10-27 · User-directed MCP/index-PIP plane trial recorded as `20261027-gripper-plane-001` in the [action log](../logs/2026-10.jsonl). This changes orientation; geometry-derived opening and tip-midpoint placement remain.

## Objective and deliverable

Refine direct hand-to-gripper mapping independently of arm IK. Deliver detached,
freely posed and actuated EZGrippers with a synchronized original-MANO viewer for
iPhone frames **[0,296)**, using the user's three-landmark orientation plane.

## Scope and boundaries

- Preserve pinned Purdue gripper assets, coupling/limits, original aligned MANO
  geometry, metres, radians, timestamps and left/right identity. Use
  `export_valid & ~motion_infilled`; do not interpolate missing observations.
- Set jaw +Y to normalized **thumb MCP→index MCP**. Set forward +X to
  **index MCP→index PIP projected perpendicular to +Y**, pointing toward index
  PIP. Both axes lie in the plane through thumb MCP, index MCP and index PIP;
  +Z = +X × +Y. Reject coincident/collinear constructions without inventing axes.
- Set the position target to midpoint(thumbtip, index tip). Retain revision 6's
  opening-dependent tip-frame placement so the gripper tip midpoint coincides
  with this target. The fixed nominal TCP is a separate reference.
- Keep geometry-derived opening from fingertip distance and the same uncrossed,
  increasing-separation branch. Individual tip correspondence is superseded by
  MCP-based jaw orientation; display the resulting offsets honestly. Do not scale
  the gripper or silently clamp unreachable separation.
- Show the construction triangle and axes, gripper tips, midpoint placement and
  individual tip offsets. Retain RGB/playback/scrubbing, closeups, visibility,
  snapshots, manual controls and compatibility with earlier mapping results.
- No arm IK, reconstruction reruns, filtering, hardware control, physical contact,
  collision or dynamics validation. Later regions and alternative contact
  landmarks remain deferred.

## Acceptance

- Test the plane, jaw direction, forward sign, proper rotation, rigid-frame
  equivariance, real-FK midpoint placement and unchanged opening. Cover missing,
  degenerate and unreachable inputs and preserve historical mappings.
- Generate the first-region mapping; audit every eligible sample and retain
  source fields. Record midpoint errors and individual tip offsets, including
  right frames 92/119. Verify the production CLI and saved snapshot reload.
- Replay and visually inspect both hands, representative frames, endpoints and
  gaps. Save mapping/settings, logs and screenshots in a new local output directory;
  update canonical documentation and commit verified work. Acceptance covers this
  inspectable geometric trial, not the roadmap simulation demonstration.
