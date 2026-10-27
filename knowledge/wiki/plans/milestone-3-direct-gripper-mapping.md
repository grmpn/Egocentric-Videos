# Milestone 3 — Direct hand-to-gripper mapping

Approved revision 6 · 2026-10-27 · User-directed two-tip correspondence trial recorded as `20261027-gripper-tips-001` in the [action log](../logs/2026-10.jsonl). This supersedes the shifted wrist and empirical opening fit for the new trial.

## Objective and deliverable

Refine the detached-gripper mapping independently of arm IK. Deliver independently
positionable, orientable and actuated EZGrippers, with a reusable synchronized
viewer of the original MANO hands and mapped grippers for iPhone frames **[0,296)**.

## Scope and boundaries

- Reuse the pinned Purdue URDF subtrees, meshes, joint limits, mimic coupling and
  existing normalized opening command. Preserve source assets and raw aligned
  MANO geometry, metres, radians, left/right identity, frame indices and timestamps.
  Eligible observations remain `export_valid & ~motion_infilled`.
- Define explicit markers at the center of each distal gripper tip edge. Solve
  opening from the actual FK separation, then compute a rigid transform mapping
  those markers onto the thumbtip and index tip respectively. Do not scale the
  robot or retain an independently fitted opening that prevents correspondence.
- Preserve the thumbtip→index-tip line. Resolve rotation around it using the
  **true wrist→thumb MCP** direction, projected perpendicular to that line. Align
  the projected native palm forward direction with this projected human direction.
  Use a proper rotation and the opening-dependent gripper tip midpoint to place
  the model. The fixed nominal TCP need not coincide with the fingertip midpoint.
- Use the uncrossed, increasing-separation branch of the existing opening rule.
  Report the reachable range. Mark unreachable or degenerate observations invalid
  rather than silently clipping, stretching, or claiming an exact match. Verify
  whether all eligible samples in this region are reachable.
- Show both hands, articulated grippers, matched tip markers, the true wrist
  construction vector, and tip residuals. Retain playback, scrubbing, synchronized
  RGB, closeups, visibility/opacity, snapshot export and independent manual gripper
  controls. Hide legacy alignment/normalization adjustments in exact-match mode
  because they would break the requested correspondence. Preserve earlier runs
  and their original mapping rules.
- No arm IK, reconstruction reruns, filtering, hardware control, collision or
  dynamics verification. Later manipulation regions and alternative human contact
  landmarks remain deferred. Mesh markers are a nominal geometric definition,
  not a physical pad/contact calibration.

## Acceptance

- Verify real FK places both gripper markers on their respective human tips to
  numerical tolerance at every valid sample, with correct hand/tip identity,
  proper rotations, rigid-frame equivariance, joint limits and mimic coupling.
  Check missing, degenerate and unreachable input behavior.
- Test the production preparation/snapshot workflow and compatibility with earlier
  saved runs. Preserve all source fields and confirm the opening changes at the
  user's reference frames 92 and 119.
- Replay the full 296-frame region; inspect both hands, endpoints, gaps and
  representative poses in the browser. Save settings, mapping arrays, reports,
  test logs and screenshots in a new local output directory. Record remaining
  physical limitations and commit verified code/documentation. This completes
  the direct-mapping trial, not the roadmap simulation demonstration.
