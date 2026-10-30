# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — user-directed IK experiments targeting >90/100; broader simulation acceptance remains open.
- Active plan: [IK configuration experiments](plans/milestone-3-ik-tuning.md), extending the fulfilled [benchmark plan](plans/milestone-3-ik-benchmark.md).
- Deliverable: reusable 100-point benchmark, preserved experiments/updating report, Config 2 palm/opening IK, missing-hand penalty and interactive viewer delivered. Roadmap simulation acceptance remains open.
- Completed outcome: all six leading distinct configurations rerun on reviewed **[0,269)** input with **461 observed hand samples**, excluding right-hand frame 29. Best **74.670** (`robust-position-limits`). [Report](../../outputs/ik-benchmark-reviewed/REPORT.md); >90 remains unachieved.
- Current work: fixed-base tolerance experiment scored 73.569; moving-base counterpart is running. All six reviewed runs independently audited. Robust pose-loss implementation passed derivative/settings/CPU–CUDA checks. Requested detached-target-gripper viewers are open at ports 8082/8083 without viewer review/tests. [Evidence](experiments/ik-benchmark-iphone.md#reviewed-region-restart).
- Blockers or decisions: CPU remains at 800 MHz with external PROCHOT asserted; exact platform component and repair remain unverified. No power protections or system settings changed. Motion/tracking tradeoff and the [10 rad/s² acceleration proxy](decisions/ik-benchmark-limits.md) remain; physical simulation acceptance is open.
- Next action: finish tolerance/base comparisons, then test robust pose losses against the best reviewed configuration; independently audit improvements. Preserve source data and old scores. Focused cleanup remains due before another milestone.
- Last verification: **2026-10-30** — [all six independent audits passed](../../outputs/ik-benchmark-reviewed/validation/top-six-audit.json); [21 selection/export checks](../../outputs/ik-benchmark-reviewed/validation/selection-tests.log), plus 12 robust-loss checks, 16 settings checks and 4 CPU/CUDA comparisons. >90 unachieved.
