# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — user-directed IK experiments targeting >90/100; broader simulation acceptance remains open.
- Active plan: [IK configuration experiments](plans/milestone-3-ik-tuning.md), extending the fulfilled [benchmark plan](plans/milestone-3-ik-benchmark.md).
- Deliverable: reusable 100-point benchmark, preserved experiments/updating report, Config 2 palm/opening IK, missing-hand penalty and interactive viewer delivered. Roadmap simulation acceptance remains open.
- Completed outcome: best current first-region **[0,296)** score **74.680**, from 100× lower temporal weights (previous best 70.806). Same 296 frames / 470 observed hand samples. [Local report](../../outputs/ik-benchmark/REPORT.md); >90 remains unachieved.
- Current work: initial sweeps mostly complete; testing robust position loss after identifying a few target jumps that dominate squared error. Scoring and Config 2 targets remain unchanged.
- Blockers or decisions: motion/tracking tradeoff remains; acceleration is an explicit [10 rad/s² proxy](decisions/ik-benchmark-limits.md). Runs use CUDA, but host CPU clocks remain ~800 MHz under load ([measurements](../../outputs/ik-benchmark/validation/tuning/runtime-hardware.txt)); cause unverified, no system settings changed. Physical simulation and pilot acceptance remain open.
- Next action: let the live SDF run finish, then profile the tested robust-loss/limit-penalty configuration in isolation with video skipped. Focused cleanup remains due before another milestone.
- Last verification: **2026-10-30** — [8 robust objective/CPU-CUDA checks](../../outputs/ik-benchmark/validation/tuning/huber-final-tests.log), [60 IK tests](../../outputs/ik-benchmark/validation/tuning/motion-tests.log), [3 SDF checks](../../outputs/ik-benchmark/validation/tuning/sdf-tests.log), and [independent 72.621-run audit](../../outputs/ik-benchmark/validation/tuning/audit-temporal-low.json). Later scores await independent audit; >90 remains unachieved.
