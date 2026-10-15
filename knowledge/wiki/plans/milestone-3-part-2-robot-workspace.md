# Milestone 3, Part 2 — Robot workspace sampling and distance queries

Approved revision 2 · 2026-10-15 · Density extension: `20261015-workspace-density-001`; original approval: `20261015-workspace-implementation-001` in the [action log](../logs/2026-10.jsonl).

## Objective and deliverable

Build left/right positional workspace approximations for
fixed-base Purdue Alex with SAKE EZGrippers. Deliver reloadable FK point clouds,
2 cm occupancy grids, signed-distance tensors and trilinear queries in robot-base
coordinates, plus interactive 3D views and a verification report for Part 3
placement, independently of human recordings.
The [Stage 3 reference](../topics/stage-3-retargeting.md#part-2-workspace-contract)
records source evidence and proposed conventions.

## Scope and boundaries

- Pin the specified canonical URDF/assets. Proposed defaults: base
  `PEDESTAL_LINK`; sample `LEFT_EZGRIPPER_TCP_LINK` and
  `RIGHT_EZGRIPPER_TCP_LINK` origins. Sample each seven-joint arm independently
  within URDF position limits, including gripper wrist rotation; hold other
  movable joints at documented zero positions. Preserve native geometry,
  metres, radians and left/right identity. Missing frames or bounds fail explicitly.
- Generate reproducible uniform joint-space samples with a recorded seed:
  initially 100,000 per arm, configurable through 10,000,000. Use scikit-robot's
  existing batch FK/voxel capabilities where compatible; pin necessary dependencies
  without disrupting working environments. Retain sampled configurations for
  representative FK checks.
- Use separate occupancy arrays on one padded, axis-aligned lattice covering both
  clouds. Record its lower-corner origin in base coordinates, spacing and axis
  order. A voxel is occupied when it contains a sample; preserve sampling holes
  without dilation, hole filling or convexification. For base point `p`,
  `i = floor((p - origin) / spacing)`; voxel centers are
  `origin + (i + 0.5) * spacing`. Reject nonfinite/out-of-domain queries explicitly.
- Compute SciPy Euclidean distance transforms with metric spacing and an empty
  border; define distance as outside EDT minus inside EDT, negative in occupied
  cells. Use PyTorch trilinear sampling with explicit center/axis conventions and
  domain validity. This approximates the sampled occupancy boundary, not exact
  distance to the robot's true reachable set.
- Provide orbit/pan/zoom views through scikit-robot's interactive viewer, showing
  robot/base axes, distinct hands, point clouds and actual voxel cells with layer
  controls. Display subsampling must not alter saved data.
- Exclude collision filtering, orientation constraints, IK, dynamic limits,
  gripper actuation mapping, placement/segmentation, simulation/control and human
  trajectory or LeRobot changes. Independent workspaces do not certify bimanual
  feasibility.

## Acceptance

- Run the workflow on the Purdue Alex model, reload both clouds/grids/tensors,
  and reproduce queries. Save settings, asset revision, commands, timing/memory,
  sample counts and limits. Compare 100,000, 1,000,000, 5,000,000 and 10,000,000
  samples per arm at 2 cm with the same seed and independent held-out positions.
  Report occupancy growth, held-out FK coverage and remaining gaps without
  claiming completeness.
- Check representative batched FK against ordinary model FK and known transforms;
  verify joint bounds, base/tool frames and hand identity.
- Verify negative coordinates, boundaries, axis order and base/index round trips:
  center reconstruction error is at most 1 cm per axis plus numerical tolerance.
  Synthetic volumes verify distance signs/metres, padding, trilinear center values
  and intermediate values, and explicit invalid-query behavior.
- Exercise camera/layer controls and inspect both clouds/grids from multiple
  viewpoints. Save screenshots and review findings alongside logs and numerical
  results under `outputs/workspace/`. Passing establishes this positional
  approximation only; trajectory feasibility remains Part 3 acceptance.
