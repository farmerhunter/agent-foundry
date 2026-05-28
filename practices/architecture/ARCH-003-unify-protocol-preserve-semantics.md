---
id: ARCH-003
title: Unify protocol, preserve semantics
domain: architecture
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [architecture, domain-modeling, normalization]
aliases:
  - do not erase business differences
  - ARCH-003
related: [ARCH-002, ARCH-005]
applies_when:
  - normalizing heterogeneous data
  - designing shared interfaces
  - building multi-provider systems
review_required: false
provenance: "Extracted from token-panic architecture redesign."
---

## Principle

Unify outer protocol and lifecycle, but preserve meaningful internal domain differences.

## Rationale

Bad normalization erases business semantics and forces all variants into an inaccurate common shape. Good normalization gives variants a shared envelope while keeping their payloads accurate.

## Guidance

Use a common envelope for identity, source, status, timestamps, and lifecycle. Use typed payloads or discriminated unions for domain-specific data.

## Example

Provider snapshots share fields such as `provider_id`, `source`, `quota_model`, `status`, and `captured_at`, while `BalancePayload`, `LimitPayload`, `UsagePayload`, and `CostPayload` remain distinct.

## Related Practices

- [[ARCH-002]]
- [[ARCH-005]]
