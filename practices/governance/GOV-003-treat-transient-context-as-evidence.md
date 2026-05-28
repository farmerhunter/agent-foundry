---
id: GOV-003
title: Treat transient context as evidence
domain: governance
type: principle
status: active
version: 1
created: 2026-05-28
updated: 2026-05-28
tags: [governance, memory, evidence, durable-records]
aliases:
  - GOV-003
  - session context is evidence
  - memory is not project truth
related: [META-006, META-007, ARCH-007]
applies_when:
  - using chat history, memory, rollout summaries, notes, logs, or temporary analysis
  - turning a session conclusion into project behavior
  - deciding whether an insight belongs in code, schema, design docs, tests, practices, or memory
  - resuming work after compaction, interruption, or handoff
review_required: false
provenance: "Extracted from the memory and rollback discussions on 2026-05-28."
---

## Principle

Treat transient context as evidence, not project truth. Chat history, agent memory, session summaries, temporary notes, and activity logs can suggest decisions, but durable project behavior must live in the project's canonical records.

## Rationale

Transient context is useful but incomplete. It can be stale, compressed, unavailable to another agent, or detached from the files that actually govern the project. If agents rely on it as truth, future work becomes inconsistent and hard to audit.

## Guidance

When a session produces a durable decision, place it in the right canonical home:

- code or tests for executable behavior;
- schema or config for machine-readable contracts;
- design docs or ADRs for architectural decisions;
- practices or assets for reusable agent behavior;
- local logs or aggregates for usage evidence.

Use memory and summaries to rediscover context, then verify against project-owned records before acting.

## Watch Out For

Do not write long-term behavior only into memory or a chat transcript. Do not assume another agent, machine, or future compacted session will recover the same context.

## Activation

- Tier: always_preflight
- Phases: planning, resume, handoff, before_edit
- Signals: relying on chat history, memory, rollout summary, temporary note, or compacted context as fact; turning a session conclusion into durable behavior
- Evidence: final report names the project-owned record checked or updated instead of relying only on transient context

## Related Practices

- [[META-006]]
- [[META-007]]
- [[ARCH-007]]
