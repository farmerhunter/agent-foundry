---
id: GOV-002
title: Prefer the smallest maintainable mechanism
domain: governance
type: principle
status: active
version: 1
created: 2026-05-28
updated: 2026-05-28
tags: [governance, maintainability, complexity, scope]
aliases:
  - GOV-002
  - smallest maintainable mechanism
  - do not add machinery before boundaries are clear
related: [META-004, META-005, ARCH-001]
applies_when:
  - choosing how much implementation, automation, abstraction, documentation, or tooling to add
  - responding to an open-ended request such as "make the necessary changes"
  - adding a new layer, workflow, script, framework, generated artifact, or integration
  - deciding whether to create, extend, skip, or defer reusable capability
review_required: false
provenance: "Extracted from the Obsidian rollback lesson and capability-governance review on 2026-05-28."
---

## Principle

Prefer the smallest maintainable mechanism that solves the real problem. More complete-looking solutions are worse when they add synchronization burden, unclear ownership, or long-term maintenance cost.

## Rationale

Agents tend to overbuild when the user gives an open-ended implementation request. Extra scripts, files, generated views, abstractions, or workflows can make the first result look polished while making the project harder to operate later.

## Guidance

Before adding machinery, ask:

- What is the smallest change that preserves the intended capability?
- What new state must be maintained?
- What future workflow must remember this change?
- Can the same value be achieved by tightening schema, checks, docs, or an existing workflow?
- What fails if no one remembers this change later?

Prefer bounded changes that integrate into existing workflows and checks. If a mechanism needs ongoing maintenance, define its owner, trigger, validation path, and failure mode.

## Watch Out For

Do not treat "more complete" as "more correct." A hub note, generated index, helper script, adapter, automation, or abstraction is only justified if it improves long-term operation without creating hidden sync work.

## Activation

- Tier: always_preflight
- Phases: planning, before_edit, before_new_layer, review
- Signals: open-ended implementation request; adding scripts, workflows, adapters, generated files, abstractions, automations, or integrations; solution seems complete but adds maintenance state
- Evidence: final report explains the smaller mechanism chosen or the maintenance path for added machinery

## Related Practices

- [[META-004]]
- [[META-005]]
- [[ARCH-001]]
