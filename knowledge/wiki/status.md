# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Planning** — requested TACO ground-truth benchmark; broader simulation acceptance remains open.
- Active plan: [TACO hand-trajectory benchmark, draft revision 1](plans/taco-hand-trajectory-benchmark.md), awaiting explicit approval. Prior iPhone comparison and export plans remain fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted.
- Completed outcome: all three 1,286-frame camera runs, shared hands/gravity/depth, pairwise metrics and graphs verified; [comparison acceptance](experiments/iphone-trajectory-comparison.md). Prior [all-region export](topics/lerobot-pipeline.md#iphone-test-export--2026-11-17) remains delivered.
- Current work: scope five **150-frame** TACO clips, all requested accuracy/resource metrics, per-method component FPS and wrist plots; [source/feasibility review](experiments/taco-benchmark-preflight.md).
- Blockers or decisions: plan approval pending; StableHand's released preprocessing is incomplete and its evaluation inputs need a GT-leakage audit. TACO geometry/gravity, HandFlow bimanual adaptation and camera-motion sufficiency remain unverified. Existing simulation limitations remain.
- Next action: approve or revise the benchmark plan, then validate data and method preprocessing before timed runs.
- Last verification: **2026-11-24** — static official-source review and RTX 4090 visibility; no TACO inference or accuracy results. Event `20261124-taco-planning-001` in the [execution evidence](logs/2026-11.jsonl). Prior [iPhone comparison acceptance](experiments/iphone-trajectory-comparison.md) remains unchanged.
