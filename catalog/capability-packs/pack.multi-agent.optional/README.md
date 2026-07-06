# Optional GitHub Collaboration Starter Pack

Official Core catalog entry for the reviewed optional GitHub collaboration
starter pack.

This entry deliberately keeps the existing `pack.multi-agent.optional` fixture
identity so older capability-pack planning, apply, update, and lifecycle tests
continue to exercise the same compatibility path. The pack is discoverable as a
first-party starter, while its member records still deploy as manual-review
candidate records in the selected User Vault.

## User Value / 用户价值

`pack.multi-agent.optional` helps teams use Agent Foundry with GitHub issues
and pull requests without losing handoff context between Implementer, Reviewer,
Architect, Coordinator, and Human decision points. Its value is repeatable
collaboration discipline, not automatic project management.

**中文要点：** 这个 pack 帮团队在 GitHub issue/PR 协作中保留 handoff context。
它提供可重复的协作纪律，不是自动项目管理。

## Supported Workflow / 支持的协作流程

The pack supports GitHub issue/PR collaboration with role labels, durable issue
comments, explicit Execution Contracts, dependency-gated queues, review
handoffs, and read-only audit before write automation. It is useful when work
must move between multiple role sessions while GitHub remains the durable source
of truth.

**中文要点：** 它覆盖 role labels、durable comments、Execution Contracts、
dependency-gated queues、review handoffs，以及 write automation 前的 read-only
audit。

## Collaboration Readiness / 协作就绪检查

The current starter guidance includes the AF15 collaboration readiness model:
new projects can check whether role labels, routing templates, Execution
Contracts, Testing Contracts, and optional Project/Kanban mirrors are present
before they start multi-agent work. Existing projects can audit drift and get a
dry-run repair plan without changing GitHub or Project state.

**中文要点：** 新项目先检查 role labels、routing templates、Execution Contracts、
Testing Contracts 和可选 Project/Kanban mirrors；老项目 audit drift 并得到安全
action plan。

Readiness reports are expected to stay read-only. They should show
`mutation_performed: false`, use REST-first GitHub access, query Project v2 only
when configured and needed, avoid default full Project scans, and report
degraded GitHub or Project access instead of hiding it.

Normal users should read the action-plan layer before raw JSON evidence:
`readiness_status`, summary, blocking gaps, unknown/degraded sources,
recommended next actions, forbidden actions, and telemetry. Recommended actions
are informational-only, handled through existing workflow, explicit human gate,
or unsupported/deferred repair/apply.

**中文要点：** 普通用户先看 action-plan layer：status、summary、blocking gaps、
unknown/degraded sources、recommended next actions、forbidden actions 和 telemetry。
Raw JSON 是 evidence/debug output。

Readiness reports stay read-only. They show `mutation_performed: false`,
use REST-first GitHub access, query Project v2 only when configured and needed,
avoid default full Project scans, and report degraded GitHub or Project access
instead of hiding it.

**中文要点：** Readiness report 仍是 read-only：不执行 repair/apply，不默认扫全量
Project，访问 degraded 时明确报告。

## What Remains Manual Or Review-Gated / 仍需手动或 Review-Gated 的内容

People or delegated workflow roles still decide scope, architecture direction,
dependency release, merge authorization, issue closure, and any action that
changes protected branches or crosses privacy/security boundaries. Project v2
may mirror status when configured, but labels and durable comments remain the
handoff mechanism.

**中文要点：** scope、architecture、release、merge、closure 和隐私/安全边界仍由
人或被委托的 workflow roles 决定；Project v2 只是可选 mirror。

## What It Does Not Automate / 不自动化什么

This pack does not merge PRs, close issues, create hidden access control, apply
runtime helpers, publish generated Skills, mutate Project v2 by default, execute
dry-run repair plans, export private Vault content, or treat local helper
receipts as authority.

**中文要点：** 它不 merge/close、不执行 live repair/apply、不 mutate Project v2、
不 publish generated Skills、不 export private Vault。

## When To Accept / 何时接受安装

Accept or install this pack when a project coordinates implementation and
review through GitHub issues/PRs and needs durable role handoffs. Skip it when a
project is single-user, local-only, or not ready to use GitHub labels and issue
comments as the workflow record.

**中文要点：** 项目通过 GitHub issues/PRs 协调并需要 durable handoffs 时安装；
纯本地单人项目可跳过。

## Authority

- Core hosts this official catalog entry and reviewed manifest reference.
- The selected User Vault remains canonical after accepted deployment.
- Generated adapters and runtime installs remain downstream projections.
- Project-specific repository names, issue numbers, branch names, Project ids,
  local caches, runtime receipts, raw sessions, secrets, and private Vault
  content are excluded.

## Scope

The pack covers a base GitHub collaboration workflow: role labels, durable
issue/PR comments, explicit Execution Contract fields, dependency-gated queues,
Testing Contract evidence when needed, collaboration readiness audit, dry-run
repair planning, degraded GitHub/Project access reporting, and read-only audit
before write automation.

Project v2 status may be a configured visual mirror, but it is not the scheduler
source of truth. Runtime helper install, generated Skill publish, and mutating
automation remain deferred to later reviewed workflows.

## Use Safely

This pack is optional after bootstrap and first value. Normal users should start
with `list capability packs`, `recommend capability packs for my setup`, and
`preview capability pack deployment <pack-path>` before any apply request.

Preview, verify, update comparison, and disable review paths should report
`writes: none`. Accepted apply paths must name the selected Vault write target.
Generated adapters, runtime installs, Project status mirrors, and local helper
receipts remain downstream status surfaces, not catalog or pack authority.

## Versioning

Pack version `0.3.1` identifies the reviewed GitHub collaboration readiness
starter contract. Pack version `0.2.0` identified the earlier GitHub
collaboration starter contract. Core git tags and releases identify repository
snapshots. These are related but independent axes.

## Review

Review evidence:

- https://github.com/farmerhunter/agent-foundry/issues/252
- https://github.com/farmerhunter/agent-foundry/issues/253
- https://github.com/farmerhunter/agent-foundry/issues/315
- https://github.com/farmerhunter/agent-foundry/issues/316
- https://github.com/farmerhunter/agent-foundry/issues/317
- https://github.com/farmerhunter/agent-foundry/issues/318
- https://github.com/farmerhunter/agent-foundry/issues/319
