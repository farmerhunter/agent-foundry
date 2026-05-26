---
id: META-004
title: Choose the smallest suitable asset
domain: meta
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [assets, discovery, skill-rot, scope]
aliases:
  - skill is not the default
  - smallest suitable reusable asset
related: [META-001, META-002, META-003, META-005]
applies_when:
  - discovering repeated workflows
  - deciding whether to create a skill
  - choosing between skill, subagent, automation, extend, skip, or defer
review_required: false
provenance: "Extracted from Agent Foundry asset lifecycle design."
---

## Principle

Package repeated work into the smallest suitable asset. A skill is one possible form, not the default.

## Rationale

Creating a new skill for every useful observation causes overlap and skill rot. Some repeated work is better handled as an automation, a bounded subagent, an extension of an existing asset, or a skipped/deferred candidate.

## Guidance

For each discovered workflow, compare:

- `skill`: reusable workflow or operating guide used by the current agent.
- `subagent`: bounded delegable role or investigation/review task.
- `automation`: scheduled or event-driven check, report, reminder, or monitor.
- `extend_existing`: existing asset mostly covers the need.
- `skip`: one-off, vague, sensitive, or already sufficiently covered.
- `defer`: promising but lacks enough evidence.

Prefer the smallest form that produces the intended value with clear triggers and success criteria.

## Watch Out For

Do not create a skill when a checklist in an existing skill, a recurring automation, or a specialized subagent would be narrower and easier to maintain.
