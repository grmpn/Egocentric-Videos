# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, MANO comparison, wrist alignment and the joint/base optimization extension.
- Stage: **Validating** — camera position objective implemented; 47 focused tests passed; posture sweep next.
- Active plan: [Joint base and trajectory optimization, approved revision 3](plans/milestone-3-joint-base-optimization.md). Fulfilled baseline: [wrist alignment amendment](plans/milestone-3-wrist-alignment.md), with earlier Parts 1–3 linked from the [index](index.md).
- Deliverable: joint XYZ/yaw base fitting, wrist pose and head rotation matching, then fixed-base trajectory smoothing within heuristic regions; existing viewer and runtime/quality comparison against workspace placement.
- Completed outcome: median trial passes 44/52 frames in region 0 (rejected) and 31/31 in region 1 (accepted), versus both at 100% with mean initialization. 45 tests, independent FK/source audit and browser review passed. [Comparison and artifacts](experiments/joint-base-bundled.md#median-initialization-trial).
- Current work: add a weighted camera position term in both stages, preserve median initialization and sweep posture residual weights 0.02/0.1/0.5/2.0.
- Blockers or decisions: median initialization worsens this clip's wrist-orientation coverage and motion smoothness. Head error, collision clearance and physical calibration remain execution limitations. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: run the controlled posture sweep, audit saved FK and review low/high-weight playback. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-20**, median production rerun, 45 focused tests, independent FK/acceptance labels and actual-failure browser inspection; `20261020-median-heading-004` in the [action log](logs/2026-10.jsonl). The previous three-run benchmark remains historical evidence.
