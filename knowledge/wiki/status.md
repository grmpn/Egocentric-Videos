# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Complete** — stronger temporal-smoothing experiment and comparison verified; no accepted demonstration.
- Active plan: [Joint base and trajectory optimization, approved revision 6](plans/milestone-3-joint-base-optimization.md). Earlier fulfilled plans remain in the [index](index.md).
- Deliverable: rerun iPhone optimization with 1,000× temporal residual weights and compare motion, pose accuracy and large-joint-change frame counts against the no-infill baseline.
- Completed outcome: >0.5 rad change frames fall 116 → 0 within regions, or 116 → 1 including the adjacent region reset; acceleration RMS 246.85 → 5.32 rad/s². Pose passes fall 855/957 → 189/957. [Comparison, plots and playback](experiments/retargeting-iphone.md#stronger-temporal-smoothing).
- Current work: experiment complete; velocity 1.0 / acceleration 0.5 are not adopted. Defaults remain 0.001 / 0.0005, with hand weights 1.0 and infilled observations excluded. Viewers: first region localhost:8082; full run localhost:8083.
- Blockers or decisions: pose/gap gates still fail; frame 1113 has a 3.136 rad region-reset jump. First two selected trajectory solves exhaust their budgets. Physical scale/gravity, collisions and dynamics remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review the accuracy tradeoff and boundary reset before authorizing another tuning experiment. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-21**, independent mask/source/FK/bounds/sampling/gate and jump-count checks, all 1,286 video timestamps, exact first-region preview equality and 22-frame browser/visual review; `20261021-smooth1000-006` in the [action log](logs/2026-10.jsonl). No production-code change or unit-test rerun.
