---
id: META-005
title: Define asset boundaries before creation
domain: meta
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [assets, scope, boundaries, discovery]
aliases:
  - define skill scope before creating it
  - asset boundaries before asset creation
  - META-005
related: [META-001, META-002, META-004]
applies_when:
  - creating or extending a reusable asset
  - deciding skill scope
  - preventing overlap between assets
review_required: false
provenance: "Extracted from Agent Foundry asset lifecycle design."
---

## Principle

Before creating a reusable asset, define its trigger, responsibility, non-responsibility, inputs, process, outputs, and success criteria.

## Rationale

Assets without explicit boundaries become broad prompt piles. Boundary definitions make assets easier to trigger, publish, review, merge, or retire.

## Guidance

Every asset should answer:

- Trigger: when should it be used?
- Responsibility: what does it do?
- Non-responsibility: what does it explicitly not do?
- Inputs: what information does it need?
- Process: what steps or checks does it follow?
- Outputs: what should it produce?
- Success criteria: how do we know it helped?

If these cannot be answered, defer the asset instead of creating it.

## Watch Out For

Avoid assets with vague triggers such as "help with engineering" or "improve code". Narrow the asset or extend an existing one.

## Related Practices

- [[META-001]]
- [[META-002]]
- [[META-004]]
