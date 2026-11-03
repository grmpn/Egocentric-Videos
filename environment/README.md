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

Use Linux or WSL2 with an exposed NVIDIA GPU, enough disk space for model weights, isolated environments and temporary dataset copies,
FFmpeg/ffprobe **6 or newer**, Git, a C/C++ build toolchain, CMake, and OpenGL/EGL runtime
libraries. The inspected compiler combination is CUDA toolkit 11.7.64 with
GCC/G++ 11.5.0 on Ubuntu 24.04. The host driver must support the modern CUDA 12.9 runtimes as well as HaWoR's CUDA 11.7 runtime. WSL2 uses the Windows host driver; its Linux installation needs the
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
the basic CUDA checks pass. The integrated shell runner applies this path only to its HaWoR subprocess,
preserving the modern processing and dataset runtimes.

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

The [runtime asset contract](../src/egocentric_pipeline/tracking/hawor_runner.py) and
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

## Processing environment

Use Python 3.12 in `.venv-pipeline` for preparation, GeoCalib gravity alignment,
retargeting, evaluation and visualization. The [combined requirements](pipeline-requirements.txt)
reuse the existing stage pins, Torch 2.10.0/CUDA 12.9, CuPy 13.6.0 and nvmath-python
0.6.0/cuDSS. They replace the separate gravity/workspace runtime declarations.

```bash
uv venv --python 3.12 .venv-pipeline
uv pip install --python .venv-pipeline/bin/python \
    pip==26.2.1 setuptools==80.10.2 wheel==0.47.0
uv pip install --python .venv-pipeline/bin/python --torch-backend=cu129 \
    --no-build-isolation-package chumpy -r environment/pipeline-requirements.txt
uv pip check --python .venv-pipeline/bin/python
```

Chumpy's legacy build needs the package-specific isolation option above. The
renderer distribution is **scikit-robot-pyrender==0.1.50**, which provides the
`pyrender` import used by scikit-robot. Do not also install the upstream `pyrender`
wheel: both distributions own the same module files. The prior workspace
specification named that fork incorrectly; the consolidated declaration fixes it.

GeoCalib is pinned to `747054d743ca64bf4b0055c26ab709fa6d234996`. Download its
pinhole checkpoint once; alignment checks its hash before inference:

```bash
mkdir -p data/models/geocalib
curl --fail --location \
    https://github.com/cvg/GeoCalib/releases/download/v1.0/geocalib-pinhole.tar \
    --output data/models/geocalib/geocalib-pinhole-v1.0.tar
sha256sum data/models/geocalib/geocalib-pinhole-v1.0.tar
```

Expected SHA-256:
`86d6aeacd8bbd974c59ce39f61854e00d36911c732ad89be471476fd708722ac`.
MANO geometry reuses the licensed files listed above. Robot stages use the pinned
[Purdue Alex assets](https://github.com/PatrizioAcquadro/purdue-alex-assets):

```bash
git clone --no-checkout https://github.com/PatrizioAcquadro/purdue-alex-assets.git data/models/purdue-alex-assets
git -C data/models/purdue-alex-assets checkout --detach 9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b
```

The [robot settings](../configs/defaults/robot_workspace.json) pin the URDF,
frames and joint chains. Asset source/license files remain local and unchanged.
Use `CUDA_PATH=/usr/local/cuda-12.9` when needed for CuPy compilation. Clear legacy
`LD_LIBRARY_PATH`; `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` avoids excessive CPU
threading. The shell runner sets these isolation/thread controls. CUDA is the
frozen solver default; no automatic CPU fallback hides a GPU failure.

## Dataset environment

Use a separate Python 3.12 environment for the official LeRobot writer/reader
and annotation client:

```bash
uv venv --python 3.12 .venv-lerobot
uv pip install --python .venv-lerobot/bin/python -r environment/lerobot-requirements.txt
uv pip check --python .venv-lerobot/bin/python
export HF_HOME="$PWD/data/models/huggingface"
```

The [requirements](lerobot-requirements.txt) pin LeRobot's Git revision and codec
stack. This separation is intentional: GeoCalib requires `opencv-python`, while
LeRobot requires `opencv-python-headless`; installing both leaves conflicting
ownership of `cv2`. HaWoR also needs its old Torch/CUDA runtime, and vLLM owns a
separate serving dependency stack. None of these need to be upgraded to run the
pipeline. Keep `HF_HOME` writable; the desktop's default home cache is not.

## Native desktop and annotation environments

The validated desktop uses an RTX 4090 with 24 GiB VRAM. Local default paths are
`.conda/envs/hawor`, `.venv-pipeline`, `.venv-lerobot`, and `.venv-vlm`; all are
ignored. When HaWoR was installed under a named Conda environment instead, set
`HAWOR_PYTHON` to that environment's absolute Python path for `pipeline/run.sh`.
Use FFmpeg/ffprobe 6 or newer. On this machine those binaries are in
`.conda/envs/hawor/bin`; add that directory to `PATH` if the system FFmpeg is older.

```bash
uv venv --python 3.12 .venv-vlm
uv pip install --python .venv-vlm/bin/python --torch-backend=cu129 \
    -r environment/vlm-requirements.txt
uv pip check --python .venv-vlm/bin/python
export HF_HOME="$PWD/data/models/huggingface"
.venv-lerobot/bin/hf download QuantTrio/Qwen3.6-27B-AWQ \
    --revision 9b507bdc9afafb87b7898700cc2a591aa6639461
```

The complete snapshot is required. [vLLM 0.19.1](vlm-requirements.txt) uses
Torch 2.10.0/CUDA 12.9. The pinned community 4-bit Qwen3.6-27B checkpoint uses
about 19.78 GiB for GPU model loading in the recorded setup; the full-precision
model does not fit this GPU. Smaller GPUs and offloading are unverified. The
[server configuration](vlm-server.yaml) uses port 8000 on loopback, one request,
8192 tokens and at most three contact sheets. CPU offload is disabled because
this vLLM version rejects it for the hybrid cache.

The shell runner starts this server after GPU processing and stops it afterward.
For standalone annotation, launch it explicitly, then run the
[annotation command](../knowledge/wiki/topics/integrated-pipeline.md#reuse-and-failure-recovery)
in another terminal:

```bash
env -u LD_LIBRARY_PATH CUDA_HOME=/usr/local/cuda-12.9 HF_HUB_OFFLINE=1 \
    .venv-vlm/bin/vllm serve --config environment/vlm-server.yaml
```

Do not run this server concurrently with HaWoR on the 24 GiB device. Changing
prompt sizes, image layouts or model configuration needs a capacity check.
Annotation records remain pending review even when inference succeeds.

## Verification and evidence

Run project code with `PYTHONPATH=src`; no installed project distribution is needed.
Use the stage's explicit interpreter. Local processing regression includes GPU
and viewer checks; dataset tests exercise official create/append and the real
annotation CLI with a deterministic local HTTP fixture:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
    .venv-pipeline/bin/python -m pytest tests --ignore=tests/test_lerobot_export.py
env -u LD_LIBRARY_PATH PYTHONPATH=src HF_HOME="$PWD/data/models/huggingface" \
    .venv-lerobot/bin/python -m pytest tests/test_lerobot_export.py tests/test_robot_episode.py tests/test_canonical.py
```

The [CI workflow](../.github/workflows/ci.yml) runs focused CPU contracts in the
[small environment](cpu-tests.yml) and a separate official LeRobot integration job.
CUDA, licensed assets, full inference and visual review remain local gates. A
workflow file does not establish that hosted CI passed.

Run `scripts/check_hawor_setup.py --output NEW_PATH.json` with HaWoR's Python and
its CUDA library environment before new-machine inference. The setup checker
refuses to overwrite evidence. Historical runtime evidence remains under
`outputs/setup/desktop-20260924/`, `outputs/gravity/part-1-20261014/`, and
`outputs/workspace/part-2-20261015/`. Milestone 2 dataset/annotation/whole-pipeline
evidence is now under `outputs/milestone-2/`; [the relocation inventory](../outputs/cleanup/relocations.json)
records byte-preserving moves. New consolidation, dataset and full-workflow
validation is under `outputs/cleanup/` and summarized in [status](../knowledge/wiki/status.md).
