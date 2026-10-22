# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Complete** — GPU solver and latest-configuration rerun verified; no accepted demonstration.
- Active plan: [GPU trajectory IK, approved revision 1](plans/milestone-3-gpu-ik.md). The [approved stronger-smoothing experiment](plans/milestone-3-joint-base-optimization.md) is fulfilled; earlier plans remain in the [index](index.md).
- Deliverable: GPU solver, measured runtime/quality comparison and rerun of the latest iPhone smoothing configuration, preserving the objective, bounds and acceptance gates.
- Completed outcome: solve 1,793.37 → 285.15 s (**6.29×**), total 1,809.46 → 301.41 s; pose passes remain 189/957. Matched first-region base/trajectory speedups are 2.76×/4.14×. [Comparison and acceptance evidence](experiments/retargeting-iphone.md#gpu-solver-rerun-2026-10-22).
- Current work: requested GPU work complete. CUDA is the default backend; default temporal weights remain 0.001/0.0005. Latest experiment retains 1.0/0.5, hand weights 1.0 and infill exclusion. Full-result viewer: localhost:8080.
- Blockers or decisions: pose/gap gates still fail; frame 1113 has a 3.133 rad region-reset jump. Orientation RMS increases 26.99° → 28.18°; first two selected trajectory solves exhaust their budgets. Physical scale/gravity, collisions and dynamics remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review pose/smoothing tradeoff and boundary reset before authorizing further tuning. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-22**, 66 tests, dependency check, matched benchmark, full rerun, independent source/FK/bounds/objective/gate/jump checks, all 1,286 video timestamps and 22-frame browser/visual review; `20261022-gpu-ik-010` in the [action log](logs/2026-10.jsonl).
