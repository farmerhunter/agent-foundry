---
id: META-001
title: Canonical practices are the source of truth for adapters
domain: meta
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [canonical, source-of-truth, adapters]
aliases:
  - skills are downstream
  - adapters are not source of truth
  - META-001
related: [GOV-001, META-002, META-003]
applies_when:
  - maintaining reusable agent practices
  - updating agent skills or prompts
  - porting practices across agent environments
review_required: false
provenance: "Initial Agent Foundry system design."
---

## Principle

Within Agent Foundry, canonical practice entries are the source of truth for agent adapters. Agent-specific skills, prompts, instructions, and commands are downstream outputs.

## Rationale

Different agent environments use different packaging formats. If practices are edited directly inside each adapter, the system will drift and become hard to deduplicate, review, and merge.

## Guidance

When adding or changing a reusable practice, update the canonical entry under `practices/` first. Update Codex skills, Claude Code instructions, ChatGPT custom instructions, DeepSeek prompt packs, or Hermes prompt packs only after the canonical entry is settled.

For the cross-project source-of-truth rule, apply [[GOV-001]]. This practice is the Agent Foundry-specific application of that broader governance principle.

## Watch Out For

Do not treat a polished `SKILL.md` as the canonical source. It is optimized for context loading and trigger behavior, not long-term knowledge governance.

## Example

An architecture principle should live under `practices/architecture/ARCH-*.md`. The Codex `architecture-design` skill should contain only the compact version needed during work.

## Related Practices

- [[GOV-001]]
- [[META-002]]
- [[META-003]]
