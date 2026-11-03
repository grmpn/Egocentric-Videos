# Integrated video-to-robot workflow

Implemented under the [approved cleanup plan](../plans/codebase-cleanup-and-pipeline.md).
Run from the repository root after following the [environment guide](../../../environment/README.md).
The [README](../../../README.md) gives the complete MP4 command. Each input becomes
one full-video LeRobot v3.1 episode, including gaps and failed robot predictions.
The [dataset contract](lerobot-pipeline.md) defines actions, masks and region metadata.

## Stages and outputs

`pipeline/run.sh` uses explicit interpreters and stops on any failed command. It
requires a new run directory, writes `logs/<stage>.log`, and runs these stages:

| Command in `pipeline/` | Runtime | Input → output inside the run directory |
| --- | --- | --- |
| `prepare_clip.py` | `.venv-pipeline` | Full MP4 → `prepared/` RGB at 30 FPS and source-frame mapping |
| `run_hawor_pipeline.py` | `.conda/envs/hawor` | Preparation → `hawor/` completed world export, overlay, manifest and report |
| `align_gravity.py` | `.venv-pipeline` | Completed manifest → `alignment/` Z-up geometry and gravity evidence |
| `segment_regions.py` | `.venv-pipeline` | Alignment → `regions.json` candidate camera-motion intervals |
| `map_gripper.py` | `.venv-pipeline` | Alignment → `mapping/` full-video accepted Config 2 targets/actions |
| `retarget_trajectory.py` | `.venv-pipeline` | Alignment, mapping, regions → `robot/trajectory/` fixed-base solves |
| `evaluate_trajectory.py` | `.venv-pipeline` | Solve and mapping → `robot/score.json` and per-frame metrics |
| `export_dataset.py` | `.venv-lerobot` | Manifest and evaluated solve → append one episode to the requested dataset |
| `annotate_dataset.py` | `.venv-lerobot` | Dataset and VLM endpoint → plans/subtasks on the added episode |

Candidate segmentation does not certify feasibility. Fitting preserves all retained
regions; independent URDF evaluation reports tracking, joint and discrete collision
failures. A completed solve with failed acceptance remains exportable with explicit
invalid action masks. Runtime failures stop processing. No interpolation connects
regions, gaps or base changes. Simulation and hardware acceptance remain open.

The runner uses every frozen setting in `configs/defaults/`, including the exact
saved `slack5-orientation8` full base + IK configuration, left +180°/original-right
mapping, CUDA, one attempt, and 700/1000 evaluation caps. See the
[retargeting contract](stage-3-retargeting.md#accepted-processing-defaults).

## Reuse and failure recovery

Pass `--run-manifest FILE` to reuse a completed full-video HaWoR run. Add
`--reuse-alignment DIR`, `--reuse-mapping DIR`, and `--reuse-trajectory DIR` for
existing later stages. Supply the same original `--video`: its hash and complete
interval are checked. A reused trajectory must match the frozen defaults and all
retained candidate regions, and requires its sibling evaluation files. Always
choose a new run directory; earlier logs and artifacts remain untouched.

The runner supports `HAWOR_PYTHON`, `PIPELINE_PYTHON`, `DATASET_PYTHON`, and
`VLM_PYTHON` environment overrides. It isolates HaWoR's legacy library path,
then releases the GPU before starting the pinned local VLM. To reuse an existing
server, supply both `--api-base URL` and `--model ID`. The runner stops only a
server that it started, including its worker processes. Cold model startup has a
15-minute readiness bound; shutdown allows 15 seconds before terminating remaining
owned workers.

Export and annotation are separate atomic dataset operations. If annotation fails
after successful export, the unannotated episode remains in the dataset and its
index is recorded in `dataset_export.json`. Resume just annotation against a running
server; rerunning export of the same video is deliberately rejected:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src HF_HOME="$PWD/data/models/huggingface" \
    .venv-lerobot/bin/python pipeline/annotate_dataset.py \
    --dataset-root data/lerobot/robot-pilot --episodes 0 \
    --api-base http://127.0.0.1:8000/v1 --model QuantTrio/Qwen3.6-27B-AWQ
```

For saved experiments with disjoint regions of the same full video,
`export_dataset.py` accepts repeated `--trajectory-directory` arguments. Each
requires its sibling `score.json` and `benchmark_frame_metrics.npz`. The exporter
checks unchanged source arrays/timestamps, compatible robot/mapping/solver settings,
and nonoverlap. This supports historical evidence without re-solving or concealing
its benchmark selections. Ordinary shell processing computes all retained regions
in one trajectory directory.

## Review and experiments

Use the processing interpreter for interactive viewers; each command prints its
local URL. Review validity and boundaries alongside robot motion:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-pipeline/bin/python \
    scripts/view_retargeting.py outputs/runs/demo-001/robot/trajectory --target-grippers
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-pipeline/bin/python \
    scripts/view_gripper_mapping.py outputs/runs/demo-001/mapping
```

HaWoR overlays live beside `trajectory_world.npz`; the aligned and retargeted
directories contain their own reports and previews. Per-episode canonical previews
live in the dataset's `meta/egocentric/` directory. Annotation records remain pending
human review even when the annotation command and validators pass.

`scripts/` contains setup checks, viewers, gripper overlays, workspace construction
and IK benchmarks. `scripts/benchmark_ik.py --help` exposes explicit experiment
settings, selection and output directories. Alternate mappings and SDF placement
remain in `configs/experiments/`; they do not change the processing defaults.
`scripts/build_robot_workspace.py` and `scripts/view_robot_workspace.py` support
that optional SDF workflow. The earlier hand-only orchestration and sequential
positional-IK entry points are retired; historical evidence is preserved in the wiki
and `outputs/milestone-2/`.

Reusable modules live under `src/egocentric_pipeline/{video,tracking,geometry,
retargeting,datasets,evaluation,visualization}`. Primary commands remain thin
entry points. [HaWoR](hawor-pipeline.md), [retargeting](stage-3-retargeting.md), and
[dataset](lerobot-pipeline.md) topics own the stage contracts.

## Cleanup verification — 2026-11-03

Local evidence under `outputs/cleanup/` is ignored by Git. The approved cleanup
preserved all 535 relocated Milestone 2 file hashes and reloaded its completed
runs, prepared metadata and historical datasets; see the
[relocation audit](../../../outputs/cleanup/relocation-validation.json).

The consolidated runtime passed 265 non-CUDA and 19 CUDA processing checks:
[initial CPU results](../../../outputs/cleanup/pipeline-cpu-tests.log),
[missing-dependency correction and retry](../../../outputs/cleanup/benchmark-regression-retry.log),
and [CUDA results](../../../outputs/cleanup/pipeline-gpu-tests.log).
[Official dataset tests](../../../outputs/cleanup/robot-dataset-tests-final.log)
cover create/append, full-video gaps, incompatible/repeated inputs and failed-append
preservation. The [final annotation fixture](../../../outputs/cleanup/annotation-final-test.log)
verifies robot/numeric fields and prior labels remain unchanged. The separate
[CPU-only CI selection](../../../outputs/cleanup/cpu-tests.log) passed 95 checks;
hosted CI was not run. The [runtime retirement audit](../../../outputs/cleanup/environment-retirement-audit.json)
and [post-retirement imports](../../../outputs/cleanup/post-retirement-imports.log)
record removal of the old gravity/workspace environments after replacement checks.

The saved iPhone export contains one 1,286-frame episode, regions `[0,269)`,
`[432,893)`, `[947,1286)`, and 217 gap frames. Official reader boundary checks,
exact selected solver joints and frozen settings passed; 665 frames have at least
one valid action component and 482 have all 18. Inspect the
[report](../../../outputs/cleanup/iphone-review.json),
[RGB boundaries](../../../outputs/cleanup/iphone-review-frames.jpg), and
[paths/base changes/action gaps](../../../outputs/cleanup/iphone-review-trajectory.png).
These checks preserve the saved failures and do not establish simulation or
hardware acceptance. iPhone language annotation was not part of this export check.

The small complete MP4 passed fresh preparation, HaWoR inference/overlay, gravity,
mapping, frozen CUDA fitting and independent evaluation. The final
[successful shell run](../../../outputs/cleanup/small-video-complete-console.log)
reused those verified intermediates, exported all 121 frames, generated real local
VLM plan/subtask annotations, and stopped its owned server. The
[numeric/visual review](../../../outputs/cleanup/small-review.json) checked regions
`[0,52)` and `[74,105)`, all 38 gap frames, and exact solver/settings parity.
[RGB boundaries](../../../outputs/cleanup/small-review-frames.jpg) and
[paths/base changes/action gaps](../../../outputs/cleanup/small-review-trajectory.png)
were inspected. There are 63 frames with some valid actions and 30 with all 18;
the rejected demonstration and 13 collision frames remain visible in the
[evaluation](../../../outputs/cleanup/small-video-final/robot/score.json).
[Annotation preservation and shutdown review](../../../outputs/cleanup/small-annotation-review.json)
checks the official reader and unchanged non-language columns. Labels remain
pending human semantic review. The VLM emitted a semaphore cleanup warning on
shutdown; its engine and server exited and its port closed.

Earlier attempts exposed the overlay subprocess import path, a live shell-edit
interruption and insufficient cold VLM startup time. They were corrected and their
logs retained in the [action log](../logs/2026-11.jsonl). Cleanup revision 2 is
fulfilled; broader Milestone 3 simulation acceptance remains open.
