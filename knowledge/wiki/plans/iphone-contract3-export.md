# iPhone contract 3.0 export and region acceptance

Approved · revision 2 · 2026-11-17 · User requested full export, then explicitly
selected collision/joint-limit-only region acceptance with tracking failures retained.
Approval event: `20261117-iphone-contract3-003` in the [November log](../logs/2026-11.jsonl).
This narrowly amends the fulfilled [export-refresh plan](lerobot-export-refresh.md).

## Objective and deliverable

Export the complete saved iPhone reconstruction and all three robot regions as
contract 3.0 LeRobot datasets under `~/dev/alex-trajectory-playback/datasets`.
Reuse existing perception, gravity alignment, gripper mapping and joint solves;
refresh evaluation and encoding only where the new contract requires them.

## Scope and boundaries

- Retain all 1,286 prepared frames in one human episode, with structured MANO
  geometry, hand provenance, aligned camera poses and synchronized RGB.
- Use the three existing frozen full-base IK region solves, preserving original
  benchmark observation exclusions and all source artifacts. Do not retune IK,
  rerun perception, change physical units or alter source-frame references.
- Change the default 85% region-export gate to count only frames with finite
  solved configurations, no self-collision and no joint position, velocity or
  acceleration violations. Include coupled fingers and locked-joint constraints.
  A region qualifies when at least 85% of its complete frames pass those checks.
- Remove geometric/tracking acceptance as a separate export gate. Preserve those
  failures, hand-observation requirements and all existing per-component action
  masks for training. Keep masked statistics and source-linked RGB behavior.
  Retain every frame in accepted regions; export acceptance is not a declaration
  that all frames are valid or suitable for physical playback.
- Permit an explicit test-dataset override to include regions failing the 85% gate.
  Preserve the true gate result and log the override; label the dataset as test
  data. This iPhone export includes region 3 using the user-approved override.
- Keep geometric acceptance, action-valid ratios and the new eligibility basis
  explicit in processing diagnostics. Update the ordinary exporter and its
  documentation so subsequent runs use the same policy. Dataset feature shapes
  and contract version remain unchanged.
- Stage and verify locally before transferring datasets to the requested sibling
  project. Keep reports outside individual dataset roots. No hardware execution,
  solver changes, policy training or broader simulation acceptance is authorized.

## Acceptance

Exercise production create/append and region filtering with focused tests proving
that tracking failures do not block qualifying regions, collision and joint-limit
failures do, and training masks remain unchanged. Verify full iPhone numeric data,
source indices, local times, FK actions, provenance and decoded RGB boundaries
through official readers. Inspect representative RGB and trajectory views.
Record accepted/rejected counts, annotation status, transfer verification and
limitations under `outputs/iphone-contract3-20261117/`; update status and action
history and commit the implementation and documentation together.
