# Local Collaboration System Design

Status: design discussion draft  
Scope: local-first collaboration state, GitHub compatibility, sync/conflict model, and Agent Foundry boundary analysis.  
Non-scope: milestone planning, implementation issue breakdown, final schema, runtime mutation, GitHub migration.

## Problem

Agent Foundry's current multi-agent collaboration workflow uses GitHub issues,
pull requests, labels, comments, and optional Project fields as the durable
coordination substrate.

That works for public audit and team visibility, but recent AF7-AF12 execution
shows a large amount of time and token budget spent on:

- repeated issue, PR, comment, label, and Project rehydration;
- GitHub API retries and transport failures;
- Project field drift and state repair;
- duplicated role handoff summaries;
- repeated confirmation that low-risk transitions are not human gates;
- final-state readbacks after every merge, close, or dispatch.

The goal is not to remove GitHub. The goal is to stop using GitHub as the only
low-level runtime database for agent coordination.

## Working Name

Use two names:

- User-facing name: **Foundry Board**.
- Technical name: **Local Collaboration Ledger**.

`Foundry Board` is concise and understandable to users. It suggests a local
work board for agent collaboration without exposing implementation details.

`Local Collaboration Ledger` names the technical substrate: append-only events,
state reduction, sync mappings, review gates, and audit history.

Avoid naming it `memory`, `project`, or `capability pack`:

- It is not the memory system. It tracks collaboration state, not general
  knowledge.
- It is not GitHub Project. It may mirror to GitHub Project, but it is a
  different domain model.
- It is not a capability pack. It may be distributed or enhanced by capability
  packs, but the coordination substrate itself is Core infrastructure.

## What Local-First Means Here

For this design, local-first means:

1. Agents can read and update collaboration state without waiting for GitHub.
2. Local state is inspectable, portable, and recoverable from files.
3. Sync to GitHub or another remote is an adapter operation, not the core
   execution path.
4. Human gates, review gates, merge gates, privacy boundaries, and closure
   authority remain explicit and auditable.
5. Remote collaboration remains possible, but remote state is not required for
   every low-level transition.

This follows the practical local-first model: local reads/writes first, remote
sync in the background or as an explicit action. It does not require fully
decentralized peer-to-peer CRDT collaboration in the first version.

## Relationship To Agent Foundry

Agent Foundry Core is the public source of truth for reusable workflows,
schemas, scripts, templates, adapters, and validation tooling.

The Local Collaboration System should therefore split into three layers:

| Layer | Owns | Should live in |
| --- | --- | --- |
| Core implementation | Schemas, reducers, validators, CLI helpers, Skill-facing workflow docs, GitHub sync adapter code. | Agent Foundry Core |
| Project collaboration state | Epics, work items, role routing, local event log, local board state, sync cursors, remote mappings. | Project-local `.agent-foundry/board/` or selected Vault project state |
| User capability governance | Reusable practices/assets/packs that teach agents how to use the board safely. | selected User Vault and Core official packs |

Core should not contain live project coordination state. Core should only ship
the system that can create, validate, inspect, and sync that state.

## Relationship To User Vault

The selected User Vault remains canonical for practices, assets, capability
pack deployment state, and approved reusable capability records.

Foundry Board state is different:

- It is operational workflow state.
- It may include issue titles, branch names, role assignment, verification
  results, and human gate summaries.
- It may be project-specific or private.
- It should not automatically become a practice, asset, memory record, or
  capability pack record.

Recommended rule:

- Project-specific board state belongs in the project workspace when the project
  owns the work.
- Cross-project reusable collaboration practices belong in the selected User
  Vault only after harvest/review.
- Board telemetry can be evidence for future practice harvest, but not authority
  by itself.

## Relationship To Capability Packs

Capability packs are governed capability bundles. Foundry Board is coordination
infrastructure. It should therefore not be published as an ordinary optional
capability pack.

If Foundry Board is split into a separate user-visible pack such as
`pack.local-board.optional`, the user experience becomes fragmented:

- users must understand whether to install the board pack before the
  multi-agent pack;
- update, disable, and compatibility guidance must explain cross-pack lifecycle
  dependencies;
- `pack.multi-agent.optional` loses the clear product meaning it just gained in
  AF12;
- GitHub bridge, role workflow, local board, and dispatch habits become separate
  choices even though users experience them as one collaboration mode.

The better model is layered:

| Layer | User-facing lifecycle | Implementation rule |
| --- | --- | --- |
| Foundry Board engine | Not a separate pack. Available as Core infrastructure. | Core ships schemas, reducers, validators, local board helpers, and sync adapters. |
| `pack.bootstrap.minimal` | Mandatory/baseline starter. | May describe source-of-truth and status boundaries, but should not own multi-agent collaboration behavior. |
| `pack.multi-agent.optional` | The user-visible optional multi-agent collaboration capability. | Evolves to become Foundry Board-aware when the board exists, while preserving GitHub issue/PR collaboration habits. |
| Project board state | Not a pack artifact. | Lives in project-local or selected-Vault project state; never in public Core catalog payloads. |

This means `pack.multi-agent.optional` should absorb the user-facing behavior:

- role routing and handoff habits;
- Human Decision Contracts;
- reviewer and Architect gate semantics;
- compact rehydration packet usage;
- GitHub bridge usage when configured;
- Foundry Board status and sync commands when available.

The pack should not own or copy live board state. Capability pack lifecycle rules
still apply. Board events do not activate, export, publish, or deploy packs.
Board state may record pack-related work, but it must preserve Core, selected
Vault, Generated, Runtime, and Local Private boundaries.

This keeps capability governance above the board, while avoiding a confusing
multi-pack lifecycle for one collaboration experience.

## Should Local Be Authoritative?

There are three possible authority modes.

| Mode | Meaning | Benefits | Risks |
| --- | --- | --- | --- |
| GitHub-authoritative with local cache | GitHub remains source of truth; local only accelerates reads. | Easiest migration; low trust shift. | Does not solve repeated GitHub mutation/readback cost. |
| Local-authoritative with GitHub mirror | Foundry Board owns workflow state; GitHub mirrors selected public/team state. | Largest token/time savings; best local-first fit. | Requires sync and conflict model. |
| Hybrid authority by namespace | Local owns routing/ledger; GitHub owns PR code review and public issue visibility. | Practical; minimizes reinvention. | Requires clear namespace boundaries. |

Recommended target: **hybrid authority by namespace**, with local authority for
collaboration workflow state once the model is stable.

Do not start with "local owns everything." GitHub should remain authoritative
for:

- pull request diff and merge state;
- remote branch state;
- public issue or PR conversation when multiple humans rely on it;
- final `main` integration evidence when the repository uses GitHub as release
  record.

Foundry Board should become authoritative for collaboration workflow state:

- role routing;
- dependency gates;
- current owner and next owner;
- compact rehydration packets;
- workflow telemetry;
- local status dashboard;
- no-write review packets;
- human gate inventory;
- GitHub sync intent and conflict review.

This gives most of the token/time savings without pretending that local state
can replace GitHub's code-hosting and PR semantics immediately.

Avoid the vague goal "local authoritative for everything." The precise goal is:

> Foundry Board owns operational collaboration state; GitHub owns remote code
> review and public collaboration state; the selected User Vault owns durable
> reusable capability state.

## Sync And Conflict Concerns

The concern about not rebuilding a complex sync engine is valid. This system
should avoid custom real-time multi-writer sync in the first version.

The safe design is:

1. Use deterministic local data structures.
2. Use append-only events for audit.
3. Use explicit sync transactions for GitHub import/export.
4. Treat conflicts as review packets, not automatic merges.
5. Delay hot multi-user sync until the domain model proves stable.

That means the first target is not CRDT multiplayer editing. It is reliable
local scheduling plus cold or warm GitHub sync.

## Existing Framework And Module Options

### SQLite Plus Append-Only Event Log

Fit: strong.

Use SQLite for queryable board state and a JSONL event log for audit. The event
log is human-readable, portable, and git-friendly enough for review. SQLite is
fast, local, simple to ship with Python, and already fits AF's script-first
tooling.

Conflict handling can be domain-specific and explicit:

- same item updated locally and remotely becomes `sync_conflict`;
- agent/human chooses resolution;
- resolution writes a new event;
- no silent overwrite.

This does not solve hot collaboration by itself, but it solves the current
highest-cost problem: repeated GitHub reads and fragile Project state repair.

### Git-Backed Local Task Tracker

Fit: medium to strong as inspiration.

Tools such as `git-task` show that local-first issue/task tracking stored inside
a git repository can sync with GitHub, GitLab, Jira, and Redmine. This is close
to AF's desired shape.

However, AF needs domain-specific state that generic trackers do not model:

- role routing and owner role;
- Human Decision Contracts;
- Execution Contracts;
- permission gates;
- capability pack boundaries;
- Core/Vault/Generated/Runtime/Local Private namespaces;
- compact rehydration and workflow telemetry.

So a generic task tracker may inspire storage and sync, but AF likely needs its
own domain model.

### Replicache / Zero

Fit: weak for current AF, strong if AF later has a web app.

Replicache and Zero are built for instant web UI and background sync. Their
model is useful conceptually: local writes, background push/pull, server
canonical convergence, and mutators. But they are JavaScript/web oriented and
need backend sync endpoints. Replicache is also in maintenance mode.

Good idea to borrow:

- mutation functions as explicit domain transitions;
- local optimistic state plus background sync;
- rebase/replay pending local changes after remote update.

Not recommended as the first substrate for a Python/CLI/repo-local AF board.

### PowerSync / ElectricSQL

Fit: weak to medium for current AF.

These solve Postgres-to-local database sync and are strong for app products
with a central backend. They avoid a lot of API glue and provide local SQLite
or local query behavior.

But AF does not currently have, or want, a central Postgres authority for
personal local workflows. Adding one would increase operational complexity.

Good future fit if Agent Foundry becomes a hosted/team product. Not the right
starting point for repo-local agent collaboration.

### Triplit / Jazz

Fit: weak to medium.

These provide higher-level local-first databases, sync, schemas, permissions,
and real-time collaboration. They are attractive if AF builds an interactive
desktop or web UI.

Current risks:

- primarily TypeScript/web ecosystem;
- extra runtime and dependency surface;
- permission model may be heavier than AF needs;
- not aligned with current Python CLI and file-backed Core/Vault model.

Worth revisiting for a future visual Foundry Board UI. Not recommended as the
first backend.

### Automerge / Yjs / CRDT Libraries

Fit: weak for the first version, medium for later hot sync.

CRDTs are powerful when multiple users edit the same document or structured
state concurrently. AF's collaboration state is more like a workflow ledger than
a shared text document.

For AF, many conflicts should not merge automatically. If one actor says an
issue is ready for human closure and another says it needs implementation, the
correct result is not a CRDT merge; it is a visible decision conflict.

Use CRDTs later only if the product needs real-time multi-user editing of board
views or notes.

### Temporal / LangGraph

Fit: strong as optional orchestration runner, weak as the board source of truth.

Temporal's deterministic workflow plus non-deterministic activities model is a
good architecture lesson. LangGraph's persistence, checkpointing,
human-in-the-loop interrupts, subgraphs, and durable execution model are
especially relevant for Coordinator automation.

If AF weakens the tool-agnostic requirement, a LangGraph-style orchestration
engine could add real capabilities:

- model Coordinator flows as explicit graphs instead of long prompt discipline;
- persist graph state across interruptions and retries;
- pause at Human Decision Contracts with a first-class interrupt and resume
  after approval;
- isolate Architect, Implementer, Reviewer, and utility actions as nodes or
  subgraphs;
- keep lower-capability models inside bounded nodes with explicit acceptance
  checks;
- record traces for workflow debugging and cost analysis;
- support time-travel or fork-style investigation of alternative routing paths.

The cost is also material:

- tool-agnostic portability drops, especially for Claude Code, Trae, and other
  systems that cannot be directly controlled as LangGraph workers;
- graph checkpoint state can become a second opaque source of truth unless every
  meaningful transition is also written to Foundry Board;
- runtime dependencies, versioning, deployment, and debugging get heavier;
- LangGraph memory/store concepts must not be confused with AF canonical
  practices, assets, capability packs, or future memory-system records.

Recommended positioning:

```text
Foundry Board = domain state, audit ledger, readable source of truth
LangGraph = optional Coordinator orchestration runner
GitHub = optional remote collaboration and public audit adapter
```

Do not make LangGraph the source of truth. Use it only if each meaningful node
transition writes a Foundry Board event and can be replayed or explained from
board state. The first likely LangGraph pilot should be Coordinator workflow,
not full replacement of Architect, Implementer, and Reviewer sessions.

### Codex SDK And Codex MCP Server

Fit: strong candidate for Codex-native orchestration, not a cross-tool
orchestration standard.

Codex SDK and Codex MCP server are different from LangGraph:

- Codex SDK controls local Codex threads programmatically.
- Codex MCP server exposes Codex as tools that an MCP client or Agents SDK can
  call.
- They orchestrate Codex, not arbitrary agent systems.

Potential value for AF:

- create or resume Codex role sessions from a local Coordinator;
- specify model and sandbox per thread or turn where supported;
- run local Codex workflows in CI or trusted automation;
- preserve thread ids as Foundry Board evidence refs;
- combine with Agents SDK or another runner to dispatch bounded Codex work.

Risks:

- Codex-specific orchestration lowers tool-agnostic portability;
- non-Codex agents still need adapters or manual/remote handoff;
- local Codex app-server, CLI runtime, auth, sandbox, and model availability
  become operational dependencies;
- SDK/MCP state must not replace Foundry Board events.

Recommended positioning:

```text
Foundry Board = tool-agnostic collaboration state
Codex SDK/MCP = optional Codex execution adapter
LangGraph/Agents SDK = optional orchestration runtime above execution adapters
```

This keeps the AF domain model independent while allowing Codex to be the first
high-quality automation target.

Current evaluation, 2026-06-26:

- Local Codex CLI is available as `codex-cli 0.133.0`.
- `codex mcp-server --help` is available and exposes a stdio MCP server entry.
- Official docs describe MCP tools `codex` and `codex-reply`, including
  `threadId`, `cwd`, `model`, `sandbox`, `approval-policy`, profile, config,
  and base-instructions controls.
- Official docs describe TypeScript SDK package `@openai/codex-sdk`; npm
  reports latest `0.142.2` and alpha `0.143.0-alpha.25`.
- Official docs describe Python package `openai-codex`, but this local
  environment does not currently have `openai_codex` importable, and `pip index
  versions openai-codex` did not find a matching distribution through the
  configured Python package index.

AF fit assessment:

| Surface | Strength | Weakness | Recommended use |
| --- | --- | --- | --- |
| Codex MCP server | Standard MCP boundary, works with Agents SDK or any MCP client, can expose `codex` and `codex-reply` as tools. | Requires long-running local CLI process and MCP client; Codex-specific. | Best first experiment for Coordinator dispatch and external orchestration. |
| TypeScript Codex SDK | Programmatic thread start/resume and server-side integration; published npm package is visible. | Adds Node dependency and still controls Codex-specific runtime. | Good if Foundry Board runner becomes TypeScript or needs richer SDK behavior. |
| Python Codex SDK | Best ecosystem fit for AF's Python scripts if package availability stabilizes. | Not currently importable here; package availability needs re-check before relying on it. | Defer as implementation substrate until install path is verified. |
| Direct Codex CLI non-interactive mode | Lowest dependency and easiest to shell out. | Weaker thread/session orchestration; harder to manage durable role sessions. | Useful fallback, not the preferred orchestration layer. |

Recommended first automation experiment:

1. Keep Foundry Board as source of truth.
2. Use Codex MCP server as the first execution adapter.
3. Build a tiny Coordinator proof of concept that:
   - reads one Foundry Board task;
   - starts a Codex thread through MCP with explicit `cwd`, `model`, sandbox,
     and approval policy;
   - records returned `threadId` as a board event;
   - continues the same thread with `codex-reply`;
   - writes no GitHub or Vault state unless the board transition allows it.
4. Treat LangGraph or Agents SDK as optional runners above the MCP adapter, not
   as the board state model.

## Recommended Technical Direction

Use a small, AF-owned domain model backed by boring local primitives:

```text
project workspace or selected Vault project state
  .agent-foundry/board/
    events.jsonl
    state.sqlite
    items/
      AF12-255.yaml
      AF12-227.yaml
    sync/
      github-mapping.yaml
      cursors.yaml
      conflicts/
    evidence/
      verification-*.yaml
```

Core provides:

```text
schemas/collaboration-*.schema.yaml
scripts/foundry_board.py
scripts/github_board_sync.py
scripts/codex_board_runner.py
workflows/manage-local-collaboration.md
adapters/... Skill-facing instructions
```

The local event log should record semantic transitions, not raw chat:

- `work_item_created`
- `dependency_satisfied`
- `role_routed`
- `handoff_posted`
- `review_accepted`
- `review_requested_changes`
- `human_gate_opened`
- `human_gate_approved`
- `pr_merged`
- `issue_closed`
- `sync_conflict_detected`
- `state_repaired`

Every event should include:

- stable id;
- actor;
- role;
- timestamp;
- subject item;
- previous state hash;
- resulting state hash or expected reducer version;
- evidence refs;
- writes performed;
- forbidden actions preserved;
- optional GitHub mapping.

## User Experience Shape

The user should not think in scripts.

Skill-facing commands:

- `show Foundry Board status`
- `show pending human gates`
- `dispatch next role work`
- `prepare compact handoff`
- `sync Foundry Board with GitHub`
- `preview GitHub sync`
- `explain board conflict`
- `repair board state from GitHub`

If `pack.multi-agent.optional` is installed, these commands become part of the
multi-agent collaboration experience rather than a separate board lifecycle.
Users choose "multi-agent collaboration", not "board internals".

Default output should be compact:

```text
Foundry Board
Epic: AF12 closed
Mode: local-primary, GitHub mirror current
Ready: none
Blocked: none
Human gates: none
Last sync: GitHub PR #262 merged, #255/#226/#227 closed
Next safe action: none
Writes: none
```

Conflict output should be explicit:

```text
Conflict: #255 routing
Local: completed after PR #262 merge
GitHub: still has needs:human
Recommended action: remove stale needs:human after verifying merge commit
Writes: none until accepted
```

## Authority Namespace

The most important design rule is not storage choice. It is authority namespace.

| Namespace | Authority |
| --- | --- |
| Code diff and mergeability | GitHub PR plus local git |
| Role routing and handoff queue | Foundry Board, mirrored to GitHub when enabled |
| Human Decision Contract inventory | Foundry Board, with GitHub/public mirror when needed |
| Public collaboration record | GitHub issues/PRs |
| Capability pack lifecycle | selected User Vault after deployment, Core catalog for official discoverability |
| Runtime install state | Runtime receipts and local manifests |
| Generated adapter output | Generated output root |
| Private evidence | Local Private or selected Vault private records |

This lets AF optimize the high-churn coordination path without weakening the
trust model for code, public collaboration, or capability governance.

## Open Design Questions

1. Should project-local board state live by default in the project repo
   `.agent-foundry/board/`, or under selected Vault `projects/<project-id>/`?
2. Should `events.jsonl` be checked into project git by default, or kept local
   and exported only as sanitized summaries?
3. What is the minimum GitHub mirror set: issue comments only, labels only,
   PR comments only, or full issue/Project sync?
4. Which transitions require full rehydration even with Foundry Board available?
5. How should a human inspect and edit the board manually without corrupting
   reducer invariants?
6. Should a future visual board be terminal-first, static HTML, TUI, or web UI?

## Current Recommendation

Do not start by solving general multi-user sync.

Start by defining Foundry Board as a local-first collaboration substrate with:

- local deterministic event log;
- local materialized state;
- compact rehydration packet generation;
- explicit GitHub import/export preview;
- conflict packets instead of automatic conflict resolution;
- Skill-facing user commands;
- capability-pack boundary awareness.

This creates a high-value local authoritative path for coordination while
leaving GitHub authoritative for PR merge state and public team collaboration.

This should ship as Core infrastructure and be exposed to users through the
existing multi-agent collaboration capability. The system can later grow into
warm or hot sync, but only after the authority namespace and event model are
stable.

Near-term research should evaluate Codex SDK and Codex MCP server as the first
execution adapter for automated Coordinator dispatch. LangGraph should remain a
separate optional orchestration-engine investigation rather than the initial
board substrate.

## Research Anchors

- Local-first principles: https://www.inkandswitch.com/essay/local-first/
- Local-first limitations: https://rxdb.info/articles/local-first-future.html
- Automerge CRDT sync: https://automerge.org/
- Replicache sync model: https://replicache.dev/ and https://doc.replicache.dev/concepts/how-it-works
- PowerSync local SQLite sync: https://powersync.com/ and https://docs.powersync.com/resources/local-first-software
- ElectricSQL Postgres sync: https://electric.ax/sync/
- Triplit local-first database: https://github.com/aspen-cloud/triplit
- Git-backed local issue tracking: https://github.com/jhspetersson/git-task
- LangGraph persistence and HITL: https://docs.langchain.com/oss/python/langgraph/persistence and https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- Temporal durable workflow model: https://temporal.io/blog/of-course-you-can-build-dynamic-ai-agents-with-temporal
- Codex SDK: https://developers.openai.com/codex/sdk
- Codex MCP with Agents SDK: https://developers.openai.com/codex/guides/agents-sdk
