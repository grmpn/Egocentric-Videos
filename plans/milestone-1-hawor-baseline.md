# Milestone 1 Plan: Validate the HaWoR Baseline

Status: Draft revision 2 — awaiting user review and approval

## 1. Goal

Build a small, reusable pipeline around the unchanged HaWoR inference code and prove that it can:

1. run the bundled HaWoR example;
2. process one short HOT3D clip;
3. only after the HOT3D gate passes, process one short Ego4D clip;
4. preserve HaWoR's native world-frame result;
5. export that result with frame timestamps and validity/provenance metadata;
6. generate a reusable visualization; and
7. produce a one-page benchmark and failure report.

Milestone 1 is a baseline and integration milestone. HaWoR remains the owner of hand reconstruction, camera tracking, metric scale estimation, motion infilling, and conversion into its world frame. Our code prepares inputs, invokes HaWoR, records what happened, validates the returned artifacts, and packages the existing world-frame output without changing its coordinate frame.

## 2. Explicit non-goals

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

Visualization is the only place where projection is unavoidable: drawing a 3D result on an RGB image requires HaWoR's camera/view projection. That projection is for rendering only. It must not create or replace a stored trajectory.

## 3. Setup requirements — complete before pipeline work

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

`environment/hawor.yml` will record the environment we successfully validated. It will include our small tooling dependencies in addition to upstream packages so a later machine can recreate one environment.

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

Project-side additions:

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
- example video can be decoded; and
- output directories are writable without overwriting prior runs.

The setup gate passes only when all required checks pass. Warnings such as low VRAM remain visible in the evidence and report.

## 4. Dataset order and gates

### Gate A — bundled HaWoR example

Run the official example end to end before downloading project datasets. This proves the environment, weights, MANO files, CUDA extensions, SLAM, infiller, and renderer can work together. Preserve the native result and log peak RAM/VRAM.

### Gate B — HOT3D

After Gate A passes, acquire one narrowly scoped HOT3D source and process a short segment. Use an Aria RGB segment from an official HaWoR validation sequence. Initial candidate: `P0002_2ea9af5b`, which is in HaWoR's published validation list and is available as 30 FPS, 1408 × 1408 RGB video with ground-truth hand/object data.

Select an 8–15 second interval after visual inspection using these criteria:

- at least one hand is visible through most of a purposeful manipulation;
- the camera moves enough to exercise SLAM;
- the background has static texture;
- motion blur is not dominant; and
- at least one brief hand disappearance is desirable but not required.

The first HOT3D path uses the standard RGB-video HaWoR entry point. Full HOT3D ground-truth evaluation is optional and must not block the baseline package. If annotations can be obtained with little additional setup, they may support one quantitative spot-check without changing the exported trajectory.

### Gate C — Ego4D access and run

Do not request, download, configure, or build Ego4D-specific handling until the HOT3D run has completed and its output has passed structural and visual review.

After Gate B passes:

1. accept or renew the Ego4D dataset terms;
2. configure the required AWS credentials locally;
3. inspect metadata/narrations to identify candidate UIDs;
4. use the official CLI's UID filtering to download only the needed video; and
5. select one 8–15 second, single-manipulation interval by visual inspection.

Credentials stay outside this repository and are never written to manifests or logs.

## 5. Input and output contracts

### 5.1 Human-authored clip specification

Each runnable clip has a JSON specification such as `configs/clips/hot3d_baseline.json`:

- `clip_id` — stable local identifier.
- `source_dataset` — `hawor_example`, `hot3d`, or `ego4d`.
- `source_video_id` — dataset-native sequence/video UID where applicable.
- `source_video_path` — local immutable source path.
- `source_start_s` and `source_end_s` — selected interval; null for the bundled example if the whole file is used.
- `task_label` — short human-readable action.
- `focal_length_px` — value supplied explicitly to HaWoR.
- `focal_length_source` — `calibration`, `metadata`, or `estimated`.
- `license_reference` — reference to the applicable source terms.

The specification contains intent and source identity. It does not contain generated facts such as checksums or measured frame counts.

### 5.2 Prepared clip

Input preparation writes:

```text
data/prepared/<clip_id>/rgb.mp4
data/prepared/<clip_id>/clip_metadata.json
```

`rgb.mp4` is a derived, constant-rate 30 FPS clip because the released HaWoR demo extracts frames at 30 FPS. `clip_metadata.json` records:

- source and prepared SHA-256 checksums;
- source interval;
- source and prepared codecs;
- width, height, FPS, duration, and frame count;
- per-frame clip-relative timestamp;
- per-frame source timestamp;
- focal length and its provenance;
- preparation command/version; and
- creation time.

Source files under `data/source/` are immutable. Preparation refuses to overwrite an existing prepared clip whose checksum or metadata differs.

### 5.3 Native HaWoR artifacts

HaWoR runs against a staged copy or link of the prepared clip inside the new run directory. This matters because the stock demo creates its working folders next to the input video. All native products remain together under:

```text
outputs/hawor/<run_id>/clips/<clip_id>/native/
```

Expected native artifacts include extracted RGB frames, detection tracks, masks, camera-space chunk JSON files, scaled SLAM output, `world_space_res.pth`, visualization frames/video, and console logs. These files are preserved as evidence and are never treated as our stable cross-milestone interface.

### 5.4 Stable world-frame export

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

## 6. Full planned repository structure

Only files reached by the implementation sequence are created. The tree below is the complete intended Milestone 1 structure, including generated/untracked paths for clarity.

```text
Egocentric/
├── AGENTS.md
├── PROJECT_STATUS.md
├── Project-Milestones-and-Timeline.md
├── .gitignore
├── .gitmodules
├── plans/
│   └── milestone-1-hawor-baseline.md
├── Sources/
│   └── HaWoR-Review.md
├── environment/
│   ├── README.md
│   └── hawor.yml
├── external/
│   └── HaWoR/                         # pinned Git submodule; upstream code
├── configs/
│   └── clips/
│       ├── hawor_example.json
│       ├── hot3d_baseline.json
│       └── ego4d_baseline.json         # created only after the HOT3D gate
├── src/
│   └── egocentric_pipeline/
│       ├── __init__.py
│       ├── clip_config.py
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
│   └── test_run_metadata.py
├── data/                               # untracked local licensed/input data
│   ├── source/
│   │   ├── hot3d/<sequence_id>/...
│   │   └── ego4d/<video_uid>/...       # absent until Gate C
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

## 7. File-by-file responsibilities and dependencies

### 7.1 Environment and external code

#### `environment/README.md` — reusable documentation

Human instructions for WSL/Linux setup, Conda creation, CUDA/PyTorch compatibility checks, model/MANO placement, installation order, headless rendering, and common recovery steps. It links to `hawor.yml` and `check_hawor_setup.py`; it does not duplicate the package list already expressed in the environment file.

Used by: developers setting up any milestone that runs HaWoR.

#### `environment/hawor.yml` — reusable environment specification

Reviewed Conda/pip dependency declaration for the successfully validated HaWoR runtime and our lightweight wrapper/test tools.

Used by: environment setup; checked by `scripts/check_hawor_setup.py`; version recorded by `run_metadata.py`.

#### `.gitmodules` and `external/HaWoR/` — reusable external engine

`.gitmodules` identifies the official HaWoR repository. `external/HaWoR/` is the pinned full source tree and nested submodules. Our modules invoke it but never import private copies of its code from elsewhere.

Used by: `check_hawor_setup.py`, `hawor_runner.py`, and `visualization.py`.

#### `.gitignore` — reusable repository protection

Excludes weights, MANO files, licensed videos, prepared video data, native HaWoR work products, environment caches, and generated outputs while leaving reviewed source/configuration files trackable.

Used by: the repository as a whole.

### 7.2 Configuration

#### `src/egocentric_pipeline/clip_config.py` — reusable

Defines the small typed clip configuration and validation rules. Loads a JSON clip file, checks required fields and time ranges, resolves paths, and returns a normalized in-memory configuration. It performs no video processing and contains no milestone-specific clip IDs.

Called by: `prepare_clip.py`, `pipeline.py`, and `run_milestone1_baseline.py`.

Reads: `configs/clips/*.json`.

#### `configs/clips/hawor_example.json` — Milestone 1-specific data

Points to the upstream bundled example and supplies the focal length/configuration needed for the smoke run.

Consumed by: `run_milestone1_baseline.py` through `pipeline.py`.

#### `configs/clips/hot3d_baseline.json` — Milestone 1-specific data

Records the chosen HOT3D sequence, interval, task, local source path, focal length, and license reference.

Consumed by: `prepare_clip.py` and `run_milestone1_baseline.py`.

#### `configs/clips/ego4d_baseline.json` — Milestone 1-specific data, deferred

Created only after Gate B. Records the selected Ego4D UID and interval without containing credentials.

Consumed by: the same reusable preparation and pipeline modules as HOT3D.

### 7.3 Reusable pipeline modules

#### `src/egocentric_pipeline/video_preparation.py` — reusable

Owns the boundary between arbitrary source video and HaWoR-ready input. It probes the source with ffprobe, selects the configured interval, writes a constant-rate 30 FPS MP4, calculates checksums, constructs the timestamp mapping, and writes `clip_metadata.json`. It refuses ambiguous or destructive overwrites.

Called by: `scripts/prepare_clip.py` and `pipeline.py`.

Uses: a validated clip configuration from `clip_config.py`, FFmpeg/ffprobe, and `run_metadata.py` checksum helpers.

Produces: `data/prepared/<clip_id>/rgb.mp4` and `clip_metadata.json`.

Reusable later for: iPhone clips, larger dataset ingestion, YouTube segments, and any model that expects normalized RGB video.

#### `src/egocentric_pipeline/hawor_runner.py` — reusable

Treats HaWoR as an external inference engine. It verifies the submodule revision and required files, creates a new run workspace, stages the prepared video under `native/`, invokes the official HaWoR entry point with an explicit focal length, captures stdout/stderr and exit status, samples peak RAM/VRAM, and returns paths to native artifacts. It does not interpret or modify coordinates.

Called by: `pipeline.py`.

Uses: `external/HaWoR/`, `clip_metadata.json`, and `run_metadata.py`.

Produces: native HaWoR outputs, logs, and per-stage execution records.

Reusable later for: every milestone that needs unchanged HaWoR inference.

#### `src/egocentric_pipeline/world_export.py` — reusable

Defines the stable boundary leaving HaWoR. It loads `world_space_res.pth` and saved detection tracks, transposes HaWoR's hand-major arrays to the documented frame-major layout, calculates direct-detection and infilled masks, checks finite values and frame counts, and writes `trajectory_world.npz` plus `trajectory_metadata.json`.

Copying/reordering array dimensions is allowed; altering coordinate values is not. This module contains an explicit assertion that no transform, scale, offset, smoothing, or alignment has been applied.

Called by: `pipeline.py`.

Uses: native artifacts from `hawor_runner.py` and timestamp data from `video_preparation.py`.

Produces: the stable world-frame trajectory interface used by later annotation, retargeting, evaluation, and visualization work.

Reusable later for: Milestones 2–5 and the optional research comparison track.

#### `src/egocentric_pipeline/visualization.py` — reusable

Creates two review artifacts:

- an RGB overlay using HaWoR's own rendering/projection utilities and native camera information; and
- a simple 3D root-trajectory preview that plots the unchanged exported world coordinates and clearly labels the axes as HaWoR world axes.

The module does not save a transformed trajectory. Any temporary display transform required by the renderer is isolated and documented as visualization-only.

Called by: `pipeline.py`.

Uses: prepared RGB video, native HaWoR camera/rendering artifacts, `trajectory_world.npz`, and `external/HaWoR/` rendering helpers.

Produces: `overlay.mp4` and `trajectory_preview.png`.

Reusable later for: pilot-dataset review, failure inspection, retargeting comparisons, and expanded-dataset QA.

#### `src/egocentric_pipeline/run_metadata.py` — reusable

Provides small shared helpers for SHA-256 hashing, timestamps, command/environment capture, software versions, hardware identity, non-overwriting run IDs, stage status, and JSON serialization. It owns no video or HaWoR logic.

Called by: `video_preparation.py`, `hawor_runner.py`, `world_export.py`, `pipeline.py`, and `benchmark.py`.

Produces: consistent portions of `clip_metadata.json`, `run_manifest.json`, and `benchmark.json`.

Reusable later for: provenance across all milestones.

#### `src/egocentric_pipeline/pipeline.py` — reusable top-level API

This is the central programmatic interface. Its conceptual call is:

```text
run_clip(clip_config) -> RunResult
```

It performs no model math. It coordinates the modules in order:

1. load/validate configuration;
2. prepare or verify the normalized clip;
3. create a non-overwriting run record;
4. call HaWoR;
5. export the unchanged world result;
6. render review artifacts;
7. run structural validation; and
8. finalize the run manifest.

Called by: `scripts/run_hawor_pipeline.py` and `scripts/run_milestone1_baseline.py`.

Reusable later for: processing arbitrary clips one at a time or as part of a larger dataset job.

#### `src/egocentric_pipeline/benchmark.py` — mostly reusable

Aggregates existing run manifests into machine-readable tables and Markdown. The aggregation logic is reusable; the exact one-page Milestone 1 report wording and two-clip pass gate are milestone-specific parameters.

Called by: `run_milestone1_baseline.py`.

Uses: `run_manifest.json`, `trajectory_metadata.json`, resource samples, and human review labels.

Produces: `benchmark.json` and `benchmark_report.md`.

Reusable later for: larger-scale success/failure summaries with different report templates.

### 7.4 User-facing scripts

#### `scripts/check_hawor_setup.py` — reusable

Read-only preflight command described in Section 3.11. It is the first command run on a new machine.

Calls/uses: environment inspection, `run_metadata.py`, and the external checkout.

#### `scripts/prepare_clip.py` — reusable

Thin command-line entry point for running `video_preparation.py` independently. Useful when selecting or inspecting a clip before paying the cost of inference.

Calls: `clip_config.py` and `video_preparation.py`.

#### `scripts/run_hawor_pipeline.py` — reusable

Thin general-purpose command-line front end to `pipeline.run_clip`. It accepts any valid clip JSON and prints the run directory and final status. This is the command expected to survive into later milestones.

Calls: `clip_config.py` and `pipeline.py`.

#### `scripts/run_milestone1_baseline.py` — Milestone 1-specific

Encodes only milestone ordering and gates. It runs the bundled example, requires its success before HOT3D, requires HOT3D structural/visual approval before enabling Ego4D, and finally calls `benchmark.py` across the accepted runs. It contains no reusable video, HaWoR, export, or visualization logic.

Calls: `pipeline.py` and `benchmark.py` with the three Milestone 1 config files.

### 7.5 Tests

#### `tests/test_clip_preparation.py` — reusable contracts

Uses a tiny synthetic video to test interval boundaries, constant 30 FPS output, monotonic timestamps, source timestamp mapping, checksum recording, and overwrite refusal.

Tests: `clip_config.py` and `video_preparation.py` without downloading datasets.

#### `tests/test_world_export.py` — reusable contracts

Uses a tiny synthetic HaWoR-like result to test hand-major to frame-major reordering, exact numeric preservation, shapes/dtypes, detection/infill provenance, invalid-value handling, and frame-count mismatch errors. The main invariant is that coordinate values are bitwise unchanged apart from dtype conversion explicitly declared by the exporter.

Tests: `world_export.py` without loading neural networks.

#### `tests/test_run_metadata.py` — reusable contracts

Tests deterministic hashing, required run-manifest fields, unique/non-overwriting run IDs, stage failure recording, and secret redaction.

Tests: `run_metadata.py`.

## 8. End-to-end file and control flow

```text
Human chooses source + interval + focal length
                      │
                      ▼
          configs/clips/<clip>.json
                      │
          clip_config.py validates it
                      │
                      ▼
          video_preparation.py
                      │
          ┌───────────┴────────────────┐
          ▼                            ▼
data/prepared/<clip>/rgb.mp4   clip_metadata.json
          │                            │
          └───────────┬────────────────┘
                      ▼
                pipeline.py
                      │
             hawor_runner.py
                      │ invokes as external engine
                      ▼
              external/HaWoR/
                      │
                      ▼
        outputs/.../<clip>/native/...
              │                  │
              │                  └──────────────┐
              ▼                                 ▼
       world_export.py                  visualization.py
              │                                 │
              ▼                                 ▼
 trajectory_world.npz                  overlay.mp4
 trajectory_metadata.json             trajectory_preview.png
              │                                 │
              └────────────────┬────────────────┘
                               ▼
                     run_manifest.json
                               │
                     benchmark.py
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
        benchmark.json              benchmark_report.md
```

The reusable path is `clip configuration → preparation → pipeline → HaWoR runner → world export → visualization → run metadata`. Milestone 1 contributes only one thin controller that decides which three clips run and in what gated order.

## 9. Metrics and failure review

Measure for every attempt:

- setup/preflight result;
- stage and total wall-clock time;
- effective frames per second;
- peak process RAM and GPU memory;
- direct-detection, motion-infill, and invalid-frame counts per hand;
- longest consecutive missing/infilled span;
- completion status for preparation, detection/tracking, hand estimation, SLAM/metric scale, infilling, export, and visualization; and
- output contract violations.

Manually review beginning, middle, end, every transition into/out of infilling, and every suspicious jump. Use these labels: missed/false hand detection, left/right identity error, implausible hand depth or scale, temporal jitter, infiller discontinuity, SLAM drift/failure, world-trajectory jump, mesh/image misalignment, rendering failure, and other.

With two dataset clips, success rate is descriptive only: successful clips divided by attempted clips.

## 10. Implementation sequence

1. Create only the environment documentation/specification, submodule declaration, ignore rules, and setup checker.
2. Establish WSL2/native Linux, Python 3.10, CUDA compiler, PyTorch, system packages, and HaWoR dependencies.
3. Place all weights and user-supplied MANO files; run the setup checker until required checks pass.
4. Run the untouched bundled HaWoR example and verify inference plus visualization. Decide whether local 8 GB execution is viable.
5. Implement the reusable config, run-record, preparation, HaWoR adapter, unchanged world export, and visualization modules with synthetic tests.
6. Acquire/select the HOT3D source, create its clip JSON, prepare it, and run it through the reusable command.
7. Validate the HOT3D export and review its visualization. Record failures and resource use.
8. Only after HOT3D passes, begin Ego4D access and UID selection. Create the Ego4D JSON only when the source and interval are known.
9. Process and validate the Ego4D clip using the same reusable command without dataset-specific code changes.
10. Run the Milestone 1 controller to aggregate accepted runs into the one-page benchmark/failure report.
11. Repeat from a clean output directory, record exact verification evidence, and update `PROJECT_STATUS.md`.

## 11. Acceptance criteria

- The setup checker passes on the execution machine and records exact software, CUDA, GPU, upstream revision, weights, and MANO presence.
- The unmodified bundled HaWoR example completes inference and produces a viewable visualization.
- One selected HOT3D clip and, after that gate, one selected Ego4D clip complete through the same reusable `run_hawor_pipeline.py` entry point.
- No dataset-specific condition exists inside the reusable HaWoR runner, world exporter, or visualizer.
- Every run uses an explicit focal length with recorded provenance.
- Prepared video frame counts equal exported trajectory frame counts; indices are contiguous; timestamps are strictly increasing and agree with 30 FPS within tolerance.
- The world export numerically preserves HaWoR's root translation, root orientation, hand pose, and shape arrays except for documented hand/frame axis reordering and an explicitly tested dtype conversion if needed.
- Hand order is `[left, right]` throughout and is visually checked.
- Direct detection, motion infill, upstream `hawor_valid`, and stricter `export_valid` are represented separately; detector confidence is present only for direct detections.
- Every valid exported value is finite; failures are reported rather than silently filled by our code.
- No canonical, aligned, rescaled, smoothed, or robot-frame trajectory is written.
- One overlay and one unchanged-world-coordinate trajectory preview exist and are manually reviewed for each accepted clip.
- `benchmark.json` and a one-page `benchmark_report.md` report runtime, peak resources, success, provenance coverage, visible failures, environment deviations, and remaining unverified claims.
- Original source, prepared input, native HaWoR artifacts, and stable export remain separate and are never silently overwritten.

## 12. Risks and mitigations

- **8 GB VRAM may be insufficient:** test the bundled example before building the surrounding pipeline; move to a >=16 GB Linux GPU if needed.
- **Native Windows uncertainty:** support WSL2/native Linux only for this baseline and avoid spending the milestone on a Windows port.
- **Old PyTorch/CUDA dependency stack:** validate one explicit compatibility set and freeze it in `environment/hawor.yml`.
- **Compiled extension failures:** require `nvcc`, build tools, initialized Eigen/`lietorch` submodules, and import checks in preflight.
- **Headless rendering failures:** validate rendering during the bundled example, not at the end of the milestone.
- **Incorrect focal fallback:** always supply an explicit focal length; the current upstream demo can otherwise silently fall back to 600 px.
- **Licensed assets:** keep MANO, HOT3D, Ego4D, and weights untracked and store no credentials.
- **HaWoR final validity loses origin information:** reconstruct direct-detection versus infilled provenance from preserved tracks without changing predictions.
- **Hand identity errors propagate:** keep fixed `[left, right]` order and inspect the overlay around gaps and crossings.
- **World frames differ between clips:** make no cross-clip geometric comparison in Milestone 1.
- **Two clips do not establish accuracy:** report reproducibility, structural correctness, cost, and observed failures only.

## 13. Remaining decisions before approval

1. Confirm WSL2 as the first execution environment, with a >=16 GB native Linux GPU as the fallback if the bundled example exceeds local VRAM.
2. Confirm the user can supply the two licensed MANO model files before the bundled example run.
3. Confirm that `external/HaWoR/` should be a pinned Git submodule rather than a manually cloned, ignored directory.
4. Approve choosing the exact HOT3D and later Ego4D intervals by the selection criteria above, unless the user wants to provide specific clips.

## 14. Primary references consulted

- HaWoR project and paper: <https://hawor-project.github.io/> and <https://arxiv.org/abs/2501.02973>
- Official HaWoR implementation and installation: <https://github.com/ThunderVVV/HaWoR>
- HaWoR CUDA extension build: <https://github.com/ThunderVVV/HaWoR/blob/main/thirdparty/DROID-SLAM/setup.py>
- Current HaWoR focal-length issue: <https://github.com/ThunderVVV/HaWoR/issues/34>
- HOT3D dataset explorer: <https://explorer.projectaria.com/hot3d-aria>
- Ego4D access and downloader, deferred until Gate C: <https://ego4d-data.org/docs/start-here/> and <https://github.com/facebookresearch/Ego4d/tree/main/ego4d/cli>
