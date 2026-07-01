# Agent Foundry Roadmap

Status: planning document
Updated: 2026-07-01
Scope: Agent Foundry productization, runtime adapter framework, Trae support, capability-system hardening, repository hygiene, role-orchestration optimization, V1.0 release readiness, and memory-system readiness.

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

Current planning stage: V1.0 release readiness.

AF-0 explains the existing mixed history. AF-1 starts the stricter planning and multi-agent coordination era. AF-2 designs the productization boundary. AF-3 executes the local Core/Vault split. AF-4 proves the split system works for the current real user across existing deployments and establishes the migration discipline needed for later major upgrades. AF-5 makes onboarding humane and reliable for new users. AF-6 closes the current Foundry product lifecycle so install, pack deployment, refresh, status, and rollback are usable beyond a one-off maintainer path. AF-7 upgrades runtime adapters and adds Trae CN support around a verified global Skill path. AF-8 hardens the capability system under realistic multi-user, multi-machine, multi-runtime, long-running-agent, and drift scenarios. AF-9 adds advanced capability-pack discovery, lifecycle, privacy-safe transfer planning, and user-facing Skill workflow packaging. AF-10 optimizes the Coordinator-driven role workflow using AF9 evidence, then pauses for an AF11 pilot migration, then resumes to analyze real telemetry and harden the workflow model. AF-11 is reserved for the Tiny IPA-incubated GitHub collaboration workflow helper migration pilot. AF-12 closes the V1 user-facing UX/docs/starter-pack surface. Memory-system planning now uses the separate MS milestone axis.

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
| V1.0 readiness | `v1.0.0`: public Core release after AF-1 through AF-12 plus release-critical hardening milestones are accepted. |

`v1.0` is the first public release target. It should include the accepted AF-1 through AF-12 baseline plus V1.0 readiness milestones needed for external users to rely on Agent Foundry without understanding this repository's personal history.

## V1.0 Release Readiness Milestones

V1.0 release readiness is tracked separately from AF stage numbering so late release-critical polish does not renumber the AF roadmap.

| Milestone | GitHub records | User-facing reason | Status |
| --- | --- | --- | --- |
| Agent Foundry `v1.0.0` release | #267 | Define the first downloadable public Core release, release notes, verification, tag, and GitHub Release gate. | Open |
| External Skills Import and Reference Hardening | #276 through #281 | Users need a clear, safe path to evaluate public skills, prompt packs, articles, repos, and local skill folders before anything becomes a practice, asset, reference-only material, adapter output, or rejected input. | Held until explicitly resumed |

External skills are V1.0-relevant because Agent Foundry already exposes `import skill <source>` and already treats external skills as evidence sources. Before public release, this path needs a complete lifecycle, reference-only semantics, user-facing decision support, review templates, fixture-backed validation, and a readiness walkthrough.

V1.0 readiness milestones do not authorize memory-system work, automatic token capture, live Vault/private/runtime/generated mutation, generated adapter publish, external script execution, or broad docs rewrites outside reviewed child issues.

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
| Stage | AF-1 through AF-12, V1.0, V2.0, MS-01, MS-02 | Maturity, release-readiness, product-version, or memory-system planning stage the item serves. |
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

- `stage:AF-1` through `stage:AF-12`
- `stage:v1.0`, `stage:v2.0`
- `stage:MS-01`, `stage:MS-02`
- `type:epic`, `type:task`, `type:decision`, `type:review`, `type:evidence`
- `area:core`, `area:vault`, `area:generated`, `area:runtime`, `area:privacy`, `area:memory-readiness`, `area:adapters`
- `needs:architect`, `needs:implementer`, `needs:reviewer`, `needs:harvester`
- `risk:low`, `risk:medium`, `risk:high`

Multi-agent rule:

- Architect creates or updates Epics and Decision issues.
- Implementer works only from Ready issues with clear scope, dependencies, branch strategy, and acceptance criteria.
- Reviewer checks against the Epic exit criteria and relevant practices.
- Harvester extracts reusable practices or asset candidates after meaningful work, using the harvest workflow.

Create GitHub Project/Epic items for the active stage and its immediate successor. Completed stage detail should stay in the split milestone files and durable GitHub records rather than expanding this overview. AF-10 work may collect readiness and workflow-optimization evidence. MS-01 planning lives on a separate milestone axis, but MS-01 execution should wait until AF10 workflow optimization evidence is accepted or explicitly waived by the user.

## Milestone Details

Detailed milestone plans are split out of this overview so the roadmap stays readable and maintainable. Use this file for the current decision, stage model, Project workflow, and high-level navigation. Use the linked milestone files for detailed execution notes, issue sequences, acceptance criteria, and historical validation records.

| Range | Detail file | Contents |
| --- | --- | --- |
| AF-0 through AF-6 | [roadmap/milestones-af0-af6.md](roadmap/milestones-af0-af6.md) | Planning context, repository hygiene, productization, Core/Vault split, current-user deployment migration, onboarding, and existing Foundry lifecycle completion. |
| AF-7 through AF-12 | [roadmap/milestones-af7-af11.md](roadmap/milestones-af7-af11.md) | Runtime adapter framework, capability hardening, advanced capability-pack discovery, Coordinator workflow optimization, GitHub collaboration helper migration, and end-to-end UX/docs/starter-pack completion. |
| V1.0 readiness | GitHub milestones #267 and #276-#281 | Public release definition plus release-critical external skill import/reference hardening. |
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

1. Complete the V1.0 external skills import/reference hardening milestone (#276-#281) after the human hold is lifted.
2. Complete #267 release planning, verification, release notes, and final Human Decision Contract for `v1.0.0`.
3. Keep #266 as a V2.0 telemetry collection window, held until formal V2.0 kickoff.
4. Keep memory-system planning on the MS milestone axis: MS-01 for readiness design and MS-02 for implementation-home decision. MS work remains gated on explicit human authorization.
5. Do not create memory directories, schemas, MCP write tools, or automatic memory writing before explicit user authorization.
