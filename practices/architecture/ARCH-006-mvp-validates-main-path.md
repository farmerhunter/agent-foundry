---
id: ARCH-006
title: MVP validates the main path
domain: architecture
type: principle
status: active
version: 2
created: 2026-05-26
updated: 2026-06-04
tags: [architecture, mvp, product]
aliases:
  - ARCH-006
  - do not validate all future imagination in MVP
related: [ARCH-001, ARCH-008]
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

When the main path is already working, keep using the same rule for later phases: the next phase should advance the product or architecture's real operating goal, not whichever adjacent engineering track is most recently visible. Release engineering, notarization, auto-update, infrastructure polish, broad plugin systems, and speculative integrations should stay behind the actual distribution or usage need they serve.

If a future capability is valuable only for a future audience or distribution mode, record the restart condition instead of promoting it into the next phase. For example: "do signing/notarization when distributing a ready-made DMG to ordinary users" is better than making signing the next milestone while the real product goal is expanding supported service sources.

## Example

In token-panic, LLM-assisted custom parser generation was deferred. The MVP focuses on one provider fetch, normalized snapshot, storage, dashboard display, and simple derived metrics.

Later in token-panic, code signing and notarization were initially treated as the next packaging phase. They were then deferred because the app was primarily for self-use and source-build users, while the real next product goal was expanding supported LLM service sources through manual and semi-automatic provider paths.

## Related Practices

- [[ARCH-001]]
- [[ARCH-008]]
