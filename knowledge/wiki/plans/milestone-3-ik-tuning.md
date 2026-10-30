# Milestone 3 — IK configuration experiments

Approved user-directed scope · revision 5 · 2026-10-30 · Explicit manual-region
amendment recorded as `20261030-ik-tuning-036`; right-target
roll experiment explicitly authorized as `20261030-ik-tuning-054`, then corrected
by the user to left-target roll with original right orientation (`20261030-ik-tuning-058`)
(original >90 tuning approval: `20261030-ik-tuning-001`) in the
[action log](../logs/2026-10.jsonl). Extends the completed
[benchmark plan](milestone-3-ik-benchmark.md).

**Stopped at user request, 2026-10-30.** The user accepted left +180° / original
right as the correct target convention and directed all IK experimentation to
stop (`20261030-ik-tuning-063`). Commit the completed work; resume experiments only
on a new instruction. The >90 objective remains unachieved.

## Objective and deliverable

Reach **strictly above 90/100** on the manually reviewed first-region iPhone IK benchmark
through reproducible solver/configuration experiments. Deliver the best verified
configuration, saved trajectory, comparison report, and diagnostic evidence.

## Scope and boundaries

- Use source frames **0–268 inclusive**, excluding **right-hand frame 29**, as
  explicitly directed by the user on 2026-10-30 to approximate later refined HaWoR
  input. Apply this selection before smoothing, both solver stages and scoring.
  Preserve original source arrays and previous [0,296) results; begin a separate
  benchmark directory. Rerun the top six distinct production configurations,
  then continue experiments. Keep Config 2 targets, timestamps, four equal score
  terms, tolerances, joint limits, acceleration proxy and collision exclusions.
  Do not remove further observations without user direction.
- Compare the corrected user-requested left palm target rotated 180° about its
  local forward +X axis, keeping the right orientation and both palm positions/
  openings unchanged. Preserve the earlier right-flip comparison. Rerun
  `robust-position-limits` and open a detached-target viewer without viewer
  review/tests. Keep this changed-target comparison in its own benchmark
  directory. The user subsequently accepted this left-roll convention as correct;
  use its explicit mapping config for future Config 2 work.
- Test lower velocity/acceleration regularization; explicit penalties for motion
  exceeding the robot velocity limits and existing benchmark acceleration cap;
  and the original SDF base-placement approach with the current base constraints
  and new palm position targets. Other solver/objective improvements serving the
  requested score are authorized, including better orientation fitting and
  collision avoidance if diagnostics justify them.
- Keep each experiment's settings, trajectory, timings (both stages and retries),
  failures, and score evidence under `outputs/ik-benchmark/`; update its existing
  report. Use controlled comparisons to distinguish improvements and tradeoffs.
- Preserve source geometry, scale, timestamps, hand identity, missing-data
  semantics, earlier runs, and CPU/CUDA and saved-viewer compatibility. Use
  existing dependencies where possible. Retain existing historical acceptance
  gates separately from the benchmark.
- This is simulation/kinematic tuning, not hardware playback, scale calibration,
  physical dynamics certification, or a new milestone.

## Acceptance

- Execute and record the requested experiment families, with unsuccessful
  attempts and reasons retained. Select a configuration scoring >90 under the
  production evaluator with the approved reviewed region; save enough settings and inputs to reproduce it.
- Independently verify the selected run's score arithmetic, common region and
  observations, source preservation, FK tracking, joint derivatives/limits,
  and collisions. Do not claim the goal achieved before this evidence exists.
- Test any new objective terms at their boundaries and on nonuniform timestamps,
  including meaningful CPU/CUDA checks and regression coverage for existing modes.
- Inspect representative robot/target poses, missing-hand spans, and remaining
  failures; preserve plots/viewer evidence. Record the best result and unresolved
  tradeoffs honestly if experiments have not yet reached the target.
- Update canonical documentation, status and action log and commit verified
  changes at coherent checkpoints. Benchmark success alone does not complete the
  broader limit-satisfying simulation milestone.
