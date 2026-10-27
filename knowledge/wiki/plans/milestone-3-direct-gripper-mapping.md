# Milestone 3 — Direct hand-to-gripper mapping

Draft revision 1 · 2026-10-27 · Not approved; requested in `20261027-gripper-plan-001` in the [action log](../logs/2026-10.jsonl).

## Objective and deliverable

Isolate hand-to-gripper mapping from arm IK. Deliver independently positionable,
orientable and actuated EZGrippers, plus a reusable interactive viewer showing
the original MANO hands and directly mapped grippers on the iPhone demonstration's
first retained manipulation region: frames **[0,296)**, approximately **0–9.87 s**
([input evidence](../experiments/retargeting-iphone.md)).

## Scope and boundaries

- **Detached grippers:** derive palm-rooted left/right grippers from the pinned
  Purdue URDF's existing subtrees, preserving meshes, joint limits and mimic
  coupling. Leave source assets intact. Support arbitrary rigid poses and one
  normalized opening command, reusing the asset package's existing command rule.
  Check closed, intermediate and open geometry before hand playback.
- **Input:** reuse existing iPhone reconstruction/gravity alignment and MANO
  reconstruction. Work in the shared gravity-aligned frame, with metres, radians,
  original frame indices/timestamps and left/right identity. Use unfiltered hand
  geometry and `export_valid & ~motion_infilled`; hide missing hands/grippers and
  label gaps. Document and visually check MANO wrist/MCP/tip landmark selection.
- **First mapping:** implement the user's humanEgo-inspired description. Grasp
  center is the thumbtip/index-tip midpoint. Set +Y to normalized thumb-MCP →
  index-MCP (closing axis). Project wrist → thumb-MCP perpendicular to +Y and
  normalize for +X (forward); +Z = +X × +Y. Mark near-zero/collinear constructions
  invalid instead of inventing a pose. Verify handedness and axis signs on both
  hands. Initially align the URDF's nominal TCP with the human grasp center;
  expose a fixed local translation/rotation correction for alignment tuning.
  Label the TCP as nominal, not a calibrated contact center.
- **Opening:** interpret normalized action as continuous **[0,1]**, with **0
  closed, 1 open**. Initially use `clip(d / 0.10 m, 0, 1)`, where `d` is fingertip
  separation. Keep closed/open distances configurable; 10 cm is a provisional
  guess, not measured calibration. Map action through the existing EZGripper
  joint command, respecting coupling and bounds.
- **Viewer:** reuse the existing visualization stack for play/pause, scrubbing,
  synchronized RGB, both-hand closeups, visibility/opacity controls, landmark and
  axis overlays, separation/action readouts, and alignment/opening adjustments.
  Save settings and derived poses/actions with validity for repeatable review.
  Manual pose/opening controls verify the detached gripper independently.
- No arm/base fitting, IK, filtering or reconstruction reruns, collision/dynamics
  certification, or hardware control. Thumb-IP/index-PIP center comparison and
  later regions follow this first-pass review; they are deferred.

## Acceptance

- Check standalone/full-model gripper geometry agreement at representative
  openings, mimic coupling, limits, center placement, proper rotations, rigid-frame
  equivariance, action clipping, left/right identity and invalid-data isolation.
- Replay all 296 frames without invoking IK. Inspect both hands at representative
  opening/closing poses, region endpoints and missing-data transitions; verify
  RGB/frame synchronization and viewer controls.
- Save reproducible settings, derived mapping, validation logs and representative
  screenshots under a new `outputs/retargeting/` run. Record alignment issues and
  opening saturation for user review; document behavior and commit verified work.
  Acceptance establishes an inspectable direct mapping, not physical grasp
  accuracy or completion of the roadmap's simulation deliverable.
