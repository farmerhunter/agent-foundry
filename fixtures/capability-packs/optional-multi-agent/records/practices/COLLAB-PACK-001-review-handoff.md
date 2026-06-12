---
id: COLLAB-PACK-001
title: Role-Generic GitHub Handoff Routing
domain: agent-collaboration
type: checklist
status: candidate
version: 2
created: 2026-06-11
updated: 2026-06-12
tags: [multi-agent, review, handoff, scheduler]
aliases: [COLLAB-PACK-001]
review_required: true
---

## Principle

Multi-agent GitHub work should route through explicit role labels, durable comments, and Execution Contract fields rather than relying on transient chat history or Project board status.

## Rationale

Multi-agent work loses continuity when completion evidence lives only in a chat thread. A project-local helper suite can make handoff faster, but the reusable rule is the role-generic coordination model: `needs:<role>` labels identify the next actor, comments preserve context, and Project status remains a visual mirror rather than the scheduler source of truth.

## Guidance

- Use one primary `needs:<role>` next-action label unless the issue contract explicitly allows parallel actors.
- Put pickup and handoff evidence on durable issue and PR surfaces when a PR exists.
- Include scope, verification commands and outcomes, residual risks, and the expected next role.
- Parse explicit Execution Contract fields for owner role, review role, acceptance role, dependency gates, branch strategy, and completion handoff.
- Prefer read-only inbox, ready-queue, pickup, handoff, and audit dry-runs before write automation.
- Keep Project status and roadmap status as mirrors or reports unless a project explicitly configures them as managed outputs.
- Treat project-specific repository names, Project ids, branch names, issue numbers, and status mappings as overlays, not reusable pack defaults.
