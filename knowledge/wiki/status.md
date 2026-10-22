# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Validating** — hand-pose refinement experiment fulfilled; roadmap simulation demonstration remains unaccepted.
- Active plan: [Hand-pose smoothing and region continuity, approved revision 1](plans/milestone-3-hand-pose-refinement.md), fulfilled. Earlier plans remain in the [index](index.md).
- Deliverable: configurable Savitzky–Golay hand-target smoothing, a weak median-camera base prior, adjacent retained-region merging and controlled CUDA comparisons with a complete iPhone rerun.
- Completed outcome: seven controlled variants and full combined rerun verified. Frame 1113 step falls 3.133 → 0.083 rad; full passes are **118/957 (12.33%) against raw** and **406/957 (42.42%) against smoothed** targets. [Comparison and acceptance evidence](experiments/hand-pose-refinement.md).
- Current work: [frame-1050 diagnosis](experiments/hand-pose-refinement.md#frame-1050-projection-jitter-diagnosis) confirms that world-only hand filtering disrupts camera/hand cancellation and increases projected jitter despite smoother 3D paths. User review continues in the [video comparison](http://localhost:8090/smoothed-overlay/review.html); no filter settings changed.
- Blockers or decisions: raw pose/gap gates still fail; the combined setting reduces raw coverage from the baseline's 189/957. All selected combined solves exhaust their budgets. Physical scale/gravity, collisions and dynamics remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review camera/hand consistency and pose/motion tradeoffs before choosing further work; no additional tuning started. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-22**, prior 84 tests and overlay audits remain applicable. Frame-1050 filter recomputation, exact camera-motion decomposition and visual diagnostics pass; `20261022-frame1050-002` in the [action log](logs/2026-10.jsonl).
