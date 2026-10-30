# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — user-directed IK experiments targeting >90/100; broader simulation acceptance remains open.
- Active plan: [IK configuration experiments](plans/milestone-3-ik-tuning.md), extending the fulfilled [benchmark plan](plans/milestone-3-ik-benchmark.md).
- Deliverable: reusable 100-point benchmark, preserved experiments/updating report, Config 2 palm/opening IK, missing-hand penalty and interactive viewer delivered. Roadmap simulation acceptance remains open.
- Completed outcome: best current first-region **[0,296)** score **72.621**, from 10× lower temporal weights (previous best 70.806). Same 296 frames / 470 observed hand samples. [Local report](../../outputs/ik-benchmark/REPORT.md); >90 remains unachieved.
- Current work: controlled temporal-weight, motion-limit penalty and SDF-base experiments with unchanged scoring and Config 2 targets.
- Blockers or decisions: acceleration uses an explicit [10 rad/s² benchmark proxy](decisions/ik-benchmark-limits.md). Lower temporal weights improve orientation but cause 211/296 joint-infeasible frames. Physical scale/contact/dynamics and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md) remain unresolved.
- Next action: finish the active temporal sweep, then benchmark the tested limit-penalty and SDF variants. Focused cleanup remains due before another milestone.
- Last verification: **2026-10-30** — [60 IK tests](../../outputs/ik-benchmark/validation/tuning/motion-tests.log), [3 SDF checks](../../outputs/ik-benchmark/validation/tuning/sdf-tests.log), [hinge boundary check](../../outputs/ik-benchmark/validation/tuning/hinge-boundary.log), and [palm workspace FK](../../outputs/ik-benchmark/palm-workspace/workspace_report.json). Existing scores retain their [independent audit](../../outputs/ik-benchmark/validation/first-region/audit.json); new experiments remain in progress.
