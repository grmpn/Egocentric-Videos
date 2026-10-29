# Project status

- Current milestone: **3 — IK benchmark and gripper integration**.
- Stage: **Validating** — implementation and reference run complete; gripper comparisons running.
- Active plan: [IK benchmark and gripper integration, approved revision 1](plans/milestone-3-ik-benchmark.md).
- Deliverable: reusable 100-point benchmark, preserved experiments and updating report, Config 2 gripper IK with missing-hand motion penalty, and a result viewer.
- Completed outcome: benchmark/report and palm/opening IK implemented; reference scores **34.83/100** against common filtered Config 2 targets. [Local report](../../outputs/ik-benchmark/REPORT.md).
- Current work: full iPhone Config 2 runs with missing-hand penalty off/on, then independent score audit and visual review. Tests cover CPU/CUDA, source preservation, missing-hand isolation and real collision geometry.
- Blockers or decisions: no implementation blocker. [Limit research](decisions/ik-benchmark-limits.md) defines an approved 10 rad/s² benchmark cap because Alex acceleration bounds are unavailable in inspected sources. Physical scale/contact, dynamics, earlier IK failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md) remain unresolved.
- Next action: finish matched runs, verify saved metrics/report and inspect the gripper IK viewer. Focused cleanup remains due before another milestone.
- Last verification: **2026-10-29**, [focused suite](../../outputs/ik-benchmark/validation/focused-tests.log) plus corrected/new [benchmark checks](../../outputs/ik-benchmark/validation/benchmark-final-tests.log); full reference output verified by the production scorer. Final independent/visual acceptance remains pending.
