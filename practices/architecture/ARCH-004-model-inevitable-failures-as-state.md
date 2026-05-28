---
id: ARCH-004
title: Model inevitable failures as state
domain: architecture
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [architecture, errors, external-dependencies]
aliases:
  - failures are domain state
  - ARCH-004
related: [ARCH-001, ARCH-005]
applies_when:
  - integrating with external systems
  - designing user-visible reliability states
  - replacing scattered exception handling
review_required: false
provenance: "Extracted from token-panic architecture redesign."
---

## Principle

Failures that are expected to happen should be modeled as domain state, not only as exceptions.

## Rationale

External systems will fail, expire credentials, change schemas, rate-limit requests, and return stale data. If these cases are not modeled, they leak into scattered fallback code and unclear UI behavior.

## Guidance

Name the expected states explicitly. Make adapters translate external failures into these states. Let UI consume clear statuses instead of interpreting low-level errors.

## Example

For token-panic provider snapshots:

```ts
status: "ok" | "stale" | "error" | "auth_required" | "disabled";
```

## Related Practices

- [[ARCH-001]]
- [[ARCH-005]]
