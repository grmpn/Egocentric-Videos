# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Validating** — hand-pose refinement experiment fulfilled; roadmap simulation demonstration remains unaccepted.
- Active plan: [Hand-pose smoothing and region continuity, approved revision 1](plans/milestone-3-hand-pose-refinement.md), fulfilled. Earlier plans remain in the [index](index.md).
- Deliverable: configurable Savitzky–Golay hand-target smoothing, a weak median-camera base prior, adjacent retained-region merging and controlled CUDA comparisons with a complete iPhone rerun.
- Completed outcome: seven controlled variants and full combined rerun verified. Frame 1113 step falls 3.133 → 0.083 rad; full passes are **118/957 (12.33%) against raw** and **406/957 (42.42%) against smoothed** targets. [Comparison and acceptance evidence](experiments/hand-pose-refinement.md).
- Current work: user review of the opened [smoothed-hand video comparison](http://localhost:8090/smoothed-overlay/review.html), alongside all nine results in the [experiment viewer](http://localhost:8090). Configurable refinements remain disabled by default; original observations still determine demonstration acceptance.
- Blockers or decisions: raw pose/gap gates still fail; the combined setting reduces raw coverage from the baseline's 189/957. All selected combined solves exhaust their budgets. Physical scale/gravity, collisions and dynamics remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review pose/motion tradeoffs before choosing further work; no additional tuning started. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-22**, prior 84 tests and experiment audits pass. Additional smoothed-hand overlays pass geometry, all-frame timestamps, decoding, browser playback and visual review; [evidence](experiments/hand-pose-refinement.md#smoothed-hands-on-source-video), `20261022-smoothed-overlay-002` in the [action log](logs/2026-10.jsonl).
