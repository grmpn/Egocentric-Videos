# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Part 1 is complete; the overall milestone is not. The user authorized starting ahead of iPhone capture on 2026-10-14.
- Stage: **Implementing** — Part 2 revision 1 approved by the user on 2026-10-15; Part 3 remains planning only.
- Active plan: [Part 2: Robot workspace, approved revision 1](plans/milestone-3-part-2-robot-workspace.md). [Part 1's approved plan](plans/milestone-3-part-1-gravity-alignment.md) is fulfilled.
- Deliverable: Stage 3 outputs hand trajectories in the robot base frame with verified kinematic limits. Completed Part 1 supplies the shared Z-up hand/camera representation.
- Completed outcome: bundled real GeoCalib run, reloadable aligned export/reversible transform, plots and diagnostics; 20 inliers, source fields preserved, full MANO/camera checks and 31 tests passed. [Part 1 acceptance and review artifacts](experiments/gravity-alignment-bundled.md).
- Current work: numerical Part 2 workflow and 10 focused tests pass; 100k/1m runs exported and reloaded. Interactive viewer acceptance is underway. [Implemented contract](topics/stage-3-retargeting.md#part-2-workspace-contract).
- Blockers or decisions: Part 3 feasibility constraints remain undecided. Gravity accuracy/metric scale remain unverified. Milestone 2's iPhone demonstrations, [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon quality/label review remain outstanding.
- Next action: finish browser camera/layer review and audit Part 2 acceptance. Process iPhone MP4s under the existing pilot plan when available.
- Last verification: **2026-10-15**, real Purdue FK, grid/EDT/query reload and 10 tests. Evidence: `20261015-workspace-implementation-005` in the [action log](logs/2026-10.jsonl); local runs under `outputs/workspace/part-2-20261015/`.
