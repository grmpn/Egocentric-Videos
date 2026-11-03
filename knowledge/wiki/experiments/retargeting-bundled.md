# Stage 3 Part 3 — Bundled placement and IK acceptance

Verified 2026-10-16 against the positional scope of [approved revision 2](../plans/milestone-3-part-3-placement-and-segmentation.md).
The original results below use TCP-to-human-wrist matching. The
[2026-10-20 wrist amendment](#wrist-alignment-amendment) records the current
wrist-to-wrist result separately.
Part 3 is complete within its positional scope. Together with
[Part 1](gravity-alignment-bundled.md) and [Part 2](robot-workspace-purdue.md),
this completes the approved fixed-base Stage 3 workflow. It does not establish
the original roadmap's controller/dynamic simulation or real-robot deliverable.

## Inputs and reproduction

The user-facing CLI reused the accepted 121-frame, 30 FPS bundled HaWoR alignment
and the preferred 10-million-FK-samples-per-arm, 2 cm workspace. Robot assets remain
Purdue Alex + SAKE revision `9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b`.
No HaWoR/GeoCalib inference or workspace sampling was repeated. All configured
baseline thresholds passed without demo-only gap/duration adjustments.

[README](../../../README.md#stage-3-part-3-fixed-base-placement-and-positional-ik)
owns reproduction commands; the [contract](../topics/stage-3-retargeting.md#part-3-placement-and-ik-contract)
owns conventions. Implementation checkpoint: `df1365b`. Reports include actual
commands, settings and package versions. The initial baseline took **5.06 s**;
this is a single observation, not a performance benchmark. Final outputs include
combined SDF/IK acceptance and clearer failure/joint-change labels.

All generated artifacts below are ignored, local-only evidence, unavailable in a
fresh clone. Reproduction needs the local accepted Part 1/2 inputs, their prepared
video/metadata and the pinned public robot assets.

- [Final run report](../../../outputs/retargeting/part-3-20261016/final/retargeting_report.json)
  and [CLI log](../../../outputs/retargeting/part-3-20261016/final.log).
- [Retargeted trajectories and transforms](../../../outputs/retargeting/part-3-20261016/final/trajectory_retargeted.npz).
- [Annotated video](../../../outputs/retargeting/part-3-20261016/final/annotated_video.mp4)
  and [feasibility timeline](../../../outputs/retargeting/part-3-20261016/final/feasibility_timeline.png).
- [Initial baseline report](../../../outputs/retargeting/part-3-20261016/baseline/retargeting_report.json),
  preserved separately from the final run.

## Observed episodes and verification

Camera seeds were `[0,52)`, `[52,57)`, `[57,74)`, `[74,105)`, `[105,121)`.
Only the first and fourth met the default one-second minimum. Their optimized
bases expanded to `[0,76)` and `[63,121)`. Deterministic overlap resolution retained
the first in full and revalidated `[76,121)` for the second base.

| Episode | Frames | Time support (s) | SDF pass | IK pass | Both pass | Longest combined gap |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `[0,76)` | `[0,2.5333)` | 73/76 (96.05%) | 75/76 (98.68%) | 73/76 (96.05%) | 0.100 s |
| 1 | `[76,121)` | `[2.5333,4.0333)` | 45/45 (100%) | 45/45 (100%) | 45/45 (100%) | 0 s |

Base XYZ/yaw, expressed in the aligned frame, is approximately
`(0.1808, 0.1312, -0.4116) m / -2.3506 rad` for episode 0 and
`(1.0265, 0.1374, 0.0240) m / 0.0097 rad` for episode 1. These are independent
fixed placements, not a mobile-base trajectory or physically grounded locations.
Optimization used 6,464 objective evaluations per seed and reached its configured
iteration budget; no global optimum is claimed.

The [independent audit](../../../outputs/retargeting/part-3-20261016/independent-audit.json)
and its [saved code](../../../outputs/retargeting/part-3-20261016/audit.py) verified:

- All **24 source arrays** retain their exact dtype/bytes, including original
  world/aligned geometry, timestamps, hand identity, validity and confidence.
- Both transform chains and inverses preserve gravity/up and source geometry.
  Independent SciPy interpolation matches all candidate SDF queries within
  **6.11e-16 m**, including hand order and invalid-query masks.
- Every retained interval independently satisfies strict **>95%** observed-frame
  coverage, **≤0.2 s** gaps and **≥1 s** duration for SDF, IK and their intersection.
- All **240 successful observed hand-frame IK solutions** obey URDF joint bounds;
  independent ordinary FK has maximum target residual **0.152 mm**, below 5 mm.
  Other joints remain locked. Source-video output has **121 frames at 30 FPS**.

Saved versus independently replayed TCP positions differ by at most **1.131 µm**.
An initial extra `1e-8 m` equality check failed; the audit uses **5 µm** consistency
tolerance for the library's incremental joint rotations/mixed-precision angle
handling. The approved **5 mm target-error limit never changed**. Original failed
audit logs and the correction are retained in event `20261016-part-3-implementation-006`.

[25 focused tests passed](../../../outputs/retargeting/part-3-20261016/tests-final.log),
covering splitting/timing, short/tail segments, strict ratios/gaps, missing data,
expansion/overlap rechecks, transform direction, hand/SDF identity, synthetic
placement, invalid settings, source-time mismatch, real-model IK success/failure
and the existing workspace contracts. The production CLI also
[refuses existing output](../../../outputs/retargeting/part-3-20261016/existing-output-check.log).
The [no-episode check](../../../outputs/retargeting/part-3-20261016/no-episodes-check.log)
raises the minimum duration only to exercise rejection: it returns exit code 2,
empty placement arrays, unassigned/NaN trajectories and a complete diagnostic video.

## Visual review and limits

[Browser checks](../../../outputs/retargeting/part-3-20261016/browser-final.json)
exercised scrubbing, play/pause, orbit/pan/zoom and both path toggles with no page
errors. [Manual review](../../../outputs/retargeting/part-3-20261016/final/visual_review.json)
inspected the source overlays, timeline and movable-camera screenshots, including
the [joint change](../../../outputs/retargeting/part-3-20261016/viewer-frame-0068.png),
[IK failure](../../../outputs/retargeting/part-3-20261016/viewer-frame-0075.png)
and [missing right estimate](../../../outputs/retargeting/part-3-20261016/final/review-frame-0120.png).
Robot bases, aligned axes, wrist/TCP markers and interval labels are visible;
missing or failed arms are hidden. Headless rendering used software WebGL;
hardware-accelerated performance was not measured.

Right-hand IK failed at frame **75**; the right estimate at frame **120** is
missing. Both remain explicit, without invented poses. Right-arm changes at
frames **68 and 69** exceed the 0.5 rad reporting threshold; the maximum is
**4.081 rad**. These are flagged discontinuities, not acceptable physical playback
commands. Missing-hand frames can pass for the available hand, without proving
bimanual feasibility. Walking seeds/expansion are a geometric heuristic, not
semantic manipulation labels. Scale, gravity accuracy, floor height, collisions,
orientation and dynamic executability remain unverified; iPhone pilot acceptance
is still separate work. Focused repository cleanup is the next checkpoint before
another milestone; it has not been performed by this task.

## Original MANO mesh comparison

The user requested this viewer extension on 2026-10-16 (approved revision 2).
It reuses the accepted run without redoing inference, placement or IK. Original
MANO pose/shape parameters are evaluated with the shared Part 1 geometry code,
then transformed into each episode's base frame and displayed with the robot.
The [contract](../topics/stage-3-retargeting.md#part-3-placement-and-ik-contract)
owns transform, validity and asset conventions.

[26 retargeting/workspace tests](../../../outputs/retargeting/mano-viewer-20261016/tests.log)
and [11 gravity regression tests](../../../outputs/retargeting/mano-viewer-20261016/gravity-regression.log)
passed, including nontrivial rotations/translations, deliberately different
candidate/episode IDs, missing/unassigned geometry, IK-independent visibility,
unchanged inputs and mismatched-wrist rejection. Licensed-asset tests executed
locally; fresh clones without those assets skip the MANO integration check.
The [bundled audit](../../../outputs/retargeting/mano-viewer-20261016/geometry-audit.json)
compared all **241 valid hand frames**, each with **778 vertices / 1,538 faces**,
against reconstruction from Part 1's aligned parameters followed by aligned-to-base
transformation. Maximum coordinate disagreement was **0.211 µm**, below the
**10 µm** geometry consistency tolerance. This does not measure physical accuracy.

[Browser checks](../../../outputs/retargeting/mano-viewer-20261016/browser.json)
passed with no page errors for playback, scrubbing across the base switch,
orbit/pan/zoom, path toggles, MANO visibility and opacity. The
[visual review](../../../outputs/retargeting/mano-viewer-20261016/visual-review.json)
confirmed blue left/orange right original hands, including
[frame 75's valid mesh despite IK failure](../../../outputs/retargeting/mano-viewer-20261016/viewer-frame-0075.png),
the [base switch](../../../outputs/retargeting/mano-viewer-20261016/viewer-frame-0076.png)
and [frame 120's missing right hand](../../../outputs/retargeting/mano-viewer-20261016/viewer-frame-0120.png).
The viewer preserves original hand orientation and articulation; robot tool
orientation remains unconstrained by positional IK. Artifacts are local-only.

## Wrist alignment amendment

Verified **2026-10-20** against the
[approved amendment](../plans/milestone-3-wrist-alignment.md).
The [diagnosis](../../../outputs/retargeting/wrist-alignment-20261020/diagnosis.json)
confirmed the old run placed TCPs at human wrists within 0.152 mm, leaving robot
`WRIST_X` origins about 23.8 cm away. The current
[contract](../topics/stage-3-retargeting.md#part-3-placement-and-ik-contract)
uses those wrist joint origins consistently for workspace, placement and IK,
retains full arm configurations with the last two rotations at zero, and
exports actual TCP positions separately. Original inputs and TCP runs remain intact.

All linked generated evidence is ignored and local-only:

- [Wrist workspace report](../../../outputs/retargeting/wrist-alignment-20261020/workspace/workspace_report.json)
  and [log](../../../outputs/retargeting/wrist-alignment-20261020/workspace.log):
  10 million samples per arm at 2 cm, using the same seeded upstream
  configurations as the old run. Maximum ordinary/batched FK difference
  **3.18e-10 m** across 70 checks; held-out occupancy **99.98%** per hand.
  Build time **25.51 s**, without new dependencies or inference.
- [Trajectory report](../../../outputs/retargeting/wrist-alignment-20261020/trajectory/retargeting_report.json),
  [arrays](../../../outputs/retargeting/wrist-alignment-20261020/trajectory/trajectory_retargeted.npz),
  [annotated video](../../../outputs/retargeting/wrist-alignment-20261020/trajectory/annotated_video.mp4)
  and [timeline](../../../outputs/retargeting/wrist-alignment-20261020/trajectory/feasibility_timeline.png).
  Production runtime **5.14 s**; all baseline thresholds retained.

| Episode | Frames | Duration | SDF pass | IK pass | Both pass | Longest combined gap |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `[0,58)` | 1.933 s | 56/58 | 56/58 | 96.55% | 0.067 s |
| 1 | `[71,121)` | 1.667 s | 48/50 | 49/50 | 96.00% | 0.067 s |

The [independent audit](../../../outputs/retargeting/wrist-alignment-20261020/independent-audit.json)
and [saved code](../../../outputs/retargeting/wrist-alignment-20261020/audit.py)
verified all **212 successful arm poses**: maximum wrist residual **2.493 mm**
(limit 5 mm), correct actual TCP positions, URDF bounds and locked joints.
It also checked all 24 unchanged source arrays, transforms, independent SDF
interpolation, episode criteria and 215 assigned valid MANO hand reconstructions.
The video retains all 121 frames at 30 FPS.

[28 final focused tests](../../../outputs/retargeting/wrist-alignment-20261020/tests-final.log)
passed, including wrist/legacy TCP workflows, rotated bases, seeded sampling,
joint bounds, zero downstream angles and missing/unreachable cases.
[Browser checks](../../../outputs/retargeting/wrist-alignment-20261020/browser.json)
and [visual review](../../../outputs/retargeting/wrist-alignment-20261020/visual-review.json)
passed for both new and preserved runs: playback, episode/gap scrubbing,
camera controls, MANO opacity/visibility and endpoint labels.
[Frame 0](../../../outputs/retargeting/wrist-alignment-20261020/viewer-frame-0000.png)
shows wrist matching; cyan markers identify displaced TCPs.
Review caught and corrected an existing case-sensitive visibility bug affecting
lowercase gripper link names. Failed/missing arms now hide those meshes too;
the valid [frame-56 MANO hand](../../../outputs/retargeting/wrist-alignment-20261020/viewer-frame-0056.png)
remains visible. Initial evidence is preserved in `browser-initial/`.

Frames **58–70** are unassigned (0.433 s); wrist reachability yields shorter
episodes than TCP reachability. Right-hand IK failures at **56, 57, 71** remain
explicit. The right-arm change at **73** is **2.282 rad**, flagged for review.
Right-hand source data is missing at **120**. Wrist alignment does not match
orientation or certify collision/dynamic feasibility. Focused repository cleanup
remains due before the next milestone.
