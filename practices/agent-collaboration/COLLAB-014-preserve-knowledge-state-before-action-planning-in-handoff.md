---
id: COLLAB-014
title: Preserve knowledge state before action planning in handoff
domain: agent-collaboration
type: checklist
status: active
version: 1
created: 2026-06-08
updated: 2026-06-08
tags: [agent-collaboration, handoff, continuity, knowledge-preservation]
aliases:
  - COLLAB-014
  - preserve knowledge before plan
  - handoff keeps research state
related: [COLLAB-005, COLLAB-006, GOV-003, ARCH-007]
applies_when:
  - writing or consuming a ChatGPT-to-Codex handoff
  - transferring context across agents or accounts
  - compressing a long discussion into a continuation artifact
  - preparing a project context transfer
review_required: false
provenance: "Corrected harvest outcome from ChatGPT memory-system design and harvest discipline discussion; source context: docs/memory-system-handoff-dump.md."
---

## Principle

A handoff for a complex discussion must preserve knowledge state before listing next actions. Do not compress a long session dump into only an implementation plan.

## Rationale

The first handoff attempt toward Codex over-focused on execution and lost the goal of preserving research output. A receiving agent needs the state of understanding, not just a task queue.

## Guidance

A good handoff should preserve:

- context and goals;
- research output;
- conceptual frameworks;
- decisions and rationale;
- rejected options;
- user corrections;
- current capability boundary;
- unresolved questions;
- next actions.

Place next actions after the knowledge state they depend on. If the handoff is too long, summarize each category explicitly instead of dropping research, rationale, corrections, or unresolved questions.

## Use This When

- ChatGPT hands work to Codex.
- One agent hands work to another agent.
- A discussion is being migrated across accounts, sessions, or tools.
- A long discussion dump is being compressed for future work.

## Watch Out For

- Do not reduce research output to a TODO list.
- Do not hide rejected options or user corrections; they are often the safest way to prevent drift.
- Do not imply proposed capabilities are current unless the repository confirms them.

## Activation

- Tier: workflow_embedded
- Phases: handoff_creation, handoff_consumption, context_compaction, migration
- Signals: ChatGPT-to-Codex handoff, agent-to-agent handoff, account migration, long discussion dump, project context transfer
- Evidence: handoff preserves knowledge-state categories before listing next actions

## Review Notes

- Human approval: approved on 2026-06-08.
- Failure prevented: losing research, rationale, constraints, corrections, and unresolved questions during cross-agent or cross-session transfer.

## Related Practices

- [[COLLAB-005]]
- [[COLLAB-006]]
- [[GOV-003]]
- [[ARCH-007]]
