---
id: GOV-001
title: Protect canonical source of truth
domain: governance
type: principle
status: active
version: 1
created: 2026-05-28
updated: 2026-05-28
tags: [governance, source-of-truth, derived-data, maintainability]
aliases:
  - GOV-001
  - do not create a second source of truth
  - derived views must stay derived
related: [META-001, META-006, ARCH-007]
applies_when:
  - creating indexes, summaries, generated files, views, caches, docs, or exports from existing data
  - adding a second representation of data that already has a canonical owner
  - deciding whether a document, schema, config, or generated artifact should be edited by hand
  - improving tool compatibility without changing the underlying product or system behavior
review_required: false
provenance: "Extracted from the Obsidian rollback lesson on 2026-05-28."
---

## Principle

Protect the canonical source of truth. In any project, derived views, generated artifacts, agent notes, summaries, caches, and compatibility files must not become a second hand-maintained truth source.

## Rationale

Duplicate truth sources create silent drift. They look helpful at first because they make a tool or workflow easier to use, but every future change must update multiple locations. Once agents or humans forget one of them, the project loses trust in its own records.

## Guidance

Before adding a new file, view, index, export, or generated artifact, identify:

- the canonical owner;
- whether the new artifact is canonical or derived;
- how derived artifacts are regenerated;
- whether consistency is checked automatically;
- who is allowed to edit the artifact by hand.

If the artifact is derived, make it generated, checked, or clearly non-authoritative. Prefer improving schema, validation, or generation paths over adding another manually maintained representation.

## Watch Out For

Do not justify duplicate truth sources by saying they improve readability in one tool. Tool-specific views are allowed only when they are generated from the canonical source or have a clear non-authoritative role.

Do not let agent session conclusions replace project-owned durable records such as schemas, ADRs, migrations, API contracts, design docs, or canonical indexes.

## Activation

- Tier: always_preflight
- Phases: planning, before_edit, before_new_file, review
- Signals: creating derived views; adding a second representation; generating indexes, summaries, caches, exports, or compatibility files; deciding whether a file is canonical or derived
- Evidence: final report identifies the canonical owner and whether any new artifact is canonical, derived, generated, or non-authoritative

## Related Practices

- [[META-001]]
- [[META-006]]
- [[ARCH-007]]
