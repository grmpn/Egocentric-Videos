# Direct gripper mapping — first iPhone region

Revision 5 fulfilled · 2026-10-27 · [Approved plan](../plans/milestone-3-direct-gripper-mapping.md).
The [mapping topic](../topics/direct-gripper-mapping.md) owns the geometry,
landmark, action and viewer contracts. All linked run artifacts are local-only.

## Thumbward wrist shift with forward priority

Revision 5 shifts the wrist construction point **2.5 cm toward the thumb** along
index-MCP→thumb-MCP, then aims at the MCP midpoint. The user explicitly selected
preserving forward and making closing perpendicular. The shared implementation
and compatibility rules are in the [mapping contract](../topics/direct-gripper-mapping.md).
The [current viewer](http://localhost:8091) loads the
[shifted result](../../../outputs/retargeting/gripper-wrist-offset-20261027/mapping/mapping_report.json).

[22 focused tests](../../../outputs/retargeting/gripper-wrist-offset-20261027/tests.log)
and the [296-frame / 470-sample audit](../../../outputs/retargeting/gripper-wrist-offset-20261027/audit.json)
pass. Every eligible shift is 0.025 m (numerical error below 4e−17 m), forward is
preserved and the rotation is proper. Original fields/landmarks, grasp centers
and opening actions are unchanged; right frames 92/119 still command **0.03/0.33**.
All four earlier saved mappings recompute with their original rules.

Median orientation change from revision 4 is **39.99°** (range 34.41–44.44°).
This includes the new axis priority: with forward priority held constant, the
2.5 cm shift itself changes orientation by a median **13.92°** (12.47–15.72°).
The maximum ordinary-FK TCP discrepancy remains **2.78e−17**. Neither the wrist
surface location nor physical contact alignment is calibrated.

[Browser verification](../../../outputs/retargeting/gripper-wrist-offset-20261027/browser.json)
passes full playback, endpoints/gaps, opening anchors, shift editing, snapshot save
and reset to 0.025 m, with no page errors. Visually checked
[frame 92](../../../outputs/retargeting/gripper-wrist-offset-20261027/right-frame-92.png),
[the shifted wrist and forward line](../../../outputs/retargeting/gripper-wrist-offset-20261027/right-landmarks-119.png)
and [both hands](../../../outputs/retargeting/gripper-wrist-offset-20261027/final-viewer.png).
A [reload check](../../../outputs/retargeting/gripper-wrist-offset-20261027/reload.json)
verifies the original five-landmark run and a new 0.03 m control-validation
snapshot. Both displayed markers/segments match the selected offset and forward
direction. The live baseline remains **0.025 m**, paused at frame **119**;
the 0.03 m snapshot is validation evidence, not an adopted tuning change.

To reopen:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_gripper_mapping.py \
    outputs/retargeting/gripper-wrist-offset-20261027/mapping --port 8091
```

## Previous wrist→MCP-midpoint direction

Revision 4 follows the user's subsequent request: forward points from wrist to
midpoint(thumb MCP, index MCP), projected perpendicular to the closing axis.
The closing axis, fingertip grasp center and fitted opening normalization remain
unchanged. Its viewer loaded the
[midpoint result](../../../outputs/retargeting/gripper-mcp-midpoint-20261027/mapping/mapping_report.json).

[17 focused tests](../../../outputs/retargeting/gripper-mcp-midpoint-20261027/tests.log)
and the [296-frame / 470-sample audit](../../../outputs/retargeting/gripper-mcp-midpoint-20261027/audit.json)
pass. All opening actions and grasp centers are unchanged; right frames 92/119
remain **0.03/0.33**. The new rotation agrees with the original wrist→thumb-MCP
construction to numerical precision, as expected from the projection identity
explained in the [mapping contract](../topics/direct-gripper-mapping.md).
The maximum rotation-element difference is **3.34e−16**.
[Browser playback](../../../outputs/retargeting/gripper-mcp-midpoint-20261027/browser.json),
[snapshot reload and both displayed forward segments](../../../outputs/retargeting/gripper-mcp-midpoint-20261027/reload.json)
pass. Visually inspected [frame 92](../../../outputs/retargeting/gripper-mcp-midpoint-20261027/right-frame-92.png),
[the midpoint construction](../../../outputs/retargeting/gripper-mcp-midpoint-20261027/right-landmarks-119.png)
and the [both-hand view at frame 119](../../../outputs/retargeting/gripper-mcp-midpoint-20261027/final-viewer.png).
The midpoint result was reviewed at frame 119. Physical contact calibration remains unverified.

To reopen:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_gripper_mapping.py \
    outputs/retargeting/gripper-mcp-midpoint-20261027/mapping --port 8091
```

## Previous index MCP→PIP trial

Revision 3 uses native MANO index joints **1→2**, projected perpendicular to the
unchanged closing axis. The shared opening fit, fingertip grasp centers and local
TCP corrections are unchanged. Its viewer loaded
[the index-axis result](../../../outputs/retargeting/gripper-index-20261027/mapping/mapping_report.json).

[16 focused tests](../../../outputs/retargeting/gripper-index-20261027/tests.log)
and the [full-region audit](../../../outputs/retargeting/gripper-index-20261027/audit.json)
pass for **296 frames / 470 eligible samples**. All original source fields, previous
six landmarks, tip distances, centers and opening actions are preserved. Right
frames **92/119 remain 0.03/0.33**. Median orientation change from the thumb-axis
mapping is **15.66°**, maximum **54.98°**. Maximum ordinary-FK TCP discrepancy is
**5.56e−17**. Older wrist- and thumb-axis results remain supported.
[Browser playback and snapshots](../../../outputs/retargeting/gripper-index-20261027/browser.json),
[reload checks](../../../outputs/retargeting/gripper-index-20261027/reload.json), and
[visual review](../../../outputs/retargeting/gripper-index-20261027/right-landmarks-119.png)
passed before the user selected the midpoint direction.

To reopen:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_gripper_mapping.py \
    outputs/retargeting/gripper-index-20261027/mapping --port 8091
```

## Previous thumb-IP forward direction and opening refinement

The user requested thumb MCP→thumb IP as the forward direction and corrected
opening examples to **right frame 92 <~0.05** and **right frame 119 ~0.33**.
The [saved thumb-axis settings](../../../outputs/retargeting/gripper-refinement-20261027/mapping/settings.json) project that
forward direction perpendicular to the unchanged MCP closing axis. Grasp centers
remain the tip midpoint. The [mapping contract](../topics/direct-gripper-mapping.md)
owns the exact shared normalization and old-result compatibility.

| Right-hand anchor | Measured tip distance | Refined command |
| --- | ---: | ---: |
| Frame 92 | 2.107880 cm | 0.030 |
| Frame 119 | 12.549594 cm | 0.330 |

The 0.03 target satisfies the first example. The fitted closed/open thresholds
are 1.063709 / 35.869421 cm; fully open is extrapolated. Across the first region,
action spans **0–0.401897**, with 8 right samples clipped closed and none clipped
open. Both hands share the rule. No physical contact calibration is established.

[15 focused tests](../../../outputs/retargeting/gripper-refinement-20261027/tests-final.log)
pass, including analytic thumb-IP axes, missing/degenerate behavior, original
five-landmark compatibility, native MANO thumb-IP selection and both opening
anchors. The [296-frame audit](../../../outputs/retargeting/gripper-refinement-20261027/audit.json)
checks all **470** valid hand samples, proper rotations, expected forward axes,
unchanged centers/distances, all 11 original source fields, limits and ordinary
FK (maximum TCP discrepancy **2.78e−17**). Orientation changes by a median 8.55°
(maximum 22.98°) relative to the original mapping.

[Browser verification](../../../outputs/retargeting/gripper-refinement-20261027/browser.json)
checks a full playback loop, endpoints/gaps, both reference commands, six-landmark
overlays, saved settings and snapshot export, with no page errors. Visually
inspected the [nearly closed frame 92](../../../outputs/retargeting/gripper-refinement-20261027/right-frame-92.png),
[frame 119](../../../outputs/retargeting/gripper-refinement-20261027/right-frame-119.png),
[thumb-IP landmarks](../../../outputs/retargeting/gripper-refinement-20261027/right-landmarks-119.png)
and a missing-left-hand frame. The [reload check](../../../outputs/retargeting/gripper-refinement-20261027/reload.json)
starts/renders both the original five-landmark viewer and a new six-landmark
snapshot; temporary servers were stopped afterward. The first browser attempt
reached the previous viewer because it still owned port 8091; its
[failure log](../../../outputs/retargeting/gripper-refinement-20261027/browser.log)
is retained. Stopping that task-owned process and restarting the revised viewer
resolved it; the numerical checks were unaffected.

The previous thumb-axis viewer used the
[refined result](../../../outputs/retargeting/gripper-refinement-20261027/mapping/mapping_report.json)
and was reviewed at frame **119**. To reopen it:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_gripper_mapping.py \
    outputs/retargeting/gripper-refinement-20261027/mapping --port 8091
```

The original first-pass evidence below is historical and remains intact.

## Original first pass: input and direct mapping

Reused the [original iPhone reconstruction/alignment](retargeting-iphone.md#reconstruction-and-alignment),
without filtering or inference reruns, for frames **[0,296)** (0–9.8667 s at
30 FPS; last frame timestamp 9.8333 s). No base, arm or IK solution is consumed.
The [mapping report](../../../outputs/retargeting/gripper-mapping-20261027/mapping/mapping_report.json),
[arrays](../../../outputs/retargeting/gripper-mapping-20261027/mapping/gripper_mapping.npz),
[settings](../../../outputs/retargeting/gripper-mapping-20261027/mapping/settings.json),
and standalone [left](../../../outputs/retargeting/gripper-mapping-20261027/mapping/left_gripper.urdf)/[right](../../../outputs/retargeting/gripper-mapping-20261027/mapping/right_gripper.urdf)
URDFs reproduce the first-pass result.

| Measurement | Left | Right |
| --- | ---: | ---: |
| Eligible and mapped hand samples | 228 | 242 |
| Missing/infilled samples | 68 | 54 |
| Degenerate mapping frames | 0 | 0 |
| Minimum fingertip distance | 1.088 cm | 0.372 cm |
| Maximum fingertip distance | 15.052 cm | 12.947 cm |
| Samples clipped fully open at 10 cm | 68 | 40 |
| Samples clipped fully closed at 0 cm | 0 | 0 |

All 470 eligible hand samples map successfully. This establishes finite direct
poses, not grasp accuracy. The opening scale remains a guess, and the nominal
TCP stays fixed relative to the palm while the physical fingers curl.

## Numerical and entry-point verification

The [12 focused tests](../../../outputs/retargeting/gripper-mapping-20261027/tests-final.log)
pass. They cover analytic centers/axes, opposing left/right closing signs, proper
rotations under a rigid world-frame change, local correction direction, continuous
action/clipping, missing/degenerate isolation, invalid settings, and actual
standalone/full-model geometry agreement at five openings. Free TCP placement,
joint bounds and mimic propagation pass for both assets. The production CLI test
checks a nonzero frame-start interval, original MANO landmark selection, source
fields/timestamps, decoded RGB and snapshot reload/no-overwrite behavior.

The [full-region audit](../../../outputs/retargeting/gripper-mapping-20261027/audit-mapping.json)
checks all 296 frames and 470 eligible hand samples. All 11 selected source fields
are byte-preserved. The maximum ordinary-FK versus saved TCP transform discrepancy
is **2.78e−17**, palm discrepancy is zero, mimic-joint discrepancy is zero, and
rotation orthogonality error is **6.66e−16**. Every opening respects URDF bounds.
All 296 RGB frames decode; nine independent PNG decodes agree exactly with the
viewer RGB buffer. Video presentation timestamps differ from saved timestamps by
at most **3.34e−7 s**, consistent with ffprobe's decimal formatting.

Initial checks and fixes are preserved: the installed older FFmpeg requires
`-vsync 0`; local socket startup needed execution outside the sandbox. A strict
MANO bit-equality test differed by 7.45e−9 m across float32 batch sizes and was
replaced with a 1e−7 m tolerance. Browser automation timed out after playback;
an interaction trace isolated a fast numeric-fill operation that emitted no GUI
update, while normal keyboard entry worked. Acceptance now uses keyboard entry.
User scrubbing also pauses playback and the loop advances from the current frame.
Manual mode hides the frame slider because this Viser version does not disable
its companion numeric box when the slider is disabled.
See the [initial tests](../../../outputs/retargeting/gripper-mapping-20261027/tests-initial.log),
[initial viewer log](../../../outputs/retargeting/gripper-mapping-20261027/viewer.log),
and [browser failure](../../../outputs/retargeting/gripper-mapping-20261027/browser-frame-pause-failure.log).

## Interactive review

The [browser acceptance](../../../outputs/retargeting/gripper-mapping-20261027/browser/browser.json)
passes all 296 source frames and per-hand observation/action labels, playback
through the loop boundary, isolated closeups, visibility/opacity, local
translation/rotation and opening adjustments, snapshot export, invalid-setting
handling/reset, and independent manual pose/opening at 0, 0.5 and 1. No page
errors occurred. Capture uses software WebGL; the browser's renderer notice is
not an IK/geometry failure.

[Visual inspection](../../../outputs/retargeting/gripper-mapping-20261027/visual-review.json)
covers both original hand meshes and their landmarks, direct grippers, opening
extrema, missing-data transitions and endpoints. Examples: isolated
[left pinch](../../../outputs/retargeting/gripper-mapping-20261027/browser/left-closeup-frame-193.png),
[right pinch](../../../outputs/retargeting/gripper-mapping-20261027/browser/right-closeup-frame-127.png),
[open hands](../../../outputs/retargeting/gripper-mapping-20261027/browser/frame-0119.png),
and manual [closed](../../../outputs/retargeting/gripper-mapping-20261027/browser/manual-opening-0.png)/[open](../../../outputs/retargeting/gripper-mapping-20261027/browser/manual-opening-1.png)
grippers. The requested mapping is visible, but hand/gripper silhouettes and
physical contact centers do not coincide throughout articulation. No alignment
or opening refinement has been adopted; the baseline retains the 10 cm guess and
zero TCP corrections.

The [review-artifact audit](../../../outputs/retargeting/gripper-mapping-20261027/audit-review.json)
checks 16 RGB images actually displayed in the browser against their source frames
(maximum mean absolute pixel difference 2.95/255, from JPEG transport).
It also verifies all fields of the exported tuning snapshot, which changes only
opening distance to 0.20 m, left local X offset to 0.02 m and right local X rotation
to 15°. This is a control-validation example, not a tuning recommendation.
Both baseline and snapshot independently [reload successfully](../../../outputs/retargeting/gripper-mapping-20261027/browser/reload.json)
with their own saved settings; the viewer checks reconstructed landmarks and
recomputed mapping against saved outputs. The initial image audit required
converting browser-canvas RGBA to RGB; the corrected comparison passes.

The original baseline remains saved at the paths above; the live viewer now
shows revision 5 described earlier. Its first-pass review deliverable was complete,
with later user feedback addressed by the refinement. The temporary baseline
snapshot viewer was stopped after its reload verification.

To reopen the baseline:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_gripper_mapping.py \
    outputs/retargeting/gripper-mapping-20261027/mapping --port 8091
```

Thumb-IP/index-PIP comparison and later regions remain deferred. Physical metric
scale, gravity, contact accuracy, collision clearance and dynamic execution are
unverified. This review does not establish the roadmap simulation deliverable.
