# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — approved cleanup/integration revision 2; broader simulation acceptance remains open.
- Active plan: [Codebase cleanup and integrated pipeline, revision 2](plans/codebase-cleanup-and-pipeline.md) (approved 2026-11-03). Prior [held-out evaluation scope](plans/milestone-3-ik-tuning.md) is fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted. Approved cleanup deliverable: one MP4-to-annotated-robot-LeRobot workflow and a smaller, organized repository.
- Completed outcome: Milestone 2 evidence relocated with all 535 file hashes preserved; completed runs and historical datasets reloaded; frozen solver/mapping defaults verified. [Relocation and checks](topics/hawor-pipeline.md). Prior [held-out evaluation](experiments/ik-benchmark-iphone.md#held-out-regions-2-and-3--2026-11-03) remains valid.
- Current work: integrating full-video robot export and reorganizing the processing workflow. The new robot feature contract has five focused checks and a 1,286-frame saved iPhone smoke; official dataset integration and the consolidated processing environment are under validation. Configuration regression rerun is still running.
- Blockers or decisions: no scope decisions pending. Robot-action export and environment consolidation require implementation and validation. Held-out tracking/collision failures and the [10 rad/s² acceleration proxy](decisions/ik-benchmark-limits.md) remain limitations.
- Next action: finish robot dataset create/append/annotation tests, reorganize capability modules and processing commands, then run the complete shell workflow and environment checks.
- Last verification: **2026-11-03** — [artifact/default parity and official historical reloads](../../outputs/cleanup/relocation-validation.json), [11 gravity tests](../../outputs/cleanup/defaults-gravity-tests.log), and CLI imports passed. New integrated workflow and broader simulation acceptance remain unverified.
