---
id: META-002
title: Harvest before publishing
domain: meta
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [harvesting, review, skill-rot]
aliases:
  - META-002
  - do not add raw notes to skills
  - review gate
related: [META-001, META-003]
applies_when:
  - extracting lessons from a project session
  - updating practices after coding work
  - preventing skill rot
review_required: false
provenance: "Initial Agent Foundry system design."
---

## Principle

Reusable lessons must be harvested, classified, deduplicated, and reviewed before being published into agent adapters.

## Rationale

Raw session notes often contain project-specific facts, duplicate ideas, and immature conclusions. Publishing them directly into skills bloats context and weakens future agent behavior.

## Guidance

Follow `workflows/harvest-practices.md`. Each candidate must receive a decision: discard, merge, create, supersede, or defer. New entries start as `candidate` or `proposed` unless the user explicitly approves activation.

## Watch Out For

Avoid creating a new practice for every interesting observation. Prefer strengthening existing rules with examples or sharper guidance.

## Example

If a session shows that UI should consume a domain summary, first search for existing frontend/domain separation practices. If one exists, merge the new case as an example rather than creating a near-duplicate.

## Related Practices

- [[META-001]]
- [[META-003]]
