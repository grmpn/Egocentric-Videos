# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Planning** — requested camera/hand trajectory comparison; broader simulation acceptance remains open.
- Active plan: [iPhone trajectory comparison, revision 1](plans/iphone-trajectory-comparison.md), draft awaiting explicit approval. [iPhone export revision 2](plans/iphone-contract3-export.md) remains fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: full 1,286-frame human episode and all three robot regions (1,069 frames) delivered to `~/dev/alex-trajectory-playback/datasets`; [acceptance evidence](topics/lerobot-pipeline.md#iphone-test-export--2026-11-17).
- Current work: full iPhone input and pairwise disagreement selected; draft specifies shared hand/gravity/depth inference, initial-pose alignment, graphs and runtime accounting. No comparison implementation or inference started.
- Blockers or decisions: plan approval pending; no ground truth, so disagreement cannot rank accuracy. Existing region-3 test override, unannotated language, scale/floor and [acceleration proxy](decisions/ik-benchmark-limits.md) limitations remain.
- Next action: approve or revise the comparison plan, then implement and run its controlled experiment; broader simulation acceptance remains outstanding.
- Last verification: **2026-11-19** — planning/source inspection located historical iPhone assets beneath `outputs/old/`; [planning evidence](logs/2026-11.jsonl), event `20261119-trajectory-comparison-001`. Latest execution acceptance remains the linked 2026-11-17 export.
