# First-region iPhone IK benchmark and gripper integration

Verified 2026-10-30 under the [approved revision 2](../plans/milestone-3-ik-benchmark.md).
The benchmark scope is fulfilled; these results do **not** complete the roadmap's
limit-satisfying simulation demonstration. Implementation contracts belong to
[Stage 3](../topics/stage-3-retargeting.md#ik-benchmark-and-gripper-targets).
Generated evidence below is local and ignored, unavailable in a fresh clone.

## Comparison and results

[Automatic report](../../../outputs/ik-benchmark/REPORT.md) preserves every run's
configuration, solver attempts/timing, original and filtered targets, trajectory,
video, per-frame scores, physical joint values and collision pairs. All current
comparisons use the same iPhone source, 0.3-second/order-2 Config 2 palm targets
and **first manipulation region [0,296)**: 296 evaluated frames and 470 observed
hand samples. The other 990 source frames are disclosed exclusions. These are
rescored saved trajectories; no new IK run was needed. Future benchmark runs
solve only this first retained region after configured adjacent-region merging.
No predictions are missing within it. Source arrays and timestamps remain unchanged.

Each column is 25 times its passing fraction. Position ≤1 cm and orientation ≤4°
use observed hand samples; joint limits and collision avoidance use all evaluated
frames. All 24 physical revolute joints enter feasibility, including neck and
finger mimics. Acceleration uses the explicitly assumed
[10 rad/s² benchmark cap](../decisions/ik-benchmark-limits.md), not an Alex rating.

| Configuration | Total /100 | Position /25 | Orientation /25 | Joint limits /25 | Collision-free /25 | Solve seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Smoothed wrist reference | 41.554 | 0.000 | 0.000 | 17.905 | 23.649 | 89.718 |
| Config 2 palm/opening | 69.877 | 24.362 | 3.032 | 20.524 | 21.959 | 96.706 |
| Config 2 + missing-hand penalty | 70.806 | 24.362 | 3.032 | 21.453 | 21.959 | 96.968 |

Solve time sums both solver stages and every retry in this region, excluding
setup/export and between-solve overhead. The original whole-trajectory timings
remain in each saved trajectory report.

The reference fits its historical shifted wrist and neutral-MANO orientation;
its zero tracking scores reflect the changed **common Config 2 palm objective**,
not a claim that its original wrist objective never succeeded. Gripper runs fit
actual palm FK and continuous opening. Both use temporal weights 1/0.5, opening
weight 20, base prior 0.3 and adjacent-region merging. The last run adds missing-hand
velocity weight 5 to the corresponding arm/opening in stage two, excluding neck.

| Configuration | Position median / P95 (mm) | Orientation median / P95 (degrees) | Joint velocity RMS / absolute P95 (rad/s) | Joint acceleration RMS / absolute P95 (rad/s²) |
| --- | ---: | ---: | ---: | ---: |
| Reference | 51.432 / 55.235 | 113.206 / 167.670 | 0.670 / 1.261 | 3.491 / 6.054 |
| Config 2 | 1.510 / 5.680 | 12.792 / 43.439 | 0.634 / 1.323 | 3.276 / 5.796 |
| Config 2 + penalty | 1.488 / 5.685 | 12.662 / 44.695 | 0.536 / 1.067 | 3.355 / 5.657 |

The extra penalty reduces velocity RMS at missing-hand destinations from
1.018403 to 0.533669 rad/s (47.60%) and absolute P95 from 2.200208 to 1.214622 rad/s.
This diagnostic pools each missing hand's seven arm joints and one opening
variable over 960 scalar interval samples, without neck or repeated mimics.
Both gripper configurations have 36 collision frames and 57 passing orientation
samples; joint-feasible frames improve from 243 to 254. Weight 5 improves gap
holding and the total score in this first region.
Neck is excluded from the added residual; its optimized motion is not guaranteed
unchanged. No extra tuning was performed beyond the approved comparison.

Final opening error has median 0.01124 and P95 0.14140 on the unitless [0,1] action.
The report also links raw-target errors, individual-joint diagnostics and exact
passing counts. All final positions satisfy URDF bounds, but 2 frames violate
speed bounds and 42 violate the benchmark acceleration cap (42 fail their
combined joint test). These and the 36 colliding frames remain visible.

## Verification and review

- [Current tests](../../../outputs/ik-benchmark/validation/first-region/tests-retry.log):
  **91 passed**, including CPU/CUDA and production workflow coverage. New cases
  verify selection after merging, preservation of source arrays, unsolved later
  frames, scoring old full runs and new limited runs, all-attempt timing and
  region-scoped motion/collision denominators. The first test session was
  interrupted before completion; its log is preserved alongside the retry.
- [First-region audit](../../../outputs/ik-benchmark/validation/first-region/audit.json)
  ([script](../../../outputs/ik-benchmark/validation/first-region/audit.py),
  [log](../../../outputs/ik-benchmark/validation/first-region/audit.log)):
  all three scores, tracking/opening/per-joint diagnostics, limits and timing
  independently recomputed. First-region per-frame evidence equals the archived
  full-run evidence; all 24 source arrays remain unchanged. Later frames have no
  benchmark predictions or passing flags. Common targets and idempotent report
  regeneration verified.
- [Browser review](../../../outputs/ik-benchmark/validation/first-region/viewer-browser.json):
  five frames passed (119, 295, 296, 432, 600), with no page errors. Inspected
  screenshots at [119](../../../outputs/ik-benchmark/validation/first-region/viewer-119.png)
  and [600](../../../outputs/ik-benchmark/validation/first-region/viewer-600.png)
  confirm first-region scores and the explicit exclusion label on later saved
  poses. Rendering used software WebGL; trajectories were not regenerated.

Use the README's viewer command with
`outputs/ik-benchmark/config2-missing-hold/trajectory` to reopen the saved run.
The current viewer is at [localhost:8080](http://localhost:8080).

## Historical full-video acceptance

The 2026-10-29 [full-video report](../../../outputs/ik-benchmark/history/full-regions-20261029/REPORT.md),
scores and frame metrics remain archived. They cover [0,296), [432,893),
[947,1286) and are superseded for current comparisons. Original full-video
trajectories, configurations, videos and logs remain in place. Previous checks:

- [Historical tests](../../../outputs/ik-benchmark/validation/final-tests.log): **134
  passed**, covering score denominators/boundaries, physical time, real known
  collision/clear poses, unclipped invalid joint evaluation, palm FK/opening/mimics,
  missing-hand/neck isolation, smoothing/source preservation, production exports,
  CPU/CUDA agreement and legacy behavior. Third-party deprecation warnings remain.
- [Independent audit script](../../../outputs/ik-benchmark/validation/audit.py),
  [log](../../../outputs/ik-benchmark/validation/audit.log) and
  [results](../../../outputs/ik-benchmark/validation/audit.json): all three scores
  and requested diagnostics recomputed from saved data; all 24 source arrays
  unchanged; common target/mask/timestamp arrays equal; all 24 robot joints
  reconstructed directly from XML mimic rules; source-time differences and
  endpoint handling checked. Gripper solver FK agrees with the scorer's ordinary
  robot FK. Report regeneration preserves every run and is idempotent.
- Initial checks exposed a missing-observation NaN regression, a mis-transcribed
  collision fixture and relative-path report formatting. All were corrected;
  their failed logs and follow-up events remain preserved in the
  [action log](../logs/2026-10.jsonl).
- [Browser checks](../../../outputs/ik-benchmark/validation/viewer-browser.json)
  passed at 14 frames spanning observations, missing hands, collision cases,
  selected-region boundaries and excluded gaps, with no page errors. Inspected
  screenshots at [119](../../../outputs/ik-benchmark/validation/viewer-119.png),
  [252](../../../outputs/ik-benchmark/validation/viewer-252.png),
  [296](../../../outputs/ik-benchmark/validation/viewer-296.png),
  [600](../../../outputs/ik-benchmark/validation/viewer-600.png),
  [959](../../../outputs/ik-benchmark/validation/viewer-959.png) and
  [1285](../../../outputs/ik-benchmark/validation/viewer-1285.png) confirm visible
  articulation/target axes, missing-observation labels, collision flags and hidden
  robot poses in excluded gaps. Browser rendering used software WebGL.

The benchmark checks sampled self-collision geometry with documented structural
and pinned-asset exclusions. It does not establish inter-frame clearance, scene
contact, torque feasibility, physical scale accuracy or safe hardware execution.
Historical raw-target demonstration gates remain separate. Further tuning or
simulation work requires a new user-directed scope; the next action is review
of these preserved results. Focused repository cleanup remains due before the
next milestone.
