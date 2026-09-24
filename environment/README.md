# Workflow environments

[hawor.yml](hawor.yml) is the reviewed dependency declaration for the local
Milestone 1 runtime. The acceptance evidence linked below records recreation,
dependency, compiled-kernel, inference, and rendering evidence; installation
instructions alone do not establish that those checks passed.

The [completed plan](../knowledge/wiki/plans/milestone-1-hawor-baseline.md) preserves
the original setup and acceptance requirements; the
[acceptance record](../knowledge/wiki/experiments/milestone-1-baseline.md) links the
historical evidence, and [project status](../knowledge/wiki/status.md) identifies
current work. Do not update an existing working environment
merely to repeat the installation instructions below.

## System prerequisites

Use Linux or WSL2 with an exposed NVIDIA GPU, at least 40 GB free disk space,
FFmpeg/ffprobe **6 or newer**, Git, a C/C++ build toolchain, CMake, and OpenGL/EGL runtime
libraries. The inspected compiler combination is CUDA toolkit 11.7.64 with
GCC/G++ 11.5.0 on Ubuntu 24.04. The host driver must support Torch's CUDA 11.7
runtime. WSL2 uses the Windows host driver; its Linux installation needs the
CUDA toolkit, not a second display driver.

The CUDA toolkit and graphics libraries are system prerequisites, outside the
Conda specification. Select CUDA 11.7 from NVIDIA's
[versioned download archive](https://developer.nvidia.com/cuda-11-7-0-download-archive),
using the WSL-Ubuntu installer on WSL. Follow its repository/keyring setup;
do not assume a repository for a newer Ubuntu release carries CUDA 11.7.
NVIDIA's [version-specific WSL guide](https://docs.nvidia.com/cuda/archive/11.7.0/wsl-user-guide/index.html#cuda-support-for-wsl-2)
explains the driver/toolkit separation. Keep `nvcc`, the Torch CUDA runtime,
and the host compiler compatible.

On Ubuntu, install the ordinary system prerequisites with APT. The inspected WSL
host uses `cuda-repo-wsl-ubuntu-11-7-local` version `11.7.0-1`, with individual
build/development components instead of the full CUDA/Nsight metapackage. After
configuring that version-specific repository, the relevant components are:

```bash
sudo apt update
sudo apt install git ffmpeg build-essential cmake ninja-build libgl1 libglib2.0-0
sudo apt install \
    cuda-nvcc-11-7 cuda-cudart-dev-11-7 cuda-libraries-dev-11-7 \
    cuda-cccl-11-7 gcc-11 g++-11
```

On native Ubuntu, use the operating system's recommended NVIDIA driver and reboot
if required. Verify the tools and exposed GPU separately:

```bash
nvidia-smi
/usr/local/cuda-11.7/bin/nvcc --version
/usr/bin/gcc-11 --version
/usr/bin/g++-11 --version
ffmpeg -version
ffprobe -version
```

## Recreate in the required order

Run from the repository root. Initialize the pinned engine first:

```bash
git submodule update --init --recursive
git -C external/HaWoR rev-parse HEAD
```

The expected HaWoR revision is
`66c7d4108d58a716deccd192cb7645170cdc7bd7`. Its source remains unchanged.

To suppress untracked build/asset noise from the nested repositories, apply these
**local** settings after initialization (they do not modify upstream source):

```bash
git config --local submodule.external/HaWoR.ignore untracked
git -C external/HaWoR config --local submodule.thirdparty/DROID-SLAM/thirdparty/eigen.ignore untracked
git -C external/HaWoR config --local submodule.thirdparty/DROID-SLAM/thirdparty/lietorch.ignore untracked
git -C external/HaWoR/thirdparty/DROID-SLAM/thirdparty/lietorch config --local submodule.eigen.ignore untracked
```

Tracked edits and changed submodule revisions remain visible. To inspect all
untracked files explicitly, run `git status --short --ignore-submodules=none`
inside HaWoR and each child, or use `git submodule foreach --recursive
'git status --short --ignore-submodules=none'` from the project root. Repeat
the local settings in a fresh clone. The laptop's exact prior command was not
found in tracked history; the user confirmed the issue was dirty-status noise.

For a new machine, bootstrap the Conda environment and the build prerequisites
listed in `hawor.yml`. Torch must already be importable when PyTorch3D and
torch-scatter build; one initial `conda env create -f hawor.yml` does not provide
that ordering. These commands repeat only the pins needed for the bootstrap:

```bash
conda create --override-channels -c conda-forge -n hawor \
    python=3.10.21 pip=26.2.1 wheel=0.47.0 'ffmpeg>=6'
conda activate hawor
python -m pip install \
    setuptools==80.10.2 ninja==1.13.2 Cython==3.3.0 numpy==1.26.4 \
    torch==1.13.0+cu117 torchvision==0.14.0+cu117 \
    --extra-index-url https://download.pytorch.org/whl/cu117

export CUDA_HOME=/usr/local/cuda-11.7
export PATH="$CUDA_HOME/bin:$PATH"
export CC=/usr/bin/gcc-11
export CXX=/usr/bin/g++-11
export CUDAHOSTCXX=/usr/bin/g++-11
export LD_LIBRARY_PATH="/usr/local/cuda-11.7/lib64:$CONDA_PREFIX/lib:$CONDA_PREFIX/lib/python3.10/site-packages/torch/lib:${LD_LIBRARY_PATH:-}"
if [ -d /usr/lib/wsl/lib ]; then
    export LD_LIBRARY_PATH="/usr/lib/wsl/lib:$LD_LIBRARY_PATH"
fi
```

On the RTX 4090, set `TORCH_CUDA_ARCH_LIST="8.6+PTX"` for source builds:
CUDA 11.7 cannot compile native Ada (`8.9`) instructions. The existing
DROID/LieTorch build already includes `sm_86`; verify execution on the actual
GPU after compilation. Keep CUDA 11.7 selected only for HaWoR, alongside any
newer toolkit used by the annotation server.

Confirm GPU access before downloading/building the remaining stack:

The WSL library path is needed for cuDNN to load `libcuda.so`; a simple CUDA
allocation can pass while convolution aborts without it. The setup checker
exercises both operations.

Keep `$CONDA_PREFIX/lib` in this HaWoR-only library path. On Ubuntu 22.04 the
system `libstdc++` lacks the ABI required by Conda's ICU/SQLite libraries;
otherwise an import of SQLite after Torch can fail during inference even when
the basic CUDA checks pass. The video-to-dataset command applies this path only
to its HaWoR subprocess, preserving the separate modern LeRobot runtime. It
resolves Conda's Python-directory aliases before locating Torch libraries.

```bash
python -c 'import torch; print(torch.__version__, torch.version.cuda); print(torch.cuda.get_device_name(0)); print((torch.ones(8, device="cuda") * 2).cpu())'
```

Then apply the complete specification. `PIP_NO_BUILD_ISOLATION=0` is pip's
environment-variable spelling for disabled build isolation: compiled packages
see the already installed Torch and build prerequisites. `MAX_JOBS=1` limits
parallel compilation memory; it does not change inference settings.

```bash
PIP_NO_BUILD_ISOLATION=0 MAX_JOBS=1 conda env update -n hawor -f environment/hawor.yml
```

HaWoR documents Lightning as a separate `--no-deps` installation. The YAML pins
its exact version and the required support packages alongside Torch, so the
resolver cannot upgrade Torch while installing Lightning. The installed
Lightning 2.2.4 metadata accepts Torch 1.13.0. Lightning also requests
`fsspec[http]`; normal resolution installs its `aiohttp` extra, which was absent
from the original environment despite its passing `pip check`.

Finally, use DROID-SLAM's official installation command. Its `setup.py` installs
both `droid_backends` and `lietorch`; their pinned source dependency is recorded
in `hawor.yml` rather than replaced by an unrelated package-index build:

```bash
(
    cd external/HaWoR/thirdparty/DROID-SLAM
    MAX_JOBS=1 python setup.py install
)
python -m pip check
python -c 'import torch; from pytorch3d import _C; import droid_backends, lietorch, lietorch_backends, torch_scatter; print("Compiled imports passed")'
```

When changing Torch, rebuild PyTorch3D, torch-scatter, DROID-SLAM, and LieTorch
against the same recorded CUDA/compiler combination. A successful import alone
does not establish CUDA kernel or inference correctness. The existing
environment also contains unrelated CUDA 13/Triton packages; they are excluded
from the specification because they are outside this cu117 runtime dependency
set.

## Assets and rendering

The [runtime asset contract](../src/egocentric_pipeline/hawor_runner.py) and
setup checker require these paths relative to `external/HaWoR/`:

```text
weights/external/droid.pth
weights/external/detector.pt
weights/hawor/checkpoints/hawor.ckpt
weights/hawor/checkpoints/infiller.pt
weights/hawor/model_config.yaml
thirdparty/Metric3D/weights/metric_depth_vit_large_800k.pth
_DATA/data/mano/MANO_RIGHT.pkl
_DATA/data_left/mano_left/MANO_LEFT.pkl
```

The model config belongs directly under `weights/hawor/`; the historical plan's
`checkpoints/model_config.yaml` path was a documentation error. Weights, MANO,
and source videos remain untracked. The checker records presence and SHA-256
hashes. Model download links are in the
[pinned upstream installation guide](https://github.com/ThunderVVV/HaWoR/blob/66c7d4108d58a716deccd192cb7645170cdc7bd7/README.md#installation);
obtain MANO separately through its licensed download. Assets are external inputs,
not Conda packages.

The desktop obtains the six public files from the
[maintainer's HaWoR model repository](https://huggingface.co/ThunderVVV/HaWoR/tree/da6335f47f9806308992d5ae1002a4cc5f7252c2)
at revision `da6335f47f9806308992d5ae1002a4cc5f7252c2`. Its `external/` files
map to the DROID, detector, and Metric3D destinations above; its `hawor/` files
map beneath `weights/hawor/`. This avoids requiring Google Drive for the
maintainer's mirrored DROID/Metric3D weights. Obtain the two MANO files through
[MANO's download process](https://mano.is.tue.mpg.de/) or your existing licensed copy.

The installed stock viewer uses ModernGL's default X11 backend even in its
headless mode. Setting `PYOPENGL_PLATFORM=egl` alone does not change that viewer
backend. A passing OpenGL import is insufficient: inspect a produced video or
representative rendered frames from the bundled example. Record the working
backend and any settings used only for display with the smoke-test evidence.

For an interactive viewer that reports a Qt `xcb` error, retain the display
provided by Linux/WSLg, select Qt's XCB backend, and install the missing XCB
runtime libraries:

```bash
export QT_QPA_PLATFORM=xcb
sudo apt install \
    libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 \
    libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 \
    libxkbcommon-x11-0 libxrender1 libxi6 libsm6 libice6
```

## Project commands and verification

Project-owned code runs directly from this checkout with the `hawor`
environment active and `PYTHONPATH=src`, without an installed project
distribution. Run from the repository root:

```bash
PYTHONPATH=src python -c 'import egocentric_pipeline; print(egocentric_pipeline.__file__)'
PYTHONPATH=src python -m pytest tests
```

`pytest` is included in `hawor.yml`. The explicit `tests` argument collects every
project test and excludes upstream HaWoR/HOT3D/DROID test scripts. The separate
[CPU environment](cpu-tests.yml) contains only the dependencies needed by these
project contracts; the [CI workflow](../.github/workflows/ci.yml) creates it,
checks the checkout import, and runs the same suite. CUDA, HaWoR, model assets,
licensed videos, and actual visual review remain local validation gates. A
workflow definition does not establish that a hosted CI run has passed.

To create that smaller CPU environment locally:

```bash
conda env create -f environment/cpu-tests.yml
conda activate egocentric-cpu-tests
PYTHONPATH=src python -m pytest tests
```

Use the environment's FFmpeg and Python together. The CPU specification does
not install the GPU runtime or download model/data assets.

Run the [setup checker](../scripts/check_hawor_setup.py) before the bundled
example, choosing a fresh evidence path for each check:

```bash
PYTHONPATH=src python scripts/check_hawor_setup.py --output outputs/hawor/milestone-1/setup-check/setup_check.json
```

The checker refuses to replace an existing evidence file. Retain its JSON
evidence and the exact environment snapshot with the successful smoke run. A
snapshot records what was installed; `hawor.yml`
continues to own dependency choices and recreation instructions. Final runtime
acceptance requires successful recreation, dependency consistency, CUDA
execution, compiled kernels, real inference, and inspected rendering.

## Native desktop and annotation environments

The 2026-09-24 desktop uses Ubuntu 22.04, RTX 4090 (24 GiB), driver 580.159.03,
and 62 GiB RAM. Its local Conda installation is `.conda/`, with HaWoR at
`.conda/envs/hawor/`; LeRobot uses `.venv-lerobot/`, and vLLM uses `.venv-vlm/`.
All are ignored by Git. To activate HaWoR in a terminal:

```bash
source .conda/etc/profile.d/conda.sh
conda activate "$PWD/.conda/envs/hawor"
```

Apply the CUDA/compiler exports above in that terminal. Ubuntu 22.04's system
FFmpeg 4.4 lacks required frame-PTS and CLI features; use the Conda FFmpeg in
both HaWoR and LeRobot commands. This desktop installed FFmpeg 9.0.2 from
conda-forge. For LeRobot, use its explicit interpreter and clear legacy library
paths, for example:

```bash
export PATH="$PWD/.conda/envs/hawor/bin:$PATH"
export HF_HOME="$PWD/data/models/huggingface"
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-lerobot/bin/python -m pytest tests
```

Keep this `HF_HOME` export for dataset creation and annotation too. The desktop's
default `~/.cache/huggingface` directory is not writable by the current user;
the repository-local cache works for both datasets and model weights.

Install the annotation server separately:

```bash
uv venv --python 3.12 .venv-vlm
uv pip install --python .venv-vlm/bin/python --torch-backend=cu129 \
    -r environment/vlm-requirements.txt
uv pip check --python .venv-vlm/bin/python
```

[vLLM 0.19.1](https://docs.vllm.ai/en/v0.19.1/getting_started/installation/gpu/)
uses Torch 2.10.0/CUDA 12.9 here. Its dependency check, GPU matrix multiplication,
and real image serving pass. The full-precision Qwen3.6-27B exceeds 24 GiB VRAM.
The verified local serving checkpoint is
[QuantTrio/Qwen3.6-27B-AWQ](https://huggingface.co/QuantTrio/Qwen3.6-27B-AWQ),
revision `9b507bdc9afafb87b7898700cc2a591aa6639461`; this is a community 4-bit
quantization, whose pilot annotation quality still needs video review.

Download the **complete** snapshot, then start the server in its own terminal:

```bash
export HF_HOME="$PWD/data/models/huggingface"
.venv-lerobot/bin/hf download QuantTrio/Qwen3.6-27B-AWQ \
    --revision 9b507bdc9afafb87b7898700cc2a591aa6639461
env -u LD_LIBRARY_PATH CUDA_HOME=/usr/local/cuda-12.9 HF_HUB_OFFLINE=1 \
    .venv-vlm/bin/vllm serve --config environment/vlm-server.yaml
```

The [server configuration](vlm-server.yaml) binds only to `127.0.0.1:8000`,
uses an 8192-token context, one request at a time, and up to three contact sheets
(the annotator's default sixty-frame window). CPU offload is disabled: this
vLLM version rejects it with Qwen's hybrid cache. GPU-only model loading uses
19.78 GiB; run HaWoR and the server sequentially. Stop the server with Ctrl+C
before HaWoR inference. Larger prompts or different image layouts require a
separate capacity check.

Desktop verification completed on 2026-09-24:

- All three dependency checks, 34 HaWoR preflight checks, and CUDA execution in
  PyTorch3D, torch-scatter, DROID and LieTorch pass. Both separately supplied MANO
  files are present and readable; no further setup asset download is needed.
- The bundled 121-frame video completes HaWoR inference, export, rendering and
  validation in 68.920 seconds, with 13.476 GiB sampled peak device memory.
  Five overlay frames and world/canonical trajectory previews were inspected.
- LeRobot creation and reload pass. Actual `lerobot-annotate` generates plans
  and subtasks through the local Qwen server; its validator reports zero errors
  or warnings. Reload preserves all 121 frames and labels at 0 and 2 seconds.
  The pickup/carry-to-sink labels match the inspected example frames.
- The full project suite passed 88 tests across two runs; six focused dataset,
  canonical and annotation checks passed again after the subprocess fixes.

This verifies setup on the bundled example, not acceptance of the unrecorded
iPhone pilot or metric trajectory accuracy. Dataset annotations retain their
`pending` review status. The test server is stopped. The earlier standalone
three-contact-sheet client smoke also passed in 6.20 seconds.

Desktop setup evidence is local-only under
`outputs/setup/desktop-20260924/`: `setup_check.json`, `compiled-kernels.json`,
`bundled-reload.json`, `bundled-annotation.log`, and `overlay-review.jpg` record
the checks above. `bundled-dataset/` contains the annotated example; failed
attempts and their logs are preserved alongside it. This clone does not contain
the laptop's datasets or generated runs.
