# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Planning** — hand-pose refinement draft awaiting approval; no implementation started.
- Active plan: [Hand-pose smoothing and region continuity, draft revision 1](plans/milestone-3-hand-pose-refinement.md). The [GPU plan](plans/milestone-3-gpu-ik.md) is fulfilled; earlier plans remain in the [index](index.md).
- Deliverable proposed: configurable Savitzky–Golay hand-target smoothing, a weak median-camera base prior, adjacent retained-region merging and controlled CUDA comparisons with a complete iPhone rerun.
- Completed outcome: GPU solve 1,793.37 → 285.15 s (**6.29×**); pose passes remain 189/957 and no demonstration is accepted. [Comparison and acceptance evidence](experiments/retargeting-iphone.md#gpu-solver-rerun-2026-10-22).
- Current work: plan review. Proposed smoothing acts on derived position/orientation targets; merging occurs after duration filtering. Original observations still determine acceptance. Latest CUDA experiment with temporal weights 1.0/0.5 is the comparison baseline.
- Blockers or decisions: pose/gap gates still fail; frame 1113 has a 3.133 rad region-reset jump. Orientation RMS increases 26.99° → 28.18°; first two selected trajectory solves exhaust their budgets. Physical scale/gravity, collisions and dynamics remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: obtain explicit approval of draft revision 1 before implementation. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-22**, planning reviewed against current code and saved segmentation; `20261022-pose-refinement-001` in the [action log](logs/2026-10.jsonl). Latest executable evidence remains the 66-test CUDA validation and full rerun (`20261022-gpu-ik-010`); no new solver results claimed.
