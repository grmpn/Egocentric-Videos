# VLM annotation workflow: future refinement reference

Adapted on 2026-10-01 from the user-provided
`vlm_annotation_workflow_handoff.md`, with the independent activity-mode track and
fixed-base use case added from `annotation_update.md` on 2026-10-01.
This page preserves the proposed direction for later milestones; it is not an
approved implementation plan or a description
of an implemented hierarchy. The handoff's mobile-base use case motivates retaining
navigation between manipulations; the activity track also supports later fixed-base
filtering without redefining the task hierarchy. Robot embodiment and implementation
scope still need agreement in the relevant milestone plan.

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

A child task identifies the goal being pursued and can contain both walking and
manipulation. Keep “Retrieve mug” as one child even when it includes walking to a
cabinet, opening it and grasping the mug. A locomotion interval does not require
a separate child task.

VLM context windows, semantic task boundaries, storage episodes and training/action
chunks serve different purposes. Long tasks may require several VLM windows.
Choose semantic boundaries using goals, workspace transitions, object-state
changes and navigation targets. Preserve task-relevant walking, carrying,
repositioning and waiting even when hands are inactive or invisible. Hand validity
should remain separate from semantic coverage.

The [HuRo source review](huro-source-review.md#language-annotation) describes its
seven-second overlapping windows and geometric eligibility rules. Those are
reference implementation choices, not semantic definitions to adopt here.

## Independent activity-mode timeline

Alongside the task hierarchy, keep a source-time track named `activity_segments`
describing the general embodied behavior. Use exactly this initial vocabulary:

| Mode | Interpretation |
| --- | --- |
| `locomotion` | Meaningful body translation between workspaces or targets, including walking toward or away from a task location. |
| `manipulation` | Local object-directed interaction: reaching, grasping, opening, placing, pouring or operating objects. |
| `other` | Idle, waiting, ambiguous or non-task behavior, and activity that does not clearly fit locomotion or manipulation. |

This track is independent of the hierarchy: child tasks describe goals, activity
modes describe the general behavior, and atomic subtasks describe concrete
actions. A mode can change within a child or continue across child boundaries;
do not force either set of boundaries to match the other. Keep the vocabulary
small until the initial workflow has been evaluated, including ambiguous cases
such as simultaneous walking and object interaction.

For example, “Retrieve mug” spans `[10, 30)` seconds, with `locomotion` during
`[10, 18)` and `manipulation` during `[18, 30)`. Its fine subtasks can still be
“walk toward cabinet,” “open cabinet,” “reach toward mug” and “grasp mug.” The
mode track complements those labels; it does not add a hierarchy level or replace
fine annotation.

## Proposed coarse-to-fine flow

1. **Coarse segmentation:** sample timestamped RGB from the source video and ask
   one coarse stage jointly for top-level tasks, child tasks, their timestamps
   and activity-mode segments. Start by evaluating 0.5–1 FPS; this is a candidate
   setting, not a validated rate. The coarse stage identifies structure and modes
   rather than every semantic subtask.
2. **Child episodes:** create a derived LeRobot episode for each accepted child
   interval, retaining its parent IDs and source-frame mapping. Supply the child
   label as its known task instruction. Retain the overlapping activity segments
   separately; create episodes by child task, not by mode. Preserve original video
   and annotations.
3. **Fine annotation:** annotate each child independently with `lerobot-annotate`.
   Child membership then follows from the episode association without another
   VLM grouping pass. Review coarse labels first: an incorrect instruction can
   bias the finer labels.
4. **Merge:** read saved subtask boundaries, map them to the source timeline and
   attach them to the recorded parents. Preserve the independent source-time mode
   track alongside the reconstructed hierarchy without another model call.

One coarse **stage** does not imply one request for an arbitrarily long video.
A future implementation must budget sampled frames and context length; if it
windows the source, it must reconcile continuing tasks and activity modes across
window edges and remove duplicate boundaries in each track. Sparse sampling can
miss short transitions. Sample density and boundary review need evaluation before
calling this approach compute-saving.

Annotate selected task windows at fine resolution, but account for omitted source
intervals explicitly. Do not discard navigation as “irrelevant” simply because
there is no manipulation. Keep auxiliary modules disabled as in the existing
wrapper; memory generation is not free and is not part of this proposal's first
version. Measure total calls, sampled frames/tokens where available, runtime and
review effort, since splitting into children can also increase overhead.

## Structured coarse output and interval rules

Request structured JSON with source identity, task/child IDs, labels, source
times in seconds, and a separate `activity_segments` array of `mode`, `start` and
`end`. Prefer schema-constrained output when the selected backend
supports it; support is not established by this reference. Otherwise parse strict
JSON and validate it, using bounded retries with actionable errors. Retain the raw
response for review; do not silently repair semantic boundaries or invent labels.

Illustrative excerpt, with other children and source intervals omitted; this is
not a complete coverage example or an implemented storage schema:

```json
{
  "source_video_id": "video_004",
  "tasks": [
    {
      "task_id": 0,
      "label": "Make coffee",
      "start": 0.0,
      "end": 120.0,
      "children": [
        {"child_id": 0, "label": "Retrieve mug", "start": 10.0, "end": 30.0}
      ]
    }
  ],
  "activity_segments": [
    {"mode": "locomotion", "start": 10.0, "end": 18.0},
    {"mode": "manipulation", "start": 18.0, "end": 30.0}
  ]
}
```

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

Validate activity intervals separately for allowed mode values, ordered positive
durations and source bounds. Within an annotated interval, represent one mode at
a time and account for gaps explicitly; `other` describes reviewed activity,
not proof that an omitted interval was inspected. Activity segments need not be
contained by an individual child. Both structures share source identity and time
units; intersect modes with child windows for derived views while preserving the
original source-time track.

Contiguity guarantees coverage, not correct meaning. Represent waiting,
transitions and uncertain intervals explicitly when observed; do not stretch a
manipulation label merely to fill a gap. Concurrent activities may require a later
representation choice; a sequential partition cannot express overlapping children.
This does not expand the initial three-value activity vocabulary.
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

## Later fixed-base filtering

For fixed-base robotization, use the `manipulation` portions of a child as semantic
anchors for geometric feasibility testing. A VLM mode label does not establish
reachability. Keep the source hierarchy and mode track intact when deriving robot
episodes; final robot boundaries need not coincide with mode boundaries.

The proposed sequence for a manipulation-centered child is:

1. Identify its manipulation portion as the candidate semantic/geometric core.
2. Verify that one fixed robot-base placement can execute the core under the
   applicable robot constraints.
3. Optionally expand backward or forward while that same placement remains
   feasible, retaining the accepted core and reviewing task coverage.
4. Keep the original semantic child/manipulation-task instruction for the derived
   episode, regardless of the human mode at its first frame.

The update's illustrative intervals are:

```text
Human child:        [10.0, 30.0)  Retrieve mug
Human locomotion:   [10.0, 18.0)
Human manipulation: [18.0, 30.0)
Robot-feasible:     [16.5, 27.0)  Instruction: "Retrieve the mug"
```

If geometry supports it, `[16.5, 18.0)` can serve as setup context for the fixed-base
robot despite its human `locomotion` label. These numbers illustrate independent
boundaries, not measured feasibility or expansion of the entire `[18, 30)` core.
Because the example ends early, task coverage and the retained core still need
review; an instruction naming the goal does not prove completion. Do not silently
trim task-essential motion to obtain a feasible episode. This filtering remains
future retargeting work under its own approved scope.

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
- There is no coarse segmenter, activity-mode track, automatic child extraction,
  parent/child storage, padding adapter or hierarchical merger in the current
  workflow. Existing dataset creation requires completed HaWoR exports; it is not a standalone RGB-only
  child-episode builder. A later plan must choose where annotation and geometry
  extraction meet while preserving their validity independently.
- Semantic alignment does not align geometry: separately processed clips have
  independent world origins and canonical anchors. Reusing a continuous source
  reconstruction versus processing children separately is a later design choice,
  especially for mobile-base motion. Source timestamps alone do not establish
  metric navigation or a shared world frame.

Retain source identity, task/child/subtask IDs, parent relationships, labels,
source intervals and the derived dataset/episode association. Retain activity
modes and their source intervals as an independent track in the data model and
downstream fixed-base filtering. Record model/run provenance and review status
using existing mechanisms where possible. Choose a
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
- Correct activity labels using exactly the three initial modes; independent task
  and mode boundaries, including children spanning modes and modes spanning children.
- Boundary error against reviewed source frames, including variable frame timing,
  adjacent children, final endpoints, context-window seams and optional padding.
- Saved/reloaded hierarchy and frame alignment; preservation of existing labels,
  the independent activity track, RGB, trajectories and validity metadata after
  annotation.
- In a later fixed-base evaluation, execution of the retained core and expanded
  context from one base placement, sufficient task coverage, and an instruction
  derived from the semantic task even when the first human mode is locomotion.
- Total compute and human correction effort, including retries and rejected coarse
  segments, rather than only successful fine-annotation calls.

Begin with coarse structure and activity modes, derived children, fine annotation
and deterministic merge. Defer adaptive sampling, elaborate ontologies, extra VLM verification
passes, hierarchical memory and policy-generated memory until an evaluation shows
a concrete need. Preserving hierarchy may support later alignment with camera,
hand, object and robot trajectories; it does not establish their accuracy or
authorize retargeting work.
