# Milestone 3, Part 1 — Gravity-aligned hand and camera trajectories

Approved revision 1 · 2026-10-14 · Approval: `20261014-gravity-implementation-001` in the [action log](../logs/2026-10.jsonl).

## Objective and deliverable

Provide a reusable post-processing workflow that converts an existing HaWoR run
into one Z-up, gravity-aligned hand/camera trajectory for later fixed-base
retargeting. Demonstrate it on the bundled HaWoR example, delivering a reloadable
derived export, its reversible world-to-aligned transform, original/aligned 3D
plots, and an estimation/verification report. This adds consumable data to the
spec's visual deliverable.

The [Stage 3 reference](../topics/stage-3-retargeting.md) owns the three-part scope
and proposed conventions. Work can precede the iPhone capture by the user's
2026-10-14 instruction; Milestone 2's pilot acceptance remains outstanding.

## Scope and boundaries

- Accept a completed project HaWoR run with prepared RGB, exact frame mapping,
  native scaled camera poses, and world hand export. Reuse existing bundled
  evidence after checking compatibility; rerun HaWoR only if necessary.
- Follow HuRo's gravity-estimation workflow: rank sharp frames, run pinhole
  GeoCalib with the existing focal prior, transform camera-frame up estimates
  into the shared world, apply the documented frame/sign and MAD filters, then
  normalize the component-wise median. Keep settings configurable and record
  selected frames, rejection/sign decisions, support and angular dispersion.
  Insufficient, degenerate, or wholly rejected evidence fails explicitly.
- Apply one proper rotation per clip, with +Z up and gravity toward −Z. Use a
  deterministic perpendicular-axis rule with a nonparallel fallback; preserving
  SLAM X is unnecessary. Keep the world origin and scale. Rotate both hands and
  camera poses consistently, accounting for MANO's root offset when producing
  physical wrist/hand geometry. Preserve articulation, shape, hand identity,
  exact timestamps, missing-data masks and confidence/provenance.
- Preserve original world/canonical data and annotations; save separate derived
  artifacts without changing the LeRobot schema. Pin the necessary GeoCalib
  dependency/model without disrupting working HaWoR or annotation environments.
- Exclude Parts 2–3 implementation, iPhone acceptance, robot assets/IK, workspace
  construction, base placement, segmentation, gripper mapping, simulation/control,
  scale correction, SLAM changes, smoothing, undistortion and IMU integration.

## Acceptance

- The user-facing command runs real GeoCalib on the bundled example and reloads
  the aligned export and transform. At least three retained frame estimates
  support a finite direction; report pre/post-filter dispersion and all fallback
  decisions. A failed estimate must not produce an accepted aligned trajectory.
- Focused checks cover known tilted directions, camera-to-world conversion and
  sign, deterministic axes near degeneracy, robust aggregation/outlier rejection,
  insufficient support, and transform inversion. Rotation orthogonality,
  determinant +1 and up-to-+Z alignment use float64 tolerance `1e-6`; saved geometry
  round trips and rigid hand/camera relationships use dtype-aware tolerances.
- Verify unchanged source arrays, timestamps, identities, masks and local hand
  parameters; check reconstructed wrist/hand geometry to catch MANO-offset errors.
- Inspect equal-scale original/aligned 3D plots showing both hands, camera path,
  axes, estimated up/down and invalid/infilled spans, plus representative RGB
  frames with projected vertical/horizon cues. Save commands, settings, model
  revision, diagnostics and review findings with the run.

Passing establishes a reusable, internally consistent gravity-alignment step.
It does not establish absolute gravity/metric accuracy, heading, floor height,
robot feasibility, or completion of Milestone 2 or all of Stage 3.
