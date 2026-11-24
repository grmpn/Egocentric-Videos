# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — approved TACO ground-truth benchmark; broader simulation acceptance remains open.
- Active plan: [TACO hand-trajectory benchmark, approved revision 1](plans/taco-hand-trajectory-benchmark.md). Prior iPhone comparison and export plans remain fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: all three 1,286-frame camera runs, shared hands/gravity/depth, pairwise metrics and graphs verified; [comparison acceptance](experiments/iphone-trajectory-comparison.md). Prior [all-region export](topics/lerobot-pipeline.md#iphone-test-export--2026-11-17) remains delivered.
- Current work: five **150-frame** test clips frozen; evaluator/tables verified. First full HaWoR trial completed with inspected overlay/3D plot; four remain. Set up HandFlow, then assess StableHand recreation as requested; [benchmark contracts](topics/hand-trajectory-benchmark.md).
- Blockers or decisions: StableHand lacks released raw-video preprocessing and has GT-derived evaluation inputs. HandFlow environment/bimanual adaptation remains unverified. GT camera motion is only 25–71 mm and 3.8–13.2°; SLAM sufficiency is unknown. Dataset +Z-up convention is supported by released axes, not an independent gravity calibration.
- Next action: finish the remaining HaWoR trials and five HandFlow trials with timing/memory evidence; retain failures. Then assess StableHand preprocessing feasibility before proposing recreation.
- Last verification: **2026-11-24** — 37 metric/report/resource-runner tests pass; HaWoR clip 20231024_029 completed with 150 frames, 267.1 s elapsed and 13.66 GiB sampled peak. [Partial comparison](../../outputs/taco-benchmark/taco-five-20261124/comparison.md) is not a five-clip result. Broader milestone acceptance remains open.
