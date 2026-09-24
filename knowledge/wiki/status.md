# Project status

- Current milestone: **2 — Record and annotate a pilot dataset**.
- Stage: **Implementing**.
- Active plan: [Video-to-LeRobot pilot, approved revision 2](plans/milestone-2-lerobot-pilot.md), approved 2026-09-23.
- Deliverable: reusable LeRobot v3.1 creation/append, 1–2 annotated iPhone demonstrations for Milestone 3, selected Eidon validation, and a data card.
- Completed outcome: integration is implemented; all three fixed Eidon attempts are reported. Cooking and cleaning reload as two episodes/240 frames, with prior episode files preserved after append. Laundry failed the unchanged timing gate. [Validation and visual quality evidence](experiments/milestone-2-eidon-validation.md).
- Current work: provisioning and checking the user-requested Linux desktop environment (RTX 4090, 24 GiB VRAM); prior integration/Eidon work is committed.
- Blockers or decisions: iPhone demonstrations remain unrecorded; desktop MANO assets and CUDA 11.7 installation are pending. The 27B annotation backend needs quantization or offload on this 24 GiB GPU. Eidon intrinsics and physical scale remain unverified.
- Next action: finish isolated HaWoR, LeRobot, and VLM dependencies; verify GPU kernels and annotation serving, then process/review supplied iPhone MP4s. No next-milestone work is authorized.
- Last verification: **2026-09-24**; desktop LeRobot checks pass all 88 tests across two runs, and HaWoR CPU checks pass 85 (LeRobot module skipped in that isolated runtime). Both Torch GPU smoke tests and dependency checks pass. CUDA extension builds await missing development headers; serving/inference and real VLM quality remain unverified. Evidence: `20260924-desktop-setup-002`/`003` in the [action log](logs/2026-09.jsonl) and [environment guide](../../environment/README.md).
