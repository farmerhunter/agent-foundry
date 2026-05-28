---
id: META-006
title: Memory is evidence, not source of truth
domain: meta
type: principle
status: active
version: 1
created: 2026-05-26
updated: 2026-05-26
tags: [memory, evidence, source-of-truth, governance]
aliases:
  - memory can suggest but foundry decides
  - memory is not canonical
  - META-006
related: [GOV-003, META-001, META-002, META-004]
applies_when:
  - using agent memory for discovery
  - converting session history into practices or assets
  - deciding what belongs in canonical records
review_required: false
provenance: "Extracted from Agent Foundry naming and memory boundary discussion."
---

## Principle

For Agent Foundry governance, memory can suggest; canonical records decide. Agent memories, session summaries, activity logs, and rollout summaries are evidence sources, not canonical source of truth for practices, assets, adapters, or lifecycle state.

## Rationale

Memory is useful for discovering repeated patterns, user preferences, and usage evidence. It may also be incomplete, stale, noisy, or unreviewed. Durable practices and reusable assets require explicit governance, indexing, review, and publication.

## Guidance

Use memory as:

- discovery evidence for repeated workflows;
- preference evidence for candidate rules;
- usage evidence candidates for assets.

Do not use memory as the only authoritative home for:

- canonical practices;
- asset records;
- adapter mappings;
- approval policy;
- lifecycle state.

If a memory contains a durable rule, harvest it into `practices/`. If it indicates repeated work, process it through `discover assets`. If it records useful asset or practice use, record concise evidence through `scripts/record_asset_usage.py` so raw evidence stays local and shared review uses sanitized aggregates.

For the cross-project rule that transient session context is evidence rather than durable project truth, apply [[GOV-003]].

## Watch Out For

Do not let automatically written memory silently override approved practices or active assets.

## Related Practices

- [[GOV-003]]
- [[META-001]]
- [[META-002]]
- [[META-004]]
