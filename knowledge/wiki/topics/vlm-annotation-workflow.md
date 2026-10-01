# VLM annotation workflow: future refinement reference

Adapted on 2026-10-01 from the user-provided
`vlm_annotation_workflow_handoff.md`. This page preserves the proposed direction
for later milestones; it is not an approved implementation plan or a description
of an implemented hierarchy. The handoff's mobile-base use case motivates retaining
navigation between manipulations. Robot embodiment and implementation scope still
need agreement in the relevant milestone plan.

The [LeRobot pipeline](lerobot-pipeline.md#mutation-and-annotation-preservation)
owns current commands, storage and preservation behavior. The
[approved Milestone 2 plan](../plans/milestone-2-lerobot-pilot.md) remains the active
scope. Implementation claims below were checked against project revision
`f1784f1` and installed LeRobot revision `9a6bb610` on 2026-10-01; no new inference
or workflow experiment was run for this reference.

## Semantic hierarchy and coverage

Preserve this proposed hierarchy independently of how video is sampled or stored:

```text
Source video
└── Top-level task: Make coffee
    ├── Child task: Retrieve mug
    │   ├── Semantic subtask: Walk to cabinet
    │   ├── Semantic subtask: Open cabinet
    │   └── Semantic subtask: Grasp mug
    └── Child task: Prepare coffee machine
        ├── Semantic subtask: Carry mug to machine
        └── Semantic subtask: Position mug
```

A top-level task is a coherent objective; a child task is a meaningful phase;
a semantic subtask describes visible behavior within that phase. “Atomic” means
the intended annotation granularity, not a guaranteed property of VLM output.
Low-level base, arm and gripper commands remain separate robot trajectories.

VLM context windows, semantic task boundaries, storage episodes and training/action
chunks serve different purposes. Long tasks may require several VLM windows.
Choose semantic boundaries using goals, workspace transitions, object-state
changes and navigation targets. Preserve task-relevant walking, carrying,
repositioning and waiting even when hands are inactive or invisible. Hand validity
should remain separate from semantic coverage.

The [HuRo source review](huro-source-review.md#language-annotation) describes its
seven-second overlapping windows and geometric eligibility rules. Those are
reference implementation choices, not semantic definitions to adopt here.

## Proposed coarse-to-fine flow

1. **Coarse segmentation:** sample timestamped RGB from the source video and ask
   one coarse stage for both top-level tasks and child boundaries. Start by
   evaluating 0.5–1 FPS; this is a candidate setting, not a validated rate.
   The coarse stage identifies structure rather than every semantic subtask.
2. **Child episodes:** create a derived LeRobot episode for each accepted child
   interval, retaining its parent IDs and source-frame mapping. Supply the child
   label as its known task instruction. Preserve original video and annotations.
3. **Fine annotation:** annotate each child independently with `lerobot-annotate`.
   Child membership then follows from the episode association without another
   VLM grouping pass. Review coarse labels first: an incorrect instruction can
   bias the finer labels.
4. **Merge:** read saved subtask boundaries, map them to the source timeline and
   attach them to the recorded parents. Reconstruct the hierarchy without another
   model call.

One coarse **stage** does not imply one request for an arbitrarily long video.
A future implementation must budget sampled frames and context length; if it
windows the source, it must reconcile tasks continuing across window edges and
duplicate boundaries. Sparse sampling can miss short transitions. Sample density
and boundary review need evaluation before calling this approach compute-saving.

Annotate selected task windows at fine resolution, but account for omitted source
intervals explicitly. Do not discard navigation as “irrelevant” simply because
there is no manipulation. Keep auxiliary modules disabled as in the existing
wrapper; memory generation is not free and is not part of this proposal's first
version. Measure total calls, sampled frames/tokens where available, runtime and
review effort, since splitting into children can also increase overhead.

## Structured coarse output and interval rules

Request structured JSON with source identity, task/child IDs, labels and source
times in seconds. Prefer schema-constrained output when the selected backend
supports it; support is not established by this reference. Otherwise parse strict
JSON and validate it, using bounded retries with actionable errors. Retain the raw
response for review; do not silently repair semantic boundaries or invent labels.

For a sequential task, the handoff's compact representation stores child starts
and the parent's end. For example, a parent `[12.4, 120.1)` with child starts
`12.4, 31.7, 58.2` expands to:

```text
[12.4, 31.7)   Retrieve mug
[31.7, 58.2)   Prepare coffee machine
[58.2, 120.1)  Brew coffee
```

Use half-open intervals `[start_s, end_s)` to give each shared boundary one owner.
This is a valid contiguous partition only if the first child starts at the parent
start, starts increase strictly, and all children have positive duration within
the parent/source bounds. Revalidate after snapping to frames; distinct model
times can collapse to the same frame. Stable IDs and valid parent references are
also required. These are proposed checks, not a new persisted schema.

Contiguity guarantees coverage, not correct meaning. Represent waiting,
transitions and uncertain intervals explicitly when observed; do not stretch a
manipulation label merely to fill a gap. Concurrent activities may require a later
representation choice; a sequential partition cannot express overlapping children.
Model-generated confidence, if retained, is uncalibrated and cannot replace review.

## Source-time mapping and context padding

Use source seconds measured from the first decoded source presentation timestamp,
matching [video preparation](../../../src/egocentric_pipeline/video_preparation.py).
Keep the requested semantic interval, selected frames and clip-relative timeline
distinct. The simple relation

`source_time = extraction_start + child_time`

describes the nominal target timeline. It is exact only when extraction preserves
that offset. Current preparation selects source frames for a 30 FPS grid; exact
source-frame timestamps may differ from the target times. Resolve saved annotation
boundaries to episode frame indices and use the existing float64
`observation.source_timestamp_s` values or preparation mapping for exact alignment.
The [dataset contract](lerobot-pipeline.md#dataset-contract) owns these fields.
Do not recover exact source times from rounded reader timestamps or FPS alone.

The final interval needs an explicit exclusive endpoint from the selected child
interval; the last frame's timestamp is not the end of its duration. Preserve both
requested boundaries and actual frame mapping so rounding and boundary choices
remain inspectable. A later merge must define its endpoint policy and check it
against source bounds.

Optional 1–2 second context padding on either side is an experiment, not an
existing wrapper feature. If used, distinguish the true child interval from the
larger extraction interval, clip context to source bounds, and map local time from
the **padded extraction origin**. Keep accepted output within the true child
interval; review or split labels crossing its boundaries and exclude padding-only
labels. Otherwise neighboring children can acquire duplicated actions.

## Reuse and integration gaps

The existing [annotation wrapper](../../../src/egocentric_pipeline/annotations.py)
already uses known task labels, emits plans/subtasks, and disables task discovery,
rephrasing, memory, interjections and VQA. It validates and publishes annotations
while preserving prior episodes. Keep those protections when evaluating this flow.
It refuses to annotate episodes with existing language records; rerun experiments
need an unannotated baseline or an explicitly designed replacement workflow.

Important limits of the current integration:

- Saved `language_persistent` records carry a style, content and **start timestamp**,
  not the handoff's illustrative `{start, end, label}` interval JSON. A future
  merger must select `subtask` records, sort their unique starts and derive ends
  from the next start and the defined child endpoint. Plan records are remaining
  steps within an episode, not the proposed top-level hierarchy.
- The pinned annotator stitches subtasks over the whole episode. Structural
  validation does not prove that waiting/navigation labels or boundaries are
  correct. Its current sampling and minimum-duration defaults are documented in
  the [pipeline topic](lerobot-pipeline.md#mutation-and-annotation-preservation);
  short actions are not guaranteed to become separate subtasks.
- There is no coarse segmenter, automatic child extraction, parent/child storage,
  padding adapter or hierarchical merger in the current workflow. Existing dataset
  creation requires completed HaWoR exports; it is not a standalone RGB-only
  child-episode builder. A later plan must choose where annotation and geometry
  extraction meet while preserving their validity independently.
- Semantic alignment does not align geometry: separately processed clips have
  independent world origins and canonical anchors. Reusing a continuous source
  reconstruction versus processing children separately is a later design choice,
  especially for mobile-base motion. Source timestamps alone do not establish
  metric navigation or a shared world frame.

Retain source identity, task/child/subtask IDs, parent relationships, labels,
source intervals and the derived dataset/episode association. Record model/run
provenance and review status using existing mechanisms where possible. Choose a
minimal hierarchy storage contract when implementing; do not imply that these
parent fields already exist in LeRobot or add a parallel provenance system now.

## Evidence needed before adoption

The [2026-09-25 Eidon evidence](../experiments/milestone-2-eidon-validation.md#desktop-annotation-retry--2026-09-25)
establishes execution and preservation on two four-second clips. Each received one
subtask, and the cooking object's noun is questionable despite zero structural
validator errors. This does not validate long-horizon segmentation, transition
timing or navigation coverage; human review remains pending in that evidence.

For a later approved refinement, use a small reviewed sample containing multiple
phases, carrying/navigation, waiting, brief interactions and uncertain boundaries.
Compare against the existing annotation workflow on the same footage. Agree on
semantic granularity and boundary tolerances before comparing results, accounting
for sampling limits and reviewer ambiguity. Check:

- Correct objectives, child association and visible action/object labels; retained
  navigation/waiting and explicit accounting for uncovered or uncertain intervals.
- Boundary error against reviewed source frames, including variable frame timing,
  adjacent children, final endpoints, context-window seams and optional padding.
- Saved/reloaded hierarchy and frame alignment; preservation of existing labels,
  RGB, trajectories and validity metadata after annotation.
- Total compute and human correction effort, including retries and rejected coarse
  segments, rather than only successful fine-annotation calls.

Begin with coarse structure, derived children, fine annotation and deterministic
merge. Defer adaptive sampling, elaborate ontologies, extra VLM verification
passes, hierarchical memory and policy-generated memory until an evaluation shows
a concrete need. Preserving hierarchy may support later alignment with camera,
hand, object and robot trajectories; it does not establish their accuracy or
authorize retargeting work.
