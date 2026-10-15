# Stage 3 Part 2 — Purdue Alex workspace acceptance

Verified 2026-10-15 against [approved revision 1](../plans/milestone-3-part-2-robot-workspace.md).
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

Coverage uses 10,000 independent FK positions per arm, with no out-of-grid cases.
The 100k subset is an exact prefix of the 1m samples and is evaluated on the same
lattice. **622 left / 572 right misses remain** at 1m; these are sampling holes
or voxel-resolution effects, not evidence that the held-out configurations are
unreachable. Neither percentage establishes uniform Cartesian coverage.

The default run took **1.82 s**; the 1m run took **4.65 s**, with **612 MiB**
peak process RSS. These are single CPU runs, including model loading, generation,
export and checks, excluding interpreter startup and viewer/browser memory.

All sampled configurations obey the source URDF position bounds. Every sample
maps into its saved hand grid; maximum center reconstruction error remains below
**1 cm per axis**. Sample arrays, grids and distances reload exactly, and 64
reloaded interpolation queries match. Per-arm batch FK checks include zero,
lower/upper bounds and 32 sampled configurations; errors against ordinary FK are
below **5.49e-10 m**, within the configured **1e-8 m** tolerance.

The independent audit reconstructs occupancy from all two million saved points,
checks joint limits directly from the URDF, verifies exact sample prefixes and
recomputes coverage. Across 400 real-field queries, PyTorch differs from SciPy
regular-grid interpolation by at most **6.53e-16 m**. Another 256 queries verify
EDT signs and metric center distances using independent nearest-neighbor trees.

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
