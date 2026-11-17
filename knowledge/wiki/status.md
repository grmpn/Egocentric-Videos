# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Validating** — iPhone test export verified; broader simulation acceptance remains open.
- Active plan: [iPhone contract 3.0 export, revision 2](plans/iphone-contract3-export.md), approved and fulfilled 2026-11-17.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: full 1,286-frame human episode and all three robot regions (1,069 frames) delivered to `~/dev/alex-trajectory-playback/datasets`; [acceptance evidence](topics/lerobot-pipeline.md#iphone-test-export--2026-11-17).
- Current work: export and transfer complete; all historical inputs/solves preserved.
- Blockers or decisions: region 3 exported as test data under explicit override (61.36% constraint-valid); tracking/collision masks retained. Language is unannotated; scale/floor and the [acceleration proxy](decisions/ik-benchmark-limits.md) remain limitations.
- Next action: review the exported test data in the playback project and agree the remaining Milestone 3 simulation acceptance work; no solver changes or next milestone started.
- Last verification: **2026-11-17** — 20 focused checks, full numeric/video validation and visual inspection, byte-matched transfer and official-reader reload at destination; see linked evidence.
