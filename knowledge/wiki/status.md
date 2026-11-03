# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — requested held-out evaluation complete; broader simulation acceptance remains open.
- Active plan: [IK configuration experiments, revision 6](plans/milestone-3-ik-tuning.md): frozen slack5-orientation8 on held-out regions 2 and 3.
- Deliverable: verified per-region benchmark scores, full solve timings and preserved trajectories for full-IK versus SDF base fitting followed by fixed-base IK.
- Completed outcome: all four runs independently audited. Full-IK/SDF scores: **96.115 / 73.812** on region 2; **77.414 / 37.840** on region 3. Total solve times **139.42 / 142.65 s**, **116.76 / 97.41 s** respectively. [Report and evidence](experiments/ik-benchmark-iphone.md#held-out-regions-2-and-3--2026-11-03).
- Current work: **no solves running**. Requested region 3 viewers open: **[full-base + IK](http://localhost:8080)** and **[SDF-base + IK](http://localhost:8081)**, with mapped target grippers and smoothed IK target paths. No viewer tests/review. Prior first-region 91.022 result and base-only comparison preserved.
- Blockers or decisions: all trajectory solves reached their configured 1000-evaluation caps. Region 3 tracking/collisions and SDF motion failures remain. No held-out tuning performed. CPU approximately 800 MHz; no system settings changed. The [10 rad/s² cap](decisions/ik-benchmark-limits.md) remains a proxy; physical simulation acceptance is open.
- Next action: user review of the held-out scores and both region 3 viewers; choose any follow-up before changing frozen settings. Focused cleanup remains due before another milestone.
- Last verification: **2026-11-03** — [region 2 audit](../../outputs/ik-benchmark-heldout-20261103/region-2/audit.json), [region 3 audit](../../outputs/ik-benchmark-heldout-20261103/region-3/audit.json), and [input/configuration checks](../../outputs/ik-benchmark-heldout-20261103/validation/preflight.json) passed. Saved numerical plots inspected; no viewer tests/screenshots/review.
