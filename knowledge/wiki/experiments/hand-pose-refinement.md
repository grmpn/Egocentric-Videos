# Hand-pose refinement: controlled iPhone comparison

Verified 2026-10-22 under the [approved plan](../plans/milestone-3-hand-pose-refinement.md).
The implementation is in `7d1ea69`; the [topic](../topics/stage-3-retargeting.md#hand-targets-base-prior-and-adjacent-regions)
owns configuration, filtering and export contracts. All linked run artifacts are
local-only under `outputs/retargeting/pose-refinement-20261022/`.

## Method

Reused the original 1,286-frame iPhone alignment and the
[latest CUDA baseline](retargeting-iphone.md#gpu-solver-rerun-2026-10-22), with
unchanged temporal weights 1.0/0.5, posture/hand/camera objectives, stride 2,
seed 42, three attempts, 700/500 evaluation budgets, hard bounds and pose gates.
No upstream inference, retiming or source-data edits. SciPy 1.15.3 was already
installed; no new project dependency was needed.

The representative sweep fits `[947,1113)` and `[1113,1286)` (310 observed frames,
588 hand observations). The smoothing setting is 0.3 seconds for both XYZ and
orientation, quadratic order, nine samples at 30 FPS. Prior strengths are residual
multipliers 0.1, 0.3 and 1.0, normalized by 1 m and 1 rad. The predeclared combined
setting uses smoothing, prior 0.3 and merging. Each variant saves its configuration,
all attempts, termination, filtered targets, joints and FK; see the
[sweep](../../../outputs/retargeting/pose-refinement-20261022/sweep.py),
[execution log](../../../outputs/retargeting/pose-refinement-20261022/sweep.log) and
[measurements](../../../outputs/retargeting/pose-refinement-20261022/comparison.json).

Merging recomputes one median-camera initialization over `[947,1286)` and uses
seed index 15; the separate final region used index 16. Sample parity happens to
stay the same here because the first interval contains 166 frames, but its final
unsampled frame now interpolates toward frame 1113 instead of holding frame 1111.
There are three merged attempts instead of six independent attempts, and the
base is shared across the old boundary. These changes are part of the comparison.
Earlier intervals and discarded gaps remain unchanged.

## Representative results

A frame passes when every eligible observed hand is within **5 mm and 10°**.
Wholly missing frames do not enter the denominator. “Smoothed” evaluates the
solution against its filtered fitting targets; for disabled filtering these equal
raw targets. The original-observation gates and restart pose-ranking remain raw.
The user explicitly requested reporting both rates after the initial comparison;
[recalculated counts and per-region rates](../../../outputs/retargeting/pose-refinement-20261022/target-pass-rates.json)
independently agree with the saved residuals.

| Variant | Raw passes / 310 | Smoothed passes / 310 | Raw position RMS (mm) | Raw angle RMS (°) | Joint acceleration RMS (rad/s²) | Frame 1113 step (rad) | Solve (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Disabled | 44 | 44 | 11.13 | 10.24 | 5.758 | 3.133 | 107.02 |
| Smoothing | 25 | 117 | 14.86 | 30.06 | 4.469 | 2.282 | 107.58 |
| Prior 0.1 | 39 | 39 | 11.84 | 10.25 | 5.967 | 0.691 | 102.09 |
| Prior 0.3 | 44 | 44 | 11.13 | 10.25 | 5.757 | 3.132 | 101.56 |
| Prior 1.0 | 39 | 39 | 11.84 | 10.25 | 5.966 | 0.692 | 106.89 |
| Merge | 38 | 38 | 11.41 | 11.34 | 5.824 | 0.079 | 92.52 |
| Combined | 26 | 125 | 15.00 | 32.02 | 7.075 | 0.078 | 92.63 |

The disabled run reproduces the historical 44 passes and 3.133 rad boundary jump;
maximum joint difference is 0.00222 rad, consistent with numerical repeat
variation rather than bitwise equivalence. Filtering smooths targets but can
change optimizer branches and reduce raw pose coverage. Merging removes the
independent-base reset, without making the region acceptable. All variants fail
the existing region gates. [Comparison figure](../../../outputs/retargeting/pose-refinement-20261022/representative-comparison.png).

The selected prior-only fits show no monotonic improvement:

| Prior weight | Translation drift, first / second (m) | Wrapped yaw drift, first / second (rad) | Prior cost, first / second |
| --- | ---: | ---: | ---: |
| 0 | 0.3544 / 0.5529 | 0.2782 / -0.3095 | 0.000000 / 0.000000 |
| 0.1 | 0.3547 / 0.2708 | 0.2776 / -0.1708 | 0.001014 / 0.000512 |
| 0.3 | 0.3545 / 0.5529 | 0.2776 / -0.3094 | 0.009122 / 0.018064 |
| 1.0 | 0.3552 / 0.2707 | 0.2774 / -0.1707 | 0.101570 / 0.051229 |

Prior costs are small relative to base-fit costs (about 162–812). Weights 0.1 and
1.0 select restart 0 for the final region, while zero and 0.3 select restart 1.
The resulting branch changes do not establish a reliable stabilizing effect.
All attempts and solver messages are preserved in each representative report.

## Complete combined rerun

The [configuration](../../../outputs/retargeting/pose-refinement-20261022/config.json)
processes all source frames, fitting `[0,296)`, `[432,893)` and `[947,1286)`.
All 24 original arrays and all timestamps are preserved; 1,096 frames receive
robot poses, with 957 observed frames and 1,797 eligible hand samples.

| Measure | Previous full CUDA run | Full combined run |
| --- | ---: | ---: |
| Raw-target frame pass rate | 189/957 (19.75%) | 118/957 (12.33%) |
| Own fitting-target frame pass rate | 189/957 (19.75%) | **406/957 (42.42%)** |
| Raw position RMS | 21.419 mm | 22.707 mm |
| Raw orientation RMS | 28.185° | 31.296° |
| Joint acceleration RMS | 5.300 rad/s² | 4.881 rad/s² |
| Frame 1113 joint step | 3.133 rad | 0.083 rad |
| Solve time | 285.15 s | 284.21 s |

Against smoothed targets the combined run's position/orientation RMS are
20.418 mm / 31.252°. Changing the reference raises the measured pass rate; it
does not prove more accurate physical reconstruction. The per-region comparison is:

| Region | Observed frames | Raw passes | Smoothed passes |
| --- | ---: | ---: | ---: |
| [0,296) | 245 | 27 (11.02%) | 88 (35.92%) |
| [432,893) | 402 | 68 (16.92%) | 215 (53.48%) |
| [947,1286) | 310 | 23 (7.42%) | 103 (33.23%) |

No region passes the original >95% coverage and ≤0.2 s gap gates; raw longest gaps
are 2.70 / 1.53 / 2.80 seconds. All selected base and trajectory solves exhaust
700 / 500 evaluations. Selected restarts are 0 / 2 / 0. The full merged result
selects a different restart from the representative combined repeat (restart 2,
26 raw / 125 smoothed passes). CUDA nonlinear repeat variability and local optima
remain material; neither result is replaced by the more favorable one.
There are zero within-region steps above 0.5 rad in both full runs; the baseline's
1113 reset was excluded from that count and is reported separately.
Total full runtime is 300.04 s, including 14.67 s of visualization.
CLI exit 2 means completed output with `demo_accepted: false`.

## Motion, displacement and filter limitations

These RMS motion statistics use consecutive eligible hand samples inside each
run's regions. Robot predictions are excluded here; their separate statistics
are in `comparison.json`. Merging adds the former boundary pair to the full run,
so the raw motion summaries differ slightly between the two region partitions.

| Full combined signal | Linear speed (m/s) | Angular speed (rad/s) | Linear acceleration (m/s²) | Angular acceleration (rad/s²) |
| --- | ---: | ---: | ---: | ---: |
| Original target | 0.685 | 2.070 | 26.042 | 51.722 |
| Filtered target | 0.523 | 1.830 | 14.754 | 22.717 |
| Robot match point / tool | 0.336 | 2.628 | 4.372 | 14.478 |

Baseline robot linear/angular speed RMS are 0.369 m/s / 2.294 rad/s, and
acceleration RMS are 6.566 m/s² / 16.808 rad/s². Thus linear motion and angular
acceleration improve in the combined run, while angular speed rises.
Raw-to-filtered displacement is 9.93 mm RMS (96.09 mm maximum), and angular
change is 1.185° RMS (21.607° maximum). Fourteen hand spans are filtered; 17 spans,
containing 40 observations, are too short and remain unchanged. No relative-pi
ambiguities occur. Missing observations and discarded gaps remain isolated.

Maximum coordinate-wise overshoot beyond the local raw window is 9.66 mm for
XYZ and 0.0291 rad for orientation logs. Speed cross-correlation over ±5 frames
peaks at zero lag for both linear and angular target motion; this descriptive
measure does not prove zero timing error at every feature. A synthetic 10 mm /
0.1 rad step has 9.09% overshoot and undershoot, with its half-amplitude crossing
at the original frame. [Step response](../../../outputs/retargeting/pose-refinement-20261022/step-response.png),
[full motion](../../../outputs/retargeting/pose-refinement-20261022/full-motion-comparison.png)
and [target boundaries](../../../outputs/retargeting/pose-refinement-20261022/target-boundaries.png).

## Verification and review

**84 focused tests pass**, including CPU/CUDA execution, omitted/disabled
settings equivalence, polynomial endpoints, short spans, missing-hand isolation,
irregular-time rejection, rotation sign/wraparound and proper rotations, prior
finite-difference derivatives, hard bounds, raw restart ranking, and exact/chained
adjacency across discarded gaps. [Test log](../../../outputs/retargeting/pose-refinement-20261022/tests.log).

Independent audits pass: ordinary URDF FK, hard bounds, transform directions,
all source arrays, both target residuals, prior cost and both selected objective
costs, all attempts' seeds/sampling/budgets, unchanged raw gates and exact merging.
The video preserves all 1,286 timestamps at 30 FPS.
[Geometry audit](../../../outputs/retargeting/pose-refinement-20261022/audit-trajectory.json),
[solver audit](../../../outputs/retargeting/pose-refinement-20261022/solver-audit.json),
[video audit](../../../outputs/retargeting/pose-refinement-20261022/video-check.json).

Browser checks pass for all nine experiment selections, frames 1112–1114 and
playback, with no page errors. The full combined viewer additionally passes 24
representative/boundary frame checks, direct/mixed/infilled observation labels,
unverified-pose visibility and hand/gripper closeups. Visually inspected the
comparison, motion, target-boundary, step-response and feasibility figures,
representative video overlays, boundary screenshots and both gripper closeups.
Rendering used software WebGL; IK used CUDA. An initial browser test raced iframe
navigation; waiting for navigation resolved it and the complete retry passed.
[All-viewer checks](../../../outputs/retargeting/pose-refinement-20261022/viewer-review.json),
[full-viewer checks](../../../outputs/retargeting/pose-refinement-20261022/viewers/full_combined/browser/browser.json)
and [both-rate display check](../../../outputs/retargeting/pose-refinement-20261022/pass-display-check.json).
The comparison page was opened with `xdg-open http://localhost:8090` after validation.

## Recommendations and use

Keep the configurable implementation. Merging is useful for eliminating an
artificial region reset, with a documented pose-coverage tradeoff. Do not promote
the tested smoothing or prior settings as a general accuracy improvement: raw
coverage worsens and the prior shows no consistent benefit. Filtering does improve
fit to its own smoother targets and some motion metrics. Defaults remain disabled;
no acceptance threshold or observation policy changed.
Physical scale, gravity, collisions, dynamic limits and successful task execution
remain unverified. This fulfills the refinement experiment, not the roadmap's
accepted simulation demonstration. Focused repository cleanup remains due before
another milestone.

The user-requested comparison page serves all nine saved results at
`http://localhost:8090`, with both raw and smoothed pass rates. Representative
views clearly label their final-region-only coverage. The source frames outside
those fits are unassigned, and robot predictions remain explicitly unverified.
To reopen after stopping the services, from the repository root run:

```bash
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-workspace/bin/python \
  outputs/retargeting/pose-refinement-20261022/open-experiments.py
```

The [full trajectory](../../../outputs/retargeting/pose-refinement-20261022/trajectory/trajectory_retargeted.npz),
[report](../../../outputs/retargeting/pose-refinement-20261022/trajectory/retargeting_report.json)
and [synchronized video](../../../outputs/retargeting/pose-refinement-20261022/trajectory/annotated_video.mp4)
are available independently of the viewers. Repeat the CLI with the saved
`config.json`, the original iPhone gravity directory and a new output directory.

## Smoothed hands on source video

User-requested visual review, 2026-10-22:
[video player](http://localhost:8090/smoothed-overlay/review.html),
[smoothed-hand overlay](../../../outputs/retargeting/pose-refinement-20261022/smoothed-overlay/smoothed-hands.mp4)
and [original/smoothed comparison](../../../outputs/retargeting/pose-refinement-20261022/smoothed-overlay/original-vs-smoothed.mp4).
Both MP4s preserve all 1,286 source frames at 30 FPS (42.867 seconds).
Blue/orange meshes identify left/right hands; 0.3-second wrist trails show motion.
The player supports slow motion, frame stepping and representative-frame jumps.

The saved full-combined targets rigidly rotate each reconstructed MANO mesh about
its original physical wrist and translate it to the filtered wrist. Original
finger articulation and shape remain intact. Projection uses the original camera
poses and approximate intrinsics, with no refitting or new inference. Invalid and
motion-infilled hands are hidden; trails never bridge missing samples or regions.
Outside-region and short-span targets remain unchanged and are labeled. These are
human fitting targets before robot IK, not robot trajectories.

Geometry checks pass: wrist agreement within 1.2e-7 m, preserved mesh distances
and agreement between analytic and renderer camera projections within 0.00062 px.
Both videos pass complete decoding and every frame timestamp matches the source.
Visually inspected frames 148, 450, 739, 1113 and 1147 plus the browser comparison.
Frame 1147 (38.233 s) has the largest smoothing displacement and shows visible
offset from the source hands; it is directly accessible in the player.
Browser checks pass for both modes, seeking, half-speed playback, frame stepping
and preservation of time/speed on mode changes. The player loads local video blobs
to support seeking on the existing server without HTTP byte ranges.
[Render geometry](../../../outputs/retargeting/pose-refinement-20261022/smoothed-overlay/render-report.json),
[video validation](../../../outputs/retargeting/pose-refinement-20261022/smoothed-overlay/validation.json)
and [browser validation](../../../outputs/retargeting/pose-refinement-20261022/smoothed-overlay/browser-check.json)
are local evidence. The [render script](../../../outputs/retargeting/pose-refinement-20261022/smoothed-overlay/render.py)
uses existing HaWoR/PyTorch3D and project MANO reconstruction; no dependencies or
production behavior changed. The player was opened after validation and linked
from the all-experiment viewer.
