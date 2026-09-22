# Knowledge and action-log maintenance

The wiki holds durable project knowledge. [AGENTS.md](../../AGENTS.md) owns general
project rules; [planning-specs.md](planning-specs.md) owns plan format and approval.

## Page ownership

| Location | Owns |
| --- | --- |
| `knowledge/raw/` | Original notes and source material; preserve unless the user requests a change |
| `index.md` | Navigation to maintained pages, historical plans, and available log months |
| `status.md` | Current milestone/stage, active plan, outcome, blockers, next action, and verification |
| `plans/` | Approved scope and acceptance, with drafts clearly labeled |
| `topics/` | Current reusable architecture, contracts, workflows, and limitations |
| `decisions/` | Significant choices, their rationale, consequences, and approval when needed |
| `experiments/` | Substantial evaluation methods, results, acceptance evidence, and limitations |
| `logs/YYYY-MM.jsonl` | Append-only record of meaningful actions and their evidence |

Create a directory only for a necessary page. Give each subject one owner and link
to it; do not copy explanations into status or plans. Use relative Markdown links
and descriptive filenames. Index every maintained page and log month. Ordinary
correctness tests do not need experiment pages, and routine coding choices do not
need decision pages. Raw research claims do not establish implemented behavior.

Update affected pages alongside material behavior, contract, or knowledge changes.
Check claims against code, tests, configurations, and evidence; distinguish static
inspection from execution. Identify the date/revision supporting a claim. Preserve
original acceptance boundaries and explain when later evidence supersedes them.

Include wiki and action-log changes in the task's local commits under the
[Git staging and commits policy](../../AGENTS.md#git-staging-and-commits).
Existing local reports
and figures under `knowledge/agent/summaries/` remain in place and ignored; reference
them as local-only evidence. Do not copy their contents or assets into tracked pages
without authorization. Likewise, inputs, model assets, and generated run evidence
remain untracked. A link to a local artifact does not make it available in a fresh
clone; record whether evidence is local, unavailable, or recoverable from Git.

## Action-log format (version 1)

Use UTF-8 JSON Lines: one complete JSON object per line, with a final newline and
no comments or blank lines. The file month is the UTC month of `recorded_at`, so
late historical imports and corrections do not require modifying older files.

| Required field | Meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `id` | Unique stable event string, e.g. a session identifier plus a sequence number |
| `session_id` | Stable string grouping this work session; `null` if an imported action's session is unknown |
| `occurred_at` | Actual UTC timestamp, historical date `YYYY-MM-DD`, or `null` if unknown |
| `recorded_at` | Actual UTC timestamp when this event is appended |
| `time_precision` | `second`, `date`, or `unknown`, matching `occurred_at` |
| `milestone` | Roadmap milestone integer or `null` for repository-wide work |
| `phase` | Plan subphase or maintenance-task name; `null` if unknown |
| `kind` | `implementation`, `validation`, `experiment`, `decision`, `documentation`, or `blocker` |
| `summary` | Concrete action and result/limitation in readable text |
| `result` | `started`, `succeeded`, `failed`, `interrupted`, or `unverified` |
| `evidence` | Array of objects with `type` and `ref`; use `path`, `git`, `command`, `run`, `url`, or `conversation` |

Timestamp form is `YYYY-MM-DDTHH:MM:SSZ`; read the clock instead of guessing the
time. Date-only historical entries retain the source's calendar date without
claiming a UTC time. Never manufacture midnight timestamps, sessions, or durations.
Historical imports also set `historical: true`; their result is the source's
reported outcome, not a claim that it was reverified during migration.

Optional fields: `related_event_id` links a finish, follow-up, or correction to an
earlier event; `corrects_event_id` explicitly identifies a corrected claim;
`started_at`/`ended_at` record known UTC execution bounds. Omit unknown optional
values. A correction can use `kind: documentation` and must explain the correction
with evidence. Keep both original and correcting records discoverable.

Evidence paths are repository-relative; Git references use a commit, optionally
followed by `:path`. Commands record what was actually executed, with relevant
context and output references. Mark local/unavailable evidence in an optional
`availability` field. Conversation references identify the dated instruction
without inventing message identifiers. Redact credentials and sensitive command
arguments; link to existing manifests and console logs instead of copying them.

## When to write and read

Append after meaningful changes, validation, experiments, decisions, or blockers.
Record failures and interruptions as well as successes. For long-running work,
append a start before execution and a linked outcome afterward. An unmatched start
means no finish was recorded; reconcile available evidence before claiming success,
failure, or interruption. Never equate output-file presence with completion.

Do not record every read or command. Group related edits into one meaningful action,
but log a new result or consequential decision when it occurs, not only at handoff.
Append records without rewriting, sorting, deleting, or compacting existing lines.
Avoid concurrent writes to the same log. Correct mistakes with linked new events.
Summaries may be regenerated from events; they do not replace the original history.

Include change and validation events before staging the logical commit. Git history
is the authoritative record of that commit's hash, author, time, and contents;
report the verified hash at handoff. A commit cannot contain its own final hash.
Do not claim commit success before it occurs or create an endless series of
log-only commits to record the preceding commit. Later events may reference the
known hash when useful. If committing fails, append a failure/blocker event and
retry after addressing its cause, or report the uncommitted work explicitly.

For current-state questions, start with status and follow the index only as needed.
For historical questions, parse relevant JSONL files and filter by occurrence date,
milestone, phase, kind, result, or session. Account for later imports/corrections in
other months; a file's month is its recording month. State unknown-time coverage
explicitly. Cite event IDs and supporting evidence in answers. Do not load all
history into every session or mistake an old test result for validation of current code.

## Verification and migration

Before handoff, parse new log lines, check required fields, unique IDs, timestamps,
and event references; verify links and index coverage; check whitespace and Git
visibility. Confirm claims match the stated evidence and preserved files remain
unchanged. Use existing tools or one-off checks; no logging package or dedicated
test wrapper is required.

The 2026-09-22 migration retains the Milestone 1 plan byte-for-byte and imports the
old status's completed-work bullets into the action log with historical provenance.
Unknown action dates remain unknown; this is not a complete reconstruction of past
commands. The [baseline acceptance page](experiments/milestone-1-baseline.md) owns
the prior acceptance and failure evidence. The original status and planning rules
remain recoverable at Git revision `908ea97bfd2b75f762b747aefc395eed383c1b18` under
their former `knowledge/agent/` paths.
