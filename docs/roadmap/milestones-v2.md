# Roadmap Milestones V2

Status: active capability roadmap
Updated: 2026-07-09
Scope: V2 local-first orchestration, Foundry Board, Local Collaboration Ledger, GitHub Project remote sync/apply, migration from existing GitHub-first projects, mixed-state recovery, management UX, dogfood adoption, and runtime/pack enablement.

## V2 Goal

V2 makes Agent Foundry a usable local-first orchestration system, not only a
read-only reporting layer.

The user value is simple: a user should be able to see what work is happening, who owns it, what evidence supports it, what is blocked, what changed, and what should happen next without reconstructing state from scattered GitHub comments, Project columns, and Codex thread history.

GitHub Project remains useful, but it becomes a remote sync and collaboration
surface. The durable orchestration record should live locally first, then sync
outward in a controlled way.

V2 is not complete until users can operate the workflow end to end:

- start a new local-first collaboration flow;
- migrate an existing GitHub-first project into reviewed local ledger state;
- make approved local orchestration changes through explicit apply gates;
- preview and then apply safe GitHub Project mirror updates through gated sync;
- handle mixed local/GitHub state without hiding conflicts;
- use a management surface that explains state, evidence, next actions, gates,
  and recovery without requiring raw JSON inspection;
- dogfood the workflow on a real project and record the practical conclusion;
- enable the behavior through practices, Skills, and capability packs without
  confusing V1.x maintenance flows.

V2 does not replace the Base Agent Foundry operating model. After V2 merges
back, Agent Foundry should have two compatible capability layers:

- the Base layer: stateless or GitHub-first workflow, practice/asset lifecycle,
  harvest, review, publish, runtime apply, and capability-pack governance;
- the Local Orchestration layer: local ledger, Foundry Board, migration apply,
  local action apply, Project mirror sync, and mixed-state recovery.

Base remains the default. Local Orchestration is enabled by an explicit
capability marker, repo configuration, local ledger presence, issue contract, or
user request. Branch names can provide development-time sanity checks, but they
must not be the canonical way to decide whether a practice, asset, Skill, or
runtime action belongs to the Local Orchestration layer.

## Product Principles

- Start from end-to-end user journeys before building storage or board features.
- Support both new projects and existing issue-driven projects.
- Build read-only visibility before write or sync automation, but treat
  read-only/dry-run as Phase 1 rather than the full V2 capability.
- Treat design acceptance as a gate, not as capability completion. A V2
  capability is not complete until the user can run the relevant local-first
  workflow, inspect evidence, and understand next actions without relying on a
  design comment.
- Preserve GitHub issue and PR evidence as durable public collaboration records.
- Preserve Agent Foundry layer boundaries: Core, User Vault, Generated, Runtime, and Local Private.
- Keep memory-system work out of V2 unless a later explicit decision changes that.
- Make migration and backfill first-class work, not a cleanup afterthought.
- Treat dogfood and testing as part of capability closure, not as final paperwork. Each
  implementation gate must carry focused automated tests, degraded-state tests,
  write-boundary assertions, and user-facing output checks; final readiness must
  verify a real adopting-project workflow rather than only fixture success.
- Treat usability as a first-class non-functional requirement. V2 is a stateful
  local runtime capability; users need a management surface, stable ViewModels,
  performance expectations, reliability/recovery behavior, and privacy/security
  boundaries before real dogfood can fairly judge the product.

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
- V2.0.0 is cut only after the full capability roadmap is accepted, dogfooded,
  enabled, and merged through the final release gate.

## V2 Milestone Sequence

V2 uses separate design and implementation gates. Closed design issues such as
#294 and #298 are accepted architecture decisions; they do not by themselves
complete the user-facing capability.

| Milestone | GitHub records | Purpose | Status |
| --- | --- | --- | --- |
| V2-0 User Journey And UX Contract | #293 | Define the end-to-end experience before implementation: new project setup, existing project migration, day-to-day orchestration, review, recovery, sync, and completion. | Accepted design |
| V2-1 Telemetry Evidence Window | #266 | Collect meaningful telemetry across selected V2 work so ledger and board design are based on real coordination overhead rather than guesses. | Completed evidence window for Phase 1 |
| V2-2 Local Collaboration Ledger Design | #294 | Define the local durable event model for assignments, dispatches, evidence, reviews, approvals, merges, closures, blockers, and handoffs. | Accepted design |
| V2-2A Local Collaboration Ledger Storage/Replay | #359 | Implement local ledger event storage and replay so local state can become durable source-of-truth evidence. | Completed Phase 1 implementation |
| V2-3 Foundry Board Domain Model | #295 | Define board state, columns, filters, issue/project/thread relationships, and user-visible status without binding too early to UI implementation. | Accepted design |
| V2-4 Existing Project Migration And Backfill Design | #296 | Define how current GitHub-first projects become candidate local-first orchestration state with provenance and conflict handling. | Accepted design |
| V2-4A Existing Project Backfill Preview | #360 | Produce read-only candidate local ledger events from bounded GitHub issue/PR/Project evidence. | Completed Phase 1 implementation |
| V2-5 Foundry Board GitHub-Evidence MVP | #297 | Provide a working read-only board/report from issue/PR/contract evidence while local ledger storage is not yet available. | Completed Phase 1 MVP slice |
| V2-5B Ledger-Backed Foundry Board | #361 | Make the Foundry Board read from local ledger replay first, with GitHub as provenance/mirror evidence. | Completed Phase 1 implementation |
| V2-6 GitHub Project Remote Sync Design | #298 | Define safe remote mirror sync, dry-run/readback behavior, field mapping, conflict rules, and human gates. | Accepted design |
| V2-6A GitHub Project Dry-Run Sync Plan | #362 | Implement read-only sync-plan generation that shows would-change/conflict/human-gate outcomes without writing Project. | Completed Phase 1 implementation |
| V2-7 Phase 1 Readiness | #299 | Verify read-only ledger, backfill preview, board visibility, dry-run sync plan, docs, telemetry, and residual risks. | Accepted Phase 1 readiness |
| V2-8 Capability Replan And Apply UX Contract | #369 | Redefine V2 completion around migration apply, local action apply, Project sync apply, mixed-state recovery, dogfood, and enablement. | Next design gate |
| V2-9 Accepted Migration Apply | #370 | Turn reviewed backfill candidates into accepted local ledger state through explicit apply gates, with rollback/readback evidence and no GitHub writes. | Planned |
| V2-10 Local Orchestration Action Apply | #371 | Let users apply approved local board actions as ledger events: assignment, blocked, review, acceptance, closure, recovery, and supersession. | Planned |
| V2-11 GitHub Project Sync Apply | #372 | Apply approved Project mirror changes after dry-run review, with idempotency, readback, partial failure handling, and Human gates for risky writes. | Planned |
| V2-12 Mixed-State Conflict And Recovery | #373 | Handle interleaved local-first and GitHub-first edits, stale comments, branch-line drift, partial sync, superseded work, and rollback/recovery paths. | Planned |
| V2-13 Management Surface And UX ViewModel | #378 | Provide a user-facing management surface and stable ViewModel for board, item detail, migration review, apply review, sync plan, conflicts, and health. | Planned |
| V2-14 Real-Project Dogfood And UX Conclusion | #374 | Run the complete workflow on a real project, document practical friction, and decide whether the experience is good enough for adoption. | Planned |
| V2-15 Runtime / Skill / Capability Pack Enablement | #375 | Harvest and publish layer-aware V2 practices, Skills, and packs without making Local Orchestration behavior the default for Base workflows. | Planned |
| V2-16 Final V2 Integration And Release Gate | #376 | Verify full V2 usability, dogfood conclusions, docs, enablement, and decide on merge-back to `main` plus `v2.0.0` release. | Planned |

## V2 Capability Phases

Phase 1, completed by #359-#362 and accepted by #299, provides read-only and
dry-run visibility:

- local ledger append/report and replay;
- read-only existing-project backfill preview into candidate events;
- ledger-backed Foundry Board reporting;
- dry-run GitHub Project sync-plan generation.

Phase 1 is valuable but not sufficient for final V2 because users still cannot
complete the adoption loop from preview to accepted migration, approved local
state change, remote mirror apply, mixed-state recovery, and runtime enablement.

Phase 2 must close migration and local apply:

- accept selected candidate backfill events into the local ledger;
- apply approved board actions as local ledger events;
- keep all write paths explicit, reviewable, idempotent, and reversible enough
  for practical recovery.

Phase 3 must close remote mirror apply and mixed-state operation:

- turn dry-run Project sync plans into gated apply operations;
- preserve Human gates for issue closure/reopen, built-in Project Status side
  effects, privacy/security-sensitive fields, and broad Project schema changes;
- handle local/GitHub mixed state without guessing hidden authority.

Phase 4 must prove real use:

- provide a management surface that lets users inspect and act on state without
  reading raw JSON or ledger files;
- dogfood the complete workflow on at least one real existing project;
- capture failures, unclear prompts, confusing command names, and missing
  actions;
- update docs and helper output based on evidence rather than assumptions.

Phase 5 must enable adoption:

- harvest V2 practices and Skills with explicit capability-layer gates;
- update capability packs only where Local Orchestration behavior belongs;
- keep V1.x `main` maintenance behavior from silently becoming V2 local-first
  behavior;
- run a final readiness gate before merge-back or release.

## Capability Layer Contract

V2 planning must treat release version, branch, and capability layer as separate
axes.

- Version or release line answers what is being shipped.
- Branch answers where code is being developed or integrated.
- Capability layer answers which operating model is active for a repo, issue,
  practice, asset, Skill, or runtime action.

The capability layer should be explicit in durable records and user-facing
reports. Recommended values:

- `base`: default Agent Foundry behavior; no local orchestration state required.
- `local_orchestration`: V2 layer; local ledger and Foundry Board semantics are
  active.
- `mixed`: transition or migration state where base and local orchestration
  evidence both exist and conflicts must be surfaced.

Selection precedence:

1. explicit user request or command;
2. repo/local capability configuration;
3. local ledger manifest or accepted ledger state;
4. issue or task contract field such as `Capability layer`;
5. capability pack or runtime profile;
6. branch/release-line evidence as a warning or fallback only.

The default is always `base`. A practice or asset should be `base` unless it
requires local ledger, Foundry Board, migration apply, Project sync apply, or
mixed-state recovery. Local-Orchestration-only entries should remain rare and
conditional.

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
- management-surface tests must show that a user can identify current state,
  evidence, next action, required gate, forbidden action, and recovery path
  without reading raw helper JSON.

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

#266 completed the Phase 1 telemetry evidence window. It should remain useful as
the evidence record for read-only/dry-run V2 work, not as an open blocker.

Future V2 phases should continue the same telemetry discipline on their own
implementation and dogfood gates. The telemetry should capture enough data to
compare:

- GitHub issue/PR comment overhead;
- Project field and label churn;
- dispatch and callback frequency;
- review and re-review loops;
- human gate count and delay;
- context rehydration cost;
- unclear owner or next-action failures;
- places where local-first state would have reduced coordination cost.

Telemetry evidence remains decision support. It is not billing-grade token
accounting and does not authorize memory-system work.

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

## V2-7 Phase 1 Readiness Gate

Phase 1 readiness verified:

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

The Phase 1 readiness walkthrough included a test matrix for:

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

#299 verified the Phase 1 readiness matrix after #359, #360, #361, and #362
were accepted. It did not complete final V2 adoption because migration apply,
local action apply, Project sync apply, mixed-state recovery, dogfood, and
runtime/pack enablement remain planned.

## V2-8 Capability Replan And Apply UX Contract

V2-8 is the next design gate. It should convert the user correction into a
precise end-to-end UX contract for the remaining capability:

- the complete user experience loop from preview to apply, recovery, dogfood,
  and enablement;
- the management surface and ViewModel required before dogfood;
- non-functional requirements for performance, reliability, security/privacy,
  usability, and recovery;
- how Base and Local Orchestration layers are identified and separated;
- how harvest, dedupe, approval, publish, generated Skill, runtime apply, and
  capability-pack flows decide whether an item belongs to `base`,
  `local_orchestration`, or `mixed`;
- how to avoid promoting Local-Orchestration-only behavior into Base defaults;
- what the user sees after a backfill preview;
- how the user accepts selected candidate events into local ledger authority;
- how local board actions become approved ledger events;
- how the user reviews and applies a GitHub Project sync plan;
- how mixed local/GitHub states are classified and recovered;
- which steps are agent-handled, which require Reviewer/Architect, and which
  require Human approval;
- what dogfood evidence is required before final readiness.

V2-8 must not implement apply behavior. It should release implementation gates
only after the action model, safety gates, and test matrix are clear.

## V2-9 Accepted Migration Apply

V2-9 should let users turn reviewed #360 backfill candidates into accepted local
ledger events.

Required behavior:

- select candidate events or candidate groups explicitly;
- preserve provenance and confidence from the preview;
- write only local ledger events;
- record accepted/rejected/skipped decisions;
- keep GitHub/Project state unchanged;
- support idempotency and duplicate prevention;
- provide rollback or compensating-event guidance rather than destructive
  history edits.

This is the first point where existing GitHub-first projects become genuinely
usable in the local-first workflow.

## V2-10 Local Orchestration Action Apply

V2-10 should let users apply approved local board actions as ledger events.

Examples:

- assign or hand off work;
- mark blocked/unblocked with reason;
- record Reviewer result;
- record Architect acceptance;
- record Human approval;
- mark local done/closed evidence;
- supersede stale work;
- recover from interrupted or contradictory state.

The command/report should always show before/after local state, evidence refs,
owner role, required gate, and forbidden remote side effects.

## V2-11 GitHub Project Sync Apply

V2-11 should turn #362 dry-run sync plans into reviewed Project mirror writes.

Required behavior:

- apply only operations from an accepted dry-run plan or revalidated equivalent;
- perform targeted Project writes, not broad scans;
- use idempotency keys and readback checks;
- classify partial failures and degraded GraphQL access;
- require Human gates for built-in Status side effects, issue closure/reopen
  implications, privacy/security-sensitive values, and broad Project policy or
  schema changes;
- never silently overwrite human GitHub edits.

This milestone still treats GitHub Project as a mirror, not the source of truth.

## V2-12 Mixed-State Conflict And Recovery

V2-12 should handle the messy operating reality after local-first adoption:

- local ledger has newer state than GitHub;
- GitHub issue/PR comments changed after local replay;
- Project fields drift from local board;
- a branch targets the wrong release line;
- a task is partly migrated and partly remote-only;
- a sync apply partially succeeded;
- a previous agent or human changed state out of band.

The user-facing output should say what is trusted, what is candidate-only, what
is remote mirror-only, what conflicts, and which safe next action exists. It
must avoid hidden repair, guessing authority, or destructive cleanup.

## V2-13 Management Surface And UX ViewModel

V2-13 should make V2 usable as a stateful local runtime capability, not only as a
set of helper commands.

The first management surface can be a static HTML report, local TUI, or local
web UI. It must be good enough for dogfood before V2-14 starts.

Required views:

- Board view: lanes, owner role, capability layer, evidence, next action, and
  conflict badges.
- Item detail: local ledger timeline, GitHub evidence, Project mirror state,
  gates, conflicts, and forbidden actions.
- Migration review: candidate events, provenance, confidence, and
  accept/reject/defer plans.
- Apply review: before/after local state, write target, idempotency, required
  gate, and rollback or compensating-event guidance.
- Sync review: local desired state vs Project mirror, would-change fields,
  conflicts, Human gates, and readback status.
- Health view: ledger root, schema version, replay performance, degraded
  GitHub/Project status, and runtime/Skill/CP enablement status.

Non-functional requirements:

- performance: representative ledger replay and board render must stay within a
  documented budget;
- reliability: interrupted/partial apply or sync states must be visible and
  recoverable;
- security/privacy: local-only/private evidence must not be pushed or displayed
  as public sync data;
- usability: a reviewer must be able to identify state, next action, required
  gate, and forbidden actions without raw JSON inspection.

## V2-14 Real-Project Dogfood And UX Conclusion

V2-14 is required before final V2 readiness.

Dogfood must cover at least one real existing project, preferably one with
non-trivial GitHub issue/PR/Project history. The walkthrough should include:

- backfill preview;
- candidate acceptance into local ledger;
- ledger-backed board use;
- local action apply;
- Project sync dry-run;
- at least one approved sync apply or an explicit Human-gated deferral;
- management surface walkthrough;
- mixed-state or degraded-source handling;
- user-facing conclusion: what felt clear, what remained confusing, and what
  must change before release.

Fixture tests cannot replace this milestone because V2 is an orchestration UX
capability, not only a parser/helper capability.

## V2-15 Runtime / Skill / Capability Pack Enablement

V2-15 should make the capability available through normal Agent Foundry use.

Required behavior:

- harvest V2 practices with explicit capability-layer gates;
- update `agent-collaboration` guidance so V2 flows trigger only when the repo,
  capability marker, local ledger state, issue contract, or user request asks
  for Local Orchestration;
- update capability packs where appropriate without making V2 behavior the
  implicit default for Base workflows;
- verify generated/runtime behavior or explicitly defer activation behind an
  open follow-up gate.

This milestone prevents V2 Core helper features from existing only as manual
script commands.

## V2-16 Final V2 Integration And Release Gate

V2-16 is the real final V2 gate.

It should verify:

- Phase 1 read-only/dry-run behavior still passes;
- migration apply works for existing projects;
- local action apply works for ordinary orchestration;
- Project sync apply works or has an explicit Human-gated deferral;
- mixed-state recovery has practical user guidance;
- management surface usability and NFR evidence are accepted;
- dogfood produced an accepted conclusion;
- practices/Skills/capability packs are enabled or explicitly deferred;
- docs explain the normal user path without requiring the user to understand
  every helper internals;
- V2 branch is ready for a separate Human-gated merge-back/release decision.

V2 release should remain separate from memory-system implementation.
