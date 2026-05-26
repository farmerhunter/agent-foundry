# Create Or Extend Asset Workflow

Use this workflow after the user approves an asset candidate.

## 1. Confirm Candidate

Read:

- `schemas/asset.schema.yaml`
- `schemas/asset-candidate.schema.yaml`
- `indexes/asset_index.yaml`
- relevant canonical practices

Confirm approved candidate, asset type, whether this creates or extends, and target agents.

Apply:

- META-004 Choose the smallest suitable asset.
- META-005 Define asset boundaries before creation.

Do not create the asset if trigger, responsibility, non-responsibility, inputs, process, outputs, or success criteria remain unclear.

## 2. Create Or Extend

For a new asset:

- assign stable ID such as `ASSET-ARCH-002`;
- create under `assets/skills/`, `assets/subagents/`, or `assets/automations/`;
- set `status: active` when approval explicitly covers creation;
- link canonical practices;
- define triggers and success criteria;
- define responsibility and non-responsibility in the asset record when useful;
- update `indexes/asset_index.yaml`.

For an existing asset:

- update the asset record;
- increment version if behavior changes;
- update `updated`;
- preserve usage history.

## 3. Publish

After asset registry update:

- run `workflows/publish-adapters.md`;
- include the asset in relevant direct programming agent adapters;
- preserve canonical ID and asset ID mapping.

## 4. Usage Evidence

If the asset was created from specific evidence, add an initial note to `usage/asset-usage-log.yaml` only when useful and concise.

## 5. Report

Report changed files, adapters published, and next review cadence.
