# Multi-Agent Collaboration Workflow

This document describes Agent Foundry's role-based issue and PR workflow. It is
an operating guide for humans and agents. Helper commands, schemas, and
template details remain in `workflows/github-collaboration-helper.md` and
`templates/`.

**中文要点：** 本文是 multi-agent collaboration 的操作指南。它解释 role、流程、
handoff、readiness 和 gate，不替代 helper/template 的机器合约。

## Purpose

Multi-agent collaboration separates different kinds of work so each decision is
made by the right role. A good workflow keeps status visible, ownership clear,
handoffs durable, and human attention focused on real judgment.

Durable state comes from GitHub issues, PRs, comments, labels, exact heads,
Execution Contracts, optional Testing Contracts, and closure evidence. Project
fields are visual mirrors and scheduler metadata; they do not outrank issue/PR
durable state.

**中文要点：** 多 Agent 协作的价值是把设计、实现、测试证据、独立审查、调度和人的
产品判断分开。GitHub issue/PR/comment/label/contract 是 durable state；
Project/Kanban 只是可视化镜像。

## Collaboration Readiness

Before a repo adopts this workflow, or when an existing project shows routing
drift, run a collaboration readiness audit. The audit should answer what is
ready, what is missing, what is inconsistent, and what the next safe action is.

The audit is read-only. It may inspect labels, role routing templates,
Execution Contract values, Testing Contract values, issue and PR routing state,
Project/Kanban visibility, and handoff evidence. Its report should state
`mutation_performed: false`.

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

The report shape should be stable enough for future local-first orchestration
and Foundry Board backfill. GitHub Project remains a sync or visibility surface;
it does not become the authority.

For V2 local-first orchestration, the Foundry Board preview is the user-facing
read-only board/report built on the same evidence discipline. It can summarize
lanes, owners, latest evidence, branch readiness, human gates, candidate versus
accepted migrated state, and Project mirror drift. It does not write GitHub,
mutate Project v2, sync a ledger, perform migration/backfill writes, or repair
branches.

**中文要点：** readiness audit 用来判断 repo 是否具备 role-based collaboration 条件。
它只读、低成本、可 degraded；可以给 dry-run repair plan，但不执行修复。报告结构要能
服务未来 Foundry Board / local-first backfill，同时明确 GitHub Project 不是权威状态。

## Roles

| Role | Triggered by | Main output | Hands off to | Boundary |
| --- | --- | --- | --- | --- |
| Coordinator | A queue, Epic, dependency, stale state, or cross-thread handoff needs synchronization. | Routing comment, dependency decision, label/Project coherence, callback. | Architect, Implementer, Reviewer, Tester, Harvester, or Human. | Does not own product acceptance or create hidden `needs:coordinator` authority. |
| Architect | Scope, architecture, taxonomy, privacy, gate, release order, or acceptance decision is needed. | Decision, Execution Contract, Human Decision Contract, downstream release, acceptance/hold. | Implementer, Tester, Reviewer, Human, or next Architect issue. | Does not implement broad changes inside design gates or bypass review. |
| Implementer | A scoped task has accepted design, allowed files, branch strategy, and verification expectations. | Code/docs/tests, PR, implementation handoff, verification evidence. | Tester or Reviewer, usually through PR and issue comments. | Does not self-accept, redefine scope, or make new product authority. |
| Tester | The issue needs explicit test planning, evidence execution, matrix coverage, or objective evidence before review/trial. | Test plan, matrix, executed evidence, gaps, residual risks. | Reviewer, Implementer, Architect, or Human. | Does not approve, reject, merge, close, or replace Reviewer/Architect/Human. |
| Reviewer | A PR, issue evidence packet, readiness gate, or Tester evidence needs independent review. | Findings-first review, acceptance or requested changes, verification basis. | Architect or Implementer. | Does not own product direction or final acceptance. |
| Human | Product direction, subjective trial, final integration, Epic/stage closure, privacy/security, destructive, or high-risk decision is required. | Approval, rejection, revision, or trial result. | Coordinator or Architect. | Should not be asked to approve routine low-risk mechanics. |
| Harvester | Real work should be converted into reusable practices, assets, or candidate capability material. | Evidence inventory, candidate packet, reuse recommendation. | Reviewer or Architect. | Does not activate/publish without review and approval. |

**中文要点：** 每个 role 的核心边界不同。Coordinator 管流程，Architect 管形状和 gate，
Implementer 做 scoped change，Tester 提供测试证据，Reviewer 做独立审查，Human 做真实
产品/风险决策，Harvester 把经验整理成候选资产。

## Standard Flow

| Step | Owner | What happens | Exit signal |
| --- | --- | --- | --- |
| 1. Intake | Coordinator | Rehydrate durable state, check dependencies, choose the next owner. | Issue has one clear next `needs:*` label or a recorded hold. |
| 2. Design / Contract | Architect | Define scope, risk, allowed actions, forbidden actions, branch strategy, target branch, acceptance criteria, and whether Tester is needed. | Execution Contract is durable; next owner is released. |
| 3. Implementation or Evidence | Implementer, Tester, or Harvester | Produce the scoped change or evidence packet. | Handoff names scope, verification, residual risks, and next owner. |
| 4. Review | Reviewer | Review exact issue evidence or exact PR head. Findings lead; acceptance is not final closure. | Accepted, requested changes, or blocked with reasons. |
| 5. Acceptance / Routing | Architect | Decide whether review evidence satisfies the contract and route merge, closure, human gate, or next issue. | Durable acceptance, hold, HDC, merge decision, or release decision. |
| 6. Human Gate | Human, when required | Approve or revise the concrete decision under review. | Explicit approval phrase or revised direction. |
| 7. Completion | Authorized role | Verify post-merge or post-action state, close delegated child issues, clean stale labels, release next dependency. | Completion comment, final state, residual risks. |

Low-risk work may stay in one thread if the role stance remains clear. Separate
role handoffs are useful when independent review, product judgment, testing
evidence, or durable scheduling outweighs coordination cost.

**中文要点：** 标准流程是 intake -> design/contract -> implementation/evidence ->
review -> architect acceptance/routing -> human gate when needed -> completion。
低风险工作可以单线程完成；需要独立判断或 durable handoff 时再拆 role。

## Role Rules

### Coordinator

Coordinator protects workflow continuity. It reads durable state, detects
dependency order, repairs mechanical routing drift, and records callbacks.
Coordinator may dispatch work, but it should not turn itself into a hidden
authority role.

Use Coordinator for queue management, stale labels, Project/label mismatch,
cross-thread handoff, Epic sequencing, callback consolidation, and status
readback.

**中文要点：** Coordinator 负责流程连续性和状态同步，不负责产品验收，也不引入
`needs:coordinator` 这种隐藏 authority。

### Architect

Architect protects the shape of the work. It decides what problem is being
solved, what is out of scope, which role owns the next step, and which gates
must remain human-owned.

Use Architect for design, taxonomy, privacy/security boundaries, issue
decomposition, branch/integration strategy, acceptance after review, and Human
Decision Contracts.

**中文要点：** Architect 决定 scope、architecture、dependency、gate 和 downstream
release，不在 design gate 里顺手做大范围 implementation。

### Implementer

Implementer changes the repository under an accepted contract. It should keep
the diff focused, write or update required tests, avoid unrelated cleanup, and
handoff with exact verification.

Use Implementer only after the issue names allowed scope, dependencies, branch
strategy, target branch, acceptance criteria, and required evidence. If scope changes while
implementing, route back to Architect instead of expanding silently.

**中文要点：** Implementer 在明确 contract 下写 production change 和 required tests。
如果发现 scope 需要扩大，应回到 Architect，而不是静默扩展。

### Tester

Tester protects confidence in behavior. It designs or executes evidence when
ordinary implementation tests are not enough to explain risk.

Use Tester for user-visible state, browser flows, route-mocked versus
real-backend behavior, runtime/Generated/Vault/Local Private boundaries,
external import, capability-pack behavior, scheduler transitions, negative or
adversarial cases, rollback, leak checks, and human-trial preparation.

Skip Tester when a small docs check, static check, unit test, or Reviewer
read-through already answers the confidence question.

Tester output routes to Reviewer when evidence is ready, to Implementer when
defects or missing tests are found, to Architect when criteria are unclear, and
to Human when objective evidence is ready but subjective acceptance remains.

**中文要点：** Tester 不是另一个 Reviewer。它负责回答“测了什么、为什么足够、还剩
什么风险”，并把证据交给 Reviewer/Implementer/Architect/Human。

### Reviewer

Reviewer protects independent judgment. It checks the issue contract, exact PR
head, diff, tests, risk, and user-visible behavior. Findings come first; a
short acceptance is enough only when no meaningful risks remain.

Reviewer acceptance routes to Architect for acceptance/routing unless the issue
contract explicitly defines another next owner.

**中文要点：** Reviewer 做独立审查，先报 findings。Reviewer acceptance 通常不是最终
closure，而是交给 Architect 做 acceptance/routing。

### Human

Human handles product direction and meaningful approval. A good human gate names
the concrete decision, evidence, allowed actions, still-forbidden actions,
consequences, and exact approval phrase.

Use Human gates for final `main` integration when not delegated, Epic/stage
closure, product/distribution choices, subjective trial acceptance,
privacy/security boundaries, destructive operations, data migration, direct
runtime/private/generated mutation, and unclear user-specific choices.

**中文要点：** Human gate 用在真正需要人的判断处。好的控制感来自状态、owner、下一步、
禁止动作和恢复路径清楚，而不是每一步都弹确认。

### Harvester

Harvester converts real work into candidate reusable value. It can inventory
lessons, patterns, and artifacts, but canonical practice/asset activation still
requires review and approval.

**中文要点：** Harvester 负责把经验整理成 candidate reusable value。是否进入 canonical
practice/asset 仍要 review 和 approval。

## Contracts

### Execution Contract

Every implementation or evidence issue should make ownership machine-readable:

```markdown
## Execution Contract

Owner role: implementer
Review role: reviewer
Acceptance role: architect
Completion handoff: to:reviewer
Branch strategy: mainline-maintenance | integration-branch | release-branch | trunk-based | stacked-pr | multi-branch | custom
Target branch: main | <integration-branch> | <release-branch>
Affected branches: <optional comma-separated branch list>
Verification branches: <optional comma-separated branch list>
Merge rule: human-gated | delegated-child | delegated-main
Forbidden actions:
  - live Vault/private/runtime/generated mutation
  - destructive operation
```

Natural-language details belong in separate fields such as `Reviewer target:`,
`Human verification needed:`, or `Acceptance criteria:`. Do not hide prose
inside role fields.

`Target branch` is the canonical field. Older `Branch target` text may appear
in legacy issues, but new contracts should not use it except to document
compatibility mapping.

**中文要点：** 新 contract 使用 `Branch strategy` 和 `Target branch`。`Branch target`
只作为旧字段兼容说明，不再作为新示例。

### Branch-Aware Collaboration

Branch-aware collaboration helps a human decide where work should land before an
agent starts editing or reviewing. It is an action-plan surface, not an
automatic branch operator. The helper may report the current branch, expected PR
base, local dirty/ahead/behind state, and degraded remote evidence, but it must
not checkout, create worktrees, retarget PRs, rebase, merge, reset, clean, or
apply repairs.

Choose the branch strategy from the user's intent:

| User intent | Branch strategy | Typical target |
| --- | --- | --- |
| Maintain the current stable product line. | `mainline-maintenance` | `main` |
| Build on a shared feature/integration line. | `integration-branch` | named integration branch |
| Prepare a release branch. | `release-branch` | release branch |
| Land directly through a trunk-style flow. | `trunk-based` | trunk branch chosen by the repo |
| Build a child PR on top of a parent PR. | `stacked-pr` | parent PR branch as `PR target` |
| Change more than one maintained line. | `multi-branch` | primary target plus affected/verification branches |
| Use a repo-specific policy. | `custom` | Architect-defined |

Agent Foundry's current presets are:

- V1.x maintenance: `Branch strategy: mainline-maintenance`,
  `Target branch: main`.
- V2 integration: `Branch strategy: integration-branch`,
  `Target branch: codex/v2-local-first-orchestration`.
- V2 merge-back to `main` remains a later readiness and Human-gated decision.

When V2 work is active but a generic Core update belongs on `main`, split the
work. Land the generic Core update on `main`, record a later forward-merge need,
and verify on both lines before claiming cross-line readiness. Multi-branch work
should name `Affected branches` and `Verification branches`; it should not hide
ordered verification inside a single vague target.

Action-plan concepts mean:

| Concept | Human-facing meaning | Safe next step |
| --- | --- | --- |
| `current_branch_ok` | The sampled local branch matches at least one branch contract. | Continue normal scoped work. |
| `switch_context_required` | The current local branch is not the target branch. | Stop editing in this checkout; route or prepare a separate reviewed context. |
| `split_work_recommended` | The request mixes branch lines or stacked work. | Split the issue/PR or record ordered sub-work. |
| `forward_merge_needed_later` | A later line needs the accepted change. | Record follow-up evidence; do not merge automatically. |
| `verify_on_multiple_lines` | Readiness claim spans more than one branch line. | Run or request verification on every named line. |
| `architect_decision_required` | Strategy is custom, unknown, or policy-sensitive. | Route to Architect before implementation or merge. |

**中文要点：** Branch-aware collaboration 先帮人判断 work 应该落在哪条 branch line。
它只给 action plan，不自动 checkout、retarget、merge 或 repair。V2 work 和通用 Core
update 交错时，优先 split work：通用更新先落 `main`，记录后续 forward-merge，并在多条
line 上验证。

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

**中文要点：** Contract 里的 role fields 必须 machine-readable。自然语言说明放在单独
字段。Handoff comment 要能让下一个 role 不靠聊天上下文也能继续工作。

## Merge And Closure Rules

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

**中文要点：** child PR 可以在授权的 non-main integration branch 内合并；final `main`
integration、Epic/stage closure、隐私/安全/破坏性动作仍需要相应更高 gate。review/merge
必须保护 exact head。

## Collaboration Modes

| Mode | Use when |
| --- | --- |
| Single-thread serial | Scope is small, low risk, and one agent can keep role stance clear. |
| Role handoff | Independent Architect, Implementer, Reviewer, Tester, Harvester, or Human stance matters. |
| Tester pass | Evidence quality is the bottleneck before review or human trial. |
| Batch checkpoint | Related low-risk issues should be reviewed or accepted together. |
| Human-gated close | Final integration, Epic closure, product distribution, privacy, or irreversible action is under review. |

**中文要点：** 不要为了形式感拆 agent。只有当独立判断、测试证据、批量 checkpoint 或
human gate 的价值超过协调成本时，才使用更重的协作模式。

## Anti-Patterns

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

**中文要点：** 常见错误是过度 human-gate、把 Tester 当 Reviewer、把 Project 当权威、
忽略 exact head、用 label 掩盖 owner 不清，以及把 tests passing 当成产品验收。
