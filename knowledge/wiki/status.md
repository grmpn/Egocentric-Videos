# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, MANO comparison, wrist alignment and the joint/base optimization extension.
- Stage: **Complete** — the approved extension passed numerical, visual and comparison acceptance.
- Active plan: [Joint base and trajectory optimization, approved revision 1](plans/milestone-3-joint-base-optimization.md). Fulfilled baseline: [wrist alignment amendment](plans/milestone-3-wrist-alignment.md), with earlier Parts 1–3 linked from the [index](index.md).
- Deliverable: joint XYZ/yaw base fitting, wrist pose and head rotation matching, then fixed-base trajectory smoothing within heuristic regions; existing viewer and runtime/quality comparison against workspace placement.
- Completed outcome: both unexpanded regions pass at 100% (83 frames / 166 hands; maximum 0.704 mm / 6.191°), with reduced acceleration RMS. 53 tests, independent FK/source audit and new/legacy viewer checks passed. Three-run median solve: joint 70.468 s, workspace 2.161 s. [Acceptance and artifacts](experiments/joint-base-bundled.md).
- Current work: approved deliverable complete; [commands and contracts](topics/stage-3-retargeting.md#joint-base-and-pose-trajectory-contract) support both methods.
- Blockers or decisions: none for this scope. Head error, sharp joint motion, collision clearance and physical calibration remain execution limitations. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: start focused repository cleanup before another milestone; preserve acceptance evidence. Further motion-quality or hardware work needs its own agreed scope.
- Last verification: **2026-10-20**, production, independent FK/data/camera-boundary audits, three timed repeats and final browser inspection. See [acceptance evidence](experiments/joint-base-bundled.md) and `20261020-joint-base-implementation-008` in the [action log](logs/2026-10.jsonl).
