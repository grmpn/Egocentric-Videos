# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Part 1 is complete; the overall milestone is not. The user authorized starting ahead of iPhone capture on 2026-10-14.
- Stage: **Planning** — Parts 2–3 remain planning only; no further implementation scope is approved.
- Active plan: [Part 1: Gravity alignment, approved revision 1](plans/milestone-3-part-1-gravity-alignment.md), fulfilled; no active Part 2 implementation plan.
- Deliverable: Stage 3 outputs hand trajectories in the robot base frame with verified kinematic limits. Completed Part 1 supplies the shared Z-up hand/camera representation.
- Completed outcome: bundled real GeoCalib run, reloadable aligned export/reversible transform, plots and diagnostics; 20 inliers, source fields preserved, full MANO/camera checks and 31 tests passed. [Part 1 acceptance and review artifacts](experiments/gravity-alignment-bundled.md).
- Current work: Part 1 handoff; [workspace and placement/segmentation](topics/stage-3-retargeting.md) await their own approved plans.
- Blockers or decisions: no remaining Part 1 implementation blocker. Gravity accuracy/metric scale remain unverified, and estimates cluster late in the example. Milestone 2's iPhone demonstrations remain unrecorded; [pilot processing/acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon quality/label review remain outstanding. Parts 2–3 need robot constraint and feasibility decisions.
- Next action: user reviews Part 1 outputs and chooses when to plan Part 2. Process iPhone MP4s under the existing pilot plan when available. Do not mark Milestone 2 or all of Stage 3 complete.
- Last verification: **2026-10-14**, real GeoCalib CUDA inference, full geometry comparison against pinned HaWoR helpers, source/reload checks, focused/regression tests and visual inspection. Evidence: `20261014-gravity-implementation-008`/`009` in the [action log](logs/2026-10.jsonl).
