# Egocentric Hand-Trajectory Pipeline

## About

This project is building a reusable pipeline that turns egocentric RGB video
into time-aligned 3D hand trajectories, language annotations, and eventually
robot-compatible trajectories. World-frame hand motion is the primary geometric
output; canonical and robot-frame representations are planned downstream.

The project is currently planning Milestone 1: reproduce and measure the
unmodified HaWoR baseline on its bundled example and one short Ego4D MP4 segment.
See the [roadmap](knowledge/raw/Project-Milestones-and-Timeline.md),
[current status](knowledge/agent/PROJECT_STATUS.md), and
[draft Milestone 1 plan](knowledge/agent/plans/milestone-1-hawor-baseline.md).
For now, the remainder of this README documents only the known-good HaWoR
installation; pipeline usage will be added as it is implemented and verified.

## HaWoR installation

The confirmed setup uses Ubuntu 24.04:

| Component | Version |
| --- | --- |
| Python | 3.10 in Conda environment `hawor` |
| PyTorch | `1.13.0+cu117` |
| torchvision | `0.14.0+cu117` |
| CUDA toolkit | 11.7 |
| CUDA host compiler | GCC/G++ 11 |

### 1. Prepare Ubuntu

Install a compatible NVIDIA driver using Ubuntu's recommended driver packages.
Reboot if required, then confirm that the GPU is visible:

```bash
nvidia-smi
```

After adding NVIDIA's CUDA repository for Ubuntu, install only the CUDA 11.7
toolkit and the compatible compiler:

```bash
sudo apt update
sudo apt install cuda-toolkit-11-7 gcc-11 g++-11
```

Do not install the generic `cuda` metapackage on Ubuntu 24.04; it can pull an
obsolete Nsight dependency that requires unavailable `libtinfo5`.

### 2. Initialize HaWoR and create the environment

[HaWoR](https://github.com/ThunderVVV/HaWoR) is tracked by this repository as a
pinned Git submodule at `external/HaWoR`. After cloning this repository,
initialize HaWoR and all of its nested submodules from the repository root:

```bash
git submodule update --init --recursive
```

Do not clone HaWoR separately. Install Miniconda, then create the environment:

```bash
conda create -n hawor python=3.10 -y
conda activate hawor

cd external/HaWoR
```

The remaining installation commands assume the current directory is
`external/HaWoR` unless stated otherwise.

### 3. Install the pinned Python stack

Install PyTorch before any other Python dependencies:

```bash
python -m pip install \
    torch==1.13.0+cu117 \
    torchvision==0.14.0+cu117 \
    --extra-index-url https://download.pytorch.org/whl/cu117

python -m pip install "setuptools<81" wheel ninja
```

Create `torch-constraints.txt` in the HaWoR directory:

```text
torch==1.13.0+cu117
torchvision==0.14.0+cu117
roma<1.6
```

Use this constraints file for every later pip installation. Do not allow another
package to upgrade PyTorch. Install the upstream requirements with the constraint:

```bash
python -m pip install -c torch-constraints.txt -r requirements.txt
```

If PyTorch3D fails because its isolated build cannot import Torch, install it
separately without build isolation, then rerun the requirements command. Limit
parallel compilation if the system is short on memory:

```bash
export MAX_JOBS=1
python -m pip install -c torch-constraints.txt \
    --no-build-isolation --no-cache-dir \
    "git+https://github.com/facebookresearch/pytorch3d.git@stable"
```

Build DROID-SLAM with CUDA 11.7 and GCC 11:

```bash
export CUDA_HOME=/usr/local/cuda-11.7
export PATH=$CUDA_HOME/bin:$PATH
export CC=/usr/bin/gcc-11
export CXX=/usr/bin/g++-11
export CUDAHOSTCXX=/usr/bin/g++-11

(
    cd thirdparty/DROID-SLAM
    python setup.py install
)
```

If the installed PyTorch version ever changes, restore the pinned version and
rebuild PyTorch3D, DROID-SLAM, and LieTorch.

### 4. Add model assets

Download the HaWoR, detector, DROID-SLAM, Metric3D, and infiller checkpoints.
Download MANO separately after accepting its license. Place the files here:

```text
external/HaWoR/
├── weights/
│   ├── external/
│   │   ├── droid.pth
│   │   └── detector.pt
│   └── hawor/
│       ├── model_config.yaml
│       └── checkpoints/
│           ├── hawor.ckpt
│           └── infiller.pt
├── thirdparty/Metric3D/weights/
│   └── metric_depth_vit_large_800k.pth
└── _DATA/
    ├── data/mano/MANO_RIGHT.pkl
    └── data_left/mano_left/MANO_LEFT.pkl
```

MANO files and model weights are external assets and must not be committed.

### 5. Configure the Ubuntu runtime

Add the following to the active shell or shell configuration:

```bash
export CUDA_HOME=/usr/local/cuda-11.7
export PATH=$CUDA_HOME/bin:$PATH
export CC=/usr/bin/gcc-11
export CXX=/usr/bin/g++-11
export CUDAHOSTCXX=/usr/bin/g++-11
export LD_LIBRARY_PATH=/usr/local/cuda-11.7/lib64:$CONDA_PREFIX/lib/python3.10/site-packages/torch/lib:${LD_LIBRARY_PATH:-}
export QT_QPA_PLATFORM=xcb
```

If visualization fails with a Qt `xcb` error, install the XCB runtime libraries:

```bash
sudo apt install \
    libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 \
    libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 \
    libxkbcommon-x11-0 libxrender1 libxi6 libsm6 libice6
```

### 6. Validate the installation

```bash
python - <<'PY'
import torch
from pytorch3d import _C
import droid_backends
import lietorch

print("Torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("GPU:", torch.cuda.get_device_name(0))
print("PyTorch3D, DROID-SLAM, and LieTorch: OK")
PY

python -m pip check
```

Expected core versions are PyTorch `1.13.0+cu117` and CUDA `11.7`. Finally,
run the bundled example:

```bash
python demo.py --video_path ./example/video_0.mp4 --vis_mode world
```

The run should complete hand detection, HaWoR inference, DROID-SLAM, Metric3D
scaling, trajectory infilling, and world-space visualization.
