# Milestone 3 — GPU trajectory IK

Approved revision 1 · 2026-10-22 · User explicitly approved GPU rewrite and latest-configuration rerun; see `20261022-gpu-ik-004` in the [action log](../logs/2026-10.jsonl).

## Objective and deliverable

Reduce the runtime of the existing two-stage joint/base and trajectory IK using
the available RTX 4090. Deliver a reusable GPU solver backend, measured runtime
and quality comparisons, and a complete rerun of the latest iPhone configuration.
The latest run is the [1,000× temporal-smoothing experiment](../experiments/retargeting-iphone.md#stronger-temporal-smoothing),
whose CPU solve took 1,793.37 seconds. Acceleration does not imply an accepted
demonstration or a guaranteed speedup factor.

## Scope and boundaries

- Reuse the existing iPhone alignment, pinned robot, camera segmentation and
  both fitting stages. Move the expensive fitting work to CUDA, including
  residual/Jacobian evaluation and the numerical optimization where supported.
  Use established library implementations when they meet these requirements;
  new dependencies are allowed and must be pinned and justified.
- Preserve the mathematical objective: hand position and orientation, camera
  orientation, posture, source-time velocity and acceleration. Preserve hard
  joint/base bounds, coordinate frames, metres/radians, timestamps, hand identity,
  and exclusion of motion-infilled observations. Do not replace bounds with
  unchecked soft penalties or silently fall back to CPU.
- Retain the CPU solver as an explicit reference and compatibility option.
  Keep existing output consumers working and identify backend, hardware,
  precision, termination and runtime in reports. Different optimization paths
  may produce different local solutions; report those differences.
- Rerun the saved smoothing configuration with weights 1.0/0.5, unchanged
  observation settings, seeds, stride and retries. Preserve evaluation budgets
  where equivalent; disclose any backend-specific counting before interpreting
  timing. Do not silently reduce work to obtain a speedup. Preserve inputs,
  historical results and default objective weights.
- No reconstruction, retiming, hardware execution, collision/dynamic
  certification, further weight tuning or next-milestone work.

## Acceptance

- Verify representative CPU/GPU FK, objective and derivative agreement, including
  missing hands, irregular timestamps and joint limits; exercise the production
  workflow and preserve its acceptance gates.
- Benchmark representative regions with matched inputs and settings. Separate
  cold setup/compilation from repeated solve time and report quality alongside
  timing. Inspect a profile before claiming which bottleneck improved.
- Complete all four regions and export the trajectory, annotated video and
  report to a new directory under `outputs/retargeting/`. Independently check
  source/mask/timestamp preservation, bounds, saved FK/errors and unchanged
  demonstration gates. Compare pose passes/errors, motion and >0.5 rad
  joint-change frames, including region boundaries; inspect representative
  visualizations. Record failures and remaining uncertainty honestly.
- Update canonical documentation, evidence and status, run focused checks and
  commit the verified changes. A completed comparison may still report no
  accepted demonstration or insufficient acceleration.
