# Multi-Agent Collaboration Workflow / 多 Agent 协作开发流程

This document describes Agent Foundry's role-based issue and PR workflow. It is
an operating guide for humans and agents. Helper commands, schemas, and
template details remain in `workflows/github-collaboration-helper.md` and
`templates/`.

本文描述 Agent Foundry 的 role-based issue / PR 工作流。它是给人和 agent
使用的操作指南。Helper commands、schemas 和 template 细节仍以
`workflows/github-collaboration-helper.md` 和 `templates/` 为准。

## Purpose / 目的

Multi-agent collaboration separates different kinds of work so each decision is
made by the right role. A good workflow keeps status visible, ownership clear,
handoffs durable, and human attention focused on real judgment.

多 Agent 协作把不同性质的工作分开，让每类决定由合适的 role 处理。好的流程让
状态可见、owner 清楚、handoff 可追溯，并把人的注意力留给真正需要判断的地方。

Durable state comes from GitHub issues, PRs, comments, labels, exact heads,
Execution Contracts, optional Testing Contracts, and closure evidence. Project
fields are visual mirrors and scheduler metadata; they do not outrank issue/PR
durable state.

Durable state 来自 GitHub issues、PRs、comments、labels、exact heads、
Execution Contracts、可选 Testing Contracts 和 closure evidence。Project
fields 是 visual mirrors 和 scheduler metadata，不能高于 issue/PR durable
state。

## Collaboration Readiness / 协作就绪检查

Before a repo adopts this workflow, or when an existing project shows routing
drift, run a collaboration readiness audit. The goal is to answer what is ready,
what is missing, what is inconsistent, and what the next safe action is.

在 repo 采用这套流程前，或已有项目出现 routing drift 时，先做 collaboration
readiness audit。它要回答：什么已经 ready、缺什么、哪里不一致、下一步安全动作是
什么。

The audit should be read-only. It may inspect labels, role routing templates,
Execution Contract values, Testing Contract values, issue and PR routing state,
Project/Kanban visibility, and handoff evidence. Its report should state
`mutation_performed: false`.

Audit 应保持 read-only。它可以检查 labels、role routing templates、Execution
Contract values、Testing Contract values、issue/PR routing state、Project/Kanban
visibility 和 handoff evidence。报告必须说明 `mutation_performed: false`。

Use a low-cost GitHub strategy:

- prefer REST for labels, issues, PRs, comments, and exact heads;
- query Project v2 with targeted GraphQL only when configured and needed;
- avoid default full Project scans;
- use bounded retry for transient TLS, EOF, timeout, or rate-limit-like errors;
- return partial or degraded reports instead of blocking unrelated progress;
- record `unknown` or `not_available` instead of inferring hidden state.

Dry-run repair plans can name possible fixes, such as adding a missing
`needs:*` label, fixing a malformed contract field, or setting a Project mirror
field. They do not apply those fixes. Real repair/apply needs a later explicit
gate.

Dry-run repair plan 可以列出可能修复项，例如添加缺失的 `needs:*` label、修正
malformed contract field，或设置 Project mirror field。它不执行这些修复。真正
repair/apply 需要后续明确 gate。

The report shape should be stable enough for future local-first orchestration
and Foundry Board backfill. GitHub Project remains a sync or visibility surface;
it does not become the authority.

报告结构应足够稳定，以便未来 local-first orchestration 和 Foundry Board backfill
复用。GitHub Project 仍是 sync 或 visibility surface，不是 authority。

## Roles / 角色

| Role | Triggered by | Main output | Hands off to | Boundary |
| --- | --- | --- | --- | --- |
| Coordinator | A queue, Epic, dependency, stale state, or cross-thread handoff needs synchronization. | Routing comment, dependency decision, label/Project coherence, callback. | Architect, Implementer, Reviewer, Tester, Harvester, or Human. | Does not own product acceptance or create hidden `needs:coordinator` authority. |
| Architect | Scope, architecture, taxonomy, privacy, gate, release order, or acceptance decision is needed. | Decision, Execution Contract, Human Decision Contract, downstream release, acceptance/hold. | Implementer, Tester, Reviewer, Human, or next Architect issue. | Does not implement broad changes inside design gates or bypass review. |
| Implementer | A scoped task has accepted design, allowed files, branch strategy, and verification expectations. | Code/docs/tests, PR, implementation handoff, verification evidence. | Tester or Reviewer, usually through PR and issue comments. | Does not self-accept, redefine scope, or make new product authority. |
| Tester | The issue needs explicit test planning, evidence execution, matrix coverage, or objective evidence before review/trial. | Test plan, matrix, executed evidence, gaps, residual risks. | Reviewer, Implementer, Architect, or Human. | Does not approve, reject, merge, close, or replace Reviewer/Architect/Human. |
| Reviewer | A PR, issue evidence packet, readiness gate, or Tester evidence needs independent review. | Findings-first review, acceptance or requested changes, verification basis. | Architect or Implementer. | Does not own product direction or final acceptance. |
| Human | Product direction, subjective trial, final integration, Epic/stage closure, privacy/security, destructive, or high-risk decision is required. | Approval, rejection, revision, or trial result. | Coordinator or Architect. | Should not be asked to approve routine low-risk mechanics. |
| Harvester | Real work should be converted into reusable practices, assets, or candidate capability material. | Evidence inventory, candidate packet, reuse recommendation. | Reviewer or Architect. | Does not activate/publish without review and approval. |

## Standard Flow / 标准流程

| Step | Owner | What happens | Exit signal |
| --- | --- | --- | --- |
| 1. Intake | Coordinator | Rehydrate durable state, check dependencies, choose the next owner. | Issue has one clear next `needs:*` label or a recorded hold. |
| 2. Design / Contract | Architect | Define scope, risk, allowed actions, forbidden actions, branch target, acceptance criteria, and whether Tester is needed. | Execution Contract is durable; next owner is released. |
| 3. Implementation or Evidence | Implementer, Tester, or Harvester | Produce the scoped change or evidence packet. | Handoff names scope, verification, residual risks, and next owner. |
| 4. Review | Reviewer | Review exact issue evidence or exact PR head. Findings lead; acceptance is not final closure. | Accepted, requested changes, or blocked with reasons. |
| 5. Acceptance / Routing | Architect | Decide whether review evidence satisfies the contract and route merge, closure, human gate, or next issue. | Durable acceptance, hold, HDC, merge decision, or release decision. |
| 6. Human Gate | Human, when required | Approve or revise the concrete decision under review. | Explicit approval phrase or revised direction. |
| 7. Completion | Authorized role | Verify post-merge or post-action state, close delegated child issues, clean stale labels, release next dependency. | Completion comment, final state, residual risks. |

Low-risk work may stay in one thread if the role stance remains clear. Separate
role handoffs are useful when independent review, product judgment, testing
evidence, or durable scheduling outweighs coordination cost.

低风险工作可以留在一个 thread 中完成，前提是 role stance 清楚。需要独立 review、
产品判断、测试证据或 durable scheduling 时，分 role handoff 才值得付出协作成本。

## Role Rules / 角色规则

### Coordinator

Coordinator protects workflow continuity. It reads durable state, detects
dependency order, repairs mechanical routing drift, and records callbacks.
Coordinator may dispatch work, but it should not turn itself into a hidden
authority role.

Coordinator 维护流程连续性。它读取 durable state，判断 dependency order，修复机械
routing drift，并记录 callback。Coordinator 可以 dispatch work，但不能变成隐藏的
authority role。

Use Coordinator for queue management, stale labels, Project/label mismatch,
cross-thread handoff, Epic sequencing, callback consolidation, and status
readback.

### Architect

Architect protects the shape of the work. It decides what problem is being
solved, what is out of scope, which role owns the next step, and which gates
must remain human-owned.

Architect 保护工作的形状。它决定要解决什么问题、什么不在范围内、下一步由哪个 role
负责，以及哪些 gate 必须由 human 决定。

Use Architect for design, taxonomy, privacy/security boundaries, issue
decomposition, branch/integration strategy, acceptance after review, and Human
Decision Contracts.

### Implementer

Implementer changes the repository under an accepted contract. It should keep
the diff focused, write or update required tests, avoid unrelated cleanup, and
handoff with exact verification.

Implementer 在 accepted contract 下修改 repo。它应保持 diff 聚焦，编写或更新要求的
tests，避免无关 cleanup，并用准确 verification 交接。

Use Implementer only after the issue names allowed scope, dependencies, branch
target, acceptance criteria, and required evidence. If scope changes while
implementing, route back to Architect instead of expanding silently.

### Tester

Tester protects confidence in behavior. It designs or executes evidence when
ordinary implementation tests are not enough to explain risk.

Tester 保护对行为的信心。当普通实现测试不足以说明风险时，Tester 负责设计或执行
evidence。

Use Tester for user-visible state, browser flows, route-mocked versus
real-backend behavior, runtime/Generated/Vault/Local Private boundaries,
external import, capability-pack behavior, scheduler transitions, negative or
adversarial cases, rollback, leak checks, and human-trial preparation.

Skip Tester when a small docs check, static check, unit test, or Reviewer
read-through already answers the confidence question.

Tester output routes to Reviewer when evidence is ready, to Implementer when
defects or missing tests are found, to Architect when criteria are unclear, and
to Human when objective evidence is ready but subjective acceptance remains.

### Reviewer

Reviewer protects independent judgment. It checks the issue contract, exact PR
head, diff, tests, risk, and user-visible behavior. Findings come first; a
short acceptance is enough only when no meaningful risks remain.

Reviewer 保护独立判断。它检查 issue contract、exact PR head、diff、tests、risk 和
user-visible behavior。Findings 优先；只有没有实质风险时，简短 acceptance 才足够。

Reviewer acceptance routes to Architect for acceptance/routing unless the issue
contract explicitly defines another next owner.

### Human

Human handles product direction and meaningful approval. A good human gate names
the concrete decision, evidence, allowed actions, still-forbidden actions,
consequences, and exact approval phrase.

Human 处理产品方向和真正有意义的 approval。好的 human gate 会说明具体 decision、
evidence、approval 后允许的动作、仍然禁止的动作、后果，以及 exact approval
phrase。

Use Human gates for final `main` integration when not delegated, Epic/stage
closure, product/distribution choices, subjective trial acceptance,
privacy/security boundaries, destructive operations, data migration, direct
runtime/private/generated mutation, and unclear user-specific choices.

### Harvester

Harvester converts real work into candidate reusable value. It can inventory
lessons, patterns, and artifacts, but canonical practice/asset activation still
requires review and approval.

Harvester 把真实工作转成 candidate reusable value。它可以 inventory lessons、
patterns 和 artifacts，但 canonical practice/asset activation 仍需要 review 和
approval。

## Contracts / 合约

### Execution Contract

Every implementation or evidence issue should make ownership machine-readable:

```markdown
## Execution Contract

Owner role: implementer
Review role: reviewer
Acceptance role: architect
Completion handoff: to:reviewer
Branch target: main | <integration-branch>
Merge rule: human-gated | delegated-child | delegated-main
Forbidden actions:
  - live Vault/private/runtime/generated mutation
  - destructive operation
```

Natural-language details belong in separate fields such as `Reviewer target:`,
`Human verification needed:`, or `Acceptance criteria:`. Do not hide prose
inside role fields.

### Testing Contract

Add a Testing Contract only when test responsibility is not obvious:

```markdown
## Testing Contract

Testing Responsibility: tester | implementer | reviewer | none
Tester Trigger:
  - user-visible state transition needs objective evidence before review
user_value_or_risk: what confidence this evidence protects
fixture_provenance: synthetic_minimal | route_mock | temp_selected_vault | real_backend_temp_db | private_or_user_data_excluded
evidence_required:
  - static
  - unit
  - integration
  - route_mocked_browser
  - negative_adversarial
handoff_target: reviewer
```

Use `unknown` or `not_available` when evidence cannot be observed. Do not guess
fixture provenance, backend coverage, latency, token cost, or environment state.

### Handoff Comment

Every meaningful handoff should record:

- issue, PR, branch, exact head, base branch, parent Epic;
- current owner and next owner;
- scope completed or decision made;
- verification commands, artifacts, or manual checks;
- labels/state changed;
- residual risks and deferred work;
- forbidden actions preserved;
- callback target when work came from another thread.

## Merge And Closure Rules / Merge 和 Closure 规则

- Child PRs may merge into authorized non-main integration branches when the
  issue/Epic contract delegates it, latest-head checks pass, and review is
  accepted.
- `main` merges require Human approval unless repo policy and issue contract
  explicitly delegate auto-main merge and no meaningful human judgment remains.
- Child issues may close after verified delegated completion. Epic, stage,
  release window, privacy/security, destructive, and product distribution
  closure still need the appropriate higher gate.
- Exact-head protection applies to review and merge. A changed head resets the
  relevant checks or review.

## Collaboration Modes / 协作模式

| Mode | Use when |
| --- | --- |
| Single-thread serial | Scope is small, low risk, and one agent can keep role stance clear. |
| Role handoff | Independent Architect, Implementer, Reviewer, Tester, Harvester, or Human stance matters. |
| Tester pass | Evidence quality is the bottleneck before review or human trial. |
| Batch checkpoint | Related low-risk issues should be reviewed or accepted together. |
| Human-gated close | Final integration, Epic closure, product distribution, privacy, or irreversible action is under review. |

## Anti-Patterns / 反模式

- routing every non-Implementer transition to Human;
- using Tester as another Reviewer;
- treating Project fields as stronger than issue/PR durable state;
- merging a PR whose head differs from the reviewed head;
- closing an Epic because child issues are done while closure evidence or human
  approval is still missing;
- hiding raw script-first behavior behind user-facing docs;
- describing generated text as live dispatch evidence;
- using role labels to mask unclear ownership;
- letting Implementer expand scope instead of routing back to Architect;
- treating passing tests as a substitute for product acceptance.
