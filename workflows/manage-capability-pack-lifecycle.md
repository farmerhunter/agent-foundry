# Manage Capability Pack Lifecycle Workflow

Use this workflow when a capability pack needs lifecycle review after detection,
deployment, update comparison, split/merge analysis, deprecation, retirement, or
exportability discussion.

This workflow plans and reports lifecycle transitions. It does not bypass
practice review, asset review, runtime approval, export review, or human approval.

## Skill-First Entry Points

For normal agent use, invoke this workflow with natural-language requests such
as:

- `review capability pack lifecycle <pack-id>`
- `review capability pack activation <pack-id>`
- `review capability pack deprecation <pack-id>`
- `retire reviewed capability pack <pack-id>`

The agent should translate those requests into dry-run lifecycle reports first.
Raw scripts are implementation details or advanced/debug commands, not the
primary user surface.

## Normal-User Consumption Contract

Normal-user capability-pack consumption flows are:

- `list capability packs`;
- `recommend capability packs for my setup`;
- `preview capability pack deployment <pack-path>`;
- `apply reviewed capability pack <pack-path>`;
- `verify capability pack <pack-id>`;
- `update capability pack <pack-id-or-path>`;
- `disable capability pack <pack-id>`.

For these flows, the agent must return a compact user-visible report with:

- pack identity: id, title, version, source, and reviewed status;
- adopter display status such as `available`, `recommended`, `compatible`,
  `incompatible`, `deployed`, `update_available`, `blocked`, or `not_installed`;
- inspected layers: Core, selected Vault, generated output, runtime receipts,
  manual targets, and Local Private exclusions;
- changed layers, if the action has an accepted write path;
- `writes: none` for list, recommend, preview, verify, update comparison,
  disable review, and transfer preview paths;
- exact selected Vault write target for accepted apply paths;
- next safe action;
- rollback or defer guidance.

Raw scripts remain implementation/debug substrate. Normal-user output must not
make candidate discovery, pack authoring, export publication, or maintainer
release decisions part of routine consumption.

When a normal-user list or recommendation flow reads the official Core catalog,
the catalog is a discovery surface only. It may show official availability,
version, manifest hash, compatibility summary, changelog, and review evidence,
but it must still route preview/apply work through the reviewed manifest and the
selected Vault. The selected Vault remains canonical after accepted deployment.

## Power-User Maintenance Contract

Power-user capability-pack workflows are advanced maintenance-level workflows.
They cover explicit requests to:

- scan, propose, or evaluate candidate boundaries;
- assemble a pack draft;
- review a pack release or version update;
- review exportability;
- review deprecation, split, or merge outcomes.

These workflows may produce taxonomy, versioning, distribution, privacy, or
compatibility decisions for review. They must not create, activate, export,
publish, or deploy a pack without a later reviewed step.

Outputs are review packets by default, not active artifacts. A maintenance
review packet must include:

- requested flow and pack or candidate identity;
- evidence sources and authority layer;
- proposed boundary, draft membership, version, taxonomy, exportability,
  deprecation, split, or merge decision;
- practice, asset, selected Vault, generated output, runtime, and Local Private
  impact;
- clearly labeled state namespace: candidate discovery outcome,
  transfer/import state, comparison/report classification, runtime/generated
  status, or canonical `lifecycle_status`;
- required Reviewer, Architect, or Human gate;
- `writes: none`;
- next safe action plus rollback or defer guidance.

The advanced/maintenance label does not imply strict role permissions or hidden
access control. It tells agents to use deeper review gates and review-packet
outputs before any later apply, export, publish, or runtime deploy step.

## Invariants

- Selected User Vault metadata owns canonical pack lifecycle state after
  deployment.
- Practice and asset records remain individually governed by
  `workflows/review-practices.md` and `workflows/review-assets.md`.
- Pack snapshots are transfer and comparison artifacts, not live authority.
- Generated adapters and runtime installs are downstream projections only.
- Local-private evidence, raw logs, runtime manifests, receipts, user paths,
  secrets, and memory-system records are not pack lifecycle authority.

## State Namespace Rule

Capability-pack workflows use several state namespaces. Persisted
`lifecycle_status` fields belong only to the canonical pack lifecycle namespace.
Display, candidate, transfer/import, comparison/report, and runtime/generated
statuses must be labeled as their own output types and must not be written as
pack lifecycle values.

| Namespace | Owns | Examples |
| --- | --- | --- |
| Pack canonical lifecycle | Manifest and deployed-pack metadata `lifecycle_status`. | `candidate`, `reviewed`, `proposed`, `active`, `exportable`, `deprecated`, `retired`, `archived`, `blocked` |
| Adopter discovery/display status | Normal-user list/recommend/status copy. | `available`, `recommended`, `compatible`, `incompatible`, `installed`, `deployed`, `update_available`, `not_installed` |
| Candidate discovery outcome | Power-user discovery review-list output. | `candidate`, `baseline_control`, `extend_existing`, `deferred_overlap`, `rejected_false_positive`, `blocked_policy` |
| Transfer/import state | Export/import preview and import review state. | `preview`, `dry-run`, `proposed`, `accepted`, `rejected`, `blocked` |
| Comparison/report classification | Update, audit, diff, and lifecycle reports. | `clean_update_available`, `merge_required`, `same_version_hash_mismatch`, `unsupported`, `stale`, `drifted` |
| Runtime/generated status | Downstream generated output and runtime freshness. | `generated_current`, `generated_stale`, `generated_missing`, `runtime_current`, `runtime_drifted`, `manual_import_required` |
| Official catalog status | Core catalog availability and display state. | `available`, `deprecated`, `retired`, `blocked` |

Official catalog status values are not canonical `lifecycle_status` values. The
official catalog uses `catalog_status` so that display availability does not
change the manifest or deployed-pack lifecycle namespace.

## Official Core Catalog

The current-stage official catalog is Core-hosted and schema-backed:

- `schemas/capability-pack-catalog.schema.yaml`
- `catalog/capability-packs/index.yaml`
- `catalog/capability-packs/<pack-id>/README.md`
- `catalog/capability-packs/<pack-id>/CHANGELOG.md`

Each official catalog entry must include:

- pack id, title, official channel, and `catalog_status`;
- latest pack version;
- reviewed manifest path and `manifest_sha256`;
- compatibility summary and manifest-derived compatibility metadata;
- changelog and readme paths;
- public review evidence;
- explicit selected Vault authority after deployment;
- explicit private/local evidence exclusion;
- explicit pack-version versus Core-release independence;
- `candidate_review_packet: false`;
- `release_artifact_published: false` until a later reviewed release workflow
  exists.

Manifest hash checks fail closed: the same `pack_id` plus same pack version with
a different `manifest_sha256` requires review before list, recommendation,
preview, apply, export, import, or deployment work can proceed.

The official catalog is not a separate repository, release artifact channel,
export/import package, deployment receipt, generated adapter, runtime install,
or selected Vault source of truth. A Core tag or release may advertise a catalog
snapshot, but pack version and Core release/tag remain independent axes.

Local candidate review packets remain diagnostic or power-user review artifacts.
They cannot appear in the official catalog, become official packs, or become
export/import/deploy inputs without a later reviewed maintainer flow that
creates a reviewed manifest and official catalog entry.

## Canonical Lifecycle States

| State | Meaning | Agent action | Required gate |
| --- | --- | --- | --- |
| `candidate` | Reviewable candidate output from discovery. | Prepare candidate packet and false-positive controls. | Reviewer/Architect review before promotion. |
| `reviewed` | Pack snapshot or boundary passed review but is not yet proposed for deployment. | Preserve as reviewed artifact or release input. | Reviewer/Architect acceptance. |
| `proposed` | Boundary accepted for possible deployment. | Produce dry-run plan, diff, and lifecycle impact. | Human approval before active use. |
| `active` | Reviewed pack is deployed as an optional capability. | Report status and downstream follow-up. | Activation approval and record governance. |
| `exportable` | Pack may be exported after privacy review. | Produce exportability status only. | Human privacy/export review; #176 owns mechanics. |
| `deprecated` | Pack remains readable but is no longer preferred. | Warn, suggest replacement, avoid new activation. | Reviewed rationale and user-visible status. |
| `retired` | Pack should no longer be used. | Dry-run/apply only after approval. | Human approval and practice/asset lifecycle review. |
| `archived` | Pack is retained only for history or provenance. | Keep readable; do not recommend or newly deploy. | Reviewed archival rationale. |
| `blocked` | Transition is unsafe or lacks evidence. | Explain blockers and write nothing. | Human correction or explicit hold. |

## Transition Gates

- `candidate -> proposed`: requires Reviewer boundary review and Architect
  acceptance.
- `proposed -> active`: requires human approval of boundary, included records,
  member lifecycle impact, generated/runtime impact, and rollback/defer plan.
- `active -> exportable`: requires privacy/export review. #175 only reports this
  state; #176 defines export/import mechanics.
- `active -> deprecated`: requires reviewed replacement or rationale and a
  user-visible warning/status report.
- `deprecated -> retired`: requires dry-run report, affected records, generated
  and runtime follow-up, and human approval.
- `active/proposed -> split outcome`: requires proposed new pack ids, before/after
  membership diff, per-record hashes, conflicts, local-edit handling, generated
  and runtime follow-up, rollback/defer plan, and human approval.
- `active/proposed -> merge outcome`: requires target pack id, membership diff,
  duplicate/conflict handling, local-edit handling, generated and runtime
  follow-up, rollback/defer plan, and human approval.
- Any transition becomes `blocked` when metadata is malformed, hashes are
  missing, local user edits conflict with deployed hashes, runtime/generated
  authority is claimed, local-private evidence is required, destructive changes
  are requested without approval, or memory-system work would be needed.

## Safe Command Sequence

1. Run lifecycle reports in dry-run mode first:

   ```bash
   python3 scripts/manage_capability_pack_lifecycle.py \
     --vault-root <selected-vault> \
     --pack-id <pack-id> \
     --action <activate|exportable|deprecate|split|merge|disable|retire>
   ```

2. Read the report:
   - current pack id and action;
   - affected member records;
   - review gate;
   - generated output follow-up;
   - runtime follow-up;
   - rollback/defer guidance;
   - `writes: none` for unsafe or review-only paths.

3. Route to the correct reviewer:
   - practice status, archive, activation tier, or broad adapter behavior:
     `review-practices`;
   - asset status, deprecation, retirement, merge, or published targets:
     `review-assets`;
   - private/exportability boundary: `needs:human` and #176 export/import review;
   - runtime write: explicit runtime-write approval before apply.

4. Apply only currently supported write actions after approval:

   ```bash
   python3 scripts/manage_capability_pack_lifecycle.py \
     --vault-root <selected-vault> \
     --pack-id <pack-id> \
     --action retire \
     --apply
   ```

  `activate`, `exportable`, `deprecate`, `split`, and `merge` are review-only
  planning surfaces in #175. They must keep `writes: none`. `split` and
  `merge` report transition outcomes, not persisted lifecycle statuses.

5. After an approved Vault lifecycle change, publish and inspect downstream
   state separately:

   ```bash
   python3 scripts/publish_adapters.py --vault-root <selected-vault> --output-root <generated-root> --apply
   python3 scripts/install_foundry.py --vault-root <selected-vault> --adapter-root <generated-root>
   python3 scripts/sync_status.py --vault-root <selected-vault> --adapter-root <generated-root>
   ```

   Apply runtime install only after explicit runtime-write approval. ChatGPT
   remains manual import.

## Rollback And Defer

- Roll back approved metadata by restoring selected Vault metadata from a
  reviewed backup or reversing the approved commit.
- Rebuild generated output from Core plus selected Vault. Do not copy another
  machine's runtime files.
- Defer by leaving the pack in `blocked`, `candidate`, or `proposed` state and
  recording missing evidence, conflicts, or human decisions.
- When local user edits conflict with deployed hashes, preserve the selected
  Vault and propose a merge. Do not overwrite.

## Fail-Closed Conditions

Lifecycle tooling must refuse writes and print `writes: none` when it sees:

- malformed deployed-pack metadata;
- unsupported lifecycle state;
- missing deployed or imported hashes for member records;
- unsafe lifecycle claims such as runtime authority, generated authority,
  destructive deletion, forced overwrite, or automatic merge;
- local-private evidence references in lifecycle, evidence, export, or runtime
  projection sections;
- memory-system references;
- metadata paths that point at the wrong record id;
- missing record files or missing/mismatched indexes;
- generated/runtime evidence used as active or exportable authority.

## #176 Boundary

#175 may show `exportable` as a canonical lifecycle status and report that
export review is required. It must not implement export/import mechanics,
produce export bundles, or mark a pack exportable from generated/runtime
evidence alone. Privacy-safe export/import behavior belongs to #176.
