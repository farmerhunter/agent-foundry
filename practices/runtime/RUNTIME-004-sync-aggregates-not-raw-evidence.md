---
id: RUNTIME-004
title: Sync aggregates, not raw evidence
domain: runtime
type: principle
status: active
version: 1
created: 2026-05-27
updated: 2026-05-27
tags: [runtime, sync, evidence, privacy, review]
aliases:
  - keep raw usage local
  - sync usage aggregates
  - aggregate evidence across machines
  - RUNTIME-004
related: [RUNTIME-002, RUNTIME-003, META-006, META-010]
applies_when:
  - recording asset or practice usage evidence
  - reviewing assets or practices across multiple machines
  - exporting portable snapshots
  - deciding what operational metadata is safe to sync
review_required: false
provenance: "Harvested from the multi-machine usage review design on 2026-05-27, where raw local evidence needed to stay private while review statistics needed cross-agent aggregation."
---

## Principle

Sync aggregate usage statistics, not raw evidence. Raw usage logs are local audit evidence. Shared review should consume sanitized aggregate rows that can be merged across machines and agents.

## Rationale

Asset and practice review needs usage statistics from every machine where agents run. If usage evidence stays only local, reviews undercount active practices and assets. If raw evidence is synced directly, project names, prompts, notes, and session context can leak into remote repositories or portable snapshots.

A two-layer model preserves both needs. Raw logs stay local for audit and reconstruction. Aggregates provide enough cross-machine signal for lifecycle review without copying sensitive session context.

## Guidance

Use two evidence layers:

1. Raw local evidence:
   - stored under gitignored local paths such as `usage/local/`;
   - may include project, trigger, short note, agent, outcome, and date;
   - excluded from snapshots and default remote sync.
2. Shared aggregate evidence:
   - stored in tracked files such as `usage/usage-aggregate.yaml`;
   - includes subject type, subject ID, month, agent, hashed machine ID, outcome counts, and last-used date;
   - excludes raw prompt text, project names, transcripts, and detailed notes.

Review scripts should use aggregates as their primary input. Raw logs are evidence sources for local audit, migration, or aggregate rebuilds.

When recording usage, update local raw evidence first, then update or rebuild the aggregate. When exporting portable snapshots, include aggregates and exclude raw local evidence.

## Watch Out For

Do not treat aggregate counts as final truth about quality. They are review signals. Low usage means investigate, not automatically deprecate.

Do not store unhashed machine names or raw session notes in shared aggregate files.

Do not remove legacy logs until their useful information has been migrated or summarized.

## Related Practices

- [[RUNTIME-002]]
- [[RUNTIME-003]]
- [[META-006]]
- [[META-010]]
