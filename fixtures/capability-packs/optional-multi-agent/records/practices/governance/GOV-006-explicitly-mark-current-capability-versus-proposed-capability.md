---
id: GOV-006
title: Explicitly mark current capability versus proposed capability
domain: governance
type: principle
status: active
version: 4
created: 2026-06-08
updated: 2026-08-10
tags: [governance, capability-boundary, architecture-discussion, handoff]
aliases:
  - GOV-006
  - mark current versus proposed capability
  - distinguish current proposed future deprecated unknown
  - design accepted is not current capability
  - proposed architecture is not implemented capability
related: [GOV-001, GOV-003, GOV-005, ARCH-007]
applies_when:
  - summarizing complex system discussions
  - writing harvest output or handoff artifacts
  - planning work based on proposed architecture
  - deciding whether docs, scripts, adapters, or workflows can depend on a capability
review_required: false
provenance: "Corrected harvest outcome from ChatGPT memory-system design and harvest discipline discussion; source context: docs/memory-system-handoff-dump.md. Revised after Agent Foundry V2 planning correction on 2026-07-08, where accepted local-first orchestration designs needed to remain proposed capability until ledger storage/replay, board, backfill, and sync-plan implementation gates exist; v4 adds AF18 fail-closed handling for unavailable trusted producers and host evidence."
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

When a plan depends on a capability, mark its state and verify repository support before writing files or claiming completion. An accepted architecture design is still `proposed` until there is a runnable implementation path, persisted state or artifact where required, verification evidence, and user-facing use instructions.

Evidence discipline applies to measurements and acceptance claims as well as implementation state: preserve `not_collected`, `unavailable`, and `unknown` literally. Do not replace a missing Human rating with an inferred number, or turn an analyst estimate into an observed metric.

Treat `unavailable` or `not_exposed` as a terminal state for the current capability boundary when no trusted producer, host field, or verifier exists. Reject caller self-attestation and do not keep expanding implementation merely to make an unobservable measurement appear available. If the measurement remains product-important, create a separately scoped follow-up with its own producer, evidence, and activation gate.

## Use This When

- A summary mixes implemented features with target architecture.
- A workflow or handoff routes work to a path, schema, or subsystem.
- A plan includes future capabilities that are not yet present.
- A design issue was accepted and downstream work is about to mark a milestone, Epic, or readiness gate complete.

## Watch Out For

- Do not let conceptual vocabulary become an implicit writable substrate.
- Do not rely on non-existent capabilities in docs, scripts, adapters, or harvest output.
- Do not leave `unknown` capability state unresolved when it affects edits.
- Do not describe design-only objects, schemas, storage, sync, migration, or board behavior as current capability before implementation and verification exist.

## Activation

- Tier: task_router
- Phases: planning, summary, harvest, handoff, review
- Signals: discussion mixes implemented behavior with proposed architecture; plan depends on a capability whose repository support is uncertain; accepted design may be mistaken for implemented workflow
- Evidence: summary, plan, or harvest marks capability state before making claims, writing dependent files, or closing readiness

## Review Notes

- Human approval: approved on 2026-06-08.
- Failure prevented: plans, docs, scripts, adapters, or harvest outputs depending on non-existent capabilities.

## Related Practices

- [[GOV-001]]
- [[GOV-003]]
- [[GOV-005]]
- [[ARCH-007]]
