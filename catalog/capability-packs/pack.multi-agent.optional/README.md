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

`pack.multi-agent.optional` 帮助团队把 Agent Foundry 用在 GitHub issues 和 pull
requests 上，并在 Implementer、Reviewer、Architect、Coordinator 和 Human decision
points 之间保留 handoff context。它的价值是可重复的协作纪律，而不是自动项目管理。

## Supported Workflow / 支持的协作流程

The pack supports GitHub issue/PR collaboration with role labels, durable issue
comments, explicit Execution Contracts, dependency-gated queues, review
handoffs, and read-only audit before write automation. It is useful when work
must move between multiple role sessions while GitHub remains the durable source
of truth.

这个 pack 支持使用 role labels、durable issue comments、explicit Execution Contracts、
dependency-gated queues、review handoffs，以及 write automation 前的 read-only audit
来进行 GitHub issue/PR 协作。当工作需要在多个 role sessions 之间流转，并且 GitHub
仍然是 durable source of truth 时，它最有用。

## What Remains Manual Or Review-Gated / 仍需手动或 Review-Gated 的内容

People or delegated workflow roles still decide scope, architecture direction,
dependency release, merge authorization, issue closure, and any action that
changes protected branches or crosses privacy/security boundaries. Project v2
may mirror status when configured, but labels and durable comments remain the
handoff mechanism.

Scope、architecture direction、dependency release、merge authorization、issue
closure，以及任何修改 protected branches 或跨越 privacy/security boundaries 的动作，
仍由人或被委托的 workflow roles 决定。Project v2 可在配置后 mirror status，但 labels
和 durable comments 仍是 handoff mechanism。

## What It Does Not Automate / 不自动化什么

This pack does not merge PRs, close issues, create hidden access control, apply
runtime helpers, publish generated Skills, mutate Project v2 by default, export
private Vault content, or treat local helper receipts as authority.

这个 pack 不会 merge PRs、close issues、创建隐藏 access control、apply runtime
helpers、publish generated Skills、默认 mutate Project v2、export private Vault
content，也不会把 local helper receipts 当成 authority。

## When To Accept / 何时接受安装

Accept or install this pack when a project coordinates implementation and
review through GitHub issues/PRs and needs durable role handoffs. Skip it when a
project is single-user, local-only, or not ready to use GitHub labels and issue
comments as the workflow record.

当项目通过 GitHub issues/PRs 协调 implementation 和 review，并需要 durable role
handoffs 时，接受或安装这个 pack。若项目是单人、本地-only，或尚未准备好把 GitHub
labels 和 issue comments 作为 workflow record，可以跳过它。

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
and read-only audit before write automation.

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

Pack version `0.2.0` identifies the reviewed GitHub collaboration starter
contract. Core git tags and releases identify repository snapshots. These are
related but independent axes.

## Review

Review evidence:

- https://github.com/farmerhunter/agent-foundry/issues/252
- https://github.com/farmerhunter/agent-foundry/issues/253
