# Full-iPhone IK benchmark and gripper integration

Verified 2026-10-29 under the [approved plan](../plans/milestone-3-ik-benchmark.md).
The benchmark scope is fulfilled; these results do **not** complete the roadmap's
limit-satisfying simulation demonstration. Implementation contracts belong to
[Stage 3](../topics/stage-3-retargeting.md#ik-benchmark-and-gripper-targets).
Generated evidence below is local and ignored, unavailable in a fresh clone.

## Comparison and results

[Automatic report](../../../outputs/ik-benchmark/REPORT.md) preserves every run's
configuration, solver attempts/timing, original and filtered targets, trajectory,
video, per-frame scores, physical joint values and collision pairs. All runs use
the same iPhone source, 0.3-second/order-2 Config 2 palm targets and regions
`[0,296)`, `[432,893)`, `[947,1286)`: 1,096 evaluated frames and 1,797 observed hand
samples. The other 190 source frames are disclosed exclusions. No predictions are
missing within evaluated regions. Source arrays and timestamps remain unchanged.

Each column is 25 times its passing fraction. Position ≤1 cm and orientation ≤4°
use observed hand samples; joint limits and collision avoidance use all evaluated
frames. All 24 physical revolute joints enter feasibility, including neck and
finger mimics. Acceleration uses the explicitly assumed
[10 rad/s² benchmark cap](../decisions/ik-benchmark-limits.md), not an Alex rating.

| Configuration | Total /100 | Position /25 | Orientation /25 | Joint limits /25 | Collision-free /25 | Solve seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Smoothed wrist reference | 34.831 | 0.000 | 0.000 | 16.720 | 18.111 | 309.77 |
| Config 2 palm/opening | 71.885 | 24.485 | 5.314 | 20.324 | 21.761 | 312.29 |
| Config 2 + missing-hand penalty | 71.489 | 24.430 | 4.883 | 18.841 | 23.335 | 307.77 |

The reference fits its historical shifted wrist and neutral-MANO orientation;
its zero tracking scores reflect the changed **common Config 2 palm objective**,
not a claim that its original wrist objective never succeeded. Gripper runs fit
actual palm FK and continuous opening. Both use temporal weights 1/0.5, opening
weight 20, base prior 0.3 and adjacent-region merging. The last run adds missing-hand
velocity weight 5 to the corresponding arm/opening in stage two, excluding neck.

| Configuration | Position median / P95 (mm) | Orientation median / P95 (degrees) | Joint velocity RMS / absolute P95 (rad/s) | Joint acceleration RMS / absolute P95 (rad/s²) |
| --- | ---: | ---: | ---: | ---: |
| Reference | 51.621 / 56.275 | 119.916 / 149.973 | 0.655 / 1.333 | 3.960 / 6.539 |
| Config 2 | 1.615 / 6.339 | 7.763 / 24.258 | 0.504 / 1.055 | 3.492 / 5.404 |
| Config 2 + penalty | 1.688 / 6.846 | 8.361 / 29.883 | 0.504 / 0.988 | 3.641 / 5.767 |

The extra penalty reduces velocity RMS at missing-hand destinations from
0.810865 to 0.434195 rad/s (46.45%) and absolute P95 from 1.896202 to 0.951842 rad/s.
This diagnostic pools each missing hand's seven arm joints and one opening
variable over 3,112 scalar interval samples, without neck or repeated mimics.
It reduces collision frames from 142 to 73, but joint-feasible frames fall from
891 to 826 and orientation passing samples from 382 to 351. Thus weight 5 improves
gap holding and collision frequency here, without improving the total score.
Neck is excluded from the added residual; its optimized motion is not guaranteed
unchanged. No extra tuning was performed beyond the approved comparison.

Final opening error has median 0.00840 and P95 0.07299 on the unitless [0,1] action.
The report also links raw-target errors, individual-joint diagnostics and exact
passing counts. All final positions satisfy URDF bounds, but 11 frames violate
speed bounds and 268 violate the benchmark acceleration cap (270 fail their
combined joint test). These and the 73 colliding frames remain visible.

## Verification and review

- [Final tests](../../../outputs/ik-benchmark/validation/final-tests.log): **134
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

Use the README's viewer command with
`outputs/ik-benchmark/config2-missing-hold/trajectory` to reopen the final run.
The viewer animates both grippers, shows filtered target axes and measured
benchmark errors/limit/collision flags, labels missing/unverified observations,
and provides **Focus robot** when moving between regions.

The benchmark checks sampled self-collision geometry with documented structural
and pinned-asset exclusions. It does not establish inter-frame clearance, scene
contact, torque feasibility, physical scale accuracy or safe hardware execution.
Historical raw-target demonstration gates remain separate. Further tuning or
simulation work requires a new user-directed scope; the next action is review
of these preserved results. Focused repository cleanup remains due before the
next milestone.
