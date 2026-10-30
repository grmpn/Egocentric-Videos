# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Validating** — first-region benchmark amendment fulfilled; the broader simulation demonstration still has limit/tracking/collision failures.
- Active plan: [IK benchmark and gripper integration, approved revision 2](plans/milestone-3-ik-benchmark.md), fulfilled with [acceptance evidence](experiments/ik-benchmark-iphone.md).
- Deliverable: reusable 100-point benchmark, preserved experiments/updating report, Config 2 palm/opening IK, missing-hand penalty and interactive viewer delivered. Roadmap simulation acceptance remains open.
- Completed outcome: first-region **[0,296)** scores **41.554 / 69.877 / 70.806** for wrist reference / Config 2 / Config 2 plus penalty; 296 frames, 470 observed hand samples. [Local report](../../outputs/ik-benchmark/REPORT.md); full-video results archived.
- Current work: ready for review; benchmark solves only the first retained region. Existing comparisons rescored without rerunning IK; [viewer](http://localhost:8080) labels later saved poses as excluded.
- Blockers or decisions: acceleration uses an explicit [10 rad/s² benchmark proxy](decisions/ik-benchmark-limits.md). First-region penalty run retains 42 joint-infeasible and 36 colliding frames, plus orientation failures. Physical scale/contact/dynamics and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md) remain unresolved.
- Next action: review the first-region report/viewer and choose the next approved retargeting scope. Focused cleanup remains due before another milestone.
- Last verification: **2026-10-30** — [91 passing tests](../../outputs/ik-benchmark/validation/first-region/tests-retry.log), [independent three-run audit](../../outputs/ik-benchmark/validation/first-region/audit.json), and [five-frame browser review](../../outputs/ik-benchmark/validation/first-region/viewer-browser.json) with representative screenshots inspected.
