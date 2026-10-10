---
id: GOV-005
title: Do not use future architecture as current operating substrate
domain: governance
type: anti-pattern
status: active
version: 1
created: 2026-06-08
updated: 2026-06-08
tags: [governance, capability-boundary, architecture, source-of-truth]
aliases:
  - GOV-005
  - future architecture is not current substrate
  - do not write to proposed systems
related: [GOV-001, GOV-003, GOV-006, META-006]
applies_when:
  - designing a future system
  - routing artifacts to repository destinations
  - writing workflows, plans, or implementation summaries
  - deciding whether a directory, schema, or workflow exists now
review_required: false
provenance: "Corrected harvest outcome from ChatGPT memory-system design and harvest discipline discussion; source context: docs/memory-system-handoff-dump.md."
---

## Principle

When a session is designing a future system, do not use the future system's concepts, directories, schemas, categories, or workflows as if they already exist.

## Rationale

Future memory subsystem concepts such as `knowledge/`, `project memory`, and `research memo` were mistakenly treated as current destinations. That created fake routing decisions and false completion claims based on architecture that had not been implemented.

## Guidance

Separate these states before acting:

- `current capability`: implemented and usable now;
- `candidate capability`: proposed and awaiting review;
- `proposed capability`: designed but not implemented;
- `future extension`: intentionally deferred;
- `conceptual vocabulary`: useful for discussion but not a writable substrate.

Before writing a file, updating a workflow, or claiming completion, ask: is this destination implemented in the current repository, or only a proposed design concept?

## Use This When

- A discussion introduces new architecture, lifecycle categories, or directory names.
- A handoff asks an agent to continue from a conceptual design.
- A plan routes artifacts to destinations that may not exist yet.

## Watch Out For

- Do not create unexecutable routing based on future vocabulary.
- Do not treat a target architecture as governance that already exists.
- Do not claim completion by pointing to categories, paths, or workflows that are not present in the repository.

## Activation

- Tier: task_router
- Phases: planning, harvest, handoff, before_edit, review
- Signals: a session designs future architecture; a plan routes work to new directories, schemas, categories, workflows, or subsystems
- Evidence: output verifies whether the destination is current, candidate, proposed, future, deprecated, or unknown before acting

## Review Notes

- Human approval: approved on 2026-06-08.
- Failure prevented: invalid paths, fake governance, unexecutable routing, and false completion.

## Related Practices

- [[GOV-001]]
- [[GOV-003]]
- [[GOV-006]]
- [[META-006]]
