# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — approved export refresh; broader simulation acceptance remains open.
- Active plan: [LeRobot export refresh, revision 1](plans/lerobot-export-refresh.md), approved 2026-11-12. Previous [cleanup/integration plan](plans/codebase-cleanup-and-pipeline.md) and [held-out evaluation scope](plans/milestone-3-ik-tuning.md) remain fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: one full-video MP4-to-annotated-robot-LeRobot workflow, preserved Milestone 2 evidence, frozen defaults, organized capabilities/commands and consolidated processing runtime. [Cleanup acceptance and review artifacts](topics/integrated-pipeline.md#cleanup-verification--2026-11-03).
- Current work: inspected the supplied specification, current exporter, shell workflow, provenance, geometry and evaluation contracts; approved revision 1; implementing the export, training and shell contracts.
- Blockers or decisions: Tracking/collision failures, unmeasured scale/floor and the [10 rad/s² acceleration proxy](decisions/ik-benchmark-limits.md) remain limitations.
- Next action: implement both datasets and update `pipeline/run.sh`; retain the broader simulation acceptance question separately.
- Last verification: **2026-11-12** — source/dependency inspection and planning only; see the November log event `20261112-export-refresh-001`. Last runtime acceptance remains the [2026-11-03 cleanup checks](topics/integrated-pipeline.md#cleanup-verification--2026-11-03).
