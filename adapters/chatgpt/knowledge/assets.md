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
- ASSET-COLLAB-001 Agent Collaboration
- ASSET-IMPL-001 Provider Integration Playbook

ASSET-COLLAB-001 currently maps to COLLAB-001 through COLLAB-012, IMPL-001, and TEST-001. It covers GitHub issue/PR traceability, repository sync, repo-local multi-agent workflow contracts, GitHub Project/Epic scheduling, issue Execution Contracts, Ready queues with dependency gates, Epic integration branch defaults, dual-surface review handoff, safe CLI Markdown comments, and render-verified document conversion. Proposed practices such as COLLAB-013 are not published into default adapters until approved active.

Assets are user-facing reusable tools discovered from repeated work:

- `skill`: reusable workflow or operating guide.
- `subagent`: bounded delegable role or investigation task.
- `automation`: scheduled or recurring check, report, reminder, or monitor.

Discovery outputs asset candidates, not canonical practices. Workflows and adapters are internal maintenance machinery, not user-facing asset types.

Memory, session summaries, and activity logs are evidence sources only. Memory can suggest; Agent Foundry decides.

Agent-native generated skills or self-improvement artifacts are also candidate inputs. Do not disable a capable agent's native learning just because Agent Foundry exists; route durable or cross-agent outputs through Agent Foundry review.

Cross-project governance practices GOV-001 through GOV-004 apply in any project: protect canonical source of truth, prefer the smallest maintainable mechanism, treat transient context as evidence, and preserve native runtime capability. `meta` practices govern the Agent Foundry capability lifecycle itself.

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
