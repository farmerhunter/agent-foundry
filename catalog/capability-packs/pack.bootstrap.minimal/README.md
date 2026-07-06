# Minimal Agent Foundry Bootstrap Pack

Official Core catalog entry for the reviewed mandatory bootstrap pack.

This catalog page is discoverability metadata only. The reviewed manifest is
`fixtures/capability-packs/bootstrap-minimal/manifest.yaml`; the catalog pins
that manifest by SHA-256 in `catalog/capability-packs/index.yaml`.

## User Value / 用户价值

`pack.bootstrap.minimal` gives a new Agent Foundry setup a small, reviewed
baseline before optional packs are considered. It helps users keep harvest,
review, refresh, status, and source-of-truth behavior consistent instead of
learning those boundaries one script at a time.

`pack.bootstrap.minimal` 为新的 Agent Foundry setup 提供一个小型、reviewed 的
baseline，然后再考虑 optional packs。它帮助用户保持 harvest、review、refresh、
status 和 source-of-truth behavior 一致，而不是逐个脚本学习这些 boundaries。

## Concrete Function / 具体功能

This pack carries the bootstrap capability and `ASSET-META-001` governance
baseline. It orients the user around the selected User Vault as the accepted
deployment target, Core as public catalog/tooling, Generated and Runtime as
downstream status or install surfaces, and Local Private evidence as excluded
from pack authority.

The bootstrap baseline also includes the reviewed external-skill import and
reference safety model. External sources are reviewed with the outcomes
`discard`, `reference_only`, `defer`, `merge_into_existing`,
`propose_practice`, or `propose_asset`; `publish_after_approval` is a later
post-approval action, not an import outcome.

这个 pack 携带 bootstrap capability 和 `ASSET-META-001` governance baseline。
它让用户明确 selected User Vault 是 accepted deployment target，Core 是 public
catalog/tooling，Generated 和 Runtime 是 downstream status 或 install surfaces，
Local Private evidence 不属于 pack authority。

## What It Enables Next / 接下来能启用什么

After bootstrap is accepted, users can safely preview optional starter packs,
verify deployed pack state, compare updates, disable a pack through a reviewed
path, and inspect generated/runtime follow-up without treating those downstream
surfaces as source of truth.

接受 bootstrap 后，用户可以安全 preview optional starter packs、verify deployed
pack state、compare updates、通过 reviewed path disable pack，并查看 generated/runtime
follow-up，同时不会把这些 downstream surfaces 当成 source of truth。

## What It Does Not Do / 不做什么

This pack does not create a separate architecture-boundary starter pack, install
runtime files, publish generated adapters, export a private Vault, or make
project-specific governance decisions. It does not duplicate `ASSET-META-001`;
it preserves that baseline in the bootstrap path.

`reference_only` import evidence stays sanitized selected Vault `imports/inbox/`
review evidence for manual lookup and future re-review. It does not create
active behavior, generated/runtime output, dedupe bypasses, or practice, asset,
or capability-pack authority.

这个 pack 不会创建单独的 architecture-boundary starter pack，不会安装 runtime
files、发布 generated adapters、export private Vault，也不会替项目做 project-specific
governance decisions。它不会复制 `ASSET-META-001`；它在 bootstrap path 中保留该
baseline。

## When To Accept / 何时接受安装

Accept or install this pack when you are setting up a selected User Vault for
normal Agent Foundry use, before installing optional packs, or when you need to
restore the baseline boundary guidance for harvest/review/status workflows.

当你为正常 Agent Foundry 使用设置 selected User Vault、准备安装 optional packs，
或需要恢复 harvest/review/status workflows 的 baseline boundary guidance 时，接受或安装这个 pack。

## Authority

- Core hosts this official catalog entry and reviewed manifest reference.
- The selected User Vault remains canonical after accepted deployment.
- Generated adapters and runtime installs remain downstream projections.
- Private Vault evidence, local machine paths, runtime manifests, receipts,
  secrets, raw sessions, and usage rows are excluded.

AF12-3 keeps bootstrap as the only mandatory starter pack. It continues to
carry `ASSET-META-001`; Core does not create a duplicate meta/governance
starter pack. The runtime and generated status path remains part of
bootstrap/status surfaces rather than a standalone capability pack.

It also carries current-stage architecture-boundary orientation: Core is public
catalog and tooling, the selected User Vault is canonical after accepted
deployment, Generated and Runtime surfaces are downstream status or install
outputs, and Local Private evidence is excluded. That guidance is bootstrap and
governance behavior, not a standalone optional pack.

## Use Safely

This pack is the baseline for optional starter packs. Normal users should ask
for `list capability packs`, `preview capability pack deployment <pack-path>`,
`apply reviewed capability pack <pack-path>`, `verify capability pack
<pack-id>`, `update capability pack <pack-id-or-path>`, or `disable capability
pack <pack-id>` before using raw scripts.

Preview, verify, update comparison, and disable review paths should report
`writes: none`. Accepted apply paths must name the selected Vault write target.
Generated adapters and runtime installs remain downstream follow-up, not pack
authority.

## Versioning

Pack version `0.3.0` identifies the reviewed bootstrap pack contract. Pack
version `0.2.0` identified the AF12-3 starter-pack catalog baseline. Core git
tags and releases identify repository snapshots. These are related but
independent axes.

## Review

Review evidence:

- https://github.com/farmerhunter/agent-foundry/issues/232
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787766294
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787780757
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787793177
- https://github.com/farmerhunter/agent-foundry/issues/253
- https://github.com/farmerhunter/agent-foundry/issues/336
- https://github.com/farmerhunter/agent-foundry/issues/337
