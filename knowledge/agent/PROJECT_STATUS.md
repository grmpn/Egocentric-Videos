# Project Status

- Current milestone: 1 — Validate HaWoR baseline
- Stage: Planning
- Active plan: Draft revision 6 — `knowledge/agent/plans/milestone-1-hawor-baseline.md` (awaiting review; not approved)
- Milestone deliverable: A reproducible baseline package that processes at least one clip from a HaWoR paper dataset and one Ego4D clip, exports HaWoR's unchanged world-frame trajectory with validity/provenance metadata, produces an overlay visualization, and includes a run-scoped one-page benchmark and failure report for each attempt.
- Last verified: 2026-09-11 — Draft revision 6 was checked for consistency with the roadmap, planning specification, and unchanged core pipeline architecture. The plan remains unapproved with no implementation started.

## Completed

- Defined the project milestones, sequence, deliverables, and major gates.
- Established the repository-wide workflow and planning requirements in `AGENTS.md`.
- Created the first draft of the Milestone 1 implementation plan.
- Refined Milestone 1 to begin with a complete setup gate, treat a pinned `external/HaWoR/` checkout as an external engine, defer Ego4D until HOT3D succeeds, and exclude canonical/other coordinate transformations.
- Standardized the required 13-section milestone-plan format, staged planning conversation, per-file documentation fields, and nested call-flow representation in `knowledge/agent/PLANNING_SPECS.md`.
- Migrated the existing Milestone 1 plan into that format without changing its architecture, scope, requirements, contracts, or decisions.
- Removed the separate dataset Gate A/B/C elaborations and simplified the end-to-end call tree while retaining dataset order in the Goals and Implementation Sequence.
- Revised the draft clip-ingestion architecture so direct videos require no per-clip config file, HOT3D native frames/calibration are adapted into the common prepared MP4 boundary, and persisted prepared metadata can be reloaded into the same typed runtime contract.
- Revised preparation dispatch so `ClipRequest` contains no encoding-control flag: source resolution produces a `VideoFileSource` or `FrameSequenceSource`, and the latter alone invokes the reusable single-pass frame-sequence encoder under `video_preparation.py` coordination.
- Revised Milestone 1 execution so `run_milestone1_baseline.py` processes one clip per invocation and automatically calls `benchmark.py` for a unique report belonging only to that run, including reportable pipeline-stage failures.
- Revised the Milestone 1 draft at the user's direction without starting implementation.

## In progress

- Review and refine Draft revision 6, especially the remaining timing-quality and Ego4D intrinsics policies, before completing plan approval.

## Blockers and decisions

- The draft Milestone 1 implementation plan has not yet been approved.
- Strict preparation thresholds for repeated-frame fraction, maximum source-frame gap, and timestamp-selection error remain undecided.
- The Ego4D focal policy remains undecided: require calibrated/derived intrinsics or explicitly permit the approximate HaWoR-style image-dimension fallback.
- Execution environment decision: attempt WSL2 on the local 8 GB RTX 3070 first, or use a Linux NVIDIA machine with at least 16 GB VRAM.
- Licensed MANO model files must be supplied before the bundled HaWoR example can run.
- Decide whether `external/HaWoR/` will be a pinned Git submodule as recommended.
- HOT3D is selected and run before any Ego4D credential or download work begins.
- Exact HOT3D and later Ego4D source intervals will be selected by the approved plan's visual criteria unless the user supplies preferred clips.

## Next action

- User reviews Draft revision 6 and resolves or revises its remaining architecture decisions. Do not begin implementation before the completed plan is explicitly approved.
