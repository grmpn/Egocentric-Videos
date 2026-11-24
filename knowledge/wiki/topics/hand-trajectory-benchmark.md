# Hand-trajectory benchmark

The [approved TACO plan](../plans/taco-hand-trajectory-benchmark.md) owns scope and
metric definitions. The benchmark currently has selective TACO ingestion,
reference preparation, metrics, tables and scientific plots. Native method runs
are still being connected; no method accuracy or speed results are accepted.
The [preflight evidence](../experiments/taco-benchmark-preflight.md) records data
verification and outstanding release prerequisites.

## Workflow

`configs/experiments/taco_benchmark.json` freezes five 150-frame test clips before
inference, the plot clip, source revisions and scoring settings. The first
150 frames of each recording use the original 30 Hz mapping. No predictions
were used for selection. Inputs stay under `data/source/taco-v1/` unchanged.

Run from the repository root:

```bash
.conda/envs/hawor/bin/python scripts/benchmark_hands.py --stage download --output outputs/taco-benchmark/setup-20261124
.conda/envs/hawor/bin/python scripts/benchmark_hands.py --stage prepare --output outputs/taco-benchmark/taco-five-20261124
MPLCONFIGDIR=/tmp/taco-matplotlib .venv-pipeline/bin/python scripts/benchmark_hands.py --stage inspect --output outputs/taco-benchmark/taco-five-20261124
MPLCONFIGDIR=/tmp/taco-matplotlib .venv-pipeline/bin/python scripts/benchmark_hands.py --stage evaluate --output outputs/taco-benchmark/taco-five-20261124
```

Download uses existing `fsspec[http]` and ZIP range requests; it validates CRC and
refuses conflicting existing inputs. Preparation requires the pinned official
TACO source and existing licensed MANO files, rejects synchronization mismatches,
and refuses to replace reference outputs. Inspection projects released joints on
first/middle/last RGB frames. Evaluation can be rerun; it replaces only derived
scores/plots and explicitly accounts for absent methods.

## Method boundary

Each method/sequence directory will contain `prediction.npz`, native artifacts,
and `run.json`. A completed run supplies total elapsed seconds, effective FPS,
sampled peak VRAM in GiB, and component timing/provenance. An unsuccessful trial
retains its status, failure and elapsed evidence without fabricated accuracy.

The common NPZ contract is implemented in
`src/egocentric_pipeline/evaluation/hand_trajectory.py`:

| Field | Shape / meaning |
| --- | --- |
| `timestamp_s`, `frame_index` | `[T]`, exact prepared timestamps and original source indices |
| `joint_order` | `mano21_thumb_first_v1`: wrist, then four joints each for thumb/index/middle/ring/pinky |
| `joints_camera_m`, `joints_world_m` | `[T,2,21,3]`, metres; hands are left, right |
| `wrist_rotation_world` | `[T,2,3,3]`, proper world-from-MANO-root rotation |
| `camera_to_world` | `[T,4,4]`, world from OpenCV camera (right/down/forward) |
| `hand_valid`, `direct_valid`, `infilled` | `[T,2]` boolean; direct and infilled are disjoint subsets of camera-relative hand validity |
| `camera_valid` | `[T]` boolean; world scoring also requires a valid camera |
| `up_world` | `[3]`, RGB-estimated up for predictions, released world +Z convention for GT |

The loader checks shapes, timestamps, joint order, rigid transforms and camera /
world joint agreement. Missing samples are excluded, never interpolated. All
samples in an interval must be valid for an RPE/scale pair to count. Gravity uses
one proper world rotation per clip; initial yaw/translation uses the fixed first
second and both wrists, without scale fitting or selecting a later start.

## Reports and limits

`evaluation.json` retains trial status, per-hand metrics, pair counts, alignment,
equal-hand/equal-clip averages, population SD, and timing summaries. CSVs retain
per-hand, per-clip, average and component results. `comparison.md` displays counts
alongside means. `curves-method.npz` and `curves-common.npz` preserve frame/pair
values. The chosen clip's PNG/PDF plot uses equal metre axes and gaps.

Common support means the intersection of **all configured methods**. A missing
method makes common-support geometry unavailable; its name is never silently
dropped. Coverage always uses GT denominators, regardless of scoring support.
Completed-run throughput and worst peak accompany per-clip averages; failed runs
remain in trial accounting. Means with fewer clips are labeled by their counts.

TACO joints are released multi-view MANO fits; validity currently means finite
released parameters, not independent pose accuracy or visibility. The native
HaWoR focal approximation uses mean(fx,fy) and image-center principal point;
the complete released intrinsic matrix is preserved for projection and methods
accepting it. Five seconds provide only 30 fully valid four-second pairs per hand
and cannot establish long-duration drift behavior.
