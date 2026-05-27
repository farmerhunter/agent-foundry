# Asset Policy

Canonical sources:

- `workflows/discover-assets.md`
- `workflows/create-asset.md`
- `workflows/review-assets.md`
- `schemas/asset.schema.yaml`
- `schemas/asset-candidate.schema.yaml`
- `indexes/asset_index.yaml`

Assets are user-facing reusable tools: skills, subagents, and automations. They are governed by canonical practices but are not canonical practices.

Memory, session summaries, and logs are evidence sources only. Apply META-006: memory can suggest, Agent Foundry decides.

Hermes native self-growth remains useful. Apply META-007: do not disable native memory or autonomous skill creation. Import useful native generated skills through Agent Foundry only when they should become durable or cross-agent.

Use `discover assets` / `发现可打包资产` to find repeated workflows worth packaging.

After approval:

```text
create or extend asset
  -> update asset index
  -> publish relevant adapters
  -> record usage evidence when useful
  -> report changed files
```

Usage evidence:

- Record ordinary non-sensitive usage automatically.
- Prefer `scripts/record_asset_usage.py`.
- Keep raw evidence local under `usage/local/`.
- Use `usage/usage-aggregate.yaml` for shared review statistics.
- Do not store raw transcripts or secrets.
