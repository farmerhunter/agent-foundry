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

## Manual Fallback

If script execution is unavailable, manually inspect:

- `indexes/practice_index.yaml`
- `indexes/asset_index.yaml`
- changed files under `practices/`, `assets/`, and `adapters/`
- `usage/usage-aggregate.yaml`

## Rule

Do not silently ignore consistency failures. Report them and fix scoped issues before considering the publish complete.
