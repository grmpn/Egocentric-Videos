# Milestone 3 — Joint base and trajectory optimization

Approved revision 6 · 2026-10-21 · User explicitly requested a large temporal-smoothing experiment, optimization rerun and comparison including large-joint-change frame counts: `20261021-smooth1000-001` in the [action log](../logs/2026-10.jsonl).

Earlier fulfilled revisions remain in Git and the [bundled](../experiments/joint-base-bundled.md) and [iPhone evidence](../experiments/retargeting-iphone.md). This amendment authorizes the requested tuning experiment; implemented observation eligibility and acceptance remain unchanged.

## Objective and deliverable

Measure the effect of substantially stronger temporal penalties on the latest
iPhone retargeting result. Produce a separate trajectory, annotated video and
comparison reporting large joint-change frame counts, motion smoothness, pose
accuracy and unchanged demonstration gates for both runs.

## Scope and boundaries

- Reuse the existing 960×540 iPhone input, HaWoR reconstruction, gravity alignment
  and pinned robot. Preserve all sources and previous runs, timestamps, metres,
  radians, coordinate frames and hand identity. No reconstruction or retiming.
- Run the existing two-stage optimization with velocity and acceleration residual
  multipliers increased 1,000-fold to 1.0 and 0.5. Keep every other configuration
  value equal to the latest no-infill baseline, including hand weights 1.0,
  posture 0.5, 5 cm offset, stride 2, seeds, retries and evaluation budgets.
  Preserve the defaults; keep the experimental configuration with its outputs.
- Continue treating `export_valid & ~motion_infilled` as eligible hand data.
  Regularized predictions through missing intervals are included in robot-motion
  diagnostics but never counted as observed hand successes.
- Use the existing 0.5 rad threshold for large adjacent-frame joint changes.
  Count each later frame once when any of the 16 joints exceeds it; report arm
  and neck subsets, denominator and exact frame indices. Compare only finite
  consecutive poses within one region; report boundaries separately.
- No new solver features, dependencies, hardware execution, collision/dynamic
  certification or automatic adoption of experimental weights.

## Acceptance

- Finish the existing workflow and preserve outputs under
  `outputs/retargeting/iphone-smooth1000-20261021/`, including failures and solver
  termination. Record actual runtime separately from quality.
- Verify only the two intended settings differ; source arrays, observation masks,
  segmentation and timestamps match. Check bounds and saved FK/error consistency.
- Independently compute unique large-change frame counts, velocity/acceleration
  RMS, maximum joint step, pose errors and passing-frame counts for both outputs.
  Report per-region results and any changed restart/base selection.
- Preserve ≤5 mm / ≤10° pose tolerances, >95% observed-frame coverage, ≤0.2 s
  unknown/failure gaps, ≥1 s duration and acceleration-improvement requirement.
  Completion is an honest measured comparison, not a guaranteed accepted demo.
- Inspect trajectory plots and representative rendered frames. Update the existing
  iPhone evidence and status with results, limitations and next action.
