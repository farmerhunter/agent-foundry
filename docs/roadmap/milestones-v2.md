# Roadmap Milestones V2

Status: planning document
Updated: 2026-07-08
Scope: V2 local-first orchestration, Foundry Board, Local Collaboration Ledger, GitHub Project remote sync, and migration from existing GitHub-first projects.

## V2 Goal

V2 makes Agent Foundry a local-first orchestration system.

The user value is simple: a user should be able to see what work is happening, who owns it, what evidence supports it, what is blocked, what changed, and what should happen next without reconstructing state from scattered GitHub comments, Project columns, and Codex thread history.

GitHub Project remains useful, but it becomes a remote sync and collaboration surface. The durable orchestration record should live locally first, then sync outward in a controlled way.

## Product Principles

- Start from end-to-end user journeys before building storage or board features.
- Support both new projects and existing issue-driven projects.
- Build read-only visibility before write or sync automation.
- Treat design acceptance as a gate, not as capability completion. A V2
  capability is not complete until the user can run the relevant local-first
  workflow, inspect evidence, and understand next actions without relying on a
  design comment.
- Preserve GitHub issue and PR evidence as durable public collaboration records.
- Preserve Agent Foundry layer boundaries: Core, User Vault, Generated, Runtime, and Local Private.
- Keep memory-system work out of V2 unless a later explicit decision changes that.
- Make migration and backfill first-class work, not a cleanup afterthought.
- Treat testing as part of capability closure, not as final paperwork. Each
  implementation gate must carry focused automated tests, degraded-state tests,
  no-write assertions, and user-facing output checks; V2-7 then verifies the
  end-to-end journeys across those accepted slices.

## Branch Policy

V2 work uses `codex/v2-local-first-orchestration` as its integration branch.

Branch rules:

- V2 child branches should target `codex/v2-local-first-orchestration`.
- V2-only changes should not target `main` while V2 is incomplete.
- `main` remains the V1.x maintenance line and default target for backward-compatible harvest-driven Core updates.
- V2 should regularly forward-merge from `main` to absorb V1.x maintenance and harvest improvements.
- Do not merge V2 back to `main` until V2 readiness is accepted and a final human-gated integration decision approves it.

Release rules:

- V1.x tags are cut from `main`.
- V2.0.0 is cut only after V2 integration is accepted and merged through the final release gate.

## V2 Milestone Sequence

V2 uses separate design and implementation gates. Closed design issues such as
#294 and #298 are accepted architecture decisions; they do not by themselves
complete the user-facing capability.

| Milestone | GitHub records | Purpose | Status |
| --- | --- | --- | --- |
| V2-0 User Journey And UX Contract | #293 | Define the end-to-end experience before implementation: new project setup, existing project migration, day-to-day orchestration, review, recovery, sync, and completion. | Accepted design |
| V2-1 Telemetry Evidence Window | #266 | Collect meaningful telemetry across selected V2 work so ledger and board design are based on real coordination overhead rather than guesses. | Open evidence window |
| V2-2 Local Collaboration Ledger Design | #294 | Define the local durable event model for assignments, dispatches, evidence, reviews, approvals, merges, closures, blockers, and handoffs. | Accepted design |
| V2-2A Local Collaboration Ledger Storage/Replay | #359 | Implement local ledger event storage and replay so local state can become durable source-of-truth evidence. | Completed implementation |
| V2-3 Foundry Board Domain Model | #295 | Define board state, columns, filters, issue/project/thread relationships, and user-visible status without binding too early to UI implementation. | Accepted design |
| V2-4 Existing Project Migration And Backfill Design | #296 | Define how current GitHub-first projects become candidate local-first orchestration state with provenance and conflict handling. | Accepted design |
| V2-4A Existing Project Backfill Implementation | #360 | Produce read-only candidate local ledger events from bounded GitHub issue/PR/Project evidence. | Completed implementation |
| V2-5 Foundry Board GitHub-Evidence MVP | #297 | Provide a working read-only board/report from issue/PR/contract evidence while local ledger storage is not yet available. | Completed MVP slice |
| V2-5B Ledger-Backed Foundry Board | #361 | Make the Foundry Board read from local ledger replay first, with GitHub as provenance/mirror evidence. | Completed implementation |
| V2-6 GitHub Project Remote Sync Design | #298 | Define safe remote mirror sync, dry-run/readback behavior, field mapping, conflict rules, and human gates. | Accepted design |
| V2-6A GitHub Project Dry-Run Sync Plan | #362 | Implement read-only sync-plan generation that shows would-change/conflict/human-gate outcomes without writing Project. | Completed implementation |
| V2-7 V2 Readiness And Release Gate | #299 | Verify end-to-end journeys, migration, ledger replay, board visibility, dry-run sync behavior, docs, telemetry, and residual risks. | Accepted readiness |

## V2 Testing Contract

V2 cannot close on design acceptance, partial helper output, or isolated unit
tests. Testing is part of the user capability:

- each implementation issue owns its own focused automated tests;
- read-only and dry-run commands must assert `mutation_performed: false` and no
  unintended Project, GitHub, Vault, runtime, generated, branch, or filesystem
  writes;
- ledger-backed behavior must prove replay determinism and source-of-truth
  boundaries, not only JSON shape;
- migration and sync tests must include degraded GitHub/Project access,
  contradictory evidence, stale state, idempotency, and human-gate
  classification;
- user-facing report tests must prove that a maintainer can see status, evidence,
  conflicts, next actions, unknown/degraded sources, and forbidden actions;
- #299 must run the end-to-end walkthrough only after #359-#362 have accepted
  implementation evidence, unless the user explicitly approves a scoped V2
  deferral.

The testing bar for #359-#362 is:

- deterministic fixture tests for the new local-first behavior;
- negative/adversarial tests for malformed, missing, stale, contradictory, or
  degraded inputs;
- no-write tests for every read-only or dry-run path;
- branch-aware tests on the V2 integration branch where branch state affects the
  output;
- telemetry hooks for #266 that record useful scale and cost signals without
  claiming billing-grade counters;
- at least one user-facing command/report smoke path that reads like a practical
  maintainer workflow, not just a raw debug payload.

## V2-0 User Journey And UX Contract

This milestone prevents V2 from repeating a common failure mode: implementing useful internal mechanics without first proving the user-facing workflow.

It should answer:

- What does a user do when starting a new local-first project?
- What does a user do when migrating an existing GitHub issue/project workflow?
- What does the board show when work is ready, in progress, in review, blocked, done, or stale?
- What can the user trust as the local source of truth?
- What is GitHub allowed to overwrite, and what is local state allowed to overwrite?
- What are the first read-only screens or reports before write automation exists?
- What evidence is required before an item is considered complete?

V2-0 should not implement the board, ledger, sync, or migration tools. It is a design and acceptance contract.

## V2-1 Telemetry Evidence Window

#266 remains the telemetry evidence window. It should not run as a standalone research task disconnected from real work.

It should be bound to a selected V2 slice after V2-0 is accepted. The telemetry should capture enough data to compare:

- GitHub issue/PR comment overhead;
- Project field and label churn;
- dispatch and callback frequency;
- review and re-review loops;
- human gate count and delay;
- context rehydration cost;
- unclear owner or next-action failures;
- places where local-first state would have reduced coordination cost.

Telemetry evidence remains decision support. It is not billing-grade token accounting and does not authorize memory-system work.

## V2-2 Local Collaboration Ledger

The Local Collaboration Ledger is the local durable event record for orchestration.

Expected event categories include:

- issue or Epic creation;
- assignment and owner-role changes;
- dispatch;
- callback;
- evidence collection;
- review;
- requested changes;
- acceptance;
- human approval;
- merge;
- closure;
- blocked state;
- migration/backfill provenance;
- GitHub sync readback.

The ledger must support audit and replay before it supports automation.

#294 accepted the event model only. #359 completed the capability closure step
for actual local storage and replay, so V2 can now use local ledger evidence as
the durable collaboration state for the implemented workflow.

#359 testing must cover event schema validation, append/replay determinism,
supersession, corrupt or unknown events, conflict/degraded evidence handling,
idempotency, no GitHub dependency for local replay, and user-facing report
output that explains what local state exists and what still needs review.

## V2-3 Foundry Board Domain Model

The Foundry Board is the user-facing view over local orchestration state.

It should help users answer:

- What should I look at next?
- What is blocked and why?
- What is waiting on human approval?
- What is done but not reflected in GitHub Project?
- What has GitHub state that disagrees with local state?
- Which thread, issue, PR, or evidence comment explains the latest state?

The domain model should define states and transitions before UI implementation.

## V2-4 Existing Project Migration And Backfill

Existing GitHub-first projects must be supported.

Migration should:

- read current issues, PRs, comments, labels, milestones, and Project fields;
- preserve provenance rather than inventing clean history;
- identify incomplete, contradictory, or stale records;
- create local ledger records with confidence levels;
- avoid changing GitHub state during read-only backfill;
- produce a migration report users can review before any write-back.

This milestone is required for V2 because Agent Foundry already has substantial
durable GitHub history.

#296 accepted the migration/backfill design only. #360 completed the capability
closure step for read-only candidate ledger events with provenance, confidence,
contradiction handling, and no GitHub mutation.

#360 testing must cover bounded GitHub evidence conversion into candidate
events, provenance/confidence preservation, contradictory and stale history,
superseded work, degraded GraphQL/Project access, no GitHub writes, and report
output that clearly separates accepted local state from candidate imported
state.

## V2-5 Foundry Board Read-Only MVP

The first usable board should be read-only.

It should display enough information for a user to operate confidently:

- active work;
- owner role;
- Roadmap Status;
- blocking reason;
- latest evidence;
- next action;
- related issue, PR, branch, and thread;
- local/GitHub sync status.

The MVP should preserve local-first boundaries:

- durable local ledger events are the intended authority once available;
- GitHub issue/PR evidence can feed the preview;
- GitHub Project is an optional visual mirror, not the source of truth;
- candidate migration/backfill records stay visibly different from accepted
  state;
- stale, contradictory, degraded, or mirror-drift evidence appears as conflict
  or warning state instead of being hidden.

The user-facing output should turn board state into next actions: dispatch an
owner, request Reviewer/Architect/Human attention, rehydrate stale evidence,
hold blocked items, or record that no action is needed. These actions must
remain routed through existing issue/PR gates.

Write automation should wait until read-only behavior is trusted.

#297 completed a useful GitHub-evidence-backed board/report MVP. #361 completed
the ledger-backed board capability after #359, so the board now reads accepted
local ledger replay first and treats GitHub as provenance and mirror evidence.

#361 testing must prove that board lanes, owner, next actions, conflicts, and
mirror drift are derived from ledger replay first. GitHub issue/PR/Project
evidence may enrich provenance, but Project degradation or absence must not make
the local board unusable.

## V2-6 GitHub Project Remote Sync

GitHub Project sync should treat GitHub as a collaboration mirror, not the canonical local orchestration store.

The sync design must define:

- dry-run plan;
- conflict detection;
- field mapping;
- Roadmap Status and built-in Status behavior;
- idempotency;
- retry and readback behavior;
- human gates for risky writes;
- rollback or repair guidance.

Project sync must not silently close issues, overwrite human edits, or hide discrepancies between local and remote state.

#298 accepted the remote sync design only. #362 completed the read-only dry-run
sync-plan generation capability that shows what would change, where conflicts
exist, and which actions require Human gates, without writing GitHub Project.

#362 testing must cover dry-run-only behavior, would-change before/after values,
idempotency keys, conflict classes, human-gate classification, degraded
GraphQL/Project readback, retry/readback metadata, partial results, and explicit
proof that Project writes, issue closure/reopen, and repair/apply are not
performed.

## V2-7 V2 Readiness And Release Gate

V2 readiness should verify:

- new project journey;
- existing project migration journey;
- daily orchestration journey;
- review and human approval journey;
- blocked/recovery journey;
- local-first source-of-truth behavior;
- ledger storage/replay behavior;
- ledger-backed Foundry Board behavior;
- GitHub Project dry-run sync-plan behavior;
- docs and user-facing walkthrough;
- telemetry evidence and residual risks.

The final readiness walkthrough must include a test matrix for:

- new local-first project setup and first board view;
- existing GitHub-first project backfill into candidate ledger events;
- daily orchestration from local replay through board next actions;
- Reviewer/Architect/Human gate visibility;
- blocked, stale, superseded, and recovery states;
- degraded GitHub Project access with useful local output;
- dry-run sync-plan review with conflicts and human gates;
- branch-aware V2 integration behavior;
- no-write guarantees for read-only/dry-run paths;
- docs and command examples matching the tested user flow.

#299 verified the end-to-end V2 readiness matrix after #359, #360, #361, and
#362 were accepted.

V2 release should remain separate from memory-system implementation.
