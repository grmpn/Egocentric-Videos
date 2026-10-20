# Joint base and wrist-pose fitting — bundled validation

Initial **mean-heading** acceptance completed 2026-10-20 under revision 1 of the
[approved plan](../plans/milestone-3-joint-base-optimization.md).
Numerical, source-preservation, browser/legacy and three-run comparison checks passed.
The [median-initialization trial](#median-initialization-trial) below records the
user's subsequent amendment; the original benchmark results remain unchanged.
The [camera-position/posture experiment](#camera-position-and-posture-weight-sweep)
adds per-frame position alignment under revision 3. The latest
[gripper-offset/hand-weight experiment](#gripper-offset-and-hand-weight-sweep)
removes it and changes the wrist match point and base-frame sampling under revision 4.
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
optimization. That historical fitting residual accepted camera rotations only;
revision 3 below adds camera positions.

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

## Median-initialization trial

On 2026-10-20 the user requested median forward camera heading and median position.
Position already used a component-wise median. Revision 2 replaces the mean of
normalized horizontal camera-forward vectors with their component-wise median,
then applies `atan2`. This remains the initializer; that trial did not include
a per-frame camera-position loss. The neutral camera offset rotates with the new
yaw, so initial base XY also changes even though the camera-position median does not.

One [production rerun](../../../outputs/retargeting/median-heading-20261020/trajectory/retargeting_report.json)
used identical inputs, regions, weights, budgets and retry seeds. The
[comparison](../../../outputs/retargeting/median-heading-20261020/comparison.json)
shows worse fitting quality on this clip:

| Measure | Previous mean | Median trial |
| --- | --- | --- |
| Initial yaw, `[0,52)` | −32.195° | −25.852° |
| Initial yaw, `[74,105)` | −8.717° | −7.949° |
| Pose coverage, `[0,52)` | 100% | 84.62% — rejected |
| Pose coverage, `[74,105)` | 100% | 100% — accepted |
| Maximum wrist position / orientation error | 0.704 mm / 6.191° | 3.717 mm / 36.409° |
| Head angular RMS | 39.469° | 39.496° |
| Joint acceleration RMS | 186.607 rad/s² | 295.874 rad/s² |

The first region exhausted three initial-posture attempts and failed orientation
at frames 0, 1, 2, 3, 27, 28, 29 and 31. Its longest failed gap is 0.133 s, but
44/52 passing frames do not meet the >95% coverage gate. The second region still
qualifies. Smoothing reduces each region's own acceleration RMS (369.43→299.19
and 335.13→290.07 rad/s²), but motion is sharper than in the mean-heading result.
Single-trial solve time was 123.845 s versus 70.395 s for the preserved first mean
trial; this is not a new repeated timing benchmark. The changed outcome is
consistent with sensitivity to initialization; it does not establish a general
advantage for either statistic.

[45 focused tests](../../../outputs/retargeting/median-heading-20261020/tests.log)
passed, including heading/position outliers, wraparound and observation-order
invariance. An [independent ordinary-FK audit](../../../outputs/retargeting/median-heading-20261020/independent-audit.json)
checked all 166 observed poses, limits, fixed bases, preserved 24 source arrays
and correct acceptance/failure labels. Audit success includes verifying the
rejected region; it does not mean every pose passes.

[Browser checks](../../../outputs/retargeting/median-heading-20261020/browser/browser.json)
and visual inspection covered the actual failed frames, both region boundaries,
MANO/head playback and controls, with no page errors. See the
[failed arm hidden](../../../outputs/retargeting/median-heading-20261020/browser/failed-hidden.png),
[unverified pose shown](../../../outputs/retargeting/median-heading-20261020/browser/failed-shown.png),
[accepted second region](../../../outputs/retargeting/median-heading-20261020/browser/viewer-frame-0074.png)
and [annotated video](../../../outputs/retargeting/median-heading-20261020/trajectory/annotated_video.mp4).
Earlier mean-heading runs are preserved. No solver weights or acceptance
thresholds were changed to compensate for the poorer result.

## Camera position and posture-weight sweep

The user subsequently requested camera position alignment and higher
neutral-posture weights. The implementation adds a camera-centre position
residual to both fitting stages, divided by a fixed 0.05 m scale. The scale is
an objective weight, not a hard alignment tolerance. The median initializer,
hand/camera rotations, source timing, region selection, solver budgets and seeds
remain unchanged.

Four sequential production trials use posture residual weights 0.02, 0.1, 0.5
and 2.0 (squared-cost strengths 1×, 25×, 625× and 10,000×). The preserved
rotation-only median result is the control. The
[completed sweep report](../../../outputs/retargeting/camera-posture-20261020/sweep_report.json)
records all 83 assigned frames and 166 observed hands, including failures.
Posture RMS is the unweighted deviation from neutral across all sixteen joints.
These are single trials, not a repeated runtime benchmark; no tests or browser
rendering ran during the solves.

| Camera-position objective / posture weight | Camera position RMS (cm) | Head angle RMS (°) | Posture RMS (rad) | Wrist-passing frames | Acceleration RMS (rad/s²) |
| --- | --- | --- | --- | --- | --- |
| Absent / 0.02 — control | 30.69 | 39.50 | 0.923 | 75/83 | 295.87 |
| Present / 0.02 | 26.91 | 67.83 | 0.947 | 72/83 | 282.83 |
| Present / 0.1 | 26.93 | 67.80 | 0.915 | 72/83 | 282.82 |
| Present / 0.5 | 26.91 | 66.77 | 0.874 | 72/83 | 286.13 |
| Present / 2.0 | 27.47 | 56.42 | 0.746 | 70/83 | 265.68 |

Adding camera position improves translation modestly, but worsens head rotation
and wrist coverage relative to the rotation-only control. Errors remain far
above the 5 cm residual scale: it is not an achieved tolerance. Increasing
posture weight moves the joints closer to neutral. **0.5 is the strongest tested
weight retaining an accepted region**; it does not improve all metrics. At 2.0,
neither region qualifies. The revision 3 default remained 0.02; revision 4 below adopts posture 0.5.

| Weight | Passing frames, region 0 / region 1 | Acceleration before → after, region 0 / region 1 (rad/s²) | Solve time (s) |
| --- | --- | --- | --- |
| 0.02 | 41/52 rejected / 31/31 accepted | 150.83 → 272.21 / 323.90 → 300.25 | 115.980 |
| 0.1 | 41/52 rejected / 31/31 accepted | 149.71 → 272.49 / 313.34 → 299.78 | 126.579 |
| 0.5 | 41/52 rejected / 31/31 accepted | 146.05 → 276.25 / 311.84 → 302.39 | 105.046 |
| 2.0 | 42/52 rejected / 28/31 rejected | 210.41 → 270.98 / 289.43 → 256.28 | 84.268 |

The fixed-base stage increases region 0's acceleration for every weight despite
its temporal objective. All region 0 runs exhaust three attempts and reach both
stage budgets. Region 1 takes two attempts for weights through 0.5 and three at
2.0; its final trajectory stage reaches the budget through 0.5. At 2.0 both
selected region 1 stages converge, but the wrist gate still rejects it.
Convergence and acceptance are different checks; no optimum is established.
Loading/export/rendering timings and every retry are retained in the reports.

Per-trial configs and results are local, reproducible artifacts:

| Weight | Config | Production report | Annotated video |
| --- | --- | --- | --- |
| 0.02 | [settings](../../../outputs/retargeting/camera-posture-20261020/configs/posture-0p02.json) | [report](../../../outputs/retargeting/camera-posture-20261020/posture-0p02/retargeting_report.json) | [video](../../../outputs/retargeting/camera-posture-20261020/posture-0p02/annotated_video.mp4) |
| 0.1 | [settings](../../../outputs/retargeting/camera-posture-20261020/configs/posture-0p1.json) | [report](../../../outputs/retargeting/camera-posture-20261020/posture-0p1/retargeting_report.json) | [video](../../../outputs/retargeting/camera-posture-20261020/posture-0p1/annotated_video.mp4) |
| 0.5 | [settings](../../../outputs/retargeting/camera-posture-20261020/configs/posture-0p5.json) | [report](../../../outputs/retargeting/camera-posture-20261020/posture-0p5/retargeting_report.json) | [video](../../../outputs/retargeting/camera-posture-20261020/posture-0p5/annotated_video.mp4) |
| 2.0 | [settings](../../../outputs/retargeting/camera-posture-20261020/configs/posture-2p0.json) | [report](../../../outputs/retargeting/camera-posture-20261020/posture-2p0/retargeting_report.json) | [video](../../../outputs/retargeting/camera-posture-20261020/posture-2p0/annotated_video.mp4) |

Use a selected config with the existing [production command](../../../README.md#joint-base-and-wrist-pose-trajectory-fitting)
and a fresh output directory to reproduce a trial.
The [orchestration script](../../../outputs/retargeting/camera-posture-20261020/run-sweep.py)
records the entire sweep from implementation commit `35e14ae`.

[47 focused tests](../../../outputs/retargeting/camera-posture-20261020/tests.log)
passed before the sweep. They include analytic versus finite-difference
camera/base/neck derivatives in both stages, camera target-translation influence
with regions/initialization fixed, missing wrists and a known-pose fit.
Independent ordinary-FK audits passed for
[0.02](../../../outputs/retargeting/camera-posture-20261020/audit-posture-0p02.json),
[0.1](../../../outputs/retargeting/camera-posture-20261020/audit-posture-0p1.json),
[0.5](../../../outputs/retargeting/camera-posture-20261020/audit-posture-0p5.json) and
[2.0](../../../outputs/retargeting/camera-posture-20261020/audit-posture-2p0.json):
all observed wrist/camera poses, bounds, fixed fingers/bases, transforms,
24 unchanged source arrays and acceptance labels agree. Audit success includes
correctly labeled failed poses. [Cross-trial checks](../../../outputs/retargeting/camera-posture-20261020/cross-trial-checks.json)
confirm that only posture weight varies, initial bases are identical and each
video retains 121 frames at 30 FPS.

[Browser checks](../../../outputs/retargeting/camera-posture-20261020/browser/browser.json)
passed for weights 0.02, 0.5 and 2.0 plus the preserved rotation-only run, using
current viewer code. No page errors occurred. Agent inspection covered camera
offsets, actual failed-arm hiding and the unverified-pose toggle, MANO/head
playback, both region boundaries, controls, annotated frames and low/high
feasibility timelines. Representative evidence:
[low-weight failure hidden](../../../outputs/retargeting/camera-posture-20261020/browser/low-failed-hidden.png),
[high-weight failure shown](../../../outputs/retargeting/camera-posture-20261020/browser/high-failed-shown.png),
[0.5 second region](../../../outputs/retargeting/camera-posture-20261020/browser/mid-frame-0074.png),
[unassigned frame](../../../outputs/retargeting/camera-posture-20261020/browser/low-frame-0052.png),
[legacy explanation](../../../outputs/retargeting/camera-posture-20261020/browser/legacy-frame-0000.png).
Weight 0.1 received the full numerical audit but no separate browser inspection.
The old control artifacts were not edited.

## Gripper offset and hand-weight sweep

Revision 4, implemented at `903b435` on 2026-10-20, moves the wrist match point
**5 cm along gripper-local +X toward the fingers**, as confirmed by the user.
It fits the shared base on alternate region frames (26/52 and 16/31), then
interpolates joint seeds and refines every original frame. Posture is fixed at
**0.5**; camera translation is removed from both losses, while camera rotation,
median initialization and segmentation remain. Original MANO geometry is unchanged.

The four sequential production trials vary only paired hand-position/orientation
residual multipliers. Squared-cost factors are 1, 0.25, 0.04 and 0.01.
[Settings, attempts, timing and metrics](../../../outputs/retargeting/gripper-offset-20261020/sweep_report.json)
and the [reproduction script](../../../outputs/retargeting/gripper-offset-20261020/run-sweep.py)
are saved locally. These are single-run times, with no concurrent tests/browser
rendering during the solves; they do not establish a repeated speed benchmark.

| Hand weight | Pose-passing frames | Position RMS (mm) | Orientation RMS (°) | Posture RMS (rad) | Acceleration RMS (rad/s²) | Solve (s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 79/83 | 0.113 | 4.50 | 0.744 | 257.90 | 72.15 |
| 0.5 | 78/83 | 0.117 | 4.99 | 0.719 | 240.27 | 33.08 |
| 0.2 | 60/83 | 0.199 | 7.20 | 0.649 | 67.40 | 32.79 |
| 0.1 | 0/83 | 0.689 | 15.88 | 0.574 | 62.64 | 14.92 |

Lower weights bring joints closer to neutral and reduce acceleration, but degrade
orientation coverage. Weight **0.5** is a modest tradeoff: 3.3% less posture
deviation and 6.8% less acceleration RMS than the revised control, with one fewer
passing frame. Weight **0.2** cuts acceleration by 73.9%, but loses 19 passing
frames. Weight **0.1** leaves no pose-passing frame. Keep hand defaults at 1.0
pending user review; the requested posture default is 0.5.

| Hand weight | Passing frames, regions 0 / 1 | Region 0 acceleration before → after | Region 1 acceleration before → after |
| --- | --- | --- | --- |
| 1 | 48/52 / 31/31 | 156.14 → 317.03 | 60.93 → 88.87 |
| 0.5 | 47/52 / 31/31 | 151.49 → 294.87 | 60.80 → 85.72 |
| 0.2 | 29/52 / 31/31 | 100.46 → 60.95 | 57.84 → 77.27 |
| 0.1 | 0/52 / 0/31 | 40.59 → 58.08 | 52.62 → 69.82 |

**No trial passes the full demonstration gate.** Region 0 fails pose coverage in
every trial. Region 1 passes all poses through weight 0.2, but refinement raises
its acceleration relative to the interpolated seed. The before value now measures
source-time interpolation of alternate-frame solutions; interpolation itself
removes motion detail. It is not comparable to the historical full-frame
unsmoothed fit. The acceleration gate was preserved and its failures are explicit.
All trials use three attempts per region and select attempt 0. The 1.0 control
hits the selected trajectory budget in region 0 and base budget in region 1;
selected stages at lower weights converge, without establishing global optimality.

At weights 1/0.5/0.2, all position errors stay below 5 mm (maxima
0.952/0.967/1.447 mm); 4/5/23 hand samples fail orientation. At 0.1, 132 hand
samples fail orientation and one position error reaches 5.409 mm. Camera position
RMS is 36.14/36.26/32.29/34.73 cm and head RMS is about 40.3–40.4°. These camera
translation errors are diagnostic, with no fitted position objective. Compared
with the historical camera-position/posture-0.5 run, the revised control has
better pose coverage (72→79/83), lower posture deviation (0.874→0.744 rad) and
lower acceleration (286.13→257.90 rad/s²), but worse camera translation and no
qualifying demonstration. Multiple requested settings differ, so this does not
isolate the effect of the 5 cm shift or sampling.

| Hand weight | Saved configuration | Production report | Annotated video |
| --- | --- | --- | --- |
| 1 | [config](../../../outputs/retargeting/gripper-offset-20261020/configs/hand-1p0.json) | [report](../../../outputs/retargeting/gripper-offset-20261020/hand-1p0/retargeting_report.json) | [video](../../../outputs/retargeting/gripper-offset-20261020/hand-1p0/annotated_video.mp4) |
| 0.5 | [config](../../../outputs/retargeting/gripper-offset-20261020/configs/hand-0p5.json) | [report](../../../outputs/retargeting/gripper-offset-20261020/hand-0p5/retargeting_report.json) | [video](../../../outputs/retargeting/gripper-offset-20261020/hand-0p5/annotated_video.mp4) |
| 0.2 | [config](../../../outputs/retargeting/gripper-offset-20261020/configs/hand-0p2.json) | [report](../../../outputs/retargeting/gripper-offset-20261020/hand-0p2/retargeting_report.json) | [video](../../../outputs/retargeting/gripper-offset-20261020/hand-0p2/annotated_video.mp4) |
| 0.1 | [config](../../../outputs/retargeting/gripper-offset-20261020/configs/hand-0p1.json) | [report](../../../outputs/retargeting/gripper-offset-20261020/hand-0p1/retargeting_report.json) | [video](../../../outputs/retargeting/gripper-offset-20261020/hand-0p1/annotated_video.mp4) |

[54 focused tests](../../../outputs/retargeting/gripper-offset-20261020/tests.log)
pass, covering offset FK/Jacobians, both stages, missing observations,
translation-loss removal, independent residual weights, alternate-frame seeds
and full-frame fit. The [initial test failure](../../../outputs/retargeting/gripper-offset-20261020/tests-initial.log)
exposed the changed meaning of the interpolated before-smoothing trajectory;
the test now checks its actual acceleration and retains the stride-1 improvement
check. No production acceptance threshold changed.

Independent ordinary-FK audits passed for
[1.0](../../../outputs/retargeting/gripper-offset-20261020/audit-hand-1p0.json),
[0.5](../../../outputs/retargeting/gripper-offset-20261020/audit-hand-0p5.json),
[0.2](../../../outputs/retargeting/gripper-offset-20261020/audit-hand-0p2.json) and
[0.1](../../../outputs/retargeting/gripper-offset-20261020/audit-hand-0p1.json).
Each verifies all 166 observed hand poses, separate physical wrist/match/TCP
positions, the rotating 5 cm offset, hard bounds, fixed fingers/base, sampled
indices, interpolated seeds, full-frame acceptance and 24 preserved source arrays.
[Cross-trial checks](../../../outputs/retargeting/gripper-offset-20261020/cross-trial-checks.json)
confirm identical remaining settings/initial bases and 121-frame, 30 FPS videos.


[Browser checks](../../../outputs/retargeting/gripper-offset-20261020/browser/browser.json)
passed for hand weights 1.0, 0.2 and 0.1 plus the preserved revision 3 posture-0.5
run, with no page errors. Checked playback/scrubbing, boundaries, failure hiding,
unverified-pose display, MANO, axes and camera diagnostics. Inspected representative
annotated frames and timeline as well as both hands in closeup. The initial left
closeup was occluded by the other gripper; an alternate orbit exposes that hand.
The user-confirmed shift is visible relative to the legacy wrist-origin mapping;
this is a geometric placement change, not calibrated fingertip contact. Weaker
orientation weights visibly tilt the gripper relative to the hand.

Representative review images:
[shifted right hand](../../../outputs/retargeting/gripper-offset-20261020/browser/control-right-gripper-closeup.png),
[shifted left hand](../../../outputs/retargeting/gripper-offset-20261020/browser/control-left-gripper-side.png),
[0.2 right hand](../../../outputs/retargeting/gripper-offset-20261020/browser/mid-right-gripper-closeup.png),
[0.1 failed pose shown](../../../outputs/retargeting/gripper-offset-20261020/browser/low-right-gripper-closeup.png),
[legacy right hand](../../../outputs/retargeting/gripper-offset-20261020/browser/legacy-right-gripper-closeup.png),
[failure hidden](../../../outputs/retargeting/gripper-offset-20261020/browser/control-failed-hidden.png),
[unassigned boundary](../../../outputs/retargeting/gripper-offset-20261020/browser/control-frame-0052.png).
Weight 0.5 received the full numerical audit but no separate browser inspection.
The experiment is complete; no full demonstration qualifies under the unchanged
gates. Review the tradeoff before selecting another objective change. Focused
repository cleanup remains due before moving to another milestone.

## Validation limits

This is kinematic pose fitting. Large joint changes, head rotation residuals,
collision clearance, dynamic limits, physical scale, gravity and floor height
remain review items, not execution certification. Camera translation was absent
from the original objectives, fitted in revision 3, and removed again in revision 4.
The nominal camera mount centre is not a calibrated
lens centre; gripper orientation uses the documented neutral anatomical mapping.
Some playback views show apparent arm/body overlap; no collision check resolves
that appearance. The original mean run's peak joint acceleration is 3451.856
rad/s², despite reduced RMS; the median trial peaks at 3466.371 rad/s².
No real-robot or simulation/controller execution was attempted. Focused repository
cleanup remains due before starting another milestone.
