# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK.
- Stage: **Validating** — requested Config 2 offset fulfilled; user comparison pending.
- Active plan: [Config 2 wrist offset, approved revision 1](plans/milestone-3-gripper-wrist-offset.md).
- Deliverable: reloadable full-video Config 2 with rear palm 25 mm backward along its existing forward axis and a separate comparison viewer.
- Completed outcome: 1,286 frames / 1,802 valid samples translated as requested, with unchanged orientation, roll, opening and source data. [Evidence](experiments/direct-gripper-iphone.md#config-2-backward-wrist-offset-2026-10-29).
- Current work: compare [shifted Config 2 :8097](http://localhost:8097) with [original :8094](http://localhost:8094). Earlier Configs 2/3/4 MP4s remain unchanged; baseline default remains.
- Blockers or decisions: no implementation blocker. Mapping selection, physical scale/contact, collisions/dynamics, earlier IK failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: user compares wrist placements; IK integration remains deferred. Focused cleanup remains due before another milestone.
- Last verification: **2026-10-29**, 47 tests passed, all-sample baseline comparison, browser checks and representative visual inspection. [Evidence](experiments/direct-gripper-iphone.md#config-2-backward-wrist-offset-2026-10-29).
