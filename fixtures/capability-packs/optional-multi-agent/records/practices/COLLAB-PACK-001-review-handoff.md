---
id: COLLAB-PACK-001
title: Role-Generic GitHub Handoff Routing
domain: agent-collaboration
type: checklist
status: candidate
version: 4
created: 2026-06-11
updated: 2026-07-06
tags: [multi-agent, review, handoff, scheduler, readiness, testing-contract, action-plan]
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
- Prefer read-only inbox, ready-queue, pickup, handoff, audit, Testing Contract, and collaboration readiness dry-runs before write automation.
- Route explicit testing evidence through Testing Contracts when the issue or risk profile asks for Tester support. Tester evidence supports Reviewer and Architect decisions; it is not final acceptance by itself.
- For new projects, run collaboration readiness before relying on multi-agent routing. Check role labels, routing templates, Execution Contracts, Testing Contracts when needed, and optional Project/Kanban mirror fields.
- For existing projects, use collaboration readiness to report drift and safe next actions. User-facing reports should include `readiness_status`, `summary`, `user_readiness_action_plan`, and `recommended_next_actions`; raw JSON remains evidence/debug output.
- Use action categories exactly: `informational_only`, `agent_handled_existing_workflow`, `explicit_human_gate`, and `unsupported_deferred_repair_apply`.
- Dry-run repair plans may name missing labels, malformed contract values, Project item drift, or missing Project fields, but they must keep `mutation_performed: false` and `apply_supported_now: false`.
- Treat TLS, EOF, timeout, rate-limit-like, and unavailable Project v2 responses as degraded sources. Return partial reports with `unknown` or `not_available` instead of inferring hidden state.
- Keep Project status and roadmap status as mirrors or reports unless a project explicitly configures them as managed outputs. Project v2 is not scheduler authority for this pack.
- Treat project-specific repository names, Project ids, branch names, issue numbers, and status mappings as overlays, not reusable pack defaults.

## Boundaries

- Do not run default full Project scans for ordinary collaboration reads.
- Do not apply dry-run repairs from this pack.
- Do not treat collaboration readiness action plans as live repair/apply authorization.
- Do not publish generated Skills, install runtime helpers, or mutate Project v2 from pack deployment.
- Keep selected User Vault records canonical after deployment; generated adapters, runtime receipts, and local helper outputs remain downstream evidence.
