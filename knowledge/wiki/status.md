# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Validating** — cleanup/integration is complete; broader simulation acceptance remains open.
- Active plan: [Codebase cleanup and integrated pipeline, revision 2](plans/codebase-cleanup-and-pipeline.md), approved and fulfilled 2026-11-03. Prior [held-out evaluation scope](plans/milestone-3-ik-tuning.md) is also fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: one full-video MP4-to-annotated-robot-LeRobot workflow, preserved Milestone 2 evidence, frozen defaults, organized capabilities/commands and consolidated processing runtime. [Cleanup acceptance and review artifacts](topics/integrated-pipeline.md#cleanup-verification--2026-11-03).
- Current work: cleanup implementation and validation finished. No next milestone or solver experiment started.
- Blockers or decisions: remaining simulation demonstration scope needs agreement. Tracking/collision failures and the [10 rad/s² acceleration proxy](decisions/ik-benchmark-limits.md) remain limitations; generated labels remain pending human semantic review.
- Next action: agree the remaining Milestone 3 simulation demonstration and acceptance evidence using the integrated workflow.
- Last verification: **2026-11-03** — 284 processing checks, official create/append/annotation tests, inspected 1,286-frame iPhone export, and [completed 121-frame shell run](../../outputs/cleanup/small-video-complete-console.log) with [annotation preservation/server shutdown](../../outputs/cleanup/small-annotation-review.json). Old gravity/workspace environments retired after replacement checks.
