# Milestone 3, Part 3 — Manipulation regions and robot-base placement

Approved revision 1 · 2026-10-16 · User requested implementation; approval: `20261016-part-3-implementation-001` in the [action log](../logs/2026-10.jsonl).

## Objective and deliverable

Use the [user spec](../../../Stage-3-Spec.md) to identify candidate
manipulation episodes in the bundled HaWoR example, fit one fixed Purdue Alex base
per episode, and export base-frame hand trajectories and scikit-robot IK results.
Deliver an annotated video, interactive robot/trajectory playback, and
reloadable episode, transform, feasibility and joint-trajectory evidence.

## Scope and boundaries

- Reuse the [Part 1/2 contracts](../topics/stage-3-retargeting.md): Z-up
  camera positions, physical wrists, and preferred 10-million-sample-per-arm,
  2 cm workspace tensors. Preserve source data, timestamps, metres, hand identity,
  confidence and validity; do not substitute MANO translation parameters for wrists.
- Lightly smooth camera positions for segmentation only. From each segment's
  first frame, measure XY displacement; at **0.3 m sustained for 0.3 s**, close
  at the first crossing and restart on the next frame. Discard segments shorter
  than **1 s**. Configure smoothing and thresholds; use timestamps for durations.
- Optimize **x, y, z and yaw**, keeping roll/pitch gravity-aligned and one base
  fixed throughout each candidate. Free Z is a placement parameter, not inferred
  floor height. Save aligned-to-base and composed original-world-to-base transforms.
  Maximize feasible-frame count using each wrist's corresponding SDF, requiring
  **distance ≤ −0.03 m**. Record initialization/search settings; claim no global optimum.
- Validity rule: a frame with at least one `export_valid` hand passes
  only if every available hand passes. Missing hands remain unverified; all-missing
  frames are unknown. Out-of-domain queries cannot pass. Report observation coverage
  separately. A region requires **>95%** passing observed frames, **≤0.2 s**
  consecutive nonpassing/unknown time, and **≥1 s** duration; reject empty denominators.
- Evaluate every video frame under each optimized transform, then extend contiguous
  intervals around their seeds while preserving those criteria. Resolve overlaps
  deterministically; do not join disconnected intervals or change base within one.
- IK scope: map physical wrists directly to corresponding EZGripper TCP
  positions, orientation unconstrained, using the pinned model/arm chains and
  locked-joint settings. Seed successive solutions from previous successes; verify
  URDF position bounds and FK residual **≤5 mm**. Preserve failures and gaps;
  report joint discontinuities. Solver failure does not prove unreachability.
- Exclude gripper actuation, collision/orientation constraints, dynamic-limit
  certification, retiming, floor calibration, simulation/control, dataset changes
  and workspace gap filling. This is a positional kinematic demonstration.

## Acceptance

- Exercise the production workflow on the bundled example. Save baseline results;
  allow documented demo-only gap/duration adjustments, retaining **>95%**, the
  **3 cm** margin and IK checks. At least one demonstrated interval must meet
  episode criteria for both SDF and IK results, reported separately; zero qualifying
  intervals leaves the demo incomplete.
- Focused checks cover sustained-crossing boundaries, short/tail segments,
  timestamps, transform direction/inversion, hand/SDF identity, missing/out-of-domain
  inputs, strict percentage/gap rules, expansion/overlap handling, synthetic known
  placements, IK failures, FK residuals, joint bounds and export reload.
- Inspect annotated video and movable-camera playback showing initial/final
  intervals, fixed bases, wrists/TCPs and feasible/infeasible/unknown/IK-failed frames.
  Save commands, settings, logs, coverage, residuals and review evidence under
  `outputs/retargeting/`. Sampled occupancy, metric scale, gravity accuracy,
  collision clearance and dynamic executability remain uncertified.
