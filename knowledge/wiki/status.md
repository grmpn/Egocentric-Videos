# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Parts 1–3, MANO comparison and wrist alignment are complete; the user requested a joint/base optimization extension.
- Stage: **Planning** — draft prepared; implementation awaits explicit approval.
- Active plan: [Joint base and trajectory optimization, draft revision 1](plans/milestone-3-joint-base-optimization.md). Fulfilled baseline: [wrist alignment amendment](plans/milestone-3-wrist-alignment.md), with earlier Parts 1–3 linked from the [index](index.md).
- Deliverable: proposed joint XYZ/yaw base fitting, wrist pose and head rotation matching, then fixed-base trajectory smoothing within heuristic regions; existing viewer and runtime/quality comparison against workspace placement.
- Completed outcome: wrist-aligned episodes of 1.933 s / 1.667 s, combined SDF/IK coverage 96.55% / 96.00%; all 212 successful arm poses independently verified, maximum wrist error 2.493 mm. 28 focused tests and wrist/legacy browser review passed. [Acceptance and artifacts](experiments/retargeting-bundled.md#wrist-alignment-amendment).
- Current work: drafted from `Milestone3-Update.md` and the user's clarification: camera position initializes the base only; per-frame head fitting uses rotation. Existing implementation remains position-only. [Current contract](topics/stage-3-retargeting.md#part-3-placement-and-ik-contract).
- Blockers or decisions: draft approval pending, including proposed arm/neck joint scope and pose acceptance. Robot/MANO and camera optical-frame mappings need verification during implementation. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review and approve or revise the draft. Focused repository cleanup remains due before another milestone; preserve acceptance evidence.
- Last verification: **2026-10-20**, planning checked against current code, settings and pinned URDF; no solver rerun. Prior executed acceptance: `20261020-wrist-alignment-007` in the [action log](logs/2026-10.jsonl).
