# Milestone 3 — Joint base and trajectory optimization

Approved revision 2 · 2026-10-20 · User-requested median initialization amendment: `20261020-median-heading-001` in the [action log](../logs/2026-10.jsonl).

Revision 1 was fulfilled at `985080b`. This amendment changes the yaw statistic
to median forward direction; camera position already used a median. Verify the
initializer with outliers/wraparound, rerun the bundled clip and compare its pose,
head and smoothness results to the preserved mean-heading run. The existing
three-repeat workflow benchmark remains historical evidence.

## Objective and deliverable

Implement [Milestone3-Update.md](../../../Milestone3-Update.md) (local user input),
amended to use camera position only for initialization.
Deliver a direct IK/base alternative to workspace placement, saved trajectories,
the existing interactive viewer, and a measured runtime/quality comparison.
Preserve the fulfilled [wrist-alignment workflow](milestone-3-wrist-alignment.md)
as the baseline.

## Scope and boundaries

- Reuse bundled gravity-aligned inputs, pinned Purdue Alex assets and existing
  dependencies where suitable. Preserve original geometry, metres/radians,
  timestamps, hand identity, confidence and validity.
- Use retained camera-motion heuristic regions **before workspace expansion**.
  Optimize each independently; do not expand regions or solve outside them.
  Missing observations remain unknown; label regularized joint predictions through
  gaps separately from observed tracking success.
- Initialize yaw from median horizontal camera-forward direction, accounting for angular
  wraparound and degenerate headings. Initialize XYZ by aligning the robot camera
  at neutral posture with the median human camera position, including the
  rotated base-to-camera offset. Keep base roll/pitch gravity-aligned.
- Jointly fit one shared XYZ/yaw base and per-frame arm/neck configurations within
  each region. Match physical human wrists to `WRIST_X` origins and human hand
  orientations through documented per-hand MANO/robot frame mappings. Match
  per-frame camera **rotation only**, with a verified robot optical-frame
  convention. Camera position has **no optimization loss**.
- Freeze that base, then optimize the region's full joint trajectory with
  timestamp-aware temporal smoothness. Enforce URDF joint bounds and regularize
  toward a documented neutral posture in both stages. Joint scope is
  all fourteen arm joints and two neck joints; gripper fingers remain fixed.
  Record weights, stopping budgets, convergence and failures.
- Retain the baseline command and old-run readability. Extend shared exports and
  playback for neck motion, orientation targets/residuals and failure labels,
  preserving MANO overlays and source synchronization. No SDF objective or margin
  gate applies to the new method. Exclude gripper actuation, rescaling, retiming,
  collision/dynamics certification, simulation and hardware.

## Acceptance

- Exercise both methods on identical heuristic regions and inputs. Independently
  replay FK; verify bases, transform direction, left/right orientation
  mappings, joint bounds, timestamps, missing-data labels and export reload.
  With regions/initialization fixed, verify camera translations cannot affect fitting.
- New-method pose gate: **≤5 mm** wrist-position and **≤10°**
  orientation error for every observed hand in a passing frame, **>95%**
  passing observed frames, **≤0.2 s** nonpassing/unknown gaps, **≥1 s** duration,
  and a nonempty denominator. At least one region must qualify.
  Report camera angular residuals separately
  because the head has only two joints. Show reduced joint-acceleration RMS after
  smoothing without losing the pose gate.
- Compare three timed runs per method on the same machine with recorded budgets:
  baseline placement plus IK versus joint/base fitting plus fixed-base smoothing.
  Report median/range, processed frames, failures and pose/smoothness quality.
  Separate workspace construction, loading and visualization from solve time;
  identify the different objectives. No speedup is required.
- Inspect synchronized robot/MANO/head playback, region boundaries and missing/
  failed samples; retain legacy playback checks. Save focused test logs,
  numerical audits, timing reports and visual evidence under
  `outputs/retargeting/`. Passing establishes kinematic fitting only.
