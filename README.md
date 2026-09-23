# Egocentric Hand-Trajectory Pipeline

## About

This project turns egocentric RGB video into time-aligned 3D hand trajectories,
with language annotations and robot-compatible trajectories planned downstream.
Milestone 1 reproduces the unchanged HaWoR baseline on its bundled example and
one short Ego4D MP4 segment. It preserves HaWoR's world coordinates: no
canonicalization, alignment, smoothing, or robot conversion is performed.

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
