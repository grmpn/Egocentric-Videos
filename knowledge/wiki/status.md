# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Part 1 is complete; the overall milestone is not. The user authorized starting ahead of iPhone capture on 2026-10-14.
- Stage: **Planning** — Part 2 draft awaits approval; Part 3 remains planning only.
- Active plan: [Part 2: Robot workspace, draft revision 1](plans/milestone-3-part-2-robot-workspace.md). [Part 1's approved plan](plans/milestone-3-part-1-gravity-alignment.md) is fulfilled.
- Deliverable: Stage 3 outputs hand trajectories in the robot base frame with verified kinematic limits. Completed Part 1 supplies the shared Z-up hand/camera representation.
- Completed outcome: bundled real GeoCalib run, reloadable aligned export/reversible transform, plots and diagnostics; 20 inliers, source fields preserved, full MANO/camera checks and 31 tests passed. [Part 1 acceptance and review artifacts](experiments/gravity-alignment-bundled.md).
- Current work: Part 2 plan incorporates the updated spec: separate FK clouds, 2 cm occupancy, signed-distance queries and interactive review; proposed defaults and evidence are in the [Stage 3 reference](topics/stage-3-retargeting.md#part-2-proposed-workspace-contract).
- Blockers or decisions: Part 2 needs plan approval, including proposed base/TCP frames and position-only scope. Part 3 feasibility constraints remain undecided. Gravity accuracy/metric scale remain unverified. Milestone 2's iPhone demonstrations, [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon quality/label review remain outstanding.
- Next action: review and approve or revise Part 2 draft revision 1. After approval, verify the pinned robot model and build the workspace workflow. Process iPhone MP4s under the existing pilot plan when available.
- Last verification: **2026-10-15**, Part 2 documentation/source review only; no robot execution. Evidence: `20261015-workspace-planning-001`/`002` in the [action log](logs/2026-10.jsonl). Last runtime acceptance remains [Part 1, 2026-10-14](experiments/gravity-alignment-bundled.md).
