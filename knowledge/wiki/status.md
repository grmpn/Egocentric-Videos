# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Validating** — approved benchmark scope fulfilled; the broader simulation demonstration still has limit/tracking/collision failures.
- Active plan: [IK benchmark and gripper integration, approved revision 1](plans/milestone-3-ik-benchmark.md), fulfilled with [acceptance evidence](experiments/ik-benchmark-iphone.md).
- Deliverable: reusable 100-point benchmark, preserved experiments/updating report, Config 2 palm/opening IK, missing-hand penalty and interactive viewer delivered. Roadmap simulation acceptance remains open.
- Completed outcome: full-iPhone scores **34.831 / 71.885 / 71.489** for wrist reference / Config 2 / Config 2 plus penalty. Extra penalty reduces missing-hand velocity RMS by **46.45%**. [Local report](../../outputs/ik-benchmark/REPORT.md).
- Current work: ready for user review; final viewer at [localhost:8081](http://localhost:8081), with artifacts/reopen command in the acceptance page. No further tuning or milestone transition started.
- Blockers or decisions: acceleration uses an explicit [10 rad/s² benchmark proxy](decisions/ik-benchmark-limits.md). Final run retains 270 joint-infeasible and 73 colliding frames, plus orientation failures. Physical scale/contact/dynamics and Milestone 2 [pilot acceptance](plans/milestone-2-lerobot-pilot.md) remain unresolved.
- Next action: review report/viewer and choose the next approved retargeting scope. Focused cleanup remains due before another milestone.
- Last verification: **2026-10-29** — [134 passing tests](../../outputs/ik-benchmark/validation/final-tests.log), [independent three-run audit](../../outputs/ik-benchmark/validation/audit.json), and [14-frame browser review](../../outputs/ik-benchmark/validation/viewer-browser.json) with representative screenshots inspected.
