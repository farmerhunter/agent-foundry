# Harvest Practices Workflow

Use this workflow when the user asks to extract, harvest, persist, process, summarize, deduplicate, merge, or publish reusable lessons from a work session.

## Invariant

Do not publish raw session notes directly into agent adapters. Canonical practices must be updated first. Each new or materially changed practice requires human approval before becoming `active`; after approval, publish relevant adapters automatically.

## 0. Locate Agent Foundry

The current project is usually the evidence source, not the canonical destination. Locate the Agent Foundry Vault before reading or writing canonical records.

Use this order:

1. `AGENT_FOUNDRY_HOME`, if set.
2. `~/.agent-foundry/config.yaml`, using `vault_root` and `core_root`.
3. The current directory, only if it contains canonical markers.
4. Known fallback paths.
5. Ask the user for the Agent Foundry path.

Validate the location before proceeding. Required markers:

- `indexes/practice_index.yaml`
- `indexes/asset_index.yaml`
- `workflows/harvest-practices.md`

If the Vault is locked, dirty in a conflicting way, or unavailable, produce candidate recommendations only and do not write files.

## 1. Current Capability Check

Before routing or drafting, distinguish current repository capability from proposed or future architecture.

Verify:

- the canonical Vault location is real and validated;
- destination directories, schemas, workflows, and indexes exist before treating them as writable substrates;
- candidate or proposed concepts are not used as current operating machinery;
- agent memory, session summaries, chat exports, and external skills remain evidence sources, not authorities.

Use this vocabulary when capability state matters:

- `current`: implemented and usable;
- `candidate`: proposed and awaiting review;
- `proposed`: designed but not implemented;
- `future`: intentionally deferred;
- `deprecated`: considered before but no longer recommended;
- `unknown`: not yet verified.

If a needed destination is only proposed or unknown, report that boundary and do not create future subsystem directories as part of harvest unless the user explicitly asks for that architecture work.

## 2. Reconstruct the Session

Summarize:

- what was built, changed, debugged, or designed;
- key decisions and tradeoffs;
- false starts or design revisions;
- problems that appeared;
- practices that may apply beyond the current project.

Keep this summary local to the harvest report unless the user asks to store it.

If using memories, rollout summaries, or activity logs, treat them as evidence only. Apply META-006: durable rules belong in canonical practice entries, not memory alone.

If the agent has native self-growth capabilities, apply META-007: do not suppress native learning. Treat native memories or generated skills as candidate inputs when they should become durable or cross-agent.

For complex handoffs, preserve knowledge state before action planning. Capture context and goals, research output, conceptual frameworks, decisions and rationale, rejected options, user corrections, current capability boundary, unresolved questions, and next actions.

## 3. Artifact Routing

Route each important session artifact before abstracting practices. Importance alone does not make something a practice.

Use these artifact classes:

- evidence only;
- design note;
- research/reference material;
- project-local decision;
- workflow update;
- practice candidate;
- skill/asset candidate;
- adapter update;
- discard.

Only items routed to `practice candidate` continue through practice drafting. Items routed to `workflow update` may update this or another workflow after review. Items routed to `skill/asset candidate` should use `workflows/discover-assets.md` or the asset workflow. Items routed to evidence, design, research, or project-local decision classes need an implemented canonical destination before writing.

When the user corrects the agent's method, first treat the correction as process evidence. Analyze whether it reveals an agent failure mode, workflow weakness, prompting gap, review checklist gap, handoff risk, harvest risk, or generalizable practice evidence before treating it as content inside the current domain.

## 4. Generalization Gate

Before drafting a practice candidate, ask:

- Would this help in unrelated future work?
- Would it help more than one agent or runtime?
- Does it describe a repeatable judgment or process?
- Can it be triggered operationally?
- Is it independent of the current domain's vocabulary?
- Is it more than a local design decision?
- Can it be reviewed and maintained as a durable rule?

Reject or reroute insights that do not pass the gate. Keep a rejected-as-practice list when useful so important material is not lost or silently promoted.

## 5. Extract Candidate Lessons

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

## 6. Classify Each Candidate

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
- `governance`
- `runtime`

## 7. Search Before Creating

Before creating a new entry:

1. Read `indexes/practice_index.yaml`.
2. Search by keywords, aliases, tags, and related domains.
3. Inspect the closest matching practice files.
4. Decide whether the candidate is genuinely new or should merge into an existing entry.

## 8. Decide

For each candidate choose exactly one decision:

- `discard`: not reusable, not actionable, or already obvious.
- `merge`: strengthens an existing practice.
- `create`: genuinely new practice.
- `supersede`: replaces an older practice.
- `defer`: promising but under-evidenced or needs human clarification.

Prefer `merge` over `create` when the distinction is weak.

## 9. Candidate Drafting and Canonical Updates

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

## 10. Rejected-As-Practice List

When important session content is rejected as a practice, preserve the reason in the harvest report or workflow update. Do not silently turn domain research or future architecture into Agent Foundry rules.

For the corrected memory-system harvest, the following were rejected as practices:

- memory-to-knowledge lifecycle;
- static research output preservation as Phase 1 priority;
- research memo / source digest / concept note taxonomy;
- project-embedded micro research handling;
- Work Context x Artifact Lane x Lifecycle Intent;
- Memory Triage Skill design;
- ChatGPT/Codex handoff strategy details;
- future knowledge/project-memory/research-memo subsystem.

Reason: these are memory-system-specific design or research outputs, or future architecture concepts. They are important, but they are not generalized Agent Foundry practices yet, and some depend on a memory subsystem that does not currently exist.

## 11. Review Grouping and Human Review Gate

Ask for approval before:

- promoting `candidate` or `proposed` to `active`;
- importing external skill content;
- executing or adapting external scripts.

### Approval Scope Guard

User approval applies only to the items, files, status changes, adapter updates, and runtime publish actions that were listed in the harvest review list or an equivalent PR/issue harvest report. Do not interpret broad phrases such as `continue`, `approved`, `do the whole chain`, or `finish it` as permission to skip artifact routing, the generalization gate, rejected-as-practice reporting, or adapter/runtime impact disclosure.

If the user approves a direction before the review list exists, treat that approval as approval to prepare the review list, not as approval to mutate canonical records or publish runtime adapters.

When the harvest modifies the harvest workflow, practice-harvester asset, adapter publishing workflow, runtime publish behavior, AGENTS instructions, or any rule that governs future self-updates, use a stricter self-referential sequence:

```text
harvest report / review list
  -> explicit approval of listed items
  -> canonical mutation
  -> PR or equivalent review surface
  -> post-merge adapter/runtime publish
  -> final verification
```

In self-referential workflow changes, do not repair a missing review list by publishing first and explaining afterward. If the review list was skipped, stop, publish no further runtime changes, add the missing harvest report to the PR or issue, and wait for approval of that report before continuing.

Present a concise review list. For each new or changed practice, show:

- title;
- action: merge, create, supersede, or defer;
- reason;
- canonical files affected;
- adapters that will be updated after approval.
- runtime or global instruction files that will be updated after approval.

Approval is per practice. When the user approves an item, apply that item's full chain:

```text
merge/create/supersede
  -> promote approved practice to active when applicable
  -> update index
  -> publish relevant adapters
  -> report changed files
```

Group review items by decision and risk where useful:

- accepted candidate practices;
- workflow updates;
- rejected-as-practice items;
- deferred items needing more evidence;
- adapter updates pending approval.

## 12. Update Adapters

After an item is approved and canonical updates are applied:

1. Read `workflows/publish-adapters.md`.
2. Update the relevant adapter references.
3. Keep adapters compact.
4. Do not duplicate long-form rationale into adapters.

## 13. Missed Activation Self-Check

Before the final report, do a lightweight missed-activation check. Record missed evidence only when there is a concrete missed moment and a specific practice ID.

Record `--evidence-type missed` when one of these is true:

- the user explicitly says the agent violated or failed to apply a practice;
- the harvest/review identifies a specific step where a practice should have triggered but did not;
- the agent can name the practice ID, the missed trigger, and the resulting risk without relying on vague self-criticism.

Do not record missed evidence for general uncertainty, low confidence, or every ordinary correction. Missed evidence is a review signal, not successful usage, and must stay local unless summarized through an approved aggregate format.

Use `workflows/record-asset-usage.md` for the command format.

## 14. Final Report Format

Report:

```text
Candidates reviewed:
1. <candidate title>
   Decision: discard | merge | create | supersede | defer
   Reason: <brief reason>
   Canonical change: <file or none>
   Adapter change: <file or none>

Rejected as practices:
- <important item>: <reason or better artifact class>

Files changed:
- <path>

Needs human review:
- <entry id/title or none>
```
