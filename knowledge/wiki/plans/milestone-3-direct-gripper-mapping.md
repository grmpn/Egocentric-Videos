# Milestone 3 — Direct hand-to-gripper mapping

Approved revision 9 · 2026-10-28 · User-requested fingertip-forward Config 2 and roll-weighted Config 3, with explicit jaw-alignment choice, recorded as `20261028-gripper-blend-001` in the [action log](../logs/2026-10.jsonl). Earlier comparison results remain preserved.

## Objective and deliverable

Extend the first-region comparison to refine Config 2's forward direction and
try a smooth transition between Config 1 for open hands and the original MCP
plane for pinches. Deliver two independently reloadable results and new viewers
for iPhone frames **[0,296)**, retaining the existing three review windows.

## Scope and boundaries

- Preserve pinned Purdue gripper assets, coupling/limits, original aligned MANO
  geometry, metres, radians, timestamps and left/right identity. Use
  `export_valid & ~motion_infilled`; do not interpolate missing observations.
- Updated Config 2: rear palm origin stays at the physical hand wrist. Forward
  becomes wrist→midpoint(thumbtip,index tip); project thumb MCP→index MCP
  perpendicular to forward for the jaw. Retain signed roll from an ideal open
  hand with matching shape and wrist orientation. Its open forward also uses
  fingertip midpoint, transported by the shortest rotation to current forward.
  Preserve earlier MCP-forward results when reloading their saved settings.
- Config 3: measure MCP-line roll using updated Config 2 and interpolate proper
  rotations between the thumb-IP and original MCP planes using existing SciPy
  rotation operations. The user approved aligning jaw directions within this
  blend: reverse Config 1's +Y/+Z while preserving +X, so its jaw points from
  thumb side toward index side. Standalone Config 1 stays unchanged.
- Start with original weight 0 at |roll|≤30°, weight 1 at ≥45°, and smoothstep
  between. Expose both thresholds and current roll/weight in the viewer. Config 3
  retains fingertip-midpoint placement and existing FK-derived opening; Config 2
  retains wrist attachment. Reject undefined axes/references without inventing
  poses or bridging missing data.
- Preserve opening branch, playback, closeups, snapshots, manual controls and
  historical mappings. Show endpoint planes, blended axes and anchor diagnostics.
- No arm IK, reconstruction reruns, filtering, hardware control, physical contact,
  collision or dynamics validation. Later regions and selecting a new default
  remain deferred until the user's comparison review.

## Acceptance

- Test updated forward/wrist placement, unchanged opening/source fields,
  zero/±90° roll, blend endpoints/interior, proper rotations and rigid-frame
  equivariance. Exercise invalid thresholds, missing/degenerate inputs, historical
  settings and saved snapshots through production commands.
- Generate both results and audit all eligible samples, original fields and
  timestamps, ordinary FK, anchors, weights, endpoint angles and adjacent-frame
  rotation changes. Inspect both hands, especially open/pinch frames 92/119.
  Verify playback, threshold adjustment, snapshots/reload, manual controls and
  existing viewer availability. Save settings, logs, audits and screenshots under a new
  local comparison directory; update wiki/status/log and commit verified work.
  Acceptance establishes an inspectable geometric comparison, not simulation
  execution or physical contact accuracy.
