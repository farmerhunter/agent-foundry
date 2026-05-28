---
id: ARCH-001
title: Boundaries before tools
domain: architecture
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [architecture, boundaries, technical-choice]
aliases:
  - architecture is not a tech stack
  - tools serve boundaries
  - ARCH-001
related: [ARCH-002, ARCH-006]
applies_when:
  - designing a new system
  - evaluating technical choices
  - refactoring around unstable implementation details
review_required: false
provenance: "Extracted from token-panic architecture redesign."
---

## Principle

Define system boundaries and change ownership before choosing or centering tools.

## Rationale

Tools answer how something is implemented. Architecture answers how the system remains locally stable when requirements, integrations, storage, UI, or infrastructure change.

## Guidance

Identify stable domain objects, independent sources of change, and module boundaries first. Then assign tools to those boundaries. If a tool can be replaced without invalidating the design, the architecture is likely centered on the right abstraction.

## Use This When

- A design starts with a technology list.
- A temporary implementation difficulty is becoming the main abstraction.
- A system needs to support multiple data sources or environments.

## Watch Out For

Do not let an important tool become an accidental domain concept.

## Example

In token-panic, Playwright was moved from the center of the architecture to one implementation of a `browser_scrape` provider adapter.

## Activation

- Tier: always_preflight
- Phases: planning, before_new_layer, architecture_review
- Signals: choosing a framework, tool, database, service, API, or automation before defining boundaries; implementation detail becoming the central abstraction
- Evidence: final report names the boundary or ownership decision before naming the tool choice

## Related Practices

- [[ARCH-002]]
- [[ARCH-006]]
