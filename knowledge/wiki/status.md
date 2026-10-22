# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Implementing** — hand-pose refinement revision 1 explicitly approved on 2026-10-22.
- Active plan: [Hand-pose smoothing and region continuity, approved revision 1](plans/milestone-3-hand-pose-refinement.md). The [GPU plan](plans/milestone-3-gpu-ik.md) is fulfilled; earlier plans remain in the [index](index.md).
- Deliverable: configurable Savitzky–Golay hand-target smoothing, a weak median-camera base prior, adjacent retained-region merging and controlled CUDA comparisons with a complete iPhone rerun.
- Completed outcome: GPU solve 1,793.37 → 285.15 s (**6.29×**); pose passes remain 189/957 and no demonstration is accepted. [Comparison and acceptance evidence](experiments/retargeting-iphone.md#gpu-solver-rerun-2026-10-22).
- Current work: implemented target smoothing, base prior and region merging; 84 focused tests pass. Controlled experiments are next. Smoothing acts on derived position/orientation targets; merging occurs after duration filtering. Original observations still determine acceptance. Latest CUDA experiment with temporal weights 1.0/0.5 is the comparison baseline.
- Blockers or decisions: pose/gap gates still fail; frame 1113 has a 3.133 rad region-reset jump. Orientation RMS increases 26.99° → 28.18°; first two selected trajectory solves exhaust their budgets. Physical scale/gravity, collisions and dynamics remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: run isolated/combined CUDA comparisons on the final iPhone regions, then the complete iPhone workflow and visual audits. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-22**, 84 filtering/pose/retargeting/workspace tests pass; `20261022-pose-refinement-004` in the [action log](logs/2026-10.jsonl). Log: `outputs/retargeting/pose-refinement-20261022/tests.log`; no new iPhone solver results yet.
