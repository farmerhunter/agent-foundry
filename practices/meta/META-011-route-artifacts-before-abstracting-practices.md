---
id: META-011
title: Route artifacts before abstracting practices
domain: meta
type: heuristic
status: active
version: 1
created: 2026-06-08
updated: 2026-06-08
tags: [harvesting, artifact-routing, practice-governance, review]
aliases:
  - META-011
  - route artifacts before practices
  - do not convert every insight into a practice
related: [META-002, META-006, META-008, META-013]
applies_when:
  - running a harvest practices workflow
  - extracting lessons from session notes or handoff dumps
  - deciding whether a session insight belongs in practices
review_required: false
provenance: "Corrected harvest outcome from ChatGPT memory-system design and harvest discipline discussion; source context: docs/memory-system-handoff-dump.md."
---

## Principle

In any `harvest practices` task, perform artifact routing before drafting practice candidates. Do not convert every important session insight into a practice.

## Rationale

The failed harvest converted important memory-system design content directly into practices without first deciding whether each item was research output, design evidence, future architecture, a project-local decision, or a generalized practice.

## Guidance

Before abstracting a lesson, route the source artifact into one of these classes:

- evidence only;
- design note;
- research/reference material;
- project-local decision;
- workflow update;
- practice candidate;
- skill/asset candidate;
- adapter update;
- discard.

Only items routed to `practice candidate` should continue through practice drafting. Items routed elsewhere may still be important, but they need a different canonical destination, review path, or no write at all.

## Use This When

- The user says `harvest practices`, `extract lessons`, `turn this session into foundry entries`, or equivalent.
- A session contains a mix of research, design, user corrections, future architecture, workflow feedback, and reusable agent rules.

## Watch Out For

- Do not treat importance as evidence that something is a practice.
- Do not create practice entries for research notes, domain design details, project-local decisions, or future-system concepts.
- Do not invent destination directories or schemas during routing.

## Example

A memory-system design session may contain a useful taxonomy for research memos. If the current repository has no implemented research-memo substrate, route that taxonomy as design or research evidence, not as a general Agent Foundry practice.

## Activation

- Tier: workflow_embedded
- Phases: harvest, import, review, before_candidate_drafting
- Signals: harvesting mixed session content; important insights include research, design, local decisions, future architecture, or workflow feedback
- Evidence: harvest output shows artifact routing before practice candidates are drafted

## Review Notes

- Human approval: approved on 2026-06-08.
- Failure prevented: practice vault pollution by research notes, domain design details, project-local decisions, and future-system concepts.

## Related Practices

- [[META-002]]
- [[META-006]]
- [[META-008]]
- [[META-013]]
