# Milestone 3 — Joint base and trajectory optimization

Approved revision 5 · 2026-10-21 · User explicitly requested that retargeting never trust infilled frames and that the iPhone workflow be rerun: `20261021-no-infill-001` in the [action log](../logs/2026-10.jsonl).

Earlier revisions and outcomes remain in Git and the [bundled evidence](../experiments/joint-base-bundled.md). This amendment changes observation eligibility; it preserves the latest weights, geometry and solver limits.

## Objective and deliverable

Treat every infilled hand sample as missing data throughout retargeting, then
produce a new iPhone trajectory, report and reviewed playback using the existing
960×540 input's reconstruction/alignment. Preserve the previous run for comparison.

## Scope and boundaries

- Define eligible hand observations per frame as `export_valid` and not
  `motion_infilled`. Exclude ineligible hand positions/orientations from fitting,
  workspace queries, IK acceptance and observed-frame denominators. A directly
  estimated opposite hand remains eligible. Frames with neither hand eligible
  remain unknown and count toward the existing gap limit.
- Apply the rule consistently to both maintained retargeting methods, comparison
  metrics, annotated video and interactive playback. Preserve original source
  geometry, validity, infill provenance, confidence, hand identity, timestamps,
  metres/radians and coordinate transforms. Export a distinct retargeting mask;
  do not rewrite HaWoR's original validity. Reject missing/malformed infill
  provenance on new input rather than silently trusting it.
- Joint trajectories may still contain regularized predictions within retained
  regions, as for existing missing data. Mark these as unobserved predictions;
  never assign observed success/errors or show infilled human targets as data.
  Preserve historical saved runs and make their earlier observation policy clear
  when viewed, without rewriting old acceptance results.
- Reuse the saved iPhone HaWoR and gravity results. Keep hand residual weights
  1.0, posture 0.5, 5 cm tool-local +X match offset, alternate-frame base solve,
  camera rotation objective, segmentation, seeds, attempts and evaluation budgets.
  No reconstruction changes, tuning, new dependencies, retiming, rescaling,
  collision/dynamics certification or controller/hardware execution.

## Acceptance

- Focused tests must demonstrate that changing infilled geometry cannot change
  fitted observations/objectives, acceptance or diagnostics; cover mixed-hand
  availability, entirely missing intervals, provenance validation, prediction
  labels, visualization and historical compatibility.
- Rerun the real iPhone retargeting workflow. Independently verify the observation
  mask, absent success/error claims for excluded hands, source-array preservation,
  timestamps, joint bounds, FK/offset transforms, sampling and region gates.
- Retain ≤5 mm / ≤10° per eligible hand, >95% passing observed frames, ≤0.2 s
  unknown/failure gaps, ≥1 s duration and reduced acceleration RMS. Report changed
  coverage and failed gates honestly. Compare the preserved run on common eligible
  observations; do not interpret a changed denominator as improved reconstruction.
- Inspect representative directly estimated, infilled, mixed and boundary frames
  in annotated video and playback. Save tests, reports and visual evidence under
  `outputs/retargeting/iphone-no-infill-20261021/`. Completion means verified
  exclusion and a reproducible run, even if no region qualifies as a demo.
