---
id: META-013
title: Apply a generalization gate before promoting insights into practices
domain: meta
type: checklist
status: active
version: 1
created: 2026-06-08
updated: 2026-06-08
tags: [harvesting, generalization, practice-governance, dedupe]
aliases:
  - META-013
  - generalization gate
  - practice candidates must generalize
related: [META-002, META-011, META-012, GOV-003]
applies_when:
  - converting a session insight into a practice candidate
  - reviewing harvest output for over-specific entries
  - deciding whether to create, merge, defer, or reject a candidate
review_required: false
provenance: "Corrected harvest outcome from ChatGPT memory-system design and harvest discipline discussion; source context: docs/memory-system-handoff-dump.md."
---

## Principle

A session insight must pass a generalization gate before becoming a practice candidate.

## Rationale

The earlier harvest generated too many memory-system-specific design points as practices. Agent Foundry practices should be reusable, reviewable, and deployable across work contexts.

## Guidance

Before drafting or promoting a practice candidate, ask:

- Would this help in unrelated future work?
- Would it help more than one agent or runtime?
- Does it describe a repeatable judgment or process?
- Can it be triggered operationally?
- Is it independent of the current domain's vocabulary?
- Is it more than a local design decision?
- Can it be reviewed and maintained as a durable rule?

If the answer is weak, route the item to a better artifact class, merge it into an existing entry, defer it, or list it as rejected-as-practice.

## Use This When

- A harvest contains many interesting but domain-specific insights.
- A candidate depends on a future architecture that is not implemented.
- A proposed rule sounds useful only inside the session's immediate domain vocabulary.

## Watch Out For

- Do not confuse "important" with "generalizable."
- Do not create durable rules that are hard to activate or maintain.
- Do not skip duplicate search after a candidate passes the gate.

## Activation

- Tier: workflow_embedded
- Phases: harvest, import, review, candidate_drafting
- Signals: session contains many interesting insights; a candidate depends on domain vocabulary, local decisions, or future architecture
- Evidence: harvest output records gate results or rejected-as-practice reasons before canonical drafting

## Review Notes

- Human approval: approved on 2026-06-08.
- Failure prevented: practice vault expansion with local design rules that are hard to activate or maintain.

## Related Practices

- [[META-002]]
- [[META-011]]
- [[META-012]]
- [[GOV-003]]
