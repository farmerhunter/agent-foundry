---
id: ARCH-006
title: MVP validates the main path
domain: architecture
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [architecture, mvp, product]
aliases:
  - do not validate all future imagination in MVP
related: [ARCH-001]
applies_when:
  - scoping an MVP
  - deferring high-uncertainty capabilities
  - preventing architecture from overfitting future features
review_required: false
provenance: "Extracted from token-panic architecture redesign."
---

## Principle

The MVP should validate the main system path and key boundaries, not every plausible future capability.

## Rationale

High-uncertainty features can distort the first implementation. A good MVP proves the architecture's core loop while leaving extension points for later.

## Guidance

Define the smallest end-to-end path that exercises the important boundaries. Defer optional, high-complexity, or low-confidence features until the main loop is working.

## Example

In token-panic, LLM-assisted custom parser generation was deferred. The MVP focuses on one provider fetch, normalized snapshot, storage, dashboard display, and simple derived metrics.

