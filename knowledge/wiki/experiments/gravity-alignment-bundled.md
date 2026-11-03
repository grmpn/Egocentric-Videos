# Stage 3 Part 1 — Bundled gravity-alignment acceptance

Verified 2026-10-14 against [approved revision 1](../plans/milestone-3-part-1-gravity-alignment.md).
Part 1 is complete. At this checkpoint Parts 2–3 and the unrecorded iPhone pilot
were outstanding; this result establishes no robot feasibility or measured metric
accuracy. Later robot verification is recorded in [Part 3 acceptance](retargeting-bundled.md).

## Reproduction and evidence

Use the [gravity setup](../../../environment/README.md#gravity-alignment-environment)
and [command](../../../README.md#stage-3-part-1-gravity-alignment). The validated
input is the existing 121-frame, 30 FPS bundled `video_0.mp4` HaWoR run at
`outputs/setup/desktop-20260924/video-to-dataset-smoke/20260924T173234197039Z-658b3f620373/20260924T173234243231Z-a62ff6c94a08/run_manifest.json`.
Its completion/artifact checks passed; no HaWoR inference was repeated.

All linked outputs below are ignored, local-only evidence, unavailable in a fresh
clone. Reproduction requires the source run, prepared RGB, licensed MANO files
and pinned GeoCalib model. The maintained [contract](../topics/stage-3-retargeting.md#implemented-part-1-export)
describes the exported fields and limitations.

- [Aligned NPZ](../../../outputs/gravity/part-1-20261014/bundled/trajectory_aligned.npz),
  [report/transform/command](../../../outputs/gravity/part-1-20261014/bundled/alignment_report.json),
  [per-frame diagnostics](../../../outputs/gravity/part-1-20261014/bundled/gravity_diagnostics.json).
- [Original/aligned 3D trajectories](../../../outputs/gravity/part-1-20261014/bundled/trajectory_comparison.png),
  [whole-clip and inlier vertical review](../../../outputs/gravity/part-1-20261014/bundled/vertical_review.png),
  [estimation plot](../../../outputs/gravity/part-1-20261014/bundled/gravity_diagnostics.png),
  [agent visual review](../../../outputs/gravity/part-1-20261014/bundled/visual_review.json).
- [Execution log](../../../outputs/gravity/part-1-20261014/bundled.log),
  [setup/package check](../../../outputs/gravity/part-1-20261014/install.log),
  [installed versions](../../../outputs/gravity/part-1-20261014/packages.txt).

## Observed results

The full command completed in **9.59 seconds** on the RTX 4090 with the default
configuration. It selected 50 sharp frames, retained 23 after the downward-pitch /
10° roll filter, and retained **20 MAD inliers**, frames 77–96. No sign flips were
needed. Post-MAD angular disagreement was **1.92° median / 4.05° p95**, down from
2.06° / 32.06° before MAD. These measure internal consistency, not true gravity error.
The prior run also retained 20 frames; GPU estimates varied slightly. Bitwise
inference reproducibility is not claimed; the axis rule is deterministic for a
given estimated direction.

The saved proper rotation maps estimated up to +Z and has zero translation. All
source arrays, left/right order, timestamps, validity/confidence and local hand
parameters survived exactly. Every exported field reloaded with matching dtype
and bytes. The original run/model files were unchanged.

For **121 left and 120 right valid hand-frames**, each frame's 778 vertices and
16 MANO joints were reconstructed before/after alignment. Maximum vertex error
was **1.91e-7 m**, below the scale-aware float32 tolerances of 5.64e-6 / 6.07e-6 m.
These tiny errors establish rigid-transform arithmetic only, not reconstruction
accuracy. The missing right-hand frame remains invalid with derived NaNs.

An independent [comparison against pinned HaWoR helpers](../../../outputs/gravity/part-1-20261014/upstream-geometry-check.json)
checked all valid hand-frames and all camera poses using the legacy Torch runtime.
Physical wrists matched exactly; maximum upstream vertex rotation error was
2.15e-7 m and hand/camera relative-coordinate discrepancy was below 2.39e-7 m.
This checks the MANO root-offset and camera-direction assumptions against the
existing reconstruction path rather than relying solely on algebraic round trips.

## Tests, visual inspection and limits

- [25 focused tests passed](../../../outputs/gravity/part-1-20261014/tests.log):
  known tilt/axis degeneracy, determinant/inversion, camera-to-world sign and scale,
  sharp-frame ordering, robust aggregation, insufficient/degenerate evidence,
  MANO offsets, exact-frame decoding, failed-estimate/no-export behavior and the
  existing world-export contracts.
- [Six LeRobot/canonical regression tests passed](../../../outputs/gravity/part-1-20261014/lerobot-regression-retry.log)
  after moving the unchanged run loader into the shared world module. They include
  actual creation/append/reload and annotation CLI behavior with a local fixture.
  The first attempt's localhost socket was blocked by the sandbox; the authorized
  retry passed. No production annotation inference was run.
- Agent inspected the 3D comparison, residual plot and RGB frames 0, 60, 120,
  77, 87 and 96. Z-up geometry preserves the same paths and shows the hands below
  the camera; infill and the invalid right endpoint remain visible. Projected up
  is qualitatively compatible with visible cabinet/bottle verticals. Horizon
  lines lie outside these downward-looking views. Beginning/end views offer weak
  vertical evidence; they cannot validate absolute tilt. Plot margins were fixed
  and rerendered from the saved export without repeating inference.

The retained estimates cover only **2.57–3.20 s** of the **0–4.00 s** clip. This
is sufficient for this fixed-gravity demonstration, not evidence of temporal
coverage on arbitrary clips or freedom from SLAM drift. Camera intrinsics use
the existing 600 px assumption. Scale, true gravity error, cross-clip heading,
floor height and robot constraints remain unverified. iPhone quality/acceptance
must still be evaluated on the eventual recordings.

Environment issues were resolved without changing prior environments: Chumpy
needed its undeclared build-time pip dependency; the independent legacy comparison
needed `PYTHONNOUSERSITE=1` to prevent a user NumPy 2 from shadowing pinned NumPy 1.26.
Details and failed attempts are retained in the [action log](../logs/2026-10.jsonl).
