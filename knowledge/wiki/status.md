# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Validating** — comparison revision 8 fulfilled; user method selection pending.
- Active plan: [Direct hand-to-gripper comparison, approved revision 8](plans/milestone-3-direct-gripper-mapping.md). Earlier approved plans remain in the [index](index.md).
- Deliverable: original detached-gripper viewer plus two independent configuration viewers for iPhone frames **[0,296)**, supporting method selection.
- Completed outcome: thumb-IP plane and wrist-anchor/roll variants verified for **470 eligible samples each**, retaining opening/source data and historical mappings. [Evidence](experiments/direct-gripper-iphone.md#two-method-comparison-2026-10-28).
- Current work: compare [baseline :8091](http://localhost:8091), [Config 1 :8092](http://localhost:8092) and [Config 2 :8093](http://localhost:8093). Both new viewers are paused at frame 119; original window preserved. Default remains baseline.
- Blockers or decisions: no implementation blocker. Mesh tip markers and physical scale/contact remain uncalibrated; collisions/dynamics, prior IK failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: user compares the three methods and selects or requests refinement. Later regions and IK integration remain deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-28**, 34 focused tests, all-sample FK/axis/anchor/roll audit, browser playback/manual controls/snapshots, old/new reload and representative visual inspection pass. [Acceptance evidence](experiments/direct-gripper-iphone.md#two-method-comparison-2026-10-28).
