# Egocentric Hand-Trajectory Pipeline

## About

This project turns egocentric RGB video into time-aligned 3D hand trajectories,
with language annotations and robot-compatible trajectories planned downstream.
Milestone 1 reproduces the unchanged HaWoR baseline on its bundled example and
one short Ego4D MP4 segment. It preserves HaWoR's world coordinates: no
canonicalization, alignment, smoothing, or robot conversion is performed by that
baseline. Milestone 2 adds LeRobot packaging/canonical coordinates; Stage 3 Part 1
adds a separate, reversible gravity-aligned export.

See the [roadmap](knowledge/raw/Project-Milestones-and-Timeline.md),
[current status](knowledge/wiki/status.md), and [knowledge index](knowledge/wiki/index.md).
The [completed Milestone 1 plan](knowledge/wiki/plans/milestone-1-hawor-baseline.md)
preserves historical approval; future work uses the
[short planning format](knowledge/wiki/planning-specs.md).

## Setup

Follow [environment/README.md](environment/README.md) for installation
prerequisites, exact asset locations, runtime library paths, and ordered
recreation of [environment/hawor.yml](environment/hawor.yml).
The supported setup is Linux/WSL2, Python 3.10 in Conda, Torch 1.13.0+cu117,
CUDA toolkit 11.7, and GCC/G++ 11. The clean recreation gate is tracked in the
[baseline acceptance record](knowledge/wiki/experiments/milestone-1-baseline.md).
Model weights, licensed MANO files, inputs, and outputs remain
local and untracked; do not commit them or access credentials.

Run commands from this repository's root with the `hawor` environment active
and the documented CUDA library paths set. Project code is imported directly
using `PYTHONPATH=src`; it is not installed as a Python distribution.

```bash
PYTHONPATH=src python -c 'import egocentric_pipeline; print(egocentric_pipeline.__file__)'
PYTHONPATH=src python scripts/check_hawor_setup.py --output outputs/hawor/milestone-1/setup-new/setup_check.json
PYTHONPATH=src python -m pytest tests
```

Choose a new setup evidence path each time. The checker refuses overwrites and
returns nonzero for failed checks. GPU execution must have real device access;
WSL cuDNN needs `/usr/lib/wsl/lib` on `LD_LIBRARY_PATH`, even when a basic Torch
allocation succeeds without it.

## Process one clip

The Milestone 1 command calls the reusable pipeline exactly once and
automatically writes that attempt's benchmark, including reportable failures:

```bash
PYTHONPATH=src python scripts/run_milestone1_baseline.py --example
```

For your own MP4, supply `--video PATH` directly; no per-clip config is needed.
Use `--start-s` and `--end-s` together for a half-open interval in seconds from
the video's first presentation timestamp. Omit both to use the entire video.
The same command accepts `--dataset`, `--video-id`, `--task-label`,
`--license-reference`, and `--focal-length-px` to record source intent. See
`--help` for the complete options.

For long recordings, first trim a separate short MP4 with FFmpeg. This avoids
probing and hashing the entire recording during pipeline preparation and reload:

```bash
ffmpeg -n -ss 600 -i data/source/ego4d/Ego4D-cooking.mp4 -t 4 \
    -map 0:v:0 -an -c:v libx264 -crf 18 -pix_fmt yuv420p \
    data/source/ego4d/cooking-0600-0604.mp4
PYTHONPATH=src python scripts/run_milestone1_baseline.py \
    --video data/source/ego4d/cooking-0600-0604.mp4 --dataset ego4d
```

Keep the original recording and record its identity, hash, trim command, and
interval alongside the evaluation evidence. Pipeline timestamps refer to the
trimmed MP4; add its original start offset to locate a frame in the recording.
Trimming preserves image dimensions and does not overwrite the original.

Preparation can also run independently:

```bash
PYTHONPATH=src python scripts/prepare_clip.py --video external/HaWoR/example/video_0.mp4
```

It prints the resulting `clip_metadata.json` path. Supply that path with
`run_milestone1_baseline.py --prepared PATH` to validate and reuse prepared RGB
in a new run; it does not resume native inference. Existing prepared metadata
owns the interval, camera value, and source identity, so new request options
are rejected alongside `--prepared`.

The reusable `scripts/run_hawor_pipeline.py` accepts `--video` or `--prepared`
and writes a manifest without the milestone-specific benchmark. Programmatic
callers use `ClipRequest`, `prepare_clip`/`load_prepared_clip`, and
`pipeline.run_clip`; adjustable timing limits live in `PreparationQualityPolicy`.

Preparation is timestamp-driven 30 FPS, with no resize, crop, pad, rotation,
calibration, or lens correction. The initial gates allow at most 5% repeated
source frames, a 0.10-second maximum source gap, and 1/60-second maximum
timestamp-selection error. Inputs exceeding any gate are rejected. An omitted
focal length uses HaWoR's approximate 600 px default, never a calibration claim.

## Outputs and review

Every attempt receives a unique run directory; source and prepared files are
kept separate from native and exported results:

```text
data/prepared/<clip_id>/
  rgb.mp4
  clip_metadata.json
outputs/hawor/milestone-1/<run_id>/
  run_manifest.json
  benchmark.json
  benchmark_report.md
  clips/<clip_id>/
    native/                  # staged RGB, console log, unchanged engine artifacts
    trajectory_world.npz
    trajectory_metadata.json
    overlay.mp4
    trajectory_preview.png
    visualization.log
```

Failed stages may leave partial artifacts; the manifest records their status
and the benchmark explains unavailable metrics. Exit codes are zero for a
completed pipeline and nonzero for failure. Completion is not a quality claim:
review starts as `pending` and requires inspection of the beginning, middle,
end, infill transitions, and suspicious jumps before acceptance.

An abrupt process or host termination can prevent manifest finalization and
automatic reporting. A stale `running` manifest is not completion evidence.
Retain its partial artifacts and logs, then use `--prepared` for a fresh attempt
after confirming the old process has stopped.

Exports use hand order `[left, right]`, preserve native world values, and
separate direct detection, motion infill, native validity, and export validity.
Detection/confidence follows HaWoR's final majority track assignment (ties
right); metadata records raw detector-label disagreements. World origins and
orientations are clip-local, not aligned across clips. Resource peaks are
sampled; device-wide GPU measurements can include other applications.
Elapsed durations use the monotonic clock. UTC timestamps are audit
labels and can step when the host clock is corrected; manifests record both
the UTC span and its difference from elapsed time.
HaWoR stdout/stderr stream to the terminal and remain saved in `native/console.log`.
The console prints elapsed seconds for preparation, inference, export,
visualization, and validation; the benchmark report shows the same phase table.
Inference includes engine verification and startup. Total pipeline time includes
validation and bookkeeping, excluding prior source trimming and report generation.

## CPU-only checks

[environment/cpu-tests.yml](environment/cpu-tests.yml) and
[GitHub Actions](.github/workflows/ci.yml) create a separate CPU environment and
run `PYTHONPATH=src python -m pytest tests`. The explicit `tests` path excludes
upstream HaWoR tests. Synthetic checks exercise timestamps, MP4 preparation,
unchanged export/provenance, orchestrator failures, and single-run reports.
They do not download or validate HaWoR, CUDA, model/MANO assets, or real datasets;
GPU execution and visual inspection remain separate local acceptance gates.

## Milestone 2 dataset workflow

[Eidon validation and remaining acceptance](knowledge/wiki/experiments/milestone-2-eidon-validation.md)
reports all three attempts. The [historical laptop review index](outputs/hawor/milestone-2/README.md)
links generated evidence retained on that machine; it is absent from this desktop clone.

Use the separate Python 3.12 environment so LeRobot does not replace HaWoR's Torch:

```bash
uv venv --python 3.12 .venv-lerobot
uv pip install --python .venv-lerobot/bin/python -r environment/lerobot-requirements.txt
```

The requirement file pins Linux x86_64 CPU wheels for dataset I/O. The CLI clears
inherited `LD_LIBRARY_PATH` for LeRobot and configures CUDA 11.7/HaWoR libraries
only in the inference subprocess. Run from the repository root, using the actual
path to your HaWoR interpreter:

```bash
PYTHONPATH=src .venv-lerobot/bin/python scripts/video_to_dataset.py \
    --video data/source/iphone/demo-01.mp4 \
    --dataset-root data/lerobot/iphone-pilot \
    --task "Pick up the cup and place it on the mat" \
    --source-dataset iphone --video-id demo-01 \
    --hawor-python /path/to/hawor/bin/python
```

Invoke again with a distinct MP4/interval to append. All episodes in one dataset
must have matching image geometry and timing; unsupported inputs are rejected.
`--start-s` and `--end-s` select an interval, `--source-metadata` accepts a JSON file
with capture/source attribution, and `--focal-length-px` records a supplied focal
length. Only `.mp4` is supported. Without calibration, HaWoR's 600 px default is
explicitly approximate. Existing source files are preserved.

Reuse an already-completed attempt without GPU inference:

```bash
PYTHONPATH=src .venv-lerobot/bin/python scripts/video_to_dataset.py \
    --run-manifest outputs/hawor/milestone-2/PATH/run_manifest.json \
    --dataset-root data/lerobot/iphone-pilot --task "Pick up the cup and place it on the mat"
```

Runs/reports are under `outputs/hawor/milestone-2/`; older evidence and baseline
commands use `milestone-1/`. The dataset contains RGB, world/canonical root poses,
MANO articulation/shape, masks, confidence, per-episode provenance, canonical
previews, and a generated `DATA_CARD.md`. The [contract and limitations](knowledge/wiki/topics/lerobot-pipeline.md)
explain atomic updates, duplicate detection, canonical inversion, exact timestamps,
and the upstream v3.0/v3.1 metadata discrepancy.

The RTX 4090 desktop uses a separate vLLM environment and a 4-bit annotation model;
see [desktop setup](environment/README.md#native-desktop-and-annotation-environments)
for installation, model revision, and verification limits. With that model served
through an OpenAI-compatible endpoint, use:

```bash
PYTHONPATH=src .venv-lerobot/bin/python scripts/annotate_dataset.py \
    --dataset-root data/lerobot/iphone-pilot \
    --model QuantTrio/Qwen3.6-27B-AWQ --api-base http://localhost:8000/v1
```

This runs the official annotation CLI for plans/subtasks only, disables thinking,
and preserves prior episodes/annotations. It does not start or install a VLM
server. Review saved labels against video and timestamps before accepting them;
local fixture tests do not establish annotation quality. The desktop passes real
VLM annotation on the bundled example; the unrecorded iPhone demonstrations and
their annotation review remain pending.

Run dataset integration checks in the isolated environment:

```bash
PYTHONPATH=src .venv-lerobot/bin/python -m pytest tests/test_lerobot_export.py tests/test_canonical.py
```

These include the real `lerobot-annotate` command against a deterministic local
HTTP fixture, without sending video externally or downloading model weights.
In a restricted environment, set `HF_HOME` and `MPLCONFIGDIR` to writable cache
directories. The legacy CPU job skips LeRobot tests; CI has a separate integration
job with the pinned environment.

## Stage 3 Part 1: gravity alignment

Install the [isolated gravity environment](environment/README.md#gravity-alignment-environment),
then pass a completed HaWoR run and a **new** output directory:

```bash
PYTHONPATH=src .venv-gravity/bin/python scripts/align_gravity.py \
    --run-manifest PATH/TO/run_manifest.json \
    --output-directory outputs/gravity/my-clip
```

The command verifies and reuses prepared RGB, world hands and scaled camera poses.
It runs GeoCalib on sharp frames, estimates world up and rotates both hands/camera
into one Z-up frame. It preserves the original world/canonical dataset and
annotations. MANO parameters retain their articulation/shape; the saved physical
wrist coordinates account for the model's root offset.

`trajectory_aligned.npz` contains the source fields plus derived poses and the
reversible transform. Inspect `alignment_report.json`, `gravity_diagnostics.json`,
`trajectory_comparison.png`, `vertical_review.png` and `gravity_diagnostics.png`.
The report distinguishes completed numerical checks from pending visual review.
Failures return nonzero with diagnostics when a run directory was allocated;
insufficient gravity support never produces an accepted trajectory.

Settings live in [configs/gravity_alignment.json](configs/gravity_alignment.json);
use `--config PATH` for another explicit configuration. `--device cpu` is available
when CUDA is unavailable; the validated default is CUDA. The command clears inherited
`LD_LIBRARY_PATH` before importing modern Torch. `--help` lists model/input overrides.

See the [frame/export contract](knowledge/wiki/topics/stage-3-retargeting.md#implemented-part-1-export)
and [bundled acceptance evidence](knowledge/wiki/experiments/gravity-alignment-bundled.md).
Gravity alignment does not certify metric accuracy or robot feasibility.

```bash
PYTHONPATH=src .venv-gravity/bin/python -m pytest tests/test_gravity_alignment.py tests/test_world_export.py
```

## Stage 3 Part 2: Robot workspace

Set up the [workspace environment and pinned robot assets](environment/README.md#robot-workspace-environment),
then build independent left/right tool-position clouds, 2 cm voxel occupancy and
signed-distance tensors in `PEDESTAL_LINK` coordinates:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/build_robot_workspace.py \
    --output-directory outputs/workspace/example-10m
```

The preferred default is 10 million configurations per arm. Use `--samples-per-arm`
with a smaller count for quick checks or density comparisons, choosing a new output
directory; the supported maximum is 10 million per arm. The command preserves
source assets and refuses to overwrite a run. It saves `samples_left.npz`,
`samples_right.npz`, `workspace_grid.npz` and `workspace_report.json`, including
FK comparisons, coordinate/reload checks, held-out coverage, settings and resources.
Only consume runs whose report has `status: completed`.

The [workspace contract](knowledge/wiki/topics/stage-3-retargeting.md#part-2-workspace-contract)
defines frames, array order, query validity and limitations. Grid occupancy is
sampled position coverage; it does not establish collision-free poses, tool
orientation reachability or feasible trajectories.

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python -m pytest tests/test_robot_workspace.py -q
```

The CLI integration check requires the pinned local assets; it is skipped when
they are absent. Other tests use small synthetic volumes and an analytic URDF.

To interactively inspect the saved workspace:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_robot_workspace.py \
    outputs/workspace/example-10m --open-browser
```

The command prints a local viewer URL (normally `http://localhost:8080`). Drag to
orbit, right-drag to pan, and scroll to zoom. Toggle left/right point and voxel
layers separately; hide all four to inspect the reference robot and base axes.
Points are reduced only for display, while all occupied 2 cm cubes are available.
The robot stays at its zero reference pose. Stop the viewer with Ctrl-C. Browser
hardware acceleration is preferable for large voxel layers; software rendering
works but is slower. `--asset-root` can relocate the same pinned assets.
See the [Purdue workspace acceptance](knowledge/wiki/experiments/robot-workspace-purdue.md)
for the 100k/1m/5m/10m comparison, review images and measured limitations.

## Stage 3 Part 3: Fixed-base placement and positional IK

Reuse completed gravity-alignment and workspace directories. The workflow
segments camera motion, fits one XYZ/yaw base per seed, expands and resolves
intervals, checks positional IK, and annotates every prepared video frame.
Run it in the existing [workspace environment](environment/README.md#robot-workspace-environment):

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/retarget_trajectory.py \
    --alignment-directory outputs/gravity/part-1-20261014/bundled \
    --workspace-directory outputs/workspace/density-20261015/10m \
    --output-directory outputs/retargeting/example
```

The output directory must be new. Use `--config` to select settings based on
[trajectory_retargeting.json](configs/trajectory_retargeting.json); `--asset-root`
can relocate the same pinned model. The default requires a 3 cm workspace margin,
strictly more than 95% passing observed frames, gaps at most 0.2 s and episodes
at least 1 s. Missing hands remain unverified. Exit code 2 means processing
completed but no episode passed demonstration acceptance; inspect the report/video.

Outputs are `trajectory_retargeted.npz` (original fields plus base transforms,
candidate distances, episode assignments and joint/IK arrays),
`retargeting_report.json`, `annotated_video.mp4`, `feasibility_timeline.png` and
representative review frames. The [Part 3 contract](knowledge/wiki/topics/stage-3-retargeting.md#part-3-placement-and-ik-contract)
explains array shapes, interval boundaries and failure handling.

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_retargeting.py \
    outputs/retargeting/example --open-browser
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python -m pytest \
    tests/test_retargeting.py tests/test_robot_workspace.py -q
```

The viewer prints a local URL and supports orbit/pan/zoom, frame scrubbing,
play/pause and camera/wrist-path toggles. Blue/orange markers show left/right
wrists; white markers show verified TCPs. Failed/missing arms are hidden.
The base changes only between separately labeled episodes. Large joint changes
are flagged; no motion is synthesized across gaps. This is position-only IK,
without collision, orientation, dynamic-limit, floor or real-robot certification.
See [bundled Part 3 acceptance](knowledge/wiki/experiments/retargeting-bundled.md)
for the two retained episodes, independent audit, visual evidence and remaining
IK failure/joint discontinuities.
