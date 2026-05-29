# Claude Code Instructions

This project contains Agent Foundry, the user's canonical agent capability system.

Published assets include ASSET-META-001 Practice Harvester and ASSET-ARCH-001 Architecture Design.

## Request Routing (META-008)

Before acting on a request, classify user intent:

- If the user asks to **execute a repeatable workflow** (harvest, design architecture, collaborate on a PR), match the request to an asset trigger and invoke the asset. During execution, reference the canonical practices the asset lists.
- If the user asks to **apply a constraint or change behavior** ("stop doing X", "always do Y"), match the request to a canonical practice and apply its Principle and Guidance. Do not invoke an asset for a one-off behavioral correction.
- If the user asks to **update or govern agent knowledge**, invoke the Practice Harvester asset (ASSET-META-001, META-001 through META-010, GOV-001 through GOV-004, RUNTIME-001 through RUNTIME-004).

Assets perform work; practices govern rules. Do not conflate them.

## Compact Preflight

Before substantial changes, check:

- Duplicate or derived truth source? Apply GOV-001.
- New machinery, layer, script, workflow, or integration? Apply GOV-002 and ARCH-001.
- Transient memory or chat summary used as fact? Apply GOV-003.
- Writing into user-owned runtime or agent configuration? Apply GOV-004 and RUNTIME-001.
- Syncing, publishing, or installing adapters? Apply RUNTIME-003.
- Producing rendered or converted output? Apply TEST-001.

## Practice Harvesting

Short commands:

- `harvest practices` / `做一次 harvest practice`
- `discover assets` / `发现可打包资产`
- `import skill <source>` / `导入这个 skill <source>`
- `publish practices` / `发布 practices`
- `review practices` / `检查 skill rot`
- `review assets` / `检查 asset rot`
- `refresh practices and assets` / `刷新practices和assets`

When asked to refresh, read `workflows/refresh.md` and follow the steps: git pull, conditionally regenerate adapters if canonical files changed, then install to local runtimes.

When asked to harvest, persist, deduplicate, merge, or publish reusable lessons:

1. Locate Agent Foundry Core and Vault. Use `AGENT_FOUNDRY_HOME`, then `~/.agent-foundry/config.yaml`, then the current directory only if canonical markers exist. The current project is evidence source, not canonical destination.
2. Read `workflows/harvest-practices.md`.
3. Read `schemas/practice-entry.schema.yaml`.
4. Search `indexes/practice_index.yaml`.
5. Update canonical practice entries under `practices/` first.
6. Do not publish `candidate` or `proposed` entries into adapters without human approval.
7. After the user approves a practice, apply it, promote it to `active` when applicable, update the index, and publish relevant adapters automatically.

When asked to discover reusable assets, read `workflows/discover-assets.md`, search `indexes/asset_index.yaml`, present asset candidates, and after approval create or extend assets and publish relevant adapters.

When an active asset is used, record concise non-sensitive usage evidence automatically, preferably with `scripts/record_asset_usage.py`.

## Cross-Project Governance

Apply GOV-001 through GOV-004 across all projects, not only inside Agent Foundry:

- GOV-001: protect canonical source of truth; derived views, generated files, caches, summaries, and compatibility artifacts must not become second hand-maintained truth sources.
- GOV-002: prefer the smallest maintainable mechanism; avoid adding scripts, layers, files, automations, or abstractions before ownership, validation, and failure modes are clear.
- GOV-003: treat transient context as evidence; memory, chat history, rollout summaries, and temporary notes must be verified against project-owned durable records.
- GOV-004: preserve maintainability and runtime capability; do not degrade native agent memory, skills, project instructions, self-improvement, or user-owned runtime configuration.

Treat memory, session summaries, and activity logs as evidence only. Durable rules and assets belong in Agent Foundry canonical records.

Do not suppress native agent memory or self-improvement features when available. Treat native learning outputs as candidates for Agent Foundry when they should become durable or cross-agent.

When publishing adapters into local runtimes, apply RUNTIME-001: treat agent runtime directories as shared user-owned environments. Use managed blocks, namespaced files, ownership markers, backups, dry-runs, and explicit adoption for unmanaged runtime paths. Never overwrite unmanaged runtime files by default.

Apply RUNTIME-002 when working with deployment manifests or offline sync: adapter profiles and runtime templates are portable repository content, while enabled targets, detected runtime paths, and adoption decisions belong in gitignored local manifests. Portable snapshots exclude machine-local runtime state by default.

Apply RUNTIME-003 after every sync or refresh operation: report the exact commit hash, unpushed commit count, adapters regenerated, runtime updates applied, and the exact next action required. Never report "done" when unpushed commits remain or runtime state is ambiguous.

Apply META-009 when publishing adapters: adapter quality must be executable and must verify the exact contract surface it claims to protect, including trigger vocabulary, Compact Preflight sections, canonical IDs, published asset IDs, target conventions, and target-specific fidelity, not only generated file existence or broad text matches.

Apply META-010 when reviewing assets: use lifecycle state, usage evidence, overlap, canonical coverage, stale triggers, and published targets before recommending keep, revise, deprecate, archive, split, or merge.

Apply RUNTIME-004 when recording or reviewing usage evidence: raw logs stay local under `usage/local/`; shared review uses sanitized aggregate rows in `usage/usage-aggregate.yaml`; missed activation and other review-only signals must not inflate shared usage counts.

## External Skills

When asked to borrow or evaluate external skills, read `workflows/import-external-skills.md`. Capture provenance, review security and license concerns, deduplicate, and ask before activation.

## GitHub And Multi-Agent Collaboration

Use the Agent Collaboration asset ASSET-COLLAB-001 for GitHub issue, PR, multi-agent sync, CLI comment, document conversion, and resume workflows. It applies canonical collaboration practices COLLAB-001 through COLLAB-005:

- For code work tied to a GitHub issue, use a feature branch and PR unless the user explicitly approves skipping the PR.
- Before moving an issue to review or closing it, comment with completion scope, linked PR or commit, verification method, verification results, and residual risks.
- If the user has authorized auto-merge, merge validated PRs by default unless review, hold, or risk conditions require confirmation.
- In multi-agent repositories, fetch or pull before issue work and verify remote sync when another machine may have pushed.
- Do not infer that the session is ending after compaction, interruption, or finishing one subtask; continue from the latest user request.

For GitHub comments containing Markdown with backticks, dollar signs, or command examples, apply IMPL-001: use `--body-file` or another safely quoted path instead of shell-interpreted inline strings.

For converted document deliverables, apply TEST-001: verify rendered output, font/encoding behavior, images, and source-to-output structure rather than relying only on command success.

## Architecture Design

Use canonical architecture practices ARCH-001 through ARCH-007:

- Boundaries before tools.
- Separate independent axes of change.
- Unify protocol while preserving semantics.
- Model inevitable failures as state.
- Let UI consume domain summaries.
- Scope MVP around the main path.
- Maintain design docs as lightweight context contracts for boundaries, decisions, contracts, operations, and user-facing runtime flows; mark rollout phases as implemented baseline, future work, rejected, or non-goal when state changes.
