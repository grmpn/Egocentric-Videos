# Project status

- Current milestone: **3 — Fixed-base trajectory preparation, Part 1**. The user authorized starting ahead of iPhone capture on 2026-10-14; Milestone 2 remains incomplete.
- Stage: **Implementing**.
- Active plan: [Part 1: Gravity alignment, approved revision 1](plans/milestone-3-part-1-gravity-alignment.md), approved 2026-10-14.
- Deliverable: Stage 3 outputs hand trajectories in the robot base frame with verified kinematic limits. Part 1 proposes a reusable Z-up hand/camera export, reversible transform, original/aligned plots and diagnostics on the bundled example.
- Completed outcome: spec organized and Part 1 drafted; no Stage 3 code or runtime acceptance. Earlier [Eidon integration evidence](experiments/milestone-2-eidon-validation.md#desktop-annotation-retry--2026-09-25) remains valid historical evidence, with significant reconstruction/label limitations.
- Current work: implement and validate the approved gravity-alignment workflow. [Parts 2–3](topics/stage-3-retargeting.md) remain planning only.
- Blockers or decisions: The iPhone demonstrations remain unrecorded; processing/review and pilot acceptance remain under the [approved Milestone 2 plan](plans/milestone-2-lerobot-pilot.md). Eidon quality/label review remains unresolved. Robot constraints and final feasibility verification belong to later planning.
- Next action: establish isolated GeoCalib inference, implement the shared transform/export and validate the bundled example. Resume iPhone pilot processing when recordings are available; do not mark Milestone 2 complete from Stage 3 progress.
- Last verification: **2026-10-14**, static source/planning review and documentation checks only; see `20261014-stage3-planning-001`/`004` in the [action log](logs/2026-10.jsonl). No new inference or robot validation.
