---
id: COLLAB-015
title: Describe user-facing capability before behavior acceptance or milestone closure
domain: agent-collaboration
type: checklist
status: active
version: 7
created: 2026-06-17
updated: 2026-08-10
tags: [agent-collaboration, milestone, epic, closure, user-facing, verification, human-gate, ux, activation, runtime]
aliases:
  - COLLAB-015
  - milestone closure needs user-facing capability summary
  - Epic closure user-facing note
  - closure note explains capability and usage
  - behavior acceptance needs user-facing trial path
  - meaningful UX gate before merge or closure
  - capability closure requires activation evidence
  - design acceptance is not capability completion
  - implementation gates required before readiness closure
related: [COLLAB-006, COLLAB-011, TEST-005, PROD-003]
review_required: false
provenance: "Harvested from tiny-ipa #146 on 2026-06-17, where the user corrected the workflow before Epic closure to require a final-user or adopter-facing explanation of capability, usage, verification, exclusions, and residual risks; v2 refined after tiny-ipa M7 dogfood to require meaningful human-facing behavior or UX gates before acceptance when needed; v3 refines AF10-B gate wording so live human approval requests include review points; v4 adds activation evidence after AF11 Core implementation was closed before Codex runtime enablement and target-thread trial; v5 adds UX-complete actionability after AF15 was reopened because a readiness audit without actionable next steps was not a complete adopter experience; v6 adds V2 capability-closure discipline after #294/#298 design gates were briefly conflated with implemented local-first orchestration capability, requiring held implementation gates #359-#362 before #299 readiness; v7 adds AF18 separation of capability, evidence, activation, and host support."
---

## Principle

Before accepting a user-visible behavior change or closing a milestone/Epic, publish a durable note from the final user's or adopter's point of view. The note must explain what capability now exists, how it is used or tried, what was verified, what remains excluded, and whether a human trial or product judgment is still required. For runtime, tooling, helper, or workflow capabilities, do not treat Core implementation as closure unless deployment, enablement, and target-environment trial evidence are complete or explicitly deferred to an open follow-up gate. For roadmap capabilities, do not treat accepted design gates as implemented capability closure; readiness must wait for the required implementation gates or an explicit Human-gated deferral.

Report four separate states in the closure note: capability implemented, trusted evidence observed, host/connector support verified, and runtime or adopter activation completed. A `current` implementation with `unavailable`, `not_exposed`, or separately held activation evidence is still a valid bounded release when the exclusions and follow-up owner are explicit; do not keep the whole capability blocked merely to obtain a nonessential higher-tier proof.

## Rationale

Issue checklists, PR merges, test runs, and agent audit results prove process state. They do not necessarily prove that the completed work is understandable, usable, or acceptable to the people who will benefit from it.

This gap is easy to miss in multi-agent work because child issues can all be technically complete while the parent milestone still lacks a coherent answer to:

- What can a user or adopter do now?
- How do they start, try, or adopt the capability?
- Which workflow or scenario was actually verified?
- What is still intentionally out of scope?
- What follow-up gate owns the remaining risks?

Without that closure note, a milestone can be administratively closed while product, workflow, or adoption readiness remains ambiguous.

The same problem can occur before milestone closure. A PR can pass tests and review while changing user behavior in a way that still needs human product judgment. In that case, the right gate is not "approve merge"; it is a concrete trial path and acceptance question.

A similar failure appears when a reusable capability is implemented in Core but not activated where the user expects to use it. A helper script can exist, tests can pass, and a generated note can describe it, while the target runtime, new thread, or adopting project still cannot invoke it. In that case the honest state is `implementation complete, activation pending`, not milestone closed.

For audit, readiness, review, or migration-helper milestones, another failure mode is stopping at diagnostic output. A report that lists findings is not a complete adopter experience unless the user can tell what to do next, which actions are safe now, which require human gates, which are unsupported/deferred, and what remains read-only evidence.

For architecture-heavy milestones, the opposite-looking failure is also common: the team accepts solid designs and closes design issues, then the roadmap starts to read as if the user-facing capability exists. Design acceptance is valuable evidence, but it is not durable storage, replay, sync-plan generation, runtime activation, or a usable workflow. The parent readiness gate must remain open until those implementation slices are completed, or until a Human-gated scope decision explicitly defers them.

## Guidance

Before accepting a user-visible behavior/UX change, or before closing a milestone or Epic:

1. Identify the real audience for the closure note:
   - end user for product features;
   - developer/operator for setup, API, tooling, or runtime work;
   - adopting repo owner, Architect, Implementer, or Reviewer for workflow/helper migrations.
2. Write a durable issue comment, PR comment, Human Decision Contract, or release note that covers:
   - completed user-facing function or operational capability;
   - who uses it and when;
   - how to start, try, configure, or adopt it;
   - what changed from previous behavior;
   - primary path or workflow verified;
   - alternate paths, empty/error states, or smoke scope covered when relevant;
   - whether the remaining decision is objective verification or subjective product/UX acceptance;
   - explicit exclusions and deferred work;
   - residual risks and why they do not block closure;
   - next milestone, migration issue, or human gate if the work continues elsewhere.
   - for readiness or audit helpers, the user-facing action categories, safe next actions, forbidden actions, and deferred apply/repair boundary.
3. For runtime, tooling, helper, adapter, skill, or workflow capabilities, add activation evidence before closure:
   - the publish, deploy, install, enable, or refresh step that makes the capability available to the intended audience;
   - the target environment where it was tried, such as a new Codex thread, another project directory, a generated adapter, a CLI wrapper, or an enabled runtime;
   - the smoke path that proves the intended audience can actually invoke or benefit from the capability;
   - the user-facing enablement instructions that explain how to trigger it and how to confirm it is active.
4. If any activation evidence is missing, keep the parent issue, Epic, or milestone open, or create and link an explicit activation-pending follow-up before claiming closure. The closure note may say `implementation complete`, but must not imply `activation complete`.
5. If accepted design work identifies implementation required for the user-facing capability, create or update explicit implementation gates before readiness:
   - name the concrete missing runnable capability, such as storage/replay, backfill, board rendering, sync-plan generation, adapter publish, or runtime apply;
   - keep those gates held or routed according to dependencies instead of silently folding them into a completed design issue;
   - update the parent roadmap/Epic so design gates, MVP slices, implementation gates, and final readiness are visibly separate;
   - keep final readiness held until the implementation gates are accepted, or until the user explicitly approves a scoped deferral.
6. Link concrete evidence:
   - walkthrough, smoke test, verification command, PR, issue checklist, or review comment;
   - browser screenshots or traces for workflow-heavy frontend features when available;
   - setup or adoption docs for tooling/runtime work.
7. If human manual verification is required, stop and surface the trial path plus the exact acceptance question in the live response; do not use a generic final merge request as the gate.
8. For adopter-facing tooling, run or request at least one real adopting-project trial when the value depends on practical interpretation of the output. A fixture can prove shape; a dogfood trial proves whether the output helps a maintainer decide what to do.
9. Only then merge, accept, or close the issue/milestone/Epic according to normal permission and readiness checkpoints.

For milestone, Epic, or behavior gates that need human approval, the live response must make the gate reviewable without forcing the human to open the durable comment first. Summarize the adopter-facing capability, trial or use path, verification, exclusions, residual risks, choices, consequences, and exact approval phrase or trial response.

For frontend or workflow-heavy product milestones, the note should summarize the scenario contract and walkthrough outcome. For non-UI tooling or migration-readiness Epics, write from the adopter's point of view rather than pretending there is an app end user.

For small behavior fixes, the note can be brief, but it must still answer what changed, how to try it, and whether human trial is needed. If automated walkthrough evidence fully covers the acceptance criteria and the change is low-risk, the note may state that no human trial is required and why.

## Use This When

- Closing a GitHub milestone, roadmap stage, or parent Epic.
- Accepting an Epic integration branch as complete.
- Accepting a PR or child issue that changes user-visible behavior, workflow semantics, or UX.
- Deciding whether a user-facing behavior change needs human manual trial.
- Marking a migration-readiness, workflow, tooling, or runtime rollout Epic as done.
- Summarizing multi-agent dogfood evidence for a later adoption decision.
- A milestone has many green child issues but no concise user-facing story.

## Watch Out For

- Do not substitute a test list for the capability explanation. Tests are evidence; they are not the user story.
- Do not write only from the implementer's perspective when the audience is a learner, developer, operator, or adopting repo owner.
- Do not ask the human only to approve a merge when the real question is whether the behavior or UX feels right.
- Do not ask the human to approve closure or behavior acceptance without the key review points in the live response.
- Do not claim a user-facing behavior is accepted only because CI, typecheck, or unit tests passed.
- Do not close a workflow milestone while the closure note admits an unresolved in-scope primary path gap.
- Do not close a readiness or audit milestone when the user can see findings but cannot identify the next safe action, the required human gate, or the deferred unsupported action.
- Do not imply migration, rollout, or broad automation is complete when the milestone only establishes readiness or planning.
- Do not imply a local-first, sync, board, ledger, migration, or orchestration capability is complete because the design model was accepted.
- Do not close final readiness while newly discovered implementation gates remain open, unless a Human-gated scope decision explicitly defers those gates from the milestone.
- Do not imply a runtime, helper, adapter, skill, or workflow capability is enabled just because its Core implementation merged.
- Do not close a capability milestone while the target runtime, target thread, adopting project, or documented first-use path has not been tried, unless an explicit activation-pending issue remains open and owns that gap.
- Do not bury human-gated next steps only in child issue comments; surface them in the parent closure note.

## Example

In tiny-ipa #146, the helper dogfood work completed a migration-readiness evaluation rather than an app feature. The closure note therefore described the adopter-facing capability:

- repo owners and role threads can use GitHub issues, labels, PRs, and comments as durable scheduler state;
- helper migration is ready for staged planning, not broad execution;
- Unit A docs/config/templates should move before read-only/dry-run helpers;
- mutation helpers and Project v2 adapters remain separately gated;
- Tiny IPA-specific Project IDs, branch conventions, issue numbers, and broad `--apply` automation must not become Agent Foundry defaults.

That note was posted before closing #146 so the Epic recorded both process completion and adopter-facing meaning.

In Agent Foundry AF15, the collaboration readiness helper initially had implementation, tests, docs, and an optional capability-pack update, but the user correctly rejected closure because an audit result without a user-facing action plan was not a complete experience. The Epic reopened, added `readiness_status`, `summary`, `user_readiness_action_plan`, safe action categories, docs, and tiny-ipa dogfood evidence, then closed only after the adopter-facing path was understandable.

In Agent Foundry V2, #294 and #298 produced accepted designs for the Local Collaboration Ledger and GitHub Project sync model. That did not mean the user could develop from a durable local ledger or generate read-only Project sync plans. The V2 roadmap was corrected so #294/#298 remained design gates, #297 remained a GitHub-evidence-backed MVP slice, #359-#362 became held implementation gates, and #299 final readiness stayed open until those gates complete or are explicitly deferred by the user.

## Activation

- Tier: workflow_embedded
- Phases: milestone_review, Epic_acceptance, release_readiness, closure
- Signals: close Epic, close milestone, roadmap stage done, final closure, migration readiness, dogfood evaluation, all child issues complete, user-visible behavior change, UX acceptance, human trial needed, runtime helper activation, adapter publish, target-thread trial, design gate accepted, implementation gates discovered, final readiness blocked by unimplemented capability
- Evidence: durable issue/PR/parent comment or release note names the audience, capability, usage path, changed behavior, verification evidence, activation/deployment evidence when applicable, exclusions, residual risks, next gate, and whether remaining gaps are implementation gates or explicitly Human-deferred scope

## Related Practices

- [[COLLAB-006]] — verify completion against the original task, including non-code deliverables
- [[COLLAB-011]] — parent Epic closure has different branch and readiness boundaries than child issue closure
- [[TEST-005]] — prove the user-facing path rather than only process startup
- [[PROD-003]] — workflow milestones need scenario contracts and walkthrough evidence
