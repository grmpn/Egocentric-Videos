# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Validating** — GPU solver and matched benchmarks verified; full iPhone rerun starting.
- Active plan: [GPU trajectory IK, approved revision 1](plans/milestone-3-gpu-ik.md). The [approved stronger-smoothing experiment](plans/milestone-3-joint-base-optimization.md) is fulfilled; earlier plans remain in the [index](index.md).
- Deliverable: GPU solver, measured runtime/quality comparison and rerun of the latest iPhone smoothing configuration, preserving the objective, bounds and acceptance gates.
- Completed outcome: >0.5 rad change frames fall 116 → 0 within regions, or 116 → 1 including the adjacent region reset; acceleration RMS 246.85 → 5.32 rad/s². Pose passes fall 855/957 → 189/957. [Comparison, plots and playback](experiments/retargeting-iphone.md#stronger-temporal-smoothing).
- Current work: CUDA backend implemented; 66 focused tests pass. Matched first-region base/trajectory speedups are 2.8×/4.1×; complete latest-configuration rerun follows. Latest run uses velocity 1.0 / acceleration 0.5; defaults remain 0.001 / 0.0005, with hand weights 1.0 and infilled observations excluded.
- Blockers or decisions: pose/gap gates still fail; frame 1113 has a 3.136 rad region-reset jump. First two selected trajectory solves exhaust their budgets. Physical scale/gravity, collisions and dynamics remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: complete the GPU rerun, audit saved geometry/gates and inspect visual comparisons. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-22**, 66 focused tests and dependency check pass; matched two-region benchmark complete. Prior completed trajectory validation remains `20261021-smooth1000-006` in the [action log](logs/2026-10.jsonl); full GPU rerun pending.
