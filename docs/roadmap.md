# Agent Foundry Roadmap

Status: planning document
Updated: 2026-06-16
Scope: Agent Foundry productization, runtime adapter framework, Trae support, capability-system hardening, repository hygiene, and memory-system readiness.

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
| AF-10 | Memory-System Ready | Future memory-system records, evidence policy, routing, privacy, and MCP boundaries are designed but not necessarily implemented. | Memory-system implementation home can be chosen with clear tradeoffs. |
| AF-11 | Memory Implementation Home Decision | The implementation home for memory-system work is chosen using evidence from completed Foundry lifecycle, runtime adapter framework, and capability-system hardening work. | Decision record names the chosen home, rejected alternatives, file/data boundaries, validation path, privacy policy, and rollback path. |

Current planning stage: AF-7 / M7.

AF-0 explains the existing mixed history. AF-1 starts the stricter planning and multi-agent coordination era. AF-2 designs the productization boundary. AF-3 executes the local Core/Vault split. AF-4 proves the split system works for the current real user across existing deployments and establishes the migration discipline needed for later major upgrades. AF-5 makes onboarding humane and reliable for new users. AF-6 closes the current Foundry product lifecycle so install, pack deployment, refresh, status, and rollback are usable beyond a one-off maintainer path. AF-7 upgrades runtime adapters and adds Trae CN support around a verified global Skill path. AF-8 hardens the capability system under realistic multi-user, multi-machine, multi-runtime, long-running-agent, and drift scenarios. AF-9 is later advanced capability-pack discovery and export lifecycle work. AF-10 is the decision gate for memory-system architecture. AF-11 chooses the memory implementation home. Memory-system implementation remains outside this current roadmap until explicitly authorized.

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
| AF-10 | `v0.10.0`: memory-system-ready design baseline. |
| AF-11 | `v0.11.0`: memory implementation-home decision baseline. |

`v1.0` should wait until the reusable core, user vault story, generated artifact policy, and runtime adapter behavior are stable enough that external users can rely on them without understanding this repository's personal history.

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
| Stage | AF-1 through AF-11 | Maturity stage the item serves. |
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

- `stage:AF-1` through `stage:AF-11`
- `type:epic`, `type:task`, `type:decision`, `type:review`, `type:evidence`
- `area:core`, `area:vault`, `area:generated`, `area:runtime`, `area:privacy`, `area:memory-readiness`, `area:adapters`
- `needs:architect`, `needs:implementer`, `needs:reviewer`, `needs:harvester`
- `risk:low`, `risk:medium`, `risk:high`

Multi-agent rule:

- Architect creates or updates Epics and Decision issues.
- Implementer works only from Ready issues with clear scope, dependencies, branch strategy, and acceptance criteria.
- Reviewer checks against the Epic exit criteria and relevant practices.
- Harvester extracts reusable practices or asset candidates after meaningful work, using the harvest workflow.

For now, create GitHub Project/Epic items for the active stage and its immediate successor. After AF-6 lifecycle completion, prioritize AF-7 runtime adapter framework and Trae support, then AF-8 capability-system hardening, before advanced capability-pack discovery or any memory-system planning. Memory-system issues should remain placeholders until the user explicitly authorizes that work.

## Milestones

### M0: Preserve Planning Context

Goal: make the current planning state discoverable without turning proposed memory architecture into current capability.

Deliverables:

- Keep `docs/memory-system-handoff-dump.md` as evidence, not final architecture.
- Link the handoff dump from the main documentation index.
- Keep `docs/system-design.md` explicit that future memory directories and schemas are not current capability.
- Keep harvested practices generalized and linked to the handoff evidence.

Acceptance criteria:

- No future memory subsystem directories are created.
- Current/proposed/future capability state is explicit in docs.
- Consistency and adapter quality checks pass.

Status: current baseline.

### M1: Repository Hygiene and Boundary Definition

Goal: make it obvious which files are source, canonical user content, generated output, runtime state, local private evidence, examples, or proposed design.

Epics:

- **Repository layer inventory**
  - Classify each top-level directory under the target layer model.
  - Identify mixed directories and ambiguous files.
  - Decide whether `adapters/` contains source-maintained adapter files, generated outputs, or both.

- **Generated artifact policy**
  - Define which generated files are tracked, regenerated, ignored, or published elsewhere.
  - Define drift checks for tracked generated outputs.
  - Define cleanup rules for generated artifacts.
  - Current policy location: `docs/system-design.md` section "Generated Artifact Policy".

- **Local/private data policy**
  - Extend the raw-local vs shared-aggregate rule beyond usage evidence.
  - Decide what happens to raw ChatGPT exports, transcripts, sensitive notes, and machine paths.
  - Add or update `.gitignore` only after policy review.
  - Current policy location: `docs/system-design.md` section "Local And Private Data Policy".

- **Example vs user content separation**
  - Decide how examples/templates should differ from the user's personal vault.
  - Identify any current content that would block external-user reuse.
  - Current policy location: `docs/system-design.md` section "Example Versus User Content Separation".

Acceptance criteria:

- A repository hygiene policy exists.
- Every top-level directory has an assigned layer.
- Generated and local-private files have explicit Git behavior.
- External users can tell what is product core versus the user's vault content.

Status: policy baseline implemented for AF-1; file movement and blank-vault initialization are deferred to AF-2.

### M2: Productization and Vault Separation

Goal: make Agent Foundry usable as a reusable system rather than only this personal repository.

Epics:

- **Core/Vault split design**
  - Define Core responsibilities.
  - Define User Vault responsibilities.
  - Decide whether Core and Vault remain in one repo for now or become separately installable later.
  - Current design location: `docs/system-design.md` section "Core And User Vault Split".

- **Blank vault initialization**
  - Design `init-vault` semantics before implementation.
  - Define starter indexes, practice/asset templates, runtime templates, and empty usage aggregate.
  - Ensure no personal content is required for a new user.
  - Current design location: `docs/system-design.md` section "Blank Vault Initialization".

- **Configuration boundary**
  - Separate portable config from machine-local config.
  - Confirm `~/.agent-foundry/config.yaml` remains a locator, not canonical knowledge.
  - Define where enabled runtimes, paths, privacy defaults, and sync remotes live.
  - Define how agents distinguish product project context, Foundry Vault operations, and Foundry Core maintenance before writing.
  - Current design location: `docs/system-design.md` section "Configuration Boundary".

- **External-user setup boundary design**
  - Document the pre-split setup narrative for a user who is not the repository maintainer.
  - Identify what a new user would eventually clone, initialize, or install.
  - Document what remains private.
  - Document how adapters are installed and updated.
  - Identify which parts cannot be completed until AF-3 split migration, AF-4 current-user deployment and upgrade migration, and AF-5 onboarding.
  - Current design location: `docs/system-design.md` section "External-User Setup Boundary".

Acceptance criteria:

- A new user can create an empty vault conceptually without inheriting personal records.
- Config and local runtime state are not confused with canonical knowledge.
- The setup story does not require knowing the maintainer's machine or personal workflow.

Execution order:

1. Complete Core/Vault split design (#6).
2. Use that boundary to design blank vault initialization (#7) and configuration boundary (#8).
3. Use #6, #7, and #8 together to write the external-user setup boundary design (#9).
4. Do not claim external-user readiness until AF-3 physically separates the active User Vault from public Core.
5. Treat onboarding modes such as starter capability packs or runtime-asset imports as AF-5 design work unless needed as constraints for #7/#8.

Blank Vault baseline:

- A blank Vault is an empty but valid canonical destination for a new user's reviewed practices, assets, indexes, usage aggregate, and reviewed imports.
- It should include empty indexes and empty aggregate evidence, not the maintainer's current active practice/asset records.
- Core owns schemas, templates, workflows, and initialization logic. The Vault owns user records and non-sensitive vault policy.
- Runtime install is not implied by blank Vault creation. Runtime deployment remains a separate local operation using Core tooling plus the selected Vault.
- Capability pack deployment happens after blank Vault creation. The mandatory bootstrap pack and optional packs enter the Vault as canonical data before `refresh`.
- Runtime-asset imports are optional AF-5 onboarding inputs, not AF-2 blank defaults.
- Empty indexes and aggregates should pass validation once AF-3 updates checks for separate Core and Vault roots.

### M3: Physical Core/Vault Split And Migration

Goal: split the reusable public Core from the maintainer's User Vault without breaking already-installed runtimes or losing reliable vault discovery.

Decision baseline:

- Target direction: public Core plus user-owned Vaults.
- The maintainer's current User Vault belongs to the `farmerhunter` account and should become private by default.
- Existing single-repo operation is a staging state, not the final multi-user deployment model.
- Physical split should happen after #6, #7, #8, and #9 are reviewed, and before claiming external-user readiness.

AF-3 is a migration stage, not only a documentation stage. It should be planned and executed as a sequence of reversible changes because it touches privacy, local runtime behavior, Git remotes, adapter generation, and agent context detection.

Non-negotiable invariants:

- Public Core must not require any current user's private Vault records.
- The current account's User Vault records must remain available after migration.
- Existing local Codex, Claude Code, Hermes, and ChatGPT workflows must have a tested migration path before the combined repository stops being the operational source.
- Core and Vault roots must be validated independently before canonical writes, adapter publishing, or runtime install.
- Runtime adapters are downstream projections from Core tooling plus the selected Vault; they are not the source of truth.
- Blank Vault validation must prove that empty indexes and empty aggregate evidence are valid, while missing or corrupt Vault files still fail clearly.
- AF-3 must not create memory-system storage such as `memory/`, top-level `knowledge/`, `research_memos/`, or `project_memory`.
- AF-3 must not solve AF-4 deployment/upgrade migration or AF-5 onboarding beyond preserving constraints needed for later stages.

Migration strategy:

1. **Design and dry-run first**: map current paths, script assumptions, generated outputs, runtime installs, and private Vault candidates before moving files.
2. **Make tooling split-aware while still in the combined repo**: introduce separate `core_root` and `vault_root` support behind compatibility behavior so checks can compare combined, current-user Vault, and blank-Vault scenarios.
3. **Extract the active User Vault only after validation can target an arbitrary Vault**: avoid moving canonical records before scripts know how to find and validate them.
4. **Regenerate adapters from the selected Vault**: prove runtime outputs come from Core plus Vault selection, not hardcoded repo-relative personal records.
5. **Migrate local runtimes after generated outputs are split-aware**: inventory, dry-run, install, then verify stale path references and manual ChatGPT steps.
6. **Gate current-user and external-user readiness separately**: AF-3 exits when the local split migration is reliable; AF-4 proves the current user's existing deployments can use it and establishes a repeatable major-upgrade migration discipline; AF-5 handles humane onboarding and starter/import choices for new users.

Migration window:

- The window starts only when extraction execution begins: active User Vault target is initialized or selected, current User Vault records are copied or moved, or `vault_root` is repointed away from the combined repository.
- The window is not opened by #31 planning or by #32 public Core cleanup if those changes do not move records or repoint runtime/local config.
- During the window, pause canonical writes such as harvest practice, harvest asset, publish, refresh, and runtime install unless the command explicitly uses verified split `core_root` and `vault_root`.
- The window closes in #33, after split Core plus active User Vault pass root validation, selected-Vault adapter publishing, runtime dry-run/install verification, stale-path checks, and rollback visibility.
- #34 is the post-window AF-3 readiness audit. If #34 finds a failure, reopen or fix the migration result; do not treat #34 as the normal window close.

Rollback points:

- Before script changes: current combined repo is the working baseline.
- After split-aware tooling but before file extraction: revert tooling changes or keep compatibility mode.
- After User Vault extraction: restore from private Vault backup or keep old combined checkout read-only until runtime migration passes.
- After runtime reinstall: use existing `scripts/rollback_runtime.py` and managed markers for local runtime rollback where supported; ChatGPT remains manual.
- Before public Core claim: verify no private Vault records are required by Core defaults.

AF-3 epics and task breakdown:

- **Split execution plan**
  - Choose final repo/directory names for Core and the active User Vault.
  - Use the common local User Vault pattern `~/.agent-foundry/vault/agent-foundry-vault-<account>` unless explicitly overridden.
  - For the current `farmerhunter` account, the selected local target is `~/.agent-foundry/vault/agent-foundry-vault-farmerhunter`.
  - Decide whether the active User Vault also has a private GitHub repo, private local repo, or another private remote-backed location.
  - Define a reversible migration sequence before moving files.
  - Define rollback points and backups.
  - Decide whether AF-3 uses an integration branch for the whole migration or smaller PRs with a protected checkpoint before file extraction.
  - Produce a pre-migration inventory of current Core, Vault, Generated, Runtime, Local Private, and Proposed Design Evidence paths.
  - Identify hardcoded single-repo assumptions in scripts, workflows, adapters, docs, and runtime manifests.
  - Exit when the migration sequence, backup plan, issue order, and stop conditions are explicit.

- **User Vault extraction**
  - Move the current account's `practices/`, `assets/`, `indexes/`, `usage/usage-aggregate.yaml`, vault-local docs, and reviewed imports into the active User Vault.
  - Keep raw local evidence ignored and local.
  - Preserve history where practical, but prioritize correctness and privacy over perfect file history.
  - Confirm no current User Vault content remains required by public Core defaults.
  - Define the User Vault repository or local path before moving files.
  - Create a Vault backup and verify it contains all canonical records and sanitized aggregate evidence.
  - Move only after split-aware checks can validate an arbitrary Vault.
  - Leave Core templates or fixtures empty and non-personal.
  - Exit when the active User Vault validates separately and Core no longer depends on its active records.

- **Public Core cleanup**
  - Keep reusable `workflows/`, `schemas/`, `scripts/`, `templates/`, runtime templates, adapter profiles, adapter quality rules, and product docs in Core.
  - Replace personal defaults with templates, examples, empty indexes, or documented capability pack deployment constraints.
  - Ensure Core does not publish the maintainer's active practices/assets as default product state.
  - Preserve blank-vault templates or generation logic in Core, while keeping blank-vault records empty and non-personal.
  - Separate Core-owned adapter profiles and quality checks from generated adapter outputs.
  - Decide whether tracked generated adapters remain in Core as distribution artifacts, move to Vault-derived build output, or become release artifacts.
  - Review `README.md`, `AGENTS.md`, `docs/usage.md`, `docs/deployment.md`, and adapter instructions for maintainer-specific wording.
  - Exit when a clean Core checkout can explain itself without requiring the `farmerhunter` User Vault.

- **Locator and config migration**
  - Update `~/.agent-foundry/config.yaml` semantics so `core_root` and `vault_root` may be different paths.
  - Keep `repo_root` only as a compatibility alias or derived field when appropriate.
  - Ensure agents can locate Core and Vault reliably from another project.
  - Define precedence for `AGENT_FOUNDRY_HOME`, explicit Core/Vault environment variables, local config, and current-directory markers.
  - Add clear failure messages when Core is found but Vault is missing, or Vault is found but Core tooling is missing.
  - Add context checks that identify whether the current operation is product project work, Foundry Vault operation, or Foundry Core maintenance.
  - Replace the current single `canonical_markers` model with separate Core markers and Vault markers.
  - Ensure workflows no longer validate a Vault by requiring Core-owned files such as `workflows/harvest-practices.md`.
  - Add command-line override support where needed for tests and migrations.
  - Exit when scripts can validate same-root compatibility mode, split maintainer mode, and blank-Vault mode.

- **Runtime deployment migration**
  - This parent issue is a coordination epic for migration-window close readiness.
  - Track sub-issues #42, #43, #46, #44, #51, #45, and #47 to avoid a single uncontrolled apply bucket.
  - Inventory installed Codex, Claude Code, Hermes, and ChatGPT adapter targets before migration.
  - Reinstall managed runtime files from the split Core plus active User Vault.
  - Preserve managed-block and managed-directory ownership markers.
  - Do not overwrite unmanaged runtime files.
  - Provide migration visibility for old path references, stale runtime files, adapter drift, and manual ChatGPT import requirements.
  - Update `scripts/install_foundry.py`, `scripts/sync_adapters.py`, runtime manifest handling, and deployment docs to consume selected Core/Vault roots.
  - Verify `~/.agent-foundry/config.yaml` is rewritten only after successful validation or explicit migration approval.
  - Treat ChatGPT as manual import; do not imply automatic update.
  - Exit when local runtimes can be refreshed from split Core plus active User Vault, stale-reference checks and rollback are visible, and canonical writes can safely resume through verified split roots.

- **Compatibility and validation**
  - Update scripts to accept separate `core_root` and `vault_root`.
  - Update consistency checks to validate the active Vault against Core schemas and workflows.
  - Update adapter publishing so generated outputs can be derived from an arbitrary Vault.
  - Verify blank-vault and current-user-vault scenarios separately.
  - Verify offline sync and usage aggregate behavior after split.
  - Confirm empty indexes and empty usage aggregates are valid, while missing/corrupt indexes still fail clearly.
  - Add fixtures or temporary test directories for combined repo, blank Vault, and current-user-like Vault validation.
  - Keep tests local and deterministic; do not require private remote access for public Core validation.
  - Verify generated adapter outputs do not leak inactive candidate/proposed records or private paths.
  - Preserve the substrate needed for later pack deployment: blank Vault first, pack canonical data second, refresh third.
  - Exit when consistency, adapter quality, activation, runtime dry-run, and split-root validation checks pass.

- **External-user readiness gate**
  - This parent issue is a post-window readiness gate and closes AF-3 only after split migration is validated.
  - Track reviews #48, #49, and #50 to cover clean public Core and runtime/Vault operating modes.
  - Treat #48 as blocked until current-user Vault records are physically split out of public Core through #54.
  - Treat #50 as blocked until canonical write/review scripts are Vault-root aware through #55 and nested product-project fixtures exist through #56.
  - Treat #49 as complete: blank/custom/current-user Vault operation passed review.
  - Test a clean setup using public Core plus a blank or new user Vault.
  - Confirm setup does not require maintainer-specific paths, private records, or personal adapters.
  - Confirm a user can choose a suitable Vault location: private Git repo, local-only repo, or other explicitly supported storage.
  - Document where the Vault should live and how agents remember or rediscover it.
  - Test nested usage: running harvest/refresh from inside a product project must locate the correct Core and Vault without confusing the product project with either.
  - Confirm setup docs clearly state what AF-3 does not include: implementing bootstrap pack deployment, optional pack UX, runtime-asset import, or memory-system implementation.
  - Exit when the project can truthfully say "public Core plus separate Vault works" without claiming AF-4 deployment/upgrade completion or AF-5 onboarding polish.

Planned GitHub issue sequence:

| Order | GitHub issue | Type | Owner role | Risk | Ready condition | Completion handoff |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | #27 Migration execution plan and inventory | Epic / Decision | Architect | High | AF-2 done, no open predecessor issues | User or structured Architect review before implementation starts |
| 2 | #28 Split-aware locator and context model | Epic | Architect | High | #27 defines root names, markers, and precedence | Batch checkpoint |
| 3 | #35 Split-root validation fixtures and checks | Task batch | Implementer with Architect-owned acceptance | Medium | #28 defines marker contract | Batch checkpoint with #28 |
| 4 | #29 Adapter generation from selected Vault | Task batch | Implementer | Medium | #28 marker contract and #35 validation helpers exist | Batch checkpoint |
| 5 | #30 Blank Vault initializer and validation | Task batch | Implementer | Medium | #35 validates empty Vault shape and preserves pack-deployment substrate | Batch checkpoint |
| 6 | #31 Maintainer Vault extraction plan and backup | Decision / Task | Architect | High | #28, #35, #29, and #30 pass in combined compatibility mode | Explicit user approval before moving private records |
| 7 | #32 Public Core cleanup and docs rewrite | Task batch | Implementer with Architect review | Medium | #31 defines extraction target and Core contents | Batch checkpoint |
| 8 | #33 Runtime deployment migration | Epic / Task batch coordination | Architect + Implementer | High | #28, #35, #29, and #30 pass; generated adapters are split-aware | User or structured Architect review before apply |
| 8.1 | #42 Layout compatibility markers and fail-closed checks | Task | Implementer | Medium | #33 approved as first child anchor | Batch checkpoint |
| 8.2 | #43 Read-only deployment migration planner | Task | Implementer | Medium | #33 approved; #42 complete | Batch checkpoint |
| 8.3 | #46 Cross-machine split refresh documentation | Task | Implementer | Medium | #33 approved; #42 and #43 complete | Batch checkpoint |
| 8.4 | #44 Gated split locator and selected-Vault dry-run | Task | Architect | High | #33 approved; #42, #43, and #46 complete; user approval for Vault init/copy and local locator write | Structured review handoff before runtime apply |
| 8.5 | #51 Runtime apply from selected User Vault | Task | Architect | High | #44 complete; planner reports `mode: split` and `safe_apply_candidate: yes`; explicit user approval for runtime writes | Structured review handoff |
| 8.6 | #45 Runtime stale-reference and rollback verification | Review | Reviewer | High | #51 and #33 complete | Structured review handoff |
| 8.7 | #47 Migration window close verification | Review | Reviewer | High | #44, #51, #45, and #46 complete | Batch checkpoint |
| 8.8 | #52 Make sync_status drift selected-Vault aware | Follow-up task | Implementer | Medium | #51 complete; selected-Vault runtime apply creates intentional adapter drift relative to tracked Core adapters | Batch checkpoint unless drift semantics block AF-3 close |
| 9 | #34 External-user readiness validation | Epic / Review batch coordination | Reviewer / Architect | High | #28, #31 through #33, #42-#47 complete; #54-#56 complete | User acceptance before AF-3 close |
| 9.1 | #54 Split active User Vault records out of public Core | Task / boundary cleanup | Architect | High | #47 complete; selected User Vault has preserved active records | Structured review handoff before #48 re-review |
| 9.2 | #55 Make canonical write and review scripts Vault-root aware | Task | Implementer with Architect review | High | #47 complete; split locator/config contract stable | Structured review handoff before #50 re-review |
| 9.3 | #56 Add nested product-project context fixture | Task | Implementer | Medium | #55 complete | Batch checkpoint with #55 before #50 re-review |
| 9.4 | #48 Clean public Core readiness | Review | Reviewer | High | #34 approved; #54 removes current-user Vault records from public Core defaults | Structured review handoff |
| 9.5 | #49 Split Vault operation readiness | Review | Reviewer | High | #34 approved; #47 confirms split runtime path and runtime migration checks | Structured review handoff |
| 9.6 | #50 Nested product-project context readiness | Review | Reviewer | High | #34 approved; #55 and #56 prove split-aware canonical write/review paths from nested contexts | Structured review handoff |

Execution order:

1. Start with Issues 1 and 2 as Architect-owned work. These set the root model, marker model, and stop conditions.
2. Let an Implementer batch Issues 3, 4, and 5 only after the execution contract says which files may change and how to verify blank/maintainer scenarios.
3. Keep Issue 6 Architect-owned because it moves privacy and repository-boundary decisions.
4. Let an Implementer help with Issue 7 only after Core cleanup rules are explicit.
5. Treat Issue 8 as a coordination parent for runtime migration.
6. Execute runtime migration children in this order: #42 -> #43 -> #46 -> #44 -> #51 -> #45 -> #47.
7. Apply #44 only after user approval for Vault init/copy and local locator write; runtime apply is split into #51.
8. Apply #51 only after explicit user approval for runtime writes.
9. Close the migration window only via #47 after split runtime behavior and rollback evidence are confirmed.
10. Complete the external-user readiness fixes in this order: #54, then #55, then #56. Re-run #48 after #54, and re-run #50 after #55 and #56.
11. Close AF-3 only through Issue 9 after #47 and #48-#50 pass, covering clean Core, active User Vault, blank Vault, runtime, and nested product-project checks.

Role-fit constraints:

- Architect owns final decisions about repository split shape, privacy boundary, marker contract, version compatibility, and external-user readiness.
- Implementer may execute bounded script/test/doc changes once the execution contract names allowed paths, root assumptions, and acceptance checks.
- Reviewer validates against AF-3 acceptance criteria, not merely against passing tests.
- Harvester runs only after meaningful workflow lessons emerge; AF-3 implementation details should not automatically become practices.

Stop conditions:

- A script would delete, move, or overwrite private Vault content without a verified backup.
- A migration would write to runtime paths without a dry-run showing managed ownership.
- Core validation depends on maintainer practices/assets.
- Vault validation depends on Core-owned `workflows/` files as Vault markers.
- Generated adapters include personal paths, raw evidence, inactive records, or future memory-system paths.
- The current context cannot distinguish product project, Foundry Vault operation, and Foundry Core maintenance.
- A proposed change collapses AF-3 split migration with AF-4 current-user deployment/upgrade migration, AF-5 onboarding, AF-7 runtime adapter framework work, AF-8 capability-system hardening, or later memory-system planning.

Minimum verification matrix:

| Scenario | Required checks |
| --- | --- |
| Current combined compatibility | Existing consistency, adapter quality, activation, runtime dry-run, and locator status pass. |
| Split current-user operation | Core root and active User Vault root validate separately; adapter generation and runtime dry-run use the selected Vault. |
| Blank Vault operation | Empty indexes and aggregate validate; adapter publishing reports empty/minimal output without copying current-user content. |
| Pack deployment substrate | The design preserves the sequence blank Vault -> pack canonical data deployment -> refresh, without treating packs as runtime-only helpers or a second source of truth. |
| Product project harvest context | Agent locates Core and Vault from outside both roots; product project is evidence source only. |
| Canonical write/review paths | Practice review, asset review, usage evidence, and aggregate updates resolve selected `vault_root` for Vault-owned records and never write to product project or public Core by accident. |
| Runtime migration | Codex, Claude Code, Hermes managed outputs are inventoried and dry-run before apply; ChatGPT manual import state is reported. |
| Privacy check | Public Core contains no required current-user Vault records, raw evidence, machine-local paths, secrets, or private adoption decisions. |

Migration close conditions:

| Window-close artifact | Required checks |
| --- | --- |
| #47 Migration window close verification | Split Core/private Vault runtime chain validated, stale references surfaced, migration logs archived, and rollback boundary published |
| #9 AF-3 completion | #48, #49, #50 complete after #54-#56, external-user readiness criteria satisfied, and AF-3 issue-chain state consistent with dependency gates |

Acceptance criteria:

- Public Core can be cloned without exposing or requiring the current account's private User Vault.
- The active User Vault is separate and private by default.
- Existing local Codex, Claude Code, Hermes, and ChatGPT workflows have a tested migration path.
- `core_root` and `vault_root` can be different paths and are both validated before canonical writes.
- Product project, Foundry Vault operation, and Foundry Core maintenance contexts are distinguishable before writes or runtime installs.
- A blank Vault can be initialized and checked without personal practices/assets, and later pack deployment can add canonical data without redefining blank Vault.
- Adapter generation and runtime install work from both the active User Vault and a blank/new user Vault.
- Rollback instructions exist for the split migration.
- No future memory-system storage is introduced as part of the split.

### M4: Current-User Deployment And Upgrade Migration

Goal: make the split Core/Vault system real for the current only production user before optimizing for hypothetical new users, and use this first real migration as the template for future major data-schema and program-structure upgrades.

Current operating reality:

- The only real user is currently `farmerhunter`.
- Agent Foundry is already deployed across multiple machines and multiple runtime types.
- The highest-priority risk is not new-user polish; it is that existing deployments diverge, keep writing to stale combined-root assumptions, cannot reliably find the same User Vault after the split, or cannot survive the next major schema/program upgrade.
- A local-only User Vault is not enough for this stage. The current user's Vault needs a reviewed private remote or equivalent sync substrate before all deployments can converge.
- This stage should produce an upgrade playbook, not only complete one Vault split. Future changes such as Vault schema versions, Core script layout changes, adapter packaging changes, capability-pack metadata, or memory-system record introduction should reuse the same discipline.

AF-4 sequence:

1. **Private User Vault remote plan**
   - Decide the private remote name, owner, visibility, and URL for `~/.agent-foundry/vault/agent-foundry-vault-farmerhunter`.
   - Define the Vault `.gitignore` and tracked/untracked boundary before initializing git.
   - Keep raw evidence, secrets, machine-local manifests, and sync state local-only.
   - Decide whether the first Vault commit preserves history or starts from a clean privacy boundary.
   - Require explicit approval before creating the private remote or pushing Vault records.

2. **Local Vault git initialization and first push**
   - Initialize git in the selected User Vault.
   - Commit canonical Vault records, indexes, sanitized usage aggregate, vault-local docs, and reviewed imports only.
   - Push to the approved private remote.
   - Verify the private remote is not public and does not contain local-only evidence.

3. **Deployment inventory**
   - List every existing deployment machine and runtime surface: Codex, Claude Code, Hermes, ChatGPT manual import, and any disabled or experimental runtime.
   - For each deployment, record Core path, Vault path, config path, runtime install path, branch/remote state, and whether it can reach the private Vault remote.
   - Do not assume all deployments share the same Core checkout location; do require the same active Vault path pattern unless explicitly overridden.

4. **Cross-machine migration drill**
   - On each deployment, pull or clone public Core.
   - Clone or pull the private User Vault into `~/.agent-foundry/vault/agent-foundry-vault-farmerhunter`.
   - Write or verify `~/.agent-foundry/config.yaml` with split `core_root` and `vault_root`.
   - Run root validation, selected-Vault adapter publish dry-run, runtime install dry-run or apply as appropriate, and stale-reference checks.
   - Verify ChatGPT manual import instructions remain explicit rather than pretending to be automated.

5. **Real workflow verification**
   - Run at least one ordinary `refresh practices and assets` path from an existing deployment.
   - Run one representative harvest/review/publish path against the selected Vault without writing to public Core or a product project by accident.
   - Verify `sync_status.py` output is understandable in split mode and does not misread selected-Vault generated runtime files as stale combined-root regression.
   - Verify another deployment can pull the Vault updates and refresh adapters.

6. **Major-upgrade readiness discipline**
   - Define how Core, Vault, Generated, Runtime, and Local Private layers advertise layout/schema/program compatibility.
   - Decide which version markers are authoritative for upgrade safety and which are only diagnostic.
   - Define a standard upgrade flow: inventory, preflight, backup, dry-run, apply, validate, runtime refresh, real workflow smoke test, cross-machine pull, and close report.
   - Define failure states: incompatible schema, unsupported Core/Vault pair, stale runtime adapter, missing rollback artifact, partial deployment, and ambiguous current context.
   - Ensure future major upgrades can be decomposed into decision, implementation, review, apply, and close-verification issues rather than ad hoc edits.

7. **Close report**
   - Produce a migration status matrix for all existing deployments.
   - Include an upgrade-readiness checklist that future schema/program migrations can reuse.
   - Document residual gaps, such as manually refreshed ChatGPT projects or machines intentionally left out of scope.
   - Only after this matrix passes should AF-5 new-user onboarding become the main priority.

Acceptance criteria:

- The current User Vault has a private remote or equivalent reviewed sync substrate.
- Every in-scope existing deployment can validate public Core plus selected private Vault.
- Existing deployments can refresh adapters from the selected Vault.
- At least one real harvest/review/publish workflow has been exercised after the Vault remote is in place.
- Cross-machine Vault updates can be pulled and used without falling back to the old combined Core.
- A reusable major-upgrade checklist exists and has been exercised against this split migration.
- Version/layout compatibility and failure states are explicit enough that future schema/program upgrades can fail closed before corrupting user data or runtimes.
- Public Core remains clean and does not regain current-user Vault records.
- Local-only evidence remains local and untracked.

Stop conditions:

- The Vault remote would be public or ambiguously visible.
- `.gitignore` would allow raw evidence, secrets, local runtime manifests, sync state, or machine paths into the private Vault remote.
- Any deployment cannot locate both Core and Vault with actionable diagnostics.
- A runtime install would overwrite unmanaged files.
- A workflow writes canonical Vault records into public Core or a product project.
- The upgrade path cannot identify current Core/Vault schema/layout versions or cannot say whether an apply step is safe.

### M5: Onboarding Experience

Goal: make a new Agent Foundry deployment usable through complete onboarding journeys, not through a loose collection of setup scripts, schemas, and docs.

AF-5 is scenario-driven. It starts from user activation paths and derives the required schemas, CLI commands, validation checks, runtime install behavior, and documentation from those paths.

The main question is:

```text
How does a user move from blank or unfamiliar state to a verified usable Agent Foundry workflow?
```

AF-5 should not start by implementing a marketplace, a broad pack registry, or advanced automatic capability discovery. Those remain later lifecycle work. AF-5 must still define the full lifecycle vocabulary so the MVP does not paint itself into a corner.

Capability pack lifecycle vocabulary:

```text
incubate
  -> identify or discover
  -> package snapshot
  -> review
  -> publish or export
  -> deploy or import into a User Vault
  -> activate or select
  -> refresh and install runtime outputs
  -> use and collect evidence
  -> update or merge
  -> deprecate, retire, or archive
```

AF-5 defined and validated the MVP path through this lifecycle: reviewed snapshot deployment into a selected Vault, activation as ordinary Vault records, refresh into runtimes, status verification, and rollback or disable behavior. AF-6 turns that model into a complete install and pack lifecycle. Marketplace channels, automatic pack discovery, broad update management, and advanced export polish remain later work.

Layer rule:

- A capability pack is an export/import snapshot and review artifact, not a runtime source of truth.
- Deploying a pack writes or updates ordinary User Vault records with provenance, pack membership metadata, and conflict history.
- After deployment, the selected User Vault owns the canonical practices, assets, indexes, and accepted payloads.
- `refresh` reads the current selected Vault plus Core adapter profiles, not live pack definitions.
- Runtime copies are installed from generated output or accepted Vault payloads through managed runtime/tool locations with receipts.
- Pack updates are reviewed releases governed by each pack's own contract. Do not regenerate a pack merely because an included canonical record changed unless Pack Relevance Review decides the change belongs inside that pack's promised use case.

Predefined packs and discovered packs are compatible with freeform Vault maintenance:

- Predefined packs are curated Core-distributed canonical data.
- Discovered packs are reviewed bundle proposals inferred from existing Vault records, workflows, and usage evidence.
- Deployment creates or updates ordinary Vault records with provenance and pack membership metadata.
- Pack membership is metadata, not ownership; a record may belong to no pack, one pack, or multiple packs.
- Pack updates must propose normal record changes and must not silently overwrite user-edited records.
- Users and agents can still create, edit, archive, or retire arbitrary practices and assets outside any pack.
- `refresh` reads current Vault records, not pack definitions, when generating adapters.

Primary onboarding journeys:

1. **Fresh install**
   - User obtains public Core.
   - User creates or selects a User Vault.
   - User initializes a blank but valid Vault.
   - User deploys the mandatory bootstrap pack into the Vault.
   - User selects local runtimes or accepts safe detected defaults.
   - User runs `refresh`.
   - System reports Core root, Vault root, enabled runtimes, manual targets, installed outputs, receipts, and the first normal workflow command.

2. **Add optional capability pack**
   - User already has Core plus a selected Vault.
   - User selects a pack such as multi-agent collaboration or future technical-documentation writing.
   - System stages the pack as a reviewed snapshot.
   - User reviews provenance, license, included records, executable payloads, permissions, conflicts, and runtime impact.
   - Deployment writes ordinary Vault records and payloads.
   - `refresh` publishes and installs only from the selected Vault.

3. **Import from existing runtime**
   - User has existing Codex skills, Claude Code instructions, Hermes skills, ChatGPT project materials, or local helper files.
   - System scans or accepts explicit paths as evidence.
   - Imported material is staged as candidates with provenance, not activated directly.
   - User reviews candidate practices/assets or rejected material.
   - Approved items become ordinary Vault records and are then refreshed into runtime outputs.

4. **Import from a product project**
   - A product project incubates reusable helper scripts, workflow docs, prompts, or templates.
   - The product project remains the evidence source.
   - The reusable subset is packaged as a candidate capability snapshot.
   - Project-local defaults are separated from reusable behavior and examples.
   - Deployment into the selected Vault happens only after review.
   - The source project is not treated as Core, Vault, or runtime truth.

5. **Cross-machine restore**
   - User clones or updates public Core on another machine.
   - User clones or pulls the private User Vault or starts from a chosen blank Vault.
   - Local locator records Core and Vault roots for that machine.
   - Runtime manifests and receipts are recreated locally.
   - `refresh` rebuilds runtime outputs from the selected Vault.
   - No runtime copy, machine-local path, or local adoption decision is inherited as canonical truth.

6. **Disable, rollback, or remove pack-sourced capability**
   - User can disable or retire pack-sourced records without deleting unrelated user-created records.
   - Runtime outputs are regenerated from current Vault state.
   - Receipts and status show whether old runtime files remain, were removed, or require manual cleanup.
   - Rollback restores runtime state without rewriting canonical Vault history unless explicitly requested.

Epics:

- **Onboarding journey contract**
  - Write the user-visible activation contract for each primary journey.
  - Define the exact starting state, user intent, required decisions, success report, failure states, rollback path, and first usable command.
  - Keep docs oriented around user journeys rather than internal implementation sequence.

- **Pack lifecycle and authority model**
  - Define pack states, manifest responsibilities, provenance, membership metadata, record copy/merge behavior, version compatibility, and conflict handling.
  - Keep pack deployment as snapshot import into ordinary Vault records.
  - Define same-ID same-version, newer-pack, local-modified, unrelated-ID-collision, deprecated, and retired conflict behavior.
  - Define update checks as reviewable diffs, not automatic overwrites.

- **Blank Vault plus bootstrap activation**
  - Keep blank Vault initialization genuinely blank: structure, metadata, empty indexes, and empty aggregate evidence only.
  - Deploy the mandatory bootstrap pack after blank Vault creation.
  - Identify the minimal public, reviewed, private-evidence-free records needed for harvest, asset discovery, refresh, review, and adapter publishing.
  - Verify a user can run the first normal workflow after deploying only the bootstrap pack and refreshing runtimes.

- **Optional capability pack path**
  - Use the same deployment mechanism for optional packs as for bootstrap.
  - Package multi-agent collaboration as the first optional pack only after bootstrap deployment works.
  - Use Tiny IPA's role-generic helper work as the validation evidence for a project-incubated optional pack.
  - Ensure optional packs can include practices, assets, docs, templates, examples, and executable payloads without becoming Core defaults or live runtime authorities.

- **Executable helper asset boundary**
  - Resolve #53 by defining where capability-owned executable helpers live, how they are reviewed, what permissions and dependencies they declare, and how they are installed or updated.
  - Do not run helper scripts directly from pack staging or the canonical Vault by default.
  - Install accepted executable payloads into managed machine-local runtime/tool locations with receipts.
  - Keep Core `scripts/` reserved for Agent Foundry platform machinery unless a reviewed exception labels a script as a temporary capability-helper candidate.

- **Runtime asset and project evidence import**
  - Define how to scan or accept explicit paths for existing Codex, Claude Code, Hermes, ChatGPT, product-project helper scripts, prompts, and workflow docs.
  - Stage imported material as evidence or candidates with provenance, license, security, and sensitivity review.
  - Route material to practice candidate, asset candidate, pack candidate, project-local decision, design note, discard, or future work before canonical mutation.
  - Avoid overwriting native runtime capabilities or product-project files.

- **Refresh, install, and status verification**
  - Confirm Core and Vault are located and validated before every setup or import action.
  - Confirm pack deployment writes canonical data into the selected Vault before refresh.
  - Confirm runtime targets are detected, enabled, disabled, or manual with clear reasons.
  - Confirm `refresh` generates adapters from Vault canonical records, not Core hidden state or live pack definitions.
  - Report which records are pack-sourced, imported, user-created, proposed, active, deprecated, retired, or skipped.
  - Report install receipts and manual ChatGPT import requirements.

Use-case derived implementation map:

| Use case | Schema/data needs | CLI/workflow needs | Validation/status needs | Runtime/docs needs |
| --- | --- | --- | --- | --- |
| Fresh install | Vault metadata, bootstrap pack manifest, pack membership metadata | first-run setup, `init-vault`, deploy bootstrap, refresh | root validation, blank-vault validation, bootstrap deployed, receipt status | quickstart, first normal command, ChatGPT manual note |
| Add optional pack | optional pack manifest, provenance, conflicts, permissions | stage pack, review diff, deploy pack, rollback/disable | conflict report, selected records, executable payload safety | optional pack docs, runtime impact report |
| Import existing runtime assets | import inbox records, candidate practices/assets | scan runtime or import explicit paths, route artifacts, review candidates | sensitivity/provenance/license checks, no direct activation | import guide, native runtime preservation notes |
| Import product-project capability | source-project evidence manifest, examples vs reusable defaults | package snapshot, separate project-local overlay, deploy reviewed subset | no product project writes, no Core pollution, path leak scan | pack authoring guide, project-overlay guidance |
| Cross-machine restore | local locator, runtime manifest, install receipt | clone/pull Core and Vault, validate, refresh | selected-output receipt, stale reference scan, manual target report | restore guide, deployment checklist |
| Disable or rollback | pack membership state, record lifecycle state, receipt history | disable/retire records, regenerate, rollback runtime install | old runtime file detection, rollback report | troubleshooting and cleanup guide |

AF-5 MVP deliverables:

- A journey-oriented onboarding guide that covers fresh install, optional pack deployment, runtime import, product-project import, restore, and rollback at the level currently implemented or explicitly future.
- A minimal capability pack manifest and deployment workflow that supports bootstrap and one optional pack without creating a third source of truth.
- A bootstrap pack built from public, reviewed canonical data.
- A first optional multi-agent collaboration pack candidate, validated against Tiny IPA helper evidence after the helper executable boundary is designed.
- CLI or workflow support for blank Vault creation, pack staging/deployment, selected-root refresh, and status reporting.
- An operation-context preflight that lets AF operations invoked from product projects, Core, Vault, generated output, or runtime directories prove their Core/Vault roots, allowed writes, and publish/install route before mutation.
- Validation fixtures for blank Vault, bootstrap-only Vault, optional-pack Vault, imported-runtime candidate, and product-project evidence source.
- Runtime install behavior that preserves managed markers, receipts, manual ChatGPT boundaries, and no direct execution from canonical stores.

Acceptance criteria:

- A new user can complete the Fresh Install journey and see a status report naming Core root, Vault root, deployed bootstrap pack, enabled runtimes, manual targets, receipts, and first usable commands.
- Bootstrap pack content is never confused with the maintainer's private Vault or with Core platform code.
- Optional packs and imported runtime/project assets are staged, reviewed, and selected before becoming canonical Vault records.
- Pack deployment and freeform practice/asset CRUD share the same Vault records and do not create parallel truth sources.
- Executable helper payloads have a reviewed Vault source, managed runtime/tool install path, dependency/permission declaration, and receipt before use.
- Cross-machine restore proves runtime state can be regenerated from public Core plus selected Vault rather than copied from another machine.
- Disable or rollback behavior can remove or supersede runtime outputs without erasing unrelated user-created Vault records.
- The onboarding flow preserves product project, Foundry Core, Foundry Vault, Generated, Runtime, and Local Private context separation.
- AF operations invoked from nested contexts display and verify their work context, evidence root, selected Core/Vault roots, allowed writes, forbidden writes, and selected-output publish/install receipt path.

Stop conditions:

- A pack design makes the pack a live runtime authority without an explicit live-dependency lifecycle.
- A bootstrap or optional pack contains private maintainer evidence, machine-local paths, secrets, or current-user-only defaults.
- A helper script must be copied into Core `scripts/` because no capability-owned executable boundary exists.
- A setup flow cannot tell the user which layer owns a record or runtime file.
- A runtime install would execute from pack staging or the canonical Vault without managed install, dependency check, receipt, and rollback semantics.
- A new-user quickstart requires understanding the maintainer's personal history or private Vault.

Planned GitHub issue sequence:

| Order | GitHub issue | Type | Owner role | Risk | Ready condition | Completion handoff |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | #73 AF5 onboarding journey contract | Decision / Epic | Architect | Medium | AF-4 close report accepted or explicitly waived for planning only | User or structured Architect review before implementation issues start |
| 2 | #74 Pack lifecycle and authority model | Decision | Architect | High | #73 defines fresh install, optional pack, import, restore, and rollback paths | Structured review handoff |
| 3 | #53 Capability-owned executable helpers | Decision | Architect | Medium | #74 names executable payload boundary and runtime receipt expectations | Structured review handoff before helper implementation |
| 4 | #75 Minimal capability pack manifest and fixtures | Task batch | Implementer with Architect review | Medium | #53 and #74 define fields, lifecycle states, and conflict behavior | Batch checkpoint |
| 5 | #76 Blank Vault plus bootstrap deployment path | Task batch | Implementer | Medium | #75 fixtures exist; blank Vault initializer validates selected roots | Batch checkpoint |
| 6 | #77 Bootstrap capability pack content | Harvester / Architect | Medium | #76 can import pack snapshot into Vault records | Human review of included canonical records before activation |
| 7 | #89 Operation context preflight and nested-context guard | Task | Architect then Implementer | Medium | #77 can deploy bootstrap content; nested-context confusion has concrete evidence | Reviewer handoff before #78 starts |
| 8 | #78 Fresh install command and status report | Task batch | Implementer | Medium | #77 can deploy into blank Vault and #89 can prove operation context before mutation | Batch checkpoint with runtime dry-run evidence |
| 9 | #79 Optional multi-agent capability pack candidate | Evidence / Task | Architect + Harvester | Medium | #76 works; #53 defines executable helper payload boundary | Review before packaging Tiny IPA helper evidence |
| 10 | #80 Runtime asset import path | Task batch | Implementer with Harvester review | Medium | #74 import staging and artifact routing model defined | Batch checkpoint |
| 11 | #81 Cross-machine restore and rollback onboarding | Review / Task | Reviewer + Architect | High | #78 selected-Vault refresh and receipts work locally | Structured review handoff |
| 12 | #82 AF5 end-to-end onboarding validation | Review | Reviewer | High | #53 and #73-#81 plus #89 complete or explicitly deferred with rationale | User acceptance before AF-5 close |

Execution order:

1. Start with Architect-owned journey and authority decisions so implementation does not center on a schema or script before the activation path is clear.
2. Resolve #53 before packaging Tiny IPA-style helper scripts as reusable capability payloads.
3. Build pack manifest fixtures before bootstrap content so bootstrap can be validated as one instance of the general deployment mechanism.
4. Build the mandatory bootstrap path before optional packs.
5. Add operation-context preflight before fresh install polish so first-run commands and nested product-project harvests prove which layer owns each read, write, publish, install, and receipt.
6. Treat the multi-agent pack as the first optional validation case, not as a blocker for fresh install.
7. Keep runtime import and product-project import behind the same staging/review rules so imported material does not bypass harvest discipline.
8. Close AF-5 only with an end-to-end validation issue that runs the user journey, not merely individual script tests.

#### AF-5 End-to-End Validation Report (#82)

Status: Reviewer validation completed on 2026-06-12 against `af5/integration`.

Findings first:

- No blocking AF-5 onboarding readiness findings remain for Architect acceptance.
- AF-5 is ready for Architect acceptance and a human AF-5 close / final `af5/integration` to `main` decision.
- Final AF-5 close, final integration to `main`, issue closure, and any real selected Vault or runtime apply remain human-gated.
- Current validation did not mutate the real selected User Vault, real runtime files, local config, private remotes, or ChatGPT project state.

Evidence map:

| Journey / boundary | Evidence | Reviewer conclusion |
| --- | --- | --- |
| Fresh install / blank Vault / bootstrap deployment / first usable command | #76, #77, #78, #89; `scripts/install_foundry.py --fresh-install`; `scripts/test_bootstrap_pack_deployment.py`; `scripts/sync_status.py` setup/status report | Temp blank Vault can initialize, deploy `pack.bootstrap.minimal`, publish generated output, report runtime dry-run/receipt status, keep ChatGPT manual, and name `python3 scripts/sync_status.py` as first usable command. |
| Optional capability pack path | #75 and #79; `fixtures/capability-packs/optional-multi-agent`; `scripts/check_capability_pack_fixtures.py` | Optional pack fixture validates as a candidate/stage-only snapshot with provenance, inert helper payload metadata, no direct runtime install, and no third source of truth. |
| Runtime asset import path | #80; `scripts/import_runtime_assets.py`; `scripts/test_import_runtime_assets.py` | Explicit runtime/source path import stages review evidence under the selected Vault inbox only after operation-context checks. It does not activate records, overwrite adapters, execute scripts, or scan broad private runtime trees by default. |
| Product-project capability candidate | #79 / Tiny IPA evidence; operation-context harvest evidence | Tiny IPA remains product-project evidence only. Reusable role-generic helper surfaces are represented as optional pack candidates; project-local defaults, Project ids, cache paths, branch state, and mutating apply behavior are excluded or marked overlay/rejected. |
| Cross-machine restore and rollback/disable | #81; `workflows/install-adapters.md`; `scripts/test_deployment_helpers.py`; `scripts/test_bootstrap_pack_deployment.py`; `scripts/test_adapter_install_receipt.py` | Restore is documented and tested as recreation from public Core plus selected Vault/generated output, not copying another machine's runtime/local state. Temp rollback/disable regression preserves unrelated Vault records and removes only managed runtime copies/blocks. |
| Core / Vault / Generated / Runtime / Local Private boundaries | #89 plus `scripts/operation_context.py`, selected-output receipt status, `scripts/sync_status.py`, `scripts/test_operation_context.py`, `scripts/test_foundry_roots.py`, selected-output adapter quality check | Operation context identifies work context, selected Core/Vault roots, generated output route, allowed reads/writes, forbidden writes, manual targets, and receipt state before publish/install/status flows. Selected-output receipt is authoritative in split mode; Core adapters are secondary diagnostics. |

Verification run for #82:

- `python3 scripts/check_consistency.py` passed.
- `python3 scripts/check_capability_pack_fixtures.py` passed.
- `python3 scripts/test_bootstrap_pack_deployment.py` passed.
- `python3 scripts/test_import_runtime_assets.py` passed.
- `python3 scripts/test_adapter_install_receipt.py` passed.
- `python3 scripts/test_operation_context.py` passed.
- `python3 scripts/test_deployment_helpers.py` passed.
- `python3 scripts/test_foundry_roots.py` passed.
- `python3 scripts/check_activation.py` passed.
- `python3 scripts/check_adapter_quality.py --surface selected-output --generated-root '/Users/jinghuliu/.agent-foundry/generated/agent-foundry-adapters'` passed.
- `python3 scripts/sync_status.py` completed read-only. It reported selected-output receipt in sync for Codex, Claude Code, and Hermes; ChatGPT remains manual. It also reported `deployed_pack: none detected` for the current maintainer Vault, which is expected because the fresh-install bootstrap deployment acceptance is temp/blank-Vault scoped and was not applied to the real selected Vault.

Residual gaps and explicit deferrals:

- Physical second-machine execution remains deferred; #81 covered local temp restore/rollback simulation and documents the physical-machine gap.
- ChatGPT manual import and cleanup remain manual by design; no live ChatGPT project update was attempted.
- Optional pack deployment beyond the MVP candidate fixture remains later work; #79 validates the candidate boundary, not real optional-pack rollout.
- Real capability-owned helper install remains deferred until a reviewed helper install path is selected; helper payloads stay declared/inert in pack fixtures.
- Advanced capability discovery, marketplace behavior, broad pack registry, automatic update management, and AF-9-style discovery remain future work.
- Memory-system implementation remains out of scope for AF-5 and should not be introduced by AF-5 close.
- Current maintainer Vault bootstrap deployment state is not evidence of new-user onboarding success; temp blank-Vault fixtures are the acceptance evidence for that journey.

Human Decision Contract draft:

Decision needed:
Authorize whether AF-5 may close and whether `af5/integration` may proceed to final human-gated integration toward `main`.

Why human input is required:
AF-5 close changes roadmap maturity state, and final `af5/integration` to `main` integration is explicitly human-gated by the AF5 branch contract. Agents may validate and route the issue, but must not close #82/#73 or merge to `main` without explicit authorization.

Agent conclusion:
Reviewer validation finds AF-5 onboarding MVP ready for Architect acceptance and human close/main-integration decision. Required AF-5 journeys have evidence, checks pass, layer boundaries remain intact, and known gaps are labeled as explicit deferrals rather than hidden blockers.

Options:

1. Approve Architect acceptance and human AF-5 close / final integration planning.
2. Request additional validation before AF-5 close, such as physical second-machine execution or a live ChatGPT manual import check.
3. Defer AF-5 close and keep #82/#73 open with the residual gaps named above.

Consequences:

- If approved: Architect may accept #82, prepare the final human-gated `af5/integration` to `main` path, and route AF-5 close decisions without merging or closing until explicitly authorized.
- If additional validation is requested: keep #82 open or create targeted follow-up issues for the requested evidence.
- If deferred: AF-6 and later lifecycle or memory-readiness work should not start from a claimed AF-5 baseline.

Explicit authorization phrases:

- `批准 AF5 close`
- `批准 af5/integration 合入 main`

### AF-6 / M6: Existing Foundry Lifecycle Completion

Goal: turn the AF-5 onboarding model into a complete, repeatable product lifecycle before adding memory record types. AF-6 is not only "new user install"; it also covers already-installed users who need to check, deploy, update, disable, or restore capability packs.

AF-6 starts from user journeys and derives implementation work from them. It should not begin with isolated scripts or schemas.

Primary journeys:

1. **Fresh install to first usable workflow**
   - User obtains public Core, selects or creates a Vault, deploys the mandatory bootstrap pack, configures local runtimes, refreshes generated output, and sees the first normal command.
   - AF-6 should reduce required manual knowledge, but it does not need a polished marketplace or fully automated ChatGPT import.

2. **Existing install status and repair**
   - User already has Core plus Vault and asks whether the installation is coherent.
   - Status must report Core version, Vault root, Vault validity, deployed packs, generated output, runtime receipts, manual targets, stale references, and next safe actions without writing.

3. **Known pack deploy or apply**
   - User has a local or explicitly named remote pack snapshot and wants to deploy it into an existing Vault.
   - The workflow stages, validates, plans, and applies reviewed records into the Vault; the pack snapshot remains transfer evidence, not live runtime authority.

4. **Known pack version check and update**
   - User has a deployed pack and an available newer snapshot.
   - The workflow compares pack id, version, manifest compatibility, included record set, per-record hashes, local Vault edits, executable payload metadata, and runtime impact before proposing update, skip, fail, or merge.

5. **Optional pack to runtime availability**
   - User deploys an optional pack, then refreshes and installs generated runtime output.
   - AF-6 should validate this with the multi-agent collaboration pack as the first real optional capability candidate, while keeping executable helper payloads inert until the helper install boundary is implemented.

6. **Disable, retire, rollback, and restore**
   - User disables a pack-sourced capability or restores another machine.
   - The workflow separates Vault lifecycle state, pack membership metadata, generated output, runtime install receipts, manual targets, and rollback artifacts.

AF-6 epics:

- **AF6 lifecycle planning and issue decomposition**
  - Align AF/M numbering and version mapping.
  - Create a single AF-6 Epic with dependency-gated child issues.
  - Keep memory readiness, memory implementation, and advanced pack discovery out of AF-6 unless they are explicit constraints.

- **Complete install experience**
  - Define and implement the preferred install command path for a normal user.
  - Preserve explicit Vault location choice and support the reviewed default path policy.
  - Produce a success report that names Core root, Vault root, deployed bootstrap pack, generated output, runtime receipt state, manual ChatGPT status, and first safe command.
  - Keep `--dry-run` or report-only behavior available before writes.

- **Pack state and installed-pack metadata**
  - Record deployed pack identity, version, manifest hash, included record hashes, deployment time, source path or URL, and conflict decisions in the selected Vault.
  - Do not make pack metadata a second source of truth for active practices or assets.
  - Keep ordinary Vault CRUD valid after pack deployment.

- **Generic pack plan/check/apply**
  - Support optional pack staging and validation beyond `mandatory_bootstrap`.
  - Plan add/update/skip/fail/merge outcomes before canonical writes.
  - Fail closed for same-version different-hash snapshots, unrelated id collisions, incompatible schema ranges, unknown provenance, and unapproved executable payload install.

- **Pack update and relevance review**
  - Implement or document how a known pack snapshot is compared with current Vault state.
  - Require Pack Relevance Review before regenerating or versioning a pack from changed canonical records.
  - Do not regenerate a pack merely because any included canonical record changed outside the pack's selected contract.

- **Optional multi-agent pack**
  - Promote the current candidate fixture into the first deployable optional pack only after generic pack plan/apply is available.
  - Keep Tiny IPA as evidence, not a runtime dependency.
  - Keep helper scripts inert or metadata-only until managed helper install, dependency checks, permissions, and receipts exist.

- **Runtime refresh, receipts, and status**
  - Ensure generated output and runtime install read the selected Vault and selected generated output, not stale Core adapter templates.
  - Preserve managed markers, receipts, manual ChatGPT boundaries, stale-reference scans, and rollback visibility.

- **Review, validation, and documentation**
  - Validate fresh install with a temp blank Vault.
  - Validate optional pack apply/update conflict behavior with fixtures.
  - Validate non-new-install status on the current split setup.
  - Keep docs journey-oriented: install, status, deploy pack, update pack, disable/rollback, restore.

AF-6 non-goals:

- Marketplace, registry search, or automatic remote discovery.
- Broad automatic capability-pack discovery from arbitrary work history.
- Memory-system storage, memory harvest routing, semantic/vector/graph indexes, or MCP memory tools.
- Executing helper scripts directly from pack staging, product projects, or canonical Vault payload paths.
- Treating a pack snapshot as live authority after deployment.

AF-6 acceptance criteria:

- A blank or existing installation can report its Core/Vault/runtime/pack state before mutation.
- Fresh install can initialize a valid Vault, deploy the mandatory bootstrap pack, publish generated output, and dry-run or apply managed runtimes according to the local manifest.
- A known optional pack can be staged, validated, planned, reviewed, deployed into the selected Vault, refreshed into generated output, and represented in status.
- Pack update checks distinguish unchanged, newer clean update, newer local-edit merge, same-version hash mismatch, incompatible schema, unknown provenance, and executable-payload block states.
- Pack disable or rollback does not delete unrelated Vault records and reports Vault lifecycle state, generated output impact, runtime receipt state, and manual targets separately.
- Core/Vault/Generated/Runtime/Product Project contexts are displayed or validated before writes and installs.
- Human review gates remain visible for pack activation, privacy/security/trust decisions, destructive changes, runtime apply when unmanaged targets would be touched, and final merges to `main`.
- `check_consistency.py`, capability pack fixture checks, install/status tests, runtime receipt tests, and operation-context tests cover the lifecycle claims they make.

Suggested AF-6 issue order:

| Order | Work | Type | Owner Role | Risk | Depends On | Handoff |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | #97 AF-6 Epic and stage labels | Epic/Task | Architect | High | AF-5 closed | Human-visible planning checkpoint |
| 2 | #98 Install UX contract and command map | Decision | Architect | High | #97 | Structured review |
| 3 | #99 Pack state metadata and installed-pack index | Decision | Architect | High | #97 | Structured review |
| 4 | #106 Generic pack plan/check for known local snapshots | Task | Implementer | Medium | #98 and #99 | Batch checkpoint |
| 5 | #100 Optional pack apply into selected Vault | Task | Implementer | High | #99 and #106 | Reviewer + Architect acceptance |
| 6 | #101 Pack update comparison and conflict handling | Task | Implementer | High | #99 and #100 | Reviewer + Architect acceptance |
| 7 | #102 Install/status repair for existing deployments | Task | Implementer | Medium | #98 | Batch checkpoint |
| 8 | #103 Optional multi-agent pack deployment path | Task/Decision | Architect + Implementer | High | #100 and #101 | Structured review |
| 9 | #104 Disable/retire/rollback pack lifecycle | Task | Implementer | High | #100, #101, and #102 | Reviewer + Architect acceptance |
| 10 | #105 AF-6 end-to-end validation and close review | Review | Reviewer | High | all AF-6 child issues | Human close/main-integration decision |

### AF-7 / M7: Runtime Adapter Framework And Trae Support

Goal: make Agent Foundry adapter publishing runtime-aware and support Trae CN through a verified global Skill path that keeps the user's day-to-day Trae setup simple.

AF-7 is adapter and runtime UX work. It does not start memory-system design or implementation. See `docs/runtime-adapter-framework-and-trae.md` for the current design.

Design areas:

- **Runtime adapter framework**
  - Define a portable adapter model between canonical practices/assets and runtime-specific outputs.
  - Track source canonical ids, versions, generator versions, target runtime, activation scope, human gates, and managed-file ownership.
  - Make generated output and installed runtime state comparable through status, dry-run, diff, and apply flows.

- **Trae CN global-first UX**
  - Publish Trae global Skills under `~/.trae-cn/skills` as the preferred reusable setup path.
  - Keep `.agents/skills` as a portable shared-skill option where compatible.
  - Use project overlays only when behavior is genuinely project-specific.
  - Do not write Trae private application state without a supported public import/export contract and explicit human approval.

- **Multi-agent role projection**
  - Project Architect, Implementer, Reviewer, Verifier, and Harvester behavior into Trae Skills or role instructions usable by SOLO Agent.
  - Keep canonical multi-agent assets runtime-neutral where possible.
  - Add Trae-specific wrappers only for activation, install path, UI wording, or future public Trae schemas.

- **Canonical update compatibility**
  - Ensure future canonical asset updates can refresh Trae outputs without forking practice logic.
  - Detect fresh, stale, drifted, unmanaged, missing, blocked, and unknown runtime states before writes.
  - Preserve fail-closed behavior for malformed or ambiguous metadata.

- **Long-running use and sync UX**
  - Show whether canonical records, generated adapters, installed Trae files, and project overlays are fresh.
  - Provide repair actions in user terms: pull, publish adapters, dry-run install, apply install, manual import, or reopen Trae.

Current GitHub records:

| Record | Purpose | Status |
| --- | --- | --- |
| #134 | AF-7 Epic for runtime adapter framework and Trae support. | In Progress |
| #135 | Historical baseline batch PR. This merged design, implementation, live Trae apply, and first validation before the child-issue plan was reconstructed. Do not use it as the AF-7 planning model. | Merged |
| #136 | Evidence issue for real Trae global Skill discovery, role UX, project instruction interaction, and project-overlay need. | Done |
| #138 | Corrective planning issue to reconstruct the AF-7 child issue plan and governance record. | Review |
| #139 | Review issue for auditing the merged #135 baseline scope and residual risks. | Done |
| #140 | Accepted decision for the Trae user-facing role invocation and project-overlay contract. | Done |
| #141 | Task issue for runtime adapter profile and selected-output contract hardening. | Inbox |
| #142 | Task issue for Trae sync, refresh, and repair UX validation. | Ready |
| #143 | Task issue for project-overlay compatibility and multi-agent coordination scenarios. | Done |
| #145 | Task issue for Trae SOLO mode and role automation planning output. | Done |
| #147 | Task issue for idle/resume Skill rehydration and collaboration transition gates. | Planning |
| #144 | Final AF-7 acceptance gate and Epic readiness review. | Inbox |

Child issue dependency order:

1. #138 repairs the Epic planning surface and records the governance correction.
2. #139 audits the already-merged #135 baseline before downstream hardening.
3. #136 supplies Trae runtime and UX evidence; #140 accepted the user-facing contract decision.
4. #141 follows #139 for adapter contract hardening.
5. #142 and #143 follow #136 plus #140 for sync/repair UX and project-overlay/multi-agent scenarios.
6. #145 follows #140 and #143 if Trae SOLO is accepted as the complex multi-role orchestration path.
7. #147 follows the observed #145/#146 collaboration-state drift and hardens idle/resume rehydration plus `needs:*` transition gates before final readiness review.
8. #144 reviews #136 and #138 through #143 plus #145 and #147 before any AF-7 completion or Epic closure decision.

Acceptance criteria:

- Trae is represented as a target runtime in profiles, docs, validation, and status.
- A generated Trae global Skill can be dry-run, installed, detected, refreshed, and repaired.
- Existing multi-agent assets can project into Trae without duplicating canonical logic.
- Project overlays remain optional and separated from global setup.
- Runtime status distinguishes canonical, generated, installed, project, unmanaged, stale, and conflict states.
- #134 drives AF-7 runtime adapter framework and Trae support through child issues #136 and #138 through #145 plus #147.
- Existing former-AF7 capability-hardening records are renumbered to AF-8 and held until AF-7 completes.
- No additional AF-7 implementation work starts from the Epic or the historical baseline PR alone; every new implementation, evidence, decision, or review step must enter through a scoped child issue.
- No memory-system directories, schemas, storage, MCP tools, or design work are introduced.

### AF-8 / M8: Capability System Hardening

Goal: harden the AF-6 capability system under realistic long-running, multi-user, multi-machine, multi-runtime, drift, restore, parser/schema, lifecycle, and scheduler-state scenarios.

AF-8 is capability-system work. It does not start memory-system design or implementation. Existing GitHub records #119 through #127 were originally created as AF-7 work and are held as AF-8 records after the AF-7 Trae/runtime adapter reorder.

Hardening areas:

- **Scenario matrix and acceptance gates**
  - Build a concrete scenario matrix for Core, selected Vault, generated output, runtime installs, local config, and Project scheduler state.
  - Classify each scenario by expected status, allowed reads, allowed writes, forbidden writes, failure mode, and repair hint.

- **Multi-user and multi-machine operation**
  - Validate one Core with one Vault, switched Vaults, multiple Core checkouts, separate users, moved Core paths, moved generated roots, missing Vaults, and stale receipts.
  - Keep live runtime and private Vault mutation behind explicit authorization; use temp fixtures for validation.

- **Long-running agent sync and activation UX**
  - Validate the experience where agents start after remote Core progress, stale generated output, stale installed runtime files, or selected-output receipt drift.
  - Make repo freshness, generated-output freshness, runtime install freshness, and manual-target freshness visible as separate states.
  - Ensure users can tell whether practices and assets are actually effective in Codex, Claude Code, Hermes, ChatGPT/manual import, and future runtime targets.

- **Runtime drift and manual target policy**
  - Distinguish selected-output receipt authority from Core reference diagnostics.
  - Keep disabled/manual targets from producing false failure signals.
  - Keep ChatGPT explicit as manual import unless a future managed target is deliberately designed.

- **Pack metadata, lifecycle, and rollback robustness**
  - Validate parser/schema behavior, duplicate keys, reordered fields, malformed metadata, same-version hash mismatch, local edits, disable/retire, generated-output exclusion, and partial-write preflight.
  - Preserve the rule that malformed or ambiguous metadata fails closed before writes.

- **Installer and first-run UX**
  - Audit the actual command path from Core checkout through Vault selection, bootstrap pack deployment, generated output publish, status, dry-run install, reviewed apply, and repair.
  - Make failure states actionable without silently inferring private Vault or runtime paths.

Acceptance criteria:

- #119 through #127 or their successors cover practical boundary scenarios and are synchronized in the GitHub Project as AF-8 records.
- Status/install/publish/lifecycle flows distinguish Core, Vault, Generated, Runtime, Local Private, manual target, and Project scheduler state.
- Temp-root tests or evidence cover stale runtime after remote update, stale generated output after Core/Vault change, second-machine onboarding, receipt drift, manual ChatGPT boundary, and lifecycle rollback behavior.
- Repair guidance is explicit and safe: fetch/pull, publish generated output, dry-run install, reviewed apply, manual import, or route to human review.
- No memory-system directories, schemas, storage, MCP tools, or design work are introduced.

### AF-9 / M9: Advanced Capability Pack Discovery and Lifecycle

Goal: improve whether Agent Foundry can recognize, maintain, and export higher-level capability packs that emerge from repeated work after the basic AF-6 pack lifecycle exists.

This is intentionally later than repository hygiene, productization, physical split migration, current-user deployment and upgrade migration, onboarding, lifecycle completion, runtime adapter framework work, and capability-system hardening. Do not use this milestone to delay AF-1 through AF-8. AF-6 owns the complete install experience, basic pack status/plan/apply/update/disable lifecycle, and first optional multi-agent collaboration pack deployment path. AF-7 makes adapters runtime-aware and adds Trae support. AF-8 hardens the actual capability system in realistic user/runtime scenarios. AF-9 is for automatic discovery, advanced lifecycle optimization, export polish, and maintenance of emergent packs.

Capability packs are not the same as individual assets. A future capability pack may bundle practices, assets, workflows, templates, adapter snippets, examples, configuration profiles, dependency metadata, and export/install behavior around a recurring user goal such as multi-agent collaboration or technical documentation writing.

Epics:

- **Capability candidate detection**
  - Define when repeated practice/asset/workflow co-activation suggests an emergent capability.
  - Let agents propose capability candidates during harvest, asset discovery, or lifecycle review.
  - Avoid requiring humans to predefine all future capability categories.

- **Capability pack schema evolution**
  - Extend the AF-5 manifest only when usage proves more fields are needed.
  - Keep schema changes compatible with deployed Vault records and pack membership metadata.

- **Review and activation lifecycle**
  - Define states such as detected, candidate, proposed, active, deprecated, split, and merged.
  - Preserve human review before an emergent capability becomes active or exportable.
  - Define how capability boundaries are revised when usage evidence shows a pack is too broad, too narrow, or overlapping.

- **Export and install model**
  - Define how an approved capability pack can be exported, installed, or reused without carrying this user's private vault content.
  - Reuse Core/Vault split, generated artifact policy, adapter publishing, and runtime install safeguards.

Acceptance criteria:

- Capability packs are modeled as emergent, reviewable bundles rather than human-predeclared categories.
- Agents can propose capability candidates from evidence, but cannot activate or publish them without review.
- Exportable packs do not include local-private evidence, personal vault content, or future architecture concepts as current substrate.
- The design proves at least one existing capability cluster could be packaged without weakening Core/Vault boundaries.

### AF-10 / M10: Memory-System Readiness Design

Goal: define memory as an adjacent future capability without implementing storage yet.

AF-10 does not begin until explicitly authorized. It is intentionally after runtime adapter framework work, capability-system hardening, and advanced capability-pack lifecycle planning.

Epics:

- **Memory record taxonomy**
  - Draft record types such as research memo, source digest, concept note, project fact, decision record, open question, profile update, practice candidate, and skill candidate.
  - Keep these as proposed until implementation.

- **Evidence and privacy model**
  - Decide raw evidence storage rules.
  - Decide whether raw ChatGPT exports ever enter Git.
  - Define encryption, local-only, shared aggregate, retention, and high-stakes metadata expectations.

- **Routing and save levels**
  - Define memory harvest routing separately from practice harvest.
  - Preserve levels such as raw only, summary, research/design preserved, candidate canonical records, and adapter/runtime impact.

- **Knowledge-to-practice promotion**
  - Define when knowledge remains reference material.
  - Define when knowledge can become a practice, asset, workflow, or adapter update.
  - Preserve rejected-as-practice reasoning.

- **MCP boundary**
  - Prefer read-only memory resources first.
  - Treat write operations as propose/validate/review/apply, not direct arbitrary writes.
  - Require proof that the write target is current capability.

Acceptance criteria:

- Memory-system design can be reviewed without creating future directories.
- Open questions remain visible.
- No automatic memory writing exists.

### AF-11 / M11: Memory Implementation Home Decision

Goal: decide the implementation home for memory-system work using evidence from AF-1 through AF-10.

AF-11 is a decision stage, not implementation. It does not authorize creating memory directories, schemas, MCP write tools, or storage.

Decision options:

- **In-repo extension**
  - Best if memory records are a natural extension of the User Vault and Core boundaries are clean.
  - Risk: repo grows too broad and mixes personal knowledge with product machinery.

- **Monorepo package**
  - Best if Core, Vault, adapters, and memory modules need shared scripts and schemas but independent packaging.
  - Risk: more tooling and release complexity.

- **Sibling repository**
  - Best if memory system should be a separate product or vault that depends on Agent Foundry governance.
  - Risk: cross-repo coordination and duplicated workflow code.

- **Forked experimental repository**
  - Best for fast exploration with permission to break structure.
  - Risk: useful work may be hard to merge back, and fork may drift from governance practices.

- **User-vault convention**
  - Best if memory should mostly be a directory/schema convention inside each user's vault.
  - Risk: weak product boundary if tooling remains implicit.

Decision criteria:

- Does memory need to be reusable by other users?
- Does it require raw/private evidence in the same Git repository?
- Does it share enough lifecycle machinery with practices/assets to justify one Core?
- Can generated outputs be reproduced cleanly?
- Can MCP and runtime adapters remain safe?
- Can a new user initialize a blank vault without personal content?

Acceptance criteria:

- Decision record names the chosen option and rejected alternatives.
- Future implementation plan has file boundaries, data flow, validation, privacy policy, and rollback path.

## Future Memory-System Implementation

Goal: implement a reviewed memory/knowledge MVP only after Foundry lifecycle, runtime adapter framework work, capability-system hardening, memory readiness, and implementation-home decisions are complete, and only after explicit user authorization.

Expected scope will be defined by AF-10 and AF-11. Until then, memory-system implementation is a future placeholder, not a license to create memory directories, schemas, or MCP write tools now.

## Work Not To Do Yet

- Do not create `memory/`, `knowledge/`, `research_memos/`, or `project_memory` directories.
- Do not implement automatic memory writing.
- Do not add semantic/vector/graph indexes.
- Do not add MCP write tools.
- Do not import raw ChatGPT exports.
- Do not implement memory-system design or implementation before explicit user authorization.
- Do not refactor adapters or runtime install behavior outside reviewed AF-7 adapter framework scope.

## Immediate Next Planning Tasks

1. Treat AF-6 as merged and complete through #116 and #105.
2. Treat the Trae/runtime adapter framework work as the active AF-7 stage.
3. Use #134 as the AF-7 runtime adapter framework and Trae support Epic.
4. Use #138 to complete the AF-7 governance repair and reconstructed child issue plan.
5. Use #139 as the next Review gate before #141 downstream hardening.
6. Release #142 and #143 as the next Ready AF-7 validation tasks after accepted #140.
7. Keep #145 in Inbox until #143 validates SOLO versus fallback behavior.
8. Use #144 as the final AF-7 readiness review before any Epic completion decision.
9. Keep #119 through #127 held as AF-8 capability-system hardening records.
10. Keep the existing AF-8 implementation PRs held until AF-7 is complete or the user explicitly resumes them.
11. Keep AF-9 advanced capability-pack discovery out of implementation until AF-8 hardening evidence is accepted.
12. Do not begin AF-10/AF-11 memory-system readiness or implementation-home work until explicitly authorized by the user.
