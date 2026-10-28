# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Validating** — revision 9 comparison fulfilled; user method selection pending.
- Active plan: [Direct hand-to-gripper comparison, approved revision 9](plans/milestone-3-direct-gripper-mapping.md). Earlier approved plans remain in the [index](index.md).
- Deliverable: preserved comparison viewers plus updated Config 2 and adjustable Config 3 for iPhone frames **[0,296)**.
- Completed outcome: fingertip-forward wrist mapping and roll blend verified for **470 eligible samples each**, preserving opening/source fields and nine historical mappings. [Evidence](experiments/direct-gripper-iphone.md#fingertip-forward-and-roll-blend-2026-10-28).
- Current work: review [updated Config 2 :8094](http://localhost:8094) and [Config 3 :8095](http://localhost:8095), verified at frame 119. Config 3 transitions at |roll| 30°–45° with adjustable thresholds. Existing viewers 8091–8093 and baseline default remain.
- Blockers or decisions: no implementation blocker. Mesh tip markers and physical scale/contact remain uncalibrated; collisions/dynamics, prior IK failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: user compares/tunes configurations and selects or requests refinement. The left frame-272 orientation step remains; later regions/IK are deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-28**, 41 tests; full FK/roll/blend/source audit, motion comparison, browser threshold/manual/snapshot checks, old/new reload and representative visual inspection pass. [Acceptance evidence](experiments/direct-gripper-iphone.md#fingertip-forward-and-roll-blend-2026-10-28).
