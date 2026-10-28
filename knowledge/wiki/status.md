# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Validating** — revision 10 comparison fulfilled; user method selection pending.
- Active plan: [Full-video gripper comparison, approved revision 10](plans/milestone-3-direct-gripper-mapping.md). Earlier plans remain in the [index](index.md).
- Deliverable: three saved overlay MP4s for Configs 2/3/4 over all **1,286 iPhone frames**, plus reloadable mappings.
- Completed outcome: Config 4 interpolated-thumb plane and full overlays verified; **1,802 eligible samples per configuration**, source/timing preserved. [Videos and evidence](experiments/direct-gripper-iphone.md#full-video-configs-234-2026-10-28).
- Current work: user compares full videos; original viewers 8091–8095 remain available. Config 4 uses the requested index→thumb-point jaw and 30°–45° roll weights. Baseline default remains.
- Blockers or decisions: no implementation blocker. Physical scale/contact, scene occlusion, collisions/dynamics, earlier IK failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: select/refine the mapping after video review; pose jumps up to 69° remain. IK integration is deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-28**, 45 tests, all-sample FK/geometry/source/camera audit, three complete MP4 decode/timestamp checks, representative visual review and Config 4 browser/snapshot reload pass. [Evidence](experiments/direct-gripper-iphone.md#full-video-configs-234-2026-10-28).
