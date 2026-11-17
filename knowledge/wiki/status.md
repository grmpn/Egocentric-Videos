# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — iPhone contract 3.0 export with revised region acceptance.
- Active plan: [iPhone contract 3.0 export, revision 2](plans/iphone-contract3-export.md), approved 2026-11-17. Prior export refresh remains fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: independent structured human LeRobot data, region-based robot data with FK actions, masks/statistics/training support, updated shell/annotation workflow and standalone human reuse. [Acceptance evidence](topics/lerobot-pipeline.md#export-refresh-acceptance--2026-11-12).
- Current work: reusing full iPhone reconstruction and three saved solves; implementing collision/joint-limit-only 85% export acceptance while retaining tracking masks.
- Blockers or decisions: user requests all three iPhone regions as test data, including region 3 with its failed 85% gate logged. Tracking/collision failures, unmeasured scale/floor and the [acceleration proxy](decisions/ik-benchmark-limits.md) remain limitations.
- Next action: finish all-region test export, inspect RGB/trajectory evidence and transfer both datasets to the requested playback project.
- Last verification: **2026-11-17** — 14 processing checks and 6 official export integration checks passed; full iPhone export/transfer in progress. See the November action log.
