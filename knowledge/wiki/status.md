# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Implementing** — requested camera/hand trajectory comparison; broader simulation acceptance remains open.
- Active plan: [iPhone trajectory comparison, revision 1](plans/iphone-trajectory-comparison.md), approved 2026-11-19 with resolution reduction allowed if needed. [iPhone export revision 2](plans/iphone-contract3-export.md) remains fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: full 1,286-frame human episode and all three robot regions (1,069 frames) delivered to `~/dev/alex-trajectory-playback/datasets`; [acceptance evidence](topics/lerobot-pipeline.md#iphone-test-export--2026-11-17).
- Current work: [comparison implementation](topics/trajectory-comparison.md); shared hands/gravity complete, representative hand overlays reviewed, 11 focused checks pass. Sequential full-video camera runs started.
- Blockers or decisions: AMB3R setup resolved; downloaded mirror matches its published checksum and official file size, but original-file hash comparison is unavailable. No ground truth. Existing simulation/export limitations remain.
- Next action: finish the three camera runs, then validate pairwise metrics, scale evidence and trajectory graphs; broader simulation acceptance remains outstanding.
- Last verification: **2026-11-20** — GPU extension/import checks and shared-hand visual inspection passed; [execution evidence](logs/2026-11.jsonl), events `20261120-trajectory-comparison-002` through `004`. Latest execution acceptance remains the linked 2026-11-17 export.
