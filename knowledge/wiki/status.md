# Project status

- Current milestone: **3 — Retarget hands and trajectories in simulation**.
- Stage: **Planning** — cleanup/integration draft awaiting approval; broader simulation acceptance remains open.
- Active plan: [Codebase cleanup and integrated pipeline, revision 2](plans/codebase-cleanup-and-pipeline.md) (draft). Prior [held-out evaluation scope](plans/milestone-3-ik-tuning.md) is fulfilled.
- Milestone deliverable: repeatable simulation demonstration, exported robot trajectories and limit-check evidence; not yet accepted. Proposed cleanup deliverable: one MP4-to-annotated-robot-LeRobot workflow and a smaller, organized repository.
- Completed outcome: four held-out runs independently audited; full-IK/SDF scores **96.115 / 73.812** (region 2), **77.414 / 37.840** (region 3). [Report and evidence](experiments/ik-benchmark-iphone.md#held-out-regions-2-and-3--2026-11-03).
- Current work: planning only. Defaults remain **full base + IK with frozen held-out slack5-orientation8 settings**, **one full video per LeRobot episode**, and manipulation intervals in metadata. Revision 2 removes hand-only compatibility and explicitly retires `video_to_dataset.py` and other deprecated scripts/code, preserving historical datasets/evidence. Implementation and artifact relocation have not started.
- Blockers or decisions: explicit plan approval pending. Existing exporter has no robot-action fields. Environment consolidation requires compatibility checks. Held-out iteration caps, tracking/collision failures and the [10 rad/s² acceleration proxy](decisions/ik-benchmark-limits.md) remain limitations.
- Next action: review/approve the cleanup plan, then migrate evidence/defaults and integrate the requested pipeline. Cleanup is now planned before another milestone.
- Last verification: **2026-11-03** — static inspection of entry points, configs, environment declarations and saved held-out settings for this draft; [prior numerical audits](experiments/ik-benchmark-iphone.md#held-out-regions-2-and-3--2026-11-03) remain the latest runtime evidence. No new solves or viewer review.
