# Egocentric video to robot trajectories

Turn one complete MP4 into synchronized hand trajectories, gravity-aligned
geometry, fixed-base robot regions and an annotated LeRobotDataset v3.1 episode.

The currently supported embodiment is **Purdue Alex with two SAKE EZGrippers**,
using the pinned robot model in [robot settings](configs/defaults/robot_workspace.json).
Each arm has 7 joints, with 2 additional neck joints and one opening command per
gripper. The exported 18-component action is ordered as left arm (7 joint angles),
right arm (7), neck (2), all in radians, then left/right gripper opening
(normalized: 0 closed, 1 open). The pipeline fits a fixed robot base for each
retained manipulation region; different regions can have different base placements.

The runner requires these inputs and destinations:

| Argument | Required value |
| --- | --- |
| `--video` | One local egocentric RGB `.mp4` showing the task and hands; the complete video is processed. |
| `--task` | A text description of the demonstrated task, used as the episode label and to guide language annotation. |
| `--dataset-root` | A local destination to create a dataset or append to an existing compatible project dataset. |
| `--run-directory` | A new directory for intermediate results, reports and logs. |

Video is prepared at 30 FPS with a mapping back to source frames and timestamps.
Use imagery suitable for pinhole processing; lens correction and conversion from
other video formats are outside the supported workflow. Dataset appends require
the same image dimensions, robot embodiment and feature contract.

Install the pinned models and isolated runtimes using the
[environment guide](environment/README.md). HaWoR and the annotation VLM use the
GPU sequentially. The processing runtime combines gravity estimation, retargeting
and visualization; dataset I/O uses the separate LeRobot interpreter.

```bash
pipeline/run.sh \
    --video data/source/demo.mp4 \
    --dataset-root data/lerobot/robot-pilot \
    --run-directory outputs/runs/demo-001 \
    --task "Pick up the cup and place it on the mat"
```

Use a new run directory for each attempt. The runner writes stage logs there,
appends exactly one full-video episode to a compatible dataset, starts the pinned
local VLM after trajectory processing, annotates the new episode, and stops the
server. To use an existing annotation server, pass both `--api-base` and `--model`.
`pipeline/run.sh --help` describes interpreter overrides and saved-stage reuse.

The dataset at `--dataset-root` contains one full-video episode with:

- Synchronized RGB, episode/source timestamps and left/right hand identity.
- Original HaWoR world-frame hand poses, MANO articulation/shape, per-hand
  canonical poses anchored to the first valid pose, and gravity-aligned Z-up
  hand/camera geometry. Positions use metres and angular values use radians; the
  reconstructed world's metric accuracy remains unverified.
- Robot joint/gripper actions, per-component validity masks, solver predictions,
  tracking errors, joint-limit and discrete self-collision results.
- Region boundaries and fixed-base transforms, source/camera metadata, detection
  confidence, and separate missing/infilled-hand provenance.
- Generated task plans and subtask annotations, with human review pending, plus
  a `DATA_CARD.md` describing sources and limitations.

A fresh run also saves these artifacts under `--run-directory`:

| Path | Output |
| --- | --- |
| `prepared/` | Prepared RGB video and source-frame mapping. |
| `hawor/` | Original world-frame trajectory, hand overlay video, run manifest and report. |
| `alignment/` | Z-up trajectories, gravity diagnostics and review figures. |
| `regions.json`, `mapping/` | Candidate manipulation intervals and hand-to-gripper targets/openings. |
| `robot/trajectory/` | Retargeted joint trajectories and per-region base fits. |
| `robot/score.json`, `robot/benchmark_frame_metrics.npz` | Tracking, joint-limit and self-collision evaluation. |
| `dataset_export.json`, `logs/` | Exported episode index and stage/server logs. |

The full timeline retains gaps and failed checks. Invalid action components are
NaN with false validity masks; no motion is synthesized between regions or across
base changes. Outputs support inspection and further simulation work; simulation
acceptance remains open, and these are not hardware execution commands.

Inputs, licensed model assets, environments and generated outputs stay local and
ignored.
