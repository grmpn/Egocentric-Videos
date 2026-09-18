# Project Status

- Current milestone: 1 — Validate HaWoR baseline
- Stage: Complete
- Active plan: Approved revision 8 — `knowledge/agent/plans/milestone-1-hawor-baseline.md` (user approval on 2026-09-15)
- Milestone deliverable: A reproducible baseline package that processes the bundled HaWoR example and one short Ego4D MP4 segment, exports HaWoR's unchanged world-frame trajectory with validity/provenance metadata, produces an overlay visualization, and includes a run-scoped one-page benchmark and failure report for each attempt.
- Last verified: 2026-09-18 — Milestone 1 accepted: source-access confirmation and license references recorded for both Ego4D videos; hosted CI passes for implementation commit `e7ef68c9f22441dd342cddd07c8fbb5ac2419d11`; all 88 checked run artifacts retain their hashes. The [acceptance evidence](../../outputs/hawor/milestone-1-acceptance-20260918-01.json) binds source provenance, accepted runs, prior validation, README review, and CI results.

## Milestone 1 acceptance record

On 2026-09-18 the user confirmed that both supplied videos were obtained through approved Ego4D access and are covered by their Ego4D license agreement: “Yes, for both Ego4D videos.” License reference: [Ego4D License Agreement and official access documentation](https://ego4d-data.org/docs/start-here/#ego4d-license-agreement). This records the user's attestation; no credentials or private signed documents were collected.

| Supplied source | User-supplied Ego4D UID | Verified source SHA-256 |
| --- | --- | --- |
| `Ego4D-cooking.mp4` | `002c3b5c-ed86-4af3-99a1-4b497b7c8a86` | `a5d1e917021aff07196c8c8e6abd3d021bf03937ae47eda0db5e0107f8cc7014` |
| `Ego4D-bike-trim.mp4` | `01aed4ae-486e-41eb-91f8-4d2e8a46db7d` | `c59f1ea2301fe6e23485b23d0f4899632a2d73731943c0ea2340cd1e0e635989` |

The required Ego4D acceptance example is cooking interval **20:00–20:04**, run `20260918T171726548487Z-01f003922c21`. Its separate input `cooking-1200-1204.mp4` has SHA-256 `edb9567defa02e842d37118b59e3cb8b63196c21bed0fe701aadd1583bda4152`; add 1200 seconds to exported timestamps to recover the original cooking-video timestamps. The [trim evidence](../../outputs/hawor/ego4d-evaluation-20260918-01/trimming.json) records the command and source chain. The accepted bundled example is run `20260916T202520659122Z-b078a74f8804`. Both runs have reviewed overlays, world previews, unchanged native-world exports, finalized manifests, and per-run benchmark reports. The bicycle evaluation is supplementary; its unknown full-recording offset does not affect the cooking acceptance example.

This is a dated post-run provenance addendum. Original manifests, requests, benchmarks, and evaluation summaries remain unchanged, including their execution-time missing-license warnings. This record resolves that missing source-access/license evidence for both supplied sources without rewriting run history or rerunning inference. The machine-readable acceptance record has SHA-256 `922a42a62d4ba57bde23a0b9ba15f7675aa5f65e1a4f928ad97e77d8261ed00d`.

Acceptance establishes a reproducible unchanged-HaWoR baseline with documented failure modes. Approximate intrinsics, residual alignment/jitter, and unreliable infilling remain recorded limitations; metric reconstruction accuracy is not an acceptance claim. Licensed inputs, model assets, and generated evidence remain local and untracked.

## Completed

- Completed five separately trimmed four-second bicycle-video evaluations for UID `01aed4ae-486e-41eb-91f8-4d2e8a46db7d`: 4–8, 28–32, 52–56, 76–80, and 100–104 seconds relative to the supplied `Ego4D-bike-trim.mp4`. FFprobe measured 120.8 seconds, and the user confirmed spreading the intervals across it. All 600 overlay frames, infill transitions, representative full-size frames, and world previews were reviewed; all 40 artifacts and export contracts pass independent checks. The 00:04 interval has the strongest two-hand overlay; other intervals retain substantial infill/alignment failures. Phase timings, per-run reviews, commands, and provenance: [bicycle evaluation summary](../../outputs/hawor/ego4d-bike-evaluation-20260918-01/SUMMARY.md). Prior cooking evidence remains unchanged.
- Added live, flushed HaWoR stdout/stderr forwarding while retaining its redacted console log; exposed preparation/inference/export/visualization/validation durations in the console and benchmark report, including failed phases. Updated README trimming and timing guidance. All 82 tests pass in the recreated runtime (34.12 seconds); GPU preflight passes.
- Completed five separate four-second Ego4D evaluations for UID `002c3b5c-ed86-4af3-99a1-4b497b7c8a86`, with original intervals 300–304, 600–604, 1200–1204, 1800–1804, and 2600–2604 seconds. All 600 overlay frames, infill transitions, representative detailed frames, and world previews were reviewed; each run has its own benchmark and failure notes. Independent checks pass for all 40 artifacts, native bitwise/validity preservation, timestamps, provenance, unchanged inputs, and console/timing parity. Results and exact commands: [cooking evaluation summary](../../outputs/hawor/ego4d-evaluation-20260918-01/SUMMARY.md). The 20:00 and 43:20 clips are qualitatively strongest; alignment errors/jitter remain, with severe infill failures and a brief identity reversal in other intervals.
- Hosted [CPU tests run 35381886887](https://github.com/grmpn/Egocentric-Videos/actions/runs/35381886887) passes for implementation commit `e7ef68c9f22441dd342cddd07c8fbb5ac2419d11`; successful environment creation, checkout import, and test-suite steps were independently verified through GitHub's API on 2026-09-18. The implementation also has 82 passing local tests. No implementation changes were made during provenance closeout.
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

- None for Milestone 1. Milestone 2 has not been started.

## Blockers and decisions

- No remaining Milestone 1 acceptance blockers. The following are retained execution/quality limitations and historical failure evidence.
- GPU execution requires host access outside the sandbox. All ten completed Ego4D runs fit the local 8 GB GPU, with sampled device-wide memory of 7.78–7.81 GiB; feasibility for longer or different inputs is not established.
- Earlier recreated-environment attempts `20260916T171924714596Z-263ebb797b15` and `20260916T172604203202Z-5d6f4c6dcbcf` have stale running manifests and logs ending during SLAM. No corresponding processes remain on the host. Their termination cause, exit time, runtime, and resource peaks are unknown; raw evidence is preserved. They have no finalized automatic reports and are not accepted validation runs.
- Both Ego4D sources have user-confirmed approved access and the license reference recorded above. The bicycle file's offset within the full recording remains unknown; its supplementary evaluation timestamps map only to the supplied trimmed source.
- The first 43:20 evaluation attempt (`20260918T172544016517Z-f3e6d3ac5632`) was interrupted at SLAM startup; launcher exit 143, cause unknown. Host checks found no remaining corresponding processes. Raw evidence is preserved in the evaluation directory, and a fresh retry completed; the interrupted attempt is excluded from completed-run timing.

## Next action

- Push the documentation closeout commit and merge `validation/milestone-1-hawor` into `main` after the required branch checks pass. Milestone 2 planning requires a separate user request.
