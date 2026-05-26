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

Use `discover assets` / `发现可打包资产` to find repeated workflows worth packaging.

Candidate forms:

- `skill`: reusable workflow or operating guide.
- `subagent`: bounded delegable role or investigation task.
- `automation`: scheduled or recurring check, report, reminder, or monitor.
- `extend_existing`: improve an existing asset.
- `skip`: one-off, vague, sensitive, or already covered.
- `defer`: promising but needs more evidence.

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
- Do not store raw transcripts or secrets.
