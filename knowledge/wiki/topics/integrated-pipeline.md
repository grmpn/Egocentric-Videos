# Integrated video-to-human-and-robot workflow

The [README](../../../README.md) gives the complete shell command. The
[export-refresh plan](../plans/lerobot-export-refresh.md) replaces the earlier
full-video robot contract with the [two dataset contracts](lerobot-pipeline.md).
The [environment guide](../../../environment/README.md) owns runtime setup.

## Stages and outputs

`pipeline/run.sh` requires separate human/robot dataset roots, a new run directory
and a task. It uses explicit interpreters, stops on stage failure and writes
`logs/<stage>.log`:

1. Prepare the full MP4 at 30 FPS; run HaWoR and gravity alignment.
2. Export the complete human episode immediately, recording `human_export.json`.
3. Segment candidate regions, map grippers, fit each fixed base and joint trajectory.
4. Evaluate all regions into `evaluation/`, including TCP FK and joint-motion limits.
5. Export accepted robot regions, recording `dataset_export.json` and all acceptance
   decisions in `region_export.json`.
6. Annotate exactly the returned robot episode indices, recording `annotations.json`.

The runner retains frozen default solver/mapping settings. Geometric region
acceptance remains mandatory; `--min-episode-valid-ratio` adds the independent
fully-valid-frame threshold (default 0.85). If all regions fail, the human dataset
and rejection report remain and the runner skips VLM startup. `--skip-annotation`
explicitly defers language annotation when episodes do qualify.

## Reuse and failure recovery

With `--video`, reuse completed stages via `--run-manifest`, `--reuse-alignment`,
`--reuse-mapping` and `--reuse-trajectory`. Original-video identity, full duration,
frozen settings and region coverage are checked. Reused solves receive a fresh
evaluation in the new run directory; original artifacts remain intact. Historical
paths may need relocation in a copied report, never edits to protected evidence.

Alternatively provide `--source-episode-index N` instead of `--video`, using an
existing human dataset. The runner invokes `export_dataset.py restore-human` and
continues from ordinary alignment inputs. Licensed MANO assets are required,
with optional `--mano-left`/`--mano-right` locations, but original HaWoR directories
are not. This boundary can be consumed by future embodiments independently.

Interpreters are configurable through `HAWOR_PYTHON`, `PIPELINE_PYTHON`,
`DATASET_PYTHON` and `VLM_PYTHON`. HaWoR's legacy library path is isolated. The
runner starts its local VLM after GPU processing, waits up to 15 minutes for
readiness and stops only its owned server/workers. Pass `--api-base URL --model ID`
for an existing server. Dataset export and annotation publish independently.
To recover after annotation failure, use the saved episode indices directly:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src HF_HOME="$PWD/data/models/huggingface" \
    .venv-lerobot/bin/python pipeline/annotate_dataset.py \
    --dataset-root data/lerobot/robot-pilot --episodes 0 1 \
    --record outputs/runs/demo-001/annotations-retry.json \
    --api-base http://127.0.0.1:8000/v1 --model QuantTrio/Qwen3.6-27B-AWQ
```

Use a fresh record path. Existing labels cannot be overwritten. To resume robot
export after the human episode was committed, use `export_dataset.py robot` with
its source index and the saved evaluated solve; do not append the human again.
Repeated `--trajectory-directory` arguments support disjoint solves; corresponding
`--evaluation-directory` arguments select new evaluation outputs when needed.

## Review

Processing reports retain MANO source data, transforms, constraints and diagnostics.
Use `scripts/view_retargeting.py` and `scripts/view_gripper_mapping.py` with the
processing interpreter. Dataset README files explain reconstructed geometry and
training masks; no canonical preview or debug report is copied into a dataset.
Inspect RGB/trajectory alignment and language semantics. This export refresh does
not complete simulation or hardware acceptance and does not retune the solver.

## Cleanup verification — 2026-11-03

Local evidence under `outputs/old/cleanup/` is ignored by Git. The approved cleanup
preserved all 535 relocated Milestone 2 file hashes and reloaded its completed
runs, prepared metadata and historical datasets; see the
[relocation audit](../../../outputs/old/cleanup/relocation-validation.json).

The consolidated runtime passed 265 non-CUDA and 19 CUDA processing checks:
[initial CPU results](../../../outputs/old/cleanup/pipeline-cpu-tests.log),
[missing-dependency correction and retry](../../../outputs/old/cleanup/benchmark-regression-retry.log),
and [CUDA results](../../../outputs/old/cleanup/pipeline-gpu-tests.log).
[Official dataset tests](../../../outputs/old/cleanup/robot-dataset-tests-final.log)
cover create/append, full-video gaps, incompatible/repeated inputs and failed-append
preservation. The [final annotation fixture](../../../outputs/old/cleanup/annotation-final-test.log)
verifies robot/numeric fields and prior labels remain unchanged. The separate
[CPU-only CI selection](../../../outputs/old/cleanup/cpu-tests.log) passed 95 checks;
hosted CI was not run. The [runtime retirement audit](../../../outputs/old/cleanup/environment-retirement-audit.json)
and [post-retirement imports](../../../outputs/old/cleanup/post-retirement-imports.log)
record removal of the old gravity/workspace environments after replacement checks.

The saved iPhone export contains one 1,286-frame episode, regions `[0,269)`,
`[432,893)`, `[947,1286)`, and 217 gap frames. Official reader boundary checks,
exact selected solver joints and frozen settings passed; 665 frames have at least
one valid action component and 482 have all 18. Inspect the
[report](../../../outputs/old/cleanup/iphone-review.json),
[RGB boundaries](../../../outputs/old/cleanup/iphone-review-frames.jpg), and
[paths/base changes/action gaps](../../../outputs/old/cleanup/iphone-review-trajectory.png).
These checks preserve the saved failures and do not establish simulation or
hardware acceptance. iPhone language annotation was not part of this export check.

The small complete MP4 passed fresh preparation, HaWoR inference/overlay, gravity,
mapping, frozen CUDA fitting and independent evaluation. The final
[successful shell run](../../../outputs/old/cleanup/small-video-complete-console.log)
reused those verified intermediates, exported all 121 frames, generated real local
VLM plan/subtask annotations, and stopped its owned server. The
[numeric/visual review](../../../outputs/old/cleanup/small-review.json) checked regions
`[0,52)` and `[74,105)`, all 38 gap frames, and exact solver/settings parity.
[RGB boundaries](../../../outputs/old/cleanup/small-review-frames.jpg) and
[paths/base changes/action gaps](../../../outputs/old/cleanup/small-review-trajectory.png)
were inspected. There are 63 frames with some valid actions and 30 with all 18;
the rejected demonstration and 13 collision frames remain visible in the
[evaluation](../../../outputs/old/cleanup/small-video-final/robot/score.json).
[Annotation preservation and shutdown review](../../../outputs/old/cleanup/small-annotation-review.json)
checks the official reader and unchanged non-language columns. Labels remain
pending human semantic review. The VLM emitted a semaphore cleanup warning on
shutdown; its engine and server exited and its port closed.

Earlier attempts exposed the overlay subprocess import path, a live shell-edit
interruption and insufficient cold VLM startup time. They were corrected and their
logs retained in the [action log](../logs/2026-11.jsonl). Cleanup revision 2 is
fulfilled; broader Milestone 3 simulation acceptance remains open.
