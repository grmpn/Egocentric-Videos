# Milestone 1 Plan: Validate the HaWoR Baseline

Status: Approved revision 8 — user approved Milestone 1 implementation on 2026-09-15; timing limits confirmed the same day

## 1. Goals

Build a small, reusable pipeline around the unchanged HaWoR inference code and prove that it can:

1. run the bundled HaWoR example;
2. process one short segment from an ordinary Ego4D MP4;
3. preserve HaWoR's native world-frame result;
4. export that result with frame timestamps and validity/provenance metadata;
5. generate a reusable visualization;
6. produce a one-page benchmark and failure report for every Milestone 1 run;
7. maintain the root README as the user-facing project entry point, beginning with an About section when implementation starts; and
8. establish only the Conda environment specifications and CPU-safe continuous integration needed to run and validate the project-owned code.

Milestone 1 is a baseline and integration milestone. HaWoR remains the owner of hand reconstruction, camera tracking, metric scale estimation, motion infilling, and conversion into its world frame. Our code prepares inputs, invokes HaWoR, records what happened, validates the returned artifacts, and packages the existing world-frame output without changing its coordinate frame.

The README, Conda environment, and CI goals support development and maintainability; they do not add pipeline stages or alter any pipeline contract, HaWoR behavior, trajectory value, dataset choice, or benchmark result.

## 2. Explicit Non-Goals

- Do not derive or export a canonical frame.
- Do not apply any coordinate-frame transform to the stored HaWoR trajectory.
- Do not align different clips to one another.
- Do not gravity-align, rotate, translate, rescale, smooth, filter, or retarget the HaWoR world output.
- Do not reimplement or retrain HaWoR, DROID-SLAM, Metric3D, WiLoR, MANO, or the motion infiller.
- Do not change HaWoR's detector, interpolation, infilling, SLAM, or scale-estimation behavior.
- Do not design the final LeRobot representation yet.
- Do not choose a universal missing-hand rejection threshold.
- Do not claim statistical generalization from two clips.
- Do not begin robot simulation or control.
- Do not ingest HOT3D, TAR archives, VRS recordings, loose frame sequences, or other dataset-native formats.
- Do not install or use `projectaria_tools`, `hand_tracking_toolkit`, or a HOT3D toolkit.
- Do not read dataset-native camera calibration or correct fisheye/lens distortion.
- Do not rectify, crop, pad, resize, rotate, or otherwise change source image geometry; reject an input that requires such correction.
- Do not add YouTube discovery or downloading; that remains Milestone 6 work. A self-recorded MP4 may be used only as an optional temporary development fixture and is not Milestone 1 acceptance evidence.
- Do not build or install the project-owned code as a Python distribution, and do not add `pyproject.toml`, `setup.py`, uv, Poetry, or other project-packaging metadata in Milestone 1.
- Do not publish a package to PyPI or another registry.
- Do not make CI download licensed datasets, model weights, MANO files, or run GPU/HaWoR inference.
- Do not add formatting, linting, type-checking, release automation, coverage gates, or documentation-generation systems unless a later approved plan revision makes one necessary.

Visualization is the only place where projection is unavoidable: drawing a 3D result on an RGB image requires HaWoR's camera/view projection. That projection is for rendering only. It must not create or replace a stored trajectory.

## 3. Setup Requirements

Setup is Phase 0 and is the first implementation gate. The reusable pipeline is not written until the upstream environment passes the checks below.

### 3.1 Operating system and shell

Supported baseline environment:

- WSL2 running Ubuntu, or a native Linux machine.
- Bash inside Linux/WSL for upstream installation commands.
- NVIDIA GPU exposed inside Linux/WSL.

The first execution environment is the existing WSL2 installation with the local
8 GB RTX 3070, following the approved local-first setup path. A >=16 GB native
Linux GPU remains the fallback if the bundled example exceeds local VRAM.

Linux is not a theoretical requirement of every PyTorch operation in HaWoR. It is a practical requirement for this project's supported baseline because:

- the official installation and tested environment are Linux-style;
- HaWoR builds custom CUDA/C++ extensions for DROID-SLAM and `lietorch`;
- the released scripts and dependency instructions assume Bash/Linux paths and tools;
- the current repository does not document or test native Windows; and
- treating a Windows port as part of Milestone 1 would mix environment porting with baseline validation.

Therefore, native Windows is out of scope for the first reproducible baseline. WSL2 is acceptable because the CUDA code executes against the Windows-hosted NVIDIA driver through the Linux environment. If WSL2 reveals an upstream-specific failure, the fallback is a native Linux NVIDIA machine.

### 3.2 Hardware and storage

- NVIDIA GPU with CUDA support.
- Current local candidate: RTX 3070 Laptop GPU, compute capability 8.6, 8 GB VRAM.
- Recommended fallback: Linux NVIDIA GPU with at least 16 GB VRAM.
- Enough system RAM for video decoding, DROID-SLAM state, Metric3D, and rendering; record the actual amount during setup.
- At least 40 GB free storage for the environment, source checkout, weights, build products, one narrowly downloaded Ego4D MP4, and run artifacts. Confirm actual free space before installation.

The 8 GB GPU is a feasibility risk, not an automatic rejection. The bundled example is the memory smoke test. We will not reduce model precision, resolution, buffer sizes, or other numerical settings merely to force the baseline to fit. If it fails for memory, use the larger-GPU fallback and record the failure.

### 3.3 System packages inside Linux/WSL

Install and verify:

- `git` and Git submodule support;
- `git-lfs` if a required upstream asset uses it;
- `ffmpeg` and `ffprobe`;
- a C/C++ build toolchain (`build-essential`);
- `ninja-build` and `cmake` for compiled Python/CUDA packages;
- NVIDIA CUDA compiler/toolkit compatible with the chosen PyTorch build (`nvcc` must be available because DROID-SLAM compiles CUDA extensions);
- OpenGL/EGL runtime libraries needed by PyTorch3D, `pyrender`, and `aitviewer`; and
- basic image/video runtime libraries such as `libgl1` and `libglib2.0-0`.

The host NVIDIA driver and the Linux CUDA toolkit are separate concerns under WSL2. Do not install a second Linux display driver inside WSL. Verify GPU access with `nvidia-smi`, then verify the compiler separately with `nvcc --version`.

### 3.4 Conda and Python

- Install Miniconda or another compatible Conda distribution inside Linux/WSL.
- Create a dedicated environment named `hawor`.
- Use Python 3.10, matching HaWoR's documented environment.
- Do not use the host's current Python 3.14 installation for HaWoR.

`environment/hawor.yml` will be the single reviewed specification for the complete validated local environment: the HaWoR/CUDA stack plus direct and test dependencies used by project-owned code. The project itself is not installed as a Python distribution. Commands run from the repository root with `PYTHONPATH=src` so the `src/egocentric_pipeline/` package is imported directly from the checkout.

### 3.5 CUDA and PyTorch

Start from the versions documented by HaWoR:

- PyTorch `1.13.0+cu117`;
- torchvision `0.14.0+cu117`; and
- CUDA 11.7-compatible build tooling.

Before any model download or compilation, verify:

- `torch.cuda.is_available()` is true;
- the CUDA version reported by PyTorch is compatible with the CUDA compiler;
- the GPU name and compute capability are visible;
- a small tensor can be allocated and evaluated on the GPU; and
- the NVIDIA driver is new enough for the selected CUDA runtime.

If the documented versions cannot be installed on the chosen Linux distribution, record the incompatibility and choose one explicit compatibility set. Do not incrementally mix unrecorded package versions.

### 3.6 Full HaWoR source checkout

Place the complete upstream repository at:

```text
external/HaWoR/
```

Use a Git submodule pinned to the resolved full SHA corresponding initially to upstream revision `66c7d41`. Initialize it recursively so HaWoR's nested `lietorch` and Eigen submodules are present.

Why a submodule:

- all upstream code is in one clearly named folder;
- our code never appears to be part of HaWoR;
- the exact upstream revision is recorded by Git;
- upstream updates are deliberate rather than silent; and
- users can inspect the exact external implementation while our adapters remain small.

Rules for `external/HaWoR/`:

- do not edit files in place for normal Milestone 1 work;
- do not copy HaWoR modules into `src/`;
- run it through the adapter boundary described below;
- if a compatibility patch becomes unavoidable, stop, document the exact diff under `patches/hawor/`, and obtain approval before using it; and
- never commit model weights, MANO data, datasets, or generated HaWoR outputs inside the submodule.

### 3.7 Python libraries

Install the upstream HaWoR requirements, including its documented special cases:

- NumPy 1.26.4;
- OpenCV;
- PyTorch3D;
- `smplx`;
- `mmcv` and `mmengine`;
- `timm`, `einops`, and transformer/model support libraries;
- Ultralytics and tracking dependencies;
- SciPy/scikit-image and scientific utilities;
- `pyrender`, `aitviewer`, `moderngl-window`, and rendering dependencies;
- `joblib`, pandas, Hydra/YACS, and serialization/configuration libraries;
- `torch-scatter` matching PyTorch/CUDA;
- PyTorch Lightning 2.2.4 installed using the upstream instructions; and
- all remaining packages in HaWoR's pinned `requirements.txt`.

Install HaWoR's masked DROID-SLAM package from `external/HaWoR/thirdparty/DROID-SLAM`. This compiles both `droid_backends` and `lietorch_backends` CUDA extensions.

Project-side additions, declared in `environment/hawor.yml` once project-owned code exists:

- `pytest` for focused automated checks;
- `psutil` for process RAM sampling; and
- no dataframe/storage dependency beyond NumPy and the Python standard library in Milestone 1.

Milestone 1 does not add `projectaria_tools`, `hand_tracking_toolkit`, a HOT3D reader, or another camera-calibration package. Its input boundary is an ordinary local MP4, and its preparation path uses the already required FFmpeg/ffprobe tools. The `ego4d` downloader is acquisition tooling only: if it is needed to fetch the selected source, run it outside the validated `hawor` runtime rather than adding it to `environment/hawor.yml`.

All resolved versions are captured after the successful smoke test. A generated environment snapshot is evidence; `environment/hawor.yml` remains the reviewed recreation specification and includes any pip-installed packages that the upstream HaWoR stack cannot obtain through Conda. Conda remains the environment owner; uv and separate project-package metadata are not used.

### 3.8 Required model files and exact locations

Download or obtain these files under the external HaWoR checkout:

```text
external/HaWoR/weights/external/droid.pth
external/HaWoR/weights/external/detector.pt
external/HaWoR/weights/hawor/checkpoints/hawor.ckpt
external/HaWoR/weights/hawor/checkpoints/infiller.pt
external/HaWoR/weights/hawor/model_config.yaml
external/HaWoR/thirdparty/Metric3D/weights/metric_depth_vit_large_800k.pth
```

Record file size and SHA-256 for every weight. The run manifest may store those hashes, but the weights themselves remain untracked.

### 3.9 Required MANO files and exact locations

The user must create an account with the MANO provider, accept its license, download the MANO models, and supply:

```text
external/HaWoR/_DATA/data/mano/MANO_RIGHT.pkl
external/HaWoR/_DATA/data_left/mano_left/MANO_LEFT.pkl
```

The setup checker verifies that both files exist and are readable. The files must never be committed, copied into outputs, or redistributed.

### 3.10 Bundled example and headless rendering

Verify that HaWoR includes:

```text
external/HaWoR/example/video_0.mp4
```

Configure rendering so it works inside WSL/Linux without requiring an interactive desktop window. Prefer a headless EGL path if supported. The setup gate includes generating an actual video or representative rendered frames, not merely completing model inference.

Request Ego4D access early enough that data acquisition does not block final validation. The official documentation estimates approximately 48 hours to receive AWS credentials after license approval; those credentials expire after 14 days and can be renewed. Keep credentials outside the repository. Download only one selected video or clip UID as an MP4, preserve it unchanged under `data/source/ego4d/<video_uid>/`, and do not download the full dataset. The selected source and interval are required for the Ego4D run, but they do not block implementation and synthetic validation against the bundled example.

### 3.11 Setup verification checklist

`scripts/check_hawor_setup.py` will perform read-only checks and emit a human-readable summary plus JSON evidence. It will verify:

- operating system is Linux/WSL;
- expected Python and package versions;
- `git`, `ffmpeg`, and `ffprobe` availability;
- PyTorch CUDA access and GPU identity;
- `nvcc` availability;
- HaWoR submodule presence and exact commit;
- nested submodules initialized;
- DROID-SLAM and `lietorch` extensions import successfully;
- all required weight and MANO paths exist;
- weight hashes can be calculated;
- example video can be decoded;
- when acquired, the selected Ego4D source is a decodable MP4 and its immutable hash can be calculated;
- output directories are writable without overwriting prior runs; and
- after project-owned code exists, `PYTHONPATH=src python -c "import egocentric_pipeline"` resolves to this checkout and `python -m pip check` passes for the combined Conda/pip environment.

The setup gate passes only when all required checks pass. Warnings such as low VRAM remain visible in the evidence and report.

### 3.12 Conda-only project environment and CI setup

The project-owned modules and synthetic tests use Python 3.10 from the active `hawor` Conda environment. Milestone 1 does not create project-packaging metadata or install `egocentric_pipeline` into `site-packages`. User-facing and test commands run from the repository root with `PYTHONPATH=src`, for example:

```bash
PYTHONPATH=src python -m pytest tests
```

This explicit source-path contract preserves the planned `src/` layout while keeping Conda as the only project environment manager. Commands issued from another working directory are unsupported unless they set `PYTHONPATH` to the absolute checkout's `src/` path. The README records this constraint with every project command rather than depending on an implicit shell customization.

`environment/hawor.yml` declares the complete local GPU runtime plus direct and test dependencies actually imported by project-owned code. If an anticipated lightweight dependency is already supplied by Python or an existing approved package, omit it. The environment file may use a pip subsection for upstream packages that are not installable through Conda; this does not introduce a second project dependency specification.

Create `environment/cpu-tests.yml` and `.github/workflows/ci.yml` when the first CPU-safe synthetic test is added. The smaller Conda specification contains only Python 3.10, FFmpeg, and the direct/test libraries required by the synthetic project tests; it deliberately excludes HaWoR, CUDA, licensed assets, and real datasets. On pull requests and pushes to the repository's default branch, CI creates that Conda environment, verifies that `PYTHONPATH=src` imports `egocentric_pipeline` from the checkout, and runs the complete CPU-safe suite with `PYTHONPATH=src python -m pytest tests`. Tests requiring the excluded resources remain explicit local validation gates and are not silently skipped as if CI had verified them.

## 4. Input and Output Contracts / Data and Metadata Files

### 4.1 In-memory `ClipRequest`

A runnable clip no longer requires a human-authored `clip_config.json`. The reusable pipeline accepts a typed, in-memory `ClipRequest`. A request describes what the caller wants processed; it does not duplicate facts that must be measured from the source.

`ClipRequest` contains:

- `source` — required `LocalVideoSource`: immutable local `.mp4` path plus optional dataset name and dataset-native video ID.
- `interval` — optional `[start_s, end_s)` selection in source time; null means the complete source.
- `clip_id` — optional stable local identifier. When absent, preparation derives one deterministically from source identity/checksum and the resolved interval.
- `task_label` — optional short human-readable action. It is not inferred from pixels.
- `license_reference` — optional while running a private local test, but required before a clip is accepted into a dataset deliverable.
- `focal_length_px` — optional positive finite scalar focal length in source/prepared pixels. When omitted, the request uses HaWoR's native 600 px fallback and labels it approximate rather than estimating or loading calibration.

`src/egocentric_pipeline/clip_request.py` normalizes only request syntax and intent: MP4 path, seconds and half-open interval semantics, optional strings, focal-length units, and the 600 px fallback. It does not probe or transform video, infer source FPS, create timestamps, estimate intrinsics, or load camera calibration.

Requests are constructed without one file per clip:

- `scripts/prepare_clip.py` and `scripts/run_hawor_pipeline.py` build a request directly from local MP4 command-line arguments; and
- `scripts/run_milestone1_baseline.py` constructs a request for the bundled example, an Ego4D MP4, or an optional local development MP4, or passes one existing prepared-clip metadata path to the pipeline.

The normalized request is snapshotted inside the generated `clip_metadata.json`. A separate request/config file is optional and is not part of the Milestone 1 architecture.

### 4.2 MP4 source contract

Every Milestone 1 source is an immutable, directly decodable `.mp4`. The required sources are the bundled HaWoR example at `external/HaWoR/example/video_0.mp4` and one licensed Ego4D MP4 stored under `data/source/ego4d/<video_uid>/`. A self-recorded MP4 may temporarily exercise the same path during development, but it does not replace the Ego4D acceptance run. YouTube acquisition is not supported.

FFprobe must identify one usable video stream, valid dimensions and duration, decodable presentation timestamps, and image geometry that HaWoR can consume without a spatial transform. Preparation may select a time interval, normalize timing to constant 30 FPS, choose the supported codec/pixel format, and remove audio. It preserves width and height and does not rectify, crop, pad, resize, rotate, or undistort. An input with non-upright display rotation, unsupported geometry, or a decoding/timing failure is rejected with corrective guidance instead of silently transformed.

Milestone 1 neither detects nor corrects lens distortion and does not claim calibrated reconstruction. A supplied `focal_length_px` is passed through with user-supplied provenance. If it is absent, preparation passes HaWoR's native 600 px fallback explicitly and records `provenance: hawor_default` and `quality: approximate`. The focal value and this limitation appear in clip metadata and the benchmark report.

### 4.3 Prepared clip and metadata

Input preparation writes:

```text
data/prepared/<clip_id>/rgb.mp4
data/prepared/<clip_id>/clip_metadata.json
```

`video_preparation.prepare_clip(request) -> PreparedClip` validates and probes the local MP4, writes both artifacts, and returns a typed in-memory object containing the prepared video path, metadata path, and the same typed `ClipMetadata` value serialized to JSON. JSON is written successfully before `PreparedClip` is returned.

`rgb.mp4` is a derived, constant-rate 30 FPS, HaWoR-ready video. Preparation creates a 30 FPS timestamp grid over the selected source interval and selects source frames by presentation timestamp. It does not change playback speed. Higher-rate sources lose unselected frames; lower-rate sources reuse the nearest source frame when permitted by the preparation-quality policy. The user-approved initial limits are a maximum repeated-source-frame fraction of 0.05, maximum source-frame gap of 0.10 seconds, and maximum absolute source-to-prepared timestamp-selection error of 1/60 second. Inputs exceeding any limit are rejected before inference; these limits must remain explicitly named and configurable.

`clip_metadata.json` has a schema version and these owned sections:

- `request`: normalized snapshot of every `ClipRequest` field and the constructor used (`direct_video` or `milestone1_baseline`).
- `source`: source kind (`local_mp4`), immutable path, SHA-256, optional dataset/video identity, license reference, codec/pixel format, width, height, display rotation, sample/display aspect ratio, time base, duration, nominal/average frame rates, frame count, and whether timing is constant or variable rate.
- `selection`: requested and resolved `[start_s, end_s)` bounds and source frame/timestamp bounds.
- `preparation`: preparation implementation/version, exact FFmpeg/ffprobe commands and versions, output codec and pixel format, audio disposition, timestamp origin, temporal interval/30 FPS resampling history, and explicit confirmation that no rectification, crop, pad, resize, rotation, undistortion, or other spatial transform was applied.
- `prepared`: prepared path and SHA-256, width, height, constant `30/1` FPS, time base, duration, frame count, and codec/pixel format.
- `hawor_camera`: scalar `focal_length_px`, provenance (`user_supplied` or `hawor_default`), quality (`provided` or `approximate`), and explicit statements that calibration was not loaded and lens distortion was not corrected.
- `frames`: one entry per prepared frame containing prepared frame index/timestamp, selected source frame index/timestamp, timestamp-selection error, and whether that source frame is reused. Aggregate fields record source frames considered, unique frames selected, dropped frames, repeated-source-frame count/fraction, median/maximum timestamp error, and maximum source-frame gap.
- `artifacts`: paths and hashes needed to connect the prepared clip to its immutable source and later run artifacts.
- `created_at`: UTC creation timestamp.

The metadata is sufficient to audit and reproduce every preparation decision when the immutable original is available. It does not claim that a lossy, frame-dropping prepared MP4 can be inverted to reconstruct the original by itself. Original source files are preserved; preparation refuses to overwrite an existing prepared clip whose source hash, request snapshot, or generated metadata differs.

For a later run that starts from an existing prepared directory, `load_prepared_clip(clip_metadata_path)` parses and validates the JSON, verifies the prepared/source hashes that are locally available, and returns the same `PreparedClip`/`ClipMetadata` types used by a fresh preparation.

### 4.4 Native HaWoR artifacts

HaWoR runs against a staged copy or link of the prepared clip inside the new run directory. This matters because the stock demo creates its working folders next to the input video. All native products remain together under:

```text
outputs/hawor/<run_id>/clips/<clip_id>/native/
```

Expected native artifacts include extracted RGB frames, detection tracks, masks, camera-space chunk JSON files, scaled SLAM output, `world_space_res.pth`, visualization frames/video, and console logs. These files are preserved as evidence and are never treated as our stable cross-milestone interface.

### 4.5 Stable world-frame export

`trajectory_world.npz` repackages HaWoR's final `world_space_res.pth` without applying a coordinate transform. Arrays are frame-major; `T` is prepared-video frame count and `H = 2` is ordered `[left, right]`:

- `frame_index`: `int64 [T]`.
- `timestamp_s`: `float64 [T]`, relative to the prepared clip.
- `source_timestamp_s`: `float64 [T]`, relative to the source video.
- `root_translation_world_m`: `float32 [T, H, 3]`, copied/reordered from HaWoR `pred_trans`.
- `root_orientation_world_axis_angle`: `float32 [T, H, 3]`, copied/reordered from HaWoR `pred_rot`.
- `hand_pose_axis_angle`: `float32 [T, H, 45]`, copied/reordered from HaWoR `pred_hand_pose`.
- `mano_betas`: `float32 [T, H, 10]`, copied/reordered from HaWoR `pred_betas`.
- `direct_detection`: `bool [T, H]`, reconstructed from the saved detector tracks.
- `motion_infilled`: `bool [T, H]`, true when the final value came from HaWoR's infiller rather than direct hand estimation.
- `hawor_valid`: `bool [T, H]`, copied/reordered from HaWoR's final `pred_valid` so the upstream meaning is preserved.
- `export_valid`: `bool [T, H]`, true only when `hawor_valid` is true, every exported value for that frame/hand is finite, and the required upstream stages completed.
- `detector_confidence`: `float32 [T, H]`, `NaN` when no direct detector output exists.

Detection and confidence provenance follow HaWoR's final track-to-hand
assignment: majority vote over the track, with ties assigned right, as in the
pinned engine. The user confirmed this choice on 2026-09-15. Record raw
per-frame handedness disagreements in trajectory validation metadata so they
remain visible without disconnecting provenance from the native trajectory.
Derive direct-estimation coverage from the preserved frame chunks and camera
results when determining infill; a detector record alone does not prove that
HaWoR estimated that frame (for example, an entire singleton track is skipped).

The pinned demo's bounding-box interpolation call is effectively a no-op because its track arrays contain only detected frames; gaps are split before hand estimation and later handled by the motion infiller. We will test and document that observed behavior rather than invent a `bbox_interpolated` provenance class for this revision.

`trajectory_metadata.json` documents:

- exact mapping from each NPZ field to the native HaWoR field;
- hand ordering and dtype/shape contracts;
- units claimed by HaWoR;
- that the coordinate frame is the unchanged HaWoR metric world frame;
- that its origin/orientation are clip-local SLAM gauge choices and not comparable across clips;
- the native artifact paths and hashes;
- validity/provenance definitions; and
- all validation results.

No canonical arrays, aligned coordinates, camera-frame copies, transformed joints, or robot-frame data are produced in this milestone.

### 4.6 Per-run record and benchmark report

Every valid `run_milestone1_baseline.py` invocation processes exactly one clip and receives a unique, non-overwriting `run_id`. It writes the following run-level artifacts together:

```text
outputs/hawor/<run_id>/run_manifest.json
outputs/hawor/<run_id>/benchmark.json
outputs/hawor/<run_id>/benchmark_report.md
```

`run_manifest.json` is generated and finalized by `pipeline.py` for the single clip attempt. Once request syntax has been validated and a run directory has been allocated, the manifest is finalized for both successful and failed pipeline outcomes. It records the schema version, `run_id`, clip/source identity, normalized request reference, start/end timestamps, overall status, ordered stage statuses, commands and environment, timing and resource samples, structural-validation results, artifact paths and hashes, warnings, and captured failure details. Missing downstream artifacts after a failed stage are recorded explicitly rather than fabricated.

`benchmark.json` is generated by `benchmark.py` from that one finalized manifest and any artifacts that exist for the same run. It contains:

- schema version, `run_id`, `clip_id`, source/dataset identity, and Milestone 1 run role (`setup_smoke`, `ego4d`, or `other_test`);
- overall and per-stage completion status, failure stage, and concise error summary;
- source/preparation timing-quality and focal-value/provenance metrics when available;
- wall-clock time, effective FPS, peak RAM, and peak GPU memory when available;
- direct-detection, motion-infill, invalid-frame, longest-gap, and provenance-coverage metrics when export exists;
- structural contract violations and generated artifact paths/hashes;
- manual-review status (`pending`, `complete`, or `not_possible`) and supplied failure labels/notes; and
- environment deviations, limitations, and claims that remain unverified.

Unavailable values are `null` with a reason; failed runs remain reportable. `benchmark_report.md` is a human-readable, approximately one-page rendering of the same single-run evidence and must not imply cross-run aggregation or statistical generalization. Both benchmark files belong only to their containing `run_id` and are never shared or overwritten by a later invocation.

`run_milestone1_baseline.py` always calls `benchmark.py` after `pipeline.py` has finalized a run manifest, including after a pipeline-stage failure. Users do not invoke `benchmark.py` separately. Invalid command-line/request syntax that is rejected before run allocation does not create a benchmark report. Milestone completion is demonstrated by accepted per-run evidence for the bundled HaWoR example and one qualifying Ego4D MP4 segment; there is no Milestone 1 multi-run controller or automatically discovered aggregate report.

## 5. Planned Repo Structure

Only files reached by the implementation sequence are created. The tree below is the complete intended Milestone 1 structure, including generated/untracked paths for clarity.

```text
Egocentric/
├── AGENTS.md
├── README.md                           # existing; maintained from implementation start
├── .gitignore
├── .gitmodules
├── .github/
│   └── workflows/
│       └── ci.yml                      # new; CPU-safe project checks only
├── knowledge/
│   ├── agent/
│   │   ├── PLANNING_SPECS.md
│   │   ├── PROJECT_STATUS.md
│   │   └── plans/
│   │       └── milestone-1-hawor-baseline.md
│   └── raw/
│       ├── Project-Milestones-and-Timeline.md
│       └── Sources/
│           └── HaWoR-Review.md
├── environment/
│   ├── README.md
│   ├── hawor.yml                       # full local GPU/runtime environment
│   └── cpu-tests.yml                   # new; minimal CPU-only CI environment
├── external/
│   └── HaWoR/                         # pinned Git submodule; upstream code
├── src/
│   └── egocentric_pipeline/
│       ├── __init__.py
│       ├── clip_request.py
│       ├── video_preparation.py
│       ├── hawor_runner.py
│       ├── world_export.py
│       ├── visualization.py
│       ├── run_metadata.py
│       ├── pipeline.py
│       └── benchmark.py
├── scripts/
│   ├── check_hawor_setup.py
│   ├── prepare_clip.py
│   ├── run_hawor_pipeline.py
│   └── run_milestone1_baseline.py
├── tests/
│   ├── test_clip_preparation.py
│   ├── test_world_export.py
│   ├── test_run_metadata.py
│   └── test_benchmark.py
├── data/                               # untracked local licensed/input data
│   ├── source/
│   │   └── ego4d/<video_uid>/<source>.mp4 # immutable licensed source
│   └── prepared/
│       └── <clip_id>/
│           ├── rgb.mp4
│           └── clip_metadata.json
└── outputs/                            # untracked generated evidence
    └── hawor/<run_id>/
        ├── run_manifest.json
        ├── setup_check.json
        ├── benchmark.json
        ├── benchmark_report.md
        └── clips/<clip_id>/
            ├── native/...
            ├── trajectory_world.npz
            ├── trajectory_metadata.json
            ├── overlay.mp4
            └── trajectory_preview.png
```

## 6. File Breakdown

### 6.1 Environments and external code

#### `environment/README.md` — reusable documentation

**Description:** Human instructions for WSL/Linux setup, Conda creation, CUDA/PyTorch compatibility checks, model/MANO placement, installation order, the repository-root `PYTHONPATH=src` invocation contract, headless rendering, and common recovery steps. It links to `hawor.yml`, `cpu-tests.yml`, and `check_hawor_setup.py`; it does not duplicate package lists already expressed in the environment files.

**Input:** None.

**Output:** Human-readable setup and recovery instructions.

**Calls:** N/A — documentation file.

**Called by:** Developers setting up any milestone that runs HaWoR.

**Metadata written:** None.

#### `environment/hawor.yml` — reusable environment specification

**Description:** The sole reviewed dependency declaration for the successfully validated local GPU environment. It contains the HaWoR/CUDA stack plus direct and test libraries actually imported by project-owned code. A pip subsection is allowed only for upstream packages that Conda cannot supply compatibly; there is no separate project-package dependency file.

**Input:** None.

**Output:** The reviewed environment specification.

**Calls:** N/A — declarative file.

**Called by:** Local environment setup; checked by `scripts/check_hawor_setup.py`; version recorded by `run_metadata.py`.

**Metadata written:** None.

#### `environment/cpu-tests.yml` — reusable CI environment specification

**Description:** Minimal Conda environment for CPU-safe synthetic validation. It pins Python 3.10 and lists only FFmpeg plus the direct/test libraries needed by the synthetic test suite. It excludes HaWoR, CUDA, GPU packages, model weights, MANO files, and datasets. Its overlap with `hawor.yml` is limited to dependencies shared by those tests and is checked when either environment changes.

**Input:** None.

**Output:** The reviewed CPU-test environment specification.

**Calls:** N/A — declarative file.

**Called by:** `.github/workflows/ci.yml` and developers reproducing CPU-only checks without the full HaWoR environment.

**Metadata written:** None.

#### `.gitmodules` and `external/HaWoR/` — reusable external engine

**Description:** `.gitmodules` identifies the official HaWoR repository. `external/HaWoR/` is the pinned full source tree and nested submodules. Our modules invoke it but never import private copies of its code from elsewhere.

**Input:** The official HaWoR repository and its nested submodules.

**Output:** The pinned external HaWoR engine at `external/HaWoR/`.

**Calls:** N/A — submodule declaration and external code.

**Called by:** `scripts/check_hawor_setup.py`, `src/egocentric_pipeline/hawor_runner.py`, and `src/egocentric_pipeline/visualization.py`.

**Metadata written:** None.

#### `.gitignore` — reusable repository protection

**Description:** Excludes weights, MANO files, licensed videos, prepared video data, native HaWoR work products, environment caches, and generated outputs while leaving reviewed source/configuration files trackable.

**Input:** None.

**Output:** Repository ignore rules.

**Calls:** N/A — declarative file.

**Called by:** The repository as a whole.

**Metadata written:** None.

### 6.2 Configuration and repository support

Milestone 1 has no persistent per-clip configuration files. Clip intent is supplied through direct-MP4 command-line arguments and normalized into an in-memory `ClipRequest`. The request snapshot, resolved defaults, source identity, and all measured/generated facts are persisted in `clip_metadata.json` and the run manifest.

#### `README.md` — existing reusable documentation, modified throughout Milestone 1

**Description:** The user-facing entry point for the repository. At the first implementation change, add an About section that explains the project purpose, the RGB-to-world-frame-hand-trajectory direction, and Milestone 1's unchanged-HaWoR baseline boundary. Preserve the already verified HaWoR installation guidance, then add Conda environment, source-path, test, and user-facing command guidance only as those workflows are implemented and verified. Keep it current in the same change whenever a public command, prerequisite, supported workflow, or output location changes. Link to the roadmap, current status, active plan, and detailed environment documentation instead of duplicating progress records or long setup material.

**Input:** Verified repository purpose, supported workflows, commands, setup requirements, and authoritative links from `knowledge/` and `environment/`.

**Output:** A concise root README with an About section and accurate setup, development, test, and usage guidance for the functionality that exists at that point in Milestone 1.

**Calls:** N/A — documentation file.

**Called by:** Developers and users entering the repository.

**Metadata written:** None.

#### `.github/workflows/ci.yml` — new reusable CPU-safe validation workflow

**Description:** Runs the project-owned synthetic validation suite on Ubuntu for pull requests and pushes to the default branch. It creates the minimal Conda environment from `environment/cpu-tests.yml`, verifies the source-tree import contract, and runs pytest. It does not install the project as a Python distribution, initialize or execute HaWoR, use a GPU, fetch licensed/model/data assets, or represent local end-to-end validation as passing CI coverage.

**Input:** The checked-out project-owned source and tests, `environment/cpu-tests.yml`, and the GitHub-hosted Ubuntu runner.

**Output:** GitHub Actions job status and logs for Conda environment creation, source-tree import verification, and the complete CPU-safe synthetic test suite.

**Calls:** Official GitHub checkout and reviewed Conda-environment setup actions pinned to full commit SHAs, Conda using `environment/cpu-tests.yml`, `PYTHONPATH=src python -c "import egocentric_pipeline"`, and `PYTHONPATH=src python -m pytest tests` over the four planned test files in Section 6.5.

**Called by:** Pull-request and default-branch push events in GitHub Actions; developers may rerun an existing workflow run through GitHub.

**Metadata written:** None in the repository; GitHub retains workflow status and logs according to repository settings.

### 6.3 `src/` modules

#### `src/egocentric_pipeline/clip_request.py` — reusable

**Description:** Defines `ClipRequest`, its local-MP4 source reference, interval and optional focal-length fields, validation, the explicit 600 px HaWoR fallback, and constructors from direct command arguments. It normalizes request syntax and intent only. It does not read video metadata, decode frames, estimate/load calibration, or write a per-clip configuration file.

**Input:** A local MP4 path plus optional dataset/video identity, interval, clip ID, task label, license reference, and focal length supplied by callers.

**Output:** A normalized in-memory `ClipRequest`.

**Calls:** None.

**Called by:** `src/egocentric_pipeline/pipeline.py`, `scripts/prepare_clip.py`, `scripts/run_hawor_pipeline.py`, `scripts/run_milestone1_baseline.py`, and `tests/test_clip_preparation.py`.

**Metadata written:** None.

#### `src/egocentric_pipeline/video_preparation.py` — reusable

**Description:** Owns the boundary between a normalized local-MP4 `ClipRequest` and a HaWoR-ready `PreparedClip`. It probes and converts the immutable source with FFmpeg/ffprobe, resolves the requested interval, builds a source-time 30 FPS grid without changing playback speed, selects frames by presentation timestamp, preserves source width/height, records the supplied or 600 px fallback focal value, calculates hashes, and refuses ambiguous or destructive overwrites. It performs no spatial correction and rejects an input that would require rotation, rectification, crop, pad, resize, undistortion, or another geometry change. It remains the sole owner of the typed `ClipMetadata` and `PreparedClip` contracts, `clip_metadata.json`, and the loader for an existing prepared directory.

**Input:** A normalized `ClipRequest`, its immutable local MP4, and the supported preparation-quality policy.

**Output:** `data/prepared/<clip_id>/rgb.mp4`, `data/prepared/<clip_id>/clip_metadata.json`, and an in-memory `PreparedClip` containing the same typed `ClipMetadata` value that was serialized.

**Calls:** FFmpeg/ffprobe and checksum/serialization helpers from `src/egocentric_pipeline/run_metadata.py`.

**Called by:** `scripts/prepare_clip.py`, `src/egocentric_pipeline/pipeline.py`, and `tests/test_clip_preparation.py`.

**Metadata written:** Owns all of `clip_metadata.json` as specified in Section 4.3: request snapshot; source identity, hash, and media/timing facts; interval resolution; FFmpeg/ffprobe commands and versions; temporal, color, audio, and encoding steps; explicit confirmation that no spatial correction was applied; prepared artifact facts and hashes; source-to-prepared frame mapping and resampling metrics; HaWoR focal value/provenance and uncorrected-distortion limitation; and creation time. Shared hashing, timestamp, and JSON serialization use `run_metadata.py`.

#### `src/egocentric_pipeline/hawor_runner.py` — reusable

**Description:** Treats HaWoR as an external inference engine. It verifies the submodule revision and required files, creates a new run workspace, stages the prepared video under `native/`, invokes the official HaWoR entry point with an explicit focal length, captures stdout/stderr and exit status, samples peak RAM/VRAM, and returns paths to native artifacts. It does not interpret or modify coordinates. It is reusable later for every milestone that needs unchanged HaWoR inference.

**Input:** `external/HaWoR/`, a validated in-memory `PreparedClip` containing typed `ClipMetadata`, and required model/MANO files. For a fresh preparation it consumes the object returned by `video_preparation.py`; for a resumed run, `video_preparation.load_prepared_clip()` first parses and validates `clip_metadata.json` into that same object. The runner does not maintain a second independent metadata parser.

**Output:** Native HaWoR outputs, logs, per-stage execution records, resource samples, and paths to the native artifacts.

**Calls:** The official entry point in `external/HaWoR/` and shared helpers in `src/egocentric_pipeline/run_metadata.py`.

**Called by:** `src/egocentric_pipeline/pipeline.py`.

**Metadata written:** Per-stage execution records used by `run_manifest.json`, including the captured command/environment, stdout/stderr locations, exit status, stage timing, and peak RAM/VRAM, using `run_metadata.py`.

#### `src/egocentric_pipeline/world_export.py` — reusable

**Description:** Defines the stable boundary leaving HaWoR. It transposes HaWoR's hand-major arrays to the documented frame-major layout, calculates direct-detection and infilled masks, checks finite values and frame counts, and writes the stable world-frame trajectory interface used by later annotation, retargeting, evaluation, and visualization work. Copying/reordering array dimensions is allowed; altering coordinate values is not. The module contains an explicit assertion that no transform, scale, offset, smoothing, or alignment has been applied. It is reusable later for Milestones 2–5 and the optional research comparison track.

**Input:** Native `world_space_res.pth` and saved detection tracks from `hawor_runner.py`, plus the prepared/source timestamp mapping in the validated `PreparedClip` metadata.

**Output:** `trajectory_world.npz` and `trajectory_metadata.json`.

**Calls:** Shared hashing and serialization helpers in `src/egocentric_pipeline/run_metadata.py`.

**Called by:** `src/egocentric_pipeline/pipeline.py` and `tests/test_world_export.py`.

**Metadata written:** `trajectory_metadata.json`, containing the native-field mapping, hand ordering, dtype/shape contracts, HaWoR-claimed units, unchanged HaWoR metric world-frame definition, clip-local SLAM gauge limitation, native artifact paths and hashes, validity/provenance definitions, and validation results, using `run_metadata.py` where shared helpers apply.

#### `src/egocentric_pipeline/visualization.py` — reusable

**Description:** Creates an RGB overlay using HaWoR's own rendering/projection utilities and native camera information, plus a simple 3D root-trajectory preview that plots the unchanged exported world coordinates and clearly labels the axes as HaWoR world axes. It does not save a transformed trajectory. Any temporary display transform required by the renderer is isolated and documented as visualization-only. It is reusable later for pilot-dataset review, failure inspection, retargeting comparisons, and expanded-dataset QA.

**Input:** Prepared RGB video, native HaWoR camera/rendering artifacts, `trajectory_world.npz`, and the rendering helpers in `external/HaWoR/`.

**Output:** `overlay.mp4` and `trajectory_preview.png`.

**Calls:** Rendering/projection helpers in `external/HaWoR/`.

**Called by:** `src/egocentric_pipeline/pipeline.py`.

**Metadata written:** None.

#### `src/egocentric_pipeline/run_metadata.py` — reusable

**Description:** Provides small shared helpers for SHA-256 hashing, timestamps, command/environment capture, software versions, hardware identity, non-overwriting run IDs, stage status, and JSON serialization. It owns no video or HaWoR logic and is reusable later for provenance across all milestones.

**Input:** Files to hash, runtime environment and hardware state, commands, timestamps, stage results, run identifiers, and metadata values supplied by its callers.

**Output:** Hashes, captured environment/software/hardware values, non-overwriting run IDs, stage-status records, and serialized JSON portions.

**Calls:** None.

**Called by:** `scripts/check_hawor_setup.py`, `src/egocentric_pipeline/video_preparation.py`, `src/egocentric_pipeline/hawor_runner.py`, `src/egocentric_pipeline/world_export.py`, `src/egocentric_pipeline/pipeline.py`, `src/egocentric_pipeline/benchmark.py`, and `tests/test_run_metadata.py`.

**Metadata written:** Consistent portions of `setup_check.json`, `clip_metadata.json`, `run_manifest.json`, `trajectory_metadata.json`, and `benchmark.json`, as assigned to each calling component; it owns the shared hashing, timestamp, command/environment, software/hardware, run-ID, stage-status, and JSON-serialization field groups.

#### `src/egocentric_pipeline/pipeline.py` — reusable top-level API

**Description:** The central programmatic interface, conceptually `run_clip(request: ClipRequest) -> RunResult`. It performs no model math. It validates request syntax, allocates a non-overwriting run record for the single clip attempt, prepares a new clip or loads and verifies an existing `PreparedClip`, verifies the recorded focal value and preparation-quality gate before inference, calls HaWoR, exports the unchanged world result, renders review artifacts, runs structural validation, and finalizes the run manifest for success or failure. It is reusable later for direct local videos or larger dataset jobs.

**Input:** A normalized in-memory `ClipRequest` or explicitly requested existing `clip_metadata.json`, its source/prepared state, and the configured HaWoR runtime.

**Output:** `RunResult`, the finalized per-clip run directory and available artifacts, structural validation results, and a success-or-failure `run_manifest.json`.

**Calls:** `src/egocentric_pipeline/clip_request.py`, `src/egocentric_pipeline/video_preparation.py`, `src/egocentric_pipeline/hawor_runner.py`, `src/egocentric_pipeline/world_export.py`, `src/egocentric_pipeline/visualization.py`, and `src/egocentric_pipeline/run_metadata.py`.

**Called by:** `scripts/run_hawor_pipeline.py` and `scripts/run_milestone1_baseline.py`.

**Metadata written:** Creates and finalizes `run_manifest.json`, including run identity, stage status, validation results, artifact locations, and shared environment/provenance fields supplied by `run_metadata.py`.

#### `src/egocentric_pipeline/benchmark.py` — mostly reusable

**Description:** Builds machine-readable benchmark evidence and a concise Markdown failure report for one finalized run. It reports available metrics for successful or failed attempts and never scans output directories or combines unrelated runs. The metric-extraction logic is reusable; the one-page Milestone 1 wording and run-role vocabulary are milestone-specific parameters.

**Input:** One finalized `run_manifest.json`; the same run's `trajectory_metadata.json`, resource samples, and generated artifacts when present; its Milestone 1 run role; and optional human review status, labels, and notes.

**Output:** `benchmark.json` and `benchmark_report.md` inside that run's unique directory.

**Calls:** Shared serialization and metadata helpers in `src/egocentric_pipeline/run_metadata.py`.

**Called by:** `scripts/run_milestone1_baseline.py` and `tests/test_benchmark.py`.

**Metadata written:** `benchmark.json`, containing the single-run identity, role, status, metrics, artifact evidence, review state, failures, environment deviations, limitations, and unavailable-value reasons defined in Section 4.6, using consistent shared portions from `run_metadata.py`.

### 6.4 `scripts/` entry points

#### `scripts/check_hawor_setup.py` — reusable

**Description:** Read-only preflight command described in Section 3.11. It is the first command run on a new machine.

**Input:** The active Conda environment, repository-root source-path state, and external-checkout state listed in Section 3.11.

**Output:** A human-readable summary and `setup_check.json` evidence.

**Calls:** Conda/environment inspection, repository-root `PYTHONPATH=src` import verification, `python -m pip check` for the combined Conda/pip environment, shared helpers in `src/egocentric_pipeline/run_metadata.py`, and checks against `external/HaWoR/`.

**Called by:** Developers setting up a machine.

**Metadata written:** `setup_check.json`, recording operating system, Python and package versions, project source-import origin and dependency consistency when applicable, tool availability, PyTorch CUDA/GPU identity, `nvcc`, HaWoR and nested-submodule revisions, required weight/MANO presence and hashes, example-video decodability, output-directory writability, and visible warnings, using `run_metadata.py`.

#### `scripts/prepare_clip.py` — reusable

**Description:** Thin command-line entry point for constructing a local-MP4 `ClipRequest` and running `video_preparation.py` independently. A local video path works without a sidecar file. It is useful when selecting or inspecting a clip before paying the cost of inference.

**Input:** A local MP4 path and optional interval, clip ID, dataset/video identity, task label, license reference, and focal-length arguments.

**Output:** The prepared `rgb.mp4` and `clip_metadata.json` produced by `video_preparation.py`.

**Calls:** `src/egocentric_pipeline/clip_request.py` and `src/egocentric_pipeline/video_preparation.py`.

**Called by:** Users preparing a clip independently.

**Metadata written:** None directly; `video_preparation.py` writes `clip_metadata.json`.

#### `scripts/run_hawor_pipeline.py` — reusable

**Description:** Thin general-purpose command-line front end to `pipeline.run_clip`. It constructs a `ClipRequest` from direct local-MP4 arguments, including optional dataset identity, or accepts an existing prepared `clip_metadata.json`, and prints the run directory and final status. No per-clip configuration file is required. This is the command expected to survive into later milestones.

**Input:** Direct-MP4 request arguments, or an existing prepared `clip_metadata.json`, plus the configured HaWoR runtime.

**Output:** The run directory and final status printed for the user, plus the run artifacts produced by `pipeline.py`.

**Calls:** `src/egocentric_pipeline/clip_request.py` and `src/egocentric_pipeline/pipeline.py`.

**Called by:** Users running an arbitrary clip.

**Metadata written:** None directly; `pipeline.py` writes and finalizes the run metadata.

#### `scripts/run_milestone1_baseline.py` — Milestone 1-specific

**Description:** Runs exactly one Milestone 1 clip attempt per invocation. It constructs one bundled-example, Ego4D, or optional local-development MP4 request from runtime arguments, or selects one existing prepared clip, calls the reusable pipeline once, and then calls `benchmark.py` for that same run. It contains no reusable video, HaWoR, export, visualization, or multi-run aggregation logic, and it never requires the other milestone clip to be supplied or run in the same invocation.

**Input:** Exactly one source selection: the bundled HaWoR example, a direct local MP4 with optional dataset name/native ID, or an existing prepared `clip_metadata.json`. Also accepts the selected interval, optional focal length, one Milestone 1 run role (`setup_smoke`, `ego4d`, or `other_test`), and optional review state. The bundled-example path is resolved from the pinned upstream checkout.

**Output:** One unique Milestone 1 run directory containing the available pipeline artifacts, finalized `run_manifest.json`, and that run's `benchmark.json` and `benchmark_report.md`; prints the run directory and final status.

**Calls:** `src/egocentric_pipeline/clip_request.py`, `src/egocentric_pipeline/pipeline.py` exactly once, and then `src/egocentric_pipeline/benchmark.py` for the finalized run.

**Called by:** Users running one Milestone 1 clip attempt. The user invokes it separately for the bundled smoke test and the Ego4D or optional development clip as needed.

**Metadata written:** None directly; `pipeline.py` owns `run_manifest.json`, and `benchmark.py` owns the same run's `benchmark.json` and `benchmark_report.md`.

### 6.5 Tests

#### `tests/test_clip_preparation.py` — reusable contracts

**Description:** Uses tiny synthetic constant- and variable-rate MP4s to test `ClipRequest` defaults and validation, MP4-only rejection, half-open interval boundaries, presentation-timestamp-driven 30 FPS conversion without speed change, frame dropping/reuse and exact source mapping, timing-quality metrics, rejection of inputs requiring spatial correction, focal-value/provenance recording, checksum recording, prepared-clip reload, in-memory/JSON equivalence, and overwrite refusal without downloading datasets.

**Input:** Tiny synthetic MP4s, frame timestamps, focal-length cases, unsupported-spatial-metadata cases, and `ClipRequest` values.

**Output:** Automated pass/fail results for the clip-request, focal-provenance, preparation, metadata, and reload contracts.

**Calls:** `src/egocentric_pipeline/clip_request.py` and `src/egocentric_pipeline/video_preparation.py`.

**Called by:** Developers through the test runner and `.github/workflows/ci.yml`.

**Metadata written:** None.

#### `tests/test_world_export.py` — reusable contracts

**Description:** Uses a tiny synthetic HaWoR-like result to test hand-major to frame-major reordering, exact numeric preservation, shapes/dtypes, detection/infill provenance, invalid-value handling, and frame-count mismatch errors without loading neural networks. The main invariant is that coordinate values are bitwise unchanged apart from dtype conversion explicitly declared by the exporter.

**Input:** A tiny synthetic HaWoR-like result and associated timestamp/provenance fixtures.

**Output:** Automated pass/fail results for the world-export contracts.

**Calls:** `src/egocentric_pipeline/world_export.py`.

**Called by:** Developers through the test runner and `.github/workflows/ci.yml`.

**Metadata written:** None.

#### `tests/test_run_metadata.py` — reusable contracts

**Description:** Tests deterministic hashing, required run-manifest fields, unique/non-overwriting run IDs, stage failure recording, and secret redaction.

**Input:** Synthetic files, commands, environment values, run identifiers, and stage outcomes.

**Output:** Automated pass/fail results for shared run-metadata contracts.

**Calls:** `src/egocentric_pipeline/run_metadata.py`.

**Called by:** Developers through the test runner and `.github/workflows/ci.yml`.

**Metadata written:** None.

#### `tests/test_benchmark.py` — per-run reporting contracts

**Description:** Uses synthetic successful and failed run manifests to verify that one invocation produces one run-scoped `benchmark.json` and `benchmark_report.md`, preserves run/clip identity and role, reports unavailable metrics with reasons, includes supplied manual-review state, never aggregates or discovers other runs, and does not overwrite another run's report.

**Input:** Synthetic finalized run manifests, optional trajectory/resource artifacts, Milestone 1 run roles, and optional review labels/notes.

**Output:** Automated pass/fail results for the single-run benchmark and failure-report contracts.

**Calls:** `src/egocentric_pipeline/benchmark.py`.

**Called by:** Developers through the test runner and `.github/workflows/ci.yml`.

**Metadata written:** None.

## 7. End-to-End File/Script Flow

The primary Milestone 1 call tree is:

```text
scripts/run_milestone1_baseline.py
├── reads: exactly one source selection + Milestone 1 run role
├── selects: exactly one run input
│   ├── src/egocentric_pipeline/clip_request.py
│   │   └── constructs: bundled-example, Ego4D, or local-development MP4 ClipRequest
│   └── existing-prepared branch
│       └── passes: existing clip_metadata.json
├── calls exactly once: src/egocentric_pipeline/pipeline.py :: run_clip(request) -> RunResult
│   ├── src/egocentric_pipeline/clip_request.py
│   │   └── validates: MP4 path, interval, optional focal length, and provenance fields
│   ├── creates: non-overwriting outputs/hawor/<run_id>/ run record
│   ├── src/egocentric_pipeline/video_preparation.py
│   │   ├── reads: normalized ClipRequest + immutable local MP4
│   │   ├── calls: FFmpeg/ffprobe for probing and video-to-video preparation
│   │   ├── creates: 30 FPS source-time grid; selects by PTS without speed change
│   │   ├── records: temporal/color/audio conversion + frame drop/reuse
│   │   ├── preserves: source width/height and upright geometry
│   │   ├── rejects: inputs requiring any spatial correction
│   │   ├── records: supplied focal or explicit approximate 600 px fallback
│   │   └── writes: data/prepared/<clip_id>/rgb.mp4
│   │               data/prepared/<clip_id>/clip_metadata.json
│   │       returns: PreparedClip(video path, metadata path, typed ClipMetadata)
│   ├── enforces: focal-record and preparation-quality gate
│   ├── src/egocentric_pipeline/hawor_runner.py
│   │   ├── reads: validated in-memory PreparedClip/ClipMetadata
│   │   ├── verifies: persisted metadata/artifact identity
│   │   ├── calls as external engine: external/HaWoR/
│   │   └── writes: outputs/.../clips/<clip_id>/native/...
│   │               console logs + per-stage execution/resource records
│   ├── src/egocentric_pipeline/world_export.py
│   │   ├── reads: native world_space_res.pth + detection tracks
│   │   │           PreparedClip source/prepared timestamp mapping
│   │   └── writes: trajectory_world.npz
│   │               trajectory_metadata.json
│   ├── src/egocentric_pipeline/visualization.py
│   │   ├── reads: prepared RGB + native camera/rendering artifacts
│   │   │           trajectory_world.npz
│   │   ├── calls: external/HaWoR/ rendering/projection helpers
│   │   └── writes: overlay.mp4 + trajectory_preview.png
│   ├── runs: structural validation
│   └── writes/finalizes: success-or-failure run_manifest.json
└── src/egocentric_pipeline/benchmark.py
    ├── always called for that finalized run manifest
    ├── reads: this run's available trajectory metadata, resource samples,
    │           artifacts, role, and optional human review labels
    └── writes: this run's benchmark.json + benchmark_report.md
```

Repository documentation, Conda environment management, and CI remain outside the runtime pipeline. Their validation flow is:

```text
.github/workflows/ci.yml [pull request or default-branch push]
├── calls: official checkout + reviewed Conda setup actions pinned to full SHAs
├── reads: environment/cpu-tests.yml
├── creates: minimal Python 3.10 + FFmpeg CPU-test Conda environment
├── calls: PYTHONPATH=src python -c "import egocentric_pipeline"
└── calls: PYTHONPATH=src python -m pytest tests
    ├── tests/test_clip_preparation.py
    ├── tests/test_world_export.py
    ├── tests/test_run_metadata.py
    └── tests/test_benchmark.py

Explicitly excluded from CI
├── external/HaWoR/ initialization or execution
├── CUDA/GPU setup
├── model weights or MANO files
└── Ego4D and end-to-end clip runs
```

`README.md` is updated at implementation start and alongside later user-visible changes; it reads the verified commands and requirements represented by this plan, `environment/`, and the implemented entry points. It documents that commands run from the repository root with the `hawor` Conda environment active and `PYTHONPATH=src`. It is not a runtime dependency and does not participate in the core call tree.

Shared metadata calls across that tree are:

```text
src/egocentric_pipeline/run_metadata.py
├── called by: scripts/check_hawor_setup.py
│   └── contributes: setup_check.json
├── called by: video_preparation.py
│   └── contributes: clip_metadata.json
├── called by: hawor_runner.py
│   └── contributes: per-stage execution records in run_manifest.json
├── called by: world_export.py
│   └── contributes: trajectory_metadata.json
├── called by: pipeline.py
│   └── contributes: run_manifest.json
└── called by: benchmark.py
    └── contributes: benchmark.json
```

The standalone command and test call trees use the same modules:

```text
scripts/check_hawor_setup.py
├── inspects: environment/hawor.yml + runtime/system state
├── checks: .gitmodules + external/HaWoR/ + weights/MANO files
├── calls: src/egocentric_pipeline/run_metadata.py
└── writes: human-readable summary + setup_check.json

scripts/prepare_clip.py
├── reads: direct local-MP4 command arguments
├── calls: src/egocentric_pipeline/clip_request.py
└── calls: src/egocentric_pipeline/video_preparation.py
    └── writes/returns: rgb.mp4 + clip_metadata.json + PreparedClip

scripts/run_hawor_pipeline.py
├── new-source branch
│   ├── reads: direct local-MP4 command arguments
│   └── calls: src/egocentric_pipeline/clip_request.py
├── existing-prepared branch
│   └── calls: video_preparation.load_prepared_clip(clip_metadata.json)
└── calls: src/egocentric_pipeline/pipeline.py
    └── follows: the reusable pipeline branch shown above

tests/test_clip_preparation.py
├── calls: src/egocentric_pipeline/clip_request.py
└── calls: src/egocentric_pipeline/video_preparation.py

tests/test_world_export.py
└── calls: src/egocentric_pipeline/world_export.py

tests/test_run_metadata.py
└── calls: src/egocentric_pipeline/run_metadata.py

tests/test_benchmark.py
└── calls: src/egocentric_pipeline/benchmark.py
```

The reusable path is `local MP4 request → ClipRequest → preparation → PreparedClip/ClipMetadata → HaWoR runner → world export → visualization → run metadata`. The Milestone 1 entry point adds only single-clip orchestration and automatic per-run benchmark reporting: each invocation constructs one request, calls the reusable pipeline once, and generates benchmark files for only that finalized run. `clip_metadata.json` is the durable prepared-clip boundary; within a fresh process the corresponding typed object is passed directly, while resumed processing loads the JSON into the same type before any downstream call.

## 8. Metrics and Failure Review

Measure for every attempt:

- setup/preflight result;
- source timing mode, median source frame interval, maximum source-frame gap, source/prepared duration difference, unique source frames selected, dropped-frame count, repeated-source-frame count/fraction, and median/maximum timestamp-selection error;
- HaWoR focal value/provenance, whether the 600 px approximate fallback was used, and confirmation that lens distortion and camera calibration were not handled;
- stage and total wall-clock time;
- effective frames per second;
- peak process RAM and GPU memory;
- direct-detection, motion-infill, and invalid-frame counts per hand;
- longest consecutive missing/infilled span;
- completion status for preparation, detection/tracking, hand estimation, SLAM/metric scale, infilling, export, and visualization; and
- output contract violations.

Manually review beginning, middle, end, every transition into/out of infilling, and every suspicious jump. Use these labels: missed/false hand detection, left/right identity error, implausible hand depth or scale, temporal jitter, infiller discontinuity, SLAM drift/failure, world-trajectory jump, mesh/image misalignment, rendering failure, and other. A report generated before review records `manual_review.status: pending`; a run is not accepted as Milestone 1 evidence until the required review is complete and its labels/notes are associated with that run.

Each report describes one attempt and records its completion status; it does not calculate a multi-run success rate. Any later summary across the small collection of Milestone 1 runs is descriptive only and is not generated implicitly by `benchmark.py`.

Repository-support validation is tracked separately from clip benchmarks. CI records successful creation of `environment/cpu-tests.yml`, source-tree import verification, and the pass/fail result for every collected CPU-safe synthetic test. The Milestone 1 handoff records a manual README review against the final verified setup, test, command, and output paths. Neither signal is a proxy for the local GPU, licensed-asset, real-data, or visual-review gates.

## 9. Implementation Sequence

1. At the first Milestone 1 implementation change, add the root README's About section and link to the roadmap, current status, active plan, and detailed environment guidance. Retain the verified HaWoR installation material, but do not add commands or outputs that do not yet exist.
2. Create only the environment documentation/specification, submodule declaration, ignore rules, and setup checker. Update the README in the same change if these user-facing setup instructions change.
3. Request Ego4D access early and keep the delivered AWS credentials outside the repository. This acquisition task proceeds independently and does not add the `ego4d` downloader to the HaWoR runtime environment.
4. Establish WSL2/native Linux, Python 3.10, CUDA compiler, PyTorch, system packages, and HaWoR dependencies.
5. Verify all weights and user-supplied MANO files; run the setup checker until required checks pass.
6. Run the untouched bundled HaWoR example and verify inference plus visualization. Decide whether local 8 GB execution is viable.
7. Before adding the first project-owned module or test, add its verified direct and test dependencies to `environment/hawor.yml`, document the repository-root `PYTHONPATH=src` command contract, and verify that the active Python 3.10 environment imports `egocentric_pipeline` from this checkout without installing it as a distribution.
8. Implement the local-MP4 `ClipRequest`, success-or-failure run records, timestamp-driven MP4 preparation, prepared-clip loading, the HaWoR adapter, unchanged world export, visualization, and single-run benchmark reporting with synthetic tests. Do not add dataset adapters, archive/frame-sequence readers, calibration handling, or spatial correction. When the first CPU-safe test is added, create `environment/cpu-tests.yml` and `.github/workflows/ci.yml`; expand the minimal Conda environment and pytest run naturally as the remaining planned tests land. Every user-facing command or prerequisite change includes the matching README update.
9. Require the CPU-test Conda CI job to pass environment creation, source-tree import verification, and all CPU-safe synthetic tests. Keep GPU inference, external assets, and real data in the explicit local gates below.
10. Invoke `run_milestone1_baseline.py` once for the bundled example to verify that one request produces one pipeline attempt and its own benchmark/failure report.
11. After Ego4D access is available, download only one suitable MP4 by video or clip UID and select a short purposeful-manipulation interval with a hand visible through most of the action, sufficient static scene texture for SLAM, and no dominant motion blur. Construct its `ClipRequest` from the immutable local path, UID, selected interval, and license reference.
12. Invoke `run_milestone1_baseline.py` separately for the Ego4D segment without an Ego4D condition inside preparation, the HaWoR runner, exporter, visualizer, or benchmark module. Validate its export and report without rerunning the bundled example automatically.
13. Repeat the required single-clip invocations from a clean output directory, confirm that every run has a unique manifest and benchmark/failure report, recheck the README against the final implemented setup/commands/outputs, record exact verification evidence, and update `knowledge/agent/PROJECT_STATUS.md`.

## 10. Acceptance Criteria

- The root README gained an About section at implementation start, accurately describes the project purpose and unchanged-HaWoR Milestone 1 boundary, preserves or links to the verified setup guidance, and contains only commands and outputs verified against the final implementation. The final documentation review is recorded in the Milestone 1 handoff.
- `environment/hawor.yml` is the sole reviewed full-runtime dependency specification, includes only verified HaWoR and project direct/test dependencies, and recreates the validated Python 3.10 environment. No `pyproject.toml`, `setup.py`, uv configuration, or installed project distribution exists. Environment recreation, `python -m pip check`, and `PYTHONPATH=src python -c "import egocentric_pipeline"` resolving to this checkout provide the evidence.
- `environment/cpu-tests.yml` and `.github/workflows/ci.yml` run on pull requests and default-branch pushes with a minimal Python 3.10 Conda environment, verify the checkout import with `PYTHONPATH=src`, and pass every planned CPU-safe synthetic test. The environment/workflow definitions and a successful run URL/status are the evidence; CI does not fetch or execute HaWoR, CUDA/GPU resources, weights, MANO files, or Ego4D.
- The setup checker passes on the execution machine and records exact software, CUDA, GPU, upstream revision, weights, and MANO presence.
- The unmodified bundled HaWoR example completes inference and produces a viewable visualization.
- One selected Ego4D MP4 segment completes through a separate invocation of `run_milestone1_baseline.py`; it calls the reusable pipeline exactly once and does not rerun the bundled example.
- A direct local video can be prepared and run without a per-clip JSON/config file; the normalized request is instead recorded in `clip_metadata.json`.
- Milestone 1 accepts only directly decodable local MP4 sources. No HOT3D/TAR/VRS/frame-sequence adapter, camera-calibration reader, fisheye correction, rectification, crop, pad, resize, or rotation path exists, and `projectaria_tools` and `hand_tracking_toolkit` are absent from the environment specifications.
- No dataset-specific condition exists inside reusable preparation, the HaWoR runner, world exporter, or visualizer.
- Every run passes an explicit focal length to HaWoR with recorded provenance. Omitted user input resolves to HaWoR's 600 px fallback and is labeled approximate; no metadata claims calibrated intrinsics or corrected lens distortion.
- `video_preparation.py` writes JSON before returning a `PreparedClip`; the in-memory `ClipMetadata` and a reload of that JSON are equivalent and identify the same hashed prepared video.
- `hawor_runner.py` accepts a validated `PreparedClip` and does not implement a competing parser or source-metadata resolver.
- `clip_metadata.json` records the immutable source identity/hash, exact selected interval, every temporal/color/audio/encoding step, explicit absence of spatial correction, focal value/provenance, uncorrected-distortion limitation, and per-frame source mapping. The original source remains independently preserved because dropped frames and lossy encoding are not reversible.
- Prepared video frame counts equal exported trajectory frame counts; indices are contiguous; timestamps are strictly increasing and agree with 30 FPS within tolerance; preparation does not change playback speed; and source/prepared duration error, frame reuse/drop counts, and timestamp-selection errors pass the approved preparation-quality limits.
- The world export numerically preserves HaWoR's root translation, root orientation, hand pose, and shape arrays except for documented hand/frame axis reordering and an explicitly tested dtype conversion if needed.
- Hand order is `[left, right]` throughout and is visually checked.
- Direct detection, motion infill, upstream `hawor_valid`, and stricter `export_valid` are represented separately; detector confidence is present only for direct detections.
- Every valid exported value is finite; failures are reported rather than silently filled by our code.
- No canonical, aligned, rescaled, smoothed, or robot-frame trajectory is written.
- One overlay and one unchanged-world-coordinate trajectory preview exist and are manually reviewed for each accepted clip.
- Every allocated Milestone 1 run directory contains its own `benchmark.json` and approximately one-page `benchmark_report.md`, generated automatically by `run_milestone1_baseline.py` after the run manifest is finalized. They report that run's runtime, peak resources, completion or failure, provenance coverage, review state and visible failures when supplied, environment deviations, unavailable-value reasons, and remaining unverified claims; they do not aggregate or discover other runs.
- Original source, prepared input, native HaWoR artifacts, and stable export remain separate and are never silently overwritten.

## 11. Risks and Mitigations

- **README drift:** commands or prerequisites can change while the prose remains stale; update the README in the same change as each user-visible workflow and perform a final command/link review before acceptance.
- **Conda environment drift:** `environment/hawor.yml` is the full local source of truth while `environment/cpu-tests.yml` intentionally repeats only the subset needed for CPU tests; review their shared versions together, verify both environments, and stop to revise the plan if the CPU subset no longer exercises the project code compatibly.
- **Checkout-only imports:** omitting project packaging means commands can import the `src/` package only when run with the documented source path; require repository-root `PYTHONPATH=src` in every user-facing command and CI step, verify the resolved module path in preflight, and treat execution without that contract as unsupported.
- **CI can create false confidence:** CPU-only synthetic checks cannot verify CUDA, HaWoR, model assets, real Ego4D input, or visual quality; name the job and README coverage accurately, keep excluded checks explicit, and require the separate local evidence in this section's acceptance criteria.
- **8 GB VRAM may be insufficient:** test the bundled example before building the surrounding pipeline; move to a >=16 GB Linux GPU if needed.
- **Native Windows uncertainty:** support WSL2/native Linux only for this baseline and avoid spending the milestone on a Windows port.
- **Old PyTorch/CUDA dependency stack:** validate one explicit compatibility set and freeze it in `environment/hawor.yml`.
- **Compiled extension failures:** require `nvcc`, build tools, initialized Eigen/`lietorch` submodules, and import checks in preflight.
- **Headless rendering failures:** validate rendering during the bundled example, not at the end of the milestone.
- **Approximate focal length:** ordinary MP4s may not provide trustworthy calibration, while HaWoR otherwise silently falls back to 600 px; pass that fallback explicitly when the user supplies no focal value, label it approximate, expose it in the report, and make no calibrated-accuracy claim.
- **Uncorrected lens distortion:** an MP4 may contain lens distortion that biases HaWoR's reconstruction; record that no correction was performed, inspect the overlay as baseline evidence, and defer calibration/rectification to a later approved milestone rather than expanding Milestone 1.
- **Low or irregular source frame rate:** timestamp-based conversion preserves duration but repeated frames add no motion information; measure repeat fraction, maximum source gap, and timing error, then reject at the preparation-quality gate when the approved limits are exceeded.
- **Prepared video is not an archival copy:** frame dropping and lossy encoding cannot be inverted; preserve the immutable original and its hash, and treat the temporal history/frame map as reproducibility evidence rather than a substitute for the source.
- **Ego4D access delay or expiry:** official guidance estimates about 48 hours for approval and the issued AWS credentials expire after 14 days; request access early, download only the selected UID, keep credentials outside the repository, and renew them if necessary.
- **Licensed assets:** keep MANO, Ego4D, and weights untracked and store no credentials.
- **HaWoR final validity loses origin information:** reconstruct direct-detection versus infilled provenance from preserved tracks without changing predictions.
- **Hand identity errors propagate:** keep fixed `[left, right]` order and inspect the overlay around gaps and crossings.
- **World frames differ between clips:** make no cross-clip geometric comparison in Milestone 1.
- **Two clips do not establish accuracy:** report reproducibility, structural correctness, cost, and observed failures only.

## 12. Remaining Decisions

1. Choose the exact Ego4D MP4 and interval. The recommended default is one short purposeful manipulation with a hand visible through most of the action, enough camera motion and static scene texture to exercise SLAM, and no dominant motion blur. Exact identity is required before the Ego4D run but does not block plan approval or implementation against synthetic inputs and the bundled example.

## 13. References

- Project roadmap and approved Milestone 1 scope correction: `knowledge/raw/Project-Milestones-and-Timeline.md`
- Operational state and active-plan record: `knowledge/agent/PROJECT_STATUS.md`
- Project HaWoR technical notes: `knowledge/raw/Sources/HaWoR-Review.md`
- HaWoR project and paper: <https://hawor-project.github.io/> and <https://arxiv.org/abs/2501.02973>
- Official HaWoR implementation and installation, pinned at commit `66c7d4108d58a716deccd192cb7645170cdc7bd7`: <https://github.com/ThunderVVV/HaWoR>
- HaWoR CUDA extension build: <https://github.com/ThunderVVV/HaWoR/blob/main/thirdparty/DROID-SLAM/setup.py>
- Current HaWoR focal-length issue: <https://github.com/ThunderVVV/HaWoR/issues/34>
- Ego4D access, approximately 48-hour credential estimate, 14-day credential expiry, and narrow downloader: <https://ego4d-data.org/docs/start-here/> and <https://ego4d-data.org/docs/CLI/> (verified 2026-09-13)
- FFmpeg timestamp-based FPS filter: <https://ffmpeg.org/ffmpeg-filters.html#fps>
- GitHub Actions guide for building and testing Python (accessed 2026-09-11): <https://docs.github.com/en/actions/tutorials/build-and-test-code/python>
