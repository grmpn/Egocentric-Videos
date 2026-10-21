# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, wrist alignment and joint/base optimization.
- Stage: **Complete** — requested iPhone run verified; no region meets the full demonstration gate.
- Active plan: [Joint base and trajectory optimization, approved revision 4](plans/milestone-3-joint-base-optimization.md). Earlier fulfilled plans remain in the [index](index.md).
- Deliverable: 5 cm gripper-relative wrist match point, alternate-frame joint/base fitting, full-frame trajectory refinement, and controlled hand-weight comparison with saved playback.
- Completed outcome: full iPhone video downscaled to 960×540 and processed through HaWoR, gravity alignment and joint fitting. 373/1,095 observed frames pass poses across four regions; all regions increase acceleration and fail acceptance. [Results, trajectory and playback](experiments/retargeting-iphone.md).
- Current work: requested run complete. User-confirmed defaults already match the last hand-weight-1 trial: posture 0.5, hand weights 1.0, 5 cm local +X offset, stride 2, no camera-position objective.
- Blockers or decisions: position/orientation errors, exhausted solve budgets and acceleration increase prevent a qualifying demo. Physical scale/gravity, collision and dynamic limits remain unverified. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review iPhone failures and reconstruction before approving tuning. Saved viewer: `outputs/retargeting/iphone-20261021/trajectory/`. Focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-21**, full input/output timestamp checks, exact defaults match, HaWoR/GeoCalib validation, independent FK/source/bounds/sampling/acceptance audit and representative browser/visual review; `20261021-iphone-009` in the [action log](logs/2026-10.jsonl).
