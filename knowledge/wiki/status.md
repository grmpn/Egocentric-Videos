# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — approved TACO ground-truth benchmark; broader simulation acceptance remains open.
- Active plan: [TACO hand-trajectory benchmark, approved revision 1](plans/taco-hand-trajectory-benchmark.md). Prior iPhone comparison and export plans remain fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: all three 1,286-frame camera runs, shared hands/gravity/depth, pairwise metrics and graphs verified; [comparison acceptance](experiments/iphone-trajectory-comparison.md). Prior [all-region export](topics/lerobot-pipeline.md#iphone-test-export--2026-11-17) remains delivered.
- Current work: five **150-frame** test clips frozen; all five HaWoR trials completed and overlays inspected. First full HandFlow trial and mirrored-hand/3D plot review passed; remaining four are running sequentially. [Benchmark contracts](topics/hand-trajectory-benchmark.md).
- Blockers or decisions: StableHand lacks released raw-video preprocessing and has GT-derived evaluation inputs; assess recreation after HaWoR/HandFlow. HandFlow's missing dependencies were resolved and failed setup evidence retained. GT camera motion is only 25–71 mm and 3.8–13.2°; SLAM sufficiency is unknown. Dataset +Z-up convention is supported by released axes, not an independent gravity calibration.
- Next action: finish four HandFlow trials and the two-method comparison, then assess StableHand preprocessing feasibility before proposing recreation.
- Last verification: **2026-11-24** — 40 focused tests pass; 14 rechecked after setup-attempt reporting changes. HaWoR mean initial wrist error 64.22 mm, PA-MPJPE 10.73 mm, 0.56 FPS, 100% coverage. HandFlow first clip: 187.1 s, 0.80 FPS, 12.17 GiB peak. [Comparison](../../outputs/taco-benchmark/taco-five-20261124/comparison.md) is complete for HaWoR and partial for HandFlow. Broader milestone acceptance remains open.
