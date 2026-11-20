# Controlled camera and wrist comparison

The [approved iPhone plan](../plans/iphone-trajectory-comparison.md) was fulfilled
on 2026-11-20. All three full-video runs, pairwise metrics, graphs and timing
measurements passed the defined contract checks. See the
[results and acceptance evidence](../experiments/iphone-trajectory-comparison.md).

## Workflow and boundaries

The [entry point](../../../scripts/compare_trajectories.py) accepts a configuration
and new output directory. It checks source/working MP4 frame counts and presentation
timestamps, then runs `hands`, `gravity`, `hawor`, `metric_depth`, `lingbot`, `amb3r`,
`scale`, and `evaluate` in order. `--stage` permits an individual stage; `all` reuses
completed stage reports. Failed attempts are retained and must be archived before
retrying; neither file existence nor an interrupted report establishes completion.
Do not run preparation and a dependent stage concurrently.

```bash
env -u LD_LIBRARY_PATH OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 \
  .venv-pipeline/bin/python scripts/compare_trajectories.py \
  --config configs/experiments/trajectory_comparison.json \
  --output outputs/trajectory-comparison/iphone-20261119
```

Use [environment setup](../../../environment/README.md#trajectory-comparison).
GPU stages require ordinary host GPU access. Settings changes require a new run
directory; preserve the original inputs and failed attempts. Start at 960×540;
the user permits lower resolution if resource evidence warrants it.

The ordinary HaWoR pipeline and robot/dataset exports are unchanged. This experiment
calls the upstream camera-space estimator and masked DROID-SLAM separately so
all methods share hands and metric-depth inference. It does not run world-motion
infilling or smooth any trajectories. Hand predictions and their native masks
are inferred once; observed and missing states remain explicit.

## Geometry and scaling

`*_raw.npz` poses are dense `[frame,4,4]` camera-to-world transforms with OpenCV
camera axes (right, down, forward), frame indices and unscaled translation units.
HaWoR's quaternion order is xyzw. LingBot's decoded camera head is already C2W;
AMB3R's exported VO poses are C2W. Keyframe indices describe scale samples, not
the dense camera timeline. Shared MANO joints/vertices are in camera metres,
ordered left/right; the physical wrist is joint 0, not the MANO translation.

Metric3D predicts each selected HaWoR keyframe once. Both HaWoR and LingBot scale
fits consume those same arrays and hand masks. Depth sampling matches DROID's
resize then bottom/right crop, avoiding a silent full-image stretch. The native
HaWoR robust scale estimator and median aggregation are reused. Shared metric
range expansion and pixel support are recorded for both fits. This explicit
pixel mapping differs from the upstream demo's final depth resize; SLAM itself
uses the unchanged native implementation.

AMB3R's learned `depth_metric` is captured without changing inference outputs.
Its native VO code does not multiply camera translations by that learned scale.
For the same selected frames, final map points are projected into their camera
frames; ratios to captured metric depth determine one global median scale.
Native AMB3R center-cropping and masks are respected. Metric scale remains an
estimate, not a measured physical reference.

Each camera path is expressed relative to frame 0 and then rotated by the same
frame-0 GeoCalib estimate. Z is up; horizontal initial camera-forward is +X and
Y completes a right-handed frame. Cameras start at exactly the same transform.
A vertical forward axis uses camera-right as the recorded heading fallback.
Camera translation is scaled before composing the shared metric hand geometry;
hand size is never multiplied by the camera scale. Later drift remains visible.

## Comparison and timing

For cameras and each observed wrist separately, all pairs use the intersection
of valid timestamps across all methods. Report sample count, coverage, summed
Euclidean distance, mean and RMSE in metres. Missing hands create plot gaps.
The sum is sample-count-dependent disagreement, not travelled distance; none of
these quantities establishes accuracy without ground truth.

The report includes 3D/XY paths, XYZ time series, disagreement curves, CSV/JSON
tables, raw/aligned arrays and representative RGB/hand overlays. Stage wall times
include imports, loading and export; table columns separate loading, inference
and other backend work.
Shared native detection/hand times include their loading. Assembled method totals
add shared hands/gravity, each backend, scale fitting and alignment/export, plus
the same Metric3D cost for HaWoR and LingBot. Preparation validation, downloads,
shared scale-input I/O/preparation, pairwise scoring and plotting are excluded
explicitly. These are single-run measurements. Shared hand timing overlapped CPU
dependency compilation; camera backend timings did not.

## Checkpoint provenance

LingBot code is pinned to `b9dd1b1de535e6d36e777fb42b8433c781bfd783`; its official
[weights repository](https://huggingface.co/robbyant/lingbot-map) was inspected at
`e8984048a940fbdfa19909f8cc0c0ad834c1ee5a`.
The downloaded checkpoint used in this run has SHA-256
`ee665103348e07e6b826d529b8e61de8f413d5432a4f2e84970d6c8fd2e1cd72`;
[local verification](../../../outputs/trajectory-comparison/iphone-20261119/lingbot-weight-verification.json)
records its size and digest.
AMB3R code is pinned to `92c4081f910f98e683503092b85301861519175e`.
Its [official checkpoint](https://drive.google.com/file/d/14x0WW2rUE_he2hUEouP6ywSRnlJDeLel/view)
hit Google's public download quota; the Drive connector also rejected its
4,141,474,131-byte size above the connector's 256 MiB limit.
The [public mirror](https://huggingface.co/outsung/amb3r-checkpoint/tree/03f7106917e4c8210b8e20c96138bc992a8e1fba)
matches that byte size and its published SHA-256:
`2d9342282cce0a20e1074ad1513d9a18c3d100dc06c734a4a11f2d1baeea5239`.
A safe weights-only load succeeded. Direct hash comparison with the official
file remains unavailable; do not describe mirror identity as verified.

Focused evidence: [12 passing checks](../../../outputs/trajectory-comparison/iphone-20261119/final-tests.log),
including native scale recovery and the virtual-environment launcher regression.
Full-video numeric and visual acceptance is recorded in the linked experiment;
none of these checks establishes model accuracy without ground truth.
