# First-region iPhone IK benchmark and gripper integration

Verified 2026-10-30 under the [approved revision 2](../plans/milestone-3-ik-benchmark.md).
The benchmark scope is fulfilled; these results do **not** complete the roadmap's
limit-satisfying simulation demonstration. Implementation contracts belong to
[Stage 3](../topics/stage-3-retargeting.md#ik-benchmark-and-gripper-targets).
Generated evidence below is local and ignored, unavailable in a fresh clone.

## Reviewed-region restart

On 2026-10-30 the user authorized source frames **0–268 inclusive** and removal
of **right-hand frame 29**, approximating later improved HaWoR input. This changes
the input benchmark; old and new scores must not be interpreted as a solver-only
comparison. Original source arrays and the old benchmark remain preserved.
The [reviewed report](../../../outputs/ik-benchmark-reviewed/REPORT.md) records
fresh solves of the six leading distinct production configurations; the duplicated
cached runtime comparison is counted once. Further experiments follow those runs.
[21 focused checks passed](../../../outputs/ik-benchmark-reviewed/validation/selection-tests.log)
for source preservation, exact boundaries, hand identity, production fitting and
scoring, legacy behavior and selection mismatch rejection.

Subsequent tuning adds optional production vector Cauchy fitting for hand pose
blocks. [12 derivative/loss checks](../../../outputs/ik-benchmark-reviewed/validation/cauchy-tests.log),
[16 settings checks](../../../outputs/ik-benchmark-reviewed/validation/cauchy-settings-tests.log)
and [4 CPU/CUDA comparisons](../../../outputs/ik-benchmark-reviewed/validation/cauchy-cuda-tests.log)
passed. This retains the scoring targets, isolates camera/motion/opening terms,
and defaults to the previous objective. Benchmark experiments using it follow
the six requested reruns; passing tests alone does not establish a score gain.

The previous Cauchy polish failed its pre-solve directional Jacobian check;
no polish trajectory or score was produced. The user ended viewer work, and its
server was stopped. Earlier viewer evidence below remains historical.

## Ongoing configuration tuning

The user subsequently authorized [experiments toward >90](../plans/milestone-3-ik-tuning.md)
on the original unchanged region before the reviewed restart above. The first completed run,
[temporal-low](../../../outputs/ik-benchmark/temporal-low/score.json), scores
**72.620759**: 463/470 position passes, 337/470 orientation passes, 85/296
joint-feasible frames, and 271/296 collision-free frames. Relative to the original
missing-hand configuration, only temporal weights changed from 1/0.5 to 0.1/0.05.
Orientation median improves from 12.66° to 2.30°, but acceleration failures offset
most of the gain. Its 396.96 seconds of solving partly overlapped focused checks;
do not interpret it as an isolated solver-speed comparison.

The original selected initialization has 112.8 rad/s² acceleration RMS and a
2.54-radian maximum frame step, motivating optional temporal regularization
during base fitting. New motion-limit penalties passed
[60 IK tests](../../../outputs/ik-benchmark/validation/tuning/motion-tests.log),
including CPU/CUDA agreement, and a further
[hinge boundary check](../../../outputs/ik-benchmark/validation/tuning/hinge-boundary.log).
SDF support passed [three focused checks](../../../outputs/ik-benchmark/validation/tuning/sdf-tests.log)
and uses a separately built
[one-million-sample palm workspace](../../../outputs/ik-benchmark/palm-workspace/workspace_report.json).
Optional base-stage continuity passed [five checks](../../../outputs/ik-benchmark/validation/tuning/base-continuity-tests-retry.log).
One initial new-mode assertion assumed the second stage must further reduce
acceleration despite stronger first-stage smoothing; its failure and correction
are preserved in event `20261030-ik-tuning-006`. Legacy acceptance is unchanged.

Subsequent completed scores: `temporal-lower` (weights 0.01/0.005) **74.680132**;
`orientation4-limits` **69.571952**; `continuous-base-limits` **69.071305**.
The remaining initial sweeps finished: original SDF palm placement **66.176682**,
orientation4-low **72.890670**, orientation8-limits **64.667194**, and
balanced-limits **65.425173**. Explicit limit penalties have not improved the best
score. A 1 cm radial Huber position loss with limit penalties scored **72.437464**;
the motivation was that five of 470 observations account for >99.999% of the
best run's squared position error. Targets and scoring remain unchanged.
The objective passed [eight focused checks](../../../outputs/ik-benchmark/validation/tuning/huber-final-tests.log).

An [independent audit](../../../outputs/ik-benchmark/validation/tuning/audit-robust-position-limits-cached.json)
passed for the original missing-hand configuration, the current best 74.680132
run, and both robust-loss timing runs. It recomputed scalar FK, collisions,
24 physical joint values/derivatives, score arithmetic and common source inputs.
No >90 result or final tuning acceptance is established yet. The
[automatic report](../../../outputs/ik-benchmark/REPORT.md) owns the full scoreboard.

Fixed-base refinement diagnostics then held the best run's base and started from
its saved joints. Three existing-objective variants scored **74.263**, **67.305**,
and **64.950**, all exhausting 1000 evaluations. The first improved joint passing
frames from 60 to 253 but lost tracking. These are exploratory saved-joint scores,
not production exports or new accepted winners; settings, joints and actual
mesh-collision scores are in the local
[refinement directory](../../../outputs/ik-benchmark/validation/tuning/refinement/).

Testing now includes radial fitting tolerances and joint/base co-optimization
in stage two. [Thirteen derivative/workflow checks](../../../outputs/ik-benchmark/validation/tuning/refinement/refinement-tests.log)
and [thirteen reference/settings checks](../../../outputs/ik-benchmark/validation/tuning/refinement/reference-tests.log)
passed. Four new tolerance-mode CPU/CUDA cases initially exceeded the existing
1% cost-agreement threshold at 150 evaluations; all passed with 1000 evaluations
in the [six-case retry](../../../outputs/ik-benchmark/validation/tuning/refinement/refinement-cuda-tests-retry.log).
Legacy comparisons passed without their budgets or tolerances changing. Current
6 mm / 2° fitting tolerances leave the benchmark at 10 mm / 4°. The fixed-base
probe reached **77.197743** (386/470 position, 219/470 orientation, 264/296 joint,
269/296 collision passes), but exhausted 2000 evaluations. The moving-base probe
finished at **73.799957**, also unconverged. The 77.198 result is not yet a
production export/audited winner. Exploratory vector Cauchy pose-loss probes
scored **85.454284** (fixed base) and **86.815339** (moving base), both with all
296 frames joint-feasible. The latter passed 458/470 positions, 277/470
orientations and 269/296 collision checks. Both exhausted 2000 evaluations.
The motivation was five observations contributing 52% of the best run's chordal
orientation loss. Their analytic directional checks passed; no production Cauchy
loss feature or acceptance result is claimed. The subsequent orientation-weight
polish failed its pre-solve derivative check, as recorded above; no polish result
is claimed. [Diagnostic evidence](../../../outputs/ik-benchmark/validation/tuning/refinement/cauchy-base.json).

The requested [detection-gap check](../../../outputs/ik-benchmark/validation/tuning/first-region-detection-gaps.json)
found one pair separated by more than ten absent frames inside [0,296): right
hand **275 → 295**, with frames 276–294 missing (19 frames), 0.667 seconds between
detections, **0.991933 m wrist displacement** and **0.988565 m palm-target
displacement** in the gravity-aligned world frame. Raw and filtered palm positions
agree for this pair. Direct-detection and benchmark observation masks are equal
in this interval. Left has no qualifying internal gap; frames 274–295 are a
22-frame trailing absence with no subsequent in-interval detection. Leading
absence before the first detection is likewise not an inter-detection gap.
These are measured discontinuities, not proof of a detector error; inputs and
scoring masks remain unchanged.

The requested hand-only review was verified at localhost:8080 (now stopped):
original MANO meshes, source RGB, detection paths without bridges across missing
frames, and jump buttons for 275/285/295. Optional faint endpoint hands make the
displacement visible. The original camera-framing issue was corrected; inspected
[screenshot](../../../outputs/ik-benchmark/validation/tuning/hand-review/review-fixed.png)
and [review record](../../../outputs/ik-benchmark/validation/tuning/hand-review/review.json)
confirm the rendered scene. This local diagnostic uses existing reconstruction
helpers; it does not alter the saved hand or robot trajectory. The screenshot
used software WebGL and captured the user's selected frame 29 without scrubbing
their view. Relaunch with workspace Python and `PYTHONPATH=src` using the ignored
[review script](../../../outputs/ik-benchmark/validation/tuning/hand-review/view.py),
optionally adding `--open-browser`.

## Runtime diagnosis — 2026-10-30

Both optimization stages use the RTX 4090 for sparse normal-matrix assembly and
cuDSS factorization. Kinematics, objective/Jacobian evaluation and trust-region
control run on the CPU. GPU use alone therefore cannot prevent a CPU slowdown.

The user's root `turbostat` measurement confirms **800 MHz busy frequency** despite
maximum HWP performance requests. `IA32_PACKAGE_THERM_STATUS = 0x8840000c` has
external PROCHOT status/log bits 2/3 set, while CPU high-temperature bits 0/1 are
clear. Intel defines this as another platform agent asserting the throttle signal
([SDM volume 3B, §17.9](https://cdrdv2-public.intel.com/874250/253669-090-sdm-vol-3b.pdf#page=48)).
CPU temperature was 36–37°C and package power ~13 W, below the configured
180/253 W limits. This establishes external platform throttling; the exact
component or firmware fault is **unverified**. No system settings were changed.
[Selected hardware counters](../../../outputs/ik-benchmark/validation/tuning/runtime-hardware-status.json)
and [earlier measurements](../../../outputs/ik-benchmark/validation/tuning/runtime-hardware.txt)
are preserved. A post-recovery measurement is still needed to quantify its full
contribution to the historical slowdown.

Controlled [constraint ablation](../../../outputs/ik-benchmark/validation/tuning/runtime-ablation-before.json)
on identical saved inputs measured 41.9 ms per objective/Jacobian evaluation
with original weights, 42.1 ms with reduced weights, and 44.2 ms with added limit
penalties; linear solving stayed ~125 ms in every case. Repeating on the much
less smooth initialization, with more active penalty rows, gave
[41.8 versus 44.5 ms](../../../outputs/ik-benchmark/validation/tuning/runtime-ablation-active-before.json),
with linear solving again ~125 ms. Thus the added constraints cost roughly 5–7%
in objective evaluation on these inputs, not the observed several-fold slowdown.
Constraints can still change convergence and iteration counts. The historical
base-stage comparison itself grew from 15.9 to 48.8 seconds with unchanged
base-stage settings and 700 evaluations in each run; those runs were not isolated.

The isolated profile also exposed avoidable repeated symbolic GPU planning:
40.4 seconds across 893 plans. The solver now reuses a plan when the sparse
structure is unchanged, updates GPU values/RHS in place, and performs fresh
numeric factorization and backward-error checks every iteration. Structural
changes rebuild the plan. [Nine targeted checks](../../../outputs/ik-benchmark/validation/tuning/cache-tests.log)
passed, including invalidation, updated operands, bounds and CPU/CUDA agreement.

| Identical robust-loss configuration | Before | With plan reuse |
| --- | ---: | ---: |
| Both optimization stages | 113.08 s | 69.61 s |
| Linear-solve path | 58.81 s | 12.92 s |
| Symbolic plans | 893 | 3 |
| Whole profiled benchmark, video skipped | 136.04 s | 92.73 s |
| Score /100 | 72.437464 | 72.437464 |

This paired run reduced solve time **38.4%** while the CPU remained throttled.
Both runs used cProfile, one attempt, and the same settings/inputs. Numerical
trajectories are not bit-identical: stage-two evaluations changed from 314 to 341,
maximum palm position difference was 6.31 µm and rotation difference 0.026°;
all four score components and joint/collision passing masks were unchanged.
The base stage reached its 700-evaluation cap in both runs; stage two converged.
[Paired comparison](../../../outputs/ik-benchmark/validation/tuning/runtime-paired-comparison.json),
[before profile](../../../outputs/ik-benchmark/validation/tuning/robust-position-limits-profile.txt),
and [after profile](../../../outputs/ik-benchmark/validation/tuning/robust-position-limits-cached-profile.txt)
preserve the evidence. A fixed-input linear-solve microbenchmark improved from
~125 to 10.5–10.7 ms; this is not a whole-solver speedup claim.

Most original experiments exhaust 700/500 evaluations across three attempts;
one also spent 89 seconds exporting video. `--skip-video` avoids that export
without changing scoring or saved interactive trajectories. To investigate the
remaining platform fault, Dell documents a
[power drain](https://www.dell.com/support/kbdoc/en-us/000139016/how-to-perform-hard-reset)
and the Aurora R16's
[F12 preboot diagnostics](https://www.dell.com/support/manuals/en-us/alienware-aurora-r16-desktop/alienware-aurora-r16-owners-manual/running-the-supportassist-pre-boot-system-performance-check?guid=guid-0b893eed-efbc-4831-a9c4-7298a7a9f619&lang=en-us).
These are proposed troubleshooting steps, not a verified repair; external
throttling protection has not been disabled.

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
The historical viewer used localhost:8080; it is no longer running.

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
