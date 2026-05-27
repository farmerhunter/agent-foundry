---
name: practice-harvester
description: Use when the user says "harvest practices", "做一次 harvest practice", "discover assets", "发现可打包资产", "提炼实践", "沉淀经验", "import skill", "导入这个 skill", "review practices", "检查 skill rot", "review assets", "检查 asset rot", "publish practices", "发布 practices", "refresh practices and assets", "刷新practices和assets", or asks to extract, persist, deduplicate, merge, review, import, borrow, approve, publish, or refresh reusable engineering practices or assets.
---

# Practice Harvester

This skill maintains Agent Foundry, the user's canonical capability system.

Asset ID: ASSET-META-001. Canonical constraints include META-001 through META-010 and RUNTIME-001 through RUNTIME-003.

## Asset vs Practice

This skill is an asset that performs a repeatable workflow. During execution, it references canonical practices as behavioral constraints. Do not confuse the skill with the practices it applies.

## Short Commands

- `harvest practices` / `做一次 harvest practice`: run the harvest workflow and present a concise review list.
- `discover assets` / `发现可打包资产`: find repeated workflows that should become skills, subagents, automations, or extensions.
- `import skill <source>` / `导入这个 skill <source>`: run the external skill import workflow.
- `publish practices` / `发布 practices`: publish adapters from current active practices.
- `review practices` / `检查 skill rot`: review for duplicates, stale entries, weak rules, and adapter drift.
- `review assets` / `检查 asset rot`: review reusable assets for usage, overlap, stale triggers, and adapter coverage.
- `refresh practices and assets` / `刷新practices和assets`: pull remote updates, conditionally regenerate adapters, and install to local runtimes. Read `workflows/refresh.md` from the agent-foundry repo.

## Workflow

1. Locate the canonical practice repository.
2. Select the workflow from the short command or user intent.
3. Read `references/harvest-workflow.md` for harvesting, `references/import-policy.md` for imports, `references/asset-policy.md` for assets, `workflows/refresh.md` from the repo for refresh, or the repository workflow file for publish/review.
4. Read `references/schema.md`.
5. Search the practice index before creating anything new.
6. Classify candidates as principle, pattern, heuristic, playbook, checklist, example, or anti-pattern.
7. Decide for each candidate: discard, merge, create, supersede, or defer.
8. Present a concise review list.
9. After the user approves a practice, apply the canonical change and publish relevant adapters automatically.
10. Report candidates, decisions, changed files, and review needs.

## Guardrails

- Do not add raw session notes directly into agent skills.
- Do not publish `candidate` or `proposed` entries into default adapters.
- Do not import external skills directly into active adapters.
- Ask for human approval before promoting a practice to `active`; after approval, publish relevant adapters unless the user asks to stage only.
- Record concise, non-sensitive asset usage evidence automatically when an active asset is invoked.
- Treat memory as evidence, not source of truth.
- Treat native agent learning outputs as candidate inputs; do not suppress native self-growth capabilities in agents that provide them.
- Treat agent runtime directories as shared user-owned environments. When publishing adapters, use managed blocks, namespaced files, ownership markers, backups, dry-runs, and explicit adoption for unmanaged runtime paths; never overwrite unmanaged runtime files by default.
- Separate portable adapter intent from machine-local deployment state. Keep adapter profiles and runtime templates in the repo, but keep enabled targets, detected paths, and adoption decisions in gitignored local manifests; portable snapshots exclude machine-local runtime state by default.
- After every sync or refresh, expose unambiguous state. Report the exact commit hash, unpushed commits, adapters regenerated, runtime updates applied, and next actions required. Do not leave the user guessing about alignment between canonical files, generated adapters, and local runtimes.
- Make adapter fidelity executable. Adapter quality checks must verify meaning signals such as triggers, canonical IDs, published asset IDs, target conventions, and high-fidelity requirements, not just generated file existence.
- Review assets with lifecycle evidence. Asset review should use lifecycle state, usage evidence, overlap, canonical coverage, stale triggers, and published targets before recommending keep, revise, deprecate, archive, split, or merge.
