# Milestone 3 — Wrist-to-wrist alignment amendment

Approved revision 1 · 2026-10-20 · Approval: `20261020-wrist-alignment-003` in the [action log](../logs/2026-10.jsonl).

## Objective and deliverable

Align each physical human wrist with the corresponding robot wrist joint in the
fixed-base trajectory workflow. Deliver regenerated wrist workspace maps,
placement/IK outputs and interactive playback on the bundled example.
This amends the endpoint convention in the fulfilled
[Part 2](milestone-3-part-2-robot-workspace.md) and
[Part 3](milestone-3-part-3-placement-and-segmentation.md) plans; their original
TCP results remain historical acceptance evidence.

## Scope and boundaries

- Use `LEFT_WRIST_X_LINK` and `RIGHT_WRIST_X_LINK` origins, at the robot's
  distal wrist flexion joints, as the human-wrist position targets. Keep actual
  EZGripper TCP positions separately identified; a wrist result must never be
  labeled as a TCP result.
- Regenerate the corresponding 2 cm workspaces with 10 million samples per arm,
  reusing saved joint configurations where compatible. Workspace queries, base
  fitting and IK must describe the same endpoint. Preserve the pinned model,
  native metres/radians, fixed gravity-aligned base per episode, source times,
  left/right identity, validity and original MANO geometry.
- Keep sequential, position-only per-frame IK, seeded from previous successes.
  Export full arm configurations; joints that do not affect the wrist position
  remain at documented defaults. Preserve failures, missing samples and
  discontinuity reporting. Keep the existing coverage, duration, gap, workspace
  margin and joint-limit requirements.
- Update exports, reports and viewer markers to distinguish human wrist, robot
  wrist and TCP. Preserve old run readability and original generated evidence;
  save new runs separately. Reuse existing dependencies and workflow.
- Orientation matching, gripper actuation, trajectory smoothing/retiming,
  collision checks, dynamics and hardware execution remain outside this change.

## Acceptance

Run the production workflow on the bundled input. Independently verify robot
wrist FK against every successful human-wrist target within **5 mm**, with URDF
joint bounds satisfied. Verify endpoint consistency between workspace, placement,
IK, exports and preview, including legacy TCP runs. Retain **>95%** coverage,
**3 cm** workspace margin, **≤0.2 s** gaps and **≥1 s** duration; at least one
episode must pass SDF, IK and their intersection.

Inspect representative MANO/robot playback frames, episode changes and
missing/failed samples. Save focused test logs, numerical residuals and visual
evidence under `outputs/retargeting/`. Passing establishes wrist position
alignment; hand/tool orientation and physical executability remain unverified.
