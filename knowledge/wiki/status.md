# Project status

- Current milestone: **3 — IK benchmark and gripper integration**.
- Stage: **Implementing** — revision 1 explicitly approved.
- Active plan: [IK benchmark and gripper integration, approved revision 1](plans/milestone-3-ik-benchmark.md).
- Deliverable: reusable 100-point benchmark, preserved experiments and updating report, Config 2 gripper IK with missing-hand motion penalty, and a result viewer.
- Completed outcome: latest Config 2's 25 mm backward placement verified previously over 1,286 frames / 1,802 valid samples. [Evidence](experiments/direct-gripper-iphone.md#config-2-backward-wrist-offset-2026-10-29).
- Current work: implement benchmark scoring and smoothed Config 2 palm/opening targets in two-stage IK; add per-hand missing-target motion penalty.
- Blockers or decisions: no implementation blocker. [Limit research](decisions/ik-benchmark-limits.md) defines an approved 10 rad/s² benchmark cap because Alex acceleration bounds are unavailable in inspected sources. Physical scale/contact, dynamics, earlier IK failures and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md) remain unresolved.
- Next action: implement and compare the existing IK reference with Config 2 gripper IK, missing-hand penalty off/on. Focused cleanup remains due before another milestone.
- Last verification: **2026-10-29**, static inspection of smoothing defaults, latest Config 2, pinned Alex limits/collision filters and external acceleration references; [research evidence](decisions/ik-benchmark-limits.md). Prior 47-test/visual validation applies to the wrist-offset work only.
