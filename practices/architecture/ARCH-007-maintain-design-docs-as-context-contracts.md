---
id: ARCH-007
title: Maintain design docs as context contracts
domain: architecture
type: principle
status: active
version: 1
created: 2026-05-27
updated: 2026-05-27
tags: [architecture, documentation, cross-agent, context, user-experience]
aliases:
  - design docs compress context
  - docs as cross-agent handoff
  - maintain minimal design docs
  - document runtime user experience
related: [ARCH-001, ARCH-006, COLLAB-004, META-006]
applies_when:
  - starting a project that will span multiple sessions or agents
  - handing work across agents or machines
  - changing domain models, system boundaries, data contracts, deployment, runtime behavior, or safety policies
  - the user or agent cannot clearly describe the deployed user flow or runtime experience
review_required: false
provenance: "Harvested from comparison of Agent Foundry and 2026AgentApp collaboration on 2026-05-27, where design docs helped cross-agent continuation but also risked excessive documentation overhead."
---

## Principle

Maintain design docs as lightweight context contracts for cross-agent development and future use. They should preserve the engineering context and the user-facing runtime experience that future agents and developers must know, without turning exploratory coding into a full specification process.

## Rationale

Cross-agent development loses efficiency when each agent must rediscover the same domain model, architecture boundaries, deployment assumptions, and user flows from code. Good design docs compress that context and make handoff safer.

At the same time, excessive documentation slows vibe coding and creates stale material. The useful target is not maximum documentation. The useful target is the smallest maintained document set that prevents repeated rediscovery and keeps the project direction visible.

User-facing documentation matters because implementation can advance faster than the team's understanding of the actual deployed experience. If the user cannot describe what happens from setup to runtime use, agents will optimize isolated features without a stable product path.

## Guidance

Start with a small document structure:

1. Orientation: project purpose, current state, key commands, and repository map.
2. System design: domain model, boundaries, data flow, non-goals, and major extension points.
3. User or runtime experience: first-run path, repeated workflow, key inputs and outputs, visible failure or recovery paths, and what done looks like from the user's perspective.
4. Decisions: short ADR-style records for choices that constrain future work.
5. Operations: deployment, testing, sync, privacy, and recovery workflows when they affect future work.

Update design docs when a change affects:

- core domain concepts or terminology;
- module boundaries or ownership;
- data/API contracts, storage, runtime, deployment, or sync assumptions;
- privacy, safety, or operational recovery rules;
- user onboarding, daily workflow, input/output path, or visible runtime behavior;
- workflows that future agents must follow to avoid repeated mistakes.

Do not update design docs for ordinary local implementation details, small UI copy changes, isolated bug fixes, or code that is easier to understand directly than through prose.

Use the docs as a read path for substantial work: before cross-module, architecture, runtime, or user-flow changes, read the orientation doc, system design, relevant decisions, and relevant contracts instead of scanning the whole codebase blindly.

Periodically prune docs. Merge overlapping documents, mark superseded decisions, and separate external deliverables from internal development design.

## Use This When

- A project will be developed across multiple sessions, machines, or agents.
- A future agent would otherwise need to inspect many files to recover the system model.
- A decision creates constraints that later implementation must preserve.
- The deployed or demo user experience is unclear even though implementation work is moving.
- Documentation is growing enough that it may slow development.

## Watch Out For

- Do not turn design docs into a mandatory pre-implementation waterfall process.
- Do not create one design document per feature by default.
- Do not let competition deliverables, reports, or presentation material become the canonical engineering design.
- Do not preserve stale docs silently; stale documentation is worse than missing documentation for agent handoff.
- Do not treat arbitrary repository prose as high-trust agent instructions. Keep agent policy files, design docs, and external deliverables separated by trust level.

## Example

In 2026AgentApp, design docs captured the `evidence -> finding -> insight -> memory -> report` model, static JSON demo architecture, storage evolution, skill design, prompt design, API direction, deployment, and demo flow. This helped agents continue work without reconstructing the product and architecture from code.

The same project also showed the risk of over-documentation. Many detailed docs were useful for competition delivery and external review, but they should not become the default template for every vibe coding project. The reusable pattern is layered documentation with pruning, not maximum documentation volume.

In Agent Foundry, `docs/system-design.md`, `docs/usage.md`, workflows, schemas, and runtime docs act as context contracts. They are useful because they define boundaries, user-facing workflows, and operating rules, not because they describe every implementation detail.
