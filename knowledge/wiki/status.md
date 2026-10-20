# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Complete** — revision 4 experiment verified; no trial meets the full pose-plus-smoothing demo gate.
- Active plan: [Joint base and trajectory optimization, approved revision 4](plans/milestone-3-joint-base-optimization.md). Earlier fulfilled plans remain in the [index](index.md).
- Deliverable: 5 cm gripper-relative wrist match point, alternate-frame joint/base fitting, full-frame trajectory refinement, and controlled hand-weight comparison with saved playback.
- Completed outcome: hand weights 1/0.5/0.2/0.1 pass 79/78/60/0 of 83 frames. Lower weights reduce posture deviation and acceleration but lose orientation coverage. Region 1 passes poses through 0.2; refinement increases its acceleration versus the interpolated seed. [Results and visual evidence](experiments/joint-base-bundled.md#gripper-offset-and-hand-weight-sweep).
- Current work: experiment complete. Defaults: posture 0.5, hand weights 1.0, 5 cm local +X offset, stride 2, no camera-position objective.
- Blockers or decisions: no qualifying full demo; orientation failures, acceleration increase versus interpolation, camera/head error and physical/collision calibration remain. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review are outstanding.
- Next action: review shifted alignment and the 0.5 hand-weight tradeoff before further tuning. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-20**, 54 focused tests, four independent FK/source/sampling/acceptance audits, identical-settings/video checks and control/downweighted/legacy browser review; `20261020-gripper-offset-006` in the [action log](logs/2026-10.jsonl).
