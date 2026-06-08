---
id: GOV-006
title: Explicitly mark current capability versus proposed capability
domain: governance
type: principle
status: active
version: 1
created: 2026-06-08
updated: 2026-06-08
tags: [governance, capability-boundary, architecture-discussion, handoff]
aliases:
  - GOV-006
  - mark current versus proposed capability
  - distinguish current proposed future deprecated unknown
related: [GOV-001, GOV-003, GOV-005, ARCH-007]
applies_when:
  - summarizing complex system discussions
  - writing harvest output or handoff artifacts
  - planning work based on proposed architecture
  - deciding whether docs, scripts, adapters, or workflows can depend on a capability
review_required: false
provenance: "Corrected harvest outcome from ChatGPT memory-system design and harvest discipline discussion; source context: docs/memory-system-handoff-dump.md."
---

## Principle

In complex system discussions, summaries, harvests, and handoffs, explicitly mark the difference between current capability and proposed capability.

## Rationale

The discussion confused the current Agent Foundry substrate with a future memory subsystem. This failure can also occur in robotics, runtime tooling, deployment, documentation, and other system design work.

## Guidance

Use this vocabulary when capability state affects action:

- `current`: implemented and usable;
- `candidate`: proposed and awaiting review;
- `proposed`: designed but not implemented;
- `future`: intentionally deferred;
- `deprecated`: considered before but no longer recommended;
- `unknown`: not yet verified.

When a plan depends on a capability, mark its state and verify repository support before writing files or claiming completion.

## Use This When

- A summary mixes implemented features with target architecture.
- A workflow or handoff routes work to a path, schema, or subsystem.
- A plan includes future capabilities that are not yet present.

## Watch Out For

- Do not let conceptual vocabulary become an implicit writable substrate.
- Do not rely on non-existent capabilities in docs, scripts, adapters, or harvest output.
- Do not leave `unknown` capability state unresolved when it affects edits.

## Activation

- Tier: task_router
- Phases: planning, summary, harvest, handoff, review
- Signals: discussion mixes implemented behavior with proposed architecture; plan depends on a capability whose repository support is uncertain
- Evidence: summary, plan, or harvest marks capability state before making claims or writing dependent files

## Review Notes

- Human approval: approved on 2026-06-08.
- Failure prevented: plans, docs, scripts, adapters, or harvest outputs depending on non-existent capabilities.

## Related Practices

- [[GOV-001]]
- [[GOV-003]]
- [[GOV-005]]
- [[ARCH-007]]
