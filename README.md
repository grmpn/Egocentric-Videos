# Egocentric video to human and robot datasets

Turn a complete MP4 into two synchronized LeRobotDataset v3.1 outputs:

- **Human:** one full prepared video per episode, structured left/right MANO poses,
  shape, physical wrists and provenance in gravity-aligned metres. Reuse it for
  new retargeting without rerunning HaWoR or SLAM.
- **Robot:** one accepted fixed-base manipulation region per episode, RGB,
  joint actions, absolute end-effector actions, validity masks and VLM plans/subtasks.

The supported robot is Purdue Alex with two SAKE EZGrippers, using the pinned
[robot settings](configs/defaults/robot_workspace.json). Actions contain left arm
7 radians, right arm 7, neck 2, then left/right normalized gripper opening
(0 closed, 1 open). `action.ee` is `[2,8]`: base-frame nominal TCP position,
normalized xyzw quaternion and opening, computed from joint-solution FK.

Install the pinned models and isolated runtimes using the
[environment guide](environment/README.md), then run:

```bash
pipeline/run.sh \
    --video data/source/demo.mp4 \
    --human-dataset-root data/lerobot/human-pilot \
    --robot-dataset-root data/lerobot/robot-pilot \
    --run-directory outputs/runs/demo-001 \
    --task "Pick up the cup and place it on the mat" \
    --min-episode-valid-ratio 0.85
```

Both dataset roots support compatible appends. Use a new run directory for each
attempt. Video must be a full MP4 suitable for pinhole processing; preparation
uses 30 FPS without lens correction. The human export precedes robot processing,
so it remains available even if retargeting fails. A robot region must have at
least 85% finite solved frames without self-collision
or joint position/velocity/acceleration violations by default. Tracking and
hand-observation failures remain in action masks and do not reject a region.
Invalid frames inside exported regions stay in temporal order. Rejected
regions and their ratios remain in `region_export.json`; no robot dataset is
created when no region qualifies. For test datasets, `--include-rejected-regions`
exports every region, labels the dataset as test data and logs each failed gate
and override without changing validity masks.

The runner annotates newly exported robot episodes and stops its owned local VLM
server afterward. Pass `--api-base URL --model ID` for an existing server, or
`--skip-annotation` to defer annotation. `--dataset-root` remains an alias for
`--robot-dataset-root`. See `pipeline/run.sh --help` for saved-stage reuse and
interpreter overrides.

To start from an existing human dataset, replace `--video` with
`--source-episode-index 0`. Supply licensed model files using `--mano-left FILE`
and `--mano-right FILE` when they are outside the default model locations. The
runner restores ordinary processing inputs from the human dataset; neither the
original video nor the original HaWoR run is required.

Each dataset has a root `README.md` explaining features, model/frame conventions
and source revisions, plus standard `data/`, `videos/` and `meta/` directories.
Robot datasets contain no MANO geometry, base transforms or solver diagnostics.
Those remain in the run:

| Path | Contents |
| --- | --- |
| `prepared/`, `hawor/`, `alignment/` | Source mapping, reconstructed geometry, overlays and gravity evidence |
| `regions.json`, `mapping/` | Candidate intervals and hand-to-gripper targets |
| `robot/trajectory/` | Joint solutions, region bases and retargeting reports |
| `evaluation/` | Tracking, joint-motion limits, collision checks and TCP FK |
| `human_export.json`, `dataset_export.json`, `region_export.json` | Added episode indices and acceptance/rejection evidence |
| `annotations.json`, `logs/` | Annotation execution record and stage/server logs |

Training must explicitly honor masks. Use
[ActionTrainingDataset and masked_mse](src/egocentric_pipeline/datasets/training.py)
with `target="joint"` or `target="ee"`; the adapter aligns temporal masks,
normalizes valid targets and excludes invalid/padded components from loss. Stock
LeRobot policies do not automatically use `quality.action_valid`. Exported numeric
statistics exclude invalid values, including finite placeholders.

Scale, floor calibration, annotation semantics and broader simulation acceptance
remain unverified; these datasets are not hardware execution commands. Inputs,
licensed models, environments and generated outputs stay local and ignored.
