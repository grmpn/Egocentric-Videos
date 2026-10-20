# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Parts 1–3, MANO comparison and wrist alignment are complete; the user requested a joint/base optimization extension.
- Stage: **Validating** — joint/base implementation and numerical acceptance passed; final viewer and timing comparison pending.
- Active plan: [Joint base and trajectory optimization, approved revision 1](plans/milestone-3-joint-base-optimization.md). Fulfilled baseline: [wrist alignment amendment](plans/milestone-3-wrist-alignment.md), with earlier Parts 1–3 linked from the [index](index.md).
- Deliverable: joint XYZ/yaw base fitting, wrist pose and head rotation matching, then fixed-base trajectory smoothing within heuristic regions; existing viewer and runtime/quality comparison against workspace placement.
- Completed outcome: wrist-aligned episodes of 1.933 s / 1.667 s, combined SDF/IK coverage 96.55% / 96.00%; all 212 successful arm poses independently verified, maximum wrist error 2.493 mm. 28 focused tests and wrist/legacy browser review passed. [Acceptance and artifacts](experiments/retargeting-bundled.md#wrist-alignment-amendment).
- Current work: both heuristic regions pass the new pose gates (166 observed hands; maximum 0.704 mm / 6.191°), with reduced acceleration RMS. Final browser/legacy checks and three-run timing comparison remain. [New evidence](experiments/joint-base-bundled.md). [Current contract](topics/stage-3-retargeting.md#joint-base-and-pose-trajectory-contract).
- Blockers or decisions: Robot/MANO and nominal optical-axis mappings are documented and numerically checked; physical calibration remains unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: finish viewer checks and the controlled comparison, then audit all acceptance evidence. Focused repository cleanup remains due before another milestone; preserve acceptance evidence.
- Last verification: **2026-10-20**, joint production CLI, independent FK and source preservation passed. Prior baseline acceptance: `20261020-wrist-alignment-007` in the [action log](logs/2026-10.jsonl).
