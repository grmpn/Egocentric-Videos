# iPhone retargeting run

User-requested execution on 2026-10-21 of the existing
[joint/base workflow](../topics/stage-3-retargeting.md#joint-base-and-pose-trajectory-contract),
using the last [hand-weight-1 experiment](joint-base-bundled.md#gripper-offset-and-hand-weight-sweep)
settings. No implementation or acceptance threshold changed. Generated evidence
below is local-only under `outputs/retargeting/iphone-20261021/`.

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
maximum relative-geometry difference is 2.85e-7 m. The
[vertical review](../../../outputs/retargeting/iphone-20261021/gravity/vertical_review.png)
was inspected at beginning/middle/end and sampled inliers. Physical gravity,
camera intrinsics and metric scale have no measured reference.

## Retargeting and review

Retargeting is running. The unchanged camera heuristic retains `[0,296)`,
`[432,893)`, `[947,1113)`, and `[1113,1286)`; shorter transitions remain unassigned.
The full 1,286-frame timeline is preserved, with 1,096 frames selected for fitting.
Results, independent FK checks and playback review will be recorded here after
completion. This run does not perform simulation/controller or hardware execution.
