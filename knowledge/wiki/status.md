# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Validating** — running the existing workflow on the iPhone demonstration at the user's request.
- Active plan: [Joint base and trajectory optimization, approved revision 4](plans/milestone-3-joint-base-optimization.md). Earlier fulfilled plans remain in the [index](index.md).
- Deliverable: 5 cm gripper-relative wrist match point, alternate-frame joint/base fitting, full-frame trajectory refinement, and controlled hand-weight comparison with saved playback.
- Completed outcome: hand weights 1/0.5/0.2/0.1 pass 79/78/60/0 of 83 frames. Lower weights reduce posture deviation and acceleration but lose orientation coverage. Region 1 passes poses through 0.2; refinement increases its acceleration versus the interpolated seed. [Results and visual evidence](experiments/joint-base-bundled.md#gripper-offset-and-hand-weight-sweep).
- Current work: iPhone downscaling to 960×540, HaWoR and gravity alignment completed; joint/base fitting is running on four retained regions. Defaults exactly match the last hand-weight-1 trial. [iPhone evidence](experiments/retargeting-iphone.md).
- Blockers or decisions: no qualifying full demo; orientation failures, acceleration increase versus interpolation, camera/head error and physical/collision calibration remain. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review are outstanding.
- Next action: inspect iPhone reconstruction, retargeted playback and unchanged acceptance gates; save evidence under `outputs/retargeting/iphone-20261021/`. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-21**, input frame/timestamp preservation, exact prior-settings match, completed HaWoR/GeoCalib numerical checks, overlay and gravity visual review; `20261021-iphone-007` in the [action log](logs/2026-10.jsonl). Retargeting acceptance remains pending.
