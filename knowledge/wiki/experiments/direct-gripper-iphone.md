# Direct gripper mapping — iPhone comparisons

Revision 10 fulfilled · 2026-10-28 · [Approved plan](../plans/milestone-3-direct-gripper-mapping.md).
The [mapping topic](../topics/direct-gripper-mapping.md) owns the geometry,
landmark, action and viewer contracts. All linked run artifacts are local-only.

## Full-video Configs 2/3/4 (2026-10-28)

The user requested an interpolated-thumb Config 4 and saved RGB overlay MP4s for
all three configurations over the complete prepared video. All outputs cover
**1,286 frames, 42.8667 seconds, 960×540, 30 fps**, with blue left/orange right
meshes at opacity 0.7. Existing viewers on 8091–8095 remain available.

| Configuration | Full RGB overlay | Encoding/projection validation |
| --- | --- | --- |
| 2: wrist anchor, fingertip forward | [MP4](../../../outputs/retargeting/gripper-full-20261028/config2-overlay.mp4) | [Report](../../../outputs/retargeting/gripper-full-20261028/config2-overlay.json) |
| 3: rotation blend | [MP4](../../../outputs/retargeting/gripper-full-20261028/config3-overlay.mp4) | [Report](../../../outputs/retargeting/gripper-full-20261028/config3-overlay.json) |
| 4: interpolated thumb plane | [MP4](../../../outputs/retargeting/gripper-full-20261028/config4-overlay.mp4) | [Report](../../../outputs/retargeting/gripper-full-20261028/config4-overlay.json) |

Config 4 uses `q=(1-w)*thumb_IP+w*thumb_MCP`, with the same absolute-roll
30°–45° smoothstep as Config 3. Jaw direction is **index MCP→q**, as requested;
its MCP endpoint has the original plane with Y/Z reversed. The
[mapping contract](../topics/direct-gripper-mapping.md#comparison-configurations)
owns the exact axes, FK placement and validity rules.

All three map **873 left + 929 right = 1,802 eligible hand samples**, without
unreachable opening or degenerate geometry. Original source fields/timestamps
and inter-configuration opening commands are unchanged. Config 4 uses pure IP
for **695 samples**, interpolates for **707**, and uses pure MCP for **400**.
Independent ordinary-FK anchor errors are below **1.15e−16 m** (Config 2 wrist)
and **4.40e−15 m** (Configs 3/4 tip midpoint); separation errors are below
1.80e−14 m. These measure internal geometric agreement, not physical accuracy.

The first 296 frames reproduce the previous Config 2/3 results within float32
MANO batch roundoff: landmark maximum difference 5.96e−8 m, transform element
maximum 9.38e−7, opening maximum 1.57e−7, roll maximum 8.25e−7 rad. They are not
claimed byte-identical after changing reconstruction batch size.

| Mapping | Largest left observed step | Largest right observed step |
| --- | --- | --- |
| Config 2 | 38.21° at frame 272 | 69.08° at frame 1265 |
| Config 3 | 41.98° at frame 272 | 56.29° at frame 736 |
| Config 4 | 42.11° at frame 272 | 56.29° at frame 736 |

No adjacent observed step exceeds 90°. These are pose-dependent mappings with
no temporal smoothing. Missing/infilled observations stay hidden; RGB continues
through every gap. Scene-depth occlusion, contact, physical scale and arm IK
remain unverified or deferred. No final default has been selected.

Local validation under `outputs/retargeting/gripper-full-20261028/`:

- [45 tests](../../../outputs/retargeting/gripper-full-20261028/tests.log) pass,
  including Config 4 endpoints/interior, directed axes, FK, rigid equivariance,
  invalid geometry/thresholds, CLI/snapshot and CV/OpenGL camera conventions.
- [Full-sample audit](../../../outputs/retargeting/gripper-full-20261028/audit.json)
  verifies source preservation, ordinary FK/joint limits, weights/axes, earlier
  results and aligned/native-world camera consistency (maximum 7.78e−16 m).
- Each video report above verifies every frame timestamp, dimensions, frame rate
  and complete decoding. Render/encode/verification times were **36.24 / 36.22 /
  35.24 seconds** for Configs 2/3/4 in this execution; Configs 2/3 ran concurrently,
  so these are not isolated performance benchmarks.
- [Visual inspection](../../../outputs/retargeting/gripper-full-20261028/visual-review.json)
  covers open/pinch, object interaction and missing-hand frames 92/119/350/600/
  900/1200/1285. Comparison sheets: [open](../../../outputs/retargeting/gripper-full-20261028/review-frame-119.jpg),
  [pinch](../../../outputs/retargeting/gripper-full-20261028/review-frame-92.jpg),
  [later interaction](../../../outputs/retargeting/gripper-full-20261028/review-frame-1200.jpg).
- [Browser checks](../../../outputs/retargeting/gripper-full-20261028/browser.json)
  verify Config 4 construction/threshold controls, invalid-setting rejection,
  reset and a full snapshot. [Snapshot reload](../../../outputs/retargeting/gripper-full-20261028/snapshot-reload.json)
  verifies all fields at tuned 60°/70° thresholds. Temporary validation viewers
  were stopped; original sessions were checked without changing controls.

## Fingertip forward and roll blend (2026-10-28)

The user requested wrist→fingertip-midpoint forward for Config 2 and a roll-driven
transition from Config 1 when open to the original plane when pinching. The
original directed endpoint rotations differed by 161–180°. The user explicitly
approved aligning jaw directions inside Config 3; its Config 1 endpoint reverses
+Y/+Z, retaining +X. This is a different directed endpoint orientation, with the
same midpoint/opening, while standalone Config 1 remains unchanged. The
[contract](../topics/direct-gripper-mapping.md#comparison-configurations) defines
the ideal-open reference, rotation interpolation and missing-data behavior.

| New viewer | Behavior | Maximum ordinary-FK anchor error |
| --- | --- | --- |
| [Updated Config 2 :8094](http://localhost:8094) | Rear palm at wrist, forward wrist→fingertip midpoint | 1.12e−16 m |
| [Config 3 :8095](http://localhost:8095) | Aligned Config 1→original plane, fingertip-midpoint placement | 1.29e−15 m |

Each result maps **470/470 eligible samples** over **296 frames**, with original
source fields/timestamps and opening commands preserved exactly. Nine historical
mappings reproduce unchanged. Earlier viewers on **8091–8093** remain available.
The new viewers were verified at frame 119 with both hands visible; default method
selection remains pending.

Config 3 uses original weight 0 for **|roll|≤30°**, 1 for **|roll|≥45°**, and
smoothstep between; both thresholds are adjustable in **Mapping adjustments**.
The roll is measured using updated Config 2, not the earlier MCP-forward axis.

| Frame | Left / right roll | Left / right original weight |
| --- | --- | --- |
| 92, pinch example | +45.80° / −41.39° | 100% / 85.44% |
| 119, open example | +14.41° / −29.36° | 0% / 0% |

Across both hands, **127 samples** use aligned Config 1 fully, **108** lie in the
transition, and **235** use the original fully. Aligned endpoint rotation angles
range **20.63–39.84°** (median 32.14°). Consecutive observed-frame rotation changes
never exceed 90°. Config 3's maximum is **41.98° left at frame 272**, versus
39.16° original / 40.97° Config 1 at the same frame; right maximum is 20.35°.
These are descriptive motion metrics, not a temporal-smoothing guarantee or
physical accuracy gate. [Motion comparison](../../../outputs/retargeting/gripper-blend-20261028/motion-comparison.json).

Local evidence under `outputs/retargeting/gripper-blend-20261028/`:

- [41 tests](../../../outputs/retargeting/gripper-blend-20261028/tests.log) pass:
  both forward rules, wrist/center FK, 0/±90° roll, blend endpoints/interior,
  equivariance, invalid geometry/thresholds and CLI/snapshot paths.
- [All-sample audit](../../../outputs/retargeting/gripper-blend-20261028/audit.json)
  independently verifies forward/roll, SciPy SLERP agreement, midpoint/wrist,
  opening, joint bounds, source preservation and historical reproduction.
- [Browser check](../../../outputs/retargeting/gripper-blend-20261028/browser.json)
  verifies playback, frames 0/33/92/119/245/295, closeups/manual mode, threshold
  edits (60°/70°), invalid-threshold rejection, reset to 30°/45° and snapshots.
  No page errors. [Reloads](../../../outputs/retargeting/gripper-blend-20261028/reload.json)
  verify both new modes, both threshold snapshots and earlier viewer formats.
- [Visual review](../../../outputs/retargeting/gripper-blend-20261028/visual-review.json)
  covers both-hand pinch examples and right open-hand comparisons:
  [updated Config 2](../../../outputs/retargeting/gripper-blend-20261028/config2-tips-right-119.png),
  [Config 3 open](../../../outputs/retargeting/gripper-blend-20261028/config3-right-119.png),
  [Config 3 pinch](../../../outputs/retargeting/gripper-blend-20261028/config3-frame-92.png).

Saved reports: [updated Config 2](../../../outputs/retargeting/gripper-blend-20261028/config2-tips/mapping_report.json),
[Config 3](../../../outputs/retargeting/gripper-blend-20261028/config3/mapping_report.json).
Physical contact/scale, collision/dynamics, later regions and arm IK remain
unverified or deferred. This completes the requested comparison trial.

## Two-method comparison (2026-10-28)

The user requested two additional configurations while retaining the original
window. Both reuse frames **[0,296)** and unchanged observed MANO estimates and
FK opening; there was no reconstruction, filtering or arm-IK rerun. The user
clarified Config 2's anchor as the rear palm origin, and zero roll as an ideal
open hand carried by the current wrist orientation. The
[mapping contract](../topics/direct-gripper-mapping.md#comparison-configurations)
defines axes, sign, reference transport and validity.

| Viewer | Configuration | Anchor | Maximum audited anchor error |
| --- | --- | --- | --- |
| [Current baseline :8091](http://localhost:8091) | Revision-7 MCP plane | Fingertip midpoint | Prior evidence below |
| [Config 1 :8092](http://localhost:8092) | Index MCP/index PIP/thumb IP plane; jaw index MCP→thumb IP | Fingertip midpoint | 1.32e−15 m |
| [Config 2 :8093](http://localhost:8093) | Wrist→MCP-midpoint forward; MCP-line roll | Rear palm at hand wrist | 1.12e−16 m |

Both new configurations map **470/470 eligible hand samples** (228 left / 242
right), with no degenerate/unreachable samples. Original selected source arrays,
timestamps and actions match the baseline exactly. Right frames 92/119 retain
commands **0.063020 / 0.327544**. Config 2's roll ranges are **−3.76° to +58.15°**
left and **−53.23° to +5.22°** right; right 92/119 are **−34.83° / −23.71°**.
These are measured angles, without forcing pinches to 90°.

Assigned per-tip offsets (median / maximum) are **27.68 / 149.50 mm** for
Config 1 and **50.74 / 90.50 mm** for Config 2. Config 1 reverses the directed
jaw relative to the baseline but keeps finger-2→thumb/finger-1→index diagnostic
labels; these numbers are not minimum distances over interchangeable tips.
Config 2 fixes the wrist instead of the fingertip midpoint. Neither offset
summary is a common-objective ranking or a physical contact measurement.

Local evidence under `outputs/retargeting/gripper-comparison-20261028/`:

- [34 focused tests](../../../outputs/retargeting/gripper-comparison-20261028/tests.log)
  pass, including both CLI/snapshot paths, plane sign, real FK, zero/±90° roll,
  shortest-forward transport, rigid-frame equivariance and invalid inputs.
- [All-sample audit](../../../outputs/retargeting/gripper-comparison-20261028/audit.json)
  passes axes, proper rotations, ordinary FK, anchors, opening, joint bounds,
  source preservation and all seven earlier mappings recomputed unchanged.
- [Browser check](../../../outputs/retargeting/gripper-comparison-20261028/browser.json)
  passes 11.5 s playback per viewer (including loop), frames 0/33/92/119/245/295,
  both closeups, manual-mode restoration and snapshots, with no page errors.
  The original viewer is reachable and its controls were not changed.
- [Reload check](../../../outputs/retargeting/gripper-comparison-20261028/reload.json)
  passes both new snapshots and the legacy, exact-tip and baseline plane modes.
- [Visual inspection](../../../outputs/retargeting/gripper-comparison-20261028/visual-review.json)
  covers both sides at frame 119, both methods at frame 92 and Config 2's
  missing-left endpoint. [Config 1](../../../outputs/retargeting/gripper-comparison-20261028/config1-right-119.png)
  and [Config 2](../../../outputs/retargeting/gripper-comparison-20261028/config2-right-119.png)
  show their different anchors, orientations and diagnostics.

Both new viewers are left at **119** with both hands visible. Saved results are
[Config 1](../../../outputs/retargeting/gripper-comparison-20261028/config1/mapping_report.json)
and [Config 2](../../../outputs/retargeting/gripper-comparison-20261028/config2/mapping_report.json).
The default remains revision 7 pending the user's selection. The accepted result
is this comparison; physical contact, collisions/dynamics, later regions and
integration with arm IK remain unverified or deferred.

## MCP/index-PIP plane orientation

Revision 7 follows the user's three-point construction: thumb MCP, index MCP and
index PIP define the orientation plane; jaw +Y is thumb→index MCP, forward +X is
in-plane and perpendicular toward PIP, and +Z = +X × +Y. The gripper tip midpoint
stays at the human fingertip midpoint. Geometry-derived opening is unchanged;
individual tip correspondence is superseded by the new jaw direction. See the
[mapping contract](../topics/direct-gripper-mapping.md) for the transform.
The [preserved baseline viewer](http://localhost:8091) loads the
[plane result](../../../outputs/retargeting/gripper-mcp-plane-20261027/mapping/mapping_report.json).

[28 focused tests](../../../outputs/retargeting/gripper-mcp-plane-20261027/tests.log)
pass, including analytic mirrored plane axes, forward sign, real-FK midpoint and
jaw placement, frame equivariance, degenerate/missing/unreachable samples, and
production CLI/snapshots for all three mapping modes. The
[296-frame audit](../../../outputs/retargeting/gripper-mcp-plane-20261027/audit.json)
passes for **470 eligible samples** (228 left, 242 right): no degenerate or
unreachable observations, maximum actual FK midpoint error **1.30e−15 m**,
proper rotations, original fields/landmarks byte-preserved, unchanged actions and
all six historical runs reproduced.

Right frames **92 / 119** retain commands **0.063020 / 0.327544**. Their individual
tip offsets are **11.90 / 5.53 mm** respectively. Across both hands, median offset
is **10.18 mm**, maximum **36.34 mm**. These are expected consequences of the MCP
jaw constraint, not midpoint-placement errors.

[Browser verification](../../../outputs/retargeting/gripper-mcp-plane-20261027/browser.json)
passes full playback/loop, source endpoints/gaps, closeups, separate midpoint/tip
readouts, snapshots and manual-mode restoration with no page errors. Inspected
[right frame 92](../../../outputs/retargeting/gripper-mcp-plane-20261027/right-frame-92.png),
[right frame 119](../../../outputs/retargeting/gripper-mcp-plane-20261027/right-frame-119.png),
[the construction triangle](../../../outputs/retargeting/gripper-mcp-plane-20261027/right-landmarks-119.png)
and [left frame 119](../../../outputs/retargeting/gripper-mcp-plane-20261027/left-frame-119.png).
[Reload checks](../../../outputs/retargeting/gripper-mcp-plane-20261027/reload.json)
verify the original viewer, exact-tip viewer and new plane snapshot, including
triangle vertices, displayed forward segment and midpoint. At the revision-7
handoff the viewer was paused at **119**, showing both hands. Physical contact, scale, collisions and
dynamics remain unverified.

To reopen:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_gripper_mapping.py \
    outputs/retargeting/gripper-mcp-plane-20261027/mapping --port 8091
```

## Previous exact fingertip correspondence

Revision 6 follows the user's request to place both gripper tips on the human
fingertips and resolve the remaining rotation using true wrist→thumb MCP.
Opening is solved from real gripper FK; the earlier empirical normalization is
superseded for this trial. See the [mapping contract](../topics/direct-gripper-mapping.md)
for marker definitions, transform construction and reachable-branch selection.
The previous viewer loaded the
[tip-matching result](../../../outputs/retargeting/gripper-tip-match-20261027/mapping/mapping_report.json).

[25 focused tests](../../../outputs/retargeting/gripper-tip-match-20261027/tests.log)
pass, including real FK correspondence, twist, frame equivariance, missing and
unreachable cases, a separation near maximum opening, production CLI, snapshots
and legacy mappings. The [full-region audit](../../../outputs/retargeting/gripper-tip-match-20261027/audit.json)
checks **296 frames / 470 eligible hand samples** (228 left, 242 right). Every
eligible sample maps; none is unreachable or degenerate. Maximum actual FK tip
error is **5.25e−15 m**. Source fields and landmarks are byte-preserved. Rotations,
axis signs, joint bounds and mimic coupling pass; all five previous mappings
recompute unchanged.

The nominal reachable separation is **0–28.0114 cm**. Observed commands span
**0.012973–0.389845**. Right frame **92**, separation 2.108 cm, now commands
**0.063020**; right frame **119**, separation 12.550 cm, commands **0.327544**.
These are geometry-derived commands, so the old frame-92 <0.05 anchor is no longer
imposed. The model is not scaled or shifted away from either matched tip.

[Browser verification](../../../outputs/retargeting/gripper-tip-match-20261027/browser.json)
passes playback through the interval and loop, representative frames/gaps,
closeups, visible residuals, hidden legacy adjustments, snapshot saving and manual
mode restoration, without page errors. Inspected
[right frame 92](../../../outputs/retargeting/gripper-tip-match-20261027/right-frame-92.png),
[right frame 119](../../../outputs/retargeting/gripper-tip-match-20261027/right-frame-119.png)
and [left frame 119](../../../outputs/retargeting/gripper-tip-match-20261027/left-frame-119.png).
[Reload checks](../../../outputs/retargeting/gripper-tip-match-20261027/reload.json)
verify the original five-landmark viewer and new snapshot, including displayed
marker positions and the true-wrist construction vector. That viewer was reviewed at **119**, showing both hands. Physical scale/contact, collisions and
dynamics remain unverified; this is geometric correspondence between mesh markers.

To reopen:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_gripper_mapping.py \
    outputs/retargeting/gripper-tip-match-20261027/mapping --port 8091
```

## Previous thumbward wrist shift with forward priority

Revision 5 shifts the wrist construction point **2.5 cm toward the thumb** along
index-MCP→thumb-MCP, then aims at the MCP midpoint. The user explicitly selected
preserving forward and making closing perpendicular. The shared implementation
and compatibility rules are in the [mapping contract](../topics/direct-gripper-mapping.md).
The previous viewer loaded the
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
direction. That reviewed baseline used **0.025 m**, paused at frame **119**;
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
