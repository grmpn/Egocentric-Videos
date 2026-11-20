# iPhone trajectory comparison — 2026-11-20

The [approved comparison](../plans/iphone-trajectory-comparison.md) is fulfilled.
All three methods completed the full 1,286-frame, 30 FPS iPhone demonstration.
LingBot-Map and AMB3R-VO agree most closely; this does **not** establish which
method is accurate. Milestone 3 simulation acceptance remains open.

The [workflow topic](../topics/trajectory-comparison.md) owns the method,
coordinate conventions, reproduction command, dependencies and checkpoint provenance.
All linked run artifacts are local-only under
[`outputs/trajectory-comparison/iphone-20261119/`](../../../outputs/trajectory-comparison/iphone-20261119/),
ignored by Git and unavailable in a fresh clone.

## Conditions and shared work

The 960×540 working MP4 preserves every source timestamp. No resolution reduction
was needed. HaWoR used its native masked DROID-SLAM settings and 600 px focal
prior; LingBot used 518×294, bfloat16, SDPA, eight initial scale frames and
keyframe interval five; AMB3R used its native 518×392 center crop, bfloat16 and
VO settings. Backend runs were sequential on the same RTX 4090 (24 GiB).
Native input fields of view, numerical precision and software environments differ.

Detection/camera-space hand estimation ran once: **519.597 s**. GeoCalib ran once
on frame 0: **11.682 s**. Metric3D ran once on each of **86 HaWoR keyframes**:
**65.263 s**, reused by both HaWoR and LingBot. AMB3R used its own learned metric
depth. All paths have the same initial camera transform, Z up and initial
horizontal camera-forward along +X. Gravity sets orientation, not metric scale.
No trajectory-to-trajectory fitting, world-motion infilling or smoothing was used.

## Pairwise position disagreement

Distances are in metres. The sum adds framewise Euclidean distances; it depends
on sample count and is **not travelled distance**. Every pair uses the same
support within its channel: camera 1,286/1,286 (100%); left wrist 862/1,286
(67.03%); right wrist 934/1,286 (72.63%).

| Channel | Pair | Sum (m) | Mean (m) | RMSE (m) |
| --- | --- | ---: | ---: | ---: |
| Camera | HaWoR / LingBot | 2655.351 | 2.065 | 2.394 |
| Camera | HaWoR / AMB3R | 2097.809 | 1.631 | 1.900 |
| Camera | LingBot / AMB3R | 612.506 | 0.476 | 0.560 |
| Left wrist | HaWoR / LingBot | 1819.144 | 2.110 | 2.450 |
| Left wrist | HaWoR / AMB3R | 1417.429 | 1.644 | 1.928 |
| Left wrist | LingBot / AMB3R | 436.519 | 0.506 | 0.584 |
| Right wrist | HaWoR / LingBot | 1966.873 | 2.106 | 2.439 |
| Right wrist | HaWoR / AMB3R | 1533.022 | 1.641 | 1.920 |
| Right wrist | LingBot / AMB3R | 471.908 | 0.505 | 0.581 |

Exact values: [disagreement CSV](../../../outputs/trajectory-comparison/iphone-20261119/disagreement.csv)
and [combined JSON](../../../outputs/trajectory-comparison/iphone-20261119/comparison.json).

## Runtime

Single runs, seconds. Backend wall time includes loading, inference, preprocessing
and export; inference columns include the native algorithm's internal mapping and
optimization. Other backend work is retained in the CSV.

| Method | Loading | Inference | Backend wall | Backend FPS | Assembled total | Assembled FPS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| HaWoR | 2.500 | 245.820 | 253.755 | 5.068 | 852.611 | 1.508 |
| LingBot-Map | 36.451 | 203.695 | 249.703 | 5.150 | 848.847 | 1.515 |
| AMB3R-VO | 64.572 | 727.397 | 837.236 | 1.536 | 1369.023 | 0.939 |

Assembled totals add shared hands/gravity (531.279 s), backend wall time,
method-specific scale fitting (2.278 / 2.575 / 0.484 s), alignment/export
(0.035 / 0.027 / 0.025 s), and Metric3D for its two consumers. They exclude
downloads, environment compilation, input verification, shared scale-input
I/O/preparation, pairwise scoring and rendering. These are assembled processing
costs, not repeated end-to-end benchmarks. Shared hand inference overlapped CPU
dependency compilation; the camera runs did not. GPU extensions were checked
before timing, so kernel caches were partly warm.

[Runtime CSV](../../../outputs/trajectory-comparison/iphone-20261119/runtime.csv)
and individual `*_timing.json` files retain the breakdown. Peak GPU allocated
memory was 5.23 GiB (HaWoR), 14.84 GiB (LingBot), and 12.29 GiB (AMB3R);
peak reserved memory was 7.26, 22.04, and 16.46 GiB respectively.

## Scale evidence and interpretation

One global median scale was applied per camera path. Hand dimensions remained in
metres and were never multiplied by camera scale. Raw units differ by model;
scale values themselves are not a quality ranking.

| Method | Global metres/raw unit | Per-frame interquartile range | Per-frame min–max |
| --- | ---: | ---: | ---: |
| HaWoR | 0.914159 | 0.753–1.157 | 0.099–2.579 |
| LingBot | 3.493898 | 2.665–4.154 | 0.690–4.929 |
| AMB3R | 4.239989 | 4.061–4.414 | 3.574–5.160 |

[Scale fits](../../../outputs/trajectory-comparison/iphone-20261119/scales.json)
record every selected frame, support size and metric-depth range. HaWoR and
LingBot used identical frames, masks, pixel support and range expansions.
The wide scale variation is a material uncertainty: disagreement combines
tracking, depth-scale and camera-model effects. This run does not separate them.

The coordinate/time plots show HaWoR's smaller forward displacement after the
first walking segment (roughly 10–16 s). LingBot and AMB3R follow closer paths,
with more separation later. Shared hand gaps remain visible. Neither this
agreement nor the initial gravity estimate establishes physical accuracy.
AMB3R checkpoint identity with the quota-limited official Drive file remains
unverified; the downloaded mirror matches its published checksum and official
file size, as documented in the workflow topic.

## Review artifacts and acceptance

- [3D and XY camera/wrist paths](../../../outputs/trajectory-comparison/iphone-20261119/trajectories.png)
- [XYZ coordinates over time](../../../outputs/trajectory-comparison/iphone-20261119/coordinates.png)
- [Pairwise disagreement over time](../../../outputs/trajectory-comparison/iphone-20261119/disagreement.png)
- [Runtime graph](../../../outputs/trajectory-comparison/iphone-20261119/runtime.png)
- [Six representative RGB/hand overlays](../../../outputs/trajectory-comparison/iphone-20261119/hand_overlays.png)
- [Independent numeric audit](../../../outputs/trajectory-comparison/iphone-20261119/numeric-validation.json)
  and its [inspection code](../../../outputs/trajectory-comparison/iphone-20261119/audit_comparison.py)
- [12 passing focused tests](../../../outputs/trajectory-comparison/iphone-20261119/final-tests.log)

All plots were visually inspected. The audit checked all 1,286 camera frames for
each method, exact frame/timestamp mappings, proper rotations, common starting
transforms, gravity alignment, positive global scales, unchanged hand geometry,
missing-data masks, all nine metric rows and runtime arithmetic. AMB3R mapped
every frame. Maximum world-to-camera hand roundtrip residual was below 2×10⁻⁷ m.
These checks establish contract consistency, not ground-truth accuracy.

The local output directory retains raw/aligned arrays, shared hand/depth/gravity
outputs, settings and logs. Failed dependency builds and the pre-inference
LingBot interpreter-path failure were preserved; the latter was fixed without
repeating completed inference. The launcher regression and native scale recovery
are covered by tests. Events `20261120-trajectory-comparison-003` through `008`
in the [November log](../logs/2026-11.jsonl) record execution and validation.

No backend was adopted into the ordinary pipeline and no robot/export behavior
changed. The next action is review of this comparison and the remaining
Milestone 3 simulation acceptance; any backend adoption needs its own scope.
