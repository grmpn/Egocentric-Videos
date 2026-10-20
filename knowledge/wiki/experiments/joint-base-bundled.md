# Joint base and wrist-pose fitting — bundled validation

Numerical validation 2026-10-20 under [approved revision 1](../plans/milestone-3-joint-base-optimization.md).
Final browser/legacy checks and the three-run timing comparison are in progress.
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

## Validation limits

This is kinematic pose fitting. Large joint changes, head rotation residuals,
collision clearance, dynamic limits, physical scale, gravity and floor height
remain review items, not execution certification. Camera translation is absent
from the fitting objective. The nominal camera mount centre is not a calibrated
lens centre; gripper orientation uses the documented neutral anatomical mapping.
No real-robot or simulation/controller execution was attempted.
