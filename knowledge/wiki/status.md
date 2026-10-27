# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Validating** — direct-mapping revision 7 fulfilled; roadmap simulation demonstration remains unaccepted.
- Active plan: [Direct hand-to-gripper mapping, approved revision 7](plans/milestone-3-direct-gripper-mapping.md), fulfilled. Earlier approved plans remain in the [index](index.md).
- Deliverable: detached, freely posed and actuated EZGrippers plus a synchronized MANO/direct-mapping viewer for iPhone frames **[0,296)**.
- Completed outcome: MCP/index-PIP plane orientation with exact fingertip-midpoint placement and unchanged FK-derived opening, verified for **296 frames / 470 eligible samples**. [Evidence](experiments/direct-gripper-iphone.md).
- Current work: user review in the [plane viewer](http://localhost:8091), paused at frame 119. Triangle, center errors and individual tip offsets are displayed; earlier mappings remain reproducible.
- Blockers or decisions: no implementation blocker. Mesh tip markers and physical scale/contact remain uncalibrated; collisions/dynamics, prior IK failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: review the plane-based orientation and fingertip offsets before choosing further changes. Alternative human contact landmarks, later regions and IK integration remain deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-27**, 28 focused tests, all-frame real-FK midpoint/plane-axis audit, browser playback/manual controls/snapshot, old/new reload and representative visual inspection pass. [Acceptance evidence](experiments/direct-gripper-iphone.md).
