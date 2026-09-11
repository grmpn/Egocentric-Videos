# Project Instructions

## Project purpose

This project builds a reusable pipeline for turning egocentric RGB video into hand trajectories, language annotations, and robot-compatible trajectories.

Work should contribute directly to the current milestone while preserving a clear path for reuse in later milestones.

The project must remain understandable to a human reader. Prefer a small, explicit implementation over a larger or more abstract one.

## Sources of truth

Before beginning work, read:

1. `knowledge/raw/Project-Milestones-and-Timeline.md` for the project roadmap.
2. `knowledge/agent/PROJECT_STATUS.md` for the active milestone and current progress.
3. The active milestone plan linked from `knowledge/agent/PROJECT_STATUS.md`.
4. Relevant material in `knowledge/raw/Sources/`.

When creating, restructuring, or materially revising a milestone plan, also read
`knowledge/agent/PLANNING_SPECS.md` before editing the plan.

These files have distinct responsibilities:

- The milestone document defines long-term scope and deliverables.
- The status document records current state.
- The active plan defines the approved implementation.
- The planning specification defines the required plan structure and planning
  conversation; it does not define milestone architecture.
- Source notes provide technical context but do not override an approved plan.

Do not duplicate the same progress information across multiple documents.

## Determining the current milestone

`knowledge/agent/PROJECT_STATUS.md` is the operational source of truth. It must identify:

- current milestone
- current stage
- active plan
- milestone deliverable
- completed work
- current work
- blockers or unresolved decisions
- next concrete action
- last verified date and supporting evidence

Allowed stages are:

- `Not started`
- `Planning`
- `Ready for implementation`
- `Implementing`
- `Validating`
- `Complete`
- `Blocked`

Do not infer that a milestone is complete from the presence of code or output files. Mark it complete only when its defined deliverable has been produced and verified.

If the status document conflicts with the repository, investigate and report the discrepancy before changing implementation.

Update `knowledge/agent/PROJECT_STATUS.md` after material progress, validation, a newly discovered blocker, or a change to the next action. Keep updates factual and concise.

## Planning gate before implementation

Do not create or modify implementation code for a milestone until:

1. The milestone has been examined in Plan mode.
2. A written implementation plan exists under `knowledge/agent/plans/` and conforms to
   `knowledge/agent/PLANNING_SPECS.md`.
3. The user has explicitly approved the plan.
4. `knowledge/agent/PROJECT_STATUS.md` identifies that plan and shows `Ready for implementation` or `Implementing`.

Follow the staged planning conversation in `knowledge/agent/PLANNING_SPECS.md`. In particular,
start from roadmap-grounded goals and non-goals, then elicit and refine the
user's desired contracts, repository structure, file breakdown, and nested
end-to-end flow before filling in the remaining sections. Do not treat an
agent-inferred architecture as approved user intent.

Every milestone plan must use the 13 required top-level sections and the
per-file and nested-flow formats defined in `knowledge/agent/PLANNING_SPECS.md`. A plan may
temporarily contain clearly marked placeholders while the planning conversation
is in progress. The user may revise any section at any time.

Implementation includes source code, scripts, tests, configuration schemas, dependency changes, and persistent data-layout changes.

Documentation-only corrections, source-note updates, and status reporting do not require a new implementation plan.

If implementation would materially depart from the approved plan, stop coding and return to Plan mode. Update the plan and obtain approval before continuing.

Only the user can authorize the transition from `Planning` to `Ready for implementation`.

## Reuse across milestones

Organize code by capability, not by milestone number.

Prefer reusable areas such as:

- video and dataset ingestion
- hand tracking
- coordinate transforms
- annotations
- trajectory retargeting
- evaluation
- visualization

Milestone-specific commands should be thin entry points built on shared modules. Do not copy an earlier milestone's implementation into a new milestone directory.

Define stable boundaries between pipeline stages. Each stage should have clear inputs, outputs, units, coordinate frames, timestamps, validity information, and provenance.

Preserve original inputs. Derived data should be reproducible and should not silently overwrite source data.

Avoid premature abstraction. Create a shared interface only when it serves the current deliverable and has a concrete expected use in a later milestone.

## Minimal project structure

Use this structure as a destination, not as a request to create empty folders:

- `knowledge/raw/Sources/` — papers and research notes
- `knowledge/agent/plans/` — approved milestone plans
- `src/` — reusable implementation
- `scripts/` — thin user-facing entry points
- `configs/` — necessary reproducible settings
- `tests/` — focused automated checks
- `data/` — local inputs and intermediate datasets
- `outputs/` — generated reports, visualizations, and run artifacts

Create a directory only when it receives a necessary file.

Do not create:

- empty placeholder directories
- speculative utility modules
- duplicate documentation
- milestone-numbered copies of reusable code
- new dependencies without justification in the approved plan
- generated artifacts that have no validation or review purpose

Before adding a file, dependency, or abstraction, confirm that it is required for the current milestone deliverable and cannot be handled clearly by an existing component.

## Dependency and implementation discipline

Before implementing functionality, check whether an existing project dependency,
standard-library feature, or established external package already provides it. Use
that implementation when it satisfies the approved requirements; do not recreate
the same capability locally. Add a new dependency only when the approved plan
justifies it and existing dependencies cannot meet the need.

Implement the smallest amount of project code needed for the current deliverable.
Avoid convenience wrappers, helper layers, abstractions, and scripts that do not
remove necessary complexity from the supported workflow.

## Legibility standards

Optimize for a human reader who needs to understand and modify the project later.

- Use descriptive names and straightforward control flow.
- Keep files and functions focused on one responsibility.
- Avoid unexplained abbreviations, metaprogramming, and unnecessary indirection.
- Document coordinate frames, units, tensor shapes, and validity conventions wherever they cross a module boundary.
- Use comments to explain reasoning and constraints, not to restate code.
- Move adjustable thresholds and paths into clearly named configuration.
- Prefer explicit errors with corrective guidance over silent fallbacks.
- Remove dead code and stale documentation when safely replacing them.
- Keep documentation brief and link to one authoritative location rather than repeating details.

## Validation

Every implementation plan must define how its deliverable will be verified.

Use the smallest representative data needed for routine tests. Do not place large datasets or generated runs in the repository unless explicitly required.

Validation should cover the contracts most likely to cause silent errors, including:

- timestamps and frame alignment
- coordinate frames and transform direction
- physical units and scale
- left/right hand identity
- missing-frame and confidence metadata
- schema compatibility between pipeline stages
- robot workspace and kinematic limits when applicable

For visual outputs, inspect representative overlays or trajectory visualizations in addition to automated checks.

Write focused tests that exercise reusable modules and user-facing scripts or
entry points. Tests should evaluate the production workflow directly. Do not add
scripts whose only purpose is to invoke the test suite when the test framework's
standard command or configuration already does so.

Report exactly what was tested, what passed, and what remains unverified.

## Completion and handoff

At the end of a work session:

1. Verify the relevant changes.
2. Update `knowledge/agent/PROJECT_STATUS.md` when progress materially changed.
3. Record the next concrete action.
4. Summarize changed files and verification results.
5. State any remaining uncertainty or decision needed from the user.

Do not broaden the milestone, begin the next milestone, or introduce an optional research change without explicit approval.

## Specialized nested instructions

Use this root file for all general project and code rules.

Add a nested `AGENTS.md` only when a directory develops genuinely different requirements that would be unsafe or confusing at the root. A future real-robot control directory may justify additional hardware-safety and execution rules.

Nested instructions must contain only the specialized differences. They must not repeat the root guidance.
