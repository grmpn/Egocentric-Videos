# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. The approved Parts 1–3 scope and MANO viewer comparison are complete; no next milestone has started.
- Stage: **Complete** — scoped positional deliverables and original MANO mesh comparison verified; dynamic simulation/hardware remain outside this acceptance.
- Active plan: [Part 3 revision 2](plans/milestone-3-part-3-placement-and-segmentation.md), fulfilled. [Part 2 revision 2](plans/milestone-3-part-2-robot-workspace.md) and [Part 1](plans/milestone-3-part-1-gravity-alignment.md) are fulfilled.
- Deliverable: base-frame hand trajectories, positional IK witnesses, annotated video and interactive playback using one fixed base per retained episode.
- Completed outcome: two bundled episodes (2.53 s / 1.50 s), combined SDF/IK coverage 96.05% / 100%; all 240 successful IK samples independently verified, maximum target error 0.152 mm. MANO comparison verified across 241 valid hand frames; 37 focused/regression tests and interactive review passed. [Acceptance and artifacts](experiments/retargeting-bundled.md).
- Current work: no remaining Part 3 implementation; focused repository cleanup has not yet been performed.
- Blockers or decisions: no blocker to scoped completion. One right-hand IK failure and two large joint changes remain flagged. Collision/dynamics, scale, gravity and floor height are unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: focused cleanup before another milestone; preserve acceptance evidence. Process iPhone MP4s under the existing pilot plan when available.
- Last verification: **2026-10-16**, MANO geometry, regression and browser checks passed; `20261016-mano-viewer-003` in the [action log](logs/2026-10.jsonl).
