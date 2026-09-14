# Project Status

- Current milestone: 1 — Validate HaWoR baseline
- Stage: Planning
- Active plan: Draft revision 8 — `knowledge/agent/plans/milestone-1-hawor-baseline.md` (scope correction recorded; full plan not approved)
- Milestone deliverable: A reproducible baseline package that processes the bundled HaWoR example and one short Ego4D MP4 segment, exports HaWoR's unchanged world-frame trajectory with validity/provenance metadata, produces an overlay visualization, and includes a run-scoped one-page benchmark and failure report for each attempt.
- Last verified: 2026-09-14 — The user explicitly waived the planning gate for Milestone 1 directory scaffolding and planning-stage CI only. The planned static directories are tracked with temporary `.gitkeep` files, and `.github/workflows/ci.yml` validates the tracked repository foundation. The full plan remains unapproved; no pipeline code, environment specification, or tests have been created.

## Completed

- Defined the project milestones, sequence, deliverables, and major gates.
- Established the repository-wide workflow and planning requirements in `AGENTS.md`.
- Created the first draft of the Milestone 1 implementation plan.
- Refined Milestone 1 to begin with a complete setup gate, treat a pinned `external/HaWoR/` checkout as an external engine, and exclude canonical/other coordinate transformations.
- Standardized the required 13-section milestone-plan format, staged planning conversation, per-file documentation fields, and nested call-flow representation in `knowledge/agent/PLANNING_SPECS.md`.
- Migrated the existing Milestone 1 plan into that format without changing its architecture, scope, requirements, contracts, or decisions.
- Removed the separate dataset Gate A/B/C elaborations and simplified the end-to-end call tree while retaining dataset order in the Goals and Implementation Sequence.
- Revised the draft clip-ingestion architecture so direct MP4 videos require no per-clip config file and persisted prepared metadata can be reloaded into the same typed runtime contract.
- Revised Milestone 1 execution so `run_milestone1_baseline.py` processes one clip per invocation and automatically calls `benchmark.py` for a unique report belonging only to that run, including reportable pipeline-stage failures.
- Removed the planned `pyproject.toml` and installable project distribution at the user's direction; local execution now uses the Conda-managed environment and an explicit repository-root `PYTHONPATH=src` contract, while CPU CI uses a separate minimal Conda specification.
- Corrected Milestone 1 to use only the bundled HaWoR example and one short Ego4D MP4 segment. HOT3D, TAR/VRS/frame-sequence ingestion, calibration toolkits, fisheye correction, and rectification are deferred.
- Verified that the pinned HaWoR submodule and nested submodules are present and that both required MANO files are readable.
- Revised the Milestone 1 draft at the user's direction without starting implementation.
- Created the planned static directory skeleton with temporary `.gitkeep` files under the user's milestone-only pre-approval waiver; no Python files were added.
- Added a planning-stage GitHub Actions workflow that checks the tracked project documents, HaWoR submodule declaration, and current commit for whitespace errors; Python, Conda, import, and pytest checks remain deferred until their implementation inputs exist.

## In progress

- Review and refine Draft revision 8, especially the remaining timing-quality thresholds, before completing plan approval.

## Blockers and decisions

- The draft Milestone 1 implementation plan has not yet been approved.
- Strict preparation thresholds for repeated-frame fraction, maximum source-frame gap, and timestamp-selection error remain undecided.
- Execution environment decision: attempt WSL2 on the local 8 GB RTX 3070 first, or use a Linux NVIDIA machine with at least 16 GB VRAM.
- This tool session could not verify GPU access; the setup gate must still prove CUDA allocation and headless rendering on the actual execution machine.
- Ego4D access and the exact MP4 interval are still required for final validation. Official guidance estimates about 48 hours for credentials; acquisition does not block approval or implementation against the bundled example.

## Next action

- User reviews Draft revision 8, resolves or accepts its remaining decisions, and explicitly approves the completed plan. Do not begin further implementation beyond the completed directory/CI waiver before approval.
