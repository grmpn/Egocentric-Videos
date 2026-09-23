# Project status

- Current milestone: **2 — Record and annotate a pilot dataset**.
- Stage: **Implementing**.
- Active plan: [Video-to-LeRobot pilot, approved revision 2](plans/milestone-2-lerobot-pilot.md), approved 2026-09-23 by the instruction to implement it.
- Deliverable: reusable LeRobotDataset v3.1 creation/append, 1–2 annotated iPhone demonstrations for Milestone 3, selected Eidon validation, and a data card.
- Completed outcome: Milestone 1 accepted; [evidence and limitations](experiments/milestone-1-baseline.md). Existing evidence is now organized by milestone; all 82 baseline tests pass.
- Current work: establish an isolated LeRobot environment, creation/append and canonical trajectory contracts, and organize HaWoR evidence by milestone.
- Blockers or decisions: iPhone demonstrations are not yet recorded (confirmed by user); Eidon camera information and local annotation feasibility remain unverified. This WSL machine has an RTX 3070 Laptop GPU with 8 GiB VRAM (about 5.8 GiB free at preflight).
- Next action: validate the pinned LeRobot reader/writer and annotation command without altering the HaWoR environment, then process the three selected Eidon segments.
- Last verification: **2026-09-23**, clean initial working tree and GPU capacity preflight; see `20260923-m2-implementation-001` in the [action log](logs/2026-09.jsonl). No new inference or dataset acceptance yet.
