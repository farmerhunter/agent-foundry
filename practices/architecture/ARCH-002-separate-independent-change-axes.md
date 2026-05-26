---
id: ARCH-002
title: Separate independent axes of change
domain: architecture
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [architecture, modeling, change-management]
aliases:
  - do not merge independent dimensions
related: [ARCH-001, ARCH-003]
applies_when:
  - modeling heterogeneous integrations
  - designing adapter layers
  - adding new variants to a system
review_required: false
provenance: "Extracted from token-panic architecture redesign."
---

## Principle

When two concepts can vary independently, model them independently.

## Rationale

Combining independent dimensions creates artificial types, special cases, and branching logic. Separating them allows the system to express valid combinations without distorting the model.

## Guidance

Look for dimensions such as source, transport, domain model, storage backend, presentation mode, and lifecycle state. If each can change without requiring the other to change, represent them separately.

## Example

In token-panic, `source` and `quota_model` were split:

```ts
source: "official_api" | "browser_scrape" | "custom_parser" | "manual";
quota_model: "balance" | "limit" | "usage" | "cost";
```

