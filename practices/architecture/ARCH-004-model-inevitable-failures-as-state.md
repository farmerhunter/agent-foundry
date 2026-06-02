---
id: ARCH-004
title: Model inevitable failures as state
domain: architecture
type: principle
status: active
version: 2
created: 2026-05-26
updated: 2026-06-02
tags: [architecture, errors, external-dependencies, diagnostics, failure-taxonomy]
aliases:
  - ARCH-004
  - failures are domain state
related: [ARCH-001, ARCH-005, DEBUG-001]
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

When the failure will be diagnosed across sessions or by a coding agent, extend the same discipline into diagnostics:

- define stable failure reasons or a failure taxonomy;
- record the failing component and boundary, not only a free-text exception;
- keep user-facing status, diagnostic reason, and low-level error message distinct;
- include enough metadata for reproduction without defaulting to sensitive raw data.

The diagnostic taxonomy does not need to be a business domain model, but it should be stable enough that tests, debug bundles, and future agents can rely on it.

## Example

For token-panic provider snapshots:

```ts
status: "ok" | "stale" | "error" | "auth_required" | "disabled";
```

For token-panic serviceability, Safari capture and parser failures use stable reasons such as `tab_not_found`, `javascript_probe_failed`, `no_limit_candidates`, and `candidate_lines_found_but_no_valid_limit` so UI, debug bundles, and coding agents can identify the failing boundary.

## Related Practices

- [[ARCH-001]]
- [[ARCH-005]]
- [[DEBUG-001]]
