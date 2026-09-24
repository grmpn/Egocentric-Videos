# Project status

- Current milestone: **2 — Record and annotate a pilot dataset**.
- Stage: **Blocked**.
- Active plan: [Video-to-LeRobot pilot, approved revision 2](plans/milestone-2-lerobot-pilot.md), approved 2026-09-23.
- Deliverable: reusable LeRobot v3.1 creation/append, 1–2 annotated iPhone demonstrations for Milestone 3, selected Eidon validation, and a data card.
- Completed outcome: integration is implemented; all three fixed Eidon attempts are reported. Cooking and cleaning reload as two episodes/240 frames, with prior episode files preserved after append. Laundry failed the unchanged timing gate. [Validation and visual quality evidence](experiments/milestone-2-eidon-validation.md).
- Current work: desktop setup is complete, including MANO, compiled GPU libraries, local Qwen serving, and the bundled video-to-annotation smoke. [Reproduction and evidence](../../environment/README.md#native-desktop-and-annotation-environments).
- Blockers or decisions: iPhone demonstrations remain unrecorded. The 4-bit Qwen backend serves successfully on this 24 GiB GPU. Eidon intrinsics and physical scale remain unverified.
- Next action: obtain the intended iPhone MP4s, then process, annotate and review them using the approved plan. No next-milestone work is authorized.
- Last verification: **2026-09-24**; 88 project tests passed across two runs, plus six focused checks after the desktop fixes. All 34 HaWoR preflight checks and four compiled CUDA checks pass. Bundled inference/export/render completes in 68.920 s; LeRobot reloads 121 frames with actual plan/subtask labels at 0 and 2 s. Representative visuals were inspected; pilot quality remains unverified. Evidence: `20260924-desktop-setup-014`/`015` in the [action log](logs/2026-09.jsonl).
