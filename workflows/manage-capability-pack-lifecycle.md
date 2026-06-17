# Manage Capability Pack Lifecycle Workflow

Use this workflow when a capability pack needs lifecycle review after detection,
deployment, update comparison, split/merge analysis, deprecation, retirement, or
exportability discussion.

This workflow plans and reports lifecycle transitions. It does not bypass
practice review, asset review, runtime approval, export review, or human approval.

## Invariants

- Selected User Vault metadata owns canonical pack lifecycle state after
  deployment.
- Practice and asset records remain individually governed by
  `workflows/review-practices.md` and `workflows/review-assets.md`.
- Pack snapshots are transfer and comparison artifacts, not live authority.
- Generated adapters and runtime installs are downstream projections only.
- Local-private evidence, raw logs, runtime manifests, receipts, user paths,
  secrets, and memory-system records are not pack lifecycle authority.

## Lifecycle States

| State | Meaning | Agent action | Required gate |
| --- | --- | --- | --- |
| `detected` | Evidence suggests a possible pack. | Gather public/sanitized evidence and score signals. | Privacy gate if private evidence is needed. |
| `candidate` | Reviewable candidate output from discovery. | Prepare candidate packet and false-positive controls. | Reviewer/Architect review before promotion. |
| `proposed` | Boundary accepted for possible deployment. | Produce dry-run plan, diff, and lifecycle impact. | Human approval before active use. |
| `active` | Reviewed pack is deployed as an optional capability. | Report status and downstream follow-up. | Activation approval and record governance. |
| `exportable` | Pack may be exported after privacy review. | Produce exportability status only. | Human privacy/export review; #176 owns mechanics. |
| `deprecated` | Pack remains readable but is no longer preferred. | Warn, suggest replacement, avoid new activation. | Reviewed rationale and user-visible status. |
| `split` | Pack boundary is divided into multiple packs. | Produce membership diff and conflict report. | Human approval with rollback/defer plan. |
| `merged` | Pack boundary is merged into another pack. | Produce target-pack diff and conflict report. | Human approval with conflict handling. |
| `retired` | Pack should no longer be used. | Dry-run/apply only after approval. | Human approval and practice/asset lifecycle review. |
| `blocked` | Transition is unsafe or lacks evidence. | Explain blockers and write nothing. | Human correction or explicit hold. |

## Transition Gates

- `detected -> candidate`: requires passing discovery authority, privacy,
  false-positive, and bootstrap-duplicate gates. No activation or export.
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
- `active/proposed -> split`: requires proposed new pack ids, before/after
  membership diff, per-record hashes, conflicts, local-edit handling, generated
  and runtime follow-up, rollback/defer plan, and human approval.
- `active/proposed -> merged`: requires target pack id, membership diff,
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
   planning surfaces in #175. They must keep `writes: none`.

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

#175 may show `exportable` as a lifecycle status and report that export review is
required. It must not implement export/import mechanics, produce export bundles,
or mark a pack exportable from generated/runtime evidence alone. Privacy-safe
export/import behavior belongs to #176.
