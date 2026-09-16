# HaWoR environment

[hawor.yml](hawor.yml) is the reviewed dependency declaration for the local
Milestone 1 runtime. The project status linked below records recreation,
dependency, compiled-kernel, inference, and rendering evidence; installation
instructions alone do not establish that those checks passed.

The [active plan](../knowledge/agent/plans/milestone-1-hawor-baseline.md) defines
the setup and acceptance requirements; the [project status](../knowledge/agent/PROJECT_STATUS.md)
records the current evidence. Do not update an existing working environment
merely to repeat the installation instructions below.

## System prerequisites

Use Linux or WSL2 with an exposed NVIDIA GPU, at least 40 GB free disk space,
FFmpeg/ffprobe, Git, a C/C++ build toolchain, CMake, and OpenGL/EGL runtime
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

For a new machine, bootstrap the Conda environment and the build prerequisites
listed in `hawor.yml`. Torch must already be importable when PyTorch3D and
torch-scatter build; one initial `conda env create -f hawor.yml` does not provide
that ordering. These commands repeat only the pins needed for the bootstrap:

```bash
conda create -n hawor python=3.10.21 pip=26.2.1 wheel=0.47.0
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
export LD_LIBRARY_PATH="/usr/local/cuda-11.7/lib64:$CONDA_PREFIX/lib/python3.10/site-packages/torch/lib:${LD_LIBRARY_PATH:-}"
if [ -d /usr/lib/wsl/lib ]; then
    export LD_LIBRARY_PATH="/usr/lib/wsl/lib:$LD_LIBRARY_PATH"
fi
```

Confirm GPU access before downloading/building the remaining stack:

The WSL library path is needed for cuDNN to load `libcuda.so`; a simple CUDA
allocation can pass while convolution aborts without it. The setup checker
exercises both operations.

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

Use the exact weight and MANO locations in the
[plan's setup requirements](../knowledge/agent/plans/milestone-1-hawor-baseline.md#38-required-model-files-and-exact-locations).
Weights, MANO, and source videos remain untracked. The setup checker records
their presence and weight hashes. Model download links are in the
[pinned upstream installation guide](https://github.com/ThunderVVV/HaWoR/blob/66c7d4108d58a716deccd192cb7645170cdc7bd7/README.md#installation);
obtain MANO separately through its licensed download. Assets are external inputs,
not Conda packages.

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
PYTHONPATH=src python scripts/check_hawor_setup.py --output outputs/hawor/setup-check/setup_check.json
```

The checker refuses to replace an existing evidence file. Retain its JSON
evidence and the exact environment snapshot with the successful smoke run. A
snapshot records what was installed; `hawor.yml`
continues to own dependency choices and recreation instructions. Final runtime
acceptance requires successful recreation, dependency consistency, CUDA
execution, compiled kernels, real inference, and inspected rendering.
