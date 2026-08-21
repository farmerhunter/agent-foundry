# Agent Foundry Roadmap

Status: planning document
Updated: 2026-08-20
Scope: Agent Foundry productization, runtime adapter framework, Trae support, capability-system hardening, repository hygiene, role-orchestration optimization, collaboration cost-control, V1.0 public release baseline, V2 local-first orchestration planning, and memory-system readiness.

## Purpose

This document coordinates future work on Agent Foundry before deciding whether a broader memory and knowledge system should be built inside this repository, as a sibling project, or as a separate product.

Agent Foundry is not finished as an experience and skill management system. Its current repository also mixes several concerns that must be separated before it can safely support other users or a larger memory system:

- reusable system code and workflows;
- the user's canonical practices and assets;
- generated or maintained adapter outputs;
- machine-local runtime state;
- raw or sensitive evidence;
- proposed future memory-system design material.

The near-term goal is not to implement the memory system. The near-term goal is to make Agent Foundry ready for a deliberate decision.

## Current Decision

Do not directly expand the current repository into a memory system without preparation.

Do not fork yet.

First complete a readiness phase that clarifies repository layers, product boundaries, generated artifact policy, install/config behavior, schema maturity, and extension policy. After that, compare:

- in-repo extension;
- monorepo package;
- sibling repository;
- forked experimental repository;
- user-vault convention using Agent Foundry as governance core.

## Capability State

Use these terms consistently:

- `current`: implemented and usable in the repository today.
- `candidate`: proposed and awaiting review.
- `proposed`: designed but not implemented.
- `future`: intentionally deferred.
- `deprecated`: considered before but no longer recommended.
- `unknown`: not verified yet.

Current Agent Foundry capabilities include practices, assets, workflows, schemas, indexes, adapters, runtime manifests/templates, usage evidence, imports, docs, and scripts already present in this repository.

Proposed memory-system concepts include `memory/`, `knowledge/`, `research_memos/`, `project_memory`, memory record schemas, Memory Triage Skill, semantic/vector/graph indexes, and MCP memory access. They must not be treated as writable substrates until implemented through reviewed repository changes.

## Target Layer Model

Agent Foundry should converge on these layers:

| Layer | Purpose | Git Behavior |
| --- | --- | --- |
| Core | Reusable workflows, schemas, scripts, templates, adapter generation logic, and docs needed by any user. | Tracked and distributable. |
| User Vault | A user's canonical practices, assets, indexes, shared aggregates, and long-form local docs. | Tracked in the user's vault repo; should be separable from Core. |
| Generated | Adapter outputs, knowledge packs, rendered summaries, and derived indexes generated from canonical records. | Prefer reproducible generation; track only when needed for adapter distribution or manual targets. |
| Runtime | Installed copies under tools such as Codex, Claude Code, Hermes, or ChatGPT project import. | Downstream, machine-local, not canonical. |
| Local Private | Raw usage logs, raw exports, secrets, machine paths, sensitive evidence, and adoption decisions. | Gitignored by default. |
| Proposed Design Evidence | Handoff dumps, research notes, unresolved questions, and future architecture sketches. | Track as docs/imports when explicitly approved; not executable substrate. |

This layer model is the main prerequisite for both external users and future memory-system work.

## Maturity Stages

Agent Foundry should use maturity stages for planning and release versions for distribution. Stages describe what kind of system the repository is becoming. Release versions can later map to stage completion.

| Stage | Name | Meaning | Exit Criteria |
| --- | --- | --- | --- |
| AF-0 | Personal Bootstrap | Early personal repo built through direct iteration before strict planning and multi-agent workflow. | Historical stage; no need to retroactively perfect it. |
| AF-1 | Governed Foundry | Practices, assets, workflows, review gates, adapter publishing, and current/proposed boundaries are governed explicitly. | Harvest/review/publish lifecycle is coherent; roadmap and hygiene work are tracked. |
| AF-2 | Productizable Foundry | Repository layers and user/product boundaries are clear enough to support a reusable system. | Core, User Vault, Generated, Runtime, Local Private, and Proposed Design Evidence are separated by policy and implementation plan. |
| AF-3 | Split Vault Migration | Core and the current account's User Vault are physically separated locally without breaking the active local runtime chain. | Public Core no longer requires current-user vault content; the active local User Vault validates separately; existing local Codex, Claude Code, Hermes, and ChatGPT setups have passed the split migration window. |
| AF-4 | Current-User Deployment And Upgrade Migration | The only real user, `farmerhunter`, can use the split system reliably across all already-deployed machines and runtime types, and Agent Foundry has a repeatable migration discipline for future major data-schema or program-structure upgrades. | The User Vault has a private remote or equivalent reviewed sync substrate; every existing deployment can locate Core plus Vault, refresh from the selected Vault, run harvest/review/publish workflows, report sync/runtime state without stale combined-root assumptions, and pass a reusable upgrade readiness checklist covering version markers, dry-runs, backups, rollback, compatibility, and cross-machine verification. |
| AF-5 | Onboarding Ready | New users can install Core, create a blank Vault, deploy the mandatory bootstrap capability pack, optionally deploy additional capability packs, and refresh adapters without confusing pack content with private user history. | Blank Vault creation, bootstrap pack deployment, optional pack selection, runtime-asset import, and first-run refresh are tested after the current user's multi-machine migration is proven. |
| AF-6 | Existing Foundry Lifecycle Completion | AF-5 onboarding journeys become a coherent product lifecycle: complete install, blank-vault bootstrap, non-new-install pack status/update/apply, optional pack deployment, runtime refresh/install, and rollback/status reporting. | A user can install or restore Agent Foundry, deploy or update reviewed packs, refresh runtimes, inspect status, and recover from failure through documented commands and validation without mixing Core, Vault, Generated, Runtime, or product-project contexts. |
| AF-7 | Runtime Adapter Framework And Trae Support | Adapter publishing becomes a runtime-aware distribution system, and Trae CN is supported through a verified global Skill path. | Canonical assets can project through a portable adapter model into generated runtime adapters with source metadata, freshness reporting, safe install behavior, and a Trae global Skill publisher validated against `~/.trae-cn/skills`. |
| AF-8 | Capability System Hardening | The post-AF6 capability system is exercised against realistic multi-user, multi-machine, multi-runtime, long-running-agent, drift, restore, parser/schema, and lifecycle edge cases. | Capability-system boundary scenarios are validated or improved through temp fixtures, status/repair UX, Project scheduler state, and safe runtime/Vault boundaries. |
| AF-9 | Advanced Capability Pack Discovery and Lifecycle | Capability packs can be recognized, maintained, exported, and optimized as higher-level reusable bundles after the basic pack lifecycle is stable and hardened. | Emergent capability-pack discovery and export/update automation can be designed without weakening Core/Vault authority, runtime freshness, or reviewed pack deployment. |
| AF-10 | Coordinator Workflow Optimization | Multi-thread role orchestration, rehydration, GitHub state synchronization, Human Decision Contracts, and Project/Roadmap coherence are measured and optimized before memory-system planning expands the workflow surface. AF10 is intentionally phased: foundation and telemetry first, an AF11 pilot in the middle, then analysis, policy, and implementation closeout. | Coordinator and role-thread workflows have measurable overhead, compact handoff patterns, durable state ledgers, and clear guidance for when to use multi-thread orchestration versus single-thread serial work. |
| AF-11 | GitHub Collaboration Helper Migration | Placeholder for migrating the GitHub-based collaboration workflow helper incubated in Tiny IPA into Agent Foundry as an interleaved pilot after AF10 foundation work and before AF10 final optimization closeout. | Migration scope, ownership boundary, reusable asset shape, user-facing workflow, validation path, and telemetry evidence are defined without importing Tiny IPA project-local assumptions. |
| AF-12 | End-to-End UX, Documentation, And Core Starter Packs | Final pre-V1 user experience consolidation across onboarding, daily operation, capability packs, runtime/generated adapters, GitHub collaboration helpers, documentation tiers, and first-party Core starter packs. | README, user docs, workflow docs, capability-pack UX, Core-hosted starter packs, and readiness evidence are coherent enough for a public V1 release path. |
| AF-13 | External Skills Import And Reference Workflow | Users can evaluate external skills, prompt packs, articles, repositories, and local skill folders through a reviewed import/reference workflow before anything becomes active Agent Foundry behavior. | External sources have clear outcomes, reference-only semantics, review packets, user-facing docs, fixture validation, and readiness evidence without treating external material as authority. |
| AF-14 | Tester Role And Test Planning Workflow | Testing becomes a first-class collaboration workflow so complex user-visible or stateful work has a clear test plan, evidence taxonomy, and automation/human-trial boundary before acceptance. | Tester role boundaries, testing contracts, scheduler support, docs, helper validation, and a bounded pilot prove that testing evidence improves confidence without replacing Architect, Implementer, Reviewer, or Human gates. |
| AF-15 | Collaboration Readiness And Action Workflow | New and existing repos can audit multi-agent collaboration readiness and receive user-facing safe next actions before any repair/apply behavior exists. | Read-only readiness reports, action-plan output, degraded GitHub/Project visibility, dry-run repair planning, docs, dogfood evidence, and capability-pack enablement are accepted without making GitHub Project the source of truth. |
| AF-16 | Branch-Aware Collaboration And Safety | Multi-agent issue and PR work becomes branch-line aware so V1.x maintenance, V2 integration, AF18 integration, stacked PRs, and custom branch policies do not silently mix. | Execution Contracts, helper reports, docs, and tests expose branch strategy, target branch, PR base, current checkout, and safe next actions without auto-retargeting, checkout, merge, reset, or repair. |
| AF-17 | Semantic Practice Loading And Adapter Reachability | Generated collaboration and architecture Skills load the right canonical practice references conditionally instead of forcing every thread to carry every practice. | Semantic practice routes, generated references, reachability checks, and adapter packaging preserve canonical practice authority while reducing irrelevant runtime context. |
| AF-18 | Collaboration Cost-Control And Control Plane | Multi-agent collaboration becomes cost-aware, bounded, portable, and human-controllable before it becomes an assumed runtime substrate. | AF18 has one integration branch, one control-plane design path, explicit policy layers, bounded runtime-owned observations, Human-facing summaries, dogfood calibration, and separate activation/policy-freeze gates. |
| ORCH-01 → ORCH-02 → ORCH-03 → ORCH-04 → ORCH-05-A0 | Local-first orchestration and integrated collaboration lifecycle | ORCH-01 provides the Board, ORCH-02 provides the SQLite ledger, ORCH-03 is bounded/optional remote materialization, ORCH-04 provides the single-machine lifecycle and developer front door, and ORCH-05-A0 supplies the handoff evidence boundary. Together they inform—not ship—the `v2.0.0` candidate. | Users can onboard, operate, inspect and recover collaboration from durable local state without treating GitHub Project as the scheduler. |

Current planning stage: AF17 and AF18 are completed pre-V2 enabling foundations
already integrated into `main`; they are not ORCH milestones and are not active
V2 completion work. V2 consumes their semantic-loading, adapter-reachability and
bounded-collaboration foundations by ancestry. ORCH-01 and ORCH-02 are complete.
ORCH-04 has functional lifecycle evidence for its single-machine path and
A0-Lite same-host/manual-custody evidence is experimental only; A0-Real remains
deferred. ORCH-03 remote
materialization/convergence and all real second-device/cross-host transport
claims remain optional, candidate or deferred as their evidence requires. AF19
follow-ups remain separate. The accepted W1/W2 prerequisites make
`codex/orch-05-single-active-handoff-integration` the sole V2 finalization line;
W3 documentation is the current gate. Final readiness, merge to `main`, tag and
release remain separate Human gates.

The accepted status evidence is owner-recorded local state: `native_ready`,
bound project/control/scheduler/Work-root records and opaque durable-role
references. It also records `native_reachability=not_checked` and
`mutation_performed=false`; it does not prove live App Server or thread
reachability, current host-process reachability, cross-host continuity, UX,
performance, real-device resilience, production readiness or release readiness.

Base Agent Foundry remains the supported/default stateless or GitHub-first
practice/asset/issue/PR layer. For fresh or existing single-machine Local
Orchestration, SQLite is the only collaboration authority; GitHub, Project and
Board surfaces remain native facts, read-only views or non-authoritative
projections. Historical JSONL and `--ledger-root` paths are export/diagnostic
evidence, not fallback authority, migration requirements or dual-write paths.

AF-0 explains the existing mixed history. AF-1 starts the stricter planning and multi-agent coordination era. AF-2 designs the productization boundary. AF-3 executes the local Core/Vault split. AF-4 proves the split system works for the current real user across existing deployments and establishes the migration discipline needed for later major upgrades. AF-5 makes onboarding humane and reliable for new users. AF-6 closes the current Foundry product lifecycle so install, pack deployment, refresh, status, and rollback are usable beyond a one-off maintainer path. AF-7 upgrades runtime adapters and adds Trae CN support around a verified global Skill path. AF-8 hardens the capability system under realistic multi-user, multi-machine, multi-runtime, long-running-agent, and drift scenarios. AF-9 adds advanced capability-pack discovery, lifecycle, privacy-safe transfer planning, and user-facing Skill workflow packaging. AF-10 optimizes the Coordinator-driven role workflow using AF9 evidence, then pauses for an AF11 pilot migration, then resumes to analyze real telemetry and harden the workflow model. AF-11 is reserved for the Tiny IPA-incubated GitHub collaboration workflow helper migration pilot. AF-12 closes the V1 user-facing UX/docs/starter-pack surface. AF-13 adds the independent external-skills import/reference workflow. AF-14 adds a Tester role and test-planning workflow as V1.x maintenance. AF-15 adds collaboration readiness audit and action workflow as V1.x maintenance. AF-16 adds branch-aware collaboration safety. AF-17 adds semantic practice loading and generated Skill reachability. AF-18 adds collaboration cost-control and control-plane governance. V2.0 moves the orchestration source of truth local-first, with GitHub Project as a sync target. Memory-system planning now uses the separate MS milestone axis.

Memory-system milestones are tracked separately as MS-01 and MS-02 so repeated AF roadmap changes do not keep renumbering memory planning. MS milestones do not authorize memory-system implementation unless an explicit human decision does so.

## Release Version Mapping

Do not force semantic versioning to carry all planning meaning yet. Use AF stages for maturity and reserve release versions for distribution points.

Suggested mapping:

| Stage Complete | Candidate Release Meaning |
| --- | --- |
| AF-1 | `v0.1.0`: governed personal foundry baseline. |
| AF-2 | `v0.2.0`: productizable architecture and repo hygiene baseline. |
| AF-3 | `v0.3.0`: split Core/Vault migration baseline. |
| AF-4 | `v0.4.0`: current-user deployment and upgrade migration baseline. |
| AF-5 | `v0.5.0`: external-user onboarding baseline. |
| AF-6 | `v0.6.0`: complete Foundry install and basic pack lifecycle baseline. |
| AF-7 | `v0.7.0`: runtime adapter framework and Trae support baseline. |
| AF-8 | `v0.8.0`: capability-system hardening baseline. |
| AF-9 | `v0.9.0`: advanced capability-pack discovery and lifecycle design baseline. |
| AF-10 | `v0.10.0`: Coordinator workflow optimization and role-orchestration evidence baseline. |
| AF-11 | `v0.11.0`: GitHub collaboration workflow helper migration baseline. |
| AF-12 | `v0.12.0`: end-to-end UX, documentation, and first-party Core starter pack baseline. |
| AF-13 | `v0.13.0`: external skills import/reference workflow baseline. |
| V1.0 readiness | `v1.0.0`: public Core release after AF-1 through AF-13 and the release checklist are accepted. |
| AF-14 | `v1.1.0` candidate: Tester role, testing contract, and test-evidence workflow as V1.x maintenance. |
| AF-15 | `v1.1.0` candidate: collaboration readiness audit, action-plan output, dry-run repair planning, and multi-agent optional pack enablement as V1.x maintenance. |
| AF-16 | `v1.1.x` maintenance candidate: branch-aware collaboration contracts and helper safety. |
| AF-17 | `v1.1.x` maintenance candidate: semantic practice loading and generated Skill reachability. |
| AF-18 | `v1.1.x` / pre-V2 collaboration-runtime control plane candidate; final activation and policy freeze remain separate Human-gated decisions. |
| ORCH candidate | `v2.0.0` candidate: supported Base workflows plus SQLite single-machine Local Orchestration, with A0-Lite explicitly experimental. ORCH-03 remote materialization/convergence and A0-Real remain deferred or separately gated; release requires a separate Human gate. |

`v1.0` is the first public release target. It includes the accepted AF-1 through AF-13 baseline plus release notes, verification, tag, and GitHub Release work needed for external users to rely on Agent Foundry without understanding this repository's personal history.

`v2.0` is the next product development target. It should not start by building board features in isolation. It starts with end-to-end user journeys, then telemetry evidence, then local ledger, board model, migration, read-only MVP, controlled GitHub sync, and readiness review.

Every public release or V1.x maintenance release-readiness gate must include a
Capability Pack impact check. The gate reviews changed workflows, docs,
templates, scripts, and generated Skill-facing behavior against affected Core
capability packs. The release packet must record either `CP impact: none` with
specific reasons, or accepted capability-pack update issue(s) with pack version,
manifest hash, catalog hash, and verification evidence. Capability-pack
implementation, generated/runtime publishing, real deploy/apply, release tags,
and GitHub Release publishing remain separate reviewed gates.

## Branch and Release Lines

Use `main` as the stable V1.x maintenance line until V2 is accepted and ready to become the default product line.

This matters because Agent Foundry Core can keep receiving harvest-driven, user-approved, backward-compatible improvements after `v1.0.0`. Those improvements should remain available to current users and future V2 work. Therefore:

- `main` receives V1.x maintenance, bug fixes, documentation improvements, workflow/template/test improvements, and generic Core harvest updates.
- `v1.1.0`, `v1.2.0`, and other V1.x tags are cut from `main` while V2 is still under development.
- `codex/orch-05-single-active-handoff-integration` is the sole V2 finalization/integration authority for the current closeout Work. The contained `codex/v2-local-first-orchestration` line is historical, not a current target.
- V2 closeout child branches target `codex/orch-05-single-active-handoff-integration`, not `main`. A separately authorized V1.x-compatible Core maintenance improvement may still target `main`.
- V2 periodically forward-merges from `main` so V1.x maintenance and harvest improvements are not lost.
- V2 merges back to `main` only after V2 readiness is accepted and a final human-gated release/integration decision is made.
- AF17 and AF18 are completed pre-V2 foundations already on `main`; preserve
  their historical integration evidence rather than reopening or renaming those
  milestone lines. AF19 follow-ups have their own scope and do not become ORCH
  work merely because V2 consumes the earlier foundations.

Default harvest routing:

| Update type | Target |
| --- | --- |
| Backward-compatible Core practice/workflow/template/docs/test improvement | `main`, then forward-merge into V2 |
| Current V2 closeout documentation/finalization Work | `codex/orch-05-single-active-handoff-integration` |
| Historical V2 orchestration development | `codex/v2-local-first-orchestration` (contained historical line; not a current target) |
| Completed AF17/AF18 foundation or separate AF19 follow-up | `main` for accepted foundation lineage; a separately authorized AF19 branch when its contract requires one |
| Private or canonical User Vault practice/asset update | selected User Vault, not Core |
| Breaking schema/runtime/source-of-truth change | V2 branch or explicit major-version gate, not default `main` maintenance |

## Active Milestone

Agent Foundry `v1.0.0` is published. The active planning area is the W3 documentation/source acceptance gate toward a `v2.0.0` candidate on the non-`main` finalization line. Design or documentation acceptance is not capability completion; final readiness, `main`, tag and release remain separately Human-gated.

| Milestone | GitHub records | User-facing reason | Status |
| --- | --- | --- | --- |
| Agent Foundry `v1.0.0` release | #267 | First downloadable public Core release for external users. | Completed; GitHub Release and tag published |
| AF-14 Tester Role And Test Planning Workflow | #302 Epic; #303 through #308; PR #311 | Users need test planning and evidence that answer what was tested, why it is enough, which risks remain, and when human trial is still needed. | Completed; integrated into `main` as V1.x maintenance |
| AF-15 Collaboration Readiness And Action Workflow | #314 Epic; #315 through #321 plus #328 through #331 | Users need a clear audit and action plan for new/existing repo collaboration readiness before any live repair/apply behavior. | Completed; integrated into `main` as V1.x maintenance |
| AF-16 Through AF-18 Collaboration Control Path | [roadmap/milestones-af16-af18.md](roadmap/milestones-af16-af18.md) | Users need branch-aware, context-aware, and semantically loaded collaboration before long-running multi-agent work is safe to scale. | Completed pre-V2 foundations integrated into `main`; V2 consumes them by ancestry without redefining them as ORCH milestones. AF19 follow-ups remain separate. |
| ORCH-01 Local-First Orchestration And Foundry Board | #292 (historical Epic); #293 through #299; #359 through #362 | Local durable Board foundation. | Completed |
| ORCH-02 SQLite Local Ledger Foundation | #525; #526 through #530 | Transactional local authority, onboarding/action routing, replay and recovery. | Completed; final adopter acceptance recorded |
| ORCH-03 Distributed Authority And Selective Sync | #400; #537, #522, #404, #405, #403, #521, #402, #406 | Bounded local authority and selective external materialization. | Candidate/readiness only; not automatic, production, or convergence evidence |
| ORCH-04 Integrated Collaboration Lifecycle And Product Experience | #538; #539 through #543; #536; #564 | SQLite single-machine onboarding, status, recovery, front door and evidence-first developer documentation. | Functional lifecycle accepted for the separate V2 final gate; W3 docs/source acceptance pending; not milestone/release complete |
| ORCH-05-A0 Single-Active Handoff Deployment Gate | #551 through #559 | Enrollment, immutable manual bundle, owner-verified import, target-local activation and evidence. | A0-Lite same-host/manual-custody experimental accepted; A0-Real cross-host/device evidence deferred |

AF18's single high-level goal is to make Agent Foundry's multi-agent
collaboration cost-aware, bounded, portable, and human-controllable before it
becomes an assumed runtime substrate. It turns role-thread reuse, dispatch,
context growth, resource observations, successor handoff, duplicate prevention,
and Human attention into explicit control-plane concepts instead of relying on
long chat history or ad hoc Coordinator narration.

AF18's high-level design is `Codex-first, portable-core`: GitHub issues,
comments, PRs, labels, and exact SHAs are the current durable authority binding;
Codex is the only MVP runtime/dogfood adapter; Core semantics stay portable.
The portable Core owns `Work`, `ExecutionRun`, `DispatchClaim`,
`SuccessorPacket`, `TransitionReceipt`, resource-observation provenance,
budget inheritance, semantic execution modes, and policy readout/explain.
Native Codex task/thread/subagent ids are adapter metadata, not Core domain
objects.

#418 remains the sole AF18 Epic and human-facing roadmap authority. #449 is the
MVP decision record, not a replacement roadmap. #454 is the accepted post-MVP
operational readiness review. Its follow-up path is tracked by #457 calibration
evidence, #458 policy-freeze HDC, #459 RoleConversation/adaptor successor design,
#460 recovery and rollback readiness, #461 LearningSignal/HarvestCandidateIndex
contract, and #462 limited real-mode rollout before #426 canonical
delivery/activation and #427 final readiness can be released.

AF18 documentation is intentionally centralized as follows:

- `docs/roadmap.md` records the single high-level goal, active branch line, and
  roadmap relationship to V2.
- `docs/roadmap/milestones-af16-af18.md` records the AF16/AF17/AF18
  collaboration-control path and the current AF18 issue sequence.
- `workflows/coordinate-agent-work.md` records the AF18 control-plane design,
  policy layers, telemetry interpretation, and Coordinator lifecycle model.
- `workflows/github-collaboration-helper.md` and
  `docs/multi-agent-collaboration.md` record branch strategy and collaboration
  contract presets.
- `schemas/af18-control-plane.schema.yaml` plus
  `scripts/plan_af18_mvp1_control.py` are implementation contracts, not the
  primary human design narrative.

ORCH work does not authorize memory-system work, automatic token capture, live Vault/private/runtime/generated mutation, generated adapter publish, or broad implementation outside reviewed child issues. It must preserve the V1 Core/User Vault/Generated/Runtime/Local Private boundaries.

Current V2 correction:

- #294 and #298 are design gates, not complete user-facing capabilities.
- #297 is a useful GitHub-evidence-backed read-only board/report MVP, not the final ledger-backed Foundry Board.
- #359 must implement Local Collaboration Ledger storage/replay before local state can become durable source-of-truth evidence.
- #360 must implement read-only existing-project backfill into candidate ledger events.
- #361 must make Foundry Board read from ledger replay first.
- #362 must implement read-only GitHub Project dry-run sync-plan generation.
- #299 must remain held until #359 through #362 are accepted or explicitly deferred by a Human-gated V2 scope decision.

## GitHub Project and Epic Workflow

It is appropriate to introduce a GitHub Project now, but only as a lightweight coordination layer for AF-1 and AF-2. The Project should not become a large process system before the repository boundary work is clear.

Recommended Project name:

```text
Agent Foundry Roadmap
```

Minimal fields:

| Field | Values | Purpose |
| --- | --- | --- |
| Status | Inbox, Ready, In Progress, Review, Done, Blocked | Human-visible work state. |
| Stage | AF-1 through AF-18, V1.0, V1.1, V2.0, MS-01, MS-02 | Maturity, release-readiness, product-version, or memory-system planning stage the item serves. V2.1 remains label-only until #401 accepts Project-field expansion. |
| Epic | Free text or single-select | Groups issues by roadmap epic. |
| Owner Role | Architect, Implementer, Reviewer, Harvester | Clarifies expected agent/human role. |
| Depends On | Issue or PR references | Prevents ready queues from bypassing dependencies. |
| Risk | Low, Medium, High | Makes review depth explicit. |

Do not start with story points, quarters, velocity, or heavyweight estimation. Add them only if the lightweight Project stops answering planning questions.

Issue types:

- **Epic**: a group of related roadmap work with scope, exit criteria, and child issues.
- **Task**: concrete implementation, documentation, policy, or verification work.
- **Decision**: an architecture choice with options and rejected alternatives.
- **Review**: lifecycle, adapter, hygiene, or readiness review.
- **Evidence**: source material or investigation result that should inform later decisions.

Recommended labels:

- `stage:AF-1` through `stage:AF-18`
- `stage:v1.0`, `stage:v1.1`, `stage:v2.0`, `stage:v2.1`
- `stage:MS-01`, `stage:MS-02`
- `type:epic`, `type:task`, `type:decision`, `type:review`, `type:evidence`
- `area:core`, `area:vault`, `area:generated`, `area:runtime`, `area:privacy`, `area:memory-readiness`, `area:adapters`
- `needs:architect`, `needs:implementer`, `needs:reviewer`, `needs:tester`, `needs:harvester`
- `risk:low`, `risk:medium`, `risk:high`

Multi-agent rule:

- Architect creates or updates Epics and Decision issues.
- Implementer works only from Ready issues with clear scope, dependencies, branch strategy, and acceptance criteria.
- Reviewer checks against the Epic exit criteria and relevant practices.
- Tester plans or gathers testing evidence when a task has explicit user-visible, stateful, runtime, import, Vault, generated, or scheduler risk; Tester does not replace Reviewer, Architect, or Human acceptance.
- Harvester extracts reusable practices or asset candidates after meaningful work, using the harvest workflow.

Create GitHub Project/Epic items for the active stage and its immediate successor. Completed stage detail should stay in the split milestone files and durable GitHub records rather than expanding this overview. AF-10 work may collect readiness and workflow-optimization evidence. MS-01 planning lives on a separate milestone axis, but MS-01 execution should wait until AF10 workflow optimization evidence is accepted or explicitly waived by the user.

## Milestone Details

Detailed milestone plans are split out of this overview so the roadmap stays readable and maintainable. Use this file for the current decision, stage model, Project workflow, and high-level navigation. Use the linked milestone files for detailed execution notes, issue sequences, acceptance criteria, and historical validation records.

| Range | Detail file | Contents |
| --- | --- | --- |
| AF-0 through AF-6 | [roadmap/milestones-af0-af6.md](roadmap/milestones-af0-af6.md) | Planning context, repository hygiene, productization, Core/Vault split, current-user deployment migration, onboarding, and existing Foundry lifecycle completion. |
| AF-7 through AF-12 | [roadmap/milestones-af7-af12.md](roadmap/milestones-af7-af12.md) | Runtime adapter framework, capability hardening, advanced capability-pack discovery, Coordinator workflow optimization, GitHub collaboration helper migration, and end-to-end UX/docs/starter-pack completion. |
| AF-13 through AF-15 | [roadmap/milestones-af13-af15.md](roadmap/milestones-af13-af15.md) | External skills import/reference workflow support, Tester role and test planning, and collaboration readiness/action workflow support. |
| AF-16 through AF-18 | [roadmap/milestones-af16-af18.md](roadmap/milestones-af16-af18.md) | Branch-aware collaboration, semantic practice loading, and AF18 collaboration cost-control/control-plane path. |
| V1.0 release | GitHub issue #267 | Public release definition, release notes, verification, tag, and GitHub Release gate after AF-13 acceptance. |
| V2.0 | [roadmap/milestones-v2.md](roadmap/milestones-v2.md) | Local-first orchestration, telemetry evidence, Local Collaboration Ledger, Foundry Board, existing project migration, GitHub Project remote sync, and V2 readiness. |
| MS-01 through MS-02 | [roadmap/memory-system-milestones.md](roadmap/memory-system-milestones.md) | Memory-system readiness design and memory implementation-home decision, tracked outside the AF stage sequence. |

## Future Memory-System Implementation

Goal: implement a reviewed memory/knowledge MVP only after Foundry lifecycle, runtime adapter framework work, capability-system hardening, MS-01 memory readiness, and MS-02 implementation-home decisions are complete, and only after explicit user authorization.

Expected scope will be defined by MS-01 and MS-02. AF-10 may optimize the collaboration workflow that future memory work will rely on, but it does not authorize memory-system implementation. Until MS-01 readiness design and MS-02 home decision are accepted, memory-system implementation is a future placeholder, not a license to create memory directories, schemas, or MCP write tools now.

## Work Not To Do Yet

- Do not create `memory/`, `knowledge/`, `research_memos/`, or `project_memory` directories.
- Do not implement automatic memory writing.
- Do not add semantic/vector/graph indexes.
- Do not add MCP write tools.
- Do not import raw ChatGPT exports.
- Do not implement memory-system design or implementation before explicit user authorization.
- Do not refactor adapters or runtime install behavior outside reviewed runtime-adapter contracts.

## Immediate Next Planning Tasks

1. Keep V2 #293 and #266 held until the next explicit V2 kickoff decision.
2. Treat V1.x maintenance work, including harvest-compatible Core/docs/workflow/test improvements, as `main`-targeted unless it changes V2-only orchestration behavior.
3. Keep memory-system planning on the MS milestone axis: MS-01 for readiness design and MS-02 for implementation-home decision. MS work remains gated on explicit human authorization.
4. Do not create memory directories, schemas, MCP write tools, or automatic memory writing before explicit user authorization.
