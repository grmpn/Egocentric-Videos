# Project knowledge

Start with [current status](status.md). Follow only the pages relevant to the task.
The [roadmap](../raw/Project-Milestones-and-Timeline.md) defines long-term scope;
[AGENTS.md](../../AGENTS.md) defines repository-wide working rules.

## Planning and maintenance

- [Planning specification](planning-specs.md) — short scope, optional subphases, and acceptance.
- [Knowledge maintenance](knowledge-maintenance.md) — page ownership, JSONL event format, and queries.
- [Planning and knowledge decision](decisions/planning-and-knowledge.md) — approved ownership and migration choices.
- [Future pipeline improvements](future-improvements.md) — deferred ideas to revisit after the full baseline works, starting with targeted IK sampling of suspected workspace gaps.

## Plans

- [Milestone 3: Direct hand-to-gripper mapping](plans/milestone-3-direct-gripper-mapping.md) — revision 7 fulfilled: MCP/index-PIP plane orientation, fingertip-midpoint placement and FK-derived opening in the detached first-region viewer.
- [Milestone 3: Hand-pose smoothing and region continuity](plans/milestone-3-hand-pose-refinement.md) — fulfilled: configurable target filtering, base prior and merging; controlled comparisons and full rerun, with pose/motion tradeoffs.
- [Milestone 3: GPU trajectory IK](plans/milestone-3-gpu-ik.md) — fulfilled GPU solver, matched benchmark and latest smoothing-configuration rerun.
- [Milestone 3: Joint base and trajectory optimization](plans/milestone-3-joint-base-optimization.md) — original fitting and infill-exclusion evidence preserved; approved stronger-smoothing experiment verified.
- [Milestone 3: Wrist alignment amendment](plans/milestone-3-wrist-alignment.md) — approved robot-wrist-to-human-wrist matching, verified with regenerated workspaces and playback; fulfilled.
- [Milestone 3, Part 3: Placement and segmentation](plans/milestone-3-part-3-placement-and-segmentation.md) — approved camera segmentation, base fitting, region expansion and positional IK acceptance; fulfilled.
- [Milestone 3, Part 2: Robot workspace](plans/milestone-3-part-2-robot-workspace.md) — approved FK sampling, voxel distance queries and interactive review, including the 5m/10m density comparison; fulfilled.
- [Milestone 3, Part 1: Gravity alignment](plans/milestone-3-part-1-gravity-alignment.md) — approved Part 1 scope and acceptance.
- [Milestone 2: Video-to-LeRobot pilot](plans/milestone-2-lerobot-pilot.md) — approved scope and acceptance.
- [Milestone 1: HaWoR baseline](plans/milestone-1-hawor-baseline.md) — preserved approval record for a completed milestone; historical paths and resolved questions remain unchanged. New plans use the short specification above.

## Topics and evidence

- [Direct hand-to-gripper mapping](topics/direct-gripper-mapping.md) — detached gripper, MANO landmark/pose/action contracts and interactive tuning without IK.
- [Direct iPhone gripper review](experiments/direct-gripper-iphone.md) — first-region geometry, opening saturation, synchronized viewer and acceptance evidence.
- [Hand-pose refinement evidence](experiments/hand-pose-refinement.md) — seven controlled variants, full iPhone rerun, raw/smoothed pass rates and all-experiment viewer.
- [iPhone retargeting evidence](experiments/retargeting-iphone.md) — full demonstration, infill exclusion, 1,000× temporal-weight comparison and verified CUDA rerun (6.29× faster solve).
- [Joint base/pose fitting evidence](experiments/joint-base-bundled.md) — original benchmark and subsequent experiments, including gripper-offset/hand-weight results and visual evidence; posture, motion and orientation tradeoffs.
- [Stage 3: Fixed-base trajectory preparation](topics/stage-3-retargeting.md) — implemented gravity, workspace, placement/segmentation and positional IK contracts and limitations.
- [Stage 3 Part 3 acceptance](experiments/retargeting-bundled.md) — historical TCP runs and current wrist-aligned episodes, independent transform/SDF/IK audits, annotated video and MANO playback with preserved failures/discontinuities.
- [Stage 3 Part 2 acceptance](experiments/robot-workspace-purdue.md) — Purdue FK runs through 10 million samples per arm, grid/query verification, sampling gaps and interactive review.
- [Stage 3 Part 1 acceptance](experiments/gravity-alignment-bundled.md) — bundled GeoCalib run, reversible geometry, preserved data, tests and visual review; physical accuracy limits remain explicit.
- [HaWoR pipeline](topics/hawor-pipeline.md) — current stage boundaries, coordinate/time conventions, and implementation references.
- [LeRobot pipeline](topics/lerobot-pipeline.md) — v3.1 creation/append, canonical transforms, annotation preservation and local inference limits.
- [VLM annotation workflow reference](topics/vlm-annotation-workflow.md) — proposed task hierarchy and independent activity modes, source-time mapping, and later fixed-base filtering; not implemented or an approved plan.
- [HuRo source review](topics/huro-source-review.md) — external detection-gap handling, infiller bypass, retargeting, and language annotation; static inspection only.
- [Milestone 2 Eidon validation](experiments/milestone-2-eidon-validation.md) — all three attempts, real dataset append/reload, visual quality limits and remaining pilot acceptance.
- [Milestone 1 baseline acceptance](experiments/milestone-1-baseline.md) — accepted runs, provenance, validation, and unresolved quality limits.

## Action history

- [October 2026 events](logs/2026-10.jsonl) — timestamped maintenance and project work.
- [September 2026 events](logs/2026-09.jsonl) — imported historical actions and timestamped maintenance work.

## Source notes

- [Milestone 3 update](../../Milestone3-Update.md) — local user input, preserved untracked. Later user amendments are captured by the active plan, which owns current scope.
- [Stage 3 user spec](../../Stage-3-Spec.md) — local-only input updated by the user through Part 3; preserved during planning, with Part 3 scope captured in the approved plan above.
- [HaWoR research notes](../raw/Sources/HaWoR-Review.md) — original source material, preserved.
- [Eidon and LeRobot](../raw/Sources/Eidon-LeRobot-Review.md) — pilot selection, camera-evidence limits, and the v3.1 annotation choice.
- [HuRo workflow reference](../raw/Sources/HuRo-Review.md) — related pipeline and pointers for later investigation; not an adopted implementation.

Local-only reports and figures stay under `knowledge/agent/summaries/`; see the
acceptance page for links. They and linked run outputs are unavailable in a fresh clone.
