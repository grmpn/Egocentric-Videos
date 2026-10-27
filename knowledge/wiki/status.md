# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Validating** — direct-mapping revision 6 fulfilled; roadmap simulation demonstration remains unaccepted.
- Active plan: [Direct hand-to-gripper mapping, approved revision 6](plans/milestone-3-direct-gripper-mapping.md), fulfilled. Earlier approved plans remain in the [index](index.md).
- Deliverable: detached, freely posed and actuated EZGrippers plus a synchronized MANO/direct-mapping viewer for iPhone frames **[0,296)**.
- Completed outcome: exact two-tip correspondence with FK-derived opening and true wrist→thumb MCP twist direction, verified for **296 frames / 470 eligible samples**. [Evidence](experiments/direct-gripper-iphone.md).
- Current work: user review in the [tip-matching viewer](http://localhost:8091), paused at frame 119. Both marker errors are displayed; prior mappings retain their original rules.
- Blockers or decisions: no implementation blocker. Mesh tip markers and physical scale/contact remain uncalibrated; collisions/dynamics, prior IK failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: review tip placement and twist before choosing further changes. Alternative human contact landmarks, later regions and IK integration remain deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-27**, 25 focused tests, all-frame real-FK correspondence/axis audit, browser playback/manual controls/snapshot, old/new reload and representative visual inspection pass. [Acceptance evidence](experiments/direct-gripper-iphone.md).
