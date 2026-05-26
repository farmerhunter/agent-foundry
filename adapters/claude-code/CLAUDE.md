# Claude Code Instructions

This project contains Agent Foundry, the user's canonical agent capability system.

## Practice Harvesting

Short commands:

- `harvest practices` / `做一次 harvest practice`
- `discover assets` / `发现可打包资产`
- `import skill <source>` / `导入这个 skill <source>`
- `publish practices` / `发布 practices`
- `review practices` / `检查 skill rot`
- `review assets` / `检查 asset rot`

When asked to harvest, persist, deduplicate, merge, or publish reusable lessons:

1. Read `workflows/harvest-practices.md`.
2. Read `schemas/practice-entry.schema.yaml`.
3. Search `indexes/practice_index.yaml`.
4. Update canonical practice entries under `practices/` first.
5. Do not publish `candidate` or `proposed` entries into adapters without human approval.
6. After the user approves a practice, apply it, promote it to `active` when applicable, update the index, and publish relevant adapters automatically.

When asked to discover reusable assets, read `workflows/discover-assets.md`, search `indexes/asset_index.yaml`, present asset candidates, and after approval create or extend assets and publish relevant adapters.

When an active asset is used, record concise non-sensitive usage evidence automatically, preferably with `scripts/record_asset_usage.py`.

Treat memory, session summaries, and activity logs as evidence only. Durable rules and assets belong in Agent Foundry canonical records.

Do not suppress native agent memory or self-improvement features when available. Treat native learning outputs as candidates for Agent Foundry when they should become durable or cross-agent.

When publishing adapters into local runtimes, apply RUNTIME-001: treat agent runtime directories as shared user-owned environments. Use managed blocks, namespaced files, ownership markers, backups, dry-runs, and explicit adoption for unmanaged runtime paths. Never overwrite unmanaged runtime files by default.

## External Skills

When asked to borrow or evaluate external skills, read `workflows/import-external-skills.md`. Capture provenance, review security and license concerns, deduplicate, and ask before activation.

## GitHub And Multi-Agent Collaboration

Use canonical collaboration practices COLLAB-001 through COLLAB-005:

- For code work tied to a GitHub issue, use a feature branch and PR unless the user explicitly approves skipping the PR.
- Before moving an issue to review or closing it, comment with completion scope, linked PR or commit, verification method, verification results, and residual risks.
- If the user has authorized auto-merge, merge validated PRs by default unless review, hold, or risk conditions require confirmation.
- In multi-agent repositories, fetch or pull before issue work and verify remote sync when another machine may have pushed.
- Do not infer that the session is ending after compaction, interruption, or finishing one subtask; continue from the latest user request.

For GitHub comments containing Markdown with backticks, dollar signs, or command examples, apply IMPL-001: use `--body-file` or another safely quoted path instead of shell-interpreted inline strings.

For converted document deliverables, apply TEST-001: verify rendered output, font/encoding behavior, images, and source-to-output structure rather than relying only on command success.

## Architecture Design

Use canonical architecture practices ARCH-001 through ARCH-006:

- Boundaries before tools.
- Separate independent axes of change.
- Unify protocol while preserving semantics.
- Model inevitable failures as state.
- Let UI consume domain summaries.
- Scope MVP around the main path.
