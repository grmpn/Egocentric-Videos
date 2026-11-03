# Future pipeline improvements

Collect potential improvements to revisit once the full baseline pipeline is
working. These ideas are deferred; select and approve an experiment through the
[planning workflow](planning-specs.md) before implementation.

For each idea, record its date, status, motivating evidence, proposed experiment
and how to assess the result. Link any later approved plan and findings here.

## Targeted IK sampling of unoccupied workspace voxels

Added 2026-10-15. Status: deferred until the full baseline pipeline works.

**Motivation:** the preferred 10 million FK samples per arm still leave known
sampling gaps, as shown by the [workspace density comparison](experiments/robot-workspace-purdue.md#density-extension-5m-and-10m-per-arm).
Some unoccupied voxels may contain reachable positions that random joint-space
sampling missed.

**Proposed experiment:** target inverse kinematics (IK) at points in unoccupied
voxels that plausibly represent missed coverage, such as gaps surrounded by
occupied cells or near the sampled boundary. Try multiple starting configurations.
Keep the same robot, joint limits, base/tool frames and positional workspace
definition as the FK baseline. Accept an added occupied voxel only when a
joint-limit-valid solution is verified by forward kinematics to place the tool
inside that voxel. Solver failure leaves reachability unresolved.

**Evaluation:** compare additional verified occupied cells, independent held-out
coverage and runtime against the 10 million sample FK baseline. Inspect remaining
gaps visually. Positional IK evidence does not establish collision clearance,
orientation coverage or trajectory feasibility.
