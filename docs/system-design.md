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

See docs/lifecycle-compatibility.md for how this loop adapts across Codex, Claude Code, Hermes, and ChatGPT from harvest through activation, evidence, and review.

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

The target product direction is a reusable public Core with user-owned Vaults. A user's Vault is private by default unless that user explicitly chooses to publish it. In the current repository, the maintainer's User Vault belongs to the maintainer, Jinghu, and should not remain bundled into a public Core distribution before Agent Foundry claims external-user readiness.

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
5. Do not claim external-user readiness while the maintainer's Vault remains required inside the public Core repository.

## Maintainer Vault Extraction Plan

This is the AF-3 decision baseline for extracting Jinghu's current User Vault from the public Core. It is a plan and verification contract, not approval to move records.

Default target:

- Core remains the public `farmerhunter/agent-foundry` repository or its renamed public successor.
- Jinghu's maintainer Vault should move to a private-by-default Git repository or private local repository named `agent-foundry-vault-jinghu` unless the user chooses another name before execution.
- The local path should be explicitly configured through `~/.agent-foundry/config.yaml` as `vault_root`; agents must not infer it from a product project checkout.

Move to the private maintainer Vault:

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
4. Initialize or select the private maintainer Vault target.
5. Copy records into the private target and run `python3 scripts/check_foundry_roots.py --core-root <core> --vault-root <private-vault>`.
6. Run `python3 scripts/publish_adapters.py --core-root <core> --vault-root <private-vault> --output-root <temp-output> --apply`.
7. Update `~/.agent-foundry/config.yaml` only after Core and Vault validate separately.

Stop conditions:

- Any required Vault path is missing from the backup or private target.
- Any public Core file still requires maintainer active practices/assets as default content.
- Any generated adapter output includes raw evidence, local private paths, or maintainer Vault records when run against a blank or custom Vault.
- Runtime install would overwrite unmanaged files or point at the old combined root without an explicit migration step.
- A private remote must be created, files must be deleted, history must be rewritten, or records must be moved out of the current repo. These require explicit user approval at execution time.

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

`init-vault` should mean "create a valid, empty canonical destination" rather than "copy the maintainer's current vault." It should initialize structure and metadata only. It should not activate practices, install runtime adapters, import external skills, deploy capability packs, or write memory-system records.

Blank Vault contents:

| Vault path or record | Blank state | Source of shape |
| --- | --- | --- |
| `practices/` | Empty practice tree, with no active/candidate/proposed practice records copied from the maintainer Vault. | Core schemas and templates. |
| `assets/` | Empty asset tree, with no active/candidate/proposed asset records copied from the maintainer Vault. | Core schemas and templates. |
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
2. It contains no maintainer-specific practices, assets, usage aggregate rows, local paths, runtime adoption decisions, raw evidence, or future memory-system directories.
3. Empty indexes and empty aggregates are accepted as valid starting state.
4. Practice and asset creation workflows can add the first candidate without requiring preexisting personal records.
5. Adapter publishing can report "nothing to publish" or produce an empty/minimal adapter output without treating that as a failure.
6. Runtime install must not copy the maintainer's generated adapters into a new user's runtime.
7. Consistency checks distinguish "empty but valid Vault" from "missing or corrupt Vault."
8. Pack deployment can add canonical data after initialization without changing the definition of blank Vault.

Implemented AF-3 baseline:

- `scripts/init_vault.py` creates empty `practices/`, `assets/`, `imports/inbox`, `usage/local`, empty practice and asset indexes, and an empty shared usage aggregate;
- blank Vault initialization does not copy maintainer practices/assets;
- blank Vault initialization does not trigger runtime install;
- `scripts/publish_adapters.py` validates selected Core/Vault roots before publishing;
- blank Vault adapter publishing reports `nothing to publish`;
- maintainer-like Vault adapter publishing can produce deterministic adapter outputs in a selected output root.

Implementation implications still remaining for AF-3:

- scripts that currently assume repository-relative `practices/`, `assets/`, `indexes/`, and `usage/` must accept a separate `vault_root`;
- checks should validate Core schemas/workflows against an arbitrary Vault;
- generated adapter outputs should be derived from the selected Vault, not from this repository's maintainer Vault by default;
- blank-vault fixtures or templates should be reproducible from Core and should not require copying personal records;
- later pack deployment should be able to populate a blank Vault with the mandatory bootstrap pack before `refresh`;
- migration must test both the maintainer Vault and a blank/new-user Vault.

Rejected as #7 scope:

- creating `memory/`, `knowledge/`, `research_memos/`, or `project_memory`;
- importing runtime skills or ChatGPT exports;
- implementing capability pack deployment before the blank Vault and selected-root substrate are reviewed;
- moving the maintainer's Vault into a private repo;
- implementing `init-vault` scripts before the design is reviewed.

## External-User Setup Boundary

External-user setup is not a current complete quickstart. AF-2 defines the boundary and prerequisites; AF-3 must physically split public Core from the maintainer's private Vault, and AF-4 must define onboarding modes before Agent Foundry can claim a tested external-user start path.

Current capability:

- single-repo operation where Core and the maintainer Vault share one repository root;
- machine-local runtime manifest setup for the current user;
- adapter install into enabled local Codex, Claude Code, and Hermes runtimes;
- manual ChatGPT import from generated adapter files;
- logical Core/Vault separation documented in this file;
- blank Vault initialization design, but no implemented `init-vault` command;
- locator config that currently writes `core_root`, `vault_root`, and `repo_root` to the same path.

Target setup narrative after AF-3/AF-4:

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
| What to clone | Current repo contains both Core and maintainer Vault; this is a maintainer setup, not public Core distribution. | AF-3 public Core split. |
| Where Vault lives | Designed as user-owned and private by default; current repo still contains maintainer Vault. | AF-3 maintainer Vault extraction. |
| How blank Vault starts | Defined as empty indexes, empty aggregate, no personal practices/assets. | AF-3 `init-vault` implementation and validation. |
| How Core/Vault are located | `~/.agent-foundry/config.yaml` exists, but current scripts assume one root. | AF-3 separate root support. |
| How adapters are generated | Current adapters are generated from the maintainer Vault. | AF-3 arbitrary-vault adapter generation. |
| How runtimes are installed | Current machine-local manifest installs into selected local runtimes. | AF-3 migration checks for split Core/Vault; AF-4 first-run UX. |
| How bootstrap capability appears | Blank Vault is created first, then mandatory bootstrap pack is deployed as canonical Vault data. | AF-4 pack deployment and first-run verification. |
| How optional capability content appears | Optional capability packs and runtime imports are not blank defaults; they are deployed or imported after the Vault exists. | AF-4 pack selection and import workflow. |
| How existing runtime assets are imported | Existing runtime assets are evidence/candidates first. | AF-4 import workflow. |
| What remains private | Raw evidence, local manifests, adoption state, secrets, maintainer Vault, personal records. | Current policy plus AF-3 migration. |

Docs implications:

- `docs/deployment.md` currently documents maintainer/single-repo deployment and local runtime install.
- `docs/usage.md` currently documents day-to-day use after Agent Foundry is already installed.
- Neither file should be read as a tested external-user quickstart until AF-3 and AF-4 are complete.
- AF-3 should rewrite deployment docs around public Core plus selected Vault.
- AF-4 should add first-run onboarding sequence: blank Vault creation, mandatory bootstrap pack deployment, optional capability pack selection, runtime-asset import when selected, and unified refresh.

Do not promise future memory-system behavior in external-user setup. Memory-system records, `knowledge/`, `research_memos/`, project memory, and MCP memory access remain proposed/future until reviewed architecture implements them.

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

Current capability: `scripts/foundry_config.py` writes `core_root`, `vault_root`, and `repo_root` to the same path for compatibility, but emits separate Core and Vault marker lists. This is still a single-repo staging mode until later AF-3 work teaches all commands to operate on distinct roots.

Locator precedence:

1. Explicit user-provided `--core-root` and `--vault-root` flags, when a command supports them.
2. Paired `AGENT_FOUNDRY_CORE` and `AGENT_FOUNDRY_VAULT` environment variables, after commands implement them.
3. `~/.agent-foundry/config.yaml`.
4. `AGENT_FOUNDRY_HOME` as a same-root compatibility locator.
5. Current directory only if it validates as the required context for the requested operation.
6. Ask the user.

Do not treat a single root found through `AGENT_FOUNDRY_HOME` or current directory as proof that split mode is unsupported. It is only a compatibility path. Commands should prefer explicit Core/Vault roots once they are available.

Do not use a product project checkout as a Vault merely because the user is working there. Do not use a Vault as Core merely because it contains practices. Do not use Core as a Vault merely because it has templates or examples.

Operation-to-config mapping:

| Operation | Required context | Reads | Writes |
| --- | --- | --- | --- |
| Product development | Product project | Product project plus optional Foundry adapter guidance | Product project |
| `harvest practices` | Product project evidence plus Foundry Core and active Vault | Evidence source, Core workflow/schema, Vault index | Vault canonical records after review |
| `refresh practices and assets` | Core plus active Vault plus local runtime manifest | Core tooling, Vault records, runtime local manifest | runtime copies and optional sanitized aggregate |
| `publish adapters` | Core plus active Vault | Core adapter profiles, Vault practices/assets | generated adapter outputs and runtime copies after approval |
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
| Canonical source | `practices/`, `assets/`, `workflows/`, `schemas/`, `templates/`, source scripts, `adapters/adapter_profiles.yaml`, adapter quality rules | Tracked | Human-reviewed canonical records and source-maintained tooling |
| Tracked generated distribution output | `adapters/codex/`, `adapters/hermes/`, `adapters/claude-code/`, `adapters/chatgpt/` | Tracked when needed for runtime install, manual import, review, or distribution | Canonical practices/assets plus adapter profiles |
| Runtime copy | Installed files under `~/.codex`, `~/.claude`, `~/.hermes`, and manual ChatGPT imports | Not tracked here | Regenerated or installed from `adapters/` |
| Local private/generated operational state | `runtime/local/`, `usage/local/`, `usage/adoption-log.yaml`, `sync/local/`, `sync/imported/`, `sync/pending/`, `sync/applied/`, `sync/conflicts/`, `sync/snapshots/` | Gitignored by default | Local runtime, sync, or evidence workflows |
| Shared aggregate or derived metadata | `usage/usage-aggregate.yaml`; future derived indexes if approved | Tracked only when sanitized and reviewable | Raw local evidence or canonical records, depending on artifact |

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

Agent Foundry is local-first, but local-first does not mean every local artifact belongs in git. The repository may contain portable Core files, canonical User Vault records, tracked generated adapter outputs, and sanitized shared aggregates. Raw evidence, machine state, secrets, personal exports, and sensitive material stay local unless a reviewed policy defines a sanitized shared form.

Default classifications:

| Data class | Current examples | Git behavior |
| --- | --- | --- |
| Machine-local runtime state | `runtime/local/`, `~/.agent-foundry/config.yaml`, enabled runtime paths, adoption decisions | Ignored or outside the repo |
| Raw usage evidence | `usage/local/usage-log.yaml` | Ignored |
| Sanitized usage aggregate | `usage/usage-aggregate.yaml` | Tracked |
| Offline sync operational state | `sync/local/`, `sync/imported/`, `sync/pending/`, `sync/applied/`, `sync/conflicts/`, `sync/snapshots/` | Ignored |
| External skill staging instructions | `imports/*/INSTRUCTIONS.md` | Tracked |
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

Agent Foundry currently stores reusable Core machinery and the maintainer's User Vault in one repository. That is acceptable for AF-1, but external users must not be asked to inherit the maintainer's personal vault as if it were product Core.

Use these terms:

- `Core`: portable workflows, schemas, scripts, templates, adapter profiles, generation/check tooling, and docs needed to operate Agent Foundry.
- `User Vault`: a user's canonical practices, assets, indexes, shared aggregates, and long-form local notes.
- `Example`: intentionally curated sample records that demonstrate shape, naming, lifecycle, and review behavior without becoming required personal content.
- `Generated`: adapter outputs, knowledge packs, and derived metadata produced from Core plus Vault records.
- `Runtime`: installed downstream files in a specific agent environment.
- `Local Private`: raw evidence, local manifests, adoption decisions, secrets, and sensitive exports.

Current repository classification:

| Path or content | AF-1 classification | External-user implication |
| --- | --- | --- |
| `workflows/`, `schemas/`, `scripts/`, `templates/`, `runtime/templates/` | Core | Candidate for reusable distribution after AF-2 boundary work |
| `practices/`, `assets/`, `indexes/`, `usage/usage-aggregate.yaml` | User Vault in this repository | Must not be copied wholesale into a blank external-user vault by default |
| `adapters/` | Generated distribution outputs plus source-maintained adapter profiles/quality material | Regenerate from the target user's vault; tracked here for current runtime install and manual imports |
| `docs/` | Mixed Core documentation, User Vault documentation, and proposed design evidence | External-user setup guidance must distinguish product docs from maintainer planning evidence |
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

AF-2 should use this policy to design a blank vault initialization path, a Core/Vault split, and external-user setup boundaries. AF-1 does not move files yet; it marks the boundary so future movement is deliberate.

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
