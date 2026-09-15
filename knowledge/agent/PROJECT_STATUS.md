# Project Status

- Current milestone: 1 — Validate HaWoR baseline
- Stage: Implementing
- Active plan: Approved revision 8 — `knowledge/agent/plans/milestone-1-hawor-baseline.md` (user approval on 2026-09-15)
- Milestone deliverable: A reproducible baseline package that processes the bundled HaWoR example and one short Ego4D MP4 segment, exports HaWoR's unchanged world-frame trajectory with validity/provenance metadata, produces an overlay visualization, and includes a run-scoped one-page benchmark and failure report for each attempt.
- Last verified: 2026-09-15 — Phase 0 passes on the existing WSL2/8 GB RTX 3070: setup evidence is `outputs/hawor/setup-20260915-03/setup_check.json`; fresh unchanged inference completed in 684.54 seconds with 7,093,936 KiB peak process RAM in `outputs/hawor/setup-smoke-20260915-02/`. The stock headless helper rendered a decodable 1920×1080, 60 FPS, 242-frame video covering the 121-frame source duration; beginning/middle/end were visually inspected. The native result SHA-256 remained `d761e5fe5e7e0d6d3a6fb642980aaadd5e418912a4f2742385ed740880864c7f` after rendering. Full environment-pin verification was added afterward and passed its targeted checks; clean recreation is still running separately.

## Completed

- Implemented timestamp-driven MP4 preparation/reload, the unchanged-engine adapter, world export, RGB overlay/world preview, full-pipeline sampled resources, finalized run manifests, and automatic single-run benchmark reporting. All 80 CPU-safe tests pass in both the working FFmpeg 6 environment (24.83 seconds) and a clean, Torch-free CPU Conda environment using FFmpeg 9.0.1 (20.11 seconds; `outputs/hawor/cpu-tests-20260915-01/test-suite-02.log`). CLI help and failure-report execution were checked. Native export/render integration against the Phase 0 result also passes frame/hash checks; its representative RGB overlays and trajectory preview were inspected.
- Recorded explicit plan approval and user-confirmed preparation limits: 5% repeated frames, 0.10-second maximum source gap, and 1/60-second maximum timestamp-selection error.
- Confirmed that exported detection/confidence provenance follows HaWoR's majority track-to-hand assignment, with raw label disagreements documented in trajectory validation metadata.
- Implemented the Phase 0 setup checker, runtime specification and setup documentation, plus ignore rules for local inputs and run evidence. Verified installed pins, upstream requirement coverage, compiled imports, and `pip check`; clean environment recreation remains unverified.
- Completed fresh bundled inference and representative headless world-view inspection with unchanged upstream source/settings. Native arrays have the planned float32 shapes and are finite; final validity is 121 left frames and 120 right frames. The right hand's final invalid frame must remain invalid in export.
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
- Added a preliminary README About section describing the overall pipeline goal, Milestone 1 boundary, and links to the roadmap, current status, and draft plan.

## In progress

- Validate the complete single-clip bundled command in fresh output directories. Final setup preflight passed at `outputs/hawor/setup-20260915-04/setup_check.json`; the first end-to-end run is active at `outputs/hawor/20260915T195819543653Z-eb1014a4fba5/`.
- Recreate the full environment independently in `/tmp/hawor-recreation-20260915-WaiTKt/hawor`; logs are in `outputs/hawor/environment-recreation-20260915-01/`. The working `hawor` environment is preserved.

## Blockers and decisions

- GPU checks require execution outside the sandbox. CUDA allocation passed with approximately 7 GB free; the earlier NVML occupancy did not reflect Torch's usable-memory result.
- The stock world view proves rendering functionality; required RGB overlay alignment and full provenance-transition review still need the pipeline visualizer.
- No Ego4D MP4 is available. Development and bundled-example validation proceed; final Ego4D acceptance requires the licensed source and selected interval.
- CPU-only Conda creation, source-tree import, and the full 80-test suite pass locally; hosted workflow success remains unverified. The user approved creation and push of `validation/milestone-1-hawor`; the local branch exists and `main` is unchanged. The validated source/test/docs changes are ready for the approved push; run artifacts and licensed assets remain excluded.

## Next action

- Finish the bundled single-clip run, inspect all required provenance transitions, and repeat from a fresh output directory while clean environment recreation completes. After local validation, commit/push the approved validation branch and inspect hosted CI.
