# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Implementing** — user-requested stronger temporal-smoothing experiment.
- Active plan: [Joint base and trajectory optimization, approved revision 6](plans/milestone-3-joint-base-optimization.md). Earlier fulfilled plans remain in the [index](index.md).
- Deliverable: rerun iPhone optimization with 1,000× temporal residual weights and compare motion, pose accuracy and large-joint-change frame counts against the no-infill baseline.
- Completed outcome: 855/957 eligible frames pass poses, versus 354/957 for the historical fit on the same observations. All four regions exceed gap limits and increase acceleration. [Results, trajectory and playback](experiments/retargeting-iphone.md#rerun-excluding-infilled-hands).
- Current work: isolated experiment uses velocity 1.0 and acceleration 0.5; all other settings and existing 960×540 input/alignment are reused. Defaults remain unchanged; infilled hands remain missing data.
- Blockers or decisions: missing-data gaps, acceleration increase and remaining pose outliers prevent a qualifying demo. Physical scale/gravity, collision and dynamic limits remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: complete the experiment under `outputs/retargeting/iphone-smooth1000-20261021/`, then independently count >0.5 rad changes and review accuracy/smoothness tradeoffs. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-21**, 62 focused tests, independent mask/FK/source/bounds/sampling/gate audit, all 1,286 video timestamps, legacy compatibility and 17-frame browser/visual review; `20261021-no-infill-010` in the [action log](logs/2026-10.jsonl).
