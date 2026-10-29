# IK benchmark joint limits

Approved benchmark settings · inspected 2026-10-29 · Authorized by the
[benchmark plan](../plans/milestone-3-ik-benchmark.md). The user requested a proxy
based on other humanoids or typical values when no Alex acceleration limit was
found; see event `20261029-ik-benchmark-001`.

## Alex model evidence

The local canonical Purdue Alex/EZGripper URDF is pinned to
`9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b` by
[robot settings](../../../configs/robot_workspace.json). Static XML inspection
found 24 revolute joints, including four mimic followers, with finite position
and velocity bounds. These are model limits, not new hardware measurements.

| Joint suffix | Left position range (rad) | Right position range (rad) | Maximum speed (rad/s) |
| --- | --- | --- | --- |
| `SHOULDER_Y` | −3.141592 to 1.22173 | −3.141592 to 1.22173 | 10.38 |
| `SHOULDER_X` | −0.261799 to 2.87979 | −2.87979 to 0.261799 | 10.38 |
| `SHOULDER_Z` | −1.91986 to 1.22173 | −1.22173 to 1.91986 | 4.47 |
| `ELBOW_Y` | −2.35619 to 0.174533 | −2.35619 to 0.174533 | 4.47 |
| `WRIST_Z` | −2.61799 to 2.61799 | −2.61799 to 2.61799 | 17.3 |
| `WRIST_X` | −1.48353 to 0.959931 | −0.959931 to 1.48353 | 17.3 |
| `GRIPPER_Y` | −0.785398 to 0.785398 | −0.785398 to 0.785398 | 17.3 |
| EZGripper joints, including mimics | 0 to 1.94 | 0 to 1.94 | 3.67 |

Neck yaw (`NECK_Z`) is ±1.22173 rad and pitch (`NECK_Y`) is ±0.488692 rad;
both have a 17.3 rad/s speed limit. The benchmark should read values from the
[pinned URDF](https://github.com/PatrizioAcquadro/purdue-alex-assets/blob/9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b/assets/robots/alex_purdue/urdf/baseline/alex_purdue_full_convex.urdf),
rather than maintain a duplicate numeric implementation table.

The [robot actuator configuration](https://github.com/PatrizioAcquadro/purdue-alex-assets/blob/9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b/src/ihmc_alex_isaaclab/robots/alex_purdue.py)
agrees with these speed limits. Neither it nor the inspected robot assets
supplies acceleration bounds. Effort limits cannot be converted into a constant
acceleration bound without configuration, inertia, gravity and loading assumptions.

The convex model contains 28 links with collision geometry. Its
[physics configuration](https://github.com/PatrizioAcquadro/purdue-alex-assets/blob/9ac4bd45c779d3f73d61f5b144cd1bb76dc8607b/src/ihmc_alex_isaaclab/robots/purdue_physics.py)
declares three false-positive collision exclusions: head–torso and each
gripper-Y link–wrist-Z link. Actual pair handling, including rigid assemblies
and adjacent links, must be documented and checked during implementation.
This inspection did not execute collision checks.

## Acceleration reference search and proposed cap

Primary sources do not establish a universal humanoid acceleration limit:

- PAL Robotics' [TALOS MoveIt configuration](https://github.com/pal-robotics/talos_moveit_config/blob/ca78cfcf3c2299c0ce226c4b3000bd362426238a/config/joint_limits.yaml)
  disables acceleration limits. Its stored zero values therefore mean no enabled
  limit, not a zero-acceleration requirement.
- Kim and Oh's [humanoid IK study](https://journals.sagepub.com/doi/10.5772/55247),
  section 3.3, uses 1,800°/s² = **31.416 rad/s²** for a simulated three-joint
  planar arm. Section 5.1 says Hubo velocity/acceleration limits were determined
  experimentally; the simulated-arm number is not a Hubo hardware specification.
- Ren, Li and Sun's [humanoid manipulation study](https://journals.sagepub.com/doi/10.5772/63070),
  table 3, lists **100–300 rad/s²** for a seven-joint ping-pong arm. These values
  describe a high-speed research example, not ordinary Alex manipulation.
- PickNik's [configuration documentation](https://docs.picknik.ai/how_to/configuration_tutorials/config_yaml_reference/#moveit_paramsjoint_limits)
  illustrates a **5 rad/s²** joint-acceleration setting. This is a configuration
  example, not a manufacturer rating or a measured typical value.

Use **10 rad/s² for each evaluated revolute joint** as the initial configurable
benchmark screening cap. This is an engineering inference: it lies above the
5 rad/s² planning example and below the research examples, while keeping one
explicit comparison rule. Applying it to neck and gripper joints is also an
assumption, not evidence about their hardware. Save the cap and its status in
every run and at the top of `REPORT.md`; permit explicit per-joint overrides.
Do not tune the cap to make a configuration pass. Changing it changes the
benchmark definition and requires consistent rescoring for comparable ranks.

This choice enables a complete simulation benchmark; it does not verify Alex's
physical acceleration capacity or authorize hardware playback.
