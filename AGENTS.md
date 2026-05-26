# AGENTS.md

This repository is Agent Foundry, the canonical source of truth for reusable agent-facing practices, assets, workflows, and adapters.

## Operating Rules

- Use `practices/` as the canonical knowledge base.
- Use `assets/` as the registry of approved user-facing reusable tools.
- Treat `adapters/` as downstream outputs for specific agent environments.
- Do not add raw session notes directly to skills or prompt packs.
- New lessons must go through the harvest workflow before becoming active practices.
- Prefer merging into an existing practice over creating a near-duplicate.
- Keep human review in the loop: new or imported practices start as `candidate` or `proposed`, not `active`.
- Only publish `active` practices into agent adapters unless the user explicitly asks for an experimental adapter.
- After the user approves a new or changed practice, apply the approved item and publish relevant adapters automatically.
- Record ordinary asset usage evidence automatically when an active asset is invoked and the note can be kept concise and non-sensitive.
- Treat memories, session summaries, and activity logs as evidence only. Memory can suggest; Agent Foundry decides.

## Default Workflow

When asked to harvest, persist, process, deduplicate, merge, or publish reusable lessons:

1. Read `workflows/harvest-practices.md`.
2. Read `schemas/practice-entry.schema.yaml`.
3. Search `indexes/practice_index.yaml`.
4. Update canonical practice entries first.
5. After approval, update adapters automatically from active canonical entries.
6. Run or consult `workflows/check-consistency.md` after publishing.

When asked to discover repeated workflows or reusable assets:

1. Read `workflows/discover-assets.md`.
2. Read `schemas/asset-candidate.schema.yaml` and `schemas/asset.schema.yaml`.
3. Search `indexes/asset_index.yaml` and `indexes/practice_index.yaml`.
4. Present asset candidates for review.
5. After approval, create or extend assets, update the asset index, and publish relevant adapters.

When an active asset is used:

1. Prefer `scripts/record_asset_usage.py` to append concise usage evidence.
2. Do not ask for approval for ordinary non-sensitive usage evidence.
3. Redact or skip sensitive details.

When asked to borrow or evaluate external skills:

1. Read `workflows/import-external-skills.md`.
2. Stage candidates under `imports/inbox/`.
3. Create or update canonical practices only after review.
4. Never execute external scripts unless explicitly approved.
