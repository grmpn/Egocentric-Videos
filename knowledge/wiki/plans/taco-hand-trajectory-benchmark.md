# TACO hand-trajectory benchmark

Approved · revision 1 · 2026-11-24.
Approval: user instruction to implement the approved plan, event
`20261124-taco-implementation-001` in the [November log](../logs/2026-11.jsonl).

Execution order clarified by the user on 2026-11-24: finish all HaWoR and HandFlow
trials and their comparison first, then assess whether recreating StableHand's
missing preprocessing is viable. Experimental StableHand recreation remains
subject to scope review; this clarification does not authorize it.

## Objective and deliverable

Benchmark base HaWoR, StableHand and HandFlow with reusable evaluation. Deliver
comparison/component-speed tables, per-clip/per-hand CSV/JSON and predicted-versus-GT
3D wrist plots for one preselected clip. This informs Milestone 3 reconstruction;
simulation acceptance remains separate.

## Scope and boundaries

- Freeze five 150-consecutive-frame clips from distinct TACO V1 test recordings,
  varying actions before inference. Preserve timestamps, identities, calibration,
  units and source offsets. Verify hand/camera synchronization and gravity.
  Report GT camera translation/rotation excursion;
  retain low-motion cases and SLAM failures.
- Run complete pipelines with pinned weights/settings: unchanged
  HaWoR including native infilling, StableHand's released enhanced HOT3D model,
  and moving-camera HandFlow. Preserve both hands; charge HandFlow's additional
  hand pass. Use identical RGB frames and available intrinsics, documenting
  resizing/calibration limits. No GT depth, shape, poses,
  masks or scale may condition inference. No training or parameter sweeps.
- Apply RGB-estimated gravity alignment to every method; preserve native outputs.
  Reuse GeoCalib; respect native conventions without double rotation or GT tilt correction.
- Resolve the [release prerequisites](../experiments/taco-benchmark-preflight.md)
  first. Faithful adapters/instrumentation are in scope; model substitution or
  undocumented preprocessing requires scope review.

Metrics use matched valid samples and millimetres for errors:

| Metric | Definition |
| --- | --- |
| Initial-aligned wrist error | Mean Euclidean error after one shared yaw/translation fit to both wrists in the first second; no scale/refitting. Unobservable alignment is unavailable. |
| Wrist error with GT camera | Transform final predicted camera-relative wrists with GT camera-to-world poses; mean Euclidean error, without further fitting. |
| Relative translation error | Wrist-pose SE(3) RPE translational RMSE at 0.5, 2 and 4 seconds: translation of `(G_i^-1 G_j)^-1 (P_i^-1 P_j)`. |
| Metric scale ratio | Median predicted/GT wrist endpoint-displacement ratio over one second; exclude GT displacement below 10 mm and report excluded counts. Ideal: 1. |
| Tracking completeness | Valid final world-wrist samples / GT-valid hand-frames; separately retain direct-estimation, infilled and camera coverage. |
| Finger PA-MPJPE | Per-hand/per-frame proper similarity alignment on 21 corresponding joints; mean error on the 20 non-wrist joints. |

Run sequentially on the RTX 4090. Measure uncached RGB-to-export wall time,
including loading, preprocessing, gravity and all subprocesses; exclude downloads,
scoring and rendering. Report `150 / seconds` end-to-end and component effective
FPS, actual component frame counts, loading time, and sampled whole-device peak
VRAM with idle baseline/sampling interval. Components include detection, hand
features/prediction, camera estimation, metric scaling, refinement and export;
label inseparable stages.

Average geometric metrics equally across hands, then clips; report mean per-clip
FPS and peak VRAM, counts, dispersion and failures. Report aggregate throughput
as total frames / total elapsed time and worst-case peak VRAM. Missing
results never become zero or an unlabeled five-clip average. Compare common-valid
support alongside individual coverage; do not bridge gaps.

## Acceptance

Complete and account for all 15 method/clip attempts; unresolved setup remains
unfinished. Check synchronization, transforms, units, handedness, alignment,
RPE, scale, joint mapping, validity and timing with focused tests. Inspect GT/RGB
overlays and equal-axis trajectory plots. Save inputs/settings, raw/derived
predictions, logs, tables and figures under `outputs/taco-benchmark/`; document
limitations, update wiki/status/logs, and commit verified work.
