# Milestone 3 — Joint base and trajectory optimization

Approved revision 3 · 2026-10-20 · User-requested camera-position/posture experiment: `20261020-camera-posture-001` in the [action log](../logs/2026-10.jsonl).

Earlier approved revisions and their results remain at `985080b` (mean heading)
and `c280e01` (median heading), with [evidence](../experiments/joint-base-bundled.md).
This request supersedes the earlier exclusion of per-frame camera position fitting.

## Objective and deliverable

Extend the existing joint/base method with camera position alignment, then measure
higher neutral-posture weights on the bundled clip. Deliver saved trajectories,
current/legacy viewer support and a reproducible comparison of camera, wrist,
posture and motion quality. Preserve the original workspace and rotation-only
results. This is a controlled experiment, not a promise that higher weights improve
all objectives.

## Scope and boundaries

- Reuse the same aligned inputs, pinned Purdue Alex model and retained camera
  heuristic regions `[0,52)` and `[74,105)`. Preserve all source geometry, timestamps,
  metres/radians, confidence, validity and hand identity. Do not expand regions.
- Retain median horizontal camera-forward initialization, median camera position
  and the rotated neutral camera offset. Fit one shared base XYZ/yaw per region;
  roll/pitch remain gravity-aligned. Preserve wrist-origin position and mapped
  hand-orientation targets, the nominal optical frame and all fourteen arm plus
  two neck joints. Fingers remain fixed.
- Add the per-frame camera-centre position residual to both shared-base fitting
  and fixed-base trajectory smoothing, alongside existing camera rotation. Use a
  configurable 0.05 m residual scale initially; this is a weighted alignment
  objective, not a hard equality or an acceptance tolerance. Keep hard URDF bounds.
- Sweep neutral-posture residual multipliers 0.02, 0.1, 0.5 and 2.0, with other
  scales, initialization, retries, random seeds, region selection and stopping
  budgets held constant. The squared posture-cost multipliers are 1, 25, 625 and
  10,000 relative to the original. Preserve all attempts and termination messages.
- Save camera position errors and identify the new objective in reports/playback.
  Compare against the preserved rotation-only median run as an ablation. Report
  residual posture distance without hiding failed poses. No extra dependencies,
  rescaling, retiming, collision/dynamics certification, simulation or hardware.

## Acceptance

- Check analytic position Jacobians against finite differences in both stages,
  including base XYZ/yaw, neck joints and missing wrists. Verify changing camera
  translation changes the objective while initialization/regions are fixed.
  Independently replay camera/wrist FK, bounds and transforms; preserve/reload
  source arrays and keep failed/missing samples distinct.
- Retain the wrist gate: ≤5 mm and ≤10° for every observed hand in a passing frame,
  >95% passing observed frames, ≤0.2 s gaps, ≥1 s and nonempty denominator. Report
  accepted/rejected regions and before/after acceleration RMS for every trial;
  never weaken gates to make the experiment succeed.
- Run all four settings through the production workflow. Report camera position
  and angle errors, wrist errors/coverage, posture deviation, motion derivatives,
  retries and single-trial solve time separately from loading/export/rendering.
  Preserve the historical three-repeat workspace comparison without rerunning it.
- Inspect representative low/high-posture playback, failures, boundaries and a
  legacy rotation-only run. Save configs, reports, tests, independent audits and
  visual evidence under `outputs/retargeting/`. Experimental completion requires
  an honest comparison, including regressions or absence of qualifying regions.
