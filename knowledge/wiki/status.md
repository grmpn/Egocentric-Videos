# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Parts 1–2 are complete; the overall milestone is not. The user authorized starting ahead of iPhone capture on 2026-10-14.
- Stage: **Planning** — Part 2 and its density extension are complete; Part 3 has no approved implementation plan.
- Active plan: [Part 2: Robot workspace, approved revision 2](plans/milestone-3-part-2-robot-workspace.md), fulfilled including 5 million and 10 million samples per arm. [Part 1](plans/milestone-3-part-1-gravity-alignment.md) is fulfilled.
- Deliverable: Stage 3 outputs hand trajectories in the robot base frame with verified kinematic limits. Parts 1–2 supply shared Z-up trajectories and sampled robot workspaces.
- Completed outcome: 10 million FK samples per arm produce separate 2 cm grids/distance tensors with 99.91% left / 99.92% right held-out occupancy coverage (9/8 misses of 10,000 per arm). Build time 32.81 s, peak RSS 2.33 GiB; 10 focused tests passed. [Part 2 acceptance](experiments/robot-workspace-purdue.md); [Part 1 acceptance](experiments/gravity-alignment-bundled.md).
- Current work: 10 million FK samples per arm is the user-selected preferred default. [Future improvements](future-improvements.md) records targeted IK gap sampling, deferred until the full baseline works; Part 3 is planning only.
- Blockers or decisions: no Part 2 blocker. Part 3 feasibility constraints remain undecided; sampled occupancy is incomplete and does not certify collision/orientation/trajectory feasibility. Gravity accuracy/metric scale remain unverified. Milestone 2 iPhone capture, [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: agree Part 3 scope and acceptance before implementation, using the preferred 10 million sample workspaces. Process iPhone MP4s under the existing pilot plan when available.
- Last verification: **2026-10-15**, preferred configuration matches the completed 10m run; 10 focused tests and wiki checks passed. Evidence: `20261015-workspace-preference-002` in the [action log](logs/2026-10.jsonl); numerical and visual acceptance remains linked above.
