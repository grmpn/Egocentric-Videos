# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Parts 1–2 are complete; the overall milestone is not. The user authorized starting ahead of iPhone capture on 2026-10-14.
- Stage: **Planning** — Part 3 draft revision 1 is ready for review; implementation is not approved.
- Active plan: [Part 3: Placement and segmentation, draft revision 1](plans/milestone-3-part-3-placement-and-segmentation.md). [Part 2 revision 2](plans/milestone-3-part-2-robot-workspace.md) and [Part 1](plans/milestone-3-part-1-gravity-alignment.md) are fulfilled.
- Deliverable: Stage 3 outputs hand trajectories in the robot base frame with verified kinematic limits. Parts 1–2 supply shared Z-up trajectories and sampled robot workspaces.
- Completed outcome: 10 million FK samples per arm produce separate 2 cm grids/distance tensors with 99.91% left / 99.92% right held-out occupancy coverage (9/8 misses of 10,000 per arm). Build time 32.81 s, peak RSS 2.33 GiB; 10 focused tests passed. [Part 2 acceptance](experiments/robot-workspace-purdue.md); [Part 1 acceptance](experiments/gravity-alignment-bundled.md).
- Current work: draft captures the updated Part 3 spec: camera segmentation, XYZ/yaw placement, interval expansion and positional IK using the preferred 10 million sample workspaces.
- Blockers or decisions: Part 3 approval pending, including proposed missing-hand handling and position-only wrist-to-TCP IK. Sampled occupancy, metric scale and gravity accuracy remain limited; collision/dynamic feasibility is outside the draft. Milestone 2 iPhone capture, [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review and explicitly approve or revise the Part 3 draft before implementation. Process iPhone MP4s under the existing pilot plan when available.
- Last verification: **2026-10-16**, draft checked against the updated spec and existing contracts; documentation checks recorded as `20261016-part-3-planning-002` in the [action log](logs/2026-10.jsonl). No implementation or new runtime validation; prior numerical/visual acceptance remains linked above.
