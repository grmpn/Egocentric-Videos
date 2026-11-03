# Milestone 3 — IK benchmark and gripper integration

Approved revision 2 · 2026-10-30 · User-directed first-region amendment recorded as
`20261030-ik-first-region-001` in the [action log](../logs/2026-10.jsonl).
Revision 1's full-iPhone acceptance remains historical evidence.

## Objective and deliverable

Build the requested reusable 100-point IK benchmark, integrate the latest Config 2
gripper targets into two-stage retargeting, and deliver a first-region iPhone comparison
with saved trajectories and an interactive robot/target viewer.

## Scope and boundaries

- Create `outputs/ik-benchmark/`. Preserve each experiment's configuration,
  targets, trajectories, per-frame metrics, solver attempts/timing, logs and viewer
  artifacts in its own directory. Update `REPORT.md` after each experiment with
  benchmark settings, a scoreboard of all registered configurations, diagnostic
  statistics, run links, and configuration explanations at the bottom.
- For speed, solve and score only the first retained manipulation region, after
  configured adjacent-region merging. Rescore existing comparisons from saved
  trajectories without rerunning IK; preserve prior full-video scores. All current
  statistics and solve timing must cover that region only, including both stages
  and all retries; distinguish saved solver time from whole-run overhead.
- State **smoothed hand-derived position/orientation targets** at the report's
  top. Use existing 0.3-second, order-2 XYZ/SO(3) filtering on mapped palm poses
  before both IK stages, separately per hand/eligible span/region. Preserve raw
  targets for diagnostics; never bridge missing/infilled samples. Retain source
  timestamps, aligned metres/radians, hand identity and original inputs.
- Latest Config 2 means fingertip-midpoint forward, MCP roll, rear palm **25 mm
  backward** from the wrist, and existing continuous open/close command. Fit the
  actual robot palm position/orientation in both stages, replacing the historical
  shifted-wrist surrogate for this mode. Add bounded opening targets in the
  fixed-base second stage, respecting leader/mimic joints. Opening need not enter
  base fitting. Retain camera orientation and existing regularizers.
- Add a configurable second-stage joint-velocity penalty only for the arm/gripper
  belonging to a missing hand target; never apply it to the neck. Preserve
  observed-hand tracking, CPU/CUDA support and earlier saved-run readability.
- Award **25 × passing fraction** for each: observed target position ≤1 cm;
  observed target geodesic orientation ≤4°; evaluated frames satisfying **all**
  joint position/velocity/acceleration limits; evaluated frames without
  self-collision. Use common regions/observations across comparisons, count failed
  predictions as failures, and disclose exclusions/empty denominators. Include
  arms, neck and articulated grippers in feasibility and collision evaluation.
- Use pinned Alex position/velocity limits and a configurable **10 rad/s²**
  benchmark acceleration cap, explicitly distinguished from hardware limits;
  [source checks and rationale](../decisions/ik-benchmark-limits.md). Check actual
  collision geometry with documented structural/source exclusions. Compute motion
  using source-time differences within regions; document endpoint handling.
- Record joint velocity/acceleration RMS and absolute P95, position/orientation
  median and P95, and solve time including both stages/retries, separately from
  setup/export. Retain per-joint diagnostics. Benchmark scores do not replace
  historical demonstration gates or establish physical execution safety.

## Acceptance

- Verify score arithmetic/denominators, threshold boundaries, time derivatives,
  missing-hand and neck isolation, palm FK/units/orientation, opening/mimics,
  smoothing boundaries, and known colliding/noncolliding poses through focused
  production-workflow tests and representative CPU/CUDA agreement checks.
- Compare the current IK reference and Config 2 gripper IK with the additional
  missing-hand penalty off/on over the same first iPhone region. Use the latest
  smoothed IK settings as the reference; explain objective differences. Score
  against common filtered Config 2 targets and report raw-target errors separately.
- Recompute scores from saved data, verify report updates preserve earlier runs,
  and inspect representative viewer poses, openings, missing-hand gaps and region
  boundaries. Save validation evidence with runs; update wiki/status/logs and
  commit verified work. No required minimum score; failures remain visible.
- Verify region selection happens before solving, later regions do not enter any
  comparison statistic, and source arrays/timestamps and saved trajectories remain
  intact. Keep legacy unrestricted retargeting available outside this benchmark.
