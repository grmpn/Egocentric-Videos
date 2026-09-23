# Project status

- Current milestone: **2 — Record and annotate a pilot dataset**.
- Stage: **Blocked**.
- Active plan: [Video-to-LeRobot pilot, approved revision 2](plans/milestone-2-lerobot-pilot.md), approved 2026-09-23.
- Deliverable: reusable LeRobot v3.1 creation/append, 1–2 annotated iPhone demonstrations for Milestone 3, selected Eidon validation, and a data card.
- Completed outcome: integration is implemented; all three fixed Eidon attempts are reported. Cooking and cleaning reload as two episodes/240 frames, with prior episode files preserved after append. Laundry failed the unchanged timing gate. [Validation and visual quality evidence](experiments/milestone-2-eidon-validation.md).
- Current work: independent integration/Eidon work is committed. Pilot acceptance is waiting for the missing iPhone captures and real VLM annotation/review; no validation job remains running.
- Blockers or decisions: iPhone demonstrations are not yet recorded (user confirmed). The default 27B annotation model exceeds this laptop's 8 GiB GPU; real VLM execution/review awaits a suitable Linux desktop. Eidon intrinsics and physical scale remain unverified.
- Next action: process iPhone MP4s when recorded, review task-essential motion, then run/review plan/subtask annotation on the desktop. No next-milestone work is authorized.
- Last verification: **2026-09-23**; full suite previously passed 88 tests; the extended real-CLI shared-file preservation case passed in 51.94 s. Both Eidon episodes passed numeric/timing/hash/inverse checks and visual review recorded quality limits. Evidence and the renewed blocker audit: `20260923-m2-implementation-013`, `016`, and `017` in the [action log](logs/2026-09.jsonl). Real VLM quality remains untested.
