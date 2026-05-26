# Harvest Practices Workflow

Use this workflow when the user asks to extract, harvest, persist, process, summarize, deduplicate, merge, or publish reusable lessons from a work session.

## Invariant

Do not publish raw session notes directly into agent adapters. Canonical practices must be updated first. Each new or materially changed practice requires human approval before becoming `active`; after approval, publish relevant adapters automatically.

## 1. Reconstruct the Session

Summarize:

- what was built, changed, debugged, or designed;
- key decisions and tradeoffs;
- false starts or design revisions;
- problems that appeared;
- practices that may apply beyond the current project.

Keep this summary local to the harvest report unless the user asks to store it.

If using memories, rollout summaries, or activity logs, treat them as evidence only. Apply META-006: durable rules belong in canonical practice entries, not memory alone.

If the agent has native self-growth capabilities, apply META-007: do not suppress native learning. Treat native memories or generated skills as candidate inputs when they should become durable or cross-agent.

## 2. Extract Candidate Lessons

Extract candidates only if they are:

- reusable across projects;
- actionable by an agent;
- more specific than generic advice;
- supported by evidence from the session;
- likely to change future agent behavior.

Reject candidates that are:

- project-specific facts;
- one-off preferences;
- obvious generic advice;
- too vague to guide action;
- already fully covered by an existing practice.

## 3. Classify Each Candidate

Use one type:

- `principle`
- `pattern`
- `heuristic`
- `playbook`
- `checklist`
- `example`
- `anti-pattern`

Use one domain:

- `architecture`
- `implementation`
- `testing`
- `debugging`
- `product`
- `agent-collaboration`
- `meta`

## 4. Search Before Creating

Before creating a new entry:

1. Read `indexes/practice_index.yaml`.
2. Search by keywords, aliases, tags, and related domains.
3. Inspect the closest matching practice files.
4. Decide whether the candidate is genuinely new or should merge into an existing entry.

## 5. Decide

For each candidate choose exactly one decision:

- `discard`: not reusable, not actionable, or already obvious.
- `merge`: strengthens an existing practice.
- `create`: genuinely new practice.
- `supersede`: replaces an older practice.
- `defer`: promising but under-evidenced or needs human clarification.

Prefer `merge` over `create` when the distinction is weak.

## 6. Update Canonical Practices

For `merge`:

- update the existing practice;
- increment `version` if meaningfully changed;
- update `updated`;
- add example or guidance rather than duplicating.

For `create`:

- assign the next stable ID for the domain;
- create the file under `practices/<domain>/`;
- set `status: proposed` unless the user explicitly approves `active`;
- set `review_required: true`;
- add the entry to `indexes/practice_index.yaml`.

For `supersede`:

- update the old entry with `status: superseded`;
- set `superseded_by`;
- add the new entry with `supersedes`.

For `defer`:

- report the candidate and reason;
- do not create a canonical entry unless the user asks for a candidate file.

## 7. Human Review Gate

Ask for approval before:

- promoting `candidate` or `proposed` to `active`;
- importing external skill content;
- executing or adapting external scripts.

Present a concise review list. For each new or changed practice, show:

- title;
- action: merge, create, supersede, or defer;
- reason;
- canonical files affected;
- adapters that will be updated after approval.

Approval is per practice. When the user approves an item, apply that item's full chain:

```text
merge/create/supersede
  -> promote approved practice to active when applicable
  -> update index
  -> publish relevant adapters
  -> report changed files
```

## 8. Update Adapters

After an item is approved and canonical updates are applied:

1. Read `workflows/publish-adapters.md`.
2. Update the relevant adapter references.
3. Keep adapters compact.
4. Do not duplicate long-form rationale into adapters.

## 9. Final Report Format

Report:

```text
Candidates reviewed:
1. <candidate title>
   Decision: discard | merge | create | supersede | defer
   Reason: <brief reason>
   Canonical change: <file or none>
   Adapter change: <file or none>

Files changed:
- <path>

Needs human review:
- <entry id/title or none>
```
