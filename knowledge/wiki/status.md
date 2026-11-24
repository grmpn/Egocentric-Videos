# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — approved TACO ground-truth benchmark; broader simulation acceptance remains open.
- Active plan: [TACO hand-trajectory benchmark, approved revision 1](plans/taco-hand-trajectory-benchmark.md). Prior iPhone comparison and export plans remain fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: all three 1,286-frame camera runs, shared hands/gravity/depth, pairwise metrics and graphs verified; [comparison acceptance](experiments/iphone-trajectory-comparison.md). Prior [all-region export](topics/lerobot-pipeline.md#iphone-test-export--2026-11-17) remains delivered.
- Current work: five **150-frame** test clips are frozen and synchronized; GT overlays reviewed, evaluator/tables implemented. Connect complete native pipelines; [benchmark contracts](topics/hand-trajectory-benchmark.md).
- Blockers or decisions: StableHand lacks released raw-video preprocessing and has GT-derived evaluation inputs. HandFlow environment/bimanual adaptation remains unverified. GT camera motion is only 25–71 mm and 3.8–13.2°; SLAM sufficiency is unknown. Dataset +Z-up convention is supported by released axes, not an independent gravity calibration.
- Next action: finish native adapters and prerequisite validation, then run uncached trials with timing/memory evidence; retain failures and all selected clips.
- Last verification: **2026-11-24** — five synchronized references and GT/RGB contact sheet; [setup evidence](experiments/taco-benchmark-preflight.md#verified-setup--2026-11-24). No TACO method accuracy/speed results yet. Prior [iPhone comparison acceptance](experiments/iphone-trajectory-comparison.md) remains unchanged.
