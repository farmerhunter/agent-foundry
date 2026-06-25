# Architecture Boundary Review Starter Pack

Official Core catalog entry for the reviewed optional architecture boundary
review starter pack.

This pack uses public, synthetic examples only. It is intended to help reviewers
separate canonical authority from generated output, runtime receipts, and
local-private evidence before implementation changes proceed.

## Authority

- Core hosts this official catalog entry and reviewed manifest reference.
- The selected User Vault remains canonical after accepted deployment.
- Generated adapters and runtime installs remain downstream projections.
- Raw selected Vault export, private project notes, runtime receipts, local
  machine paths, secrets, generated adapter output, and private screenshots are
  excluded.

## Scope

The starter covers source-of-truth inventory, layer boundaries, downstream
status visibility, and fail-closed evidence gaps. Provider integration,
frontend workflow design, export publication, and runtime apply behavior remain
deferred until a later reviewed issue owns them.

## Use Safely

This pack is optional after bootstrap and first value. Normal users should start
with `list capability packs`, `recommend capability packs for my setup`, and
`preview capability pack deployment <pack-path>` before any apply request.

Preview, verify, update comparison, and disable review paths should report
`writes: none`. Accepted apply paths must name the selected Vault write target.
Generated adapters, runtime installs, raw selected Vault exports, and Local
Private evidence remain downstream or excluded surfaces, not catalog or pack
authority.

## Versioning

Pack version `0.1.0` identifies the reviewed architecture boundary starter
contract. Core git tags and releases identify repository snapshots. These are
related but independent axes.

## Review

Review evidence:

- https://github.com/farmerhunter/agent-foundry/issues/252
- https://github.com/farmerhunter/agent-foundry/issues/253
