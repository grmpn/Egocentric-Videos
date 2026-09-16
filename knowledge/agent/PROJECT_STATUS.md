# Project Status

- Current milestone: 1 — Validate HaWoR baseline
- Stage: Validating
- Active plan: Approved revision 8 — `knowledge/agent/plans/milestone-1-hawor-baseline.md` (user approval on 2026-09-15)
- Milestone deliverable: A reproducible baseline package that processes the bundled HaWoR example and one short Ego4D MP4 segment, exports HaWoR's unchanged world-frame trajectory with validity/provenance metadata, produces an overlay visualization, and includes a run-scoped one-page benchmark and failure report for each attempt.
- Last verified: 2026-09-16 — Full runtime recreation passes, including bundled run `outputs/hawor/20260916T202520659122Z-b078a74f8804/`, all 121 overlay frames and infill transitions, larger RGB comparisons, and world-preview review. The run completed all stages in 1012.469 monotonic seconds with bitwise native-world preservation and valid counts of 121 left / 120 right. Final evidence is `outputs/hawor/environment-recreation-20260916-01/final-validation.json`: all 8 manifest artifact checks and all 24 prior input/evidence preservation checks pass. The user pushed the validation branch; CI's whitespace failure in commit `2c39c8a` was reproduced locally and corrected as described below. Hosted tests and Ego4D acceptance remain unverified.

## Completed

- Implemented timestamp-driven MP4 preparation/reload, the unchanged-engine adapter, world export, RGB overlay/world preview, full-pipeline sampled resources, finalized run manifests, and automatic single-run benchmark reporting. All 80 CPU-safe tests pass in both the working FFmpeg 6 environment (24.83 seconds) and a clean, Torch-free CPU Conda environment using FFmpeg 9.0.1 (20.11 seconds; `outputs/hawor/cpu-tests-20260915-01/test-suite-02.log`). CLI help and failure-report execution were checked. Native export/render integration against the Phase 0 result also passes frame/hash checks; its representative RGB overlays and trajectory preview were inspected.
- Recorded explicit plan approval and user-confirmed preparation limits: 5% repeated frames, 0.10-second maximum source gap, and 1/60-second maximum timestamp-selection error.
- Confirmed that exported detection/confidence provenance follows HaWoR's majority track-to-hand assignment, with raw label disagreements documented in trajectory validation metadata.
- Implemented the Phase 0 setup checker, runtime specification and setup documentation, plus ignore rules for local inputs and run evidence. Recreated Conda/Torch and all dependencies, including freshly built PyTorch3D, torch-scatter, DROID, and LieTorch. Recreated-prefix GPU kernel checks, preflight, and `pip check` pass; all 80 CPU-safe tests pass in 37.15 seconds (`outputs/hawor/environment-recreation-20260916-01/{compiled-kernels.json,setup_check.json,pip-check.log,project-tests.log}`).
- Validated the recreated environment through inference, unchanged export, and rendering on the local 8 GB GPU. Its run-scoped benchmark records missed detections, mesh/image misalignment, and qualitative trajectory jitter after full frame review; no reconstruction-accuracy claim is made. Sampled peaks are 6.813 GiB process-tree RSS and 7.804 GiB device-wide GPU memory. Reviewed README/setup links and commands, documented abrupt-termination limitations, and retained the original working environment and prior evidence.
- Corrected repository ignore rules after commit `2c39c8a` accidentally tracked two Hydra `.gitignore` files from the recreated environment. Ignoring the entire `data/` and `outputs/` directories prevents dependency-local negations from making files trackable. Removed only those two files from the index, preserving their local bytes and the existing tracked `.gitkeep` files. Local ignore, tracked-file, and whitespace checks pass; the CI workflow is unchanged.
- Completed and reviewed bundled runs `outputs/hawor/20260915T195819543653Z-eb1014a4fba5/` and `outputs/hawor/20260915T201758566130Z-802f2facfb7f/`, including all 121 overlay frames, infill transitions, and world previews. Native world arrays are bitwise preserved; the final right-hand frame remains invalid. Separate reports record misses/misalignment/jitter and runtimes of 651.986 and 707.688 monotonic seconds, qualified by concurrent compilation and separately measured UTC clock corrections.
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

- Local bundled validation is finished. Remaining milestone acceptance work is hosted CPU CI verification and the licensed Ego4D clip run/review.

## Blockers and decisions

- GPU execution requires host access outside the sandbox; the recreated environment's complete bundled run passes there. Peak device memory is close to the 8 GB limit; feasibility for the eventual Ego4D interval is unverified.
- Earlier recreated-environment attempts `20260916T171924714596Z-263ebb797b15` and `20260916T172604203202Z-5d6f4c6dcbcf` have stale running manifests and logs ending during SLAM. No corresponding processes remain on the host. Their termination cause, exit time, runtime, and resource peaks are unknown; raw evidence is preserved. They have no finalized automatic reports and are not accepted validation runs.
- No Ego4D MP4 is available, reconfirmed by the user on 2026-09-16. Final Ego4D acceptance requires the licensed source, video UID, selected interval, and license reference.
- CPU-only Conda creation, source-tree import, and all 80 tests pass locally (`outputs/hawor/cpu-tests-20260915-01/test-suite-04.log`, 19.64 seconds). The user pushed `validation/milestone-1-hawor` and reported CI failing at `git diff --check HEAD^ HEAD` on Hydra's trailing blank line, before environment creation or pytest. The corrective commit needs a user-controlled push and a fresh hosted run; no agent remote writes occurred.

## Next action

- Push the ignore-rule correction on `validation/milestone-1-hawor`, then inspect the fresh hosted CPU CI result. When the licensed Ego4D MP4 and interval are available, run and review that clip through a separate baseline invocation. Do not mark Milestone 1 complete until both acceptance gates pass.
