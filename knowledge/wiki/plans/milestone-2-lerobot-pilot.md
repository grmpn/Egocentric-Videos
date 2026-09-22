# Milestone 2 — Video-to-LeRobot pilot dataset

Draft revision 2 · 2026-09-22 · Not approved; approval event pending.

## Objective and deliverable

Deliver a workflow accepting a local `.mp4` video and dataset directory, producing a
LeRobotDataset **v3.1** episode, and appending to an existing compatible dataset.
Produce a versioned pilot with 1–2 deliberate, high-quality iPhone demonstrations
for Milestone 3, reviewed plan/subtask
annotations, a data card, and a small Eidon validation report.

## Scope and boundaries

- All videos, including iPhone recordings, must be provided as `.mp4`. Other
  formats and conversion from them are outside project scope for now. Reuse
  preparation, unchanged HaWoR, world export, and review, preserving sources and
  frame mapping. Each clip or selected interval becomes one episode.
- Preserve synchronized RGB, timestamps in seconds, left/right identity,
  HaWoR's clip-local world coordinates and claimed metres, camera metadata,
  missing-frame validity, confidence, and detection/infill provenance. Retain
  unknown confidence. Derive a documented, reversible hand-centered
  canonical representation while keeping world trajectories primary. Clip-local
  worlds have independent origins; confidence does not measure geometric accuracy.
- Create or append at the supplied local directory. Validate dataset version,
  features, and timing/image compatibility before mutation. Preserve existing
  episodes and annotations; failed additions must leave a readable dataset.
  Record source identity and handle repeated additions explicitly.
- Use three short Eidon RGB segments, selected before inference across at
  least two tasks and two contributors.
  Download selected recordings only; record IDs, revisions, hashes, and intervals.
  Use pinhole-suitable footage; document camera information and
  approximations. [Source verification limits](../../raw/Sources/Eidon-LeRobot-Review.md)
  remain explicit. IMU integration is outside scope.
- Run `lerobot-annotate`, limit output to plans/subtasks, and review results. Disable
  interjections and VQA. Pin compatible dependencies without breaking the
  existing HaWoR environment; select the annotation backend before execution.
- Exclude hand-detector or motion-infiller fixes, lens undistortion, synthetic
  robot embodiment, retargeting, policy training, and large-scale evaluation.
  [HuRo](../../raw/Sources/HuRo-Review.md) informs investigation only.

## Subphases

1. Establish creation, append, and reload with preserved trajectory
   contracts and the canonical transform.
2. Process and visually review the iPhone demonstrations and selected Eidon
   segments; retain failed attempts and report runtime/resource use.
3. Annotate, reload, and review; finalize version/provenance records,
   the data card, and acceptance evidence.

## Acceptance

- The user-facing workflow creates a dataset, appends a second distinct episode
  after reopening it, and reloads both through the pinned LeRobot reader.
  Focused checks cover synchronization, indexing, units, transform inversion,
  hand identity, missing data, unsupported formats, incompatible inputs, failed append, and preservation
  of prior episodes and annotations.
- The 1–2 iPhone episodes cover the intended task with reviewed overlays and
  world/canonical previews, including grasp/release, gaps, and infill transitions.
  Preserve wrist pose and finger geometry needed by Milestone 3. Unsuitable
  reconstruction remains a blocker; do not remove task-essential motion to pass.
- Report all three Eidon attempts, including failures and visible quality limits.
  Load one successful Eidon episode through this workflow.
- Run annotation on the pilot and verify saved plans/subtasks against video
  timestamps after reload. Record commands, versions, and review evidence.
  Passing establishes integration and reviewed examples, not metric accuracy,
  general HaWoR robustness, or robot feasibility.
