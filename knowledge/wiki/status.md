# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Validating** — direct-mapping revision 5 fulfilled; roadmap simulation demonstration remains unaccepted.
- Active plan: [Direct hand-to-gripper mapping, approved revision 5](plans/milestone-3-direct-gripper-mapping.md), fulfilled. Earlier approved plans remain in the [index](index.md).
- Deliverable: detached, freely posed and actuated EZGrippers plus a synchronized MANO/direct-mapping viewer for iPhone frames **[0,296)**.
- Completed outcome: 2.5 cm thumbward wrist shift with preserved forward direction verified for **296 frames / 470 eligible samples**; right frames 92/119 command **0.03/0.33**. [Evidence](experiments/direct-gripper-iphone.md).
- Current work: user review in the [shifted-wrist viewer](http://localhost:8091), paused at frame 119. Shift distance is adjustable and saved in snapshots; prior mappings retain their original rules.
- Blockers or decisions: normalization examples are resolved (frame 119 replaces 199); the fully-open threshold is extrapolated and contact alignment remains uncalibrated. Physical scale/gravity, collisions and dynamics remain unverified; prior IK pose/gap failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: review the refined orientation and opening response before choosing further changes. Thumb-IP/index-PIP center comparison, later regions and IK integration remain deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-27**, 22 focused tests, all-frame shift/axis audit, browser playback/shift adjustment/reset, old/new reload and representative visual inspection pass. [Acceptance evidence](experiments/direct-gripper-iphone.md).
