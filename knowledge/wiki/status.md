# Project status

- Current milestone: **2 — Record and annotate a pilot dataset**.
- Stage: **Blocked**.
- Active plan: [Video-to-LeRobot pilot, approved revision 2](plans/milestone-2-lerobot-pilot.md), approved 2026-09-23.
- Deliverable: reusable LeRobot v3.1 creation/append, 1–2 annotated iPhone demonstrations for Milestone 3, selected Eidon validation, and a data card.
- Completed outcome: integration is implemented; all three fixed Eidon attempts are reported. Cooking and cleaning reload as two episodes/240 frames, with prior episode files preserved after append. Laundry failed the unchanged timing gate. [Validation and visual quality evidence](experiments/milestone-2-eidon-validation.md).
- Current work: restored all three Eidon sources for the requested annotation retry. Cooking/cleaning pass CPU preparation; laundry reproduces its timing failure. [Review outputs and retry evidence](experiments/milestone-2-eidon-validation.md#desktop-annotation-retry--2026-09-25).
- Blockers or decisions: today's NVIDIA update left loaded driver 580.159.03 mismatched with installed 580.178.04; GPU inference is blocked until restart. iPhone demonstrations remain unrecorded; Eidon intrinsics and physical scale remain unverified.
- Next action: restart the desktop, verify GPU availability, then complete Eidon HaWoR/create/append and local plan/subtask annotation with manual review. Subsequently obtain/process the intended iPhone MP4s. No next-milestone work is authorized.
- Last verification: **2026-09-25**; restored 766,650,813 source bytes, recorded hashes/ffprobe, prepared two 120-frame clips and inspected representative RGB. No new inference or labels. See `20260925-eidon-annotation-002`–`005` in the [action log](logs/2026-09.jsonl). The [2026-09-24 bundled GPU/annotation success](../../environment/README.md#native-desktop-and-annotation-environments) remains historical evidence, not current GPU availability.
