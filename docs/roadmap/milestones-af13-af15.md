# Roadmap Milestones AF-13 Through AF-15

This file contains detailed AF-13 through AF-15 milestone plans moved out of `docs/roadmap.md` to keep the main roadmap readable.

Return to the main roadmap: ../roadmap.md

### AF-13: External Skills Import And Reference Workflow
Goal: support the independent external-skills use case before the public `v1.0.0` release.

This work is tracked as GitHub milestone `AF-13: External Skills Import and Reference Workflow` with Epic #286 and child issues #276 through #281.

Current scheduler state: the human hold is lifted, #276 is accepted as the completed planning/decomposition record, and #277 is the active next issue.

Why it is an independent AF milestone:

- Agent Foundry already exposes `import skill <source>` to users.
- External skills, prompt packs, articles, repos, and local skill folders can be valuable, but they are reviewed inputs rather than authorities.
- Users need a clear review result: discard, reference-only, defer, merge into existing, propose practice, propose asset, or publish after approval.
- Reference-only material must be searchable or manually useful without becoming active practice/asset authority or adapter output.

Planned issue sequence:

1. #276 plan end-to-end import, reference, and user-facing workflow hardening.
2. #277 define outcome taxonomy and reference-only contract.
3. #278 harden import workflow and review packet template.
4. #279 add user-facing import/reference workflow docs.
5. #280 add fixture-backed validation for import outcomes.
6. #281 run final readiness walkthrough for the import/reference workflow.

Acceptance criteria:

- External-skill import has a complete lifecycle from source review through approval, canonicalization, adapter publish, and verification.
- User-facing docs explain when to import, what the report means, what approval changes, and what remains blocked.
- Script-bearing or unsafe external material remains inert unless explicitly reviewed and approved.
- Fixture coverage proves safe public skill, local folder, script-bearing skill, duplicate practice, reference-only material, unknown/unsafe license, and prompt-injection cases.
- No real external skill import, external script execution, Vault/private/runtime/generated mutation, generated adapter publish, capability-pack operation, or memory-system work occurs without a later reviewed issue and explicit authorization where required.

### AF-14: Tester Role And Test Planning Workflow

Goal: make testing a first-class collaboration workflow so complex user-visible or stateful work has a clear test plan, evidence taxonomy, automation boundary, and human-trial boundary before acceptance.

AF-14 is V1.x maintenance. It is not V2 local-first orchestration, and it does not authorize memory-system work.

Accepted outputs:

- Tester role boundary: Tester plans and gathers evidence, but does not replace Implementer, Reviewer, Architect, or Human approval.
- Testing Contract model for risk, expected evidence, fixture provenance, route-mock versus real-backend coverage, negative/adversarial checks, and residual risk.
- Scheduler support for `needs:tester` and Project Owner Role=Tester where a task explicitly needs testing evidence.
- Workflow docs and helper validation for Testing Contract and malformed role handoff cases.
- Bounded readiness/pilot evidence proving the role improves confidence without making Tester mandatory for every issue.

Current GitHub records:

| Record | Purpose | Status |
| --- | --- | --- |
| #302 | AF-14 Epic for Tester role and test planning workflow. | Done |
| #303 | Tester role and workflow gates decision. | Done |
| #304 | Testing Contract and evidence taxonomy decision. | Done |
| #305 | Scheduler and Project workflow support decision. | Done |
| #306 | Workflow docs and templates implementation. | Done |
| #307 | Helper validation and fixtures implementation. | Done |
| #308 | Readiness and pilot review. | Done |

Acceptance criteria:

- Users can ask for test planning or a tester pass in plain language.
- Test evidence states what was tested, why it is enough, what remains risky, and whether human trial is still required.
- Tester output supports review and acceptance decisions without becoming approval authority.
- Scheduler labels, Project role options, docs, templates, helper validation, and fixture tests are aligned.
- No V2 or memory-system work is introduced.

### AF-15: Collaboration Readiness And Action Workflow

Goal: make multi-agent collaboration setup auditable and actionable for both new repos and existing GitHub-first projects, without introducing live repair/apply or V2 local-first orchestration yet.

AF-15 is V1.x maintenance. It improves the current GitHub collaboration workflow and prepares evidence shape for V2 migration/backfill, but GitHub Project remains an optional visual/sync surface rather than the source of truth.

Accepted outputs:

- Collaboration readiness model covering labels, role routing config, Execution Contracts, Testing Contracts, human gate boundaries, Project mirror status, and source-of-truth rules.
- Read-only `collaboration-readiness` helper output with `readiness_status`, summary, `user_readiness_action_plan`, `recommended_next_actions`, and raw JSON evidence/debug output.
- Low-cost GitHub access strategy: REST-first, targeted Project v2 GraphQL only when configured, bounded retry, degraded/unknown reporting, and no default full Project scan.
- Dry-run repair planning that keeps `mutation_performed: false` and `apply_supported_now: false`.
- User-facing docs explaining new-repo setup, existing-project audit, action categories, forbidden actions, and V2-compatible telemetry shape.
- `pack.multi-agent.optional` updated with collaboration readiness and action-plan guidance.

Current GitHub records:

| Record | Purpose | Status |
| --- | --- | --- |
| #314 | AF-15 Epic for collaboration readiness and action workflow. | Done |
| #315 | Collaboration readiness model and low-cost GitHub strategy design. | Done |
| #316 | Read-only collaboration readiness helper implementation. | Done |
| #317 | Dry-run repair plan and degraded access behavior. | Done |
| #318 | User-facing collaboration readiness docs. | Done |
| #319 | Tester readiness/dogfood evidence. | Done |
| #320 | Capability-pack enablement for multi-agent optional pack. | Done |
| #321 | Final AF-15 readiness and integration. | Done |
| #328 | UX-centered action workflow correction decision. | Done |
| #329 | User-facing readiness action-plan output. | Done |
| #330 | Collaboration readiness audit/action workflow docs. | Done |
| #331 | Final readiness rerun after UX correction. | Done |

Acceptance criteria:

- New repo users can ask for multi-agent collaboration setup and receive a safe action plan.
- Existing project users can audit drift and degraded GitHub/Project visibility without triggering live repair.
- Audit results map to real next actions: informational, agent-handled existing workflow, explicit human gate, or unsupported/deferred repair/apply.
- Reports preserve `mutation_performed: false`, `apply_supported_now: false`, Project v2 optional/degraded visibility, and no default full Project scan.
- The report shape can feed V2 telemetry/backfill later without starting V2 implementation.
- No live Project repair/apply, generated Skill publish, capability-pack deploy/apply, V2 implementation, or memory-system work is introduced.
