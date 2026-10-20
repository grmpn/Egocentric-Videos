# Milestone 3 — Joint base and trajectory optimization

Approved revision 4 · 2026-10-20 · User-requested gripper alignment and hand-weight experiment: `20261020-gripper-offset-001` in the [action log](../logs/2026-10.jsonl).

Earlier revisions and their outcomes remain in Git and the [evidence page](../experiments/joint-base-bundled.md). This amendment supersedes revision 3's camera-position objective and wrist-origin endpoint for the joint/base method.

## Objective and deliverable

Improve human-hand/gripper alignment by moving the wrist match point toward the
extended fingers, reduce joint/base fitting to alternate frames, and measure the
tradeoff from weaker hand-pose objectives. Deliver reproducible trajectories,
viewer evidence and a controlled comparison on the bundled clip.

## Scope and boundaries

- Use the same aligned input, pinned Purdue Alex model and retained regions
  `[0,52)` and `[74,105)`. Preserve source geometry, timestamps, metres/radians,
  hand identity, validity and confidence. Preserve previous runs and workspace
  behavior; no workspace regeneration is required for this joint/base amendment.
- Match each human wrist to a point 0.05 m from the robot wrist-joint origin along
  the gripper's local +X direction, toward its fingers. The user confirmed this
  gripper-relative direction; it rotates with the tool. Keep physical wrist,
  shifted match point and actual TCP distinct in reports/playback. Preserve the
  anatomical orientation mapping and original MANO geometry.
- Optimize shared base XYZ/yaw and joint poses on every other frame of each
  retained region, starting at its first frame. Initialize omitted frames by
  source-time joint interpolation, holding the last sampled pose at an unmatched
  endpoint. Freeze the base, then optimize and evaluate every original frame.
  Preserve median camera initialization, gravity-aligned roll/pitch, hard URDF
  bounds and fixed fingers.
- Remove the camera-position residual in both stages; retain camera rotation,
  segmentation and median-position initialization. Set posture residual weight
  to 0.5. Compare joint hand position/orientation residual multipliers 1.0, 0.5,
  0.2 and 0.1 with identical remaining settings, retries, seeds and budgets.
  Record squared-cost scaling; retain failures and termination messages.
- Reuse existing dependencies and workflows. No retiming, rescaling, collision or
  dynamics certification, simulation/controller execution or hardware transfer.

## Acceptance

- Verify the 5 cm offset and both-stage analytic Jacobians against ordinary FK
  and finite differences, including both hands and missing observations. Verify
  camera translation cannot affect the loss at fixed initialization/regions.
- Verify alternate-frame selection, source-time interpolation and full-resolution
  output/acceptance. Independently audit FK, bounds, transforms, source arrays,
  timestamps and failed/missing labels for all four production trials.
- Keep ≤5 mm and ≤10° per observed hand, >95% passing observed frames, ≤0.2 s
  gaps, ≥1 s duration and reduced acceleration RMS for demonstrated regions.
  Lower objective weights must not weaken these gates.
- Compare hand errors/coverage, posture, head/camera diagnostics, acceleration,
  attempts and single-run solve time. Inspect representative control/downweighted
  playback, hand/gripper closeups, failures and boundaries; retain legacy viewer
  support. Save configs, reports, tests, audits and visual evidence under
  `outputs/retargeting/`. Completion means an honest experiment, including any
  regressions or absence of qualifying regions.
