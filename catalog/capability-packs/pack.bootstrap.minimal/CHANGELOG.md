# Changelog

## 0.3.0

- Refreshed `META-003`, `META-011`, `META-012`, `META-013`, and the sanitized
  public `ASSET-META-001` snapshot from current reviewed canonical guidance.
- Added direct Practice Harvester dependency `GOV-007`; bootstrap now has 26
  members and still excludes optional collaboration content.
- Removed repository-specific selected-Vault merge authority from the public
  asset snapshot.
- Added the supported newer-version update, exact private backup and
  drift-checked restore path without implying generated/runtime activation.

## 0.2.1

- Added AF13 external-skill import/reference baseline semantics to bootstrap.
- Clarified import outcomes, `reference_only` selected Vault `imports/inbox/`
  evidence, and post-approval publish boundaries.
- Preserved runtime/generated publishing, real deploy/apply, and private/local
  evidence as separate reviewed gates outside pack authority.

## 0.2.0

- Cataloged as the first minimal official Core-hosted capability pack entry.
- Manifest reference remains the reviewed bootstrap fixture at
  `fixtures/capability-packs/bootstrap-minimal/manifest.yaml`.
- Pack version remains independent from Core release or git tag names.
- AF12-3 confirms this pack remains the home for `ASSET-META-001`; runtime and
  generated status stay folded into bootstrap/status surfaces rather than a
  standalone pack.
- AF12-3 correction folds source-of-truth boundary orientation, Generated /
  Runtime downstream separation, and Local Private evidence exclusion into
  bootstrap instead of publishing a standalone architecture-boundary pack.
- No release artifact publishing, export/import, deployment, activation, live
  Vault mutation, generated adapter publish, runtime install, or private/local
  evidence export is authorized by this catalog entry.
