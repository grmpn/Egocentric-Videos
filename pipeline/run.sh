#!/usr/bin/env bash
# Full MP4 -> reusable human dataset -> evaluated robot region episodes -> annotations.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
usage() {
    cat <<'EOF'
Usage: pipeline/run.sh --video INPUT.mp4 --human-dataset-root HUMAN --robot-dataset-root ROBOT --run-directory NEW_DIR --task TEXT

Or start from HUMAN alone with --source-episode-index N instead of --video.
Licensed models may be supplied with --mano-left FILE --mano-right FILE.
--min-episode-valid-ratio defaults to 0.85; --skip-annotation skips VLM execution.

Runs the pinned local VLM after export, then stops it. To use an existing server,
provide both --api-base URL and --model ID instead.
Reuse completed stages with --run-manifest FILE, --reuse-alignment DIR,
--reuse-mapping DIR, and --reuse-trajectory DIR. The input must be the full video.
Interpreters: HAWOR_PYTHON, PIPELINE_PYTHON, DATASET_PYTHON, VLM_PYTHON.
EOF
}
video= dataset= human_dataset= source_episode= run= task= manifest= alignment= mapping= trajectory= api_base= model=
min_valid_ratio=0.85
skip_annotation=false
mano_left=$root/external/HaWoR/_DATA/data_left/mano_left/MANO_LEFT.pkl
mano_right=$root/external/HaWoR/_DATA/data/mano/MANO_RIGHT.pkl
while (($#)); do
    if [[ $1 == --skip-annotation ]]; then skip_annotation=true; shift; continue; fi
    if [[ $1 != --help && $1 != -h && $# -lt 2 ]]; then
        printf 'Missing value for %s\n' "$1" >&2; exit 2
    fi
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --video) video=$2 ;;
        --dataset-root|--robot-dataset-root) dataset=$2 ;;
        --human-dataset-root) human_dataset=$2 ;;
        --source-episode-index) source_episode=$2 ;;
        --mano-left) mano_left=$2 ;;
        --mano-right) mano_right=$2 ;;
        --min-episode-valid-ratio) min_valid_ratio=$2 ;;
        --run-directory) run=$2 ;;
        --task) task=$2 ;;
        --run-manifest) manifest=$2 ;;
        --reuse-alignment) alignment=$2 ;;
        --reuse-mapping) mapping=$2 ;;
        --reuse-trajectory) trajectory=$2 ;;
        --api-base) api_base=$2 ;;
        --model) model=$2 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
    shift 2
done
if [[ -z $human_dataset || -z $dataset || -z $run || -z $task ]]; then usage >&2; exit 2; fi
if [[ -z $video && -z $source_episode || -n $video && -n $source_episode ]]; then
    printf 'Supply either --video or --source-episode-index.\n' >&2; exit 2
fi
if [[ -n $source_episode && ( -n $manifest || -n $alignment || -n $mapping || -n $trajectory ) ]]; then
    printf 'Human-dataset input starts new robot processing; do not combine it with reused run stages.\n' >&2; exit 2
fi
if [[ -n $api_base && -z $model || -z $api_base && -n $model ]]; then
    printf 'External annotation requires both --api-base and --model.\n' >&2; exit 2
fi
# Resolve user paths before changing to the repository root.
if [[ -n $video ]]; then video=$(realpath -e -- "$video"); fi
human_dataset=$(realpath -m -- "$human_dataset")
mano_left=$(realpath -m -- "$mano_left")
mano_right=$(realpath -m -- "$mano_right")
dataset=$(realpath -m -- "$dataset")
run=$(realpath -m -- "$run")
for name in manifest alignment mapping trajectory; do
    if [[ -n ${!name} ]]; then printf -v "$name" '%s' "$(realpath -e -- "${!name}")"; fi
done
HAWOR_PYTHON=${HAWOR_PYTHON:-$root/.conda/envs/hawor/bin/python}
PIPELINE_PYTHON=${PIPELINE_PYTHON:-$root/.venv-pipeline/bin/python}
DATASET_PYTHON=${DATASET_PYTHON:-$root/.venv-lerobot/bin/python}
VLM_PYTHON=${VLM_PYTHON:-$root/.venv-vlm/bin/python}
for name in HAWOR_PYTHON PIPELINE_PYTHON DATASET_PYTHON VLM_PYTHON; do
    printf -v "$name" '%s' "$(realpath -m -s -- "${!name}")"
done
# Never replace an earlier attempt or its logs.
mkdir -p -- "$(dirname -- "$run")"
mkdir -- "$run"
mkdir -- "$run/logs"
cd -- "$root"
export PYTHONPATH="$root/src${PYTHONPATH:+:$PYTHONPATH}"
export HF_HOME=${HF_HOME:-$root/data/models/huggingface}
export MPLCONFIGDIR="$run/matplotlib"
export PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
unset LD_LIBRARY_PATH
stage() {
    local label=$1
    shift
    printf 'Stage %s; log: %s/logs/%s.log\n' "$label" "$run" "$label"
    "$@" 2>&1 | tee "$run/logs/$label.log"
}
vlm_pid=
cleanup() {
    if [[ -n $vlm_pid ]]; then
        # Signal the owned session, including workers still profiling the model.
        kill -TERM -- "-$vlm_pid" 2>/dev/null || true
        for ((attempt=0; attempt<15; attempt++)); do
            kill -0 -- "-$vlm_pid" 2>/dev/null || break
            sleep 1
        done
        kill -KILL -- "-$vlm_pid" 2>/dev/null || true
        wait "$vlm_pid" 2>/dev/null || true
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [[ -n $source_episode ]]; then
    alignment=$run/alignment
    stage restore_human "$DATASET_PYTHON" pipeline/export_dataset.py restore-human \
        --human-dataset-root "$human_dataset" --source-episode-index "$source_episode" \
        --output-directory "$alignment" --mano-models "$mano_left" "$mano_right"
else
if [[ -z $manifest ]]; then
    stage prepare "$PIPELINE_PYTHON" pipeline/prepare_clip.py --video "$video" --task-label "$task" --prepared-root "$run/prepared"
    clips=("$run"/prepared/*/clip_metadata.json)
    [[ ${#clips[@]} == 1 && -f ${clips[0]} ]]
    # Only the legacy inference subprocess receives HaWoR's CUDA/C++ libraries.
    hawor_prefix=$(dirname -- "$(dirname -- "$HAWOR_PYTHON")")
    stage hawor env PATH="$hawor_prefix/bin:$PATH" \
        LD_LIBRARY_PATH="/usr/lib/wsl/lib:/usr/local/cuda-11.7/lib64:$hawor_prefix/lib:$hawor_prefix/lib/python3.10/site-packages/torch/lib" \
        "$HAWOR_PYTHON" pipeline/run_hawor_pipeline.py --prepared "${clips[0]}" --output-root "$run/hawor"
    manifests=("$run"/hawor/*/run_manifest.json)
    [[ ${#manifests[@]} == 1 && -f ${manifests[0]} ]]
    manifest=${manifests[0]}
fi
stage verify_input "$PIPELINE_PYTHON" - "$video" "$manifest" <<'PY'
from pathlib import Path
import sys
from egocentric_pipeline.tracking.world_export import load_run
from egocentric_pipeline.run_metadata import sha256_file
_, _, clip, _, _ = load_run(sys.argv[2])
if sha256_file(sys.argv[1]) != clip['source']['sha256']:
    raise ValueError('Reused HaWoR run belongs to a different input video')
start, stop = clip['selection']['resolved_interval_s']
if start != 0 or abs(stop - clip['source']['duration_s']) > 1e-9:
    raise ValueError('Use a full-video HaWoR run, without interval trimming')
print('Completed HaWoR run matches the entire supplied MP4')
PY
if [[ -z $alignment ]]; then
    alignment=$run/alignment
    stage gravity "$PIPELINE_PYTHON" pipeline/align_gravity.py --run-manifest "$manifest" --output-directory "$alignment"
fi
stage human_export "$DATASET_PYTHON" pipeline/export_dataset.py human --alignment-directory "$alignment" \
    --dataset-root "$human_dataset" --task "$task" --result "$run/human_export.json"
source_episode=$($DATASET_PYTHON -c 'import json,sys; print(json.load(open(sys.argv[1]))["episode_index"])' "$run/human_export.json")
fi
stage segmentation "$PIPELINE_PYTHON" pipeline/segment_regions.py --alignment-directory "$alignment" --output "$run/regions.json"
if [[ -z $mapping ]]; then
    mapping=$run/mapping
    stage grippers "$PIPELINE_PYTHON" pipeline/map_gripper.py --alignment-directory "$alignment" --output-directory "$mapping"
fi
if [[ -z $trajectory ]]; then
    trajectory=$run/robot/trajectory
    stage retargeting "$PIPELINE_PYTHON" pipeline/retarget_trajectory.py --alignment-directory "$alignment" \
        --gripper-mapping-directory "$mapping" --regions "$run/regions.json" --output-directory "$trajectory"
else
    stage verify_reuse "$PIPELINE_PYTHON" - "$trajectory" "$run/regions.json" <<'PY'
import sys
from pathlib import Path
from egocentric_pipeline.run_metadata import read_json
report = read_json(Path(sys.argv[1]) / 'retargeting_report.json')
proposal = read_json(sys.argv[2])
if (report['settings'] != read_json('configs/defaults/retargeting.json')
        or report['gripper_mapping_settings'] != read_json('configs/defaults/gripper_mapping.json')
        or report.get('benchmark_selection') is not None or report.get('region_limit') is not None
        or report['source_run_id'] != proposal['source_run_id']
        or [(r['start'], r['stop']) for r in report['regions']] != [(r['start'], r['stop']) for r in proposal['regions']]):
    raise ValueError('Reuse requires the frozen defaults and all retained regions of this input')
print('Reused trajectory matches frozen settings and full-video candidate regions')
PY
fi
stage evaluation "$PIPELINE_PYTHON" pipeline/evaluate_trajectory.py --trajectory-directory "$trajectory" \
    --mapping-directory "$mapping" --output-directory "$run/evaluation"
stage robot_export "$DATASET_PYTHON" pipeline/export_dataset.py robot --human-dataset-root "$human_dataset" \
    --source-episode-index "$source_episode" --trajectory-directory "$trajectory" --evaluation-directory "$run/evaluation" \
    --dataset-root "$dataset" --task "$task" --min-episode-valid-ratio "$min_valid_ratio" \
    --diagnostics "$run/region_export.json" --result "$run/dataset_export.json"
episodes_text=$($DATASET_PYTHON -c 'import json,sys; print(" ".join(map(str,json.load(open(sys.argv[1]))["episode_indices"])))' "$run/dataset_export.json")
if [[ -z $episodes_text || $skip_annotation == true ]]; then
    printf 'Export complete. Robot episode indices: [%s]. Diagnostics: %s/region_export.json\n' "$episodes_text" "$run"
    exit 0
fi
read -r -a episodes <<< "$episodes_text"
if [[ -z $api_base ]]; then
    # Start only after the inference/IK processes have released their GPU memory.
    "$DATASET_PYTHON" - <<'PYPORT'
import socket
try:
    connection = socket.create_connection(('127.0.0.1', 8000), timeout=2)
except OSError:
    pass
else:
    connection.close()
    raise RuntimeError('Port 8000 is already occupied; use --api-base and --model for that server')
PYPORT
    api_base=http://127.0.0.1:8000/v1
    model=$($DATASET_PYTHON -c "import yaml; print(yaml.safe_load(open('environment/vlm-server.yaml'))['served-model-name'])")
    setsid env CUDA_HOME=/usr/local/cuda-12.9 HF_HUB_OFFLINE=1 "$VLM_PYTHON" -m vllm.entrypoints.cli.main serve \
        --config environment/vlm-server.yaml > "$run/logs/vlm-server.log" 2>&1 &
    vlm_pid=$!
    printf 'Starting local VLM; log: %s/logs/vlm-server.log\n' "$run"
    # A bounded readiness check fails if the child exits or never becomes healthy.
    "$DATASET_PYTHON" - "$vlm_pid" <<'PY'
import os, sys, time, urllib.request
pid = int(sys.argv[1])
# Cold Triton profiling can exceed six minutes on the supported GPU.
deadline = time.monotonic() + 900
while time.monotonic() < deadline:
    os.kill(pid, 0)
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2) as response:
            if response.status == 200:
                break
    except OSError:
        time.sleep(2)
else:
    raise RuntimeError('VLM readiness timed out; inspect logs/vlm-server.log')
PY
fi
stage annotations "$DATASET_PYTHON" pipeline/annotate_dataset.py --dataset-root "$dataset" \
    --model "$model" --api-base "$api_base" --episodes "${episodes[@]}" --record "$run/annotations.json"
printf 'Completed human episode %s and robot episodes [%s]. Logs: %s/logs\n' "$source_episode" "$episodes_text" "$run"
