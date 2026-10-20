# Project status

- Current milestone: **3 — Fixed-base trajectory preparation**. Approved Parts 1–3 and MANO comparison remain complete; the wrist-alignment amendment is approved.
- Stage: **Implementing** — approved wrist endpoint change; prior positional acceptance remains valid for TCP matching.
- Active plan: [Wrist alignment amendment, approved revision 1](plans/milestone-3-wrist-alignment.md). Fulfilled plans: [Part 3 revision 2](plans/milestone-3-part-3-placement-and-segmentation.md), [Part 2 revision 2](plans/milestone-3-part-2-robot-workspace.md), [Part 1](plans/milestone-3-part-1-gravity-alignment.md).
- Deliverable: base-frame hand trajectories, positional IK witnesses, annotated video and interactive playback using one fixed base per retained episode.
- Completed outcome: two bundled episodes (2.53 s / 1.50 s), combined SDF/IK coverage 96.05% / 100%; all 240 successful IK samples independently verified, maximum target error 0.152 mm. MANO comparison verified across 241 valid hand frames; 37 focused/regression tests and interactive review passed. [Acceptance and artifacts](experiments/retargeting-bundled.md).
- Current work: diagnosed the apparent wrist offset and drafted consistent wrist workspace/IK/preview changes. Current implementation still targets TCPs and replays precomputed per-frame IK; see the [contract and diagnosis](topics/stage-3-retargeting.md#part-3-placement-and-ik-contract).
- Blockers or decisions: no blocker to the approved `LEFT/RIGHT_WRIST_X_LINK` endpoint change. Existing IK failure/joint jumps, collision/dynamics, scale, gravity and floor-height limits remain. Milestone 2 iPhone [pilot acceptance](plans/milestone-2-lerobot-pilot.md) and Eidon review remain outstanding.
- Next action: implement wrist workspace/IK/preview consistency and regenerate the bundled demo. Focused cleanup remains due before another milestone; preserve acceptance evidence.
- Last verification: **2026-10-20**, replayed FK for all 240 successful arm samples: TCP error ≤0.152 mm; robot wrist offset ≈23.8 cm. `20261020-wrist-alignment-001` in the [action log](logs/2026-10.jsonl). Prior MANO/browser acceptance remains dated 2026-10-16.
