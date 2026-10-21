# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Implementing** — user-approved exclusion of infilled hand observations and iPhone rerun.
- Active plan: [Joint base and trajectory optimization, approved revision 5](plans/milestone-3-joint-base-optimization.md). Earlier fulfilled plans remain in the [index](index.md).
- Deliverable: 5 cm gripper-relative wrist match point, alternate-frame joint/base fitting, full-frame trajectory refinement, and controlled hand-weight comparison with saved playback.
- Completed outcome: historical run (includes infill): full iPhone video downscaled to 960×540 and processed through HaWoR, gravity alignment and joint fitting. 373/1,095 observed frames pass poses across four regions; all regions increase acceleration and fail acceptance. [Results, trajectory and playback](experiments/retargeting-iphone.md).
- Current work: exclusion implemented and 60 focused tests pass; rerun the saved iPhone alignment. Preserve defaults: posture 0.5, hand weights 1.0, 5 cm local +X offset, stride 2, no camera-position objective.
- Blockers or decisions: position/orientation errors, exhausted solve budgets and acceleration increase prevent a qualifying demo. Physical scale/gravity, collision and dynamic limits remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: rerun and independently inspect `outputs/retargeting/iphone-no-infill-20261021/`. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-21**, full input/output timestamp checks, exact defaults match, HaWoR/GeoCalib validation, independent FK/source/bounds/sampling/acceptance audit and representative browser/visual review; `20261021-iphone-009` in the [action log](logs/2026-10.jsonl).
