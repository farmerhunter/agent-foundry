# Changelog

## 0.3.0

- Updated `META-003` to carry the AF13 external skill import/reference outcome
  model: `discard`, `reference_only`, `defer`, `merge_into_existing`,
  `propose_practice`, and `propose_asset`.
- Clarified that `publish_after_approval` is a post-approval action, not a
  terminal import outcome.
- Clarified that `reference_only` is sanitized selected Vault `imports/inbox/`
  review evidence only and cannot create active behavior, generated/runtime
  output, dedupe bypasses, or practice, asset, or capability-pack authority.
- No capability-pack deploy/apply, generated Skill publish, runtime mutation,
  Vault mutation, release artifact publishing, or private/local evidence export
  is authorized by this catalog entry.

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
