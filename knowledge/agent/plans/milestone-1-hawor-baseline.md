# Milestone 1 Plan: Validate the HaWoR Baseline

Status: Draft revision 6 — repository documentation, packaging, and CI targets added without changing the core pipeline; awaiting user review and approval

## 1. Goals

Build a small, reusable pipeline around the unchanged HaWoR inference code and prove that it can:

1. run the bundled HaWoR example;
2. process one short HOT3D clip;
3. only after the HOT3D gate passes, process one short Ego4D clip;
4. preserve HaWoR's native world-frame result;
5. export that result with frame timestamps and validity/provenance metadata;
6. generate a reusable visualization; and
7. produce a one-page benchmark and failure report for every Milestone 1 run;
8. maintain the root README as the user-facing project entry point, beginning with an About section when implementation starts; and
9. establish only the packaging metadata and CPU-safe continuous integration needed to install and validate the project-owned code.

Milestone 1 is a baseline and integration milestone. HaWoR remains the owner of hand reconstruction, camera tracking, metric scale estimation, motion infilling, and conversion into its world frame. Our code prepares inputs, invokes HaWoR, records what happened, validates the returned artifacts, and packages the existing world-frame output without changing its coordinate frame.

The README, packaging, and CI goals support development and maintainability; they do not add pipeline stages or alter any pipeline contract, HaWoR behavior, trajectory value, dataset choice, or benchmark result.

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
- At least 40 GB free storage for the environment, source checkout, weights, build products, a narrowly downloaded HOT3D source, and run artifacts. Confirm actual free space before installation.

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

`environment/hawor.yml` will record the validated HaWoR/CUDA base environment so a later machine can recreate it. Once project-owned code exists, its lightweight direct and test dependencies are authoritative in `pyproject.toml` and are installed into that environment with the project; they are not maintained as a second independent list in the environment file.

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

Project-side additions, declared through `pyproject.toml` once project-owned code exists:

- `pytest` for focused automated checks;
- `psutil` for process RAM sampling; and
- no dataframe/storage dependency beyond NumPy and the Python standard library in Milestone 1.

All resolved versions are captured after the successful smoke test. A generated environment snapshot is evidence; `environment/hawor.yml` remains the reviewed recreation specification.

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
- output directories are writable without overwriting prior runs; and
- after project-owned code exists, `pyproject.toml` is present, the installed `egocentric_pipeline` resolves to this checkout, and `python -m pip check` passes in the combined environment.

The setup gate passes only when all required checks pass. Warnings such as low VRAM remain visible in the evidence and report.

### 3.12 Project packaging and CI setup

The project-owned Python package and synthetic tests use Python 3.10, matching the supported HaWoR environment. When the first `src/egocentric_pipeline/` module or test is implemented, create a root `pyproject.toml` rather than relying on ad hoc `PYTHONPATH` changes. It will:

- define the internal, unpublished `egocentric-videos` distribution at initial version `0.1.0` and `src/` package discovery for the `egocentric_pipeline` import package;
- declare the supported Python range as `>=3.10,<3.11`;
- list only direct, project-owned runtime dependencies that the implemented wrapper code actually imports;
- provide a `dev` optional dependency group containing `pytest` and any other approved CPU-test dependency that is demonstrably required; and
- hold the minimal pytest configuration needed for the planned test suite.

The resolved HaWoR/CUDA base environment remains authoritative in `environment/hawor.yml`. The project file must not duplicate HaWoR's full upstream dependency stack, model assets, MANO files, or CUDA installation instructions; HaWoR and its specialized runtime remain an explicitly documented external prerequisite. If implementation shows that a proposed lightweight dependency is already supplied by Python or an existing approved package, omit it rather than adding it for convenience.

Create `.github/workflows/ci.yml` when the first CPU-safe synthetic test is added. On pull requests and pushes to the repository's default branch, it will use Ubuntu and Python 3.10, install FFmpeg plus the project and its `dev` dependencies from `pyproject.toml`, run `python -m pip check`, and run the complete CPU-safe synthetic test suite with `python -m pytest`. CI will not initialize the HaWoR submodule or require CUDA, a GPU, weights, MANO files, HOT3D, Ego4D, or network access beyond fetching the source, declared test dependencies, and the runner's standard packages/actions. Tests requiring those excluded resources remain explicit local validation gates and are not silently skipped as if CI had verified them.

## 4. Input and Output Contracts / Data and Metadata Files

### 4.1 In-memory `ClipRequest`

A runnable clip no longer requires a human-authored `clip_config.json`. The reusable pipeline accepts a typed, in-memory `ClipRequest`. A request describes what the caller wants processed; it does not duplicate facts that must be measured from the source.

`ClipRequest` contains:

- `source` — required tagged source reference:
  - `LocalVideoSource`: immutable local video path plus optional dataset name and dataset-native video ID; or
  - `Hot3DClipSource`: HOT3D root/archive path, native clip ID, device, and selected image stream ID.
- `interval` — optional `[start_s, end_s)` selection in source time; null means the complete source. Dataset-native frame/timestamp selectors are resolved by the relevant adapter before preparation and may not conflict with this interval.
- `clip_id` — optional stable local identifier. When absent, preparation derives one deterministically from source identity/checksum and the resolved interval.
- `task_label` — optional short human-readable action. It is not inferred from pixels.
- `license_reference` — optional while running a private local test, but required before a clip is accepted into a dataset deliverable.
- `camera_override` — optional object containing `focal_length_px`, the source/prepared resolution to which it applies, and provenance. Values must be finite and positive. An override is never silently assumed.
- `intrinsics_policy` — `strict` or `allow_approximate`; defaults to `strict`. Strict preparation may finish with unresolved intrinsics, but HaWoR inference must not start until a compatible focal length is available.

`src/egocentric_pipeline/clip_request.py` normalizes only request syntax and intent: source tags and paths, seconds and half-open interval semantics, optional strings, camera-override units, allowed policy values, and defaults. It does not probe or transform video, infer source FPS, create timestamps, or resolve camera calibration.

`ClipRequest` does not contain a `use_frame_encoder`, `convert_to_mp4`, or similar execution flag. Its `source` field identifies the source and the adapter needed to open it. Opening that reference produces one of two internal source representations:

- `VideoFileSource` — an existing immutable video file with container timing; or
- `FrameSequenceSource` — an ordered, read-only frame sequence with source timestamps, frame/native IDs, and any camera-calibration records.

`video_preparation.py` dispatches on this resolved representation. A `VideoFileSource` follows the video-to-video path; only a `FrameSequenceSource` follows the frame-sequence encoding path. This keeps the request declarative and prevents callers from selecting an encoding path that contradicts the actual source.

Requests are constructed without one file per clip:

- `scripts/prepare_clip.py` and `scripts/run_hawor_pipeline.py` build a `LocalVideoSource` request directly from command-line arguments;
- `src/egocentric_pipeline/hot3d_adapter.py` builds a `Hot3DClipSource` request from the selected HOT3D archive/clip and native metadata; and
- `scripts/run_milestone1_baseline.py` selects exactly one clip input per invocation. It constructs one request for a bundled-example, direct-video/Ego4D, or HOT3D source, or passes one existing prepared-clip metadata path to the pipeline. HOT3D request construction routes through the adapter.

The normalized request is snapshotted inside the generated `clip_metadata.json`. A separate request/config file is optional and is not part of the Milestone 1 architecture.

### 4.2 HOT3D source contract

Milestone 1 uses an Aria HOT3D clip with the RGB stream and its native per-frame camera metadata. The imported HOT3D source remains untracked and immutable under `data/source/hot3d/`. The adapter reads the native clip definition/archive, ordered image frames, timestamps, stream identity, device identity, calibration model and projection parameters, and license/source identifiers.

The HOT3D adapter does not encode or overwrite video. When `video_preparation.py` opens a `Hot3DClipSource`, it uses the adapter's ordered RGB frame handles, timestamps, native frame IDs, calibration, and provenance to construct a read-only `FrameSequenceSource`. Video preparation owns interval selection, timing policy, and any required fisheye-to-pinhole rectification, then calls `frame_sequence_encoding.py` to encode the selected prepared frames directly into the common final `rgb.mp4`. There is no intermediate MP4 or second encoding pass. The original HOT3D images and camera JSON/VRS data remain unchanged.

The supported Milestone 1 source is the smallest official HOT3D representation that supplies the selected RGB frames, timestamps, and camera calibration. Adding a second HOT3D representation, such as direct full-VRS ingestion when the selected clip archive is sufficient, is out of scope.

### 4.3 Prepared clip and metadata

Input preparation writes:

```text
data/prepared/<clip_id>/rgb.mp4
data/prepared/<clip_id>/clip_metadata.json
```

`video_preparation.prepare_clip(request) -> PreparedClip` opens the request source as a `VideoFileSource` or `FrameSequenceSource`, writes both artifacts, and returns a typed in-memory object containing the prepared video path, metadata path, and the same typed `ClipMetadata` value serialized to JSON. JSON is written successfully before `PreparedClip` is returned. `frame_sequence_encoding.py` is invoked only for the frame-sequence representation; its result is folded into the metadata by `video_preparation.py`.

`rgb.mp4` is a derived, constant-rate 30 FPS, HaWoR-ready video. Preparation creates a 30 FPS timestamp grid over the selected source interval and selects source frames by presentation timestamp. It does not change playback speed. Higher-rate sources lose unselected frames; lower-rate sources reuse the nearest source frame when permitted by the preparation-quality policy. Exact rejection thresholds for source gaps and repeated-frame fraction remain a plan decision.

`clip_metadata.json` has a schema version and these owned sections:

- `request`: normalized snapshot of every `ClipRequest` field and the constructor used (`direct_video`, `hot3d_adapter`, or `milestone1_baseline`).
- `source`: request source kind, resolved representation (`video_file` or `frame_sequence`), immutable path/native identifiers, SHA-256 or native artifact hashes, dataset/device/stream identity, license reference, codec/pixel format when applicable, width, height, display rotation, sample/display aspect ratio, time base, duration, nominal/average frame rates, frame count, and whether timing is constant or variable rate.
- `selection`: requested and resolved `[start_s, end_s)` bounds, source frame/timestamp bounds, and any dataset-native selector resolution.
- `source_camera`: imported or embedded camera model, `fx`, `fy`, `cx`, `cy`, distortion/projection model and coefficients, calibration resolution, whether calibration changes with time, and exact provenance; fields are null with `status: unresolved` when unavailable.
- `preparation`: preparation implementation/version, source adapter and frame encoder used or explicitly not used, exact FFmpeg/adapter/encoding commands and relevant library versions, output codec and pixel format, audio disposition, timestamp origin, and an ordered spatial/temporal transform history. Spatial history records orientation correction, rectification, crop, pad, resize, and color/pixel-format conversion with all parameters; temporal history records interval selection and timestamp-based 30 FPS resampling. A step that was not applied is recorded explicitly as such rather than omitted ambiguously.
- `prepared`: prepared path and SHA-256, width, height, constant `30/1` FPS, time base, duration, frame count, and codec/pixel format.
- `prepared_camera`: camera model and intrinsics in prepared-image pixel coordinates, derivation from the source calibration/override/approximation, compatibility with HaWoR's equal-focal centered-principal-point interface, the scalar `hawor_focal_length_px` actually selected, provenance, and quality status (`calibrated`, `derived`, `approximate`, or `unresolved`).
- `frames`: one entry per prepared frame containing prepared frame index/timestamp, selected source frame index/timestamp/native ID, timestamp-selection error, and whether that source frame is reused. Aggregate fields record source frames considered, unique frames selected, dropped frames, repeated-source-frame count/fraction, median/maximum timestamp error, and maximum source-frame gap.
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

- schema version, `run_id`, `clip_id`, source/dataset identity, and Milestone 1 run role (`setup_smoke`, `paper_dataset`, `ego4d`, or `other_test`);
- overall and per-stage completion status, failure stage, and concise error summary;
- source/preparation timing-quality and camera-provenance metrics when available;
- wall-clock time, effective FPS, peak RAM, and peak GPU memory when available;
- direct-detection, motion-infill, invalid-frame, longest-gap, and provenance-coverage metrics when export exists;
- structural contract violations and generated artifact paths/hashes;
- manual-review status (`pending`, `complete`, or `not_possible`) and supplied failure labels/notes; and
- environment deviations, limitations, and claims that remain unverified.

Unavailable values are `null` with a reason; failed runs remain reportable. `benchmark_report.md` is a human-readable, approximately one-page rendering of the same single-run evidence and must not imply cross-run aggregation or statistical generalization. Both benchmark files belong only to their containing `run_id` and are never shared or overwritten by a later invocation.

`run_milestone1_baseline.py` always calls `benchmark.py` after `pipeline.py` has finalized a run manifest, including after a pipeline-stage failure. Users do not invoke `benchmark.py` separately. Invalid command-line/request syntax that is rejected before run allocation does not create a benchmark report. Milestone completion is demonstrated by the collection of accepted per-run evidence, including at least one qualifying HOT3D run and one later qualifying Ego4D run; there is no Milestone 1 multi-run controller or automatically discovered aggregate report.

## 5. Planned Repo Structure

Only files reached by the implementation sequence are created. The tree below is the complete intended Milestone 1 structure, including generated/untracked paths for clarity.

```text
Egocentric/
├── AGENTS.md
├── README.md                           # existing; maintained from implementation start
├── pyproject.toml                      # new; project packaging + CPU test configuration
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
│   └── hawor.yml
├── external/
│   └── HaWoR/                         # pinned Git submodule; upstream code
├── src/
│   └── egocentric_pipeline/
│       ├── __init__.py
│       ├── clip_request.py
│       ├── hot3d_adapter.py
│       ├── frame_sequence_encoding.py
│       ├── camera_intrinsics.py
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
│   ├── test_hot3d_adapter.py
│   ├── test_frame_sequence_encoding.py
│   ├── test_world_export.py
│   ├── test_run_metadata.py
│   └── test_benchmark.py
├── data/                               # untracked local licensed/input data
│   ├── source/
│   │   ├── hot3d/<clip_id>/...          # immutable frames + camera metadata
│   │   └── ego4d/<video_uid>/...       # deferred
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

**Description:** Human instructions for WSL/Linux setup, Conda creation, CUDA/PyTorch compatibility checks, model/MANO placement, installation order, headless rendering, and common recovery steps. It links to `hawor.yml` and `check_hawor_setup.py`; it does not duplicate the package list already expressed in the environment file.

**Input:** None.

**Output:** Human-readable setup and recovery instructions.

**Calls:** N/A — documentation file.

**Called by:** Developers setting up any milestone that runs HaWoR.

**Metadata written:** None.

#### `environment/hawor.yml` — reusable environment specification

**Description:** Reviewed Conda/pip dependency declaration for the successfully validated HaWoR/CUDA base runtime. Project-owned lightweight runtime and test dependencies are declared once in `pyproject.toml` and installed on top of this environment rather than copied into a second list here.

**Input:** None.

**Output:** The reviewed environment specification.

**Calls:** N/A — declarative file.

**Called by:** Environment setup; checked by `scripts/check_hawor_setup.py`; combined with the project install defined by `pyproject.toml`; version recorded by `run_metadata.py`.

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

Milestone 1 has no persistent per-clip configuration files. Clip intent is supplied through command-line arguments or a dataset adapter and normalized into an in-memory `ClipRequest`. The request snapshot, resolved defaults, source identity, and all measured/generated facts are persisted in `clip_metadata.json` and the run manifest.

#### `README.md` — existing reusable documentation, modified throughout Milestone 1

**Description:** The user-facing entry point for the repository. At the first implementation change, add an About section that explains the project purpose, the RGB-to-world-frame-hand-trajectory direction, and Milestone 1's unchanged-HaWoR baseline boundary. Preserve the already verified HaWoR installation guidance, then add setup, development install, test, and user-facing command guidance only as those workflows are implemented and verified. Keep it current in the same change whenever a public command, prerequisite, supported workflow, or output location changes. Link to the roadmap, current status, active plan, and detailed environment documentation instead of duplicating progress records or long setup material.

**Input:** Verified repository purpose, supported workflows, commands, setup requirements, and authoritative links from `knowledge/` and `environment/`.

**Output:** A concise root README with an About section and accurate setup, development, test, and usage guidance for the functionality that exists at that point in Milestone 1.

**Calls:** N/A — documentation file.

**Called by:** Developers and users entering the repository.

**Metadata written:** None.

#### `pyproject.toml` — new reusable project packaging and test configuration

**Description:** Created when the first project-owned source module or test is added. It uses PEP 621 metadata and a standard `src/`-layout build configuration to make `egocentric_pipeline` installable without path manipulation, records the supported Python range, declares only direct dependencies actually required by project-owned code, provides the minimal `dev` dependency set, and configures pytest. It does not duplicate the complete HaWoR/CUDA environment, package external code, or define publishing/release automation.

**Input:** The implemented `src/egocentric_pipeline/` package, its verified direct imports, and the planned CPU-safe test requirements.

**Output:** Installable project metadata, `src/` package discovery, runtime and `dev` dependency declarations, and pytest configuration.

**Calls:** N/A — declarative file.

**Called by:** Developers performing a local editable install and `.github/workflows/ci.yml`.

**Metadata written:** None.

#### `.github/workflows/ci.yml` — new reusable CPU-safe validation workflow

**Description:** Runs the project-owned synthetic validation suite on Ubuntu with Python 3.10 for pull requests and pushes to the default branch. It installs FFmpeg and the project with its `dev` dependencies from `pyproject.toml`, checks the installed dependency set, and runs pytest. It does not initialize or execute HaWoR, use a GPU, fetch licensed/model/data assets, or represent local end-to-end validation as passing CI coverage.

**Input:** The checked-out project-owned source and tests, `pyproject.toml`, the GitHub-hosted Ubuntu/Python 3.10 environment, and FFmpeg from the runner's package manager.

**Output:** GitHub Actions job status and logs for installation, `python -m pip check`, and the complete CPU-safe synthetic test suite.

**Calls:** Official GitHub checkout/setup-Python actions pinned to reviewed full commit SHAs, the runner package manager for FFmpeg, Python/pip using `pyproject.toml`, and `python -m pytest` over the six planned test files in Section 6.5.

**Called by:** Pull-request and default-branch push events in GitHub Actions; developers may rerun an existing workflow run through GitHub.

**Metadata written:** None in the repository; GitHub retains workflow status and logs according to repository settings.

### 6.3 `src/` modules

#### `src/egocentric_pipeline/clip_request.py` — reusable

**Description:** Defines `ClipRequest`, its tagged source-reference types, interval and camera-override types, allowed policies, validation, and constructors from direct command arguments. It normalizes request syntax and intent only. It does not read video metadata, decode frames, estimate calibration, choose an encoding implementation, or write a per-clip configuration file.

**Input:** Source paths or dataset references plus optional interval, clip ID, task label, license reference, camera override, and intrinsics policy supplied by callers.

**Output:** A normalized in-memory `ClipRequest`.

**Calls:** None.

**Called by:** `src/egocentric_pipeline/hot3d_adapter.py`, `src/egocentric_pipeline/pipeline.py`, `scripts/prepare_clip.py`, `scripts/run_hawor_pipeline.py`, `scripts/run_milestone1_baseline.py`, `tests/test_clip_preparation.py`, and `tests/test_hot3d_adapter.py`.

**Metadata written:** None.

#### `src/egocentric_pipeline/hot3d_adapter.py` — reusable dataset adapter

**Description:** Owns the HOT3D-native boundary. It locates and validates the selected Aria HOT3D clip/archive and RGB stream, reads native ordered frames, timestamps, clip/device/stream identity, camera projection model and parameters, and license/source references. It constructs a normalized `Hot3DClipSource` `ClipRequest` and resolves that reference to a read-only `FrameSequenceSource` for video preparation. It does not modify native files, rectify images, encode MP4, or write project metadata.

**Input:** HOT3D dataset root or clip archive, native clip ID, selected RGB stream ID, and optional task label or interval selection.

**Output:** A normalized `ClipRequest` and, when opened by video preparation, ordered native RGB frame handles, timestamps, native IDs, calibration records, and source provenance from which `video_preparation.py` constructs a `FrameSequenceSource`.

**Calls:** `src/egocentric_pipeline/clip_request.py` and the supported official HOT3D reader/calibration utilities.

**Called by:** `src/egocentric_pipeline/video_preparation.py`, `scripts/prepare_clip.py`, `scripts/run_hawor_pipeline.py`, `scripts/run_milestone1_baseline.py`, and `tests/test_hot3d_adapter.py`.

**Metadata written:** None; it returns native values and provenance to `video_preparation.py`, which owns `clip_metadata.json`.

#### `src/egocentric_pipeline/frame_sequence_encoding.py` — reusable

**Description:** Encodes an ordered prepared-frame stream into the final constant-rate MP4. It is dataset-agnostic: it has no HOT3D paths, IDs, calibration logic, interval-selection policy, or request parsing. It receives frames after `video_preparation.py` has resolved source timing, selected the 30 FPS frame plan, and coordinated required spatial transforms. It performs one encoding pass, does not create an intermediate video, and returns a structured record of exactly what it encoded. It does not write `clip_metadata.json`.

**Input:** An ordered prepared-frame iterator and target timestamps supplied by `video_preparation.py`, the final `rgb.mp4` path, and explicit codec, pixel-format, frame-rate, and color settings.

**Output:** The final `data/prepared/<clip_id>/rgb.mp4` and a typed encoding result containing the command/settings, input and output frame counts, warnings, and relevant encoder version.

**Calls:** FFmpeg or its approved process interface.

**Called by:** `src/egocentric_pipeline/video_preparation.py` and `tests/test_frame_sequence_encoding.py`.

**Metadata written:** None directly; it returns its structured encoding result to `video_preparation.py`, which records it under `preparation` and `prepared` in `clip_metadata.json`.

#### `src/egocentric_pipeline/camera_intrinsics.py` — reusable

**Description:** Resolves camera information from an explicit override, dataset-native calibration, supported embedded metadata, or the explicitly permitted approximate fallback. It applies the recorded spatial preparation transform to produce intrinsics in prepared-image coordinates, checks whether they can be represented by HaWoR's single equal-focal, centered-principal-point input, and returns the scalar focal value and provenance. It does not modify video or invoke HaWoR. A future focal estimator can be added behind this boundary without changing `ClipRequest`, `PreparedClip`, or `hawor_runner.py`.

**Input:** Normalized `ClipRequest`, observed source geometry, optional source calibration, ordered spatial transform description, and prepared geometry.

**Output:** Typed source/prepared camera metadata, HaWoR compatibility status, and `hawor_focal_length_px` or an unresolved result.

**Calls:** None in the baseline; later estimator implementations may be added only through an approved plan revision.

**Called by:** `src/egocentric_pipeline/video_preparation.py` and `tests/test_clip_preparation.py`.

**Metadata written:** None directly; `video_preparation.py` serializes the returned values under `source_camera` and `prepared_camera` in `clip_metadata.json`.

#### `src/egocentric_pipeline/video_preparation.py` — reusable

**Description:** Owns the boundary between a normalized `ClipRequest` and a HaWoR-ready `PreparedClip`, including the small internal `VideoFileSource` and `FrameSequenceSource` resolved-source contracts. It opens the tagged source reference as one of those representations and dispatches on the representation rather than on a dataset name or request flag. The video-file branch probes and converts the immutable source with FFmpeg/ffprobe. The frame-sequence branch reads frames/calibration through its source adapter and delegates the single final MP4 encode to `frame_sequence_encoding.py`. Across both branches, this module resolves the requested interval, applies and records required orientation/rectification/spatial changes, builds a source-time 30 FPS grid without changing playback speed, selects frames by presentation timestamp, resolves prepared-camera metadata, calculates hashes, and refuses ambiguous or destructive overwrites. It remains the sole owner of the typed `ClipMetadata` and `PreparedClip` contracts, `clip_metadata.json`, and the loader for an existing prepared directory.

**Input:** A normalized `ClipRequest`, the immutable source it resolves to as a `VideoFileSource` or `FrameSequenceSource`, and the supported preparation-quality policy.

**Output:** `data/prepared/<clip_id>/rgb.mp4`, `data/prepared/<clip_id>/clip_metadata.json`, and an in-memory `PreparedClip` containing the same typed `ClipMetadata` value that was serialized.

**Calls:** FFmpeg/ffprobe for `VideoFileSource`; `src/egocentric_pipeline/hot3d_adapter.py` to resolve HOT3D references; `src/egocentric_pipeline/frame_sequence_encoding.py` only for `FrameSequenceSource`; `src/egocentric_pipeline/camera_intrinsics.py`; and checksum/serialization helpers from `src/egocentric_pipeline/run_metadata.py`.

**Called by:** `scripts/prepare_clip.py`, `src/egocentric_pipeline/pipeline.py`, and `tests/test_clip_preparation.py`.

**Metadata written:** Owns all of `clip_metadata.json` as specified in Section 4.3: request snapshot; resolved source representation; source identity, hashes, media/timing facts, and calibration; interval resolution; adapter/encoder selection; every applied or explicitly skipped temporal, spatial, rectification, color, audio, and encoding step with parameters and versions; prepared artifact facts and hashes; source-to-prepared frame mapping and resampling metrics; prepared intrinsics and HaWoR focal value/provenance; and creation time. Shared hashing, timestamp, and JSON serialization use `run_metadata.py`.

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

**Description:** The central programmatic interface, conceptually `run_clip(request: ClipRequest) -> RunResult`. It performs no model math. It validates request syntax, allocates a non-overwriting run record for the single clip attempt, prepares a new clip or loads and verifies an existing `PreparedClip`, enforces the requested intrinsics policy before inference, calls HaWoR, exports the unchanged world result, renders review artifacts, runs structural validation, and finalizes the run manifest for success or failure. It is reusable later for direct local videos, dataset-adapter requests, or larger dataset jobs.

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

**Input:** The environment, project-install state, and external-checkout state listed in Section 3.11, including `pyproject.toml` after project-owned code exists.

**Output:** A human-readable summary and `setup_check.json` evidence.

**Calls:** Environment and installed-project inspection, `python -m pip check` after project-owned code exists, shared helpers in `src/egocentric_pipeline/run_metadata.py`, and checks against `external/HaWoR/`.

**Called by:** Developers setting up a machine.

**Metadata written:** `setup_check.json`, recording operating system, Python and package versions, project-install origin and dependency consistency when applicable, tool availability, PyTorch CUDA/GPU identity, `nvcc`, HaWoR and nested-submodule revisions, required weight/MANO presence and hashes, example-video decodability, output-directory writability, and visible warnings, using `run_metadata.py`.

#### `scripts/prepare_clip.py` — reusable

**Description:** Thin command-line entry point for constructing a `ClipRequest` and running `video_preparation.py` independently. A local video path works without a sidecar file; HOT3D-specific arguments route request construction through the adapter. It is useful when selecting or inspecting a clip before paying the cost of inference.

**Input:** A local video path or HOT3D root/archive plus clip/stream selection, and optional interval, clip ID, task label, license reference, camera override, and intrinsics policy arguments.

**Output:** The prepared `rgb.mp4` and `clip_metadata.json` produced by `video_preparation.py`.

**Calls:** `src/egocentric_pipeline/clip_request.py`, optionally `src/egocentric_pipeline/hot3d_adapter.py`, and `src/egocentric_pipeline/video_preparation.py`.

**Called by:** Users preparing a clip independently.

**Metadata written:** None directly; `video_preparation.py` writes `clip_metadata.json`.

#### `scripts/run_hawor_pipeline.py` — reusable

**Description:** Thin general-purpose command-line front end to `pipeline.run_clip`. It constructs a `ClipRequest` from a direct local video or supported dataset arguments, or accepts an existing prepared `clip_metadata.json`, and prints the run directory and final status. No per-clip configuration file is required. This is the command expected to survive into later milestones.

**Input:** Direct-video or HOT3D request arguments, or an existing prepared `clip_metadata.json`, plus the configured HaWoR runtime.

**Output:** The run directory and final status printed for the user, plus the run artifacts produced by `pipeline.py`.

**Calls:** `src/egocentric_pipeline/clip_request.py`, optionally `src/egocentric_pipeline/hot3d_adapter.py`, and `src/egocentric_pipeline/pipeline.py`.

**Called by:** Users running an arbitrary clip.

**Metadata written:** None directly; `pipeline.py` writes and finalizes the run metadata.

#### `scripts/run_milestone1_baseline.py` — Milestone 1-specific

**Description:** Runs exactly one Milestone 1 clip attempt per invocation. It constructs one bundled-example, direct-video/Ego4D, or HOT3D request from runtime arguments, or selects one existing prepared clip, calls the reusable pipeline once, and then calls `benchmark.py` for that same run. It contains no reusable video, HaWoR, export, visualization, or multi-run aggregation logic, and it never requires the other milestone clips to be supplied or run in the same invocation.

**Input:** Exactly one source selection: the bundled HaWoR example; a direct local video with optional dataset name/native ID; a HOT3D root/archive plus selected clip/stream ID; or an existing prepared `clip_metadata.json`. Also accepts the selected interval, optional approved camera override or policy, one Milestone 1 run role (`setup_smoke`, `paper_dataset`, `ego4d`, or `other_test`), and optional review state. The bundled-example path is resolved from the pinned upstream checkout.

**Output:** One unique Milestone 1 run directory containing the available pipeline artifacts, finalized `run_manifest.json`, and that run's `benchmark.json` and `benchmark_report.md`; prints the run directory and final status.

**Calls:** `src/egocentric_pipeline/clip_request.py`, optionally `src/egocentric_pipeline/hot3d_adapter.py`, `src/egocentric_pipeline/pipeline.py` exactly once, and then `src/egocentric_pipeline/benchmark.py` for the finalized run.

**Called by:** Users running one Milestone 1 clip attempt. The user invokes it separately for the bundled smoke test and for each HOT3D, Ego4D, or additional test clip as needed.

**Metadata written:** None directly; `pipeline.py` owns `run_manifest.json`, and `benchmark.py` owns the same run's `benchmark.json` and `benchmark_report.md`.

### 6.5 Tests

#### `tests/test_clip_preparation.py` — reusable contracts

**Description:** Uses tiny synthetic constant- and variable-rate videos plus a synthetic frame-sequence source to test `ClipRequest` defaults and validation, source-representation dispatch, the invariant that only a frame sequence invokes `frame_sequence_encoding.py`, half-open interval boundaries, presentation-timestamp-driven 30 FPS conversion without speed change, frame dropping/reuse and exact source mapping, timing-quality metrics, complete transform-history recording, camera propagation, checksum recording, prepared-clip reload, in-memory/JSON equivalence, and overwrite refusal without downloading datasets.

**Input:** Tiny synthetic videos, a synthetic frame sequence, frame timestamps, calibration/override fixtures, and `ClipRequest` values.

**Output:** Automated pass/fail results for the clip-request, camera, preparation, metadata, and reload contracts.

**Calls:** `src/egocentric_pipeline/clip_request.py`, `src/egocentric_pipeline/camera_intrinsics.py`, and `src/egocentric_pipeline/video_preparation.py`.

**Called by:** Developers through the test runner and `.github/workflows/ci.yml`.

**Metadata written:** None.

#### `tests/test_hot3d_adapter.py` — reusable dataset-adapter contracts

**Description:** Uses a tiny synthetic HOT3D-like frame bundle to test native frame/timestamp ordering, RGB-stream selection, calibration/projection parsing, source identity and license provenance, request construction, missing/mismatched metadata errors, and the invariant that the adapter never modifies or encodes native data.

**Input:** Synthetic HOT3D clip-definition, frame, timestamp, and camera-metadata fixtures.

**Output:** Automated pass/fail results for the HOT3D adapter boundary.

**Calls:** `src/egocentric_pipeline/clip_request.py` and `src/egocentric_pipeline/hot3d_adapter.py`.

**Called by:** Developers through the test runner and `.github/workflows/ci.yml`.

**Metadata written:** None.

#### `tests/test_frame_sequence_encoding.py` — reusable encoding contracts

**Description:** Uses a tiny sequence of distinguishable synthetic frames to verify ordered single-pass encoding into the final MP4, constant `30/1` output timing, expected frame count and pixel format, structured encoding-result fields, failure cleanup, and the absence of HOT3D-specific assumptions or an intermediate MP4.

**Input:** Synthetic prepared frames, target timestamps, explicit encoding settings, and a temporary final output path.

**Output:** Automated pass/fail results for the frame-sequence encoder boundary.

**Calls:** `src/egocentric_pipeline/frame_sequence_encoding.py`.

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
│   │   └── constructs: bundled-example or direct local/Ego4D ClipRequest
│   ├── src/egocentric_pipeline/hot3d_adapter.py [HOT3D only]
│   │   ├── reads: selected immutable HOT3D clip/archive and native metadata
│   │   └── constructs: HOT3D ClipRequest with RGB stream/calibration identity
│   └── existing-prepared branch
│       └── passes: existing clip_metadata.json
├── calls exactly once: src/egocentric_pipeline/pipeline.py :: run_clip(request) -> RunResult
│   ├── src/egocentric_pipeline/clip_request.py
│   │   └── validates: normalized request, interval, override, and policies
│   ├── creates: non-overwriting outputs/hawor/<run_id>/ run record
│   ├── src/egocentric_pipeline/video_preparation.py
│   │   ├── reads: normalized ClipRequest + immutable source
│   │   ├── opens source reference as one internal representation
│   │   │   ├── local video → VideoFileSource
│   │   │   └── HOT3D reference → hot3d_adapter.py → FrameSequenceSource
│   │   ├── creates: 30 FPS source-time grid; selects by PTS without speed change
│   │   ├── coordinates/records: orientation, rectification, crop/pad/resize,
│   │   │                        color/pixel conversion, frame drop/reuse
│   │   ├── calls: camera_intrinsics.py
│   │   │   └── returns: source/prepared camera metadata + HaWoR focal/status
│   │   ├── dispatches by resolved representation, never a request flag
│   │   │   ├── VideoFileSource
│   │   │   │   └── calls: FFmpeg/ffprobe for final video-to-video conversion
│   │   │   └── FrameSequenceSource
│   │   │       └── calls: frame_sequence_encoding.py for one final MP4 encode
│   │   └── writes: data/prepared/<clip_id>/rgb.mp4
│   │               data/prepared/<clip_id>/clip_metadata.json
│   │       returns: PreparedClip(video path, metadata path, typed ClipMetadata)
│   ├── enforces: intrinsics policy and preparation-quality gate
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

Repository documentation, packaging, and CI remain outside the runtime pipeline. Their validation flow is:

```text
.github/workflows/ci.yml [pull request or default-branch push]
├── calls: official checkout and Python-setup actions pinned to reviewed SHAs
├── selects: Ubuntu runner + Python 3.10
├── installs: FFmpeg
├── reads: pyproject.toml
├── calls: python -m pip install -e ".[dev]"
├── calls: python -m pip check
└── calls: python -m pytest
    ├── tests/test_clip_preparation.py
    ├── tests/test_hot3d_adapter.py
    ├── tests/test_frame_sequence_encoding.py
    ├── tests/test_world_export.py
    ├── tests/test_run_metadata.py
    └── tests/test_benchmark.py

Explicitly excluded from CI
├── external/HaWoR/ initialization or execution
├── CUDA/GPU setup
├── model weights or MANO files
└── HOT3D, Ego4D, and end-to-end clip runs
```

`README.md` is updated at implementation start and alongside later user-visible changes; it reads the verified commands and requirements represented by this plan, `pyproject.toml`, `environment/`, and the implemented entry points. It is not a runtime dependency and does not participate in the core call tree.

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
├── reads: direct local-video or HOT3D command arguments
├── calls: src/egocentric_pipeline/clip_request.py
├── optionally calls: src/egocentric_pipeline/hot3d_adapter.py
└── calls: src/egocentric_pipeline/video_preparation.py
    └── writes/returns: rgb.mp4 + clip_metadata.json + PreparedClip

scripts/run_hawor_pipeline.py
├── new-source branch
│   ├── reads: direct local-video or HOT3D command arguments
│   ├── calls: src/egocentric_pipeline/clip_request.py
│   └── optionally calls: src/egocentric_pipeline/hot3d_adapter.py
├── existing-prepared branch
│   └── calls: video_preparation.load_prepared_clip(clip_metadata.json)
└── calls: src/egocentric_pipeline/pipeline.py
    └── follows: the reusable pipeline branch shown above

tests/test_clip_preparation.py
├── calls: src/egocentric_pipeline/clip_request.py
├── calls: src/egocentric_pipeline/camera_intrinsics.py
└── calls: src/egocentric_pipeline/video_preparation.py

tests/test_hot3d_adapter.py
├── calls: src/egocentric_pipeline/clip_request.py
└── calls: src/egocentric_pipeline/hot3d_adapter.py

tests/test_frame_sequence_encoding.py
└── calls: src/egocentric_pipeline/frame_sequence_encoding.py

tests/test_world_export.py
└── calls: src/egocentric_pipeline/world_export.py

tests/test_run_metadata.py
└── calls: src/egocentric_pipeline/run_metadata.py

tests/test_benchmark.py
└── calls: src/egocentric_pipeline/benchmark.py
```

The reusable path is `request constructor or dataset adapter → ClipRequest → source resolution (VideoFileSource or FrameSequenceSource) → preparation → PreparedClip/ClipMetadata → HaWoR runner → world export → visualization → run metadata`. The Milestone 1 entry point adds only single-clip orchestration and automatic per-run benchmark reporting: each invocation constructs one request, calls the reusable pipeline once, and generates benchmark files for only that finalized run. `clip_metadata.json` is the durable prepared-clip boundary; within a fresh process the corresponding typed object is passed directly, while resumed processing loads the JSON into the same type before any downstream call. Frame-sequence encoding is an internal preparation capability selected from the resolved source representation, not a user-authored request option.

## 8. Metrics and Failure Review

Measure for every attempt:

- setup/preflight result;
- source timing mode, median source frame interval, maximum source-frame gap, source/prepared duration difference, unique source frames selected, dropped-frame count, repeated-source-frame count/fraction, and median/maximum timestamp-selection error;
- camera source, prepared-camera quality status, HaWoR focal provenance, and any rectification or approximation used;
- stage and total wall-clock time;
- effective frames per second;
- peak process RAM and GPU memory;
- direct-detection, motion-infill, and invalid-frame counts per hand;
- longest consecutive missing/infilled span;
- completion status for preparation, detection/tracking, hand estimation, SLAM/metric scale, infilling, export, and visualization; and
- output contract violations.

Manually review beginning, middle, end, every transition into/out of infilling, and every suspicious jump. Use these labels: missed/false hand detection, left/right identity error, implausible hand depth or scale, temporal jitter, infiller discontinuity, SLAM drift/failure, world-trajectory jump, mesh/image misalignment, rendering failure, and other. A report generated before review records `manual_review.status: pending`; a run is not accepted as Milestone 1 evidence until the required review is complete and its labels/notes are associated with that run.

Each report describes one attempt and records its completion status; it does not calculate a multi-run success rate. Any later summary across the small collection of Milestone 1 runs is descriptive only and is not generated implicitly by `benchmark.py`.

Repository-support validation is tracked separately from clip benchmarks. CI records installation success, dependency consistency, and the pass/fail result for every collected CPU-safe synthetic test. The Milestone 1 handoff records a manual README review against the final verified setup, test, command, and output paths. Neither signal is a proxy for the local GPU, licensed-asset, real-data, or visual-review gates.

## 9. Implementation Sequence

1. At the first Milestone 1 implementation change, add the root README's About section and link to the roadmap, current status, active plan, and detailed environment guidance. Retain the verified HaWoR installation material, but do not add commands or outputs that do not yet exist.
2. Create only the environment documentation/specification, submodule declaration, ignore rules, and setup checker. Update the README in the same change if these user-facing setup instructions change.
3. Establish WSL2/native Linux, Python 3.10, CUDA compiler, PyTorch, system packages, and HaWoR dependencies.
4. Place all weights and user-supplied MANO files; run the setup checker until required checks pass.
5. Run the untouched bundled HaWoR example and verify inference plus visualization. Decide whether local 8 GB execution is viable.
6. Before adding the first project-owned module or test, create `pyproject.toml` with the package metadata, verified direct dependencies, `dev` test dependencies, `src/` discovery, and pytest configuration defined in Sections 3 and 6. Confirm a clean Python 3.10 environment can install the project without `PYTHONPATH` changes, and add the verified development-install/test command to the README.
7. Implement `ClipRequest`, the `VideoFileSource`/`FrameSequenceSource` source-resolution boundary, dataset-agnostic frame-sequence encoding, camera resolution, success-or-failure run records, timestamp-driven preparation, prepared-clip loading, the HaWoR adapter, unchanged world export, visualization, and single-run benchmark reporting with synthetic tests. When the first CPU-safe test is added, create `.github/workflows/ci.yml`; expand its pytest run naturally as the remaining planned tests land. Every user-facing command or prerequisite change includes the matching README update.
8. Require the Python 3.10 CI job to pass its install, dependency, and complete CPU-safe synthetic-test checks. Keep GPU inference, external assets, and real datasets in the explicit local gates below.
9. Invoke `run_milestone1_baseline.py` once for the bundled example to verify that one request produces one pipeline attempt and its own benchmark/failure report.
10. Implement and test the HOT3D adapter against a minimal synthetic frame/calibration bundle, then acquire/select the real Aria HOT3D RGB clip. Construct its request through the adapter, resolve it to a read-only `FrameSequenceSource`, and have video preparation rectify/select its frames and call `frame_sequence_encoding.py` for the single final `rgb.mp4` encode. Invoke `run_milestone1_baseline.py` separately for this clip without a per-clip config file; do not rerun the bundled example automatically.
11. Validate the HOT3D export and review its visualization. Its unique run directory retains its own benchmark/failure report, resource evidence, and review state.
12. Only after HOT3D passes, begin Ego4D access and UID selection. Construct the Ego4D `ClipRequest` from its local video path, UID, and selected interval at runtime.
13. Invoke `run_milestone1_baseline.py` separately for the Ego4D clip without an Ego4D condition inside the HaWoR runner, exporter, visualizer, or benchmark module. Validate its export and report without rerunning HOT3D automatically.
14. Repeat the required single-clip invocations from a clean output directory, confirm that every run has a unique manifest and benchmark/failure report, recheck the README against the final implemented setup/commands/outputs, record exact verification evidence, and update `knowledge/agent/PROJECT_STATUS.md`.

## 10. Acceptance Criteria

- The root README gained an About section at implementation start, accurately describes the project purpose and unchanged-HaWoR Milestone 1 boundary, preserves or links to the verified setup guidance, and contains only commands and outputs verified against the final implementation. The final documentation review is recorded in the Milestone 1 handoff.
- `pyproject.toml` exists once project-owned source/tests exist, configures the `src/` package layout and Python `>=3.10,<3.11`, contains only verified direct and `dev` dependencies, and supports a clean editable install plus test discovery without manual `PYTHONPATH` changes. A Python 3.10 install and `python -m pip check` provide the evidence.
- `.github/workflows/ci.yml` runs on pull requests and default-branch pushes with Ubuntu/Python 3.10, installs FFmpeg and the project `dev` dependencies from `pyproject.toml`, and passes `python -m pip check` plus every planned CPU-safe synthetic test. The workflow definition and a successful run URL/status are the evidence; the workflow does not fetch or execute HaWoR, CUDA/GPU resources, weights, MANO files, HOT3D, or Ego4D.
- The setup checker passes on the execution machine and records exact software, CUDA, GPU, upstream revision, weights, and MANO presence.
- The unmodified bundled HaWoR example completes inference and produces a viewable visualization.
- One selected HOT3D clip and then one selected Ego4D clip complete through separate invocations of `run_milestone1_baseline.py`; each invocation calls the reusable pipeline exactly once and never requires or reruns the other clips.
- A direct local video can be prepared and run without a per-clip JSON/config file; the normalized request is instead recorded in `clip_metadata.json`.
- The HOT3D adapter reads the selected immutable Aria RGB frames, timestamps, and calibration and supplies the read-only records from which `video_preparation.py` constructs a `FrameSequenceSource`; it never encodes or modifies the source.
- `video_preparation.py` dispatches on `VideoFileSource` versus `FrameSequenceSource`, never a dataset name or caller-supplied encoding flag. It owns and records the rectification/timing decisions and calls the dataset-agnostic `frame_sequence_encoding.py` only for frame sequences.
- `frame_sequence_encoding.py` performs one direct encode to the final `rgb.mp4`, creates no intermediate video, contains no HOT3D-specific logic, and returns its encoding record to `video_preparation.py` for inclusion in `clip_metadata.json`.
- No dataset-specific condition exists inside the reusable HaWoR runner, world exporter, or visualizer.
- Every run uses an explicit focal length with recorded provenance.
- `video_preparation.py` writes JSON before returning a `PreparedClip`; the in-memory `ClipMetadata` and a reload of that JSON are equivalent and identify the same hashed prepared video.
- `hawor_runner.py` accepts a validated `PreparedClip` and does not implement a competing parser or source-metadata resolver.
- `clip_metadata.json` records the immutable source identity/hash, exact selected interval, every applied or explicitly skipped spatial/temporal/color/audio/encoding step, camera derivation, and per-frame source mapping. The original source remains independently preserved because dropped frames and lossy encoding are not reversible.
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
- **Duplicated or divergent dependency declarations:** `pyproject.toml` and `environment/hawor.yml` serve different scopes; keep direct project/dev dependencies in the former, the resolved HaWoR/CUDA environment in the latter, verify the combined local environment with the setup checker and `pip check`, and stop to revise the plan if one reproducible environment cannot satisfy both.
- **CI can create false confidence:** CPU-only synthetic checks cannot verify CUDA, HaWoR, model assets, real dataset adapters, or visual quality; name the job and README coverage accurately, keep excluded checks explicit, and require the separate local evidence in this section's acceptance criteria.
- **8 GB VRAM may be insufficient:** test the bundled example before building the surrounding pipeline; move to a >=16 GB Linux GPU if needed.
- **Native Windows uncertainty:** support WSL2/native Linux only for this baseline and avoid spending the milestone on a Windows port.
- **Old PyTorch/CUDA dependency stack:** validate one explicit compatibility set and freeze it in `environment/hawor.yml`.
- **Compiled extension failures:** require `nvcc`, build tools, initialized Eigen/`lietorch` submodules, and import checks in preflight.
- **Headless rendering failures:** validate rendering during the bundled example, not at the end of the milestone.
- **Incorrect focal fallback:** always supply an explicit focal length; the current upstream demo can otherwise silently fall back to 600 px.
- **HOT3D camera model mismatch:** native HOT3D images may use a fisheye model that HaWoR's scalar pinhole focal cannot represent; rectify through the official calibration path to a fixed pinhole prepared image, record the full transform and target intrinsics, and stop if the mapping cannot be verified.
- **Low or irregular source frame rate:** timestamp-based conversion preserves duration but repeated frames add no motion information; measure repeat fraction, maximum source gap, and timing error, then reject at the preparation-quality gate when the approved limits are exceeded.
- **Prepared video is not an archival copy:** frame dropping, rectification, and lossy encoding cannot be inverted; preserve the immutable original and its hash, and treat the transform history/frame map as reproducibility evidence rather than a substitute for the source.
- **Licensed assets:** keep MANO, HOT3D, Ego4D, and weights untracked and store no credentials.
- **HaWoR final validity loses origin information:** reconstruct direct-detection versus infilled provenance from preserved tracks without changing predictions.
- **Hand identity errors propagate:** keep fixed `[left, right]` order and inspect the overlay around gaps and crossings.
- **World frames differ between clips:** make no cross-clip geometric comparison in Milestone 1.
- **Two clips do not establish accuracy:** report reproducibility, structural correctness, cost, and observed failures only.

## 12. Remaining Decisions

1. Confirm WSL2 as the first execution environment, with a >=16 GB native Linux GPU as the fallback if the bundled example exceeds local VRAM.
2. Confirm the user can supply the two licensed MANO model files before the bundled example run.
3. Confirm that `external/HaWoR/` should be a pinned Git submodule rather than a manually cloned, ignored directory.
4. Choose the exact HOT3D clip and later Ego4D interval. The recommended default is one short purposeful manipulation with a hand visible through most of the action, enough camera motion and static scene texture to exercise SLAM, and no dominant motion blur. Exact identities are required before their respective runs but need not block approval of the reusable architecture unless the user wants them fixed in the plan.
5. Choose the strict preparation-quality thresholds for maximum repeated-source-frame fraction, maximum source-frame gap, and maximum source-to-prepared timestamp-selection error. This blocks final plan approval because it determines which lower-rate or irregular videos may reach HaWoR.
6. Decide whether the Milestone 1 Ego4D run must resolve calibrated/derived intrinsics or may explicitly use the approximate HaWoR-style image-dimension fallback when no trustworthy calibration exists. This blocks final plan approval for the Ego4D input contract.

## 13. References

- HaWoR project and paper: <https://hawor-project.github.io/> and <https://arxiv.org/abs/2501.02973>
- Official HaWoR implementation and installation: <https://github.com/ThunderVVV/HaWoR>
- HaWoR CUDA extension build: <https://github.com/ThunderVVV/HaWoR/blob/main/thirdparty/DROID-SLAM/setup.py>
- Current HaWoR focal-length issue: <https://github.com/ThunderVVV/HaWoR/issues/34>
- HOT3D dataset explorer: <https://explorer.projectaria.com/hot3d-aria>
- HOT3D-Clips frame and per-frame camera format: <https://github.com/facebookresearch/hot3d/blob/main/hot3d/clips/README.md>
- Ego4D access and downloader: <https://ego4d-data.org/docs/start-here/> and <https://github.com/facebookresearch/Ego4d/tree/main/ego4d/cli>
- FFmpeg timestamp-based FPS filter: <https://ffmpeg.org/ffmpeg-filters.html#fps>
- Python Packaging User Guide for `pyproject.toml` project metadata and dependency declarations (accessed 2026-09-11): <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>
- Setuptools package discovery and `src` layout (accessed 2026-09-11): <https://setuptools.pypa.io/en/latest/userguide/package_discovery.html>
- GitHub Actions guide for building and testing Python (accessed 2026-09-11): <https://docs.github.com/en/actions/tutorials/build-and-test-code/python>
