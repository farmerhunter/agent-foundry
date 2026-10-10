---
id: COLLAB-016
title: Use bounded collaboration by default
domain: agent-collaboration
type: playbook
status: active
version: 3
created: 2026-08-05
updated: 2026-08-26
tags: [agent-collaboration, bounded-collaboration, work-contract, handoff, privacy, harvest, scope-lock, capability-boundary, external-blocker, decision-relevance]
aliases:
  - COLLAB-016
  - bounded collaboration by default
  - contract-driven collaboration control plane
  - converge on a non-substitutable external blocker
related: [COLLAB-008, COLLAB-009, COLLAB-010, COLLAB-012, COLLAB-015, TEST-005, META-002]
applies_when: A project already uses multi-agent collaboration and needs predictable default coordination without a separate product opt-in.
review_required: true
provenance: AF18 #426 Human-approved active canonical practice; selected adapters have been published. v2 approved through AF18 #524 harvest review on 2026-08-10. v3 approved through V2-HARVEST-R1 on 2026-08-26 after #556 showed that repeated same-host evidence cannot replace a physically distinct device prerequisite; future substantive changes remain subject to Human harvest-practices review.
---

## Principle

Use a bounded Work contract as the default way to coordinate multi-agent work. Keep one active Work per logical objective, make ownership and role binding explicit, and preserve a small privacy-safe terminal handoff for Human review and later harvest.

For a project that is not yet prepared, route explicit one-time setup through [[COLLAB-017]] before relying on this daily default.

## Rationale

Unbounded dispatch makes duplicate work, ambiguous ownership, and silent continuation easy. A small contract gives existing collaboration workflows predictable stopping points without claiming unavailable runtime telemetry or automatic enforcement.

## Guidance

- Bind every Work to its root contract, logical objective, owner, role, and durable scheduler record before dispatch.
- Allow only one active Work for the same logical objective. Check durable scheduler state before dispatching; hold the duplicate rather than starting parallel work.
- Use explicit `hold` or `disable` state for ambiguity, failed gates, missing authority, or unavailable capability. Do not auto-resume held Work.
- When work must continue, create a logical successor packet that names the predecessor, preserved scope, owner, next gate, and stop condition. A successor is a scheduler record, not a native runtime continuation.
- End each Work with a concise WorkSummary and, when Human attention is needed, an AttentionSummary. Summaries must state outcome, evidence, open gate, next owner, and residual risk.
- Preserve a privacy-safe terminal handoff only: scope, durable links or identifiers, decision/evidence summary, capability state, and next action. Do not retain raw transcript content, secrets, private tool output, or user data.
- A terminal handoff may produce `candidate_hold` material for Human review through `harvest-practices`. It is not an automatic Harvester invocation, canonical Vault write, adapter publish, runtime activation, or policy update.
- Report unavailable measurements literally as `unavailable` or `not_exposed`. Do not infer token use, model mapping, context age, or trusted runtime metrics from dispatch requests or ledger estimates.
- Keep one Work tied to one user-visible objective. Separate Core, Vault, adapter/generated, host/connector, Project, runtime activation, evidence, and Harvest lanes in the root contract; a held or unavailable lane must not silently expand the Work.
- When current in-scope implementation and evidence are complete and the only missing proof depends on a non-substitutable external prerequisite, publish one durable resume condition and move the Work to an honest hold. Name the missing device, account, credential, operator, environment, or authority fact without inventing a substitute.
- After that convergence, do not create repeated contracts, same-environment permutations, evidence-polishing reruns, or speculative implementation merely to keep the Work moving. Resume only when the named external condition changes; a new internal defect may open separate bounded work, but it does not erase the external hold.

## Activation

- Tier: task_router
- Phases: collaboration intake, dispatch, completion handoff, Human review
- Signals: multi-agent issue work, role dispatch, duplicate-risk objective, hold/disable event, non-substitutable external prerequisite, terminal handoff
- Evidence: durable scheduler record, Work/root contract, ownership binding, terminal summary, one explicit resume condition for an external hold, and any Human harvest decision

## Watch Out For

- This practice does not create runtime enforcement, trusted metrics, automatic continuation, automatic harvesting, automatic Vault writes, adapter publication, runtime activation, or auto-tuning.
- A proposed practice is not published into default adapters until Human approval changes its lifecycle state and the approved publish step is completed.
- `degraded`, `held`, `unavailable`, and `not_exposed` remain real capability or failure-state terms; do not hide them with product language.
- Do not weaken a Hard Boundary, relabel missing external proof as a residual, or auto-resume merely because substitute tests are green.

## Example

Before starting implementation for one issue, the Coordinator records the Work/root contract and owner. If an equivalent Work is already active, the new request is held. At completion, the owner posts a short evidence-backed WorkSummary. A sanitized `candidate_hold` can then be presented to a Human in the normal harvest review list; nothing is written to the canonical Vault until that review authorizes it.

## Review Notes

This AF18 #426 practice is active and published to the selected adapters following Human approval. Future substantive changes remain subject to review before activation or publication.

## Related Practices

- [[COLLAB-008]]
- [[COLLAB-009]]
- [[COLLAB-010]]
- [[COLLAB-012]]
- [[COLLAB-015]]
- [[TEST-005]]
- [[META-002]]
