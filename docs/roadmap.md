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
| AF-3 | External-User Ready | A new user can initialize and operate a clean vault without inheriting personal records. | Blank vault initialization, user-local config, examples/templates, and setup docs are usable. |
| AF-4 | Memory-System Ready | Future memory-system records, evidence policy, routing, privacy, and MCP boundaries are designed but not necessarily implemented. | Memory-system implementation home can be chosen with clear tradeoffs. |
| AF-5 | Memory-System Implementation | A reviewed memory/knowledge system is implemented according to the chosen architecture. | MVP validates the main memory lifecycle without bypassing Agent Foundry governance. |

Current planning stage: AF-1.

AF-0 explains the existing mixed history. AF-1 starts the stricter planning and multi-agent coordination era. AF-2 and AF-3 are prerequisites for broad reuse. AF-4 is the decision gate for memory-system architecture. AF-5 is intentionally future work.

## Release Version Mapping

Do not force semantic versioning to carry all planning meaning yet. Use AF stages for maturity and reserve release versions for distribution points.

Suggested mapping:

| Stage Complete | Candidate Release Meaning |
| --- | --- |
| AF-1 | `v0.1.0`: governed personal foundry baseline. |
| AF-2 | `v0.2.0`: productizable architecture and repo hygiene baseline. |
| AF-3 | `v0.3.0`: external-user-ready vault/core setup. |
| AF-4 | `v0.4.0`: memory-system-ready design baseline. |
| AF-5 MVP | `v0.5.0` or later: memory-system MVP, not automatically `v1.0`. |

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

For now, create GitHub Project/Epic items only for AF-1 and AF-2 unless a later discussion explicitly opens AF-4 memory-system readiness work. AF-5 implementation issues should remain placeholders until M5 resolves the implementation home.

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

- **Local/private data policy**
  - Extend the raw-local vs shared-aggregate rule beyond usage evidence.
  - Decide what happens to raw ChatGPT exports, transcripts, sensitive notes, and machine paths.
  - Add or update `.gitignore` only after policy review.

- **Example vs user content separation**
  - Decide how examples/templates should differ from the user's personal vault.
  - Identify any current content that would block external-user reuse.

Acceptance criteria:

- A repository hygiene policy exists.
- Every top-level directory has an assigned layer.
- Generated and local-private files have explicit Git behavior.
- External users can tell what is product core versus the user's vault content.

### M2: Productization and Vault Separation

Goal: make Agent Foundry usable as a reusable system rather than only this personal repository.

Epics:

- **Core/Vault split design**
  - Define Core responsibilities.
  - Define User Vault responsibilities.
  - Decide whether Core and Vault remain in one repo for now or become separately installable later.

- **Blank vault initialization**
  - Design `init-vault` semantics before implementation.
  - Define starter indexes, practice/asset templates, runtime templates, and empty usage aggregate.
  - Ensure no personal content is required for a new user.

- **Configuration boundary**
  - Separate portable config from machine-local config.
  - Confirm `~/.agent-foundry/config.yaml` remains a locator, not canonical knowledge.
  - Define where enabled runtimes, paths, privacy defaults, and sync remotes live.

- **External-user quickstart**
  - Document what a new user clones or installs.
  - Document what remains private.
  - Document how adapters are installed and updated.

Acceptance criteria:

- A new user can create an empty vault conceptually without inheriting personal records.
- Config and local runtime state are not confused with canonical knowledge.
- The setup story does not require knowing the maintainer's machine or personal workflow.

### M3: Existing Foundry Lifecycle Completion

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

### M4: Memory-System Readiness Design

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

### M5: Fork vs Extension Decision

Goal: decide the implementation home for memory-system work using evidence from M1 through M4.

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

## Work Not To Do Yet

- Do not create `memory/`, `knowledge/`, `research_memos/`, or `project_memory` directories.
- Do not implement automatic memory writing.
- Do not add semantic/vector/graph indexes.
- Do not add MCP write tools.
- Do not import raw ChatGPT exports.
- Do not refactor adapters or runtime install behavior until repository hygiene policy exists.

## Immediate Next Planning Tasks

1. Create a repository layer inventory.
2. Draft repository hygiene and generated artifact policy.
3. Draft extension policy for optional subsystems.
4. Create the lightweight GitHub Project and initial AF-1/AF-2 Epics after review.
5. Revisit fork vs extension only after M1 and M2 are clear.
