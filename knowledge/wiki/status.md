# Project status

- Current milestone: **2 — Record and annotate a pilot dataset**.
- Stage: **Implementing**.
- Active plan: [Video-to-LeRobot pilot, approved revision 2](plans/milestone-2-lerobot-pilot.md), approved 2026-09-23.
- Deliverable: reusable LeRobot v3.1 creation/append, 1–2 annotated iPhone demonstrations for Milestone 3, selected Eidon validation, and a data card.
- Completed outcome: dataset creation/append/reload, reversible canonical poses, provenance, atomic publication, and protected plan/subtask annotation are implemented; [contract, validation scope, and limitations](topics/lerobot-pipeline.md). HaWoR outputs are organized by milestone.
- Current work: Eidon 56 completed HaWoR and reloads as a 120-frame LeRobot episode after fixing a legacy-library conflict. Eidon 204 failed the unchanged timing gate; Eidon 1566 is running. Review/acceptance remain pending.
- Blockers or decisions: iPhone demonstrations are not yet recorded (user confirmed). The default 27B annotation model exceeds this laptop's 8 GiB GPU; real VLM execution/review is deferred to a suitable Linux desktop. Eidon intrinsics remain approximate.
- Next action: poll the live Eidon execution, inspect all attempts and world/canonical overlays, verify a successful dataset reload, and record the validation report. Then process the iPhone recordings and run real annotation when available.
- Last verification: **2026-09-23**; 88 full-suite tests passed, then 6 focused checks passed after canonical-plot/annotation additions; CLI help, dependency compatibility and documentation checks passed. See `20260923-m2-implementation-008` in the [action log](logs/2026-09.jsonl). Fixture VLM responses do not establish annotation quality.
