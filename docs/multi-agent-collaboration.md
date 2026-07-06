# Multi-Agent Collaboration Workflow / 多 Agent 协作开发流程

This document describes how Agent Foundry uses role-based collaboration for
issue-driven development. It is a human-readable operating model, not an
automation contract. Detailed helper behavior remains in
`workflows/github-collaboration-helper.md` and related templates.

本文描述 Agent Foundry 如何使用 role-based collaboration 做 issue-driven
development。它是人可读的工作模式说明，不是自动化合约。具体 helper 行为仍以
`workflows/github-collaboration-helper.md` 和相关 templates 为准。

## Core Idea / 核心思路

Multi-agent collaboration exists to keep different kinds of judgment separate.
Design, implementation, test evidence, independent review, scheduling, and human
product judgment each need a different stance.

多 Agent 协作的目的，是把不同性质的判断分开。设计、实现、测试证据、独立审查、
调度，以及人的产品判断，需要不同的工作姿态。

The durable scheduler state is GitHub issue and PR state: issue body, Execution
Contract, Testing Contract when present, comments, labels, PR head, merge target,
and closure evidence. Project fields are useful mirrors, but they are not the
primary source of truth.

Durable scheduler state 以 GitHub issue 和 PR 为准：issue body、Execution
Contract、必要时的 Testing Contract、comments、labels、PR head、merge target
和 closure evidence。Project fields 是有用的镜像，但不是主要 source of truth。

## Roles / 角色

| Role | Primary responsibility | Does not do |
| --- | --- | --- |
| Coordinator | Intake, durable state readback, dependency order, routing, label/Project coherence, callback. | Product acceptance, implementation review, hidden `needs:coordinator` authority. |
| Architect | Scope, architecture, Execution Contract, downstream release, acceptance routing, Human Decision Contract when needed. | Implement broad changes in a design gate, bypass Reviewer, bypass Human gates. |
| Implementer | Scoped production change, required tests, branch/PR, implementation handoff. | Define new product authority after scope is set, self-accept the work. |
| Tester | Testing plan, test matrix, evidence execution or evidence gap report, residual risk handoff. | Approve, reject, merge, close, replace Reviewer/Architect/Human acceptance. |
| Reviewer | Independent findings-first review against issue contract, risk, tests, and changed behavior. | Own product direction, merge without gate, treat passing tests as the whole review. |
| Human | Product direction, subjective trial, high-risk or final integration approval, closure authorization when required. | Repeat every low-risk mechanical transition. |
| Harvester | Evidence collection and reusable practice/asset candidate extraction. | Activate practices/assets without review. |

## Normal Development Flow / 标准开发流

1. **Intake and scheduling**

   Coordinator or an equivalent scheduler reads durable state, identifies the
   next dependency-ready issue, and routes it with a `needs:*` label and owner
   role.

2. **Architect design or contract**

   Architect defines scope, boundaries, branch strategy, acceptance criteria,
   and the next owner. This is where Testing Contract responsibility is decided
   when the risk needs explicit test evidence.

3. **Optional Tester planning or evidence**

   Tester is used when confidence depends on an explicit test matrix, fixture
   provenance, route-mocked versus real-backend coverage, negative/adversarial
   assertions, state-transition evidence, or objective evidence before a human
   trial.

4. **Implementer work**

   Implementer changes production files within the accepted scope and writes the
   required tests or fixtures named by the Execution Contract or Testing
   Contract. If a Tester pass already produced a matrix, Implementer uses it as
   implementation guidance rather than acceptance.

5. **Reviewer gate**

   Reviewer checks the exact PR head or exact issue evidence. Findings lead.
   Reviewer can accept, request changes, or identify gaps, but acceptance routes
   to Architect for the next state.

6. **Architect acceptance and routing**

   Architect decides whether Reviewer evidence satisfies the contract. For child
   PRs into authorized non-main integration branches, Architect may merge when
   the issue/Epic contract delegates it and checks pass. For final `main`
   integration, Epic/stage closure, privacy/security boundary changes, or other
   human-only decisions, Architect posts a Human Decision Contract.

7. **Human gate when needed**

   Human approval states the concrete decision under review. Good control comes
   from visible state, owner, next action, forbidden actions, and recovery path,
   not from asking for approval on every low-risk transition.

8. **Closure and release of the next dependency**

   After verified completion, the authorized owner closes the issue if delegated
   completion criteria are met, removes stale `needs:*` labels, records durable
   verification, and releases the next dependency-gated issue.

## Tester Placement / Tester 在流程中的位置

Tester can appear in two places:

- before implementation, when Architect needs a test plan or matrix before
  coding starts;
- after implementation, when changed behavior needs focused evidence before
  Reviewer or Human evaluation.

Tester is triggered by risk, not by hierarchy. Use Tester when the question is:
what was tested, why is it enough, what remains risky, and what evidence should
the next role trust?

Common Tester triggers:

- user-visible workflows, state transitions, browser paths, or manual trial
  preparation;
- route-mocked versus real-backend behavior where both matter;
- runtime, Generated, selected Vault, Local Private, external import, or
  capability-pack boundaries;
- scheduler state changes, label/Project transitions, or handoff semantics;
- negative, adversarial, prompt-injection, stale-state, unsafe-write, leak, or
  rollback cases;
- high residual risk where passing unit tests does not explain user confidence.

Skip Tester when:

- the change is small docs/copy/static validation;
- existing unit or integration tests already answer the confidence question;
- Reviewer can directly inspect the exact behavior without extra evidence;
- the issue contract intentionally delegates test design to Implementer and the
  risk is low.

Tester output normally routes:

- to Reviewer when evidence is complete;
- to Implementer when defects or missing tests are found;
- to Architect when scope, risk, or acceptance criteria are unclear;
- to Human when objective evidence is ready but subjective trial or product
  approval is still required.

## Testing Contract / 测试合约

A Testing Contract is added only when explicit test responsibility is needed.
It should be short enough to guide work without becoming a second design spec.

Typical fields:

```markdown
## Testing Contract

Testing Responsibility: tester | implementer | reviewer | none
Tester Trigger:
  - user-visible state transition needs objective evidence before review
user_value_or_risk: what user confidence this test evidence protects
user_journey_or_state_chain: start -> action -> visible result -> next action
fixture_provenance: synthetic_minimal | route_mock | temp_selected_vault | real_backend_temp_db | private_or_user_data_excluded
evidence_required:
  - static
  - unit
  - integration
  - route_mocked_browser
  - real_backend_temp_db_browser
  - negative_adversarial
  - manual_human_trial
test_matrix:
  - scenario: preview does not write runtime files
    risk: unsafe_write
    evidence_type: integration
    fixture: temp selected Vault
    expected_signal: writes none, report names next safe action
    owner: tester
    residual_gap: does not prove subjective wording clarity
handoff_target: reviewer
```

Use `unknown` or `not_available` when evidence cannot be observed. Do not guess
latency, token cost, environment state, fixture provenance, or backend coverage.

## Handoff Evidence / 交接证据

Every meaningful handoff should state:

- subject: issue, PR, branch, exact head, base branch, parent Epic;
- current owner and next owner;
- scope completed or decision made;
- commands, artifacts, or manual checks performed;
- labels/state changed;
- residual risks and deferred work;
- forbidden actions preserved;
- callback target when the work came from another thread or role.

For PR work, exact-head verification protects the review. If the head changes,
rerun the relevant review or checks before accepting or merging.

## Human Gates / Human gate

Human approval is required for final `main` integration unless a repo policy or
issue contract explicitly delegates it, Epic/stage/window closure, direct
privacy/security boundary changes, destructive operations, force push/reset,
live Vault/runtime/generated/private mutation, generated adapter publish when
not already reviewed, and any product/distribution decision the contract marks
as human-owned.

The Human Decision Contract should name the concrete decision, verification
basis, allowed actions after approval, forbidden actions that remain forbidden,
and exact approval phrase.

## Collaboration Modes / 协作模式

| Mode | Use when |
| --- | --- |
| Single-thread serial | Scope is small, low risk, and one agent can design, implement, and explain checks without losing clarity. |
| Role-thread handoff | Independent role stance matters, such as Architect to Implementer to Reviewer. |
| Tester pass | Evidence quality is the bottleneck before review or human trial. |
| Batch checkpoint | Several child issues or PRs must be accepted together to preserve dependency order. |
| Human-gated close | Final integration, Epic closure, product distribution, privacy, or irreversible actions need explicit human review. |

## Anti-Patterns / 反模式

- routing every non-Implementer transition to Human;
- using Tester as another Reviewer;
- treating Project fields as stronger than issue/PR durable state;
- merging a PR whose head differs from the reviewed head;
- closing an Epic because child issues are done when the closure output or human
  gate is still missing;
- hiding raw script-first behavior behind user-facing docs;
- describing generated text as live dispatch evidence;
- using role labels to mask unclear ownership.
