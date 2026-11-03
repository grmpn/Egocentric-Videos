# HuRo — workflow reference

Added 2026-09-22 at the user's request.
[Project page](https://3587jjh.github.io/HuRo/) ·
[Repository](https://github.com/3587jjh/HuRo) ·
[Inspected repository revision](https://github.com/3587jjh/HuRo/tree/aeaae17f0fd51cc325b030bbef79ceb68a25199e).
This is a bounded documentation review, not a reproduction or implementation audit.

## Source claims

HuRo reconstructs egocentric human video, segments and labels manipulation, retargets
hand motion, removes visible human arms, and renders a synthetic robot embodiment.
Its released workflow exports LeRobot V2.0 episodes containing robotized images
and retargeted states/actions. These outputs differ from this project's
human-video/hand-trajectory pilot.

The [pipeline description](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/pipeline/README.md)
separates camera calibration, hand detection, track-side refinement, HaWoR hand
reconstruction, camera trajectory estimation, language segmentation, inpainting,
retargeting, rendering, and dataset export. It documents 100DoH detection and
BoT-SORT refinement before HaWoR, with separate camera-trajectory estimation.
It also describes undistorting frames to a pinhole view. Those are HuRo's choices,
not verified improvements to our accepted baseline.

## Relevance and limits

Use the stage boundaries, detection/refinement stages, and
[HaWoR patch](https://github.com/3587jjh/HuRo/blob/aeaae17f0fd51cc325b030bbef79ceb68a25199e/submodules_patches/hawor.patch)
as starting points for later investigations of detection and infilling. The patch
was located in the repository tree but not audited; this review does **not**
establish that HuRo fixes our motion-infiller failures. Any proposed change needs
its own evidence against our baseline and authorization under the roadmap.

The user explicitly wants a reference, not a blueprint to copy. Milestone 2 keeps
the existing HaWoR detector and infiller behavior, does not add lens correction,
and does not introduce synthetic robot imagery. HuRo's format does not override
the user's subsequent selection of LeRobotDataset v3.1. Retargeting remains
Milestone 3 work. No HuRo code, dependencies, models, or pipeline assets were
installed or imported.
