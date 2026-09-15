# Project Status

- Current milestone: 1 — Validate HaWoR baseline
- Stage: Implementing
- Active plan: Approved revision 8 — `knowledge/agent/plans/milestone-1-hawor-baseline.md` (user approval on 2026-09-15)
- Milestone deliverable: A reproducible baseline package that processes the bundled HaWoR example and one short Ego4D MP4 segment, exports HaWoR's unchanged world-frame trajectory with validity/provenance metadata, produces an overlay visualization, and includes a run-scoped one-page benchmark and failure report for each attempt.
- Last verified: 2026-09-15 — Final preflight passes at `outputs/hawor/setup-20260915-04/setup_check.json`. The single-clip command completed all stages in `outputs/hawor/20260915T195819543653Z-eb1014a4fba5/`; all 121 RGB-overlay frames and the world preview were inspected. Its report records qualitative misses/misalignment/jitter, unchanged native world arrays, and the final invalid right-hand frame. Reported monotonic elapsed time is 651.986 seconds; UTC stamps span 694.541 seconds, a timing discrepancy under investigation. Peak sampled process-tree RAM is 8.005 GiB and device GPU memory 7.806 GiB. Full runtime recreation and repeat-run verification remain pending.

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

- Repeat the successful, visually reviewed single-clip command from a fresh output directory. The timing discrepancy is explained by 20 observed forward UTC-clock steps totaling 42.468 seconds; independent MONOTONIC/BOOTTIME probes remain aligned. Manifests now explicitly distinguish elapsed duration from UTC audit span; the first report records this evidence without altering its finalized manifest.
- Recreate the full environment independently in `/tmp/hawor-recreation-20260915-WaiTKt/hawor`; logs are in `outputs/hawor/environment-recreation-20260915-01/`. The working `hawor` environment is preserved.

## Blockers and decisions

- GPU checks require execution outside the sandbox. CUDA allocation passed with approximately 7 GB free; the earlier NVML occupancy did not reflect Torch's usable-memory result.
- The first pipeline overlay/world preview and all infill transitions have been inspected. Baseline failure labels are recorded in that run's benchmark; no reconstruction-accuracy claim is made.
- No Ego4D MP4 is available. Development and bundled-example validation proceed; final Ego4D acceptance requires the licensed source and selected interval.
- CPU-only Conda creation, source-tree import, and the full 80-test suite pass locally. Commit `1a0c5d5` is on local `validation/milestone-1-hawor`; `main` is unchanged. Despite explicit user approval, the environment refuses agent pushes because they are exclusively user-controlled. The user must push this branch before hosted CI can be verified. No remote writes occurred; run artifacts and licensed assets are excluded from the commit.

## Next action

- Complete and visually inspect the fresh bundled repeat, finish full runtime recreation, and commit final verification notes. After the user-controlled validation-branch push, inspect hosted CPU CI. Ego4D acceptance remains deferred until its licensed MP4/interval is available.
