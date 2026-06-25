# Minimal Agent Foundry Bootstrap Pack

Official Core catalog entry for the reviewed mandatory bootstrap pack.

This catalog page is discoverability metadata only. The reviewed manifest is
`fixtures/capability-packs/bootstrap-minimal/manifest.yaml`; the catalog pins
that manifest by SHA-256 in `catalog/capability-packs/index.yaml`.

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

Pack version `0.2.0` identifies the reviewed bootstrap pack contract. Core git
tags and releases identify repository snapshots. These are related but
independent axes.

## Review

Review evidence:

- https://github.com/farmerhunter/agent-foundry/issues/232
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787766294
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787780757
- https://github.com/farmerhunter/agent-foundry/issues/232#issuecomment-4787793177
- https://github.com/farmerhunter/agent-foundry/issues/253
