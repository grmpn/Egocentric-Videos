# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Validating** — direct-mapping revision 2 fulfilled; roadmap simulation demonstration remains unaccepted.
- Active plan: [Direct hand-to-gripper mapping, approved revision 2](plans/milestone-3-direct-gripper-mapping.md), fulfilled. Earlier approved plans remain in the [index](index.md).
- Deliverable: detached, freely posed and actuated EZGrippers plus a synchronized MANO/direct-mapping viewer for iPhone frames **[0,296)**.
- Completed outcome: thumb MCP→IP forward axis and opening fit verified for **296 frames / 470 eligible samples**; right frames 92/119 command **0.03/0.33**. [Evidence](experiments/direct-gripper-iphone.md).
- Current work: user review in the [refined viewer](http://localhost:8091), paused at frame 119. Original first-pass mapping preserved; old runs and new tuning snapshots reload successfully.
- Blockers or decisions: normalization examples are resolved (frame 119 replaces 199); the fully-open threshold is extrapolated and contact alignment remains uncalibrated. Physical scale/gravity, collisions and dynamics remain unverified; prior IK pose/gap failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: review the refined orientation and opening response before choosing further changes. Thumb-IP/index-PIP center comparison, later regions and IK integration remain deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-27**, 15 focused tests, all-frame geometry/anchor audit, full browser playback, old/new saved-result reload and representative visual inspection pass. [Acceptance evidence](experiments/direct-gripper-iphone.md).
