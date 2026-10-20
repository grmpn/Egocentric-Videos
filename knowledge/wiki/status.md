# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**, including Parts 1–3, MANO comparison, wrist alignment and the joint/base optimization extension.
- Stage: **Complete** — camera-position extension and four-weight experiment verified; fitting regressions retained.
- Active plan: [Joint base and trajectory optimization, approved revision 3](plans/milestone-3-joint-base-optimization.md). Fulfilled baseline: [wrist alignment amendment](plans/milestone-3-wrist-alignment.md), with earlier Parts 1–3 linked from the [index](index.md).
- Deliverable: shared XYZ/yaw base fitting, wrist/camera pose objectives and fixed-base trajectory smoothing; preserved original comparison plus controlled camera-position/posture experiments with saved trajectories and viewer evidence.
- Completed outcome: camera position RMS improves 30.7→26.9 cm, with worse head rotation and wrist coverage. Weights 0.02/0.1/0.5 retain region 1; 2.0 rejects both. 0.5 is the strongest tested weight retaining a qualifying region. [Comparison and artifacts](experiments/joint-base-bundled.md#camera-position-and-posture-weight-sweep).
- Current work: approved experiment complete; posture default remains 0.02.
- Blockers or decisions: substantial camera/head error, rejected first region, budget-limited fits, collision clearance and physical calibration remain limitations. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: review the 0.5 tradeoff before choosing any further tuning; focused repository cleanup remains due before another milestone.
- Last verification: **2026-10-20**, 47 focused tests, four independent FK/source/acceptance audits, identical-settings/video checks and low/mid/high/legacy browser inspection; `20261020-camera-posture-005` in the [action log](logs/2026-10.jsonl). Earlier benchmarks remain historical evidence.
