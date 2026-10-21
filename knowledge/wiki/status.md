# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Complete** — requested infilled-hand exclusion and iPhone rerun verified; no region meets the full demonstration gate.
- Active plan: [Joint base and trajectory optimization, approved revision 5](plans/milestone-3-joint-base-optimization.md). Earlier fulfilled plans remain in the [index](index.md).
- Deliverable: exclude infilled hands throughout both retargeting methods, preserve source data, and produce a reviewed iPhone rerun with weight-1 defaults.
- Completed outcome: 855/957 eligible frames pass poses, versus 354/957 for the historical fit on the same observations. All four regions exceed gap limits and increase acceleration. [Results, trajectory and playback](experiments/retargeting-iphone.md#rerun-excluding-infilled-hands).
- Current work: requested change and rerun complete. Defaults remain posture 0.5, hand weights 1.0, 5 cm local +X offset, stride 2 and no camera-position objective. The existing 960×540 input/alignment is reused.
- Blockers or decisions: missing-data gaps, acceleration increase and remaining pose outliers prevent a qualifying demo. Physical scale/gravity, collision and dynamic limits remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review gaps, frame 295 and acceleration failures before approving further tuning. Viewer: `outputs/retargeting/iphone-no-infill-20261021/trajectory/`. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-21**, 62 focused tests, independent mask/FK/source/bounds/sampling/gate audit, all 1,286 video timestamps, legacy compatibility and 17-frame browser/visual review; `20261021-no-infill-010` in the [action log](logs/2026-10.jsonl).
