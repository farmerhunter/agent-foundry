---
id: PROD-002
title: Design onboarding as an end-to-end activation journey
domain: product
type: checklist
status: active
version: 2
created: 2026-06-11
updated: 2026-08-10
tags: [product, onboarding, activation, lifecycle, user-journey, harvest, capability-boundary]
aliases:
  - PROD-002
  - onboarding is an activation journey
  - first-run setup needs an end-to-end path
  - design onboarding by user scenario
related: [ARCH-006, ARCH-007, GOV-006]
applies_when:
  - designing onboarding, first-run setup, installation, migration, bootstrap, or rehydration flows
  - a plan lists schemas, scripts, docs, or install steps before naming the user scenario
  - a system has multiple layers or stores that a new user must understand before productive use
review_required: false
provenance: "Harvested from AF5 capability-pack and onboarding design discussion on 2026-06-11; extended after AF18 candidate/Harvest and native onboarding boundary review on 2026-08-10."
---

## Principle

Design onboarding as an end-to-end activation journey. Start from the user's complete path from blank or unfamiliar state to a verified usable workflow, then derive scripts, schemas, packs, docs, checks, and runtime install steps from that path.

Start with the user-visible workflow rather than a storage or index proposal. For an experience such as learning or Harvest, verify the path from source history through candidate review and durable practice publication before treating candidate records, cursors, indexes, or shadow stores as the product. Keep Core capability, trusted evidence, native host support, and runtime activation as separate states in the walkthrough.

## Rationale

Onboarding work often drifts into scattered implementation deliverables: a schema here, a setup script there, a paragraph in docs, and a validation check somewhere else. Those pieces can all be correct while the user still lacks a coherent installation experience. A complete activation journey keeps the product goal visible: the user should know what was installed, where their canonical data lives, what was enabled, what remains manual, how to verify success, and what to do next.

## Guidance

For onboarding or first-run work, define the scenario before designing technical pieces:

1. **Starting state**: blank user, existing user on a new machine, migrated user, imported runtime user, or project-local capability incubation.
2. **User intent**: what useful workflow the user expects to perform after setup.
3. **Canonical locations**: where product code, user records, generated output, runtime copies, and local private state live.
4. **Required bootstrap**: which mandatory content or setup steps are needed before the system is usable.
5. **Optional choices**: which packs, runtimes, integrations, or imports are optional.
6. **Verification**: what status, receipt, smoke test, or first command proves the setup worked.
7. **Failure recovery**: what the user sees when setup is partial, ambiguous, or unsafe.
8. **Next action**: the first normal workflow the user can run after onboarding.

Treat a setup command as complete only when it can report the activation state in user terms, not only in file-write terms.

## Use This When

- Planning first-run setup for a new product or CLI.
- Splitting product Core from user data or local runtime state.
- Designing bootstrap packs, optional packs, imports, or migrations.
- The user asks whether the current plan covers the real installation experience.
- A roadmap stage is about onboarding, deployment, migration, or user activation.

## Watch Out For

- Do not let implementation nouns become the onboarding plan.
- Do not claim onboarding is solved because individual commands exist.
- Do not require users to understand internal layers before the setup flow has shown them the relevant paths and states.
- Do not hide manual targets, skipped runtimes, or partial activation behind a generic success message.
- Do not design only for the maintainer's current machine when the scenario is external-user onboarding.

## Example

For Agent Foundry AF5, a complete onboarding path is not just "add a capability pack schema." The path should cover installing Core, creating or selecting a User Vault, deploying the mandatory bootstrap pack, optionally importing a multi-agent workflow pack, refreshing runtime adapters, reporting ChatGPT manual-import status, verifying receipts, and showing the first normal command the user can run.

## Activation

- Tier: task_router
- Phases: product_planning, onboarding_design, migration_design, release_review
- Signals: first-run setup, install flow, bootstrap, onboarding, migration, capability pack deployment, runtime refresh
- Evidence: plan or final report names the starting state, activation path, verification signal, failure recovery, and next usable workflow

## Related Practices

- [[ARCH-006]]
- [[ARCH-007]]
- [[GOV-006]]
