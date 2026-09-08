# Milestone Planning Specification

This document defines how milestone implementation plans are developed and
written. It standardizes the planning artifact; it does not prescribe the
architecture of any milestone.

Milestone plans live under `plans/`. Existing plans are not silently reformatted
or treated as approved merely because this specification changes.

## Planning conversation

Develop a milestone plan in the following stages.

### Stage 1 — establish scope

1. Read `Project-Milestones-and-Timeline.md`, `PROJECT_STATUS.md`, the current
   plan if one exists, and relevant material in `Sources/`.
2. Draft **Goals** and **Explicit Non-Goals** from the milestone roadmap and the
   current project state.
3. Present those drafts to the user as editable proposals. The roadmap is the
   starting point, not a substitute for user review.

### Stage 2 — elicit the architecture

Ask the user for their desired specifications for these sections before
finalizing them:

- **4. Input and Output Contracts / Data and Metadata Files**
- **5. Planned Repo Structure**
- **6. File Breakdown**
- **7. End-to-End File/Script Flow**

Help the user turn those specifications into a complete, internally consistent
architecture. Identify ambiguities, missing boundaries, mismatched producers and
consumers, and conflicts with the roadmap or repository rules. Ask focused
follow-up questions when the answer would materially change the architecture.
Do not fill architectural gaps with unmarked assumptions, and do not present an
inferred architecture as a decision the user has made.

The plan may already contain all 13 headings during this stage. Sections that
have not been developed must be labeled clearly as pending rather than filled
with speculative detail.

### Stage 3 — complete the plan when directed

After Sections 4–7 have been refined, wait until the user directs the agent to
continue. Then draft or revise:

- **3. Setup Requirements**
- **8. Metrics and Failure Review**
- **9. Implementation Sequence**
- **10. Acceptance Criteria**
- **11. Risks and Mitigations**
- **12. Remaining Decisions**
- **13. References**

Derive these sections from the agreed architecture, repository evidence, and
relevant sources. Check the completed plan for consistency across all sections.
The user may modify any section, including Goals and Explicit Non-Goals, at any
point.

### Stage 4 — approval and implementation

Keep the plan in draft status until the user explicitly approves it. Writing or
revising a plan is not approval to implement it. Implementation begins only when
all gates in `AGENTS.md` are satisfied. Approval of an earlier plan does not
automatically approve a materially revised architecture.

## Required plan sections

Use these top-level sections in this exact order. A milestone may add subsections
inside them, but must not reorder or rename the top-level sections.

### 1. Goals

State the concrete milestone outcomes and the evidence the milestone is intended
to produce. Begin from the corresponding roadmap milestone, then incorporate
user revisions. Keep goals outcome-oriented; implementation details belong in
later sections.

### 2. Explicit Non-Goals

State nearby work that is intentionally excluded. Include tempting extensions,
later-milestone work, research changes, unsupported environments, and outputs
that must not be produced when those boundaries are relevant.

### 3. Setup Requirements

Document what is newly required for this milestone. Cross-reference setup that
was already established and remains unchanged instead of repeating it.

At minimum, state:

- supported operating system and relevant shell/runtime assumptions;
- required Python version;
- required Python libraries, with version constraints or the source of the
  resolved versions; and
- how the setup is verified before milestone implementation or execution.

When relevant, also document hardware, accelerators, system packages, external
repositories and pinned revisions, model weights or licensed assets, credentials
and secrets handling, environment variables, storage, build tools, services, and
fallback environments. Distinguish requirements from recommendations and note
which setup items block later work.

### 4. Input and Output Contracts / Data and Metadata Files

Define every persistent or cross-component artifact used or produced by the
milestone, including all JSON, NPZ, video, image, report, log, checkpoint, and
other data files. Group artifacts by pipeline boundary when useful.

For each artifact, specify:

- canonical name or path pattern;
- whether it is human-authored, imported, generated, or derived;
- producer and consumer(s);
- purpose and source of truth;
- complete content/schema;
- required versus optional values and defaults;
- validation rules and failure behavior;
- versioning, overwrite, and immutability rules;
- provenance, hashes, or upstream references when applicable; and
- whether it is tracked, ignored, licensed, sensitive, or generated.

For JSON, enumerate every key, its type, meaning, required/optional status, and
allowed values or units. For NPZ and similar array containers, enumerate every
array, dtype, shape, axis order, units, coordinate frame, and invalid/missing
value convention. For time-based data, define timestamp origin, units, frame
index relationship, rate assumptions, and alignment rules. For hand and robot
data, define left/right ordering, validity, confidence, provenance, and transform
direction wherever applicable.

### 5. Planned Repo Structure

Show one code-fenced repository tree containing every existing or proposed path
needed for the milestone, plus generated/untracked paths when they clarify the
architecture. Do not add empty or speculative directories.

Annotate paths sufficiently to distinguish:

- existing, new, and modified files when that distinction matters;
- reusable code from milestone-specific entry points or data;
- external or vendored code from project-owned code; and
- tracked source/configuration from ignored inputs and generated outputs.

The tree must agree with the artifact paths in Section 4 and the files in
Section 6.

### 6. File Breakdown

Document files in this order:

1. environments and external code;
2. configuration;
3. `src/` modules;
4. `scripts/` entry points; and
5. tests.

Within each group, follow dependency order where practical. Every proposed
script or executable module must use this exact field structure:

```markdown
#### `path/to/file.py`

**Description:** What the file owns, and what it deliberately does not own.

**Input:** Files, arguments, configuration, environment state, or in-memory
objects it reads. Use `None` when applicable.

**Output:** Files, return values, state changes, logs, or user-visible results it
produces. Use `None` when applicable.

**Calls:** Project modules, scripts, external programs, or services it invokes.
Use `None` when it calls nothing.

**Called by:** Scripts, modules, tests, or users that invoke it. Use `None` for a
top-level entry point with no programmatic caller.

**Metadata written:** Name every metadata file it writes or updates and list the
fields or field groups for which this file is responsible. Identify shared
helpers such as `run_metadata.py`. Use `None` when it writes no metadata.
```

Use the same fields for non-Python executables. For declarative configuration,
environment files, and external-code entries, retain the headings and use
`N/A — declarative file` where call relationships do not apply. Do not hide
important work behind vague phrases such as “handles metadata”; identify the
artifact and ownership boundary.

Every call relationship must be reciprocal: if file A lists file B under
**Calls**, file B must list file A under **Called by**. Every file output consumed
elsewhere must appear as an input to its consumer. Identify reusable versus
milestone-specific responsibilities without creating duplicate implementations.

### 7. End-to-End File/Script Flow

The primary representation must be a nested, code-fenced call tree that makes
script and module ownership visible. A flat sequence or an unlabeled box-and-arrow
diagram is not sufficient.

Use indentation and tree branches to show actual calls. Put important inputs and
outputs directly beneath the component that reads or writes them. Label optional
branches, gates, loops, external-engine calls, and human review steps. Distinguish
control flow (“calls”) from data flow (“reads” or “writes”).

Use this notation as a structural example only; these names are not a mandated
or approved architecture:

```text
scripts/run_milestone1.py
├── reads: configs/clips/<clip>.json
├── src/pipeline.py
│   ├── src/clip_config.py
│   │   └── returns: validated clip configuration
│   ├── src/video_preparation.py
│   │   ├── reads: source video
│   │   └── writes: rgb.mp4, clip_metadata.json
│   ├── src/hawor_runner.py
│   │   ├── calls: external/HaWoR/
│   │   └── writes: native model artifacts and execution records
│   ├── src/world_export.py
│   │   ├── reads: native world result and clip metadata
│   │   └── writes: trajectory_world.npz, trajectory_metadata.json
│   └── src/visualization.py [optional]
│       └── writes: review visualization
└── src/benchmark.py
    ├── reads: accepted run manifests and review labels
    └── writes: benchmark data and report

Cross-cutting metadata calls:
└── src/run_metadata.py
    ├── called by: video preparation, runner, export, pipeline, benchmark
    └── writes/updates: the explicitly assigned metadata field groups
```

Supplement the tree with a compact artifact-flow table only when it makes input,
output, or handoff contracts materially clearer. The nested call tree remains
mandatory and primary. Every callable file in Section 6 must appear in this flow,
and every flow node must be defined in Section 6.

### 8. Metrics and Failure Review

Define what is measured, why it matters, the formula and units, where it is
captured, how it is aggregated, and any pass/fail threshold. Separate automatic
metrics from manual review. Define the review sample, required visualizations,
failure taxonomy, severity or disposition, reviewer-recorded fields, and where
failure evidence is stored. State what remains descriptive because the sample is
too small for a statistical claim.

### 9. Implementation Sequence

Give an ordered, dependency-aware sequence with explicit gates. Introduce each
file, schema, dependency, and persistent path only when it is needed. Pair
contract implementation with focused tests, identify points requiring visual or
user review, and state when `PROJECT_STATUS.md` is updated. Do not begin work
outside the milestone.

### 10. Acceptance Criteria

Write objective, verifiable completion criteria traceable to the goals, contracts,
metrics, and failure review. Each criterion must name the evidence that proves it
passed. Cover environment reproducibility, schema and data invariants, execution,
tests, representative visual inspection, preservation of source data, and
explicit non-goals when relevant. Do not equate the presence of output files with
successful completion.

### 11. Risks and Mitigations

For each material risk, state its cause or trigger, likely impact, mitigation,
detection evidence, and fallback or stop condition. Include technical,
data/licensing, resource, schedule, scientific-validity, and safety risks when
applicable. Do not disguise an unresolved architecture choice as a mitigation.

### 12. Remaining Decisions

List only unresolved choices. For each, state the available options, why the
choice matters, the current evidence or recommended default if one exists, and
whether it blocks plan approval or only later implementation. Remove resolved
items by incorporating the decision into the authoritative section instead of
keeping a duplicate decision log.

### 13. References

List the roadmap, status document, relevant source notes, upstream primary
documentation, papers, repositories, dataset documentation, and exact version or
commit references used to justify the plan. Prefer primary sources. Make clear
which architectural claims or constraints each reference supports, and record an
access or verification date for sources that may change.

## Final consistency review

Before requesting plan approval, verify that:

- all 13 sections are present and no pending placeholders remain;
- goals and non-goals match the roadmap or clearly record an approved change;
- every artifact in Section 4 has a producer, consumer, schema, and path that
  agrees with Sections 5–7;
- every executable file in Section 6 uses the required fields and has reciprocal
  call relationships;
- Section 7 is primarily a nested call tree and matches Section 6;
- setup requirements support the proposed implementation without repeating
  unchanged prior-milestone setup;
- metrics feed the acceptance criteria;
- risks and decisions are not contradictory or duplicated; and
- the plan status still says draft until the user explicitly approves it.
