# Check Consistency Workflow

Use this workflow before or after publishing adapters, and during periodic review.

## Automated Check

Run:

```bash
python3 scripts/check_consistency.py
```

This checks:

- index paths exist;
- practice IDs match filenames;
- asset IDs match filenames;
- asset records contain boundary fields;
- inactive statuses do not leak into adapters;
- no direct DeepSeek adapter exists;
- shared usage aggregate exists.
- adapter quality checks pass;
- activation tier and compact preflight checks pass.

For Core/Vault root selection checks, also run:

```bash
python3 scripts/foundry_config.py status
python3 scripts/check_foundry_roots.py --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault
python3 scripts/operation_context.py status --core-root . --vault-root ~/.agent-foundry/vault/my-agent-foundry-vault
```

This checks:

- selected Core markers exist;
- selected Vault markers exist;
- Vault indexes are present and parseable;
- indexed practice and asset paths resolve relative to the selected Vault;
- blank Vault indexes and empty usage aggregate are valid;
- missing or corrupt Vault indexes fail with actionable messages.
- blank Vault publishing reports nothing to publish;
- populated Vault publishing can produce adapter outputs in a temporary output root.
- operation-context status reports Core, selected Vault, allowed reads, and read-only forbidden writes.

To exercise deterministic same-root, blank Vault, maintainer-like Vault, and failure fixtures, run:

```bash
python3 scripts/test_foundry_roots.py
python3 scripts/test_operation_context.py
```

## Manual Fallback

If script execution is unavailable, manually inspect:

- `indexes/practice_index.yaml`
- `indexes/asset_index.yaml`
- changed files under `practices/`, `assets/`, and `adapters/`
- `usage/usage-aggregate.yaml`

In split mode, inspect the `indexes/`, `practices/`, `assets/`, and `usage/` paths under the selected User Vault, not under the public Core checkout.

## Rule

Do not silently ignore consistency failures. Report them and fix scoped issues before considering the publish complete.
