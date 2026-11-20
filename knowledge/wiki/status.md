# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Validating** — camera/hand trajectory comparison fulfilled; broader simulation acceptance remains open.
- Active plan: [iPhone trajectory comparison, revision 1](plans/iphone-trajectory-comparison.md) fulfilled 2026-11-20. [iPhone export revision 2](plans/iphone-contract3-export.md) remains fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: all three 1,286-frame camera runs, shared hands/gravity/depth, pairwise metrics and graphs verified; [comparison acceptance](experiments/iphone-trajectory-comparison.md). Prior [all-region export](topics/lerobot-pipeline.md#iphone-test-export--2026-11-17) remains delivered.
- Current work: comparison handoff; no backend adoption or robot/export change.
- Blockers or decisions: no ground truth; per-frame metric-scale variation limits interpretation. AMB3R mirror matches its published checksum and official size, but original-file hash comparison is unavailable. Existing simulation/export limitations remain.
- Next action: review comparison results and the remaining Milestone 3 simulation acceptance; scope any backend adoption separately.
- Last verification: **2026-11-20** — 12 tests, full saved-array audit and visual inspection passed; [execution evidence](logs/2026-11.jsonl), event `20261120-trajectory-comparison-008`.
