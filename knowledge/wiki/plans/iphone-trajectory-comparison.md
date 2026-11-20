# iPhone trajectory comparison: LingBot-Map, AMB3R-VO and HaWoR SLAM

Fulfilled 2026-11-20 · revision 1 with resolution allowance, approved 2026-11-19.
See [acceptance evidence](../experiments/iphone-trajectory-comparison.md).
Approval: `20261119-trajectory-comparison-003` in the
[November log](../logs/2026-11.jsonl).

## Objective and deliverable

Compare camera and left/right wrist trajectories from the three methods on the
full iPhone demonstration: 1,286 frames at 30 FPS, using the
960×540 working video initially. Lower resolution is authorized if runtime or
memory requires it; keep compared inputs consistent and record the reason. Deliver a reproducible comparison command, aligned
trajectories, pairwise disagreement tables, graphs and runtime measurements to
inform Milestone 3 reconstruction quality. The user selected pairwise disagreement;
this experiment cannot establish accuracy without ground truth.

## Scope and boundaries

- Preserve source, historical runs and frame/timestamp mappings. Supply
  identical frames to each method; record necessary native resizing, intrinsics,
  precision and keyframe settings. Use pinned upstream implementations/checkpoints:
  HaWoR masked DROID-SLAM, LingBot-Map and AMB3R-VO with the AMB3R base model.
- Run detection/camera-relative hand estimation once; cache geometry, identity,
  masks and observation validity for all three. Compose these same hand estimates
  with each camera trajectory. Score observed wrists; leave missing hands missing
  and exclude world-motion infilling and smoothing.
- Run GeoCalib once for the common initial reference frame. Gravity establishes
  orientation, not metric scale. Run Metric3D once per selected HaWoR keyframe,
  caching predictions for both HaWoR and LingBot. Use matching frames, pixel
  geometry, focal prior, masks and the same scale-fitting procedure; fit one
  positive global scale per method. Convert AMB3R's VO output using its own metric
  predictions, verifying consistency between depth,
  geometry and camera translation. Do not assume its exported poses are metres.
- Express every trajectory relative to its initial camera pose, then apply one
  shared gravity/heading rotation: Z up, initial horizontal camera-forward along
  +X, and +Y completing a right-handed frame. Starting camera transforms coincide.
  Record an axis fallback if forward is vertical. Apply the same
  transform to cameras and hands; do not fit rotation or scale to another
  trajectory or remove later drift.
- For each of the three pairs, separately score cameras, left wrists and right
  wrists on their respective common-valid timestamps across all methods. Report
  sample count/coverage, summed Euclidean distance, mean distance and RMSE in
  metres. Sum depends on sample count; it is not travelled distance.
  Plot equal-scale 3D paths, XY paths, coordinates and disagreement over time.
- Run methods sequentially on the same local GPU. Report wall time and effective
  FPS, separating loading, core inference, scaling/postprocessing and shared work.
  Measure shared hand/gravity work once; charge shared Metric3D only to its two
  consumers in assembled per-method totals. Identify startup/compilation overhead
  and label single-run timings. Exclude downloads and rendering from
  processing totals. No tuning sweep, backend adoption or robot/export changes.

## Acceptance

Complete three full-video runs. Verify frame alignment, units, pose direction,
proper rotations, identical starting transforms, shared-hand preservation and
validity-aware metrics through focused checks and numeric inspection.
Inspect trajectory graphs and representative RGB/hand overlays. Save raw/derived
trajectories, settings, stage timings, logs, tables, plots and limitations under
`outputs/trajectory-comparison/iphone-20261119/`. Record failures explicitly;
partial coverage is not full-video completion. Update the wiki,
status and action log and commit verified work. Milestone 3 simulation acceptance
remains separate.
