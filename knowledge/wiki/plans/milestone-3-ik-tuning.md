# Milestone 3 — IK configuration experiments

Approved user-directed scope · revision 6 · 2026-11-03 · Held-out evaluation and
SDF/full-IK comparison explicitly requested and clarified by the user in
`20261103-ik-heldout-001` ([November action log](../logs/2026-11.jsonl)).
Extends the fulfilled [benchmark plan](milestone-3-ik-benchmark.md).
Earlier tuning/roll approvals remain in the [October log](../logs/2026-10.jsonl);
revision 5 is preserved in Git at `a24de68`.

## Objective and deliverable

Evaluate the frozen `slack5-orientation8` configuration on held-out iPhone
regions 2 and 3. Deliver per-region benchmark scores and total/stage solve times
for **full-IK base fitting followed by fixed-base IK**, versus **SDF base fitting
followed by fixed-base IK**, with saved configurations, trajectories and an
independently checked comparison report. The previous first-region >90 objective
was achieved at 91.022; this extension measures transfer without further tuning.

## Scope and boundaries

- Region 2 is source **[432,893)**; region 3 is **[947,1286)**, with exclusive stops.
  Preserve the established adjacent-region merge for region 3. Apply selection
  before smoothing, both fitting stages and scoring. Do not solve region 1 or
  remove additional observations. Missing/infilled hand semantics remain unchanged.
- Use the accepted **left +180° / original right Config 2** palm targets, source
  timestamps, geometry, units and hand identity. Keep four equal benchmark terms,
  1 cm / 4° tracking tolerances, pinned joint limits, the 10 rad/s² acceleration
  proxy and collision exclusions unchanged.
- Reuse the exact saved `slack5-orientation8` settings. Both methods start fresh
  for each region, with one attempt and existing evaluation caps. The full-IK
  method jointly fits the base and sampled poses; SDF uses the verified actual-palm
  workspace, current camera-centred bounds/prior and existing search settings.
  Both then hold their base fixed during trajectory IK. The only configuration
  differences select SDF placement and its required workspace/search settings.
- Preserve each run under `outputs/ik-benchmark-heldout-20261103/`. Run sequentially
  for timing clarity. Include SDF placement, pose initialization and trajectory
  solving in total solve time; report stages separately and distinguish setup,
  export, cached workspace construction and any failed attempts. Do not compare
  incremental warm-start times with complete fresh-run totals.
- Preserve prior first-region scores, base-only comparison and original data.
  No held-out tuning, new model/benchmark changes, hardware playback or new milestone.
  Existing viewers may remain open; viewer testing is not part of this request.

## Acceptance

- Complete and preserve the four requested production runs, including unsuccessful
  outcomes, iteration-cap/convergence status and exact benchmark denominators.
- Independently check common observations/targets within each region, source-array
  preservation, transform/FK correctness, all physical joint limits/derivatives,
  collisions, score arithmetic and per-stage/total timing.
- Save and inspect representative numerical diagnostic plots for held-out tracking,
  motion-limit and collision failures; report what remains unverified. Do not change
  scoring or selected observations in response to the results.
- Update the canonical evidence page, status, navigation and append-only action log;
  commit verified work. Benchmark scores do not establish physical simulation or
  hardware acceptance.
