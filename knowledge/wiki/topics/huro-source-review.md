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

The standard HaWoR video demo differs: at our pinned upstream revision
[`66c7d410`](https://github.com/ThunderVVV/HaWoR/blob/66c7d4108d58a716deccd192cb7645170cdc7bd7/lib/pipeline/tools.py),
it loads an Ultralytics YOLO detector. The
[HaWoR README](https://github.com/ThunderVVV/HaWoR/blob/66c7d4108d58a716deccd192cb7645170cdc7bd7/README.md)
downloads that checkpoint from WiLoR. The demo passes confidence 0.2, versus
HuRo's 0.5; scores across these different detectors are not calibrated to a shared
accuracy level. HaWoR uses persistent Ultralytics tracking and majority hand-side
assignment, while HuRo explicitly refines 100DoH detections with BoT-SORT.
This establishes a different detector, not superior detection accuracy.

[Stage 4](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/stage4_annot_hand.py)
rejects uncertain sides and excessive crop overflow. Its default `gap_fill=3`
tolerates three consecutive missing frames (0.1 seconds at assumed 30 FPS), then
ends that hand's sequence. Despite the option name, missing images/boxes are not
inserted. HaWoR receives windows of 16 accepted observations with stride 12;
windows spanning more than 18 frame-index steps are skipped. Short sequences
without 16 observations produce no reconstruction. Overlapping estimates are
averaged, using hemisphere-aligned quaternions for rotations. Invalid projected
keypoints become null.

For example, accepted frames 100–102 and 105 onward remain one reconstruction
sequence when only 103–104 are missing. No boxes or poses are generated for
103–104 by this stage. Four consecutive misses end the side's sequence. The
16-observation window also permits at most three missing timeline slots in total
(16 observations within 19 raw frames), even if no individual gap exceeds three.
The helper receives the observed images consecutively and maps outputs back to
their original frame IDs; skipped time is not explicitly supplied to the model.
BoT-SORT's separate 30-frame track buffer supports association, not 30 frames of
reconstructed motion. Stage 6's later grouping needs only one reconstructed hand,
so a long absence of one hand need not split an episode while the other remains.

## Motion infiller

The released stage runner uses the camera-frame reconstruction helper added by
the [HaWoR patch](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/submodules_patches/hawor.patch).
Stage 4 does not call `hawor_infiller`. The patch retains the upstream demo's
infiller call, adding timing there, and does not repair the infiller algorithm.
Thus the inspected workflow bypasses that component; it is not evidence of a fix
for our baseline's infiller failures.

In the original
[HaWoR demo path](https://github.com/ThunderVVV/HaWoR/blob/66c7d4108d58a716deccd192cb7645170cdc7bd7/scripts/scripts_test_video/hawor_video.py),
tracks contain detected entries only. Its bbox-interpolation call therefore does
not insert missing frames; reconstruction chunks split at frame-index gaps.
The subsequent learned world-motion infiller uses 120-frame context windows,
canonicalization, and interpolation before transformer prediction, replacing
missing poses. The context length is not a demonstrated safe gap-duration limit.

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

## Comparison with LeRobot annotation

The official [LeRobot annotation CLI](https://huggingface.co/docs/lerobot/en/annotation_pipeline)
also uses a configurable VLM backend, currently defaulting to Qwen3.6-27B. This
comparison concerns that CLI, not the separately named annotation UI repository.
Inspected configuration, plan generator, validator, and writer files at
[`9a6bb610`](https://github.com/huggingface/lerobot/tree/9a6bb61043bac8c14353fcb6ea513b7473c118e3/src/lerobot/annotations/steerable_pipeline)
matched their pinned Git blob hashes; no annotation run was performed.

| Dimension | HuRo custom captioning | LeRobot annotation CLI |
| --- | --- | --- |
| Output | Left/right/bimanual captions, merged to one instruction per accepted window | Timed subtasks and plans in LeRobot v3.1 language columns |
| Visual input | 10 FPS video with wrist overlays; overlapping windows up to 7 seconds | Timestamped frame grids at configurable 2 FPS by default; longer episodes windowed automatically |
| Quality approach | Multiple samples, text and video verification, field selection, rejection traces | Describe then segment; optional span relabeling; structural/timing validator |
| Coverage tradeoff | Drops unsuitable windows; useful motion may be excluded | Stitches surviving spans over the whole episode; idle intervals can inherit action labels |
| Integration/cost tradeoff | Hand attribution already designed in, but custom output adaptation and maintenance; repeated checks/overlap add work | Direct dataset integration and configurable backend; serving resources and annotation-preservation behavior still need validation |

Source detail: the
[plan generator](https://github.com/huggingface/lerobot/blob/9a6bb61043bac8c14353fcb6ea513b7473c118e3/src/lerobot/annotations/steerable_pipeline/modules/plan_subtasks_memory.py)
snaps boundaries to frames and extends the first/last spans to episode edges,
closing intervening gaps. Frame alignment does not prove semantic boundary accuracy.
The [validator](https://github.com/huggingface/lerobot/blob/9a6bb61043bac8c14353fcb6ea513b7473c118e3/src/lerobot/annotations/steerable_pipeline/validator.py)
checks structure and consistency, not whether an action is visible. Its
[writer](https://github.com/huggingface/lerobot/blob/9a6bb61043bac8c14353fcb6ea513b7473c118e3/src/lerobot/annotations/steerable_pipeline/writer.py)
rebuilds language columns from staging and replaces shards; preservation of prior
annotations on partial reruns remains a required pilot check.

Inference for our pilot: LeRobot's timed subtasks and native v3.1 integration fit
the deliverable better. HuRo's hand-specific prompts and visual rejection checks
are candidates for a later measured improvement, not grounds to replace the
planned workflow. Neither approach has established annotation accuracy on our
videos. Both can run locally; no privacy advantage is inherent to HuRo.
For plans/subtasks only, the inspected
[configuration](https://github.com/huggingface/lerobot/blob/9a6bb61043bac8c14353fcb6ea513b7473c118e3/src/lerobot/annotations/steerable_pipeline/config.py)
also requires `plan.emit_memory=false` and `plan.n_task_rephrasings=0` alongside
disabling interjections and VQA (task-axis augmentation defaults off).

## Project implication

HuRo offers examples of explicit gap limits, validity-aware retargeting, and
filtered segment captioning. Static inspection does not establish better detection,
accurate gap recovery, or annotation quality on our clips. The
[Milestone 2 draft](../plans/milestone-2-lerobot-pilot.md) remains unapproved and
continues to exclude detector/infiller changes; no implementation scope changed.
