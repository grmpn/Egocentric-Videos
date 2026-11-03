# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — accepted-roll IK score tuning resumed at user request; broader simulation acceptance remains open.
- Active plan: [IK configuration experiments](plans/milestone-3-ik-tuning.md), extending the fulfilled [benchmark plan](plans/milestone-3-ik-benchmark.md).
- Deliverable: best verified configuration, trajectory and report on the updated benchmark; roadmap limit-satisfying simulation acceptance remains open.
- Completed outcome: five new accepted-roll comparisons independently audited. Best **89.666**, up from **85.127**, with all 269 joint-feasibility checks passing; >90 not yet achieved. [Evidence](experiments/ik-benchmark-iphone.md#accepted-roll-tuning-resumed--2026-11-03); [report](../../outputs/ik-benchmark-left-roll-flip/REPORT.md).
- Current work: continuing the best saved trajectory and testing robust fitting thresholds. Use the accepted [left +180° / original right Config 2](../../configs/gripper_wrist_roll_left_flip.json), reviewed **[0,269)** input and **461 observed hand samples**, excluding right-hand frame 29. Preserve source data and old scores.
- Blockers or decisions: orientation/motion tradeoff and finger collisions remain. CPU still approximately 800 MHz; external PROCHOT was observed historically, exact component/repair unverified. No system settings changed. The [10 rad/s² acceleration cap](decisions/ik-benchmark-limits.md) remains a proxy.
- Next action: finish controlled refinements, audit the best result, inspect diagnostic plots and save its reproducible settings. Focused cleanup remains due before another milestone.
- Last verification: **2026-11-03** — [six accepted-roll audits passed](../../outputs/ik-benchmark-left-roll-flip/validation/audit-slack5-orientation16.json), including source/FK/physical joints/derivatives/collisions/arithmetic; initial comparison plot inspected. No viewer tests/review this session.
