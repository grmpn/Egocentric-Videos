# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Parts 1–2 are complete; the overall milestone is not. The user authorized starting ahead of iPhone capture on 2026-10-14.
- Stage: **Planning** — Part 2 acceptance is complete; Part 3 has no approved implementation plan.
- Active plan: [Part 2: Robot workspace, approved revision 1](plans/milestone-3-part-2-robot-workspace.md), fulfilled. [Part 1](plans/milestone-3-part-1-gravity-alignment.md) is also fulfilled.
- Deliverable: Stage 3 outputs hand trajectories in the robot base frame with verified kinematic limits. Parts 1–2 supply shared Z-up trajectories and sampled robot workspaces.
- Completed outcome: two million FK samples, separate 2 cm grids/distance tensors, reloadable queries and interactive 3D review; 10 focused tests passed. Held-out occupancy coverage is 93.78% left / 94.28% right. [Part 2 acceptance](experiments/robot-workspace-purdue.md); [Part 1 acceptance](experiments/gravity-alignment-bundled.md).
- Current work: Part 2 handoff and user review. [Workspace conventions and limitations](topics/stage-3-retargeting.md#part-2-workspace-contract) are implemented; Part 3 placement/segmentation remains planning only.
- Blockers or decisions: no Part 2 blocker. Part 3 feasibility constraints remain undecided; sampled occupancy is incomplete and does not certify collision/orientation/trajectory feasibility. Gravity accuracy/metric scale remain unverified. Milestone 2 iPhone capture, [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: user reviews Part 2 outputs, then agrees Part 3 scope and acceptance before implementation. Process iPhone MP4s under the existing pilot plan when available.
- Last verification: **2026-10-15**, full source-bound/sample/grid audit, independent SciPy queries, focused/legacy tests and browser/visual review. Evidence: `20261015-workspace-implementation-008` in the [action log](logs/2026-10.jsonl).
