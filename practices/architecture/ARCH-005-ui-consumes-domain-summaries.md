---
id: ARCH-005
title: UI consumes domain summaries
domain: architecture
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [architecture, frontend, domain]
aliases:
  - ARCH-005
  - renderer displays state
  - domain derives state
related: [ARCH-003, ARCH-004]
applies_when:
  - designing frontend/backend boundaries
  - building dashboards
  - moving business rules out of UI components
review_required: false
provenance: "Extracted from token-panic architecture redesign."
---

## Principle

UI should consume domain summaries, not raw integration data or core business derivations.

## Rationale

When UI components parse raw data and compute business meaning, the logic becomes hard to test and hard to reuse across surfaces.

## Guidance

Let the domain layer produce display-ready summaries such as primary metric, status, confidence, warning state, and derived estimates. UI should handle layout, interaction, and presentation.

## Example

In token-panic, `ProviderSummary` is produced by Core Domain from snapshots and history. The renderer does not calculate burn rate or remaining time directly.

## Related Practices

- [[ARCH-003]]
- [[ARCH-004]]
