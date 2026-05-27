# Assets

Canonical sources:

- `workflows/discover-assets.md`
- `workflows/create-asset.md`
- `workflows/review-assets.md`
- `schemas/asset.schema.yaml`
- `schemas/asset-candidate.schema.yaml`
- `indexes/asset_index.yaml`

Published asset IDs:

- ASSET-META-001 Practice Harvester
- ASSET-ARCH-001 Architecture Design

Assets are user-facing reusable tools discovered from repeated work:

- `skill`: reusable workflow or operating guide.
- `subagent`: bounded delegable role or investigation task.
- `automation`: scheduled or recurring check, report, reminder, or monitor.

Discovery outputs asset candidates, not canonical practices. Workflows and adapters are internal maintenance machinery, not user-facing asset types.

Memory, session summaries, and activity logs are evidence sources only. Memory can suggest; Agent Foundry decides.

Agent-native generated skills or self-improvement artifacts are also candidate inputs. Do not disable a capable agent's native learning just because Agent Foundry exists; route durable or cross-agent outputs through Agent Foundry review.

After approval:

```text
create or extend asset
  -> update asset index
  -> publish relevant adapters
  -> record usage evidence when useful
  -> report changed files
```

Usage evidence should be recorded automatically when an active asset is invoked and the note can be concise and non-sensitive. Do not store raw transcripts or secrets.

Raw usage evidence stays local under `usage/local/`. Cross-machine review uses sanitized shared aggregate rows in `usage/usage-aggregate.yaml`.
