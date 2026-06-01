---
id: ARCH-001
title: Boundaries before tools
domain: architecture
type: principle
status: active
version: 2
created: 2026-05-26
updated: 2026-06-01
tags: [architecture, boundaries, technical-choice]
aliases:
  - ARCH-001
  - architecture is not a tech stack
  - tools serve boundaries
  - boundary rewrite
  - substitution test
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

Identify stable domain objects, durable outcomes, independent sources of change, and module boundaries first. Then assign tools to those boundaries. If a tool can be replaced without invalidating the design, the architecture is likely centered on the right abstraction.

When a design appears centered on a current implementation path, perform a boundary rewrite. Separate the durable state or outcome, stable responsibilities, ownership boundaries, change points, and current mechanisms. Then run substitution tests against plausible alternatives for tools, APIs, storage, UI, workflows, or automations. Keep the architecture shape only if its core responsibilities survive those substitutions.

## Use This When

- A design starts with a technology list.
- A temporary implementation difficulty is becoming the main abstraction.
- The hardest current implementation problem becomes the system's central noun.
- The proposed architecture is mostly a sequence of current tools or implementation steps.
- Replacing one current mechanism would collapse the proposed core abstraction.
- A system needs to support multiple data sources or environments.

## Watch Out For

Do not let an important tool become an accidental domain concept.

## Example

In token-panic, Playwright was moved from the center of the architecture to one implementation of a `browser_scrape` provider adapter.

## Activation

- Tier: always_preflight
- Phases: planning, before_new_layer, architecture_review
- Signals: choosing a framework, tool, database, service, API, prompt, parser, scraper, storage format, workflow, or automation before defining boundaries; implementation detail becoming the central abstraction; proposed architecture is mostly a sequence of current tools or implementation steps; hardest current implementation problem becomes the system's central noun; replacing one current mechanism would collapse the proposed core abstraction
- Evidence: final report names the durable state or outcome, stable responsibilities, current mechanisms, and at least one substitution test showing what remains stable when a mechanism changes

## Related Practices

- [[ARCH-002]]
- [[ARCH-006]]
