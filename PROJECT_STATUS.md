# Project Status

- Current milestone: 1 — Validate HaWoR baseline
- Stage: Planning
- Active plan: Draft revision 2 — `plans/milestone-1-hawor-baseline.md` (awaiting architecture revision; not approved)
- Milestone deliverable: A reproducible baseline package that processes at least one clip from a HaWoR paper dataset and one Ego4D clip, exports HaWoR's unchanged world-frame trajectory with validity/provenance metadata, produces an overlay visualization, and includes a one-page benchmark and failure report.
- Last verified: 2026-09-08 — `AGENTS.md` now points to the repository-wide planning standard in `PLANNING_SPECS.md`; the Milestone 1 draft itself has not been reformatted, revised, or approved, and implementation has not started.

## Completed

- Defined the project milestones, sequence, deliverables, and major gates.
- Established the repository-wide workflow and planning requirements in `AGENTS.md`.
- Created the first draft of the Milestone 1 implementation plan.
- Refined Milestone 1 to begin with a complete setup gate, treat a pinned `external/HaWoR/` checkout as an external engine, defer Ego4D until HOT3D succeeds, and exclude canonical/other coordinate transformations.
- Standardized the required 13-section milestone-plan format, staged planning conversation, per-file documentation fields, and nested call-flow representation in `PLANNING_SPECS.md`.

## In progress

- Elicit and refine the user's desired Milestone 1 architecture for plan Sections 4–7 before revising the plan.

## Blockers and decisions

- The draft Milestone 1 implementation plan has not yet been approved.
- The requested Milestone 1 architecture changes have not yet been specified or incorporated into the draft.
- Execution environment decision: attempt WSL2 on the local 8 GB RTX 3070 first, or use a Linux NVIDIA machine with at least 16 GB VRAM.
- Licensed MANO model files must be supplied before the bundled HaWoR example can run.
- Decide whether `external/HaWoR/` will be a pinned Git submodule as recommended.
- HOT3D is selected and run before any Ego4D credential or download work begins.
- Exact HOT3D and later Ego4D source intervals will be selected by the approved plan's visual criteria unless the user supplies preferred clips.

## Next action

- Draft roadmap-grounded Goals and Explicit Non-Goals for user review, then ask for the user's desired specifications for Sections 4–7. Do not revise the Milestone 1 plan or begin implementation until directed through the planning workflow.
