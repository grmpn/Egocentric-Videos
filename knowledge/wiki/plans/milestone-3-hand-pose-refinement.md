# Milestone 3 — Hand-pose smoothing and region continuity

Approved revision 1 · 2026-10-22 · User approval recorded as `20261022-pose-refinement-003` in the [action log](../logs/2026-10.jsonl).

## Objective and deliverable

Improve retargeted motion through smoother hand position/orientation targets, a
small preference for the median-camera base initialization, and merged adjacent
manipulation regions. Deliver configurable behavior, controlled comparisons
against the [latest CUDA run](../experiments/retargeting-iphone.md#gpu-solver-rerun-2026-10-22),
and a complete iPhone rerun with inspectable trajectories and video.

## Scope and boundaries

- **Hand-pose smoothing:** smooth derived wrist-position and palm-orientation
  targets before both IK stages using Savitzky–Golay filtering. Reuse
  [SciPy's filter and coefficients](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.signal.savgol_filter.html).
  Filter XYZ coordinates; evaluate local rotation-vector log/exp filtering for
  orientations, preserving valid rotations and handling wraparound. Configure
  position/orientation windows in seconds and polynomial order; support disabling.
  Use centred offline windows with explicit endpoint handling; leave too-short
  spans unchanged and reported. Require uniform timestamps when enabled, with
  guidance to disable for irregular input; do not resample. Process each hand's
  contiguous eligible spans inside merged regions without bridging missing/infilled
  observations or region gaps. Preserve source arrays, masks, timestamps, hand
  identity, aligned frames, metres/radians and wrist/tool mapping; save filtered
  targets separately.
- **Base initialization penalty:** add a configurable weak quadratic prior on
  shared-base XYZ and wrapped yaw displacement from the existing median-camera
  initialization, with explicit metre/radian normalization and zero-weight
  disablement. Apply it only during base fitting; the second stage still freezes
  that base. Retain hard bounds and the existing camera-orientation objective.
  This does not add per-frame camera-position tracking. Compare zero with a few
  small strengths and report the prior's contribution and resulting base drift.
- **Adjacent regions:** after the existing minimum-duration filter, merge chains
  of retained half-open intervals whenever one stop equals the next start.
  Preserve discarded intervals and never bridge them. Recompute initialization
  and fit one shared base/trajectory per merged interval. The current
  `[947,1113)` and `[1113,1286)` should become `[947,1286)`; earlier regions stay
  separate. Keep merging configurable for comparison and preserve seed diagnostics.
- Keep CUDA/CPU support, existing consumers, joint regularizers and acceptance
  thresholds. Compare against the latest temporal weights 1.0/0.5 with other
  settings fixed except these changes; disclose sampling/restart differences
  caused by merging. Exclude upstream reconstruction, retiming, hardware execution,
  collision/dynamics certification and unrelated tuning.

## Acceptance

- Verify disabled equivalence, polynomial-signal recovery, short spans/endpoints,
  missing-hand isolation, irregular-input rejection, rotation sign/wraparound
  handling, valid rotations, bounds, prior derivatives and exact adjacency/chained
  merging with discarded gaps.
- Compare changes individually, then together, using representative data before
  the complete rerun. Report target and robot-hand linear/angular motion,
  raw-to-smoothed displacement, overshoot/lag, base drift, pose errors,
  gate results, joint jumps including frame 1113, runtime and solver termination.
  Evaluate errors against both raw and smoothed targets; existing demonstration
  gates and restart pose-ranking use original eligible observations.
- Save configurations, reports, plots and synchronized video under a new
  `outputs/retargeting/` directory; inspect representative motion and boundaries.
  Document keep/reject recommendations, update wiki/status/logs and commit verified
  work. A completed experiment may find no beneficial setting or accepted demo;
  smoother targets alone do not establish better physical accuracy.
