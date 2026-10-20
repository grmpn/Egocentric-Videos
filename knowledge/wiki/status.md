# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Parts 1–3, MANO comparison and wrist alignment are complete; no next milestone has started.
- Stage: **Complete** — scoped positional deliverables and wrist/legacy playback verified; dynamic simulation/hardware remain outside acceptance.
- Active plan: [Wrist alignment amendment, revision 1](plans/milestone-3-wrist-alignment.md), fulfilled. Earlier fulfilled plans: [Part 3](plans/milestone-3-part-3-placement-and-segmentation.md), [Part 2](plans/milestone-3-part-2-robot-workspace.md), [Part 1](plans/milestone-3-part-1-gravity-alignment.md).
- Deliverable: base-frame hand trajectories, positional IK witnesses, annotated video and interactive playback using one fixed base per retained episode.
- Completed outcome: wrist-aligned episodes of 1.933 s / 1.667 s, combined SDF/IK coverage 96.55% / 96.00%; all 212 successful arm poses independently verified, maximum wrist error 2.493 mm. 28 focused tests and wrist/legacy browser review passed. [Acceptance and artifacts](experiments/retargeting-bundled.md#wrist-alignment-amendment).
- Current work: no remaining wrist-alignment implementation. Preview replays saved per-frame position-only IK; orientation is unconstrained. [Current contract](topics/stage-3-retargeting.md#part-3-placement-and-ik-contract).
- Blockers or decisions: no blocker to scoped completion. Three right-hand IK failures, one large joint change and unassigned frames 58–70 remain explicit. Collision/dynamics, scale, gravity and floor height remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review are outstanding.
- Next action: focused repository cleanup before another milestone; preserve acceptance evidence. Process iPhone MP4s under the existing pilot plan when available.
- Last verification: **2026-10-20**, wrist FK, source/MANO geometry, focused tests and corrected failed-gripper/legacy playback passed; `20261020-wrist-alignment-007` in the [action log](logs/2026-10.jsonl).
