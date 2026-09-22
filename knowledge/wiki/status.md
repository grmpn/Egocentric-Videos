# Project status

- Current milestone: **2 — Record and annotate a pilot dataset**.
- Stage: **Planning**.
- Active plan: [Video-to-LeRobot pilot, draft revision 2](plans/milestone-2-lerobot-pilot.md); not approved.
- Deliverable: reusable video-to-LeRobotDataset v3.1 creation/append, 1–2 annotated iPhone demonstrations for Milestone 3, selected Eidon validation, and a data card.
- Completed outcome: Milestone 1 accepted on 2026-09-18 and merged into `main`; [acceptance, evidence, and limitations](experiments/milestone-1-baseline.md). No Milestone 2 execution evidence yet.
- Current work: draft 2 explicitly requires `.mp4` input, including iPhone recordings, and excludes other formats and their conversion. LeRobotDataset v3.1 remains the target for direct annotation.
- Blockers or decisions: plan approval pending. Selected Eidon camera geometry/intrinsics, task-length inference feasibility, and annotation backend/resources remain unverified. Detector/infiller fixes and undistortion are excluded.
- Next action: review and explicitly approve or revise draft 2, including its three-segment Eidon sample and acceptance criteria; then begin implementation. Capture task and annotation backend can be selected before their execution phases.
- Last milestone verification: **2026-09-18** for Milestone 1 only; see acceptance evidence. Planning did not rerun tests or inference.
- Last documentation verification: **2026-09-22**; see `20260922-m2-mp4-003` in the [action history](logs/2026-09.jsonl) for checks and limits.
