# Milestone planning

Plans define the work the user authorizes and the evidence needed to finish it.
They live in `knowledge/wiki/plans/` and should take only a few minutes to read:
target 300–500 words, with shorter plans welcome when the scope is clear.

## Conversation and approval

1. Read the [roadmap](../raw/Project-Milestones-and-Timeline.md), [status](status.md),
   any active plan, and relevant knowledge. Propose the full milestone or current
   implementation scope, including boundaries and acceptance evidence.
2. Resolve questions that affect the desired outcome. Optional subphases describe
   useful intermediate outcomes. The agent chooses routine implementation details.
3. Present the short plan for explicit approval. Drafting a plan is not approval.
   Record the approved revision, approval date, and decision event; update status
   to `Ready for implementation` only when the user has authorized it.
4. Implement and validate within the approved scope. Update status, relevant wiki
   pages, and the action log as work progresses; keep the plan focused on intent.

Planning does not depend on a particular tool mode. Ask only questions whose
answers affect scope, essential constraints, acceptance, or unresolved user choices.
Do not ask the user to specify the file structure or internal architecture.

## Plan format

Start with a title and a short metadata line: draft/approved, revision, approval
date when known, and a reference to the approval event. Use these sections:

- **Objective and deliverable:** what will exist and why it serves the roadmap.
- **Scope and boundaries:** supported behavior, inputs and outputs at a conceptual
  level, essential constraints, and excluded work. Keep scientific requirements
  such as units, coordinate preservation, synchronization, and identity explicit
  when they determine correctness. Include any agreed resource limits.
- **Subphases (optional):** a few ordered outcomes, each with a completion condition.
  Keep them in this plan; avoid separate plans for routine implementation steps.
- **Acceptance:** observable completion criteria and the evidence that proves them.
  Cover representative execution, relevant correctness checks, and visual review
  where applicable. State material limitations on what passing establishes.
- **Open decisions (only when needed):** unresolved user choices, their impact, and
  whether they block approval or only a later phase. Remove resolved choices here
  after incorporating them into scope; preserve their rationale in a decision page
  or event when significant.

Do not require setup inventories, repository trees, per-file descriptions,
function breakdowns, call trees, exhaustive schemas, or a second detailed plan.
The agent documents actual contracts and significant choices alongside the work
in [topics and decisions](index.md). A short working checklist is optional and
does not become another approval document.

## Changes and completion

Approval covers implementation choices that satisfy the agreed scope, constraints,
and acceptance. Reorganizing modules or selecting a justified dependency within
those limits does not require a plan revision.

Revise the plan and obtain approval before changing the deliverable, expanding
scope, weakening acceptance, breaking agreed compatibility, or exceeding an
agreed resource constraint. Record the approved revision and reason in the log.
Continue independent authorized work while a scope decision is pending.

Declare completion only against the acceptance evidence. Record results in status
and the appropriate wiki/evidence page; do not rewrite the plan as an implementation
history. Preserve completed plans as approval records. The relocated
[Milestone 1 plan](plans/milestone-1-hawor-baseline.md) is unchanged historical
evidence with old paths and resolved questions; it is not the template for new work.
