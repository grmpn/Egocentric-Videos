# Planning and knowledge ownership

Approved by the user on 2026-09-22 in the conversation requesting this refactor.
Exact approval time is unavailable. Event: `20260922-knowledge-refactor-approval`.

The previous process required complete schemas, per-file specifications, and call
trees before implementation; Milestone 1's plan reached 1,032 lines. Status also
accumulated project history, making current work harder to find.

Use short scope-and-acceptance plans and let the agent choose implementation details
within approved constraints. Keep current state, durable explanations, significant
rationale, and dated actions in separate authoritative locations. The
[planning specification](../planning-specs.md) and
[maintenance convention](../knowledge-maintenance.md) define the rules.

The reference [knowledge conventions](https://github.com/PatrizioAcquadro/isaac-audio-sensors/blob/b568dd23cc09dcf9c322c91885ed599b125f33d8/knowledge/AGENTS.md)
informed canonical page ownership. Extend its dated wiki-maintenance log into a
timestamped JSONL action history covering implementation, validation, experiments,
decisions, documentation, and blockers. No new software dependency is needed.

Preserve the completed Milestone 1 approval record unchanged, including its old
paths. Import supported historical statements without inventing missing times.
Keep original notes, licensed inputs, run artifacts, and ignored local reports in
place. Existing local-report links may be corrected without publishing the reports.
This refactor authorizes documentation and workflow changes only; it does not
reopen Milestone 1 implementation or begin Milestone 2.
