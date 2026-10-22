# iPhone retargeting run

User-requested execution on 2026-10-21 of the existing
[joint/base workflow](../topics/stage-3-retargeting.md#joint-base-and-pose-trajectory-contract),
using the last [hand-weight-1 experiment](joint-base-bundled.md#gripper-offset-and-hand-weight-sweep)
settings. The initial run below used the historical observation policy, including
motion infill. The user subsequently requested that infilled hands be treated as
missing data; the [rerun](#rerun-excluding-infilled-hands) uses that policy with
unchanged solver settings and acceptance thresholds. Generated evidence is local-only.

## Input and settings

The original `data/source/iPhone/iPhoneDemonstration.mp4` is preserved. At the
user's request, FFmpeg downscaled 1920×1080 to **960×540** using Lanczos, H.264
CRF 18, and timestamp passthrough; audio is omitted from the derived working copy.
All **1,286 video frames**, their presentation timestamps and 30 FPS are preserved
([input check](../../../outputs/retargeting/iphone-20261021/input/downscale-check.json),
[derived video](../../../outputs/retargeting/iphone-20261021/input/iphone-960x540.mp4)).
Video duration is 42.8667 s; the original container's 42.901 s includes audio.
No measured intrinsics were supplied: HaWoR uses its existing approximate
600 px focal length at the working resolution, not calibrated iPhone intrinsics.

[All settings match](../../../outputs/retargeting/iphone-20261021/settings-check.json):
the joint configuration equals the previous saved `hand-1p0.json`; robot and
gravity settings also equal that experiment's inputs. The current
[default configuration](../../../configs/joint_retargeting.json) already had
hand position/orientation weights **1.0**, posture **0.5**, gripper-local offset
`[0.05, 0, 0]` m, base stride **2**, no camera-position objective, seed **42**,
three attempts, and base/trajectory evaluation budgets **700/500**. The user
confirmed these as defaults; no configuration edit was needed.

## Reconstruction and alignment

The first attempt failed because local NumPy 2.2.6 was incompatible with Torch
1.13. Restoring the existing `environment/hawor.yml` pin, NumPy 1.26.4, resolved
it; [dependency checking passes](../../../outputs/retargeting/iphone-20261021/dependency-check-after.log).
The [failed log](../../../outputs/retargeting/iphone-20261021/hawor.log) and attempt
remain intact. No new dependency was introduced.

The [successful HaWoR run](../../../outputs/retargeting/iphone-20261021/hawor/20261021T160936159279Z-f3f5d674a342/run_manifest.json)
completed all five stages in **249.04 s**. Each hand has 1,285 export-valid
frames; left/right direct-detection counts are 873/929, with 412/356 motion-infilled
frames. Infill validity does not establish visible observation or geometric accuracy.
The [overlay review](../../../outputs/retargeting/iphone-20261021/overlay-review.jpg)
shows wrists and approximate hand silhouettes tracking the sampled tasks, with
finger-shape/projection mismatch and an explicitly labeled infilled hand at 32 s.

[Gravity alignment](../../../outputs/retargeting/iphone-20261021/gravity/alignment_report.json)
completed in **39.86 s**, retaining 297 consensus inliers from 385 selected frames.
Source arrays/files and hand-camera relative geometry pass preservation checks;
maximum relative-geometry difference is 2.84e-7 m. The
[vertical review](../../../outputs/retargeting/iphone-20261021/gravity/vertical_review.png)
was inspected at beginning/middle/end and sampled inliers. Physical gravity,
camera intrinsics and metric scale have no measured reference.

## Historical retargeting and review (includes infill)

The unchanged camera heuristic retained four regions; shorter transitions remain
unassigned. All 1,286 frames are exported, with 1,096 assigned frames and 1,095
frames with valid reconstructed hands (the final source frame is invalid).
**373/1,095 observed frames pass the pose tolerances; no region qualifies as a
demonstration.** Here “observed” follows the historical `export_valid` contract and
includes HaWoR motion infill. Each frame passes only if every available hand
meets both 5 mm and 10°.

| Frames [start, stop) | Time (s) | Pose-passing frames | Longest failing gap (s) | Acceleration RMS before → after (rad/s²) |
| --- | --- | --- | --- | --- |
| [0, 296) | 0–9.87 | 206/296 (69.59%) | 1.27 | 133.22 → 246.69 |
| [432, 893) | 14.40–29.77 | 117/461 (25.38%) | 3.23 | 101.90 → 194.52 |
| [947, 1113) | 31.57–37.10 | 50/166 (30.12%) | 1.47 | 137.49 → 222.30 |
| [1113, 1286) | 37.10–42.87 | 0/172 (0%) | 5.77 | 173.11 → 341.23 |

Every region fails >95% coverage, ≤0.2 s gaps, and reduced acceleration RMS;
all exceed the ≥1 s duration requirement. Across 2,190 available hand samples,
702 fail position and 810 fail orientation (overlapping counts). Position RMS
is **144.66 mm**, maximum **1,314.77 mm**; orientation RMS is **40.42°**, maximum
**174.31°**. Camera-position RMS is 0.491 m, diagnostic only. These failed
fits remain saved and must not be interpreted as executable robot motion.

All regions used three attempts; selected attempts are 1/0/0/0. Selected base
and trajectory stages all exhausted their unchanged evaluation budgets. Solve
time was **814.64 s**; total retargeting time was **831.05 s**, including
15.10 s of visualization. These are one-run timings, not a speed benchmark.
CLI exit 2 means completed output with `demo_accepted: false`, not a crashed run.

Review the [summary](../../../outputs/retargeting/iphone-20261021/run-summary.json),
[full solver report](../../../outputs/retargeting/iphone-20261021/trajectory/retargeting_report.json),
[exported trajectory](../../../outputs/retargeting/iphone-20261021/trajectory/trajectory_retargeted.npz),
[annotated video](../../../outputs/retargeting/iphone-20261021/trajectory/annotated_video.mp4),
and [timeline](../../../outputs/retargeting/iphone-20261021/trajectory/feasibility_timeline.png).

## Historical verification and limits

The [independent ordinary-FK audit](../../../outputs/retargeting/iphone-20261021/audit-trajectory.json)
passed for all 2,190 available hand samples and all assigned joint solutions:
hard URDF bounds, locked fingers, separate physical wrist/match point/TCP,
rotating 5 cm offset, transform direction, alternate-frame indices and seed
interpolation, full-frame acceptance, missing/prediction labels, and all 24
source arrays preserved byte-for-byte. Saved FK agrees within 4.45e-10 m and
6.21e-10 rad. This verifies output consistency, not successful task execution.

[Video checking](../../../outputs/retargeting/iphone-20261021/video-check.json)
passed all 1,286 frames and timestamps at 30 FPS. The annotated video is 960×736
because the review panel is added below the 960×540 RGB. The existing production
workflow and these data audits were exercised; the unchanged unit suite was not
rerun.

[Browser checks](../../../outputs/retargeting/iphone-20261021/browser/browser.json)
passed playback, 14 representative/boundary frames, hand/gripper closeups and
pose visibility without page errors. Additional
[failure views](../../../outputs/retargeting/iphone-20261021/browser/failure-review.json)
compare hidden/shown failed poses in all four regions. Visual inspection includes
the timeline, annotated RGB, passing region-0 alignment, later failed/missing
arms, both hands, and an alternate left-hand angle. Failed poses and apparent
arm/body overlap remain review limitations; no collision or dynamics check was
performed. No simulation/controller or hardware execution was attempted.
The [visual review record](../../../outputs/retargeting/iphone-20261021/visual-review.json)
identifies the inspected frames and limitations; generated reports' original
`manual_review: pending` fields remain unchanged.

Open the saved run with the existing command (no inference or fitting rerun):

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_retargeting.py \
    outputs/retargeting/iphone-20261021/trajectory --open-browser
```

At handoff, the local review viewer is running on `http://localhost:8080` with
region overview and hand-closeup camera shortcuts. Next: review the failed
regions and reconstruction before approving any tuning. Focused repository
cleanup remains due before another milestone; Milestone 2 pilot dataset and
annotation acceptance are not established by this run.

## Rerun excluding infilled hands

The user's 2026-10-21 amendment is implemented in `cd50a37`; the
[observation contract](../topics/stage-3-retargeting.md#joint-base-and-pose-trajectory-contract)
applies to both maintained methods, fitting, acceptance, metrics and playback.
The original arrays remain intact. Infilled targets/errors are absent, their
success flags are false, and joint poses through gaps are unobserved predictions.
New inputs require boolean infill provenance. Historical saved outputs retain
their original policy with an explicit viewer notice.

The rerun reuses the existing **960×540** reconstruction and gravity alignment;
no inference, rescaling or retiming is repeated. It keeps every numerical fitting
setting, robot setting, seed, retry budget and acceptance threshold from the
weight-1 defaults. Across the full source it excludes **412 left / 356 right**
infilled hand samples, leaving **873 left / 929 right** eligible samples. Within
the same four retained regions there are **1,797 eligible hand samples on 957
frames**, including 117 frames with only one eligible hand; 139 assigned frames
have neither hand eligible. The
[coverage report](../../../outputs/retargeting/iphone-no-infill-20261021/observation-coverage.json)
records per-region counts. Each full region already has a missing-data gap longer
than 0.2 s (0.97, 0.77, 0.33 and 0.63 s), so none can meet the unchanged gap gate.

The first attempt was interrupted after more than 20 minutes while fitting the
second region. NumPy and SciPy each used a 32-thread OpenBLAS pool; the process
had 63 threads and accumulated nearly ten CPU-hours. The
[interrupted report](../../../outputs/retargeting/iphone-no-infill-20261021/trajectory-interrupted/retargeting_report.json)
and [log](../../../outputs/retargeting/iphone-no-infill-20261021/retargeting-interrupted.log)
are preserved. The restart sets only `OPENBLAS_NUM_THREADS=1` to reduce thread
overhead ([runtime record](../../../outputs/retargeting/iphone-no-infill-20261021/runtime-threads.json));
the fitting configuration is unchanged. This runtime-environment difference means
timings are not a controlled speed comparison. The completed first-region result
in both attempts is 218/245 passing poses with acceleration RMS 159.08 → 261.90 rad/s².

**855/957 eligible frames pass (89.34%), versus 354/957 (36.99%) in the
historical fit evaluated on the same observations. No region qualifies as a
demonstration.** The last two regions exceed 95% pose coverage, but all four
exceed the gap limit and increase acceleration RMS.

| Frames [start, stop) | Historical passes on eligible frames | Rerun passes | Longest unknown/failing gap (s) | Acceleration RMS before → after (rad/s²) |
| --- | --- | --- | --- | --- |
| [0, 296) | 176/245 | 218/245 (88.98%) | 1.07 | 159.08 → 261.90 |
| [432, 893) | 127/402 | 334/402 (83.08%) | 1.23 | 151.43 → 231.00 |
| [947, 1113) | 51/156 | 153/156 (98.08%) | 0.33 | 203.32 → 303.06 |
| [1113, 1286) | 0/154 | 150/154 (97.40%) | 0.63 | 115.62 → 196.09 |

The [comparison](../../../outputs/retargeting/iphone-no-infill-20261021/comparison.json)
uses identical eligible hand samples and assigned frames for both saved fits.
Position RMS decreases **53.51 → 18.49 mm**, and orientation RMS decreases
**30.31 → 5.63°**. The rerun has 6 position-failing and 101 orientation-failing
hand samples (overlapping), with 1,695/1,797 hand samples passing both gates.
The worst positional residual increases **310.09 → 758.12 mm**: the right hand
at frame **295** remains a severe outlier despite being eligible. Maximum
orientation error is 67.33°, at right-hand frame 275. These results measure fit
to estimated geometry, not reconstruction accuracy or executable robot motion.

All regions use three attempts, selecting 0/2/2/0. The selected base solve in
region 0 and trajectory solve in region 2 converge; the other selected stages
exhaust their unchanged budgets. Solve time is **942.03 s**, total **958.03 s**;
these are single-run measurements with the documented BLAS thread difference.
CLI exit 2 means completed output with `demo_accepted: false`.

Review the [solver report](../../../outputs/retargeting/iphone-no-infill-20261021/trajectory/retargeting_report.json),
[trajectory](../../../outputs/retargeting/iphone-no-infill-20261021/trajectory/trajectory_retargeted.npz),
[annotated video](../../../outputs/retargeting/iphone-no-infill-20261021/trajectory/annotated_video.mp4),
and [timeline](../../../outputs/retargeting/iphone-no-infill-20261021/trajectory/feasibility_timeline.png).

All **62 focused tests pass** in the
[test log](../../../outputs/retargeting/iphone-no-infill-20261021/tests-final.log).
They exercise both production workflows with mixed/all-infilled observations,
excluded NaN/extreme geometry, acceptance gaps and prediction labels, malformed
provenance, comparison metrics and original MANO rendering. Changing excluded
geometry leaves the fitted outputs unchanged. A final viewer check also covers
an entirely infilled left or right hand: fitting/metrics retain the opposite
hand and the empty wrist path has the required `[0,3]` color shape. This display
fix leaves the completed iPhone fit unchanged. Only existing dependency
deprecation warnings remain. The
[historical browser check](../../../outputs/retargeting/iphone-no-infill-20261021/legacy-browser.json)
loads the preserved fit, keeps its original mask and shows the historical-policy
notice without page errors.

The [independent audit](../../../outputs/retargeting/iphone-no-infill-20261021/audit-trajectory.json)
passes all 1,797 eligible hand samples and FK/bounds for all assigned predictions:
effective mask, absent excluded targets/errors/success, prediction labels, all 24
source arrays byte-preserved, left/right identity, transformed wrist/tool/TCP
geometry, 5 cm rotating offset, alternate-frame interpolation and full-frame
gates. Maximum saved-versus-ordinary-FK differences are 3.71e-10 m and 5.84e-10 rad.
The [video check](../../../outputs/retargeting/iphone-no-infill-20261021/video-check.json)
passes all 1,286 frames and timestamps at 30 FPS.

[Browser validation](../../../outputs/retargeting/iphone-no-infill-20261021/browser/browser.json)
passes playback and 17 representative/boundary/outlier frames with no page errors.
Visual inspection confirms absent infilled meshes/targets and NaN hand errors at
frame 450, left-only observed data at mixed frame 739, explicit unobserved robot
predictions, direct-hand failures, both hand/gripper closeups at frame 638, and
later-region passing/missing frames. The timeline and annotated-video labels agree.
At frame 295 the target is far from the robot; its RGB shows movement between
work areas without a clearly visible hand. Excluding infill does not guarantee
that every remaining source estimate is accurate. The
[visual review](../../../outputs/retargeting/iphone-no-infill-20261021/visual-review.json)
records these observations and remaining large joint changes/apparent arm-body
overlap. No collision, dynamic-limit, physical calibration or hardware validation
is implied. Generated reports retain their original `manual_review: pending`;
the separate review record owns the completed inspection.

Reproduce fitting in a new output directory with the recorded execution setting:

```bash
env -u LD_LIBRARY_PATH OPENBLAS_NUM_THREADS=1 PATH="$PWD/.conda/envs/hawor/bin:$PATH" PYTHONPATH=src .venv-workspace/bin/python scripts/retarget_trajectory.py \
    --method joint \
    --alignment-directory outputs/retargeting/iphone-20261021/gravity \
    --asset-root data/models/purdue-alex-assets \
    --output-directory outputs/retargeting/iphone-no-infill-repeat
```

Use the existing viewer on the completed result:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_retargeting.py \
    outputs/retargeting/iphone-no-infill-20261021/trajectory --open-browser
```

At this handoff, the new review viewer runs on `http://localhost:8081` with region
and hand-closeup shortcuts; the historical viewer remains on port 8080. Next:
review missing-data gaps, frame 295 and acceleration failures before any further
tuning. Focused repository cleanup remains due before another milestone.

## Stronger temporal smoothing

On 2026-10-21 the user requested a large increase in temporal penalties and a
comparison including large-joint-change frame counts. Under approved revision 6,
the [experimental configuration](../../../outputs/retargeting/iphone-smooth1000-20261021/config.json)
raises velocity **0.001 → 1.0** and acceleration **0.0005 → 0.5**: 1,000× residual
multipliers, or 1,000,000× squared penalties. Every other setting matches the
no-infill baseline above, including hand weights 1.0, posture 0.5, original
timestamps, segmentation, seeds, retries and evaluation budgets. The 960×540
reconstruction/alignment is reused. Default settings and source code are unchanged.

The [completed run](../../../outputs/retargeting/iphone-smooth1000-20261021/trajectory/retargeting_report.json)
took 1,793.37 s solving / 1,809.46 s total, compared with baseline 942.03 / 958.03 s.
All four regions are exported; CLI exit 2 indicates no accepted demonstration.
The [comparison](../../../outputs/retargeting/iphone-smooth1000-20261021/comparison.json)
uses the same 1,096 assigned frames, 957 observed frames and 1,797 eligible hand
samples. Large changes mean **any of 16 joints changes strictly more than 0.5 rad
(28.65°)** from the preceding frame; count the later frame once, including robot
predictions through missing observations. Unassigned gaps are not bridged.

| Metric | Baseline | Strong smoothing |
| --- | ---: | ---: |
| Large-change frames, including adjacent region boundary | **116 / 1,093** | **1 / 1,093** |
| Large-change frames within regions | **116 / 1,092** | **0 / 1,092** |
| Largest within-region joint step (rad) | 4.92384 | 0.23741 |
| Within-region velocity RMS (rad/s) | 5.95011 | 0.75388 |
| Within-region acceleration RMS (rad/s²) | 246.84942 | 5.31944 |
| Pose-passing observed frames | 855/957 (89.34%) | 189/957 (19.75%) |
| Eligible-hand position RMS (mm) | 18.49 | 21.42 |
| Eligible-hand position 95th percentile (mm) | 0.16 | 17.74 |
| Eligible-hand orientation RMS (degrees) | 5.63 | 26.99 |

The remaining adjacent-frame change is at **frame 1113 (37.1 s)**, the independent
region reset: `LEFT_WRIST_Z` changes 3.13573 rad, versus 0.24650 rad maximum across
joints at that boundary in the baseline. It is excluded from within-region
smoothing metrics but included in the first table row. Two other region resets
span unassigned gaps; their joint differences are recorded separately in the JSON.
Baseline within-region counts are 57 left-arm / 72 right-arm / 0 neck frames;
13 frames overlap between arms, giving 116 unique frames. Strong smoothing has
zero in every subset. Exact indices and per-joint counts are in the comparison;
[baseline](../../../outputs/retargeting/iphone-smooth1000-20261021/baseline-joint-changes.csv)
and [experimental](../../../outputs/retargeting/iphone-smooth1000-20261021/smooth1000-joint-changes.csv)
CSVs contain every within-region transition.

| Frames [start, stop) | Large-change frames, baseline → strong | Pose passes, baseline → strong | Acceleration RMS, baseline → strong (rad/s²) |
| --- | ---: | ---: | ---: |
| [0, 296) | 38 → 0 | 218/245 → 35/245 | 261.90 → 4.50 |
| [432, 893) | 47 → 0 | 334/402 → 109/402 | 231.00 → 5.47 |
| [947, 1113) | 17 → 0 | 153/156 → 17/156 | 303.06 → 5.82 |
| [1113, 1286) | 14 → 0 | 150/154 → 28/154 | 196.09 → 5.70 |

All twelve first-pass attempt costs and evaluation counts reproduce exactly.
The first two regions retain the same selected attempts and bases; the last two
select different restarts and bases (attempts 2 → 0 and 0 → 1). Thus the comparison
is of the standard two-stage workflow, not a fixed-base-only ablation everywhere.
The first two selected trajectory solves reach the 500-evaluation budget; the
last two stop on `ftol` at 217 and 279 evaluations. No global optimum is claimed.
All regions reduce acceleration from their interpolated seeds, but all fail
pose coverage and gap gates. This setting removes within-region spikes at a
substantial tracking cost; it is **not adopted as the default**.

The [independent audit](../../../outputs/retargeting/iphone-smooth1000-20261021/audit-trajectory.json)
passes all source/mask/prediction, joint-bound, FK/offset, sampling and gate checks.
All 24 original arrays are preserved; maximum saved-versus-ordinary-FK differences
are 3.72e−10 m and 6.13e−10 rad. The
[video check](../../../outputs/retargeting/iphone-smooth1000-20261021/video-check.json)
verifies all 1,286 original timestamps. No production code changed, so existing
unit tests were not rerun. [Browser checks](../../../outputs/retargeting/iphone-smooth1000-20261021/browser/browser.json)
cover 22 representative/boundary frames, playback, prediction visibility and
hand closeups without page errors. The
[visual review](../../../outputs/retargeting/iphone-smooth1000-20261021/visual-review.json)
includes the [motion/error plot](../../../outputs/retargeting/iphone-smooth1000-20261021/motion-and-pose-comparison.png),
[joint trajectories](../../../outputs/retargeting/iphone-smooth1000-20261021/joint-trajectory-comparison.png)
and rendered boundary poses. Physical calibration, collisions and dynamics remain
unverified. These are generated, local-only artifacts.

At the user's request, a first-region reproduction was opened before full export.
Its joints, seed, residuals, mask and base now
[match the completed run exactly](../../../outputs/retargeting/iphone-smooth1000-20261021/preview-equality.json).
At handoff, first-region playback is on `http://localhost:8082`; full-run playback
is on `http://localhost:8083`. To reopen the full result:

```bash
env -u LD_LIBRARY_PATH OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv-workspace/bin/python scripts/view_retargeting.py \
    outputs/retargeting/iphone-smooth1000-20261021/trajectory --open-browser
```

Reproduce fitting with the earlier no-infill command, adding
`--config outputs/retargeting/iphone-smooth1000-20261021/config.json` and a new
output directory. Next: review the accuracy tradeoff and region reset before
authorizing another tuning experiment. Cleanup remains due before another milestone.

## GPU solver rerun (2026-10-22)

The [approved GPU plan](../plans/milestone-3-gpu-ik.md) is fulfilled. The latest
1,000× smoothing configuration was rerun on the RTX 4090, adding only
`solver_backend: "cuda"`. All objective weights, seeds, three attempts per region,
stride, 700/500 residual-evaluation budgets and acceptance gates are unchanged.
The [solver contract](../topics/stage-3-retargeting.md#gpu-sparse-solver) owns the
CUDA/CPU split and numerical limitations; setup is in
[environment/README.md](../../../environment/README.md#cuda-trajectory-ik).

| Measurement | Previous CPU run | CUDA rerun |
| --- | ---: | ---: |
| Complete solve, all attempts | 1,793.37 s | **285.15 s (6.29× faster)** |
| Total including video export | 1,809.46 s | **301.41 s (6.00× faster)** |
| Pose-passing observed frames | 189/957 | 189/957 |
| Position RMS | 21.420 mm | 21.419 mm |
| Orientation RMS | 26.991° | 28.185° |
| Velocity RMS | 0.75388 rad/s | 0.73251 rad/s |
| Acceleration RMS | 5.31944 rad/s² | 5.29975 rad/s² |
| >0.5 rad change frames, within regions | 0/1,092 | 0/1,092 |
| >0.5 rad change frames, including adjacent reset | 1/1,093 | 1/1,093 |
| Demonstration accepted | No | No |

These are observed complete-run times against the historical CPU result, not a
controlled hardware-only benchmark. The CUDA path also replaces iterative LSMR
with direct sparse factorization. A fresh [matched benchmark](../../../outputs/retargeting/gpu-ik-20261022/benchmark.json)
uses identical stage inputs, tolerances and budgets with one OpenBLAS/OpenMP
thread. First-region full-budget base/trajectory times are 32.10/56.45 s on CPU
versus 11.65/13.65 s on repeated CUDA runs (2.76×/4.14×). Their CUDA objective
costs are slightly lower. The larger region's 40-evaluation trajectory sample is
24.77 versus 1.64 s (15.09×), with equal cost to numerical precision. Its truncated
base sample is faster but has a higher cost (24,171 versus 19,067); acceleration
does not imply uniformly better optimization. First CUDA base execution, with
fresh kernel cache/imports, takes 13.58 s. Repeat termination counts differ, so
the first/repeat difference is not a pure compilation-time measurement.

All four selected restarts remain 0/2/0/1. Pose-passing counts by region are
36/245, 109/402, 17/156 and 27/154, versus CPU 35/245, 109/402, 17/156 and 28/154.
The first two selected trajectory solves exhaust 500 evaluations; the last two
terminate by `ftol`. The adjacent region reset at frame 1113 remains **3.133 rad**;
the worst observed position residual remains about **758 mm**. All regions still
fail pose coverage/gap gates. Orientation errors and some individual poses differ;
neither bitwise equivalence nor improved reconstruction accuracy is claimed.

Validation passes: **66 focused tests**, compatible installed dependencies, all
24 source arrays byte-preserved, unchanged masks/segmentation and all 1,286 video
timestamps, hard joint/base bounds, ordinary URDF FK and saved-error consistency,
selected-stage objective recomputation, all attempts' initializations/budgets,
and unchanged acceptance labels. The maximum CUDA linear backward error is
4.34e-16. The browser checks 22 representative/boundary frames, observation labels,
prediction visibility, hand/gripper closeups and playback with no page errors.
Plots, timeline, video labels and representative hand/robot screenshots were
visually inspected. Browser capture uses software WebGL; IK uses CUDA.

Local-only evidence: [report](../../../outputs/retargeting/gpu-ik-20261022/trajectory/retargeting_report.json),
[trajectory](../../../outputs/retargeting/gpu-ik-20261022/trajectory/trajectory_retargeted.npz),
[annotated video](../../../outputs/retargeting/gpu-ik-20261022/trajectory/annotated_video.mp4),
[comparison and frame counts](../../../outputs/retargeting/gpu-ik-20261022/comparison.json),
[plots](../../../outputs/retargeting/gpu-ik-20261022/motion-and-pose-comparison.png),
[geometry audit](../../../outputs/retargeting/gpu-ik-20261022/audit-trajectory.json),
[solver audit](../../../outputs/retargeting/gpu-ik-20261022/solver-audit.json),
[video check](../../../outputs/retargeting/gpu-ik-20261022/video-check.json),
[browser review](../../../outputs/retargeting/gpu-ik-20261022/browser/browser.json),
[pose/retargeting tests](../../../outputs/retargeting/gpu-ik-20261022/tests.log),
[workspace tests](../../../outputs/retargeting/gpu-ik-20261022/workspace-tests.log),
and [visual review](../../../outputs/retargeting/gpu-ik-20261022/visual-review.json).

The viewer is available at `http://localhost:8080`. Reopen the saved result with
`scripts/view_retargeting.py outputs/retargeting/gpu-ik-20261022/trajectory` in
the workspace environment. To repeat fitting, use the earlier joint command
with `--config outputs/retargeting/gpu-ik-20261022/config.json` and a new output
directory. CUDA is now the default backend; default temporal weights remain
0.001/0.0005. Review the pose/smoothing tradeoff and region reset before further
tuning. Focused repository cleanup remains due before another milestone.
