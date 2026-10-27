# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Validating** — direct-mapping plan fulfilled; roadmap simulation demonstration remains unaccepted.
- Active plan: [Direct hand-to-gripper mapping, approved revision 1](plans/milestone-3-direct-gripper-mapping.md), fulfilled. Earlier approved plans remain in the [index](index.md).
- Deliverable: detached, freely posed and actuated EZGrippers plus a synchronized MANO/direct-mapping viewer for iPhone frames **[0,296)**.
- Completed outcome: standalone left/right grippers and direct MANO mapping verified for all **296 frames / 470 eligible hand samples**, with numerical and browser/visual acceptance. [Evidence](experiments/direct-gripper-iphone.md).
- Current work: user review in the [direct gripper viewer](http://localhost:8091); initial 10 cm opening scale and zero TCP corrections retained. Tuning controls save independent snapshots; manual controls freely pose and actuate grippers without IK.
- Blockers or decisions: no implementation blocker. Opening clips 108/470 samples fully open; nominal TCP/contact alignment needs user review. Physical scale/gravity, collisions and dynamics remain unverified; prior IK pose/gap failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: review hand/gripper alignment and opening scale before choosing refinements. Thumb-IP/index-PIP comparison, later regions and IK integration remain deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-27**, 12 focused tests, all-frame geometry/RGB/browser audits, manual controls, saved-tuning reload and representative visual inspection pass. [Acceptance evidence](experiments/direct-gripper-iphone.md).
