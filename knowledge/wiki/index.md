# Project knowledge

Start with [current status](status.md). Follow only the pages relevant to the task.
The [roadmap](../raw/Project-Milestones-and-Timeline.md) defines long-term scope;
[AGENTS.md](../../AGENTS.md) defines repository-wide working rules.

## Planning and maintenance

- [Planning specification](planning-specs.md) — short scope, optional subphases, and acceptance.
- [Knowledge maintenance](knowledge-maintenance.md) — page ownership, JSONL event format, and queries.
- [Planning and knowledge decision](decisions/planning-and-knowledge.md) — approved ownership and migration choices.

## Plans

- [Milestone 2: Video-to-LeRobot pilot](plans/milestone-2-lerobot-pilot.md) — approved scope and acceptance; implementation in progress.
- [Milestone 1: HaWoR baseline](plans/milestone-1-hawor-baseline.md) — preserved approval record for a completed milestone; historical paths and resolved questions remain unchanged. New plans use the short specification above.

## Topics and evidence

- [HaWoR pipeline](topics/hawor-pipeline.md) — current stage boundaries, coordinate/time conventions, and implementation references.
- [LeRobot pipeline](topics/lerobot-pipeline.md) — v3.1 creation/append, canonical transforms, annotation preservation and local inference limits.
- [HuRo source review](topics/huro-source-review.md) — external detection-gap handling, infiller bypass, retargeting, and language annotation; static inspection only.
- [Milestone 1 baseline acceptance](experiments/milestone-1-baseline.md) — accepted runs, provenance, validation, and unresolved quality limits.

## Action history

- [September 2026 events](logs/2026-09.jsonl) — imported historical actions and timestamped maintenance work.

## Source notes

- [HaWoR research notes](../raw/Sources/HaWoR-Review.md) — original source material, preserved.
- [Eidon and LeRobot](../raw/Sources/Eidon-LeRobot-Review.md) — pilot selection, camera-evidence limits, and the v3.1 annotation choice.
- [HuRo workflow reference](../raw/Sources/HuRo-Review.md) — related pipeline and pointers for later investigation; not an adopted implementation.

Local-only reports and figures stay under `knowledge/agent/summaries/`; see the
acceptance page for links. They and linked run outputs are unavailable in a fresh clone.
