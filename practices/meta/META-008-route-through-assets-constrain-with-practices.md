---
id: META-008
title: Route through assets, constrain with practices
domain: meta
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [assets, practices, routing, dispatch, meta]
aliases:
  - META-008
  - assets perform work, practices govern rules
  - skill vs practice boundary
  - invoke asset, apply practice
related: [META-001, META-004, META-005, META-006]
applies_when:
  - interpreting user intent at session start
  - deciding whether to invoke a skill or apply a rule
  - writing or updating agent adapters
  - discovering or creating new reusable capabilities
review_required: false
provenance: "Harvested from the practice vs asset boundary review on 2026-05-26."
---

## Principle

Route user requests through assets; constrain execution with practices. Assets are user-facing reusable workflows. Practices are canonical behavioral rules. Do not conflate them.

## Rationale

When an agent treats a practice as a callable workflow, it invents unnecessary skills. When it treats an asset as a behavioral rule, it misses the structured process and success criteria the asset provides. A clear boundary prevents bloat, drift, and ambiguous responsibility.

## Guidance

Before acting on a request, classify it:

1. **Is the user asking you to execute a repeatable workflow?**
   - Match the request to an asset `usage_trigger`.
   - Invoke the asset: load its inputs, process, and outputs.
   - During execution, reference the canonical practices listed in the asset's `canonical_practices`.
2. **Is the user asking you to behave differently or apply a constraint?**
   - Match the request to a canonical practice in the relevant domain.
   - Apply the practice's Principle and Guidance to your current behavior.
   - Do not invent a new asset for a one-off behavioral correction.
3. **Is the user asking you to update, canonize, or govern agent knowledge?**
   - This is meta-work. Invoke the Practice Harvester asset, which itself references META practices.

## Use This When

- The user gives a command that could match both a short command and a general domain rule.
- You are deciding whether to create a new skill or write a new practice.
- You are updating an adapter and need to decide whether the content belongs in a skill body or in a rules section.

## Watch Out For

- Do not route a request to a practice when an active asset covers it. Practices constrain behavior; they do not own end-to-end workflows.
- Do not invoke an asset when the user only asked for a behavioral correction. For example, "stop closing issues without comments" is a practice application (COLLAB-002), not a skill invocation.
- Do not duplicate an asset's process into a practice entry. Assets own the workflow; practices own the rules.

## Example

User: `"harvest practices from this session"`
- Classification: execute repeatable workflow → invoke asset `ASSET-META-001`
- Asset process runs; during execution it references `META-001` (canonical practices are source of truth), `META-002` (harvest before publishing), etc.

User: `"I noticed you keep choosing tools before defining boundaries. Stop doing that."`
- Classification: behavioral correction → apply practice `ARCH-001`
- No asset is invoked. The agent adjusts its behavior according to the principle.

## Related Practices

- [[META-001]]
- [[META-004]]
- [[META-005]]
- [[META-006]]
