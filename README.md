# Egocentric video to robot trajectories

Turn one complete MP4 into synchronized hand trajectories, gravity-aligned
geometry, fixed-base robot regions and an annotated LeRobotDataset v3.1 episode.
The pipeline preserves gaps, original hand estimates and failed tracking/limit/
collision checks. Outputs support inspection and further simulation work; they
are not hardware execution commands.

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

- [Workflow and commands](knowledge/wiki/topics/integrated-pipeline.md) — stage inputs, reuse, logs, viewers and experiments.
- [Dataset contract](knowledge/wiki/topics/lerobot-pipeline.md) — robot actions, validity, region metadata, append and annotation preservation.
- [Retargeting contracts](knowledge/wiki/topics/stage-3-retargeting.md) — geometry, frozen defaults, limits and known failure modes.
- [Current status](knowledge/wiki/status.md), [knowledge index](knowledge/wiki/index.md), and [roadmap](knowledge/raw/Project-Milestones-and-Timeline.md).

Inputs, licensed model assets, environments and generated outputs stay local and
ignored. Historical Milestone 2 evidence lives under `outputs/milestone-2/`.
