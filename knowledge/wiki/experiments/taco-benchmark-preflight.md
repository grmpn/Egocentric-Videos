# TACO benchmark: source and feasibility review

Static inspection on 2026-11-24 for the
[draft benchmark plan](../plans/taco-hand-trajectory-benchmark.md).
No TACO inference, dataset download, benchmark implementation or accuracy
measurement has been performed. These are source findings and implementation
prerequisites, not acceptance evidence for the proposed benchmark.

## Available data and reference geometry

The [official TACO instructions](https://github.com/leolyliu/TACO-Instructions)
link the V1 release on Dropbox and
[the author's Hugging Face dataset](https://huggingface.co/datasets/leolyliu/TACO).
The instructions distinguish 2,317 total sequences from 2,212 with egocentric
modalities, and provide availability and train/test lists. Select from their
intersection; verify actual files before freezing the five clips. The Hugging
Face listing was not retrievable through the web tool in this session; no file
availability or archive size was verified.

The [paper, section 3.1](https://arxiv.org/html/2401.08399v2#S3.SS1) states that
the head-mounted Realsense L515 and the other cameras run at 30 Hz, and the L515
motion is tracked by optical mocap. Section 8.2 describes nearest-timestamp
synchronization with a maximum difference of 17 ms. The hand reference is a
multi-view MANO fit, not independently measured joint truth; report that limit.

The official
[egocentric projection code](https://github.com/leolyliu/TACO-Instructions/blob/master/dataset_utils/project_pose_to_egocentric_view.py)
loads `Egocentric_Camera_Parameters/<triplet>/<sequence>/egocentric_intrinsic.txt`
and `egocentric_frame_extrinsic.npy`. The latter is explicitly **world-to-camera**,
shape `[frames, 4, 4]`; invert it for camera-to-world composition. The code rejects
RGB/pose frame-count mismatches. Its
[hand loader](https://github.com/leolyliu/TACO-Instructions/blob/master/dataset_utils/hand_pose_loader.py)
uses wrist-centered MANO, converts mesh/joint output from millimetres to metres,
then adds `hand_trans`, returning 21 joints. Joint ordering, root rotations,
timestamp mapping, gravity direction and RGB reprojection still need validation
on actual selected records. The
[world-axis visualizations](https://github.com/leolyliu/TACO-Instructions/tree/master/assets/world_coordinate_system_visualizations)
are a reference for checking the released world convention, not a measured
gravity calibration by themselves.

At 30 FPS, 150 frames cover 5 seconds of video; first-to-last sample separation
is 149/30 seconds. With fully valid data, the requested 0.5/2/4-second offsets
provide **135/90/30 forward pairs per hand**, respectively. One-second scale
ratios have 120 pairs per hand. Missing samples reduce these counts. Actual
timestamps must confirm this arithmetic; a short clip provides limited evidence
about long-term drift. Camera motion sufficiency remains unmeasured.

## Method prerequisites

**Base HaWoR.** The installed upstream checkout is clean at
`66c7d4108d58a716deccd192cb7645170cdc7bd7`. The maintained
[pipeline](../topics/hawor-pipeline.md) preserves its native world result and
infilling. The fulfilled iPhone comparison instead shared camera-relative hands
between camera backends and excluded world infilling; its outputs and assembled
timings cannot serve as this full-method benchmark.

**StableHand.** The current
[README](https://github.com/huajian-zeng/stablehand/blob/main/README.md)
releases inference, checkpoints and prepared HOT3D/ARCTIC caches, while listing
data preprocessing as unfinished. The
[enhanced release](https://github.com/huajian-zeng/stablehand/blob/main/docs/enhanced_version.md)
uses WiLoR and VGGT-Omega, differing from the paper's Depth Anything 3 version.
The draft selects the enhanced HOT3D checkpoint explicitly because this is an
egocentric evaluation; do not select a checkpoint using TACO scores.

Static inspection of
[inference](https://github.com/huajian-zeng/stablehand/blob/main/sample/infer_clips.py)
and the [clip loader](https://github.com/huajian-zeng/stablehand/blob/main/data_loaders/clip_dataset.py)
shows cached WiLoR proposals, visual/scene features, estimated camera geometry
and depth signals. `--rgb_dir` supplies visualization images, not a complete RGB
preprocessing path. The evaluation loader also reads reference hand shape and
camera fields. A TACO adapter must audit which fields affect prediction, use
estimated inputs, and keep GT exclusively on the evaluation side. Existing
benchmark-cache inference does not establish new-video support or end-to-end
speed. Resolve and validate faithful preprocessing before claiming this method
has run; an unavailable stage must remain unavailable, not a guessed number.

**HandFlow.** Its
[README](https://github.com/mxxu00/HandFlow/blob/main/README.md)
documents new-video inference with a separate ViPE process/environment for moving
cameras, HaMeR features and a WiLoR detector. The release describes a right-hand
model and requires mirroring left-hand videos. The
[demo](https://github.com/mxxu00/HandFlow/blob/main/scripts/demo.py)
supports saved NPZ output and a hand-side argument, but this does not establish
complete bimanual behavior. Verify two stable hand identities, inverse mirroring
of geometry/intrinsics, wrist rotations, shared camera consistency and all extra
runtime before scoring both hands.

## Reuse and measurement

The existing trajectory evaluation, gravity alignment, plotting and resource
monitoring provide reusable pieces. Existing HaWoR stage timings use received
stdout markers, which can charge initialization to adjacent stages; the runner
also groups SLAM and metric scaling. Instrument actual boundaries where feasible
and retain explicitly combined stages otherwise. CUDA work must complete before
its timing boundary, and subprocess work belongs in end-to-end elapsed time.
Do not present a cached refinement time as complete pipeline FPS.

The proposed RPE follows the transform ordering and translational RMSE in
[Sturm et al., equations 1–2](https://cvg.cit.tum.de/_media/spezial/bib/sturm12iros.pdf),
applied to world-from-wrist poses with a consistent wrist-frame convention.
Endpoint-displacement ratios and SE(3) RPE measure different properties; do not
replace RPE with a difference of path lengths. The plan's 10 mm scale-denominator
cutoff is a proposed numerical/low-motion guard, not a measured TACO accuracy
bound. Retain the rejected-pair count.

The workspace contains HaWoR and prior comparison inputs, but no TACO files or
StableHand/HandFlow checkout was found in the project data/source and external
locations inspected. The local GPU is an RTX 4090 with 24,564 MiB reported memory;
2.7 TiB was free on the workspace filesystem. Sandboxed `nvidia-smi` failed;
the authorized outside-sandbox retry succeeded. This verifies hardware visibility,
not model compatibility or available peak memory during a future run.

Next action: approve or revise the short plan, then validate TACO reference
geometry and method preprocessing before the timed runs.
