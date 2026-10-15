# Stage 3 Part 2 — Purdue Alex workspace acceptance

Verified 2026-10-15 against [approved revision 2](../plans/milestone-3-part-2-robot-workspace.md),
including the user-authorized 5m/10m density extension after initial acceptance.
Part 2 is complete. This accepts a sampled positional approximation; Part 3
placement and trajectory feasibility remain unimplemented and unapproved.

## Reproduction and artifacts

Follow the [environment setup](../../../environment/README.md#robot-workspace-environment)
and [build/view commands](../../../README.md#stage-3-part-2-robot-workspace).
The source is Purdue Alex + SAKE revision `9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b`,
using `PEDESTAL_LINK`, both EZGripper TCP origins and seven joints per arm.
The [contract](../topics/stage-3-retargeting.md#part-2-workspace-contract) owns frame,
array, sampling and query conventions.

Local-only artifacts below are ignored and unavailable in a fresh clone. They can
be regenerated from the pinned public assets and recorded settings/commands.

- [100k report](../../../outputs/workspace/part-2-20261015/100k/workspace_report.json)
  and [execution log](../../../outputs/workspace/part-2-20261015/100k.log).
- [1m report](../../../outputs/workspace/part-2-20261015/1m/workspace_report.json),
  [execution log](../../../outputs/workspace/part-2-20261015/1m.log),
  [left samples](../../../outputs/workspace/part-2-20261015/1m/samples_left.npz),
  [right samples](../../../outputs/workspace/part-2-20261015/1m/samples_right.npz),
  [occupancy/distance export](../../../outputs/workspace/part-2-20261015/1m/workspace_grid.npz).
- [Final tests](../../../outputs/workspace/part-2-20261015/tests-final.log),
  [legacy compatibility](../../../outputs/workspace/part-2-20261015/tests-legacy-compatibility.log),
  [independent completion audit](../../../outputs/workspace/part-2-20261015/completion-audit.json),
  [installed packages](../../../outputs/workspace/part-2-20261015/packages.txt).

## Numerical results

The common lattice is **90 × 114 × 92**, spacing **0.02 m**, with lower-corner
origin **(−0.88, −1.14, −0.46) m** in the base frame. Both grids have an empty
border; no dilation, filling or hull construction is applied.

| Samples per arm | Left occupied voxels | Right occupied voxels | Left held-out coverage | Right held-out coverage |
| --- | ---: | ---: | ---: | ---: |
| 100,000 | 79,177 | 79,125 | 36.65% | 37.60% |
| 1,000,000 | 269,985 | 268,420 | 93.78% | 94.28% |
| 5,000,000 | 316,951 | 315,175 | 99.75% | 99.72% |
| 10,000,000 | 323,388 | 321,562 | 99.91% | 99.92% |

Coverage uses 10,000 independent FK positions per arm, with no out-of-grid cases.
The runs share one lattice and seed, with exact sample prefixes and identical
held-out configurations. Misses fall from **622 left / 572 right** at 1m to
**25 / 28** at 5m and **9 / 8** at 10m. These held-out FK configurations are
reachable under the sampled joint limits; their empty cells demonstrate remaining
sampling gaps. Coverage is weighted by the joint-space sampling distribution;
it does not establish uniform Cartesian coverage or classify every empty cell.

The initial 100k run took **1.82 s**; the 1m run took **4.65 s**, with **612 MiB**
peak process RSS. These are single CPU runs, including model loading, generation,
export and checks, excluding interpreter startup/imports and viewer/browser memory.

All sampled configurations obey the source URDF position bounds. Every sample
maps into its saved hand grid; maximum center reconstruction error remains below
**1 cm per axis**. Sample arrays, grids and distances reload exactly, and 64
reloaded interpolation queries match. Per-arm batch FK checks include zero,
lower/upper bounds and 32 sampled configurations; errors against ordinary FK are
below **5.49e-10 m**, within the configured **1e-8 m** tolerance.

The initial acceptance audit reconstructs occupancy from all two million saved points,
checks joint limits directly from the URDF, verifies exact sample prefixes and
recomputes coverage. Across 400 real-field queries, PyTorch differs from SciPy
regular-grid interpolation by at most **6.53e-16 m**. Another 256 queries verify
EDT signs and metric center distances using independent nearest-neighbor trees.

## Density extension: 5m and 10m per arm

The user authorized both larger runs on 2026-10-15. Only the supported sample
ceiling and CLI help changed; sampling, FK, occupancy and query algorithms are
unchanged. Both runs use seed 42, the
same pinned model/packages, 2 cm voxels and the original independent 10,000
held-out configurations per arm. Original outputs are preserved.

After reviewing these results, the user selected **10 million samples per arm**
as the preferred default on 2026-10-15. The
[default configuration](../../../configs/robot_workspace.json) now matches the
validated 10m run; the 100k run remains historical comparison evidence.

| Samples per arm | Both-arm build time | Left sampling/check/export | Right sampling/check/export | Peak process RSS |
| --- | ---: | ---: | ---: | ---: |
| 1,000,000 | 4.65 s | 1.39 s | 1.37 s | 0.60 GiB |
| 5,000,000 | 17.42 s | 6.84 s | 6.87 s | 1.37 GiB |
| 10,000,000 | 32.81 s | 13.50 s | 13.47 s | 2.33 GiB |

These are single sequential CPU runs, not repeated benchmarks or isolated FK
timings. The timing boundaries match initial acceptance. Doubling 5m to 10m adds
6,437 left and 6,387 right occupied cells (about 2% growth) and reduces held-out
misses from 53 to 17 across both arms. This is diminishing measured gain, with
remaining holes still unclassified outside the known held-out misses.

Both production runs passed all sample-to-cell checks, representative ordinary
FK comparisons (maximum error below 5.49e-10 m), exact sample/grid reloads and 64
reloaded interpolation queries. A separate comparison verified exact 1m→5m→10m
sample prefixes, identical held-out arrays/settings/packages/lattice, monotonically
growing occupancy, recomputed coverage and distance signs. All **10 focused tests
passed in 4.04 s**. Prior independent interpolation and interactive control tests
were not repeated because those algorithms did not change.

Agent inspection of saved X/Z slices at Y = +0.31 m (left) and −0.29 m (right)
shows that the scattered gaps visible at 1m largely disappear by 5m and shrink
further at 10m. Central empty regions and scattered boundary gaps persist; the
figure alone does not establish whether each remaining cell is unreachable.
No geometric hole filling was applied. Plotting reused the existing gravity
environment's Matplotlib; no workspace dependency was added.

- [5m report](../../../outputs/workspace/density-20261015/5m/workspace_report.json)
  and [execution log](../../../outputs/workspace/density-20261015/5m.log).
- [10m report](../../../outputs/workspace/density-20261015/10m/workspace_report.json)
  and [execution log](../../../outputs/workspace/density-20261015/10m.log).
- [Comparison and checks](../../../outputs/workspace/density-20261015/comparison.json),
  [reproduction script](../../../outputs/workspace/density-20261015/compare.py),
  [voxel slice comparison](../../../outputs/workspace/density-20261015/voxel-slices.png),
  [visual review](../../../outputs/workspace/density-20261015/visual-review.json),
  [focused tests](../../../outputs/workspace/density-20261015/tests.log).

Each new run retains both full sample archives and `workspace_grid.npz`. Open
either directory with the existing viewer, for example:

```bash
env -u LD_LIBRARY_PATH PYTHONPATH=src .venv-workspace/bin/python scripts/view_robot_workspace.py \
    outputs/workspace/density-20261015/10m --open-browser
```

## Tests and interactive review

**10 focused tests passed**, including analytic rotated chains/fixed tool offsets,
base-frame invariance under moving the entire model, deterministic prefixes,
negative coordinates and boundaries, empty padding/holes, metric EDT, float32/64
interpolation and gradients, actual-asset CLI/reload, overwrite refusal and
failed-model-revision behavior. The legacy Python 3.10 / Torch 1.13 environment
passed eight checks; two scikit-robot-dependent checks skipped as expected.
No shared inference behavior changed, so inference regressions were not rerun.

Automated Chrome exercised orbit, pan, zoom and all four hand/representation
checkboxes. Both browser runs had zero page errors. Agent visual inspection
confirmed distinct left/right clouds, actual stepped voxel cells, changed camera
views, independent layer visibility, and the reference robot/base axes when layers
are hidden. Point display uses 50,000 samples per hand; all occupied cubes are
available, with mesh LOD disabled.

- [Final point clouds](../../../outputs/workspace/part-2-20261015/points-final.png),
  [robot and base axes](../../../outputs/workspace/part-2-20261015/robot-reference.png),
  [left cloud after orbit](../../../outputs/workspace/part-2-20261015/points-left-final.png).
- [Both voxel grids](../../../outputs/workspace/part-2-20261015/voxels-both.png),
  [left voxels](../../../outputs/workspace/part-2-20261015/voxels-left.png),
  [right voxels](../../../outputs/workspace/part-2-20261015/voxels-right.png).
- [Browser interaction evidence](../../../outputs/workspace/part-2-20261015/browser-review.json),
  [final viewer check](../../../outputs/workspace/part-2-20261015/browser-final.json),
  [visual review findings](../../../outputs/workspace/part-2-20261015/visual-review.json).

Software WebGL rendered the full voxel layers slowly; GPU-browser performance
was not measured. Initial sandbox socket restrictions prevented viewer startup;
the authorized retry worked. Early tests exposed a float32 boundary-rounding bug,
which was fixed, and an unnecessarily strict ordinary-FK fixture tolerance,
which was aligned with the configured tolerance. Failed attempts remain in the
[action log](../logs/2026-10.jsonl) and local logs.

Passing does not establish complete workspace coverage, an exact continuous SDF,
physical robot calibration, collision clearance, attainable tool orientations,
simultaneous bimanual feasibility, dynamic limits or trajectory execution.
Part 3 must decide and verify those constraints before accepting robot trajectories.
