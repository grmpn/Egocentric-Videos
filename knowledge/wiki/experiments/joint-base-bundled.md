# Joint base and wrist-pose fitting — bundled validation

Acceptance completed 2026-10-20 under [approved revision 1](../plans/milestone-3-joint-base-optimization.md).
Numerical, source-preservation, browser/legacy and three-run comparison checks passed.
[README](../../../README.md#joint-base-and-wrist-pose-trajectory-fitting) owns
commands; the [contract](../topics/stage-3-retargeting.md#joint-base-and-pose-trajectory-contract)
owns conventions. All linked run artifacts are ignored, local-only evidence.

## Inputs and numerical evidence

Reused the accepted 121-frame/30 FPS bundled alignment and pinned Purdue Alex
SAKE assets. No HaWoR/GeoCalib inference or workspace sampling was repeated.
The camera heuristic retained `[0,52)` and `[74,105)`; neither region was expanded.
All 83 frames and 166 observed hands passed the new wrist-pose gate.

| Region | Duration | Pose coverage | Acceleration RMS before → after (rad/s²) |
| --- | --- | --- | --- |
| `[0,52)` | 1.733 s | 100% | 190.31 → 79.11 |
| `[74,105)` | 1.033 s | 100% | 326.29 → 289.95 |

The [independent ordinary-FK audit](../../../outputs/retargeting/joint-base-20261020/independent-audit.json)
verified every observed pose: maximum wrist error **0.704 mm**, orientation
error **6.191°**. It also verified joint limits, locked fingers, head FK,
transform composition, fixed bases, unassigned NaNs and all **24** original
arrays' dtype/bytes. Saved/batched versus ordinary FK differed by at most
0.2 nanometres in position and 5.7e-10 radians in rotation.

The [production report](../../../outputs/retargeting/joint-base-20261020/production-initial/retargeting_report.json),
[trajectory](../../../outputs/retargeting/joint-base-20261020/production-initial/trajectory_retargeted.npz),
[annotated video](../../../outputs/retargeting/joint-base-20261020/production-initial/annotated_video.mp4)
and [timeline](../../../outputs/retargeting/joint-base-20261020/production-initial/feasibility_timeline.png)
retain settings, all attempts, convergence and pose evidence. Region 0 accepted
its first posture initialization; region 1 accepted its second. Finite evaluation
budgets were reached in some stages; FK acceptance does not claim convergence
or global optimality.

Initial exploratory fits failed the gates. The [core check](../../../outputs/retargeting/joint-base-20261020/core-check.json)
and [initialization search](../../../outputs/retargeting/joint-base-20261020/solver-search.json)
remain available; no thresholds were relaxed. Their derivative checks agreed
within 1.2e-8. The production configuration strengthens positional weighting,
uses finite 700/500 evaluation budgets and at most three seeded attempts.

## Controlled comparison

The [comparison report](../../../outputs/retargeting/joint-base-20261020/comparison/comparison_report.json)
records three sequential, alternating runs per method on this machine and the same
83 frames. No tests or browser rendering ran during the timed solves. Both methods
passed their own gates in every run; the common gate additionally tests orientation.

| Measure | Joint/base + smoothing | Workspace placement + positional IK |
| --- | --- | --- |
| Median solve time (min–max), seconds | 70.468 (70.395–70.529) | 2.161 (2.138–2.186) |
| Common wrist-pose passing frames | 83/83 | 0/83 |
| Maximum wrist position error | 0.704 mm | 2.019 mm |
| Maximum wrist orientation error | 6.191° | 179.862° |
| Head orientation RMS | 39.469° | 73.610° |
| Joint acceleration RMS | 186.607 rad/s² | 29.464 rad/s² |

The new method is slower and has higher acceleration than the baseline, while
meeting the added orientation objective. Its acceleration decreases relative to
its own unsmoothed fit in both regions. The baseline does not optimize hand/head
orientation or temporal smoothness; this compares workflows, not isolated IK
algorithms. All 166 observed hands received finite solutions for both methods.
Historical workspace construction took 25.512 s and was not repeated. Per-run
loading, export and video-generation times are separate in the report.

The [repeat audit](../../../outputs/retargeting/joint-base-20261020/repeat-audit.json)
confirmed identical trajectory arrays across each method's three runs and equality
between the benchmark's joint result and the independently audited production run.
The [camera-translation audit](../../../outputs/retargeting/joint-base-20261020/camera-translation-audit.json)
perturbed every camera position with 5 m standard-deviation noise while fixing
segmentation and initialization. Every input to the production fitter stayed
identical. Saved fits were reused for this boundary audit; it did not repeat
optimization. The fitting residual accepts camera rotations only.

## Tests and visual review

[42 focused tests](../../../outputs/retargeting/joint-base-20261020/tests-final.log)
passed in the workspace environment, covering ordinary/batched FK, optical axes,
base initialization, sparse objective derivatives, missing observations, irregular
timestamps, smoothing, acceptance and existing workspace/retargeting behavior.
[11 gravity regression tests](../../../outputs/retargeting/joint-base-20261020/gravity-regression.log)
passed in their existing gravity environment. An initial combined invocation used
the wrong environment and failed collection on absent `cv2`; its
[failure log](../../../outputs/retargeting/joint-base-20261020/tests-collection-failed.log)
is preserved. No dependency was added.

Agent visual inspection and [browser checks](../../../outputs/retargeting/joint-base-20261020/browser-final/browser.json)
covered frames 0, 20, 51, 52, 74, 104, 105 and 120, including both region boundaries,
head/arm/MANO synchronization, orientation axes, opacity, orbit/pan/zoom and playback.
Representative screenshots show [region 0](../../../outputs/retargeting/joint-base-20261020/browser-final/viewer-frame-0000.png),
[region 1](../../../outputs/retargeting/joint-base-20261020/browser-final/viewer-frame-0074.png)
and an [unassigned frame](../../../outputs/retargeting/joint-base-20261020/browser-final/viewer-frame-0052.png).
Source-video annotations and the feasibility timeline were also inspected.

[Compatibility checks](../../../outputs/retargeting/joint-base-20261020/browser-final/compatibility.json)
passed for the original TCP and prior wrist-aligned saved runs using current viewer
code. A clearly labeled, display-only synthetic fixture verified failed-arm hiding,
missing-MANO hiding and the optional unverified robot display:
[failure hidden](../../../outputs/retargeting/joint-base-20261020/browser-final/diagnostic-failed-hidden.png),
[failure shown](../../../outputs/retargeting/joint-base-20261020/browser-final/diagnostic-failed-shown.png),
[missing observation with prediction](../../../outputs/retargeting/joint-base-20261020/browser-final/diagnostic-missing-shown.png).
This fixture is excluded from numerical acceptance; original runs are unchanged.
All final browser sessions reported no page errors. The first resumed browser
attempt used a stale port and failed to connect; the server's reported port was
then used successfully.

## Validation limits

This is kinematic pose fitting. Large joint changes, head rotation residuals,
collision clearance, dynamic limits, physical scale, gravity and floor height
remain review items, not execution certification. Camera translation is absent
from the fitting objective. The nominal camera mount centre is not a calibrated
lens centre; gripper orientation uses the documented neutral anatomical mapping.
Some playback views show apparent arm/body overlap; no collision check resolves
that appearance. Peak joint acceleration is 3451.856 rad/s², despite reduced RMS.
No real-robot or simulation/controller execution was attempted. Focused repository
cleanup remains due before starting another milestone.
