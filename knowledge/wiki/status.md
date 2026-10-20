# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, MANO comparison, wrist alignment and the joint/base optimization extension.
- Stage: **Validating** — gripper-offset implementation verified; controlled production sweep next.
- Active plan: [Joint base and trajectory optimization, approved revision 4](plans/milestone-3-joint-base-optimization.md). Fulfilled baseline: [wrist alignment amendment](plans/milestone-3-wrist-alignment.md), with earlier Parts 1–3 linked from the [index](index.md).
- Deliverable: 5 cm gripper-relative wrist match point, alternate-frame joint/base fitting and full-frame trajectory smoothing, with a controlled hand-weight comparison.
- Completed outcome (revision 3): camera position RMS improves 30.7→26.9 cm, with worse head rotation and wrist coverage. Weights 0.02/0.1/0.5 retain region 1; 2.0 rejects both. 0.5 is the strongest tested weight retaining a qualifying region. [Comparison and artifacts](experiments/joint-base-bundled.md#camera-position-and-posture-weight-sweep).
- Current work: implementation complete for fingerward offset, posture 0.5, rotation-only camera objective and alternate-frame base fitting; run the hand residual-weight sweep.
- Blockers or decisions: substantial camera/head error, rejected first region, budget-limited fits, collision clearance and physical calibration remain limitations. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: run four controlled hand-weight trials, audit full-frame outputs and inspect playback. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-20**, 54 focused tests pass for revised FK/objective/sampling contracts; `20261020-gripper-offset-003` in the [action log](logs/2026-10.jsonl). Production and visual review remain pending; earlier benchmarks are historical evidence.
