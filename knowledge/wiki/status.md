# Project status

- Current milestone: **3 — Hand-to-gripper mapping**, isolated from arm IK for this refinement.
- Stage: **Implementing** — direct mapping approved; roadmap simulation demonstration remains unaccepted.
- Active plan: [Direct hand-to-gripper mapping, approved revision 1](plans/milestone-3-direct-gripper-mapping.md). Earlier approved plans remain in the [index](index.md).
- Deliverable: detached, freely posed and actuated EZGrippers plus a synchronized MANO/direct-mapping viewer for iPhone frames **[0,296)**.
- Completed outcome: prior hand-pose refinement experiment fulfilled; controlled comparisons and full rerun are preserved in the [acceptance evidence](experiments/hand-pose-refinement.md). They do not establish an accepted robot demonstration.
- Current work: implementing detached gripper geometry, landmark-derived poses/opening and interactive first-region playback under the approved scope.
- Blockers or decisions: no implementation blocker. Opening scale and nominal TCP alignment are provisional tuning parameters. Physical scale/gravity, collisions and dynamics remain unverified; prior IK pose/gap failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md)/Eidon review remain unresolved.
- Next action: verify detached articulation and direct mapping, then inspect first-region playback. Thumb-IP/index-PIP comparison and later regions are deferred. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-27**, planning inputs statically inspected; documentation checks recorded in `20261027-gripper-plan-003` in the [action log](logs/2026-10.jsonl). No new mapping or runtime validation claimed.
