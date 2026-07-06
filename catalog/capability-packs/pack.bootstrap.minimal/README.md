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

**中文要点：** 这是新 Vault 的最小 reviewed baseline，用来先建立 harvest、
review、refresh、status 和 source-of-truth 边界，再考虑 optional packs。

## Concrete Function / 具体功能

This pack carries the bootstrap capability and `ASSET-META-001` governance
baseline. It orients the user around the selected User Vault as the accepted
deployment target, Core as public catalog/tooling, Generated and Runtime as
downstream status or install surfaces, and Local Private evidence as excluded
from pack authority.

**中文要点：** 它携带 bootstrap capability、`ASSET-META-001` governance
baseline，并明确 Core、selected User Vault、Generated、Runtime、Local Private
各自的权威边界。

## What It Enables Next / 接下来能启用什么

After bootstrap is accepted, users can safely preview optional starter packs,
verify deployed pack state, compare updates, disable a pack through a reviewed
path, and inspect generated/runtime follow-up without treating those downstream
surfaces as source of truth.

**中文要点：** 接受 bootstrap 后，用户可以安全 preview、verify、update、disable
optional packs，同时不会把 generated/runtime downstream surfaces 当成 source of
truth。

It also carries the AF13 external-skill import/reference baseline. External
sources are reviewed inputs with explicit outcomes: `discard`, `reference_only`,
`defer`, `merge_into_existing`, `propose_practice`, or `propose_asset`.
`reference_only` stays selected Vault `imports/inbox/` evidence only; publishing
adapters or generated Skills is a later post-approval action after canonical
records are approved.

**中文要点：** 它也包含 AF13 external-skill import/reference baseline：外部来源只
能先成为 reviewed input；`reference_only` 只是 `imports/inbox/` 证据，不会激活、
publish 或成为 pack authority。

## What It Does Not Do / 不做什么

This pack does not create a separate architecture-boundary starter pack, install
runtime files, publish generated adapters, export a private Vault, or make
project-specific governance decisions. It does not duplicate `ASSET-META-001`;
it preserves that baseline in the bootstrap path.

**中文要点：** 它不安装 runtime files、不发布 generated adapters、不 export
private Vault、不替项目做 governance decision，也不会把 external/reference-only
材料变成 active authority。

## When To Accept / 何时接受安装

Accept or install this pack when you are setting up a selected User Vault for
normal Agent Foundry use, before installing optional packs, or when you need to
restore the baseline boundary guidance for harvest/review/status workflows.

**中文要点：** 新建 selected Vault、安装 optional packs 前，或需要恢复
harvest/review/status baseline 时接受它。

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

Pack version `0.2.1` identifies the reviewed bootstrap pack contract. Core git
tags and releases identify repository snapshots. These are related but
independent axes.

## Review

Review evidence:

- https://github.com/farmerhunter/agent-foundry/issues/232
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787766294
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787780757
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787793177
- https://github.com/farmerhunter/agent-foundry/issues/253
