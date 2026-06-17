# Export And Import Capability Packs

Use this workflow when a reviewed capability pack may be shared, transferred, or
staged for import into a selected User Vault.

This workflow is privacy-safe and review-first. It plans and validates transfer
material; it does not export a private Vault, activate a pack, apply runtime
changes, or write selected Vault records.

## Boundaries

- Core owns public schemas, workflows, validators, fixtures, examples, and
  report-only transfer tooling.
- The selected User Vault owns canonical practice, asset, index, pack metadata,
  import staging, and reviewed lifecycle state.
- Generated adapters and runtime installs are downstream projections only.
- Local Private state includes raw evidence, session transcripts, local notes,
  runtime receipts, machine paths, local runtime manifests, user settings, and
  private Vault history.
- Offline repository snapshots are separate recovery/sync tooling. Do not treat
  `scripts/export_snapshot.py`, `scripts/import_snapshot.py`, or
  `scripts/compare_snapshot.py` as capability-pack export/import semantics.

## Allowed Transfer Material

- Capability pack manifest and reviewed metadata.
- Included practice or asset records only when approved for distribution or
  represented as sanitized copies.
- Public Core workflow, schema, template, example, fixture, and checksum
  references.
- Review notes that contain only public issue/PR links, sanitized aggregate
  summaries, or stable record ids.

## Exclusions

Fail closed before sharing or import acceptance when transfer material contains:

- raw private evidence, raw logs, session transcripts, local notes, secrets, or
  tokens;
- absolute user paths such as `/Users/...`, `~`, `.agent-foundry`, `.codex`, or
  `.trae`;
- runtime receipts, runtime manifests, machine-specific settings, usage/local,
  runtime/local, or sync/local material;
- private project ids, raw Vault history, generated output, or runtime files as
  authority;
- memory-system records or references;
- executable payload execution, install side effects, destructive changes, or
  automatic activation claims.

## Import States

| State | Meaning | Writes |
| --- | --- | --- |
| `preview` | Transfer package is inspected for contents, privacy, and compatibility. | none |
| `dry-run` | Planner reports selected Vault diffs, conflicts, and review gates. | none |
| `proposed` | Import is ready for human or Reviewer acceptance. | none |
| `accepted` | Human accepted the import plan; apply must use a separate reviewed workflow. | none in this workflow |
| `rejected` | Import is declined and staged material should be discarded. | none |
| `blocked` | Privacy, compatibility, conflict, or authority checks failed. | none |

Imported material must not silently become active. Practice and asset records
still pass through `workflows/review-practices.md` and
`workflows/review-assets.md`; pack lifecycle state still follows
`workflows/manage-capability-pack-lifecycle.md`.

## Safe Sequence

1. Preview the transfer package:

   ```bash
   python3 scripts/plan_capability_pack_transfer.py \
     <pack-root> \
     --vault-root <selected-vault> \
     --action import-preview \
     --import-state preview
   ```

2. Run a dry-run diff before any selected Vault write:

   ```bash
   python3 scripts/plan_capability_pack_transfer.py \
     <pack-root> \
     --vault-root <selected-vault> \
     --action import-dry-run \
     --import-state dry-run
   ```

3. Review the report for allowed contents, excluded material, conflicts,
   checksum mismatches, local-edit preservation, rollback guidance, and
   `writes: none`.

4. Route the next decision:
   - privacy/export boundary: human or Reviewer privacy review;
   - practice content or lifecycle: `review-practices`;
   - asset content, published targets, or status: `review-assets`;
   - runtime apply: explicit runtime-write approval in a separate workflow.

5. Apply accepted material only through an existing reviewed deployment,
   practice, asset, or lifecycle workflow. This workflow never performs that
   write.

## Conflict Handling

- Same id with incompatible kind, path, or provenance fails closed.
- Same pack id and version with a different manifest hash fails closed.
- Existing selected Vault edits remain canonical user state. The transfer report
  should propose merge review rather than overwrite.
- Executable payloads remain inert and cannot be executed or installed during
  transfer.

## Rollback

- Before apply, rollback means discarding staged transfer material or rejecting
  the import.
- After a separately approved Vault change, rollback by reverting the reviewed
  Vault commit or restoring a reviewed backup.
- Regenerate adapters from Core plus the selected Vault after approved rollback;
  do not copy runtime files from another machine.

## Status Output

Transfer reports must include:

- package root, selected Vault root, pack id, version, and review state;
- allowed export contents and excluded material;
- diff-before-write rows for each included record;
- validation status and failure reasons;
- rollback and handoff guidance;
- `writes: none`.
