# Agent Foundry Roadmap

Status: planning document  
Updated: 2026-06-08  
Scope: Agent Foundry productization, repository hygiene, and memory-system readiness.

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
| AF-3 | Split Vault Migration | Core and the maintainer's User Vault are physically separated without breaking existing local runtimes. | Public Core no longer requires maintainer vault content; maintainer Vault is private by default; existing Codex, Claude Code, Hermes, and ChatGPT setups are migrated or given a tested migration path; clean new-user setup is tested. |
| AF-4 | Memory-System Ready | Future memory-system records, evidence policy, routing, privacy, and MCP boundaries are designed but not necessarily implemented. | Memory-system implementation home can be chosen with clear tradeoffs. |
| AF-5 | Memory-System Implementation | A reviewed memory/knowledge system is implemented according to the chosen architecture. | MVP validates the main memory lifecycle without bypassing Agent Foundry governance. |

Current planning stage: AF-2.

AF-0 explains the existing mixed history. AF-1 starts the stricter planning and multi-agent coordination era. AF-2 designs the productization boundary. AF-3 executes the Core/Vault split needed for broad reuse. AF-4 is the decision gate for memory-system architecture. AF-5 is intentionally future work.

## Release Version Mapping

Do not force semantic versioning to carry all planning meaning yet. Use AF stages for maturity and reserve release versions for distribution points.

Suggested mapping:

| Stage Complete | Candidate Release Meaning |
| --- | --- |
| AF-1 | `v0.1.0`: governed personal foundry baseline. |
| AF-2 | `v0.2.0`: productizable architecture and repo hygiene baseline. |
| AF-3 | `v0.3.0`: split Core/Vault migration baseline. |
| AF-4 | `v0.4.0`: memory-system-ready design baseline. |
| AF-5 MVP | `v0.5.0` or later: memory-system MVP, not automatically `v1.0`. |
| Post-AF-5 | Future: capability pack discovery/export after the core lifecycle and memory decisions are stable. |

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
| Stage | AF-1, AF-2, AF-3, AF-4, AF-5 | Maturity stage the item serves. |
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

- `stage:AF-1` through `stage:AF-5`
- `type:epic`, `type:task`, `type:decision`, `type:review`, `type:evidence`
- `area:core`, `area:vault`, `area:generated`, `area:runtime`, `area:privacy`, `area:memory-readiness`, `area:adapters`
- `needs:architect`, `needs:implementer`, `needs:reviewer`, `needs:harvester`
- `risk:low`, `risk:medium`, `risk:high`

Multi-agent rule:

- Architect creates or updates Epics and Decision issues.
- Implementer works only from Ready issues with clear scope, dependencies, branch strategy, and acceptance criteria.
- Reviewer checks against the Epic exit criteria and relevant practices.
- Harvester extracts reusable practices or asset candidates after meaningful work, using the harvest workflow.

For now, create GitHub Project/Epic items only for AF-1 through AF-3 unless a later discussion explicitly opens AF-4 memory-system readiness work. AF-5 implementation issues should remain placeholders until M6 resolves the implementation home.

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

- **Configuration boundary**
  - Separate portable config from machine-local config.
  - Confirm `~/.agent-foundry/config.yaml` remains a locator, not canonical knowledge.
  - Define where enabled runtimes, paths, privacy defaults, and sync remotes live.
  - Define how agents distinguish product project context, Foundry Vault operations, and Foundry Core maintenance before writing.

- **External-user quickstart**
  - Document what a new user clones or installs.
  - Document what remains private.
  - Document how adapters are installed and updated.

Acceptance criteria:

- A new user can create an empty vault conceptually without inheriting personal records.
- Config and local runtime state are not confused with canonical knowledge.
- The setup story does not require knowing the maintainer's machine or personal workflow.

Execution order:

1. Complete Core/Vault split design (#6).
2. Use that boundary to design blank vault initialization (#7) and configuration boundary (#8).
3. Use #6, #7, and #8 together to write the external-user quickstart (#9).
4. Do not claim external-user readiness until AF-3 physically separates the maintainer Vault from public Core.

### M3: Physical Core/Vault Split And Migration

Goal: split the reusable public Core from the maintainer's User Vault without breaking already-installed runtimes or losing reliable vault discovery.

Decision baseline:

- Target direction: public Core plus user-owned Vaults.
- The maintainer's current User Vault belongs to Jinghu and should become private by default.
- Existing single-repo operation is a staging state, not the final multi-user deployment model.
- Physical split should happen after #6, #7, #8, and #9 are reviewed, and before claiming external-user readiness.

Epics:

- **Split execution plan**
  - Choose final repo/directory names for Core and the maintainer Vault.
  - Decide whether the maintainer Vault is a private GitHub repo, private local repo, or another private remote-backed location.
  - Define a reversible migration sequence before moving files.
  - Define rollback points and backups.

- **Maintainer Vault extraction**
  - Move the maintainer's `practices/`, `assets/`, `indexes/`, `usage/usage-aggregate.yaml`, vault-local docs, and reviewed imports into the private Vault.
  - Keep raw local evidence ignored and local.
  - Preserve history where practical, but prioritize correctness and privacy over perfect file history.
  - Confirm no maintainer Vault content remains required by public Core defaults.

- **Public Core cleanup**
  - Keep reusable `workflows/`, `schemas/`, `scripts/`, `templates/`, runtime templates, adapter profiles, adapter quality rules, and product docs in Core.
  - Replace personal defaults with templates, examples, empty indexes, or documented starter packs.
  - Ensure Core does not publish the maintainer's active practices/assets as default product state.

- **Locator and config migration**
  - Update `~/.agent-foundry/config.yaml` semantics so `core_root` and `vault_root` may be different paths.
  - Keep `repo_root` only as a compatibility alias or derived field when appropriate.
  - Ensure agents can locate Core and Vault reliably from another project.
  - Define precedence for `AGENT_FOUNDRY_HOME`, explicit Core/Vault environment variables, local config, and current-directory markers.
  - Add clear failure messages when Core is found but Vault is missing, or Vault is found but Core tooling is missing.
  - Add context checks that identify whether the current operation is product project work, Foundry Vault operation, or Foundry Core maintenance.

- **Runtime deployment migration**
  - Inventory installed Codex, Claude Code, Hermes, and ChatGPT adapter targets before migration.
  - Reinstall managed runtime files from the split Core plus maintainer Vault.
  - Preserve managed-block and managed-directory ownership markers.
  - Do not overwrite unmanaged runtime files.
  - Provide a migration check that reports old path references, stale runtime files, adapter drift, and manual ChatGPT import requirements.

- **Compatibility and validation**
  - Update scripts to accept separate `core_root` and `vault_root`.
  - Update consistency checks to validate the active Vault against Core schemas and workflows.
  - Update adapter publishing so generated outputs can be derived from an arbitrary Vault.
  - Verify blank-vault and maintainer-vault scenarios separately.
  - Verify offline sync and usage aggregate behavior after split.

- **External-user readiness gate**
  - Test a clean setup using public Core plus a blank or new user Vault.
  - Confirm setup does not require maintainer-specific paths, private records, or personal adapters.
  - Confirm a user can choose a suitable Vault location: private Git repo, local-only repo, or other explicitly supported storage.
  - Document where the Vault should live and how agents remember or rediscover it.
  - Test nested usage: running harvest/refresh from inside a product project must locate the correct Core and Vault without confusing the product project with either.

Acceptance criteria:

- Public Core can be cloned without exposing or requiring the maintainer's private Vault.
- The maintainer's Vault is separate and private by default.
- Existing local Codex, Claude Code, Hermes, and ChatGPT workflows have a tested migration path.
- `core_root` and `vault_root` can be different paths and are both validated before canonical writes.
- Product project, Foundry Vault operation, and Foundry Core maintenance contexts are distinguishable before writes or runtime installs.
- A blank Vault can be initialized and checked without personal practices/assets.
- Adapter generation and runtime install work from both the maintainer Vault and a blank/new user Vault.
- Rollback instructions exist for the split migration.
- No future memory-system storage is introduced as part of the split.

### M4: Existing Foundry Lifecycle Completion

Goal: finish the practice/asset/adapter loop before adding memory record types.

Epics:

- **Executable schema validation**
  - Move from human-readable schema guidance toward deterministic validation where useful.
  - Validate required frontmatter, index entries, related IDs, lifecycle states, and file paths.

- **Index and dedupe maturity**
  - Ensure practices and assets can be searched, deduped, reviewed, and routed reliably.
  - Make duplicate/near-duplicate review explicit.

- **Promotion paths**
  - Define and test paths from session evidence to practice candidate, asset candidate, active practice, active asset, adapter, runtime install, usage evidence, and review.
  - Keep human review gates visible.

- **Adapter publishing contract**
  - Define which adapter files are source-maintained versus generated.
  - Keep adapter fidelity executable.
  - Preserve target-specific conventions without duplicating long canonical content.

- **Review operations**
  - Keep `review practices` and `review assets` useful for lifecycle, stale entries, missed activation, and adapter drift.

Acceptance criteria:

- `check_consistency.py`, adapter quality checks, and review scripts cover the lifecycle claims they make.
- Candidate/proposed entries do not publish into default adapters.
- Active entries have either Activation guidance or explicit asset coverage/reference-only intent.

### M5: Memory-System Readiness Design

Goal: define memory as an adjacent future capability without implementing storage yet.

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

### M6: Fork vs Extension Decision

Goal: decide the implementation home for memory-system work using evidence from M1 through M5.

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

### M7: Capability Pack Discovery and Lifecycle

Goal: define whether Agent Foundry can recognize, maintain, and export higher-level capability packs that emerge from repeated work.

This is intentionally later than repository hygiene, productization, physical split migration, lifecycle completion, memory readiness, and the fork-vs-extension decision. Do not use this milestone to delay AF-1 through AF-6.

Capability packs are not the same as individual assets. A future capability pack may bundle practices, assets, workflows, templates, adapter snippets, examples, configuration profiles, dependency metadata, and export/install behavior around a recurring user goal such as multi-agent collaboration or technical documentation writing.

Epics:

- **Capability candidate detection**
  - Define when repeated practice/asset/workflow co-activation suggests an emergent capability.
  - Let agents propose capability candidates during harvest, asset discovery, or lifecycle review.
  - Avoid requiring humans to predefine all future capability categories.

- **Capability pack schema**
  - Define relationships among practices, assets, workflows, templates, adapters, examples, dependencies, versions, and target runtimes.
  - Keep the schema separate from current asset records unless review proves they should converge.

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

## Work Not To Do Yet

- Do not create `memory/`, `knowledge/`, `research_memos/`, or `project_memory` directories.
- Do not implement automatic memory writing.
- Do not add semantic/vector/graph indexes.
- Do not add MCP write tools.
- Do not import raw ChatGPT exports.
- Do not implement capability pack discovery, packaging, export, or install before the earlier repository, lifecycle, and memory-readiness decisions are stable.
- Do not refactor adapters or runtime install behavior until repository hygiene policy exists.

## Immediate Next Planning Tasks

1. Create a repository layer inventory.
2. Draft repository hygiene and generated artifact policy.
3. Draft extension policy for optional subsystems.
4. Create the lightweight GitHub Project and initial AF-1/AF-2 Epics after review.
5. Revisit fork vs extension only after M1 and M2 are clear.
