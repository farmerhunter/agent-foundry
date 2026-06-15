# Agent Foundry System Design

## Purpose

Agent Foundry, short for Agent Capability Foundry, is a personal system for turning real work experience into reusable, deployable agent capabilities across environments such as Codex, ChatGPT, Claude Code, Hermes, and similar tools.

The goal is not to maintain a pile of prompts. The goal is to run a closed loop:

```text
discover repeated work and reusable lessons
  -> distill canonical practices
  -> package reusable assets
  -> publish heterogeneous adapters
  -> record usage evidence
  -> aggregate safe usage statistics
  -> review and improve
```

See docs/lifecycle-compatibility.md for how this loop adapts across Codex, Claude Code, Hermes, and ChatGPT from harvest through activation, evidence, and review. See docs/runtime-adapter-framework-and-trae.md for the proposed AF-7 runtime adapter framework and Trae support model.

## Core Principle

Canonical practices are the source of truth. Agent-specific skills, prompts, commands, and instructions are adapters.

```text
project session experience
  -> candidate lesson
  -> canonical practice entry
  -> reviewed active rule
  -> agent adapters
```

Repeated work can also become user-facing reusable assets:

```text
work history
  -> asset candidate
  -> human approval
  -> active skill / subagent / automation
  -> agent adapters
  -> local usage evidence
  -> shared usage aggregate
  -> review and improvement
```

Adapters can be regenerated, rewritten, or discarded. Canonical practice entries should preserve the durable content, rationale, lifecycle state, and relationships.

Assets are not canonical practices. They are tools governed by canonical practices and tracked in `assets/` plus `indexes/asset_index.yaml`.

Memory, session summaries, and activity logs are evidence sources. They can suggest candidates, but they are not the source of truth for durable practices, assets, workflows, or adapters.

Native agent learning should remain useful. For agents such as Hermes that can remember, create skills, or improve local skills, Agent Foundry should not disable those native capabilities. Native outputs are upstream candidate inputs when they should become durable or cross-agent.

`docs/memory-system-handoff-dump.md` is preserved evidence for a proposed future memory and knowledge subsystem. It records research, corrections, open questions, and possible future architecture, but it does not make `memory/`, `knowledge/`, `research_memos/`, or project-memory directories current Agent Foundry capabilities.

`docs/roadmap.md` coordinates the readiness work needed before deciding whether that memory system should become an Agent Foundry extension, a sibling repository, a monorepo package, a forked experiment, or a user-vault convention.

## Practice Domains

`meta` is reserved for Agent Foundry capability governance: how practices, assets, adapters, imports, harvesting, routing, publishing, and review work inside this system.

`governance` is for cross-project operating constraints that agents should apply in any repository or task. These include protecting source of truth, avoiding unnecessary machinery, treating transient context as evidence, and preserving long-term runtime capability.

Do not put a practice under `meta` only because it is abstract or broadly useful. A practice belongs in `meta` only when it governs the Agent Foundry capability lifecycle itself. If it constrains general project work, durable records, maintainability, or runtime capability across projects, use `governance` or another domain that matches the work surface.

## Repository Layers

```text
Foundry Core:
  workflows/     Strict procedures agents should follow
  schemas/       Canonical entry shape and lifecycle rules
  scripts/       Deterministic tooling
  templates/     Record templates

Foundry Vault:
  practices/     Canonical practice source of truth
  assets/        Registry of reusable skills, subagents, and automations
  indexes/       Searchable registry for dedupe and routing
  usage/         Shared usage aggregates plus gitignored local raw evidence
  docs/          Long-form explanations for humans and future agents
  imports/       Staging area for external skills and ideas

Downstream:
  adapters/      Outputs for specific agent environments
  runtime/       Machine-local deployment manifests and portable templates
```

Core and Vault currently live in one repository for maintainability. They are separate logical units so agents can distinguish the canonical destination from the current project they are harvesting from.

## Core And User Vault Split

The target product direction is a reusable public Core with user-owned Vaults. A user's Vault is private by default unless that user explicitly chooses to publish it. In the current repository, the maintainer's User Vault belongs to the `farmerhunter` account and should not remain bundled into a public Core distribution before Agent Foundry claims external-user readiness.

AF-2 documents and validates the boundary before moving files. This is a staging step, not a final architecture. Physical Core/Vault separation should happen during the AF-3 migration work, after blank-vault initialization and configuration boundaries are designed well enough to avoid breaking existing local runtimes.

Core contains reusable system capability:

- workflow definitions and command procedures;
- schemas and templates for canonical records;
- deterministic scripts for validation, generation, sync, install, and review;
- adapter profiles and adapter quality rules;
- runtime templates;
- product documentation that describes how Agent Foundry works for any user.

User Vault contains a user's governed capability records and review evidence:

- canonical practices;
- reusable assets;
- practice and asset indexes;
- sanitized usage aggregate evidence;
- user-specific long-form docs, hubs, and planning evidence;
- reviewed imports or staged external material that belongs to that user's capability base.

Generated outputs are neither Core nor Vault. They are projections from Core tooling plus Vault records. Runtime copies are installed downstream and are never canonical.

Executable helper scripts expose a boundary that AF-5 must handle explicitly. AF-3 has an implemented home only for Core platform scripts, so any script that needs to run today must live under Core `scripts/`. That is correct for platform lifecycle tooling such as root validation, Vault initialization, adapter publishing, runtime install, migration planning, consistency checks, and rollback helpers. It is not a complete answer for scripts that belong to a specific capability, practice, or asset, such as multi-agent GitHub Project helpers.

Until capability-owned executable packaging exists, capability-specific helpers may live in Core `scripts/` only as capability-helper candidates. They must avoid personal defaults, avoid treating the User Vault as an executable trust boundary, and remain reviewable as future migration candidates. The AF-5 executable helper boundary defines package location, metadata, permission model, provenance, install/update behavior, and how helpers relate to Vault records without conflicting with freeform practice/asset CRUD.

Current repository mapping:

| Path or content | Split classification | Notes |
| --- | --- | --- |
| `workflows/` | Core | Agent-operable procedures. |
| `schemas/` | Core | Canonical shape definitions. |
| `scripts/` | Core | Deterministic tooling; must avoid personal defaults. |
| `templates/` | Core | Starter record shapes, not personal content. |
| `runtime/templates/` | Core | Portable runtime manifest template. |
| `adapters/adapter_profiles.yaml` | Core | Describes target adapter behavior. |
| `adapters/quality/` | Core | Adapter fidelity rules. |
| `README.md`, `docs/usage.md`, `docs/deployment.md`, `docs/system-design.md`, `docs/lifecycle-compatibility.md`, `docs/offline-sync.md`, `docs/standards-and-sources.md` | Core-oriented docs with some current-repo context | External-user wording should be reviewed during AF-3. |
| `docs/roadmap.md` | Mixed planning doc | Current maintainer roadmap; useful evidence, not required for a blank vault. |
| `docs/memory-system-handoff-dump.md` | Proposed Design Evidence | Not Core runtime capability and not current memory architecture. |
| `docs/obsidian.md` | User Vault / local workflow docs | Obsidian-oriented usage is not required Core behavior. |
| `practices/` | User Vault | The maintainer's active governed practice base. |
| `assets/` | User Vault | The maintainer's approved reusable assets. |
| `indexes/` | User Vault | Registry for the current vault's records. |
| `usage/usage-aggregate.yaml` | User Vault shared aggregate | Sanitized, but still specific to this vault. |
| `imports/` | User Vault staging machinery plus tracked instructions | Directory convention may become Core; staged content is Vault/evidence. |
| `adapters/codex/`, `adapters/claude-code/`, `adapters/hermes/`, `adapters/chatgpt/` | Generated distribution outputs | Tracked for install/manual import; regenerate from Core plus target Vault. |
| `runtime/local/`, `sync/local/`, `usage/local/` | Local Private | Gitignored machine-local state. |
| `Agent Foundry.md` | User Vault navigation | Maintainer hub, not required for external users. |
| `.claude/settings.json` | Maintainer/runtime-specific setting | Boundary-sensitive; should not be product setup guidance without review. |

Staged split decision:

1. Keep Core and User Vault in one repository only until the AF-2 design gates are reviewed.
2. Treat the current split as a documented boundary enforced by policy, checks, and initialization design.
3. Plan the physical split as AF-3 migration work, not as distant memory-system work.
4. Design scripts so `core_root` and `vault_root` can point to different repositories or directories.
5. Do not claim external-user readiness while any current user's Vault records remain required inside the public Core repository.

## User Vault Extraction Plan

This is the AF-3 decision baseline for extracting the current account's User Vault from the public Core. It is a plan and verification contract, not approval to move records. `farmerhunter` is the current account identity for this migration instance, not a special maintainer-only architecture role.

Default target:

- Core remains the public `farmerhunter/agent-foundry` repository or its renamed public successor.
- The active User Vault should live under the same machine-local location pattern on every deployment: `~/.agent-foundry/vault/agent-foundry-vault-<account>`.
- For this account, the selected local target is `~/.agent-foundry/vault/agent-foundry-vault-farmerhunter`.
- The Vault should receive a reviewed private remote or equivalent sync substrate during AF-4 current-user multi-deployment migration. Its local locator path should stay stable across deployments.
- The local path should be explicitly configured through `~/.agent-foundry/config.yaml` as `vault_root`; agents must not infer it from a product project checkout.
- Use the singular directory name `vault` for the active account Vault location. Avoid a generic `vaults` path unless a future multi-vault manager defines what it means.

Migration window:

- The AF-3 migration window starts only when execution changes the local substrate: a private User Vault target is initialized or selected for records, current User Vault records are copied or moved, public copies are deleted, or `vault_root`/runtime config is repointed away from the combined repository.
- The migration window is not opened by this plan, by read-only inventory, or by public Core cleanup that does not move Vault records.
- While the window is open, pause normal canonical writes and adapter/runtime publishing unless the operation explicitly uses verified split `core_root` and `vault_root`.
- The normal window close point is #33 Runtime deployment migration, not #34. It closes only after Core and active User Vault validate separately, selected-Vault adapter publishing succeeds, local runtime refresh/dry-run no longer depends on the old combined root, stale path checks pass, and rollback is visible.
- #34 is a post-window readiness audit. Failures found in #34 should reopen or fix the migration result instead of extending an ambiguous half-migrated state.
- AF-4 starts after the local split window closes. It is responsible for private Vault remote setup, all existing deployment migrations, real workflow verification across machines, and the reusable upgrade discipline needed for future data-schema or program-structure major changes. AF-5 new-user onboarding should not become the main priority until AF-4 proves the current user can actually operate and upgrade the split system.

Move to the active User Vault:

- `practices/`
- `assets/`
- `indexes/`
- `usage/usage-aggregate.yaml`
- reviewed import staging if present under `imports/`
- vault-local workspace docs such as `Agent Foundry.md` and Obsidian-oriented notes when they are not required Core product docs

Keep local-only and ignored:

- `usage/local/`
- `runtime/local/`
- `sync/local/`, `sync/imported/`, `sync/pending/`, `sync/applied/`, `sync/conflicts/`, `sync/snapshots/`
- secrets, tokens, raw exports, transcripts, machine paths, adoption state, and unmanaged runtime copies

Keep in public Core:

- reusable workflows, schemas, scripts, templates, runtime templates, adapter profiles, adapter quality rules, blank Vault initializer, selected-Vault validation, selected-Vault adapter publishing, and product docs
- non-personal fixtures or examples only when clearly labeled and not required as a default user Vault

Backup and restore gates before movement:

1. Run `python3 scripts/plan_vault_extraction.py` and resolve missing required paths.
2. Create a local archive or clone of the current combined checkout before moving records.
3. Verify the backup can be listed or restored before changing tracked files.
4. Initialize or select the active User Vault target, normally `~/.agent-foundry/vault/agent-foundry-vault-<account>`.
5. Copy records into the private target and run `python3 scripts/check_foundry_roots.py --core-root <core> --vault-root <user-vault>`.
6. Run `python3 scripts/publish_adapters.py --core-root <core> --vault-root <user-vault> --output-root <temp-output> --apply`.
7. Update `~/.agent-foundry/config.yaml` only after Core and Vault validate separately.
8. Resume harvest/publish/refresh only after #33 verifies split Core, active User Vault, generated adapters, runtime install or dry-run, stale-path checks, and rollback visibility.

Stop conditions:

- Any required Vault path is missing from the backup or private target.
- Any public Core file still requires a current user's active practices/assets as default content.
- Any generated adapter output includes raw evidence, local private paths, or current User Vault records when run against a blank or custom Vault.
- Runtime install would overwrite unmanaged files or point at the old combined root without an explicit migration step.
- A private remote must be created, files must be deleted, history must be rewritten, or records must be moved out of the current repo. These require explicit user approval at execution time.

## Current-User Deployment And Upgrade Migration

AF-4 is not new-user onboarding. It is the operational migration and upgrade-readiness stage for the current only real user, whose Agent Foundry setup already exists on multiple machines and runtime surfaces.

AF-4 should establish the current user's private Vault sync substrate before broad onboarding work:

1. Initialize the selected User Vault as its own git repository only after a Vault-specific `.gitignore` and tracked/untracked policy are reviewed.
2. Push canonical Vault records to a private remote, normally named for the account and Vault, such as `agent-foundry-vault-farmerhunter`.
3. Verify the remote is private and does not contain raw evidence, secrets, machine-local manifests, local sync state, unmanaged runtime files, or product project material.
4. On every existing deployment, clone or pull public Core and private Vault separately.
5. Keep the local Vault path stable: `~/.agent-foundry/vault/agent-foundry-vault-farmerhunter`.
6. Write or verify `~/.agent-foundry/config.yaml` on each machine so agents can locate both `core_root` and `vault_root` from product project work, Vault work, or Core maintenance work.
7. Run validation, selected-Vault adapter publishing, runtime refresh, stale-reference checks, and at least one real harvest/review/publish workflow across deployments.
8. Generalize the migration checks into an upgrade playbook that future schema/layout/program changes can reuse.

AF-4 should also treat the Core/Vault split as the first real production migration rehearsal. Later changes may introduce new Vault schema versions, Core layout changes, adapter packaging changes, capability-pack metadata, or memory-system record types. Those upgrades should not rely on ad hoc human memory. They should have the same structure: version markers, inventory, compatibility check, backup, dry-run, gated apply, validation, runtime refresh, real workflow smoke test, cross-machine propagation, and close verification.

AF-4 exit means the current user can actually operate and upgrade the split system across deployed machines. It does not require polished blank-Vault onboarding, bootstrap capability packs, optional pack UX, or memory-system records. Those belong to later stages.

Future major-upgrade invariants:

- Core, Vault, generated adapters, runtime installs, and local-private state must be distinguishable before upgrade.
- Version/layout markers must be explicit enough for tooling to decide whether an operation is safe, blocked, or only diagnostic.
- Upgrade scripts should fail closed when Core and Vault versions are incompatible or unknown.
- Backups and rollback boundaries must be visible before destructive or irreversible steps.
- A partially migrated deployment must be detectable.
- Real workflow verification is required before a major upgrade is considered complete.

## Private User Vault Remote Policy

AF-4 should make the current User Vault syncable before broad onboarding work starts. The default remote target for the current account is:

```text
owner: farmerhunter
repository: agent-foundry-vault-farmerhunter
visibility: private
local path: ~/.agent-foundry/vault/agent-foundry-vault-farmerhunter
```

Remote creation and first push are privacy-boundary operations. They require explicit user approval at execution time. Planning, inventory, and dry-run checks may happen before approval; remote creation, `git init` inside the Vault, commits, pushes, and remote visibility changes may not.

The first Vault repository should use a clean privacy-boundary history by default. Preserving the old public Core file history is lower priority than proving the private Vault contains only approved Vault records and no raw/local evidence. Historical context remains available in the public Core repository history and AF-3 migration comments; the private Vault should not need to carry that full history to be operational.

Tracked in the private Vault:

- `.agent-foundry-vault.yaml`
- `Agent Foundry.md` and other vault-local user docs approved for sync
- `practices/`
- `assets/`
- `indexes/`
- `imports/` instructions and reviewed import records that are safe to sync
- `usage/usage-aggregate.yaml`
- sanitized shared usage/adoption records only when explicitly approved for sync
- Vault-specific documentation needed to operate the current user's capability base

Ignored or excluded from the private Vault remote:

- raw usage evidence under `usage/local/`
- secrets, tokens, credentials, cookies, API keys, and environment files
- machine-local runtime manifests or install state
- sync transport state, snapshots, conflicts, pending/applied queues, and imported archives
- unmanaged runtime copies from Codex, Claude Code, Hermes, or ChatGPT
- product project source trees, build outputs, logs, caches, and temporary files
- raw chat exports, transcripts, screenshots, or sensitive evidence unless a later reviewed policy defines a sanitized form

Proposed Vault `.gitignore` baseline:

```gitignore
usage/local/
runtime/
sync/
.env
.env.*
*.secret
*.key
*.pem
*.p12
*.log
.DS_Store
__pycache__/
*.pyc
```

The ignore file is a starting point, not approval to push. Before first push, run an explicit file inventory and review every tracked path. If any tracked file contains a machine path, secret, raw evidence, unmanaged runtime copy, or product project material, stop and revise the policy.

Cross-machine expectations:

- Every deployment should use the same local Vault path pattern unless explicitly overridden.
- `~/.agent-foundry/config.yaml` is machine-local and points to the local Core and Vault paths; it is not committed to the Vault.
- The private Vault remote is the canonical sync substrate for the current user's Vault records.
- The public Core remote remains the source for reusable tooling and docs.
- A deployment is not considered migrated until it can validate Core plus Vault, publish adapters from the selected Vault, refresh managed runtimes or record an intentional manual/deferred runtime, and run at least one real workflow after pulling the Vault.

## Major Upgrade Migration Discipline

AF-4 should turn the split migration into the standard pattern for future major upgrades. A major upgrade is any change that may make existing deployments or Vault records incompatible without a planned transition. Examples include:

- Vault schema version changes;
- Core marker or directory layout changes;
- generated adapter packaging changes;
- runtime install ownership model changes;
- capability-pack metadata introduction;
- memory-system record type introduction;
- migration from local-only state to remote-backed state;
- any change that can make one deployment write records another deployment cannot read safely.

Required upgrade states:

| State | Meaning |
| --- | --- |
| `compatible` | Current Core, Vault, generated outputs, and runtime state can operate safely. |
| `dry_run_only` | The upgrade can be planned but must not apply yet. |
| `blocked` | A required dependency, approval, backup, or compatibility condition is missing. |
| `unknown` | Tooling cannot determine the current version/layout safely. |
| `partial` | Some deployments or layers have migrated and others have not. |
| `rollback_required` | Validation failed after apply and the documented rollback path should be used. |
| `complete` | All in-scope deployments pass validation and real workflow smoke tests. |

Standard upgrade issue chain:

1. Decision issue: define the target version/layout, compatibility rule, stop conditions, and owner role.
2. Inventory issue: record current Core, Vault, generated, runtime, local-private, and deployment states.
3. Implementation issue: make tooling support both old and new states where practical.
4. Dry-run issue: prove migration planning without writes.
5. Apply issue: perform gated writes only after explicit approval.
6. Review issue: verify backups, rollback visibility, version markers, stale references, and real workflows.
7. Close issue: record cross-machine completion and residual risks.

Standard upgrade checklist:

- identify authoritative Core and Vault layout/schema markers;
- classify generated outputs and runtime copies as downstream, not canonical;
- inventory every in-scope deployment before applying;
- create or verify backups before destructive or irreversible changes;
- run dry-run planning before apply;
- fail closed on unknown or incompatible marker pairs;
- apply only after explicit approval when privacy, data movement, deletion, or runtime writes are involved;
- validate Core plus Vault separately after apply;
- regenerate or refresh adapters from the selected Vault;
- run at least one real workflow smoke test;
- verify another deployment can pull/sync the result;
- record residual risks and intentionally deferred deployments;
- keep AF-5 onboarding, AF-7 runtime adapter framework work, AF-8 capability-system hardening, and later memory-system planning out of the upgrade unless explicitly scoped.

Future split options:

| Option | Use when | Tradeoff |
| --- | --- | --- |
| Single repo with logical split | AF-2 design staging only | Simple and low migration cost, but personal Vault remains physically adjacent to Core and cannot be the external-user-ready endpoint. |
| Monorepo with `core/` and `vault/` packages | Core and Vault need separate installs but shared development | More structure and migration work; still one remote. |
| Core repo plus user vault repo | External-user distribution needs clean separation | Best product boundary, but requires install/init tooling and version compatibility. |
| Template repository / starter vault | Blank-vault setup becomes the main adoption path | Easier onboarding, but template drift must be managed. |

Migration risks:

- scripts may assume repo-relative paths that currently point to both Core and Vault;
- consistency checks may assume one combined index/practice/asset tree;
- adapters may encode the maintainer's current Vault content as if it were default product content;
- docs may mix product instructions with maintainer planning evidence;
- tracked workspace affordances such as `Agent Foundry.md` and `.claude/settings.json` may confuse external users;
- usage aggregates are sanitized but still belong to the current user's Vault;
- future memory-system evidence could accidentally be promoted into Core if capability state is not marked.

AF-2 follow-up implications:

- #7 should define a blank vault that starts with empty indexes, templates, and no personal practices/assets.
- #8 should define portable Core config separately from machine-local runtime and adoption state.
- #9 should describe external-user setup without requiring the maintainer's Vault records.
- AF-3 should execute the physical split and migration: public Core, maintainer private Vault, updated locators, runtime migration, and compatibility checks.

## Blank Vault Initialization

Blank Vault initialization is the AF-2 design for creating a new User Vault without inheriting the maintainer's personal records. AF-3 now provides a local initializer and validation path through `scripts/init_vault.py`, `scripts/check_foundry_roots.py`, and `scripts/test_foundry_roots.py`. Current single-repo operation remains supported for compatibility while AF-3 continues updating publish, install, and migration flows for separate `core_root` and `vault_root` paths.

Design goal:

```text
public Core + empty User Vault -> valid starting point for reviewed practices, assets, usage evidence, and adapter generation
```

`init-vault` should mean "create a valid, empty canonical destination" rather than "copy the current account's active Vault." It should initialize structure and metadata only. It should not activate practices, install runtime adapters, import external skills, deploy capability packs, or write memory-system records.

Blank Vault contents:

| Vault path or record | Blank state | Source of shape |
| --- | --- | --- |
| `practices/` | Empty practice tree, with no active/candidate/proposed practice records copied from a current-user Vault. | Core schemas and templates. |
| `assets/` | Empty asset tree, with no active/candidate/proposed asset records copied from a current-user Vault. | Core schemas and templates. |
| `indexes/practice_index.yaml` | `schema_version`, `updated`, Core-provided domain vocabulary, and `practices: []`. | Core index template or generated initializer. |
| `indexes/asset_index.yaml` | `schema_version`, `updated`, Core-provided asset type vocabulary, and `assets: []`. | Core index template or generated initializer. |
| `usage/usage-aggregate.yaml` | `schema_version`, `updated`, and `aggregates: []`. | Core usage aggregate template or generated initializer. |
| `imports/` | Empty reviewed-import staging area, with no raw external imports. | Core workflow convention. |
| Vault metadata | Minimal non-sensitive vault identity, privacy default, Core compatibility range, and initialized date. | Proposed AF-3 implementation detail; no current schema exists yet. |
| Runtime manifest | Not part of the canonical Vault by default. Runtime deployment remains machine-local unless a later reviewed policy defines portable runtime intent. | Runtime template and local manifest policy. |

Template rule: practice and asset templates belong to Core. A blank Vault may receive copied template files only if the implementation needs standalone editing affordances, and those copies must be clearly marked as templates, not canonical records. Template copies must not appear in indexes as active records.

Capability pack rule: capability packs are deployed after blank Vault creation, not during blank Vault initialization. A deployed pack writes canonical practice and asset records, index entries, and any pack metadata into the user's Vault. After deployment, those records are normal Vault records governed by the same create, read, update, deprecate, retire, review, and adapter-publish workflows as manually created records. Pack deployment is an import/bootstrap path, not a second source of truth.

Normal onboarding should deploy a mandatory bootstrap pack after the blank Vault exists. Optional packs, such as multi-agent collaboration or future technical documentation writing, use the same deployment mechanism but remain user-selected. Runtime adapters are generated only after pack deployment through `refresh`, from Vault canonical data.

Predefined packs and discovered packs do not conflict with freeform Vault CRUD because they operate at different moments:

- A predefined pack is curated Core-distributed canonical data that can be deployed into a Vault.
- A discovered pack is a reviewed bundle proposal inferred from existing practices, assets, workflows, and usage evidence.
- Once deployed, both become ordinary Vault records with provenance and pack membership metadata.
- Later pack updates must propose normal record changes; they must not overwrite user-edited Vault records silently.
- Users and agents may still create, edit, archive, or retire individual practices and assets outside any pack.
- A record may belong to no pack, one pack, or multiple packs; pack membership is metadata, not ownership.
- `refresh` ignores pack source and reads only the current active/revised Vault records.

Validation expectations for a blank Vault:

1. It validates as a Vault destination before canonical writes.
2. It contains no current-user-specific practices, assets, usage aggregate rows, local paths, runtime adoption decisions, raw evidence, or future memory-system directories.
3. Empty indexes and empty aggregates are accepted as valid starting state.
4. Practice and asset creation workflows can add the first candidate without requiring preexisting personal records.
5. Adapter publishing can report "nothing to publish" or produce an empty/minimal adapter output without treating that as a failure.
6. Runtime install must not copy the current account's generated adapters into a new user's runtime.
7. Consistency checks distinguish "empty but valid Vault" from "missing or corrupt Vault."
8. Pack deployment can add canonical data after initialization without changing the definition of blank Vault.

Implemented AF-3 baseline:

- `scripts/init_vault.py` creates empty `practices/`, `assets/`, `imports/inbox`, `usage/local`, empty practice and asset indexes, and an empty shared usage aggregate;
- blank Vault initialization does not copy current-user practices/assets;
- blank Vault initialization does not trigger runtime install;
- `scripts/publish_adapters.py` validates selected Core/Vault roots before publishing;
- blank Vault adapter publishing reports `nothing to publish`;
- current-user-like Vault adapter publishing can produce deterministic adapter outputs in a selected output root.

Implementation implications still remaining for AF-3:

- scripts that currently assume repository-relative `practices/`, `assets/`, `indexes/`, and `usage/` must accept a separate `vault_root`;
- checks should validate Core schemas/workflows against an arbitrary Vault;
- generated adapter outputs should be derived from the selected Vault, not from a bundled current-user Vault by default;
- blank-vault fixtures or templates should be reproducible from Core and should not require copying personal records;
- later pack deployment should be able to populate a blank Vault with the mandatory bootstrap pack before `refresh`;
- migration must test both the active User Vault and a blank/new-user Vault.

Rejected as #7 scope:

- creating `memory/`, `knowledge/`, `research_memos/`, or `project_memory`;
- importing runtime skills or ChatGPT exports;
- implementing capability pack deployment before the blank Vault and selected-root substrate are reviewed;
- moving the maintainer's Vault into a private repo;
- implementing `init-vault` scripts before the design is reviewed.

## External-User Setup Boundary

External-user setup is not a current complete quickstart. AF-2 defines the boundary and prerequisites; AF-3 must physically split public Core from the active private User Vault, AF-4 must prove the current user's existing deployments can operate the split system, and AF-5 must define onboarding modes before Agent Foundry can claim a tested external-user start path.

Current capability:

- single-repo operation where Core and the active User Vault share one repository root;
- machine-local runtime manifest setup for the current user;
- adapter install into enabled local Codex, Claude Code, and Hermes runtimes;
- manual ChatGPT import from generated adapter files;
- logical Core/Vault separation documented in this file;
- blank Vault initialization design, but no implemented `init-vault` command;
- locator config that currently writes `core_root`, `vault_root`, and `repo_root` to the same path.

Target setup narrative after AF-3 through AF-5:

1. The user obtains the public Core.
2. The user creates or selects a User Vault location.
3. The user initializes an empty Vault.
4. Core deploys the mandatory bootstrap pack into that Vault as canonical data.
5. The user optionally deploys selected capability packs into the Vault.
6. The local locator records separate `core_root` and `vault_root`.
7. Core tooling validates both roots before any canonical write.
8. The user runs `refresh`, which generates adapters from Vault canonical data and installs only to selected local runtimes.
9. ChatGPT remains manual unless a future supported import path exists.

Pre-split boundary for #9:

| Setup concern | Current AF-2 answer | Blocked by |
| --- | --- | --- |
| What to clone | Current repo contains both Core and the current account's User Vault; this is a combined staging setup, not public Core distribution. | AF-3 public Core split. |
| Where Vault lives | Designed as user-owned and private by default; current repo still contains the active User Vault. | AF-3 User Vault extraction. |
| How blank Vault starts | Defined as empty indexes, empty aggregate, no personal practices/assets. | AF-3 `init-vault` implementation and validation. |
| How Core/Vault are located | `~/.agent-foundry/config.yaml` exists, but current scripts assume one root. | AF-3 separate root support. |
| How adapters are generated | Current adapters are generated from the active User Vault. | AF-3 arbitrary-vault adapter generation. |
| How runtimes are installed | Current machine-local manifest installs into selected local runtimes. | AF-3 migration checks for split Core/Vault; AF-4 proves current deployments; AF-5 first-run UX. |
| How bootstrap capability appears | Blank Vault is created first, then mandatory bootstrap pack is deployed as canonical Vault data. | AF-5 pack deployment and first-run verification. |
| How optional capability content appears | Optional capability packs and runtime imports are not blank defaults; they are deployed or imported after the Vault exists. | AF-5 pack selection and import workflow. |
| How existing runtime assets are imported | Existing runtime assets are evidence/candidates first. | AF-5 import workflow. |
| What remains private | Raw evidence, local manifests, adoption state, secrets, User Vault, personal records. | Current policy plus AF-3 migration. |

Docs implications:

- `docs/deployment.md` currently documents maintainer/single-repo deployment and local runtime install.
- `docs/usage.md` currently documents day-to-day use after Agent Foundry is already installed.
- Neither file should be read as a tested external-user quickstart until AF-3, AF-4, and AF-5 are complete.
- AF-3 should rewrite deployment docs around public Core plus selected Vault.
- AF-5 should add first-run onboarding sequence: blank Vault creation, mandatory bootstrap pack deployment, optional capability pack selection, runtime-asset import when selected, and unified refresh.

Do not promise future memory-system behavior in external-user setup. Memory-system records, `knowledge/`, `research_memos/`, project memory, and MCP memory access remain proposed/future until reviewed architecture implements them.

## AF-5 Onboarding And Capability Pack Model

AF-5 should be driven by onboarding journeys, not by isolated implementation objects. The product question is whether a user can move from blank or unfamiliar state to a verified usable Agent Foundry workflow.

Primary AF-5 journeys:

1. **Fresh install**: public Core, blank Vault, mandatory bootstrap pack, runtime selection, refresh, receipts, and first normal command.
2. **Add optional capability pack**: stage, review, deploy, refresh, and verify an optional pack such as multi-agent collaboration.
3. **Import existing runtime assets**: treat existing Codex, Claude Code, Hermes, or ChatGPT material as evidence/candidates before canonical activation.
4. **Import product-project capability**: treat project-local helpers, docs, prompts, or templates as evidence before packaging the reusable subset.
5. **Cross-machine restore**: rebuild runtime state from public Core plus selected Vault instead of copying runtime files from another machine.
6. **Disable or rollback pack-sourced capability**: update Vault lifecycle state and regenerate runtime outputs without deleting unrelated user-created records.

Each journey must have an activation contract before implementation begins. The contract should name the starting state, user intent, required user decisions, success report, failure states, rollback or recovery path, first usable command, and downstream AF-5 issue that owns implementation.

### AF-5 Activation Journey Contracts

#### Fresh install

- Starting state: the user has public Core or can obtain it, but has no selected User Vault on this machine.
- User intent: get from blank local state to a usable Agent Foundry that can run a first normal workflow.
- Required decisions: Vault location, local-only versus remote-backed Vault, enabled runtimes, ChatGPT manual import acceptance, and whether optional packs are deferred.
- Success report: Core root, Vault root, bootstrap pack deployed, enabled/disabled/manual runtimes, generated outputs, install receipts, and first normal command are visible.
- Failure states: Core missing, Vault invalid, bootstrap pack unavailable, runtime target unsafe or unmanaged, ChatGPT manual import unclear, or setup cannot explain which layer owns a file.
- Recovery path: stop before runtime write, preserve blank Vault if valid, show exact failed step, and allow rerun after config, pack, or runtime correction.
- First usable command: `refresh practices and assets` or a bootstrap-provided harvest/review command after bootstrap deployment.
- Implementation owner: #76, #77, and #78 derive the blank Vault, bootstrap deployment, and first-run status work.

#### Add optional capability pack

- Starting state: Core and selected User Vault validate, bootstrap is already deployed, and the user chooses an optional pack.
- User intent: add a bounded capability without importing private history or creating a second source of truth.
- Required decisions: pack source, version, included records, executable payload permissions, dependency acceptance, conflict handling, and runtime targets affected by refresh.
- Success report: staged pack reviewed, records added/updated/skipped, conflicts or local edits reported, pack membership metadata recorded, and refresh/install impact listed.
- Failure states: pack provenance unknown, license/security unclear, ID collision unrelated, local modified record would be overwritten, executable payload lacks install boundary, or pack tries to act as live runtime authority.
- Recovery path: keep the pack in staging, write no canonical records on failed review, and show a merge proposal or rejection reason.
- First usable command: the pack's published trigger or generated runtime skill after deployment and refresh.
- Implementation owner: #74 defines authority and conflicts; #75 defines manifest fixtures; #79 validates the first optional multi-agent candidate.

#### Import existing runtime assets

- Starting state: the user already has Codex, Claude Code, Hermes, ChatGPT, or local runtime materials outside the selected Vault.
- User intent: preserve useful existing work by converting it into reviewed Agent Foundry candidates.
- Required decisions: explicit source paths, sensitivity boundary, provenance, license/security risk, candidate routing, and whether any item should be discarded.
- Success report: imported material is classified as evidence, practice candidate, asset candidate, pack candidate, project-local decision, design note, discard, or future work; no item becomes active without review.
- Failure states: source path is too broad, raw private data appears, executable script would run during import, runtime file ownership is unclear, or imported content duplicates active Vault records.
- Recovery path: leave material in staging or report-only mode, redact or narrow source scope, and rerun artifact routing before canonical mutation.
- First usable command: a review/harvest command that presents candidates for approval, not a runtime install command.
- Implementation owner: #80 owns runtime asset import path and must reuse harvest/import discipline.

#### Import product-project capability

- Starting state: a product project contains reusable helper scripts, docs, prompts, templates, or workflow conventions that may become a capability pack.
- User intent: promote reusable capability without confusing the product project with Core, Vault, or runtime truth.
- Required decisions: source project scope, reusable subset, project-local overlay, examples versus defaults, private path handling, executable payload boundary, and whether the capability is optional.
- Success report: product evidence is inventoried, reusable contents are proposed as a candidate snapshot, project-local defaults are separated from reusable examples, and no files are copied into Core or Vault without review.
- Failure states: project-specific issue labels or branches become global defaults, private paths leak, helper scripts require Core `scripts/` because no asset payload model exists, or the source project becomes an implicit live dependency.
- Recovery path: keep the source project as evidence, defer executable payloads until #53 is resolved, and produce rejected-as-pack reasoning for project-local material.
- First usable command: none until the pack is deployed and refreshed; before that, only review and packaging commands are valid.
- Implementation owner: #79 validates Tiny IPA's role-generic GitHub helpers as the first optional product-project capability candidate.

#### Cross-machine restore

- Starting state: the user has another machine or deployment with public Core and either a private Vault remote or a chosen blank Vault path.
- User intent: recreate a working local Agent Foundry without copying runtime files or machine-local state from another deployment.
- Required decisions: Core path, Vault clone/pull path, locator write, runtime enablement, whether to apply runtime install, and ChatGPT manual import status.
- Success report: Core/Vault roots validate, selected Vault commit is visible, runtime manifests and receipts are local to this machine, refresh/install status is clear, and stale combined-root references are absent or reported.
- Failure states: Vault remote unavailable, Core/Vault version incompatible, local config points to old combined root, runtime receipt missing or stale, or machine-local path would be committed.
- Recovery path: stop before runtime apply, preserve local config backup, report exact stale references, and allow rerun after clone, pull, or locator correction.
- First usable command: `sync_status` or `refresh practices and assets` after root validation and runtime dry-run.
- Implementation owner: #81 owns restore and rollback review after #78 proves local first-run status.

#### Disable or rollback pack-sourced capability

- Starting state: the selected Vault contains records with pack membership metadata and runtimes may contain generated outputs from those records.
- User intent: disable, retire, or roll back a capability without damaging unrelated user-created records.
- Required decisions: disable versus retire versus archive, runtime cleanup scope, whether canonical history changes, and whether rollback affects only runtime state or also Vault lifecycle state.
- Success report: affected records, unrelated records, generated outputs, runtime files, receipts, manual targets, and residual cleanup are listed separately.
- Failure states: rollback deletes user-created records, runtime files remain referenced after disable, pack membership is treated as ownership, or ChatGPT manual imports cannot be represented.
- Recovery path: prefer lifecycle state changes and regeneration over deletion, back up runtime files before managed cleanup, and preserve audit trail of prior pack membership.
- First usable command: status/refresh after disable, plus explicit cleanup instructions for manual targets.
- Implementation owner: #81 and #82 validate rollback behavior before AF-5 closes.

### AF-5 Pack Lifecycle And Authority Decision

This decision applies `GOV-007`: before a pack affects canonical records or runtime behavior, classify the layer that has authority. AF-5 adopts a local-first snapshot-import model, not a live pack dependency model.

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

AF-5 implements only the basic path through this lifecycle: reviewed snapshot deployment into a selected Vault, activation as ordinary Vault records, refresh into runtimes, status verification, and rollback or disable behavior. Marketplace channels, automatic pack discovery, broad update management, and advanced export polish remain later work.

Authority layers:

| Layer | Examples | Authority in AF-5 |
| --- | --- | --- |
| Source evidence | Tiny IPA helpers, existing runtime files, session notes, external repos | Evidence only. It can justify a pack candidate but is not queried by `refresh` or runtime install. |
| Package snapshot | Bootstrap pack, optional multi-agent pack, exported pack archive | Transfer and review artifact. It is immutable or versioned for comparison, but not the live source after deployment. |
| Import staging | Unreviewed or reviewed pack staging area | Temporary review surface for provenance, license, security, conflicts, and user decisions. Failed staging writes no canonical records. |
| Canonical Vault records | Practices, assets, indexes, accepted payloads, pack membership metadata | Source of truth after deployment. Freeform Vault CRUD can create, edit, retire, or archive these records outside pack workflows. |
| Generated output | Adapter files, runtime skill output, generated helper wrappers | Downstream output from the selected Vault plus Core generator/profile logic. It is reproducible and not canonical. |
| Runtime copy or dependency | Installed runtime files, managed helper copies, dependency checks, receipts | Machine-local operational state. It must be installed with receipts and rollback semantics where managed. |
| Live upstream authority | Marketplace, registry, source repo consulted at runtime | Not part of AF-5 MVP. It requires a separate trust, versioning, offline, conflict, and rollback design. |

Capability packs are exported or deployable snapshots, not independent runtime truth sources. A pack may contain practice records, asset records, docs, templates, examples, configuration defaults, and executable payloads. Deployment writes or updates normal User Vault records with provenance, pack membership metadata, and conflict history. After deployment, the selected User Vault owns the canonical records; `refresh` reads current Vault state, not live pack definitions.

Pack deployment is not ownership transfer to a pack controller. A deployed record may belong to no pack, one pack, or multiple packs. Pack membership explains provenance and update comparison; it does not prevent ordinary reviewed edits, deprecation, retirement, or archive decisions. If a user edits a pack-sourced record, later pack updates must treat that local edit as canonical user state and produce a reviewable merge proposal rather than overwriting it.

Pack updates are reviewed releases, not automatic mirrors of all canonical record changes. Each pack should carry enough contract metadata to answer what user journey or capability it promises. A changed canonical record triggers a pack update only after a Pack Relevance Review decides the change belongs inside that pack's promised boundary.

Pack Relevance Review asks:

- Did pack membership change?
- Did the pack's promised use case, first-run behavior, activation/default behavior, compatibility range, or schema expectations change?
- Does the canonical change fix a bug, privacy issue, security issue, or misleading instruction that is material to this pack's promised use case?
- Would users receiving the older pack snapshot be materially unsafe, blocked, or misled for this pack's journey?

If yes, propose a new pack version, included-record diff, manifest update, and checksum refresh. If no, record that no pack update is needed. Do not regenerate a pack merely because an included canonical record changed outside the pack's selected contract.

Minimal manifest responsibilities for #75:

- stable pack id, title, description, lifecycle status, version, exported date, source provenance, and maintainer/source contact when available;
- compatibility range for Core schema and Vault schema or metadata versions;
- included practices, assets, docs, templates, examples, configuration defaults, executable payloads, and generated-output expectations;
- per-item id, path, kind, lifecycle status, source version, content hash, and intended destination layer;
- provenance, license, sensitivity, security, permission, dependency, and runtime-impact metadata;
- conflict policy, rollback notes, and whether the pack is mandatory bootstrap, optional user-selected capability, or product-project candidate;
- checksums for snapshot integrity and enough metadata to compare a later pack version with the user's current Vault records;
- selection scope, pack contract, or included-rationale metadata that supports later Pack Relevance Review.

Conflict and update behavior:

| Situation | Required behavior |
| --- | --- |
| Same id, same pack version, same content hash | Verify or skip as already deployed. |
| Same id, same pack version, different content hash | Fail closed; require review because the snapshot is not reproducible. |
| Same id, newer pack version, local record unchanged since prior import | Show a diff and allow reviewed update. Do not silently apply unless the workflow has an explicit low-risk auto-update policy, which AF-5 does not define. |
| Same id, newer pack version, local record modified after import | Produce a merge proposal or keep local state. Do not overwrite user edits. |
| Same id, unrelated provenance or incompatible kind | Fail closed as an unrelated id collision. |
| Missing dependency, incompatible Core/Vault schema, or executable payload without a reviewed install boundary | Fail before canonical write or runtime install. |
| Pack marks a record deprecated or retired | Propose lifecycle change; do not delete canonical records by default. |
| User retires or archives a pack-sourced record | Respect the Vault lifecycle state. Later pack refresh may propose reactivation only with explicit review. |

Activation semantics:

- Deploying a pack into the selected Vault is separate from making every included record active. Records still carry their normal lifecycle status, and human review remains required unless the pack has already been reviewed as the mandatory bootstrap distribution.
- `refresh` uses active or otherwise selected Vault records according to existing adapter publishing rules. It must not activate staged pack content by reading directly from a pack snapshot.
- Runtime install uses generated output or accepted Vault payloads plus Core platform machinery. It must not execute from pack staging or canonical Vault payloads directly unless #53 defines and validates that boundary.
- ChatGPT-style manual imports remain manual targets; a pack may provide instructions or generated text, but not a hidden managed install.

Rollback and disable semantics:

- Prefer lifecycle state changes, pack membership metadata updates, and regeneration over deletion.
- Runtime rollback is separate from Vault history. Managed runtime files can be restored or removed according to receipts without rewriting canonical Vault records.
- Disabling a pack should identify affected pack-sourced records, user-created records, generated outputs, runtime copies, manual targets, and residual cleanup separately.
- Removing pack membership metadata must not erase provenance needed for later audit unless a reviewed privacy policy requires redaction.

### AF-5 Capability-Owned Executable Helper Boundary

Capability-owned helper scripts are executable payloads that support a specific reusable capability, asset, or practice set. They are different from Core platform scripts. Core scripts make Agent Foundry itself work; capability helpers make a selected user capability more ergonomic after that capability has been reviewed and installed.

Layer decision:

| Layer | Helper responsibility |
| --- | --- |
| Core `scripts/` | Platform lifecycle tooling: locate and validate roots, initialize Vaults, publish adapters, install runtimes, check consistency, migrate deployments, create backups, roll back managed runtime files, export/import offline snapshots, and record usage evidence. |
| Capability pack snapshot | Transfer helper source, examples, docs, and metadata for review. It is not executable authority and must not run during staging. |
| Selected User Vault | Canonical accepted asset record, provenance, lifecycle state, reviewed metadata, and optionally reviewed payload source. The Vault is not a direct execution boundary. |
| Generated output | Optional wrappers, command manifests, or runtime instructions derived from the accepted Vault record plus Core install logic. |
| Managed runtime/tool location | Machine-local executable copy, dependency state, permissions, receipts, and rollback metadata. This is where executable use happens. |
| Product project | Evidence source or project-local overlay. It must not become a hidden dependency after the helper is packaged. |

Trust and install model:

1. Treat every helper as inert while it is in pack staging or import review.
2. Accept the helper only through an asset or capability-pack review that records provenance, license, sensitivity, permissions, dependencies, and intended runtime impact.
3. Store the canonical decision in the selected Vault as ordinary asset data. If payload source is stored in the Vault, treat it as reviewed source, not as the path to execute.
4. Install executable copies into managed machine-local runtime/tool locations through Core platform install logic.
5. Write receipts that include helper id, asset id, pack id when applicable, source hash, installed path, dependency check result, permissions, install time, Core version, Vault version or commit, and rollback path.
6. Run helpers only from managed installed locations or from an explicitly approved development path. Do not run helpers from pack staging, imported archives, product projects, or canonical Vault payload paths by default.
7. Support dry-run/status modes before apply. A helper that cannot explain install impact, dependencies, or rollback is not ready for managed install.

Minimal helper metadata for later schema work:

- helper id, title, capability id, related asset id, related pack id, lifecycle status, version, owner or maintainer;
- source provenance, source path or archive reference, source hash, license, sensitivity classification, and review date;
- supported platforms, interpreter/runtime, dependency list, network/filesystem/process permissions, and whether the helper is read-only or mutating;
- safe dry-run command, status command, install command shape, uninstall or rollback behavior, and expected managed install target;
- runtime targets affected, adapter exposure, user-visible trigger text, and failure modes;
- update policy, compatibility range, supersedes/superseded-by metadata, and whether local user edits are allowed.

Current Core script classification:

| Current script group | Classification | Notes |
| --- | --- | --- |
| Root/config/install/migration helpers | Core platform-essential | `foundry_config.py`, `check_foundry_roots.py`, `init_vault.py`, `install_foundry.py`, `migrate_deployment.py`, `plan_vault_extraction.py`, `check_deployment_migration.py`, and `collect_deployment_inventory.py` operate on Core/Vault setup and upgrade boundaries. |
| Adapter publish/install/status helpers | Core platform-essential | `publish_adapters.py`, `sync_adapters.py`, `sync_status.py`, `runtime_manifest.py`, `adapter_install_receipt.py`, `deployment_checks.py`, and `rollback_runtime.py` operate generated/runtime state from Core plus selected Vault. |
| Review, usage, and consistency helpers | Core platform-essential | `check_consistency.py`, `check_adapter_quality.py`, `check_activation.py`, `review_practices.py`, `review_assets.py`, `record_asset_usage.py`, and `aggregate_usage.py` enforce Agent Foundry governance and evidence handling. |
| Offline sync helpers | Core platform-essential | `export_snapshot.py`, `import_snapshot.py`, `compare_snapshot.py`, and `sync_state.py` support local-first transfer and recovery. |
| Test scripts | Core platform-essential test surface | `test_*.py` files validate Core behavior and should remain in Core. |
| Capability-specific helpers | Capability-helper candidates | No current Core script should be treated as a finished capability helper by default. Future scripts that mainly serve optional multi-agent collaboration, technical writing, or another user capability should be labeled as candidates and migrated once the helper packaging path is implemented. |

Migration path:

1. Keep existing Core scripts in place unless a reviewed classification shows that a script primarily serves an optional capability rather than Agent Foundry platform operation.
2. For any new capability-specific script needed before packaging exists, mark it as a temporary capability-helper candidate in the issue/PR and avoid personal defaults or hidden Vault assumptions.
3. When #75 and later implementation provide pack manifests and helper install metadata, move candidate helpers into capability-pack or asset payload source with provenance and checksums.
4. Install reviewed helpers into managed runtime/tool locations with receipts instead of executing from Core, pack staging, product projects, or Vault payload paths.
5. Leave Core `scripts/` for platform machinery and tests; do not grow it into a repository of optional user capabilities.

The Tiny IPA role-generic GitHub helpers are a validation case for this model. Tiny IPA remains the evidence source. The reusable multi-agent helper subset can become a candidate optional capability pack only after AF-5 defines pack snapshot, provenance, project-local overlay, executable payload, and runtime install boundaries.

#### Optional Multi-Agent Pack Candidate Evidence

Issue #79 uses the Tiny IPA `tools/agents/` helpers and companion design docs as product-project evidence for the first optional capability pack candidate. The evidence is useful because it has already exercised role-generic routing, fast label inboxes, dry-run pickup and handoff, contract parsing, and read-only audit checks in a real multi-agent project. It is not canonical Agent Foundry content by itself, and Tiny IPA must not become a hidden runtime dependency after packaging.

Reusable candidate nucleus:

| Candidate area | Candidate contents | Packaging stance |
| --- | --- | --- |
| Practices | role-generic `needs:<role>` routing, durable handoff comments, explicit Execution Contract fields, dependency-gated ready queues, dry-run before mutation, read-only audit first | Candidate or proposed Vault records after review; not active by default merely because the pack is deployed. |
| Asset | role-generic GitHub scheduler helper set for inbox, ready queue, pickup, handoff, audit, label routing, and context summary | Candidate asset that declares permissions, dependencies, supported roles, dry-run behavior, and install boundary. |
| Docs/templates | role routing configuration guide, Execution Contract template, pickup/handoff comment templates, reviewer/architect handoff examples | Pack docs or templates copied into the Vault/import surface as examples, not Core defaults. |
| Scripts | `agent-inbox`, `agent-ready-queue`, `agent-pickup`, `agent-handoff`, `agent-audit`, `agent-issue-context`, `agent-pr-context`, `agent-label`, `agent-role-config`, `gh-retry`, shared role config library, and tests | Executable payload candidates only. They remain inert in the pack snapshot and require managed runtime/tool install before use. |
| Optional overlay | Project v2 status sync, roadmap status mapping, project ids, status option ids, issue type labels, and cache paths | Project-local overlay, not reusable defaults. Omitted unless a target project explicitly configures them. |

Rejected-as-pack for this candidate:

- Tiny IPA's default `GH_REPO`, GitHub Project id, status field ids, status option ids, `.agent-cache` files, issue numbers, branch names, and current project-specific label/status conventions.
- Mutating `--apply` behavior before the helper install and permission boundary is implemented.
- Treating Project v2 as the scheduler source of truth.
- Copying helper scripts into Core `scripts/` as platform tooling.
- Executing helpers from Tiny IPA, pack staging, or canonical Vault payload paths after import.
- Packaging Tiny IPA design notes as active Agent Foundry practices without a separate harvest review.

The candidate pack should therefore be evaluated as a reviewed snapshot: evidence from Tiny IPA, optional public pack fixture, deployable candidate practice and asset records, no executable payload metadata in the current manifest, no runtime install, and no private path leakage. If later implementation imports the pack, the selected User Vault owns the resulting records; the pack remains provenance and update-comparison evidence, not a live authority. Helper scripts remain deferred evidence until managed helper install, dependency checks, permissions, receipts, and rollback behavior are implemented.

### AF-6 Complete Install And Pack Lifecycle Boundary

AF-6 promotes the AF-5 onboarding model from reviewed design into an end-to-end lifecycle. The scope is not only first install. It also covers existing installations where a user already has Core and a selected Vault and now needs to check state, deploy a known pack, compare an updated pack snapshot, apply reviewed records, refresh generated output, install runtime copies, disable a capability, or restore another machine.

AF-6 keeps these authority rules:

- Core owns platform tooling, validation, generation, install orchestration, status reporting, and rollback helpers.
- The selected User Vault owns canonical practices, assets, indexes, pack membership metadata, accepted payload metadata, and user edits after deployment.
- Capability pack snapshots are transfer and comparison artifacts. They are not queried by `refresh` after deployment and are not live runtime authorities.
- Generated output is derived from Core plus the selected Vault.
- Runtime copies and helper installs are machine-local and require managed markers, receipts, dependency checks where relevant, and rollback semantics.

Pack lifecycle support should therefore be split into report, plan, apply, refresh/install, and rollback phases:

| Phase | Required behavior |
| --- | --- |
| Report | Resolve Core/Vault roots, selected generated output, runtime manifest, installed pack metadata, receipts, manual targets, and stale references without writing. |
| Plan | Compare a known local or explicitly named remote pack snapshot with current Vault records, pack membership metadata, manifest compatibility, per-record hashes, local edits, executable payload metadata, and runtime impact. |
| Apply | Write or update selected Vault records only after review, preserving user edits and failing closed for incompatible schema ranges, unknown provenance, same-version hash mismatch, unrelated id collision, or unapproved executable install. |
| Refresh/install | Regenerate output from current Vault state and install only managed runtime copies or manual-import instructions. Do not install directly from pack staging or canonical Vault payload paths. |
| Rollback/disable | Prefer Vault lifecycle state changes, pack membership metadata, regeneration, and runtime receipt rollback over deletion. Report manual targets separately. |

Non-new-install pack update checks should answer:

- Is this the same pack id and version with the same manifest/content hash?
- Is the available snapshot newer, and is the current Vault record unchanged since import?
- Did the user modify a pack-sourced record after deployment?
- Did the pack's promised use case, first-run behavior, activation/default behavior, compatibility range, included record set, executable payload metadata, or security/privacy posture change?
- Does the change belong inside this pack's selected contract, or is it ordinary Vault evolution that should not force a pack version bump?

The first optional pack validation case is the multi-agent collaboration pack. It should prove the generic pack lifecycle without turning Tiny IPA into a hidden dependency, without copying product-project defaults into Core, and without executing helper scripts until the managed helper install boundary is implemented.

#### AF-6 Install UX Contract (#98)

AF-6 uses a small command map rather than a wizard-first design. Scripts may later be wrapped by a friendlier CLI, but the contract below is the source of truth for implementation.

| User intent | Command shape | Writes allowed | Required report |
| --- | --- | --- | --- |
| Inspect an existing install | `python3 scripts/sync_status.py` | None | Core/Vault roots, root validation, generated output, deployed packs, runtime manifest, selected-output receipt, manual targets, stale references, next safe actions. |
| Dry-run a fresh install | `python3 scripts/install_foundry.py --fresh-install --vault-root <path>` | None | Proposed Core root, Vault root, bootstrap pack, generated output root, runtime targets, manual ChatGPT status, and what `--apply` would write. |
| Create/select Vault and publish generated output | `python3 scripts/install_foundry.py --fresh-install --vault-root <path> --apply` | Vault initialization when missing, bootstrap deployment, generated adapter output, machine-local locator unless suppressed. | Same as dry-run plus created/skipped Vault markers, bootstrap deployment result, generated output manifest, locator write status, first safe command. |
| Install managed runtime copies | Add `--runtime-apply` after a successful dry-run | Managed runtime targets declared in `runtime/local/runtime_manifest.yaml`; install receipt. | Per-target managed/skipped/manual state, receipt path, checked files, rollback visibility, ChatGPT manual import note. |
| Refresh existing generated output | `python3 scripts/publish_adapters.py --output-root <generated-root> --apply` or future wrapper | Generated output only. | Selected Vault, active records included, manifest/hash, output root, no runtime write unless a later install step runs. |
| Repair or reinstall runtime copies | `python3 scripts/install_foundry.py --adapter-root <generated-root> --apply` after status/review | Managed runtime targets only. | Selected-output receipt, per-target installed files, skipped/manual targets, stale-reference scan result. |

Default path policy:

- Core root is the public Agent Foundry checkout that passes Core markers.
- Vault root must be explicit for first install until a reviewed account/profile identity exists. A future default may be `~/.agent-foundry/vault/agent-foundry-vault-<account>`, but scripts must display it before writes and allow override.
- Generated output default for fresh install is machine-local under `~/.agent-foundry/generated/agent-foundry-adapters`; tracked Core `adapters/` remain distribution/reference output, not the selected split runtime authority.
- `~/.agent-foundry/config.yaml` is written only in apply mode and remains a machine-local locator, not canonical knowledge.

Install preflight must classify writes before mutation:

| Class | Examples | Write rule |
| --- | --- | --- |
| Core | public scripts, schemas, templates, docs | Read-only during install/status. |
| Vault | blank Vault markers, bootstrap records, indexes, pack metadata | Written only by explicit `--apply` after root validation and operation-context report. |
| Generated | selected generated adapter output | Written by publish/refresh apply; safe to delete/regenerate only under generated-output root. |
| Runtime | Codex, Claude Code, Hermes managed paths; ChatGPT manual import | Managed targets need dry-run visibility, markers or adoption policy, receipt, and rollback path. ChatGPT remains manual. |
| Local locator | `~/.agent-foundry/config.yaml` | Written only after explicit apply; backup or report previous value when overwriting. |

Runtime apply requires a stronger gate than generated-output apply. It may proceed without a separate prompt only when the target is enabled in the local runtime manifest, the destination is already managed or safely adoptable according to runtime policy, the dry-run report names every changed path, and rollback receipt behavior is available. If any target is unmanaged, ambiguous, shared without managed block, or missing rollback visibility, the command must stop or route to `needs:human`.

Failure and recovery behavior:

- If Core or Vault root validation fails, stop before any write and print the failing markers.
- If bootstrap deployment fails, preserve an initialized blank Vault if it is valid and report how to rerun; do not continue to generated output or runtime install.
- If generated output publish fails, do not install runtimes.
- If runtime install fails after some managed targets succeed, write or preserve receipts for successful targets when possible and report partial state.
- Existing install repair must start with report-only status. Repair actions should be explicit follow-up commands, not hidden writes inside status.

Downstream implementation work:

- #102 owns improving existing install status/repair reporting.
- #106 owns pack plan/check report behavior.
- #100/#101 own optional pack apply and update behavior.
- #104 owns disable/rollback/restore behavior.

#### AF-6 Pack State Metadata Contract (#99)

The selected User Vault should record deployed pack state under a Vault-owned metadata area:

```text
packs/deployed-pack-index.yaml
```

This file is canonical Vault metadata, but it is not the authority for whether a practice or asset is active. Practice and asset records plus their indexes remain the canonical source for current capability content. Pack metadata exists to support provenance, status, update comparison, conflict detection, disable/retire planning, and rollback reporting.

Minimal `deployed-pack-index.yaml` shape:

```yaml
schema_version: 1
updated: YYYY-MM-DD
deployed_packs:
  - pack_id: pack.example
    title: Example Pack
    version: 0.1.0
    lifecycle_status: deployed
    distribution_type: optional_capability
    deployed_at: YYYY-MM-DDTHH:MM:SSZ
    source:
      kind: local_path | git_ref | archive | url
      locator: "<path-or-url-or-ref>"
      manifest_sha256: "<sha256>"
      reviewed_by: human | architect | reviewer
    compatibility:
      core_schema_versions: []
      vault_layout_versions: []
    records:
      - id: PRACTICE-001
        kind: practice
        path: practices/domain/file.md
        imported_version: "1"
        imported_sha256: "<sha256>"
        deployed_sha256: "<sha256>"
        lifecycle_status_at_import: candidate
        current_state: unchanged | locally_modified | missing | retired | archived | unknown
        membership_role: primary | supporting | optional
        activation_default: candidate | proposed | active | inactive
    executable_payloads:
      - id: helper.example
        install_boundary: managed_runtime_copy_required
        source_sha256: "<sha256>"
        install_state: blocked | not_installed | installed | manual
    decisions:
      conflict_policy: fail_closed | merge_required | skip_if_present
      notes: []
```

Metadata rules:

1. A deployed pack record is provenance and comparison evidence. It does not override the current lifecycle status inside a practice or asset record.
2. Ordinary reviewed Vault CRUD remains valid after pack deployment. If a user edits a pack-sourced record, that edited record is canonical user state.
3. Later pack updates compare against `imported_sha256`, `deployed_sha256`, current file hash, current index entry, and current lifecycle state. Local edits produce a merge proposal, not overwrite.
4. Same pack id plus same version plus different `manifest_sha256` fails closed because the snapshot is not reproducible.
5. Same record id with unrelated provenance or incompatible kind fails closed as an id collision.
6. A record may appear in multiple packs. Membership metadata is many-to-many provenance, not ownership.
7. Retiring, archiving, or disabling a pack should prefer lifecycle changes and regeneration over deletion. Pack metadata may mark records as disabled or retired by pack operation, but it must not erase user-created records.
8. Remote source locators are provenance only unless a later trust model makes a registry authoritative. AF-6 supports explicit known sources, not marketplace discovery.
9. Executable payload metadata must remain blocked or not-installed until managed helper install, dependency, permission, receipt, and rollback behavior exist.

Index and record relationship:

| Surface | Role |
| --- | --- |
| `practices/` and `assets/` records | Current canonical content and lifecycle state. |
| `indexes/practice_index.yaml` and `indexes/asset_index.yaml` | Search and routing indexes for current records. |
| `packs/deployed-pack-index.yaml` | Pack provenance, imported snapshot comparison, and update/disable planning. |
| Generated adapters or runtime skills | Downstream output from active or selected Vault records; never read pack snapshots directly. |

Downstream implementation work:

- #106 reads this metadata for generic plan/check.
- #100 writes this metadata during optional pack apply.
- #101 uses it for update comparison and local-edit detection.
- #104 uses it for disable, retire, rollback, and restore reporting.

## Operating Context Separation

Agent Foundry must remain safe when it is used inside another software project. Users and agents regularly operate in nested contexts:

1. **Product project context**: the user's actual software project, such as `token-panic`. This project is the evidence source and work target.
2. **Foundry Vault context**: harvest, refresh, review, asset discovery, and adapter publishing for the user's Agent Foundry capability records.
3. **Foundry Core maintenance context**: changing Agent Foundry's workflows, schemas, scripts, templates, adapter generation, install behavior, or roadmap.

These contexts must not be inferred only from the current working directory or from a recent chat message. Before writing files, installing adapters, recording evidence, or updating GitHub issues, an agent should identify:

```text
work context: product project | foundry vault operation | foundry core maintenance
evidence source: <project/session/import path>
canonical vault root: <path>
core root: <path>
write target: <repo/path/runtime>
review target: current session | user | separate reviewer | batch checkpoint
```

Context rules:

1. Product project work may generate evidence for Agent Foundry, but the product project is not the canonical Foundry Vault unless it validates as one.
2. Foundry Vault operations may read product project evidence, but canonical practice/asset/index writes go to the active Vault.
3. Foundry Core maintenance changes reusable machinery and should go through Core review, even when prompted by a product project session.
4. Runtime adapter install writes to user-owned runtime directories and must be derived from Core plus the selected Vault.
5. `refresh practices and assets` is a Vault/Core synchronization command, not a product project dependency install.
6. `harvest practices` must route artifacts before writing: product facts stay with the product project, reusable practices/assets go to the Vault, and Core workflow defects become Core maintenance.
7. After the physical split, agents must validate both `core_root` and `vault_root` before canonical writes. If either is missing or ambiguous, stop and ask instead of guessing.

Failure modes this prevents:

- writing product project notes into the Foundry Core repo;
- harvesting a project-local decision as a general Foundry practice;
- modifying Core scripts when the user intended only to refresh a Vault;
- installing stale adapters from the wrong Vault;
- treating the maintainer's Vault as a default public capability pack;
- using future memory-system paths as current writable destinations.

## Configuration Boundary

Configuration is split by portability and ownership. Core should define schemas, templates, and validation behavior. Vault should define the user's canonical capability records and portable vault policy. Runtime/local files should define machine-specific paths, enabled targets, adoption decisions, and sync state.

Use these configuration classes:

| Class | Examples | Ownership | Git behavior |
| --- | --- | --- | --- |
| Core config intent | adapter profiles, schemas, workflow defaults, runtime manifest template | Public Core | Tracked |
| Vault config intent | vault metadata, selected capability packs, privacy defaults, optional import-pack choices | User Vault | Tracked in the user's Vault when non-sensitive |
| Machine-local locator | `~/.agent-foundry/config.yaml` with `core_root`, `vault_root`, markers, and compatibility fields | User machine | Not tracked |
| Machine-local runtime deployment | `runtime/local/runtime_manifest.yaml`, enabled runtimes, install paths, adoption decisions | User machine | Gitignored |
| Runtime copies | installed files under Codex, Claude Code, Hermes, and manual ChatGPT imports | User runtime | Outside Core/Vault canonical records |
| Product project config | the actual software project's build/test/app config | Product project | Owned by the product project |

Locator semantics:

- `core_root`: path to the reusable Agent Foundry Core that provides workflows, schemas, scripts, templates, adapter profiles, and docs.
- `vault_root`: path to the active User Vault that provides practices, assets, indexes, shared aggregates, and vault-local docs.
- `repo_root`: compatibility field for current single-repo operation. After physical split, it should be derived or deprecated rather than treated as proof that Core and Vault share a root.
- `core_markers`: markers that validate Core before running Core tooling. Required examples include `workflows/harvest-practices.md`, `schemas/practice-entry.schema.yaml`, and `scripts/foundry_config.py`.
- `vault_markers`: markers that validate a Vault before canonical writes. Required examples include `indexes/practice_index.yaml`, `indexes/asset_index.yaml`, and `usage/usage-aggregate.yaml`.
- `canonical_markers`: deprecated compatibility field from the single-root staging state. It may be read for old local configs, but new configs should use `core_markers` and `vault_markers`.

Current capability: `scripts/foundry_config.py` records separate `core_root`, `vault_root`, and compatibility `repo_root` values, and emits separate Core and Vault marker lists. Split mode is valid when both roots validate. Same-root operation remains a compatibility path, not proof that Core and Vault are the same authority.

Locator precedence:

1. Explicit user-provided `--core-root` and `--vault-root` flags, when a command supports them.
2. Paired `AGENT_FOUNDRY_CORE` and `AGENT_FOUNDRY_VAULT` environment variables, after commands implement them.
3. `~/.agent-foundry/config.yaml`.
4. `AGENT_FOUNDRY_HOME` as a same-root compatibility locator.
5. Current directory only if it validates as the required context for the requested operation.
6. Ask the user.

Do not treat a single root found through `AGENT_FOUNDRY_HOME` or current directory as proof that split mode is unsupported. It is only a compatibility path. Commands should prefer explicit Core/Vault roots once they are available.

Do not use a product project checkout as a Vault merely because the user is working there. Do not use a Vault as Core merely because it contains practices. Do not use Core as a Vault merely because it has templates or examples.

`scripts/operation_context.py` is the current preflight guard for this boundary. It reports invocation cwd, operation type, work context, evidence root, selected Core/Vault roots, generated adapter output route, manual targets, allowed reads, allowed writes, forbidden writes, root validation, and warnings. Harvest, publish, install, refresh, and status workflows should display this context before writes or installs.

Operation-to-config mapping:

| Operation | Required context | Reads | Writes |
| --- | --- | --- | --- |
| Product development | Product project | Product project plus optional Foundry adapter guidance | Product project |
| `harvest practices` | Product project evidence plus Foundry Core and active Vault | Evidence source, Core workflow/schema, Vault index | Vault canonical records after review |
| `refresh practices and assets` | Core plus active Vault plus local runtime manifest | Core tooling, Vault records, runtime local manifest | runtime copies and optional sanitized aggregate |
| `publish adapters` | Core plus active Vault | Core adapter profiles, Vault practices/assets | generated adapter outputs and runtime copies after approval |
| Operation context preflight | current cwd plus selected Core/Vault | Core/Vault markers, runtime manifest, install receipt when relevant | no writes |
| Foundry Core maintenance | Core | Core docs/workflows/scripts/schemas | Core repo |
| Vault maintenance | active Vault | Vault practices/assets/indexes/usage | Vault repo |

Failure states should be explicit:

- Core missing: cannot run Foundry tooling; ask for Core root.
- Vault missing: cannot write practices/assets/indexes; ask for Vault root or initialize a Vault.
- Product project ambiguous: ask whether the current directory is evidence source or canonical destination.
- Runtime target missing: skip or mark missing; do not delete installed files automatically.
- Manual target such as ChatGPT: produce import instructions, do not pretend install is automatic.
- Core and Vault version mismatch: stop or warn before publishing adapters.

Onboarding implication: a blank Vault is the first state, not the complete usable setup. Future onboarding should always create a blank Vault, deploy the mandatory bootstrap pack as canonical Vault data, optionally deploy selected capability packs, and then run `refresh`. Existing Codex, Claude Code, Hermes, or ChatGPT assets remain import candidates, not canonical truth, unless the user accepts them into the Vault.

Machine-local locator:

```text
~/.agent-foundry/config.yaml
```

This file records `repo_root`, `core_root`, `vault_root`, Core markers, and Vault markers. It is written during install and is not canonical knowledge. Agents working in another repository should locate Agent Foundry through this config or `AGENT_FOUNDRY_HOME`, then validate Core and Vault separately before writing canonical records. After the physical split, `core_root` and `vault_root` may intentionally point to different repositories or directories; agents must validate both instead of assuming one repo root.

## Generated Artifact Policy

Generated artifacts are downstream projections from canonical records, not independent sources of truth.

Use these categories:

| Category | Current examples | Git behavior | Source of truth |
| --- | --- | --- | --- |
| Core source | `workflows/`, `schemas/`, `templates/`, source scripts, `adapters/adapter_profiles.yaml`, adapter quality rules, product docs | Tracked in public Core | Source-maintained tooling and operating rules |
| User Vault canonical records | `practices/`, `assets/`, `indexes/`, reviewed imports, `usage/usage-aggregate.yaml` | Tracked in the selected User Vault, not public Core by default | Human-reviewed canonical records and sanitized Vault metadata |
| Tracked generated distribution output | `adapters/codex/`, `adapters/hermes/`, `adapters/claude-code/`, `adapters/chatgpt/` | Tracked when needed for runtime install, manual import, review, or distribution | Canonical practices/assets plus adapter profiles |
| Runtime copy | Installed files under `~/.codex`, `~/.claude`, `~/.hermes`, and manual ChatGPT imports | Not tracked here | Regenerated or installed from `adapters/` |
| Local private/generated operational state | `runtime/local/`, `usage/local/`, `usage/adoption-log.yaml`, `sync/local/`, `sync/imported/`, `sync/pending/`, `sync/applied/`, `sync/conflicts/`, `sync/snapshots/` | Gitignored by default | Local runtime, sync, or evidence workflows |
| Shared aggregate or derived metadata | Future Core-owned derived indexes if approved | Tracked only when sanitized, reviewable, and Core-owned | Derived metadata, not raw local evidence |

Rules:

1. Edit canonical records first. Practice, asset, workflow, schema, template, or source-tool changes must be made upstream before regenerating downstream artifacts.
2. Track generated artifacts only when they serve a durable review, distribution, install, manual-import, or offline-sync purpose. Otherwise prefer regeneration or ignore them.
3. Tracked generated artifacts must have an explicit regeneration path or a documented manual-target rationale. Adapter outputs are tracked because local runtimes and ChatGPT manual import need concrete files.
4. Runtime copies are never canonical. If a runtime copy drifts, regenerate or reinstall from repository adapters rather than treating the runtime file as policy.
5. Local private or sensitive generated state stays ignored unless a later policy explicitly defines a sanitized shared form.
6. Shared aggregate files may be tracked when they avoid raw evidence and support review. They are still user-vault metadata, not Core default content for a blank external-user vault.
7. Future memory indexes, knowledge packs, graph indexes, or retrieval bundles should be derived from approved current capability records. Do not create `memory/`, top-level `knowledge/`, `research_memos/`, or `project_memory` outputs until reviewed architecture introduces them.
8. Adapter packaging paths such as `adapters/chatgpt/knowledge/` are generated/manual-import adapter outputs. They do not imply that a current top-level memory subsystem `knowledge/` directory exists.

Cleanup and regeneration expectations:

- If canonical records change, publish relevant adapters, run adapter quality checks, then install to enabled runtimes.
- If generated tracked files are hand-edited in an emergency, back-propagate the durable rule to canonical records or document why the generated artifact is intentionally source-maintained.
- If a generated artifact cannot be reproduced or checked, treat that as a policy gap before relying on it for external-user setup.
- If generated files include local paths, raw evidence, secrets, or sensitive content, move them to ignored local/private paths or replace them with sanitized aggregates/templates.

## Usage Evidence Boundary

Usage evidence is split by sensitivity and sync behavior.

Raw evidence is local. Agents write concise raw entries to `usage/local/usage-log.yaml`, which is gitignored and excluded from portable snapshots. Raw entries may include project names, triggers, short notes, and local audit context.

Aggregate evidence is shared. `usage/usage-aggregate.yaml` contains sanitized counts by subject type, subject ID, month, agent, hashed machine ID, outcome counts, and last-used date. Review workflows use the aggregate so multiple machines and agents can contribute statistics without syncing raw notes or session context.

Legacy `usage/asset-usage-log.yaml` remains migration input. New recording should go through `scripts/record_asset_usage.py`, and aggregate rebuilds should use `scripts/aggregate_usage.py`.

## Local And Private Data Policy

Agent Foundry is local-first, but local-first does not mean every local artifact belongs in git. The public Core repository contains portable Core files and tracked generated adapter outputs. Canonical User Vault records and sanitized shared aggregates belong to the selected User Vault. Raw evidence, machine state, secrets, personal exports, and sensitive material stay local unless a reviewed policy defines a sanitized shared form.

Default classifications:

| Data class | Current examples | Git behavior |
| --- | --- | --- |
| Machine-local runtime state | `runtime/local/`, `~/.agent-foundry/config.yaml`, enabled runtime paths, adoption decisions | Ignored or outside the repo |
| Raw usage evidence | `usage/local/usage-log.yaml` | Ignored |
| Sanitized usage aggregate | `usage/usage-aggregate.yaml` in the selected User Vault | Tracked in the Vault, not public Core by default |
| Offline sync operational state | `sync/local/`, `sync/imported/`, `sync/pending/`, `sync/applied/`, `sync/conflicts/`, `sync/snapshots/` | Ignored |
| External skill staging instructions | `imports/*/INSTRUCTIONS.md` in the selected User Vault or future Core templates | Tracked only in the owning layer |
| Raw external imports or exports | downloaded skills, raw chat exports, transcripts, source dumps, sensitive review packets | Not committed by default; stage only after explicit review |
| Runtime adapter outputs | `adapters/codex/`, `adapters/claude-code/`, `adapters/hermes/`, `adapters/chatgpt/` | Tracked distribution/manual-import outputs |
| User workspace affordances | `Agent Foundry.md`, Obsidian-oriented metadata, local agent settings | Treat as User Vault or maintainer-local unless promoted into Core by review |

Rules:

1. Raw ChatGPT exports, transcripts, session dumps, raw research packets, and future memory evidence are evidence sources, not canonical records. Do not commit them by default.
2. If raw evidence is needed for review, place it in an implemented review/staging path only after checking sensitivity, provenance, and whether a summarized or sanitized form is enough.
3. Secrets, tokens, credentials, private keys, exact local runtime paths from other machines, personal account exports, and sensitive third-party data must never be committed.
4. Machine-local manifests and adoption logs remain local. Portable templates may be tracked when they contain no local path, account, or adoption decision.
5. Shared aggregates are allowed only when they exclude raw prompts, transcripts, sensitive notes, and project-specific details that would expose private context.
6. Future memory-system evidence follows the same boundary: raw memory records, knowledge imports, source digests, embeddings, and graph indexes are not current writable substrates and must not be introduced through AF-1 policy work.
7. `.gitignore` is the enforcement floor, not the whole policy. If a path is not ignored but contains private material, do not commit it merely because git permits it.

Current ignored local/private paths include `runtime/local/`, `usage/local/`, `usage/adoption-log.yaml`, and the operational sync paths under `sync/`. If new workflows introduce local state, they must extend this policy and `.gitignore` together.

## Example Versus User Content Separation

Agent Foundry now separates reusable Core machinery from the selected User Vault. External users must not be asked to inherit the maintainer's personal vault as if it were product Core.

Use these terms:

- `Core`: portable workflows, schemas, scripts, templates, adapter profiles, generation/check tooling, and docs needed to operate Agent Foundry.
- `User Vault`: a user's canonical practices, assets, indexes, shared aggregates, and long-form local notes.
- `Example`: intentionally curated sample records that demonstrate shape, naming, lifecycle, and review behavior without becoming required personal content.
- `Generated`: adapter outputs, knowledge packs, and derived metadata produced from Core plus Vault records.
- `Runtime`: installed downstream files in a specific agent environment.
- `Local Private`: raw evidence, local manifests, adoption decisions, secrets, and sensitive exports.

Current repository classification:

| Path or content | AF-3 classification | External-user implication |
| --- | --- | --- |
| `workflows/`, `schemas/`, `scripts/`, `templates/`, `runtime/templates/` | Core | Reusable distribution substrate |
| `practices/`, `assets/`, `indexes/`, `usage/usage-aggregate.yaml` | User Vault outside public Core by default | Must not be copied wholesale into a blank external-user vault by default |
| `adapters/` | Generated distribution outputs plus source-maintained adapter profiles/quality material | Regenerate from the target user's vault; tracked here for current runtime install and manual imports |
| `docs/` | Core documentation plus proposed design evidence | External-user setup guidance must distinguish current capability from future plans |
| `docs/memory-system-handoff-dump.md` | Proposed Design Evidence | Do not treat as implemented memory-system architecture |
| `Agent Foundry.md` | User Vault navigation/hub for the maintainer's Obsidian-style workspace | Not a required Core file for external users |
| `.claude/settings.json` | Maintainer/runtime-specific workspace setting | Should not become product setup guidance without AF-2 review |

Example conventions:

1. Examples must be clearly labeled as examples, templates, or sample vault records.
2. Example records should avoid real personal project history, private paths, raw session evidence, and maintainer-specific runtime assumptions.
3. A blank vault should start from schemas, templates, empty indexes, and empty or zeroed aggregates, not from the maintainer's active practices/assets by default.
4. The maintainer's active practices and assets may be used as design references or optional import packs only after the Core/Vault split defines that packaging model.
5. Adapter outputs for an external user should be generated from that user's approved vault records, not copied from this repository's personal vault unless explicitly deployed through a reviewed capability pack.
6. Proposed memory-system material must stay in docs/imports/evidence form until reviewed architecture creates implemented memory directories, schemas, and workflows.

AF-3 implements the Core/Vault split and blank Vault initialization path. AF-4 proves the current user's multi-deployment operation on top of that split. AF-5 establishes onboarding and capability-pack journey contracts on top of the proven boundary. AF-6 completes the install and pack lifecycle as a repeatable product path.

## Practice Types

- `principle`: durable design or engineering rule.
- `pattern`: reusable solution shape for a recurring problem.
- `heuristic`: decision aid or question that guides judgment.
- `playbook`: multi-step procedure for a task.
- `checklist`: compact verification list.
- `example`: concrete grounding for a broader rule.
- `anti-pattern`: recurring mistake to avoid.

## Lifecycle

```text
candidate -> proposed -> active -> revised -> superseded -> archived
```

- `candidate`: captured from a session or external source, not yet trusted.
- `proposed`: normalized and deduped, waiting for human approval.
- `active`: approved for use and publication into adapters.
- `revised`: active entry with material updates.
- `superseded`: replaced by another entry; keep for traceability.
- `archived`: no longer recommended and not published.

## Human Review Gate

Human review is mandatory before a practice becomes `active`. After approval, relevant adapters should be published automatically unless the user asks to stage without publishing.

Agents may:

- extract candidates;
- classify them;
- search for duplicates;
- propose merges;
- draft canonical entries;
- update adapters after approval.

Agents should not:

- silently promote new practices to `active`;
- import public skills directly into adapters;
- execute external scripts without explicit permission;
- overwrite canonical entries without explaining the merge decision.

## Adapter Strategy

Each agent environment gets its own adapter because each has different instruction mechanics:

- Codex: `SKILL.md` folders with references.
- Claude Code: `CLAUDE.md` and optional slash commands.
- ChatGPT: custom/project instructions plus knowledge files.
- Hermes: `SKILL.md` folders with references.
- DeepSeek, MiniMax, and similar systems: underlying model providers used through direct programming agents, not direct adapters here.

Adapter entry points should be compact, task-triggered, and operational. Full fidelity is provided through references, command files, or knowledge files rather than one large prompt.

## External Skill Borrowing Strategy

External skills are treated as inputs, not authorities.

Borrowing path:

```text
external skill/repo/article
  -> provenance record in imports/inbox/
  -> security and quality review
  -> candidate practices
  -> dedupe against index
  -> proposed canonical entries
  -> human approval
  -> active practices
  -> adapters
```

Good external material may contribute wording, workflows, trigger descriptions, schemas, or examples. It should not be copied wholesale unless the license permits it and the content passes review.

## Skill Rot Controls

This repository avoids skill rot through:

- stable IDs for practices;
- lifecycle states;
- alias and related-entry metadata;
- dedupe before creation;
- human approval before activation;
- adapter outputs generated from active practices only;
- periodic reviews of stale, conflicting, or too-generic entries;
- separation between long-form docs and compact agent instructions.
- cross-project governance rules that keep derived views, transient context, and runtime integrations from becoming hidden maintenance burdens.
