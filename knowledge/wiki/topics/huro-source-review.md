# HuRo source review: gaps, infilling, and language

Static inspection on 2026-09-22 of HuRo revision
[`aeaae17f0fd51cc325b030bbef79ceb68a25199e`](https://github.com/3587jjh/HuRo/tree/aeaae17f0fd51cc325b030bbef79ceb68a25199e).
Sixteen downloaded source files matched the revision's Git blob hashes. No HuRo
models, dependencies, or inference were run. This extends the earlier
[bounded reference review](../../raw/Sources/HuRo-Review.md); raw notes remain
historical. Findings describe external code, not implemented project behavior.

## Detection gaps

[Stage 2](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/stage2_annot_contact.py)
uses 100DoH Faster R-CNN with a default hand confidence threshold of 0.5.
[Stage 3](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/stage3_annot_contact_refine.py)
uses BoT-SORT to assign a consistent left/right label from confidence-weighted
track evidence and resolve conflicts. It writes refined observed detections;
tracking does not itself create missing hand observations.

[Stage 4](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/stage4_annot_hand.py)
rejects uncertain sides and excessive crop overflow. Its default `gap_fill=3`
tolerates three consecutive missing frames (0.1 seconds at assumed 30 FPS), then
ends that hand's sequence. Despite the option name, missing images/boxes are not
inserted. HaWoR receives windows of 16 accepted observations with stride 12;
windows spanning more than 18 frame-index steps are skipped. Short sequences
without 16 observations produce no reconstruction. Overlapping estimates are
averaged, using hemisphere-aligned quaternions for rotations. Invalid projected
keypoints become null.

## Motion infiller

The released stage runner uses the camera-frame reconstruction helper added by
the [HaWoR patch](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/submodules_patches/hawor.patch).
Stage 4 does not call `hawor_infiller`. The patch retains the upstream demo's
infiller call, adding timing there, and does not repair the infiller algorithm.
Thus the inspected workflow bypasses that component; it is not evidence of a fix
for our baseline's infiller failures.

[Retargeting stage 8](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/stage8_robot_retarget.py)
linearly fills interior world-keypoint gaps, holds endpoint values at boundaries,
and applies validity-aware Gaussian smoothing. This filler has no maximum gap
length. Original invalid frames retain zero alignment weight; speed/acceleration
outliers receive reduced weights. The
[robot solver](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/retargeting/retargeter.py)
uses temporal joint smoothness and rest/limit costs across missing observations.
Stage 8 records hand validity masks and pins a wholly unobserved side to its home
pose. This produces robot motion without establishing the missing human motion's
accuracy; final dataset mask propagation was not established by this review.

## Language annotation

[Stage 6](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/stage6_annot_narr.py)
groups frames with camera poses and at least one reconstructed hand, bridging up
to three missing frames. Defaults are a 50-frame minimum, 210-frame windows
(7 seconds), 50% overlap, and VLM sampling every third frame (10 FPS).
These are geometric/window boundaries, not individually timed semantic subtasks.
Wrist overlays distinguish hands; short gaps are interpolated in world coordinates
for visualization and drawn dashed, while longer gaps break the trail. This
overlay interpolation does not replace missing hand annotations.

The [captioning code](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/captioning/caption.py)
uses Qwen3.5-9B and, from stage 6's defaults, four candidate samples. It requests
left, right, and bimanual action phrases, with `n/a` for unsupported fields.
It applies deterministic format checks, a text-only label-quality check, a
video-grounding check, field-survival thresholds, and final cross-field checks.
The survival thresholds count non-null fields, not agreement on identical action
meaning. Verifier parse failures keep candidates, so verification is not a
guarantee. Rejection and selection traces are saved.

[Instruction merging](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/common/io.py)
prefers a bimanual caption, otherwise the longer left/right string (right on a
tie). One instruction covers the segment; uncaptionable windows are dropped.
The inspected path uses custom captioning rather than `lerobot-annotate`.

## Project implication

HuRo offers examples of explicit gap limits, validity-aware retargeting, and
filtered segment captioning. Static inspection does not establish better detection,
accurate gap recovery, or annotation quality on our clips. The
[Milestone 2 draft](../plans/milestone-2-lerobot-pilot.md) remains unapproved and
continues to exclude detector/infiller changes; no implementation scope changed.
