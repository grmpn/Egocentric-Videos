# Project Instructions

## Project purpose

This project builds a reusable pipeline for turning egocentric RGB video into hand trajectories, language annotations, and robot-compatible trajectories.

Work should contribute directly to the current milestone while preserving a clear path for reuse in later milestones.

The project must remain understandable to a human reader. Prefer a small, explicit implementation over a larger or more abstract one.

## Sources of truth

Before beginning work, read:

1. `knowledge/raw/Project-Milestones-and-Timeline.md` for the project roadmap.
2. `knowledge/wiki/status.md` for the active milestone and current progress.
3. The active milestone plan linked from that status, when one is active.
4. `knowledge/wiki/index.md`, then only the topics, decisions, evidence, and raw
   sources relevant to the task.

When creating, restructuring, or materially revising a milestone plan, also read
`knowledge/wiki/planning-specs.md` before editing the plan. For wiki or action-log
work, read `knowledge/wiki/knowledge-maintenance.md`.

These files have distinct responsibilities:

- The milestone document defines long-term scope and deliverables.
- The status document records current state.
- The active plan defines approved scope, constraints, and acceptance evidence.
- The planning specification defines the short plan and approval conversation.
- Wiki topics explain implemented behavior; decisions preserve significant rationale.
- The append-only action log records dated actions and evidence, including failures.
- Source notes provide technical context but do not override an approved plan.

Code and tests establish executable behavior; plans establish authorized scope.
Label historical results, source claims, inference, and unverified claims clearly.
Link to one authoritative explanation instead of duplicating it. Preserve raw
source material unless the user explicitly requests a change to it.

## Determining the current milestone

`knowledge/wiki/status.md` is the operational source of truth. Keep it about one
screen long, identifying:

- current milestone
- current stage
- active plan
- milestone deliverable
- a brief completed outcome with a link to acceptance evidence
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

Update `knowledge/wiki/status.md` after material progress, validation, a newly
discovered blocker, or a change to the next action. Move history to the action log
and durable explanations to the wiki; do not accumulate completed-work lists here.

## Planning gate before implementation

Do not create or modify implementation code for a milestone until:

1. The milestone scope has been discussed with the user.
2. A short written plan exists under `knowledge/wiki/plans/` and conforms to
   `knowledge/wiki/planning-specs.md`.
3. The user has explicitly approved the plan.
4. `knowledge/wiki/status.md` identifies that plan and shows `Ready for implementation` or `Implementing`.

Agree on the objective, scope, essential constraints, optional outcome-based
subphases, and acceptance evidence. Target 300–500 words; shorter is fine when
the scope is clear. Do not require repository trees, file breakdowns, call trees,
complete schemas, or a second detailed implementation plan.

Approval authorizes the agent to choose files, module organization, internal
interfaces, tests, and justified dependencies within that scope. Maintain actual
contracts and significant rationale in the wiki alongside implementation.
Routine implementation choices do not require another approval or a particular
tool mode. The user may revise the scope at any time.

Implementation includes source code, scripts, tests, configuration schemas, dependency changes, and persistent data-layout changes.

Documentation-only corrections, source-note updates, and status reporting do not require a new implementation plan.

If a choice changes the deliverable, expands scope, weakens acceptance, breaks
agreed compatibility, or exceeds an agreed resource constraint, stop the affected
work, revise the short plan, and obtain approval before proceeding with that
change. Continue independent work already authorized by the current scope.

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
- `knowledge/wiki/` — agent-maintained status, plans, topics, decisions, and action logs
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
- new dependencies without a concrete need within approved scope
- generated artifacts that have no validation or review purpose

Before adding a file, dependency, or abstraction, confirm that it is required for the current milestone deliverable and cannot be handled clearly by an existing component.

## Dependency and implementation discipline

Before implementing functionality, check whether an existing project dependency,
standard-library feature, or established external package already provides it. Use
that implementation when it satisfies the approved requirements; do not recreate
the same capability locally. Add a new dependency only when existing dependencies
cannot meet a concrete need within the approved scope. Record the reason and
reproducible version declaration; significant tradeoffs belong in a wiki decision.
An ordinary dependency choice does not require editing the milestone plan.

Implement the smallest correct, maintainable change that fully satisfies the
current requirement. Reuse existing patterns and interfaces; use or propose a
simpler approach when available. Avoid convenience wrappers, helper layers,
abstractions, and scripts that do not remove necessary complexity from the
supported workflow. Do not add production functionality solely to support tests.

Add metadata, hashes, fingerprints, manifests, freeze rules, or similar complexity
only to address a concrete failure mode or an explicit safety, interface, release,
transfer, publication, or reproducibility requirement.

## Legibility standards

Optimize for a human reader who needs to understand and modify the project later.
Keep solutions concise, simple, and clear, and workflows efficient and intuitive.

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

Add tests only when they meaningfully verify essential behavior. Keep validation
proportional to the project stage, risk, and current objective. Reserve exhaustive
integrity, provenance, and reproducibility gates for workflows that explicitly
require them. Do not repeat expensive checks without a concrete reason.

Use the smallest representative data needed for routine tests. Do not place large datasets or generated runs in the repository unless explicitly required.

Validation should cover the contracts most likely to cause silent errors, including:

- timestamps and frame alignment
- coordinate frames and transform direction
- physical units and scale
- left/right hand identity
- missing-frame and confidence metadata
- schema compatibility between pipeline stages
- robot workspace and kinematic limits when applicable

For physical or probabilistic systems, use justified tolerances, acceptance ranges,
or confidence measures that reflect real-world variability. Avoid unrealistic
requirements that reject a functioning system; preserve agreed acceptance criteria
and safety limits.

For visual outputs, inspect representative overlays or trajectory visualizations in addition to automated checks.

Write focused tests that exercise reusable modules and user-facing scripts or
entry points. Tests should evaluate the production workflow directly. Do not add
scripts whose only purpose is to invoke the test suite when the test framework's
standard command or configuration already does so.

Report exactly what was tested, what passed, and what remains unverified.

Whenever running a validation, tell the user where its outputs are saved so they
can inspect them manually. Include concrete paths or links to the relevant logs,
reports, videos, or visualizations in progress updates and the final handoff.

## Repository cleanup

At each milestone's completion, remind the user to start a focused repository
cleanup before beginning the next milestone, unless that cleanup is already done
or scheduled. Use milestone completion as the checkpoint rather than elapsed idle
time. Record completed cleanup and any deferred work in the existing action log.

When cleanup is within scope, keep the active repository focused on capabilities
that are currently used or intentionally maintained. Remove obsolete run-specific
configs, scripts, tests, tracked artifacts, and orchestration only after verifying
that no active consumer or protected evidence requires them. Preserve raw sources
and required acceptance evidence; rely on Git for ordinary source history.

## Git staging and commits

Authorization to perform a task includes staging its changes and creating local
commits. Commit completed, verified work automatically without asking for another
confirmation, unless the user explicitly requests otherwise. This applies to
documentation as well as implementation.

- Inspect the current branch, working tree, and index before changing or staging
  files. Identify existing user work and preserve it.
- Commit at meaningful checkpoints: a coherent change or completed subphase. Do
  not commit every edit or defer all commits until a large milestone is finished.
- Stage explicit paths or relevant hunks, including intended additions and
  deletions. Avoid unrestricted `git add .` or `git add -A`. Never include unrelated
  user changes or pre-existing staged work in the agent's commit. If changes
  overlap, isolate the task's hunks; if ownership cannot be established, leave the
  affected changes intact and explain the blocker.
- Run the checks appropriate to the change, inspect the complete staged diff,
  and run `git diff --cached --check` before committing. Confirm that the commit
  includes only intended work. Keep credentials, licensed assets, datasets,
  generated outputs, and ignored local reports out of commits; do not force-add
  them as part of routine staging.
- Include related tests, documentation, wiki/status updates, and action-log
  entries in the same logical commit. Use a descriptive commit message explaining
  the concrete result. Do not bypass failing checks or hooks to make a commit.
- After committing, verify the new commit and Git status. Leave no task-owned,
  intended-to-be-tracked changes uncommitted at handoff unless work is incomplete,
  validation is blocked, or the user requested otherwise. Report commit hashes,
  verification results, and any remaining changes with their reason.

Local commit authorization does not authorize pushing, merging, amending existing
commits, or rewriting history. Perform those operations only when specifically
authorized; earlier explicit authorization in the session still applies. Never
discard unrelated work to produce a clean working tree.

## Completion and handoff

During work, append meaningful implementation, validation, experiment, decision,
documentation, and blocker events to `knowledge/wiki/logs/YYYY-MM.jsonl` using
the format in `knowledge/wiki/knowledge-maintenance.md`. Record actual UTC times,
outcomes, and evidence. Log long-running starts and finishes separately. Do not
log routine reads or treat planned work as completed. Never rewrite old events;
append a linked correction. Update affected canonical wiki pages as behavior or
knowledge materially changes.

At the end of a work session:

1. Verify the relevant changes.
2. Update `knowledge/wiki/status.md` when progress materially changed.
3. Record the next concrete action, finish the action log, and update wiki navigation
   when pages were added, moved, or removed.
4. Stage, review, and commit completed work under the Git policy above; verify the
   commit and remaining working-tree state.
5. Summarize changed files, verification results, and commit hashes.
6. State any remaining changes, uncertainty, or decision needed from the user.

Do not broaden the milestone, begin the next milestone, or introduce an optional research change without explicit approval.

## Specialized nested instructions

Use this root file for all general project and code rules.

Add a nested `AGENTS.md` only when a directory develops genuinely different requirements that would be unsafe or confusing at the root. A future real-robot control directory may justify additional hardware-safety and execution rules.

Nested instructions must contain only the specialized differences. They must not repeat the root guidance.
