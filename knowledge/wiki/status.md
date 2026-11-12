# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Validating** — export refresh is verified; broader simulation acceptance remains open.
- Active plan: [LeRobot export refresh, revision 1](plans/lerobot-export-refresh.md), approved and fulfilled 2026-11-12. Prior cleanup and held-out evaluation scope remain fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: independent structured human LeRobot data, region-based robot data with FK actions, masks/statistics/training support, updated shell/annotation workflow and standalone human reuse. [Acceptance evidence](topics/lerobot-pipeline.md#export-refresh-acceptance--2026-11-12).
- Current work: implementation and focused validation complete; final repository handoff. Historical datasets and processing artifacts remain preserved.
- Blockers or decisions: the saved 121-frame example's two regions fail geometric acceptance and are correctly rejected. Tracking/collision failures, unmeasured scale/floor, the [acceleration proxy](decisions/ik-benchmark-limits.md) and pending language review remain limitations.
- Next action: agree the remaining Milestone 3 simulation demonstration and acceptance evidence using the refreshed workflow; no solver changes or next milestone started.
- Last verification: **2026-11-12** — 114 processing checks, official LeRobot/annotation integration, saved-stage shell run, real MANO/TCP and RGB review, and standalone human reconstruction/mapping; see the linked acceptance evidence and November action log.
