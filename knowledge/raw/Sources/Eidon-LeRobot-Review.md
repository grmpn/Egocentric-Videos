# Eidon and LeRobot — pilot planning sources

Reviewed 2026-09-22 for [Milestone 2 planning](../../wiki/plans/milestone-2-lerobot-pilot.md).
These are source claims and planning implications, not executed validation.

## Eidon video selection

The [Eidon organization](https://huggingface.co/eidon-ai) links the
[`tracker-pov` video dataset](https://huggingface.co/datasets/eidon-ai/tracker-pov),
its separate IMU dataset, and an additional video-only storage bucket. The
[dataset card](https://huggingface.co/datasets/eidon-ai/tracker-pov/blob/47c55ccc6d0308894ab482009c6fa91569057a08/README.md)
describes ordinary egocentric household recordings, MP4 video from 1080p to 4K,
mostly 30 FPS, and per-recording metadata for task, contributor, image dimensions,
timing, and automated quality scores. Its declared license is CC-BY-4.0.

For the pilot, `tracker-pov` provides a concrete, revisioned source. Select from
metadata and retrieve individual MP4s rather than the complete corpus. Record
source revision, recording/contributor IDs, task, attribution, hashes, and any
trim interval. Quality scores guide selection; they do not establish HaWoR success.
The video-only bucket is an alternative source, not a required second ingestion path.

The user identifies Eidon footage as undistorted pinhole input. The inspected card
does not state a pinhole calibration or undistortion guarantee, and describes the
video as unprocessed. This neither proves nor disproves suitable lens geometry.
Selected-clip geometry and intrinsics remain unverified: retain available camera
evidence and distinguish measured values from assumptions before processing.
Visual inspection alone cannot certify calibration. Inputs requiring lens
correction remain outside Milestone 2; this uncertainty does not authorize adding
an undistortion pipeline. No videos or sensor streams were downloaded in planning.

## Dataset and annotation compatibility

The official [annotation workflow](https://huggingface.co/docs/lerobot/en/annotation_pipeline)
documents LeRobotDataset v3.1, local dataset roots, and plan/subtask generation.
Interjections and VQA have independent disable flags. The current workflow writes
language columns into dataset Parquet files; actual append/annotation preservation
and reload behavior must be tested with the selected dependency revision.

The user initially requested v2, then explicitly selected **v3.1 for direct
annotation** on 2026-09-22 after the compatibility question. There is no v2 export
or conversion requirement in the revised milestone. Dataset destination means a
local dataset root directory, not a single file.

The [annotation entry point](https://github.com/huggingface/lerobot/blob/9a6bb61043bac8c14353fcb6ea513b7473c118e3/src/lerobot/scripts/lerobot_annotate.py)
was inspected at the contemporaneous upstream revision. A separate
[`huggingface/lerobot-annotate` UI repository](https://github.com/huggingface/lerobot-annotate)
also exists; sharing a name does not establish interchangeable behavior.
The milestone targets the official VLM annotation command documented above.

Planning did not install LeRobot, select or run a VLM, or prove feasibility on the
local GPU. Backend choice and runtime/resource evidence are implementation work;
retaining the working HaWoR environment is an essential compatibility constraint.
